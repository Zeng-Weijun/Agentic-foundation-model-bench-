#!/usr/bin/env python3
"""Focused contract tests for NL2Repo offline enablement skeleton."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_nl2repo_dataset.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_nl2repo_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_nl2repo_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "nl2repo.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"


class NL2RepoEnableContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_upstream_envcommons_and_layout(self) -> None:
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
        self.assertEqual(payload["bench_id"], "nl2repo")
        self.assertEqual(payload["upstream_repo"], "https://github.com/multimodal-art-projection/NL2RepoBench.git")
        self.assertEqual(payload["upstream_commit"], "781a1da1ee41fb8edb0bed22f586d69111610edf")
        self.assertEqual(payload["envcommons_repo"], "https://github.com/EnvCommons/NL2RepoBench.git")
        self.assertEqual(payload["envcommons_commit"], "61d26cc0abd084ece8f5d805dcbd3f806a291f15")
        self.assertEqual(payload["task_count_upstream"], 104)
        self.assertEqual(payload["task_count_envcommons_executable"], 103)
        self.assertEqual(payload["declared_test_count"], 25640)
        self.assertEqual(payload["task_list_sha256"], "88d33cf19a9e01ecbe5acee306cdeda7b148e11c821e1bc46f45d07392af197f")
        self.assertEqual(len(payload["categories"]), 9)
        self.assertTrue(payload["dataset_dir"].endswith("shared_bench/nl2repo-20260702"))
        self.assertIn("SHA256SUMS", payload["sha256_manifest"])
        self.assertIn("task_list", payload["layout"])
        self.assertIn("task_manifest", payload["layout"])
        self.assertNotIn("generated_tasks_json", payload["layout"])

    def test_image_manifest_is_108_image_fail_closed_skeleton(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "nl2repo")
        self.assertEqual(data["status"], "blocked_until_openhands_task_transport_materialized")
        self.assertEqual(data["expected_task_count_upstream"], 104)
        self.assertEqual(data["expected_image_count"], 108)
        self.assertEqual(data["image_system"], "EnvCommons task images plus OpenHands app/runtime images")
        self.assertTrue(data["wheelhouse_required"])
        images = data["images"]
        self.assertEqual(len(images), 108)
        roles = {row["role"] for row in images}
        self.assertEqual(roles, {"task_environment", "openhands_app", "openhands_runtime"})
        task_rows = [row for row in images if row["role"] == "task_environment"]
        self.assertEqual(len(task_rows), 104)
        runtime_rows = [row for row in images if row["role"] in {"openhands_app", "openhands_runtime"}]
        self.assertEqual(len(runtime_rows), 4)
        for row in images:
            self.assertTrue(row["required"])
            self.assertEqual(row["image_transport"], "missing")
            self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
            self.assertNotIn("p0_digest_ref", row)
            self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_includes_nl2repo_fail_closed_row(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("nl2repo", manifests)
        self.assertEqual(manifests["nl2repo"]["path"], "images/nl2repo.yaml")
        self.assertIn("blocked", manifests["nl2repo"]["status"])
        self.assertEqual(manifests["nl2repo"]["policy"], "required_when_nl2repo_enabled")

    def test_runner_dry_run_exposes_openhands_relay_wheelhouse_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "nl2repo-20260702"
            dataset.mkdir()
            wheelhouse = Path(td) / "wheelhouse"
            wheelhouse.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "NL2REPO_DATASET_DIR": str(dataset),
                    "NL2REPO_WHEELHOUSE_DIR": str(wheelhouse),
                    "NL2REPO_OUTPUT_DIR": str(Path(td) / "run"),
                    "NL2REPO_MODEL": "gpt-5.4-mini",
                    "NL2REPO_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                    "NL2REPO_MAX_WORKERS": "2",
                    "NL2REPO_TASK_ID": "aiofiles",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--task-id", "aiofiles"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["mode"], "smoke")
        self.assertEqual(payload["scaffold"], "openhands-headless")
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["openai_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["max_workers"], 2)
        self.assertEqual(payload["task_id"], "aiofiles")
        self.assertTrue(payload["wheelhouse_required"])
        self.assertIn("openhands", " ".join(payload["planned_command"]).lower())

    def test_runner_non_dry_run_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "nl2repo-20260702"
            dataset.mkdir()
            wheelhouse = Path(td) / "wheelhouse"
            wheelhouse.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "NL2REPO_DATASET_DIR": str(dataset),
                    "NL2REPO_WHEELHOUSE_DIR": str(wheelhouse),
                    "NL2REPO_OUTPUT_DIR": str(Path(td) / "run"),
                    "NL2REPO_MODEL": "gpt-5.4-mini",
                    "NL2REPO_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--mode", "smoke", "--task-id", "aiofiles"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("fail-closed", proc.stderr)

    def test_strict_parser_uses_pytest_reward_and_submit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            ok = run_dir / "aiofiles"
            ok.mkdir()
            (ok / "workspace.tar.zst").write_text("placeholder")
            (ok / "trajectory.jsonl").write_text("{}\n")
            (ok / "result.json").write_text(json.dumps({
                "task_id": "aiofiles",
                "transport_status": "p0_proven",
                "wheelhouse_status": "verified",
                "agent_status": "submitted",
                "submit_called": True,
                "test_commands_total": 2,
                "test_commands_completed": 2,
                "passed_tests": 10,
                "failed_tests": 0,
                "error_tests": 0,
                "total_tests": 10,
                "reward": 1.0,
                "patch_or_workspace_archive": str(ok / "workspace.tar.zst"),
                "trajectory_path": str(ok / "trajectory.jsonl"),
            }))
            bad = run_dir / "broken"
            bad.mkdir()
            (bad / "result.json").write_text(json.dumps({
                "task_id": "broken",
                "transport_status": "missing",
                "wheelhouse_status": "missing",
                "agent_status": "error",
                "submit_called": False,
                "test_commands_total": 2,
                "test_commands_completed": 1,
                "passed_tests": 3,
                "failed_tests": 1,
                "error_tests": 1,
                "total_tests": 10,
                "reward": 0.3,
            }))
            proc = subprocess.run(
                ["python3", str(PARSER_SCRIPT), "--run-dir", str(run_dir), "--expected-tasks", "2", "--json"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["bench_id"], "nl2repo")
        self.assertEqual(summary["expected_tasks"], 2)
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertIn("image_transport_unproven", summary["failures"][0]["failure_classes"])
        self.assertIn("wheelhouse_missing", summary["failures"][0]["failure_classes"])
