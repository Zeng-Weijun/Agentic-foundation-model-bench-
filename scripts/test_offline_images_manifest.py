import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_offline_images_manifest.py"


class OfflineImagesManifestTest(unittest.TestCase):
    def test_check_mode_uses_rootless_docker_host_and_does_not_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fakebin = tmp / "bin"
            fakebin.mkdir()
            command_log = tmp / "docker.log"
            docker = fakebin / "docker"
            docker.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    echo "$DOCKER_HOST|$*" >> {command_log}
                    if [[ "$1 $2" == "image ls" ]]; then
                      echo "repo/present:latest"
                      exit 0
                    fi
                    if [[ "$1" == "load" ]]; then
                      echo "load must not run in check mode" >&2
                      exit 42
                    fi
                    exit 99
                    """
                ),
                encoding="utf-8",
            )
            docker.chmod(0o755)
            asset_root = tmp / "assets"
            (asset_root / "images").mkdir(parents=True)
            (asset_root / "images" / "missing.tar").write_text("tar", encoding="utf-8")
            manifest = tmp / "offline.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """\
                    schema_version: agentic_bench.offline_images.v1
                    images:
                      - id: already_present
                        required_images:
                          - repo/present:latest
                        source_path:
                          - images/present.tar
                      - id: needs_load
                        required_images:
                          - repo/missing:latest
                        source_path:
                          - images/missing.tar
                    """
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
            env.pop("DOCKER_HOST", None)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--manifest",
                    str(manifest),
                    "--asset-root",
                    str(asset_root),
                    "--check",
                    "--json",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            log_text = command_log.read_text(encoding="utf-8")

        self.assertEqual(proc.returncode, 1, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["docker_host"], "unix:///tmp/rl/run/docker.sock")
        self.assertEqual(summary["counts"]["present"], 1)
        self.assertEqual(summary["counts"]["missing"], 1)
        self.assertEqual(summary["counts"]["loaded"], 0)
        self.assertEqual(summary["counts"]["skipped"], 1)
        self.assertEqual(summary["entries"][1]["status"], "missing")
        self.assertIn("repo/missing:latest", summary["entries"][1]["missing_tags"])
        self.assertIn("unix:///tmp/rl/run/docker.sock|image ls", log_text)
        self.assertNotIn("|load ", log_text)

    def test_load_mode_skips_present_images_and_loads_missing_tar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fakebin = tmp / "bin"
            fakebin.mkdir()
            command_log = tmp / "docker.log"
            docker = fakebin / "docker"
            docker.write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    echo "$DOCKER_HOST|$*" >> {command_log}
                    if [[ "$1 $2" == "image ls" ]]; then
                      echo "repo/present:latest"
                      exit 0
                    fi
                    if [[ "$1" == "load" ]]; then
                      test "$2" = "-i"
                      test -f "$3"
                      echo "Loaded image: repo/missing:latest"
                      exit 0
                    fi
                    exit 99
                    """
                ),
                encoding="utf-8",
            )
            docker.chmod(0o755)
            asset_root = tmp / "assets"
            (asset_root / "images").mkdir(parents=True)
            missing_tar = asset_root / "images" / "missing.tar"
            missing_tar.write_text("tar", encoding="utf-8")
            manifest = tmp / "offline.yaml"
            manifest.write_text(
                textwrap.dedent(
                    """\
                    schema_version: agentic_bench.offline_images.v1
                    images:
                      - id: already_present
                        required_images:
                          - repo/present:latest
                        source_path:
                          - images/present.tar
                      - id: needs_load
                        required_images:
                          - repo/missing:latest
                        source_path:
                          - images/missing.tar
                    """
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
            env["DOCKER_HOST"] = "unix:///custom/rootless.sock"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--manifest",
                    str(manifest),
                    "--asset-root",
                    str(asset_root),
                    "--load",
                    "--json",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            log_lines = command_log.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["docker_host"], "unix:///custom/rootless.sock")
        self.assertEqual(summary["counts"]["present"], 1)
        self.assertEqual(summary["counts"]["loaded"], 1)
        self.assertEqual(summary["counts"]["missing"], 0)
        self.assertEqual(summary["counts"]["skipped"], 1)
        self.assertEqual(summary["entries"][1]["loaded_tars"], [str(missing_tar)])
        self.assertEqual(log_lines.count(f"unix:///custom/rootless.sock|load -i {missing_tar}"), 1)


if __name__ == "__main__":
    unittest.main()
