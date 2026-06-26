import contextlib
import hashlib
import io
import importlib.util
import json
import os
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

    def test_check_manifest_tags_pulled_digest_to_local_ref(self):
        module = load_module()
        digest_ref = "100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-install-windows-3.11@sha256:5dcb2476f1597ebc81da54ad010e9dddf5cc5bb2670f225c7be36e8b50ec4265"
        local_ref = "tb2-offline/install-windows-3.11:20260425"
        image_id = "sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "tb2-install-windows.yaml"
            manifest.write_text(
                textwrap.dedent(
                    f"""
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: tb2_install_windows_probe
                    images:
                      - id: tb2_install_windows_3_11
                        required: true
                        local_ref: {local_ref}
                        image_ref: {digest_ref}
                        source_image_id: {image_id}
                    """
                ).strip(),
                encoding="utf-8",
            )

            calls = []

            def fake_runner(argv, env):
                calls.append(argv)
                if argv == ["docker", "image", "inspect", local_ref]:
                    if calls.count(argv) == 1:
                        return module.CommandResult(1, "", "No such image")
                    return module.CommandResult(
                        0,
                        json.dumps([{"Id": image_id, "RepoDigests": [digest_ref]}]),
                        "",
                    )
                if argv == ["docker", "pull", digest_ref]:
                    return module.CommandResult(0, "pulled", "")
                if argv == ["docker", "image", "inspect", digest_ref]:
                    return module.CommandResult(
                        0,
                        json.dumps([{"Id": image_id, "RepoDigests": [digest_ref]}]),
                        "",
                    )
                if argv == ["docker", "tag", digest_ref, local_ref]:
                    return module.CommandResult(0, "", "")
                raise AssertionError(f"unexpected docker command: {argv!r}")

            summary = module.check_image_manifest(
                manifest,
                asset_root=root,
                runner=fake_runner,
                allow_pull=True,
            )

        self.assertEqual(summary["counts"]["present"], 1)
        self.assertEqual(summary["counts"]["pulled"], 1)
        self.assertEqual(summary["counts"]["tagged"], 1)
        self.assertEqual(summary["images"][0]["present_ref"], local_ref)
        self.assertEqual(summary["images"][0]["local_tag_status"], "tagged")
        self.assertIn(["docker", "tag", digest_ref, local_ref], calls)


    def test_check_manifest_rejects_present_tag_with_wrong_image_identity(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "swebench.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: swe_bench_verified_smoke
                    images:
                      - id: astropy_1776_astropy-7671
                        required: true
                        local_ref: swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest
                        source_image_id: sha256:expected-base
                        source_repo_digest: swebench/sweb.eval.x86_64.astropy_1776_astropy-7671@sha256:expecteddigest
                    """
                ).strip(),
                encoding="utf-8",
            )

            def fake_runner(argv, env):
                self.assertEqual(argv, ["docker", "image", "inspect", "swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest"])
                return module.CommandResult(
                    0,
                    json.dumps(
                        [
                            {
                                "Id": "sha256:wrong-prebuilt",
                                "RepoDigests": ["swerex-prebuilt@sha256:other"],
                            }
                        ]
                    ),
                    "",
                )

            summary = module.check_image_manifest(manifest, asset_root=root, runner=fake_runner)

        self.assertEqual(summary["counts"]["identity_mismatch"], 1)
        self.assertEqual(summary["counts"]["present"], 0)
        self.assertEqual(summary["counts"]["missing"], 0)
        self.assertEqual(summary["images"][0]["status"], "identity_mismatch")
        self.assertEqual(summary["images"][0]["inspect_attempts"][0]["identity_status"], "mismatch")
        self.assertEqual(summary["images"][0]["inspect_attempts"][0]["actual_image_id"], "sha256:wrong-prebuilt")
        self.assertEqual(summary["images"][0]["inspect_attempts"][0]["expected_image_ids"], ["sha256:expected-base"])


    def test_optional_missing_can_be_fatal_for_optional_audit(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "optional.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: optional_runtime
                    images:
                      - id: optional_placeholder
                        required: false
                        image_transport: todo
                    """
                ).strip(),
                encoding="utf-8",
            )

            def runner(argv, env):
                return module.CommandResult(1, "", "missing")

            summary = module.check_image_manifest(
                manifest,
                asset_root=root,
                runner=runner,
                fail_on_optional_missing=True,
            )

        self.assertEqual(summary["counts"]["optional_missing"], 1)
        self.assertTrue(summary["mode"]["fail_on_optional_missing"])

    def test_inventory_cache_filters_prefixes_and_sets_docker_host(self):
        module = load_module()
        calls = []

        def fake_runner(argv, env):
            calls.append((argv, env.get("DOCKER_HOST")))
            self.assertEqual(argv, ["docker", "image", "ls", "--format", "{{json .}}"] )
            return module.CommandResult(
                0,
                "\n".join(
                    [
                        json.dumps({"Repository": "tb2-offline/headless-terminal", "Tag": "20260425", "ID": "sha256:aaa", "Digest": "<none>", "Size": "185MB"}),
                        json.dumps({"Repository": "swebench/sweb.eval.x86_64.django_1776_django-13810", "Tag": "latest", "ID": "sha256:bbb", "Digest": "<none>", "Size": "1.2GB"}),
                        json.dumps({"Repository": "unrelated/image", "Tag": "latest", "ID": "sha256:ccc", "Digest": "<none>", "Size": "10MB"}),
                    ]
                ) + "\n",
                "",
            )

        summary = module.docker_cache_inventory(
            prefixes=["tb2-offline/", "swebench/"],
            docker_host="unix:///tmp/test-docker.sock",
            runner=fake_runner,
        )

        self.assertEqual(calls, [(["docker", "image", "ls", "--format", "{{json .}}"], "unix:///tmp/test-docker.sock")])
        self.assertEqual(summary["schema_version"], "agentic_bench.docker_cache_inventory.v1")
        self.assertEqual(summary["counts"], {"images": 2, "prefixes": 2})
        self.assertEqual(
            [image["ref"] for image in summary["images"]],
            [
                "swebench/sweb.eval.x86_64.django_1776_django-13810:latest",
                "tb2-offline/headless-terminal:20260425",
            ],
        )


    def test_inventory_cache_can_enrich_full_image_identity(self):
        module = load_module()
        calls = []

        def fake_runner(argv, env):
            calls.append(argv)
            if argv == ["docker", "image", "ls", "--format", "{{json .}}"]:
                return module.CommandResult(
                    0,
                    json.dumps(
                        {
                            "Repository": "tb2-offline/gcode-to-text",
                            "Tag": "20260425",
                            "ID": "8fba1dce95b8",
                            "Digest": "<none>",
                            "Size": "182MB",
                        }
                    ) + "\n",
                    "",
                )
            if argv == ["docker", "image", "inspect", "tb2-offline/gcode-to-text:20260425"]:
                return module.CommandResult(
                    0,
                    json.dumps(
                        [
                            {
                                "Id": "sha256:8fba1dce95b8full",
                                "RepoDigests": ["tb2-offline/gcode-to-text@sha256:repo-digest"],
                            }
                        ]
                    ),
                    "",
                )
            raise AssertionError(f"unexpected docker command: {argv!r}")

        summary = module.docker_cache_inventory(
            prefixes=["tb2-offline/"],
            docker_host="unix:///var/run/docker.sock",
            runner=fake_runner,
            inspect_identities=True,
        )

        self.assertEqual(summary["counts"]["identity_inspected"], 1)
        self.assertEqual(summary["counts"]["identity_errors"], 0)
        self.assertEqual(summary["images"][0]["full_image_id"], "sha256:8fba1dce95b8full")
        self.assertEqual(summary["images"][0]["repo_digests"], ["tb2-offline/gcode-to-text@sha256:repo-digest"])
        self.assertEqual(
            calls,
            [
                ["docker", "image", "ls", "--format", "{{json .}}"],
                ["docker", "image", "inspect", "tb2-offline/gcode-to-text:20260425"],
            ],
        )


    def test_remote_inventory_cache_runs_host_scoped_inventory_commands(self):
        module = load_module()
        calls = []

        def fake_runner(argv, env):
            calls.append((argv, env))
            self.assertEqual(argv[:2], ["ssh", "swe_dev"])
            self.assertIn("agentic_bench_images.py inventory-cache", argv[-1])
            self.assertIn("--prefix tb2-offline/", argv[-1])
            self.assertIn("--prefix swebench/", argv[-1])
            self.assertIn("--docker-host unix:///var/run/docker.sock", argv[-1])
            self.assertIn("--output /shared/inventory/swe_dev.docker_cache_inventory.json", argv[-1])
            self.assertIn("--inspect-identities", argv[-1])
            return module.CommandResult(0, "inventory ok\n", "")

        summary = module.remote_cache_inventory(
            hosts=["swe_dev"],
            prefixes=["tb2-offline/", "swebench/"],
            project_root="/shared/repo",
            output_dir="/shared/inventory",
            docker_host="unix:///var/run/docker.sock",
            inspect_identities=True,
            runner=fake_runner,
        )

        self.assertEqual(summary["schema_version"], "agentic_bench.remote_cache_inventory.v1")
        self.assertEqual(summary["counts"], {"hosts": 1, "ok": 1, "failed": 0})
        self.assertEqual(summary["hosts"][0]["host"], "swe_dev")
        self.assertEqual(summary["hosts"][0]["output"], "/shared/inventory/swe_dev.docker_cache_inventory.json")
        self.assertEqual(len(calls), 1)


    def test_remote_inventory_cache_accepts_labelled_ssh_targets(self):
        module = load_module()
        calls = []

        def fake_runner(argv, env):
            calls.append(argv)
            self.assertEqual(argv[1], "zengweijun+zwj.group@endpoint")
            self.assertIn("--output /shared/inventory/swe_dev.docker_cache_inventory.json", argv[-1])
            self.assertIn("--host-label swe_dev", argv[-1])
            return module.CommandResult(0, "", "")

        summary = module.remote_cache_inventory(
            hosts=["swe_dev=zengweijun+zwj.group@endpoint"],
            prefixes=[],
            project_root="/shared/repo",
            output_dir="/shared/inventory",
            runner=fake_runner,
        )

        self.assertEqual(summary["hosts"][0]["host"], "swe_dev")
        self.assertEqual(summary["hosts"][0]["ssh_target"], "zengweijun+zwj.group@endpoint")
        self.assertEqual(summary["hosts"][0]["output"], "/shared/inventory/swe_dev.docker_cache_inventory.json")


    def test_match_manifest_inventory_finds_remote_cache_candidates(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "tb2.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: terminal_bench_2_1_smoke
                    images:
                      - id: mteb_retrieve
                        required: true
                        local_ref: tb2-offline/mteb-retrieve:20260425
                        source_image_id: sha256:expected-full-id
                      - id: still_missing
                        required: true
                        local_ref: tb2-offline/still-missing:20260425
                    """
                ).strip(),
                encoding="utf-8",
            )
            inventory = root / "swe_dev.docker_cache_inventory.json"
            inventory.write_text(
                json.dumps(
                    {
                        "schema_version": "agentic_bench.docker_cache_inventory.v1",
                        "host": "swe_dev",
                        "images": [
                            {
                                "ref": "tb2-offline/mteb-retrieve:20260425",
                                "image_id": "short",
                                "full_image_id": "sha256:expected-full-id",
                                "repo_digests": [],
                                "size": "1.2GB",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = module.match_manifest_inventory(
                manifest,
                inventories=[inventory],
                asset_root=root,
            )

        self.assertEqual(summary["schema_version"], "agentic_bench.image_inventory_match.v1")
        self.assertEqual(summary["counts"]["images"], 2)
        self.assertEqual(summary["counts"]["matched"], 1)
        self.assertEqual(summary["counts"]["required_missing"], 1)
        self.assertEqual(summary["images"][0]["id"], "mteb_retrieve")
        self.assertEqual(summary["images"][0]["match_status"], "matched")
        self.assertEqual(summary["images"][0]["matches"][0]["host"], "swe_dev")
        self.assertEqual(summary["images"][0]["matches"][0]["match_reason"], "ref")
        self.assertEqual(summary["images"][1]["match_status"], "missing")


    def test_match_manifest_inventory_rejects_ref_match_with_wrong_identity(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "tb2.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: terminal_bench_2_1_smoke
                    images:
                      - id: mteb_retrieve
                        required: true
                        local_ref: tb2-offline/mteb-retrieve:20260425
                        source_image_id: sha256:expected-full-id
                    """
                ).strip(),
                encoding="utf-8",
            )
            inventory = root / "swe_dev.docker_cache_inventory.json"
            inventory.write_text(
                json.dumps(
                    {
                        "schema_version": "agentic_bench.docker_cache_inventory.v1",
                        "host": "swe_dev",
                        "images": [
                            {
                                "ref": "tb2-offline/mteb-retrieve:20260425",
                                "image_id": "short",
                                "full_image_id": "sha256:wrong-cache-id",
                                "repo_digests": [],
                                "size": "1.2GB",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = module.match_manifest_inventory(
                manifest,
                inventories=[inventory],
                asset_root=root,
            )

        self.assertEqual(summary["counts"]["matched"], 0)
        self.assertEqual(summary["counts"]["required_missing"], 1)
        self.assertEqual(summary["counts"]["identity_mismatch"], 1)
        self.assertEqual(summary["images"][0]["match_status"], "identity_mismatch")
        self.assertEqual(summary["images"][0]["matches"], [])
        self.assertEqual(summary["images"][0]["identity_mismatches"][0]["full_image_id"], "sha256:wrong-cache-id")


    def test_plan_missing_transport_uses_remote_cache_match_for_stage_rows(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "tb2.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: terminal_bench_2_1_smoke
                    images:
                      - id: tb2_missing_transport
                        required: true
                        local_ref: tb2-offline/missing-transport:20260425
                        source_image_id: sha256:abc123
                      - id: tb2_digest_ready
                        required: true
                        local_ref: tb2-offline/ready:20260425
                        image_ref: 100.97.118.137:8555/swe-data-harness/ready@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                    """
                ).strip(),
                encoding="utf-8",
            )
            inventory = root / "swe_dev.docker_cache_inventory.json"
            inventory.write_text(
                json.dumps(
                    {
                        "schema_version": "agentic_bench.docker_cache_inventory.v1",
                        "host": "swe_dev",
                        "images": [
                            {
                                "ref": "tb2-offline/missing-transport:20260425",
                                "image_id": "abc123",
                                "size": "2GB",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = module.plan_missing_transport_staging(
                manifest,
                inventories=[inventory],
                tar_dir="/shared/images/tb2",
                registry_domain="100.97.118.137:8555",
                repository_prefix="swe-data-harness",
                p0_name_prefix="terminal-bench-2-1-",
            )

        self.assertEqual(summary["schema_version"], "agentic_bench.missing_transport_staging_plan.v1")
        self.assertEqual(summary["counts"], {"missing_transport": 1, "matched": 1, "unmatched": 0})
        self.assertEqual(summary["rows"][0]["id"], "tb2_missing_transport")
        self.assertEqual(summary["rows"][0]["slug"], "missing-transport")
        self.assertEqual(summary["rows"][0]["source_host"], "swe_dev")
        self.assertEqual(summary["rows"][0]["fallback_tar"], "/shared/images/tb2/missing-transport.tar")
        self.assertEqual(summary["rows"][0]["p0_tag"], "100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-missing-transport:20260425")


    def test_cli_dispatches_remote_inventory_command(self):
        module = load_module()
        calls = []
        original = module.remote_cache_inventory

        def fake_remote_cache_inventory(**kwargs):
            calls.append(kwargs)
            return {
                "schema_version": "agentic_bench.remote_cache_inventory.v1",
                "counts": {"hosts": 1, "ok": 1, "failed": 0},
                "hosts": [{"host": "swe_dev", "status": "ok", "output": "/out/swe_dev.docker_cache_inventory.json"}],
            }

        module.remote_cache_inventory = fake_remote_cache_inventory
        try:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = module.main([
                    "inventory-remote-cache",
                    "--host",
                    "swe_dev",
                    "--prefix",
                    "tb2-offline/",
                    "--project-root",
                    "/shared/repo",
                    "--output-dir",
                    "/out",
                    "--json",
                ])
        finally:
            module.remote_cache_inventory = original

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0]["hosts"], ["swe_dev"])
        self.assertEqual(calls[0]["prefixes"], ["tb2-offline/"])
        self.assertIn("agentic_bench.remote_cache_inventory.v1", stdout.getvalue())



    def test_stage_cache_images_script_executes_with_fake_docker(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
                    if [ "$1 $2" = "image inspect" ]; then
                      printf '[{"Id":"sha256:fake"}]\n'
                      exit 0
                    fi
                    if [ "$1" = "save" ]; then
                      out=""
                      while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                          out="$2"
                          shift 2
                          continue
                        fi
                        shift
                      done
                      printf 'fake docker tar bytes' > "$out"
                      exit 0
                    fi
                    echo "unexpected docker $*" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "missing.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_missing\tmissing\ttb2-offline/missing:20260425\tsha256:fake\tswe_dev\ttb2-offline/missing:20260425\tfake\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/missing:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_DOCKER_LOG"] = str(root / "docker.log")
            proc = subprocess.run(
                ["bash", str(script), "--plan", str(plan), "--execute", "--output-tsv", str(out_tsv)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(tar_path.is_file())
            result_text = out_tsv.read_text(encoding="utf-8")
            self.assertIn("source_host", result_text)
            self.assertIn("source_ref", result_text)
            self.assertIn("source_cache_image_id", result_text)
            self.assertIn("actual_image_id", result_text)
            self.assertIn("fallback_tar_sha256", result_text)
            self.assertIn("\tswe_dev\t", result_text)
            self.assertIn("\tsha256:fake\tsaved", result_text)
            self.assertIn(hashlib.sha256(b"fake docker tar bytes").hexdigest(), result_text)


    def test_stage_cache_images_script_rejects_push_without_digest(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
                    if [ "$1 $2" = "image inspect" ]; then
                      printf '[{"Id":"sha256:fake"}]\n'
                      exit 0
                    fi
                    if [ "$1" = "save" ]; then
                      out=""
                      while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                          out="$2"
                          shift 2
                          continue
                        fi
                        shift
                      done
                      printf 'fake docker tar bytes' > "$out"
                      exit 0
                    fi
                    if [ "$1" = "tag" ]; then
                      exit 0
                    fi
                    if [ "$1" = "push" ]; then
                      printf 'pushed but no digest recorded\n'
                      exit 0
                    fi
                    if [ "$1" = "inspect" ]; then
                      exit 0
                    fi
                    echo "unexpected docker $*" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "missing-digest.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_missing_digest\tmissing-digest\ttb2-offline/missing-digest:20260425\tsha256:fake\tswe_dev\ttb2-offline/missing-digest:20260425\tfake\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/missing-digest:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_DOCKER_LOG"] = str(root / "docker.log")
            proc = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--plan",
                    str(plan),
                    "--execute",
                    "--push",
                    "--output-tsv",
                    str(out_tsv),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("missing p0 digest", proc.stderr)
            self.assertTrue(tar_path.is_file())
            result_text = out_tsv.read_text(encoding="utf-8")
            self.assertIn("push_digest_missing", result_text)
            self.assertNotIn("saved_pushed", result_text)
            docker_log = (root / "docker.log").read_text(encoding="utf-8")
            self.assertIn("push 100.97.118.137:8555/swe-data-harness/missing-digest:20260425", docker_log)


    def test_stage_cache_images_script_rejects_wrong_push_repository_digest(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
                    if [ "$1 $2" = "image inspect" ]; then
                      printf '[{"Id":"sha256:fake"}]\n'
                      exit 0
                    fi
                    if [ "$1" = "save" ]; then
                      out=""
                      while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                          out="$2"
                          shift 2
                          continue
                        fi
                        shift
                      done
                      printf 'fake docker tar bytes' > "$out"
                      exit 0
                    fi
                    if [ "$1" = "tag" ]; then
                      exit 0
                    fi
                    if [ "$1" = "push" ]; then
                      printf 'pushed wrong repository digest\n'
                      exit 0
                    fi
                    if [ "$1" = "inspect" ]; then
                      printf '100.97.118.137:8555/swe-data-harness/other-repo@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n'
                      exit 0
                    fi
                    echo "unexpected docker $*" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "wrong-digest-repo.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_wrong_digest_repo\twrong-digest-repo\ttb2-offline/wrong-digest-repo:20260425\tsha256:fake\tswe_dev\ttb2-offline/wrong-digest-repo:20260425\tfake\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/expected-repo:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_DOCKER_LOG"] = str(root / "docker.log")
            proc = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--plan",
                    str(plan),
                    "--execute",
                    "--push",
                    "--output-tsv",
                    str(out_tsv),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("p0 digest mismatch", proc.stderr)
            self.assertTrue(tar_path.is_file())
            result_text = out_tsv.read_text(encoding="utf-8")
            self.assertIn("push_digest_mismatch", result_text)
            self.assertIn("100.97.118.137:8555/swe-data-harness/other-repo@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", result_text)
            self.assertNotIn("saved_pushed", result_text)
            docker_log = (root / "docker.log").read_text(encoding="utf-8")
            self.assertIn("push 100.97.118.137:8555/swe-data-harness/expected-repo:20260425", docker_log)


    def test_stage_cache_images_script_times_out_hung_docker_save(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
                    if [ "$1 $2" = "image inspect" ]; then
                      printf '[{"Id":"sha256:fake"}]\n'
                      exit 0
                    fi
                    if [ "$1" = "save" ]; then
                      sleep 30
                      exit 0
                    fi
                    echo "unexpected docker $*" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "hung.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_hung\thung\ttb2-offline/hung:20260425\tsha256:fake\tswe_dev\ttb2-offline/hung:20260425\tfake\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/hung:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_DOCKER_LOG"] = str(root / "docker.log")
            proc = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--plan",
                    str(plan),
                    "--execute",
                    "--save-timeout-seconds",
                    "1",
                    "--output-tsv",
                    str(out_tsv),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("docker save timeout", proc.stderr)
            self.assertFalse(tar_path.exists())
            result_text = out_tsv.read_text(encoding="utf-8")
            self.assertIn("save_timeout", result_text)
            docker_log = (root / "docker.log").read_text(encoding="utf-8")
            self.assertIn("save -o", docker_log)

    def test_stage_cache_images_script_rejects_wrong_source_image_id(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
                    if [ "$1 $2" = "image inspect" ]; then
                      printf '[{"Id":"sha256:wrong-cache-id"}]\n'
                      exit 0
                    fi
                    if [ "$1" = "save" ]; then
                      echo "unexpected docker save" >&2
                      exit 9
                    fi
                    echo "unexpected docker $*" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "wrong.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_wrong\twrong\ttb2-offline/wrong:20260425\tsha256:expected-full-id\tswe_dev\ttb2-offline/wrong:20260425\tsha256:wrong-cache-id\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/wrong:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_DOCKER_LOG"] = str(root / "docker.log")
            proc = subprocess.run(
                ["bash", str(script), "--plan", str(plan), "--execute", "--output-tsv", str(out_tsv)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("image identity mismatch", proc.stderr)
            self.assertFalse(tar_path.exists())
            docker_log = (root / "docker.log").read_text(encoding="utf-8")
            self.assertIn("image inspect tb2-offline/wrong:20260425", docker_log)
            self.assertNotIn("save", docker_log)
            result_text = out_tsv.read_text(encoding="utf-8")
            self.assertIn("actual_image_id", result_text)
            self.assertIn("sha256:wrong-cache-id", result_text)
            self.assertIn("identity_mismatch", result_text)


    def test_stage_cache_images_script_rejects_wrong_source_host_label(self):
        script = ROOT / "scripts" / "stage_cache_images_from_plan.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fakebin = root / "bin"
            fakebin.mkdir()
            fake_docker = fakebin / "docker"
            fake_docker.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env bash
                    echo "docker should not be called" >&2
                    exit 9
                    """
                ).lstrip(),
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            plan = root / "plan.tsv"
            tar_path = root / "images" / "wrong-host.tar"
            plan.write_text(
                "id\tslug\tlocal_ref\tsource_image_id\tsource_host\tsource_ref\tsource_cache_image_id\tsource_size\tfallback_tar\tp0_tag\tmatch_status\n"
                f"tb2_wrong_host\twrong-host\ttb2-offline/wrong-host:20260425\tsha256:expected-full-id\tswe_dev\ttb2-offline/wrong-host:20260425\texpected\t1GB\t{tar_path}\t100.97.118.137:8555/swe-data-harness/wrong-host:20260425\tmatched\n",
                encoding="utf-8",
            )
            out_tsv = root / "result.tsv"
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            proc = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--plan",
                    str(plan),
                    "--execute",
                    "--source-host-label",
                    "swe_dev2",
                    "--output-tsv",
                    str(out_tsv),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("source host mismatch", proc.stderr)
            self.assertFalse(tar_path.exists())
            self.assertIn("source_host_mismatch", out_tsv.read_text(encoding="utf-8"))


    def test_lint_manifest_reports_required_rows_without_offline_transport(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "images.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: lint_probe
                    images:
                      - id: digest_ready
                        required: true
                        image_ref: 100.97.118.137:8555/swe-data-harness/example@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                      - id: tar_ready
                        required: true
                        fallback_tar: images/example.tar
                        fallback_tar_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
                      - id: required_missing_transport
                        required: true
                        local_ref: example/missing:latest
                      - id: optional_missing_transport
                        required: false
                        local_ref: example/optional:latest
                    """
                ).strip(),
                encoding="utf-8",
            )

            summary = module.lint_image_manifest(manifest, require_offline_transport=True)

        self.assertEqual(summary["counts"]["images"], 4)
        self.assertEqual(summary["counts"]["required_images"], 3)
        self.assertEqual(summary["counts"]["required_with_digest_ref"], 1)
        self.assertEqual(summary["counts"]["required_with_fallback_sha"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["images"][2]["lint_status"], "missing_offline_transport")
        self.assertEqual(summary["images"][3]["lint_status"], "optional_not_required")



    def test_example_mcp_atlas_manifest_lints_as_fail_closed(self):
        module = load_module()
        manifest = ROOT / "manifests" / "images" / "mcp_atlas.yaml"

        summary = module.lint_image_manifest(manifest, require_offline_transport=True)

        self.assertEqual(summary["bench_id"], "mcp_atlas")
        self.assertEqual(summary["counts"]["required_images"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["images"][0]["id"], "mcp_atlas_server_runtime_todo")
        self.assertEqual(summary["images"][0]["lint_status"], "missing_offline_transport")

    def test_example_programbench_manifest_lints_as_fail_closed(self):
        module = load_module()
        manifest = ROOT / "manifests" / "images" / "programbench.yaml"

        summary = module.lint_image_manifest(manifest, require_offline_transport=True)

        self.assertEqual(summary["bench_id"], "programbench")
        self.assertEqual(summary["counts"]["required_images"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["images"][0]["id"], "programbench_runtime_todo")
        self.assertEqual(summary["images"][0]["lint_status"], "missing_offline_transport")

    def test_example_tool_decathlon_manifest_lints_as_fail_closed(self):
        module = load_module()
        manifest = ROOT / "manifests" / "images" / "tool_decathlon.yaml"

        summary = module.lint_image_manifest(manifest, require_offline_transport=True)

        self.assertEqual(summary["bench_id"], "tool_decathlon")
        self.assertEqual(summary["counts"]["required_images"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["images"][0]["id"], "tool_decathlon_tool_server_runtime_todo")
        self.assertEqual(summary["images"][0]["lint_status"], "missing_offline_transport")

    def test_cli_lint_reports_missing_offline_transport(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "image.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: cli_lint_probe
                    images:
                      - id: missing_transport
                        required: true
                        local_ref: example/missing:latest
                    """
                ).strip(),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "lint",
                    "--image-manifest",
                    str(manifest),
                    "--asset-root",
                    str(root),
                    "--require-offline-transport",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 1, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)


    def test_lint_registry_filters_policy_and_aggregates_manifest_lint(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "ready.yaml").write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: ready_bench
                    images:
                      - id: ready_runtime
                        required: true
                        image_ref: 100.97.118.137:8555/swe-data-harness/ready@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                    """
                ).strip(),
                encoding="utf-8",
            )
            (image_dir / "audit.yaml").write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: audit_bench
                    images:
                      - id: audit_runtime
                        required: true
                        local_ref: tb2-offline/audit:20260425
                    """
                ).strip(),
                encoding="utf-8",
            )
            registry = root / "bench_registry.yaml"
            registry.write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.registry.v1
                    registry:
                      domain: 100.97.118.137:8555
                    image_manifests:
                      - id: ready
                        path: images/ready.yaml
                        policy: required_for_registry_health
                      - id: audit
                        path: images/audit.yaml
                        policy: audit_manifest_for_tb2_full_image_warmup
                    """
                ).strip(),
                encoding="utf-8",
            )

            summary = module.lint_registry_manifests(
                registry,
                asset_root=root,
                policies=["audit_manifest_for_tb2_full_image_warmup"],
                require_offline_transport=True,
            )

        self.assertEqual(summary["schema_version"], "agentic_bench.registry_lint.v1")
        self.assertEqual(summary["filters"]["policies"], ["audit_manifest_for_tb2_full_image_warmup"])
        self.assertEqual(summary["counts"]["selected_manifests"], 1)
        self.assertEqual(summary["counts"]["manifests"], 1)
        self.assertEqual(summary["counts"]["images"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["counts"]["manifests_with_issues"], 1)
        self.assertEqual(summary["manifests"][0]["id"], "audit")
        self.assertEqual(summary["manifests"][0]["policy"], "audit_manifest_for_tb2_full_image_warmup")
        self.assertEqual(summary["manifests"][0]["lint_status"], "missing_offline_transport")


    def test_cli_lint_registry_reports_selected_policy_transport_gaps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "selected.yaml").write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: selected_bench
                    images:
                      - id: missing_transport
                        required: true
                        local_ref: example/missing:latest
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
                      - id: selected
                        path: images/selected.yaml
                        policy: required_for_smoke
                    """
                ).strip(),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "lint-registry",
                    "--registry",
                    str(registry),
                    "--asset-root",
                    str(root),
                    "--policy",
                    "required_for_smoke",
                    "--require-offline-transport",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 1, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["counts"]["selected_manifests"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)


    def test_lint_manifest_can_verify_fallback_file_hashes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tar_path = root / "images" / "runtime.tar"
            tar_path.parent.mkdir(parents=True)
            tar_path.write_bytes(b"runtime bytes")
            digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
            manifest = root / "image.yaml"
            manifest.write_text(
                textwrap.dedent(
                    f"""
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: verify_fallback_probe
                    images:
                      - id: valid_fallback
                        required: true
                        fallback_tar: images/runtime.tar
                        fallback_tar_sha256: {digest}
                      - id: missing_fallback
                        required: true
                        fallback_tar: images/missing.tar
                        fallback_tar_sha256: {digest}
                    """
                ).strip(),
                encoding="utf-8",
            )

            summary = module.lint_image_manifest(
                manifest,
                asset_root=root,
                require_offline_transport=True,
                verify_fallback_files=True,
            )

        self.assertEqual(summary["counts"]["fallback_tar_verified"], 1)
        self.assertEqual(summary["counts"]["fallback_tar_missing"], 1)
        self.assertEqual(summary["counts"]["fallback_tar_mismatch"], 0)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["images"][0]["lint_status"], "ok")
        self.assertEqual(summary["images"][1]["lint_status"], "fallback_tar_missing")


    def test_cli_lint_registry_can_verify_fallback_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "selected.yaml").write_text(
                textwrap.dedent(
                    """
                    schema_version: agentic_bench.image_manifest.v1
                    bench_id: selected_bench
                    images:
                      - id: missing_tar_but_sha
                        required: true
                        fallback_tar: images/missing.tar
                        fallback_tar_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
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
                      - id: selected
                        path: images/selected.yaml
                        policy: required_for_smoke
                    """
                ).strip(),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "lint-registry",
                    "--registry",
                    str(registry),
                    "--asset-root",
                    str(root),
                    "--policy",
                    "required_for_smoke",
                    "--require-offline-transport",
                    "--verify-fallback-files",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 1, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["counts"]["fallback_tar_missing"], 1)
        self.assertEqual(summary["counts"]["required_without_offline_transport"], 1)
        self.assertEqual(summary["manifests"][0]["lint_status"], "fallback_tar_missing")

    def test_example_registry_includes_nl2repo_fail_closed_manifest(self):
        module = load_module()
        registry = ROOT / "manifests" / "bench_registry.yaml"

        validation = module.validate_registry(registry, asset_root=ROOT)
        manifests_by_id = {manifest["id"]: manifest for manifest in validation["manifests"]}

        self.assertIn("nl2repo", manifests_by_id)
        nl2repo = manifests_by_id["nl2repo"]
        self.assertEqual(nl2repo["status"], "ok")
        self.assertEqual(nl2repo["bench_id"], "nl2repo")
        self.assertEqual(len(nl2repo["images"]), 1)
        self.assertEqual(nl2repo["images"][0]["id"], "nl2repo_images_todo")
        self.assertFalse(nl2repo["images"][0]["required"])
        self.assertEqual(nl2repo["images"][0]["image_refs"], [])
        self.assertEqual(nl2repo["images"][0]["fallback_tars"], [])

        lint = module.lint_registry_manifests(
            registry,
            asset_root=ROOT,
            manifest_ids=["nl2repo"],
            require_offline_transport=True,
        )
        self.assertEqual(lint["counts"]["selected_manifests"], 1)
        self.assertEqual(lint["counts"]["required_images"], 0)
        self.assertEqual(lint["counts"]["optional_images"], 1)
        self.assertEqual(lint["counts"]["required_without_offline_transport"], 0)
        self.assertEqual(lint["manifests"][0]["lint_status"], "ok")
        self.assertEqual(lint["manifests"][0]["images"][0]["lint_status"], "optional_not_required")


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
