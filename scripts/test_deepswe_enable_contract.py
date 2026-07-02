#!/usr/bin/env python3
"""Focused contract tests for DeepSWE offline enablement skeleton."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_deepswe_dataset.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_deepswe_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_deepswe_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "deepswe.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"


class DeepSWEEnableContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_official_source_and_layout(self) -> None:
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
        self.assertEqual(payload["bench_id"], "deepswe")
        self.assertEqual(payload["source_repo"], "https://github.com/datacurve-ai/deep-swe")
        self.assertEqual(payload["source_commit"], "578129c")
        self.assertEqual(payload["data_version"], "v1.1")
        self.assertEqual(payload["expected_task_count"], 113)
        self.assertTrue(payload["dataset_dir"].endswith("shared_bench/deepswe-v1.1"))
        self.assertIn("SHA256SUMS", payload["sha256_manifest"])
        self.assertEqual(
            payload["language_counts"],
            {"TypeScript": 35, "Go": 34, "Python": 34, "Rust": 5, "JavaScript": 5},
        )

    def test_image_manifest_is_113_task_fail_closed_skeleton(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "deepswe")
        self.assertEqual(data["status"], "blocked_until_r2e_pier_transport_materialized")
        self.assertEqual(data["expected_task_count"], 113)
        self.assertEqual(data["image_system"], "R2E/Pier task environment images")
        images = data["images"]
        self.assertEqual(len(images), 113)
        task_ids = {row["task_id"] for row in images}
        self.assertEqual(len(task_ids), 113)
        for row in images:
            self.assertTrue(row["required"])
            self.assertEqual(row["image_transport"], "missing")
            self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
            self.assertTrue(row["source_image"].startswith("public.ecr.aws/d3j8x8q7/swe-bench-202605:"))
            self.assertNotIn("p0_digest_ref", row)
            self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_keeps_deepswe_fail_closed_required_when_enabled(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("deepswe", manifests)
        self.assertEqual(manifests["deepswe"]["path"], "images/deepswe.yaml")
        self.assertIn("blocked", manifests["deepswe"]["status"])
        self.assertEqual(manifests["deepswe"]["policy"], "required_when_deepswe_enabled")

    def test_runner_dry_run_exposes_mini_swe_agent_relay_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "deepswe-v1.1"
            (dataset / "tasks").mkdir(parents=True)
            env = os.environ.copy()
            env.update(
                {
                    "DEEPSWE_DATASET_DIR": str(dataset),
                    "DEEPSWE_OUTPUT_DIR": str(Path(td) / "run"),
                    "DEEPSWE_MODEL": "gpt-5.4-mini",
                    "DEEPSWE_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                    "DEEPSWE_MAX_WORKERS": "4",
                    "DEEPSWE_TASK_ID": "ink-grid-box-layout",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--task-id", "ink-grid-box-layout"],
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
        self.assertEqual(payload["agent"], "mini-swe-agent")
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["openai_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["max_workers"], 4)
        self.assertEqual(payload["task_id"], "ink-grid-box-layout")
        self.assertIn("pier", " ".join(payload["planned_command"]))
        self.assertIn("mini-swe-agent", " ".join(payload["planned_command"]))


    def test_runner_dry_run_is_testable_before_dataset_snapshot_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing_dataset = Path(td) / "missing-deepswe-v1.1"
            env = os.environ.copy()
            env.update(
                {
                    "DEEPSWE_DATASET_DIR": str(missing_dataset),
                    "DEEPSWE_OUTPUT_DIR": str(Path(td) / "run"),
                    "DEEPSWE_MODEL": "gpt-5.4-mini",
                    "DEEPSWE_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--task-id", "ink-grid-box-layout"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["dataset_tasks_exists"])
        self.assertIn("deepswe dataset snapshot sha256 manifest exists", payload["fail_closed_until"])

    def test_runner_non_dry_run_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "deepswe-v1.1"
            (dataset / "tasks").mkdir(parents=True)
            env = os.environ.copy()
            env.update(
                {
                    "DEEPSWE_DATASET_DIR": str(dataset),
                    "DEEPSWE_OUTPUT_DIR": str(Path(td) / "run"),
                    "DEEPSWE_MODEL": "gpt-5.4-mini",
                    "DEEPSWE_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--mode", "smoke", "--task-id", "ink-grid-box-layout"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("fail-closed", proc.stderr)

    def test_parser_behavior_verifier_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            ok = run_dir / "ink-grid-box-layout"
            ok.mkdir()
            (ok / "result.json").write_text(json.dumps({
                "task_id": "ink-grid-box-layout",
                "agent": "mini-swe-agent",
                "model": "gpt-5.4-mini",
                "agent_exit_status": "submitted",
                "verifier": {"rc": 0, "reward": 1.0, "resolved": True},
                "patch_path": str(ok / "patch.diff"),
                "trajectory_path": str(ok / "trajectory.jsonl"),
                "transport_status": "p0_proven",
            }))
            (ok / "patch.diff").write_text("diff --git a/a b/a\n")
            (ok / "trajectory.jsonl").write_text("{}\n")

            bad = run_dir / "missing-trajectory"
            bad.mkdir()
            (bad / "result.json").write_text(json.dumps({
                "task_id": "missing-trajectory",
                "agent": "mini-swe-agent",
                "model": "gpt-5.4-mini",
                "agent_exit_status": "submitted",
                "verifier": {"rc": 1, "reward": 0.0, "resolved": False},
                "transport_status": "fallback_verified",
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
        self.assertEqual(summary["bench_id"], "deepswe")
        self.assertEqual(summary["expected_tasks"], 2)
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertIn("missing_patch_path", summary["failures"][0]["reasons"])
