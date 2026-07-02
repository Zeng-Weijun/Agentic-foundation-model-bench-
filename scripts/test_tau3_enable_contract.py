#!/usr/bin/env python3
"""Focused contract tests for the tau3 offline enablement skeleton."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_tau3_dataset.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_tau3_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_tau3_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "tau3.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"


class Tau3EnableContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_pinned_source_and_target_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "shared_bench"
            proc = subprocess.run(
                [
                    "bash",
                    str(SNAPSHOT_SCRIPT),
                    "--dry-run",
                    "--output-root",
                    str(out_root),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["source_repo"], "https://github.com/sierra-research/tau2-bench.git")
        self.assertEqual(payload["source_ref"], "v1.0.0")
        self.assertEqual(payload["source_commit"], "17e07b1da2bbc0cadfddeea36412686e0604127b")
        self.assertEqual(payload["expected_task_count"], 375)
        self.assertEqual(payload["domain_counts"], {"airline": 50, "retail": 114, "telecom": 114, "banking_knowledge": 97})
        self.assertTrue(payload["dataset_dir"].endswith("shared_bench/tau3-v1.0.0"))
        self.assertIn("SHA256SUMS", payload["sha256_manifest"])

    def test_image_manifest_is_fail_closed_skeleton(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "tau3_bench")
        self.assertEqual(data["status"], "blocked_until_full_transport_materialized")
        self.assertEqual(data["expected_task_count"], 375)
        image_ids = {row["id"] for row in data["images"]}
        self.assertEqual(image_ids, {"tau3_full_main_runtime_pending", "tau3_full_mcp_runtime_pending"})
        for row in data["images"]:
            self.assertTrue(row["required"])
            self.assertEqual(row["image_transport"], "missing")
            self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
            self.assertNotIn("p0_digest_ref", row)
            self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_includes_tau3_fail_closed_row(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("tau3_bench", manifests)
        self.assertEqual(manifests["tau3_bench"]["path"], "images/tau3.yaml")
        self.assertIn("blocked", manifests["tau3_bench"]["status"])
        self.assertEqual(manifests["tau3_bench"]["policy"], "required_when_tau3_enabled")

    def test_runner_dry_run_exposes_dual_relay_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "tau3-v1.0.0"
            dataset.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "TAU3_DATASET_DIR": str(dataset),
                    "TAU3_OUTPUT_DIR": str(Path(td) / "run"),
                    "TAU3_AGENT_MODEL": "openai/test-agent",
                    "TAU3_USER_MODEL": "openai/test-user",
                    "TAU3_AGENT_BASE_URL": "http://100.96.1.101:18540/v1",
                    "TAU3_USER_BASE_URL": "http://100.96.1.101:18540/v1",
                    "TAU3_CONCURRENCY": "3",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--task-limit", "2"],
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
        self.assertEqual(payload["task_limit"], 2)
        self.assertEqual(payload["concurrency"], 3)
        self.assertEqual(payload["agent_model"], "openai/test-agent")
        self.assertEqual(payload["user_simulator_model"], "openai/test-user")
        self.assertEqual(payload["agent_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["user_simulator_base_url"], "http://100.96.1.101:18540/v1")
        self.assertIn("harbor", " ".join(payload["planned_command"]))

    def test_parser_summarizes_rewards_and_fails_on_missing_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            task_dir = run_dir / "tau3-airline-0"
            task_dir.mkdir()
            (task_dir / "result.json").write_text(json.dumps({
                "task_id": "tau3-airline-0",
                "verifier_result": {
                    "rewards": {"reward": 1.0},
                    "reward_info": {"DB_STATE": "ok"},
                },
                "agent": {"model": "oracle", "termination_reason": "agent_stop"},
                "runtime_state": {"messages": [{"role": "user", "content": "hi"}], "step_count": 3, "num_errors": 0},
            }))
            bad_dir = run_dir / "tau3-retail-0"
            bad_dir.mkdir()
            (bad_dir / "result.json").write_text(json.dumps({
                "task_id": "tau3-retail-0",
                "verifier_result": {"rewards": {"reward": 0.0}},
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
        self.assertEqual(summary["bench_id"], "tau3_bench")
        self.assertEqual(summary["expected_tasks"], 2)
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["passed_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertIn("missing_reward_info", summary["failures"][0]["reasons"])
        self.assertIn("missing_runtime_state", summary["failures"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
