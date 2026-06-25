import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agentic_bench_images.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agentic_bench_images", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AgenticBenchImagesTest(unittest.TestCase):
    def test_validate_registry_resolves_image_manifest_inventory(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_manifest = root / "manifests" / "images" / "repozero.yaml"
            image_manifest.parent.mkdir(parents=True)
            image_manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: repozero_py2js_smoke
                    images:
                      - id: repozero_runtime
                        required: true
                        local_ref: ghcr.io/jessezzzzz/repoarena-new:latest
                        image_ref: 100.97.118.137:8555/agentic-bench/repozero-runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                        fallback_tar: images/repozero/repoarena-new_latest.tar
                    """
                ).strip(),
                encoding="utf-8",
            )
            registry = root / "manifests" / "bench_registry.yaml"
            registry.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.registry.v1
                    registry:
                      name: swe_data_harness_p0
                      url: https://100.97.118.137:8555
                      domain: 100.97.118.137:8555
                    image_manifests:
                      - id: repozero
                        path: manifests/images/repozero.yaml
                    """
                ).strip(),
                encoding="utf-8",
            )

            summary = module.validate_registry(registry, asset_root=root)

        self.assertEqual(summary["schema_version"], "agentic_bench.registry_validation.v1")
        self.assertEqual(summary["registry"]["domain"], "100.97.118.137:8555")
        self.assertEqual(summary["counts"], {"manifests": 1, "images": 1, "required_images": 1, "missing_manifests": 0})
        self.assertEqual(summary["manifests"][0]["id"], "repozero")
        self.assertEqual(summary["manifests"][0]["bench_id"], "repozero_py2js_smoke")
        self.assertEqual(summary["manifests"][0]["images"][0]["local_refs"], ["ghcr.io/jessezzzzz/repoarena-new:latest"])

    def test_check_manifest_uses_injected_docker_inspect_and_verifies_fallback_sha(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tar_path = root / "images" / "repozero" / "runtime.tar"
            tar_path.parent.mkdir(parents=True)
            tar_path.write_bytes(b"fake docker tar bytes")
            digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
            manifest = root / "repozero.yaml"
            manifest.write_text(
                textwrap.dedent(
                    f"""
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: repozero_py2js_smoke
                    images:
                      - id: repozero_runtime
                        required: true
                        local_ref: ghcr.io/jessezzzzz/repoarena-new:latest
                        image_ref: 100.97.118.137:8555/agentic-bench/repozero-runtime@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
                        fallback_tar: images/repozero/runtime.tar
                        fallback_tar_sha256: {digest}
                    """
                ).strip(),
                encoding="utf-8",
            )

            docker_calls = []

            def fake_runner(argv, env):
                docker_calls.append(argv)
                if argv[:3] == ["docker", "image", "inspect"]:
                    return module.CommandResult(0, "[]", "")
                raise AssertionError(f"unexpected docker command: {argv!r}")

            summary = module.check_image_manifest(
                manifest,
                asset_root=root,
                docker_host="unix:///tmp/rl/run/docker.sock",
                runner=fake_runner,
            )

        self.assertEqual(summary["counts"]["present"], 1)
        self.assertEqual(summary["counts"]["missing"], 0)
        self.assertEqual(summary["counts"]["tar_verified"], 1)
        self.assertEqual(summary["images"][0]["status"], "present")
        self.assertEqual(summary["images"][0]["fallback"]["sha256_status"], "match")
        self.assertEqual(docker_calls, [["docker", "image", "inspect", "ghcr.io/jessezzzzz/repoarena-new:latest"]])

    def test_cli_validate_emits_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_manifest = root / "image.yaml"
            image_manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: p0_smoke
                    images:
                      - id: p0_click
                        image_ref: 100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
                    """
                ).strip(),
                encoding="utf-8",
            )
            registry = root / "registry.yaml"
            registry.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.registry.v1
                    registry:
                      domain: 100.97.118.137:8555
                    image_manifests:
                      - id: p0
                        path: image.yaml
                    """
                ).strip(),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "validate",
                    "--registry",
                    str(registry),
                    "--asset-root",
                    str(root),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["counts"]["manifests"], 1)
        self.assertEqual(summary["counts"]["images"], 1)


if __name__ == "__main__":
    unittest.main()
