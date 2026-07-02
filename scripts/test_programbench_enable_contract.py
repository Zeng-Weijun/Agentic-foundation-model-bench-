#!/usr/bin/env python3
"""Focused contract tests for ProgramBench offline enablement skeleton."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_programbench_tests.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_programbench_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_programbench_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "programbench.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"
FIXTURE_TASK = "testorg__calculator.abc1234"


class ProgramBenchEnableContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_hf_tests_and_official_200_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "shared_bench"
            proc = subprocess.run(
                ["bash", str(SNAPSHOT_SCRIPT), "--dry-run", "--output-root", str(out_root)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["bench_id"], "programbench")
        self.assertEqual(payload["source_repo"], "https://github.com/facebookresearch/ProgramBench")
        self.assertEqual(payload["source_commit"], "31952f0c261db73f1f864542e8aa1cb3d010c817")
        self.assertEqual(payload["hf_dataset"], "programbench/ProgramBench-Tests")
        self.assertEqual(payload["hf_revision"], "de0ddfb637590c7ecb54fa0b5301f6dc7dfbcee5")
        self.assertEqual(payload["expected_task_count"], 200)
        self.assertEqual(payload["excluded_fixture"], FIXTURE_TASK)
        self.assertEqual(payload["expected_test_archive_count"], 1832)
        self.assertGreater(len(proc.stdout.splitlines()), 1)
        self.assertTrue(payload["dataset_dir"].endswith("ProgramBench-Tests/de0ddfb637590c7ecb54fa0b5301f6dc7dfbcee5"))
        self.assertIn("SHA256SUMS", payload["sha256_manifest"])


    def test_snapshot_materializes_local_fixture_and_writes_hash_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file_root = root / "hf_files"
            files = {
                ".gitattributes": b"*.tar.gz filter=lfs\n",
                "task-one.111/LICENSE": b"license-one\n",
                "task-one.111/tests/a.tar.gz": b"aaa",
                "task-one.111/tests/b.tar.gz": b"bbbb",
                "task-two.222/ATTRIBUTION.md": b"attr-two\n",
                "task-two.222/tests/c.tar.gz": b"ccccc",
            }
            for rel, data in files.items():
                target = file_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            metadata = {
                "sha": "fixture-revision",
                "siblings": [
                    {"rfilename": rel, "size": len(data)}
                    for rel, data in sorted(files.items())
                ],
            }
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps(metadata))
            out_root = root / "out"
            env = os.environ.copy()
            env.update(
                {
                    "PROGRAMBENCH_EXPECTED_TASK_COUNT": "2",
                    "PROGRAMBENCH_EXPECTED_TEST_ARCHIVE_COUNT": "3",
                    "PROGRAMBENCH_HF_REVISION": "fixture-revision",
                }
            )
            proc = subprocess.run(
                [
                    "bash",
                    str(SNAPSHOT_SCRIPT),
                    "--output-root",
                    str(out_root),
                    "--metadata-json",
                    str(metadata_path),
                    "--download-base-url",
                    file_root.as_uri() + "/",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "snapshot_complete")
            self.assertEqual(payload["task_count"], 2)
            self.assertEqual(payload["test_archive_count"], 3)
            dataset_dir = Path(payload["dataset_dir"])
            self.assertTrue((dataset_dir / "task-one.111" / "tests" / "a.tar.gz").is_file())
            self.assertTrue((dataset_dir / "SHA256SUMS").is_file())
            sha_rows = (dataset_dir / "SHA256SUMS").read_text().splitlines()
            self.assertEqual(len(sha_rows), len(files))
            task_manifest = json.loads((dataset_dir / "programbench_full200_tasks.json").read_text())
            self.assertEqual(task_manifest["task_count"], 2)
            self.assertEqual(task_manifest["test_archive_count"], 3)
            self.assertEqual([row["task_id"] for row in task_manifest["tasks"]], ["task-one.111", "task-two.222"])

    def test_snapshot_refuses_when_metadata_size_exceeds_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps({
                "sha": "fixture-revision",
                "siblings": [{"rfilename": "task/tests/a.tar.gz", "size": 12345}],
            }))
            env = os.environ.copy()
            env["PROGRAMBENCH_HF_REVISION"] = "fixture-revision"
            proc = subprocess.run(
                [
                    "bash",
                    str(SNAPSHOT_SCRIPT),
                    "--output-root",
                    str(root / "out"),
                    "--metadata-json",
                    str(metadata_path),
                    "--download-base-url",
                    (root / "files").as_uri() + "/",
                    "--max-bytes",
                    "100",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("exceeds max bytes", proc.stderr)

    def test_image_manifest_is_full200_fail_closed_skeleton(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "programbench")
        self.assertEqual(data["status"], "blocked_until_programbench_assets_materialized")
        self.assertEqual(data["expected_task_count"], 200)
        self.assertEqual(data["excluded_fixture"], FIXTURE_TASK)
        self.assertEqual(data["image_system"], "ProgramBench cleanroom task images")
        self.assertTrue(data["hidden_tests_required"])
        images = data["images"]
        self.assertEqual(len(images), 200)
        task_ids = {row["task_id"] for row in images}
        self.assertEqual(len(task_ids), 200)
        self.assertNotIn(FIXTURE_TASK, task_ids)
        sample = next(row for row in images if row["task_id"] == "abishekvashok__cmatrix.5c082c6")
        self.assertEqual(
            sample["source_image"],
            "docker.io/programbench/abishekvashok_1776_cmatrix.5c082c6:task_cleanroom_v6",
        )
        self.assertEqual(sample["p0_target_repo"], "100.97.118.137:8555/swe-data-harness/programbench/abishekvashok_1776_cmatrix.5c082c6")
        self.assertTrue(sample["fallback_tar"].endswith("abishekvashok_1776_cmatrix.5c082c6.task_cleanroom_v6.tar"))
        for row in images:
            self.assertTrue(row["required"])
            self.assertEqual(row["image_transport"], "missing")
            self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
            self.assertNotIn("p0_digest_ref", row)
            self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_includes_programbench_fail_closed_row(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("programbench", manifests)
        self.assertEqual(manifests["programbench"]["path"], "images/programbench.yaml")
        self.assertIn("blocked", manifests["programbench"]["status"])
        self.assertEqual(manifests["programbench"]["policy"], "required_when_programbench_enabled")

    def test_runner_dry_run_exposes_mini_extra_hidden_eval_relay_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            blob_dir = Path(td) / "ProgramBench-Tests" / "de0ddfb637590c7ecb54fa0b5301f6dc7dfbcee5"
            blob_dir.mkdir(parents=True)
            source_root = Path(td) / "ProgramBench"
            source_root.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "PROGRAMBENCH_SOURCE_ROOT": str(source_root),
                    "PROGRAMBENCH_BLOB_DIR": str(blob_dir),
                    "PROGRAMBENCH_OUTPUT_DIR": str(Path(td) / "run"),
                    "PROGRAMBENCH_MODEL": "gpt-5.4-mini",
                    "PROGRAMBENCH_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                    "PROGRAMBENCH_WORKERS": "2",
                    "DOCKER_HOST": "unix:///tmp/rl-vfs/run/docker-shim.sock",
                }
            )
            proc = subprocess.run(
                [
                    "bash",
                    str(RUNNER_SCRIPT),
                    "--dry-run",
                    "--mode",
                    "smoke",
                    "--filter",
                    "abishekvashok__cmatrix.*",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["bench_id"], "programbench")
        self.assertEqual(payload["mode"], "smoke")
        self.assertEqual(payload["agent_scaffold"], "mini-swe-agent")
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["openai_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["workers"], 2)
        self.assertEqual(payload["filter"], "abishekvashok__cmatrix.*")
        self.assertIn("mini-extra", " ".join(payload["planned_infer_command"]))
        self.assertIn("programbench", " ".join(payload["planned_eval_command"]))
        self.assertTrue(payload["hidden_behavioral_tests_required"])
        self.assertIn("PROGRAMBENCH_BLOB_DIR", payload["eval_environment"])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(payload))

    def test_runner_non_dry_run_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env.update(
                {
                    "PROGRAMBENCH_SOURCE_ROOT": str(Path(td) / "ProgramBench"),
                    "PROGRAMBENCH_BLOB_DIR": str(Path(td) / "ProgramBench-Tests"),
                    "PROGRAMBENCH_OUTPUT_DIR": str(Path(td) / "run"),
                    "PROGRAMBENCH_MODEL": "gpt-5.4-mini",
                    "PROGRAMBENCH_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                    "DOCKER_HOST": "unix:///tmp/rl-vfs/run/docker-shim.sock",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--mode", "smoke", "--filter", "abishekvashok__cmatrix.*"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("fail-closed", proc.stderr)

    def test_strict_parser_counts_resolved_and_infra_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            agent_dir = root / "agent_output"
            eval_dir = root / "eval"
            ok_agent = agent_dir / "abishekvashok__cmatrix.5c082c6"
            ok_agent.mkdir(parents=True)
            (ok_agent / "submission.tar.gz").write_bytes(b"submission")
            (ok_agent / "abishekvashok__cmatrix.5c082c6.traj.json").write_text("{}\n")
            ok_eval = eval_dir / "abishekvashok__cmatrix.5c082c6"
            ok_eval.mkdir(parents=True)
            (ok_eval / "abishekvashok__cmatrix.5c082c6.eval.json").write_text(json.dumps({
                "error_code": None,
                "error_details": None,
                "test_branch_errors": {},
                "warnings": [],
                "test_results": [
                    {"name": "test_cli_help", "branch": "main", "status": "passed"},
                    {"name": "test_delta", "branch": "main", "status": "passed"},
                ],
            }))
            bad_agent = agent_dir / "agourlay__zip-password-finder.704700d"
            bad_agent.mkdir(parents=True)
            (bad_agent / "submission.tar.gz").write_bytes(b"submission")
            bad_eval = eval_dir / "agourlay__zip-password-finder.704700d"
            bad_eval.mkdir(parents=True)
            (bad_eval / "agourlay__zip-password-finder.704700d.eval.json").write_text(json.dumps({
                "error_code": "docker_error",
                "error_details": "task image transport missing",
                "test_branch_errors": {"main": "container failed"},
                "warnings": ["missing results.xml"],
                "test_results": [
                    {"name": "test_zip", "branch": "main", "status": "system_error"},
                ],
            }))
            proc = subprocess.run(
                [
                    "python3",
                    str(PARSER_SCRIPT),
                    "--agent-dir",
                    str(agent_dir),
                    "--eval-dir",
                    str(eval_dir),
                    "--expected-tasks",
                    "2",
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["bench_id"], "programbench")
        self.assertEqual(summary["expected_tasks"], 2)
        self.assertEqual(summary["eval_json_count"], 2)
        self.assertEqual(summary["attempted_instances"], 2)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["infra_failure_count"], 1)
        failures = {row["instance_id"]: row for row in summary["failures"]}
        self.assertIn("agourlay__zip-password-finder.704700d", failures)
        self.assertIn("system_error", failures["agourlay__zip-password-finder.704700d"]["failure_classes"])
        self.assertIn("missing_agent_trace", failures["agourlay__zip-password-finder.704700d"]["failure_classes"])


if __name__ == "__main__":
    unittest.main()
