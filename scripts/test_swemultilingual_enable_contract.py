#!/usr/bin/env python3
"""Focused contract tests for SWE-bench Multilingual offline enablement."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_swebench_multilingual_dataset.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_swebench_multilingual_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_swebench_multilingual_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "swemultilingual.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"


class SWEMultilingualEnableContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_official_dataset_and_layout(self) -> None:
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
        self.assertEqual(payload["bench_id"], "swebench_multilingual")
        self.assertEqual(payload["dataset_id"], "SWE-bench/SWE-bench_Multilingual")
        self.assertEqual(payload["hf_sha"], "2b7aced941b4873e9cad3e76abbae93f481d1beb")
        self.assertEqual(payload["split"], "test")
        self.assertEqual(payload["expected_task_count"], 300)
        self.assertEqual(payload["repo_count"], 42)
        self.assertEqual(len(payload["languages"]), 9)
        self.assertTrue(payload["dataset_dir"].endswith("shared_bench/swebench-multilingual-2025-08-26"))
        self.assertIn("SHA256SUMS", payload["sha256_manifest"])


    def test_snapshot_non_dry_run_writes_row_count_from_parquet_footer(self) -> None:
        def varint(value: int) -> bytes:
            out = bytearray()
            while True:
                b = value & 0x7F
                value >>= 7
                if value:
                    out.append(b | 0x80)
                else:
                    out.append(b)
                    return bytes(out)

        def zigzag(value: int) -> int:
            return (value << 1) ^ (value >> 63)

        # Minimal TCompactProtocol FileMetaData: version=1, num_rows=300.
        metadata = bytes([0x15]) + varint(zigzag(1)) + bytes([0x26]) + varint(zigzag(300)) + bytes([0x00])
        parquet_bytes = b"PAR1" + metadata + len(metadata).to_bytes(4, "little") + b"PAR1"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "shared_bench"
            source = Path(td) / "test.parquet"
            source.write_bytes(parquet_bytes)
            proc = subprocess.run(
                [
                    "bash",
                    str(SNAPSHOT_SCRIPT),
                    "--output-root",
                    str(root),
                    "--source-parquet",
                    str(source),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            dataset_dir = root / "swebench-multilingual-2025-08-26"
            row_count = json.loads((dataset_dir / "ROW_COUNT.json").read_text())
            sha_manifest = (dataset_dir / "SHA256SUMS").read_text()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(row_count["row_count"], 300)
        self.assertEqual(row_count["expected_task_count"], 300)
        self.assertEqual(row_count["status"], "verified_from_parquet_footer")
        self.assertIn("ROW_COUNT.json", sha_manifest)

    def test_image_manifest_is_300_task_fail_closed_skeleton(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "swebench_multilingual")
        self.assertEqual(data["status"], "blocked_until_full300_transport_materialized")
        self.assertEqual(data["expected_task_count"], 300)
        self.assertEqual(data["image_system"], "SWE-bench harness instance images")
        self.assertIn("stage_swebench_verified_p0.py", data["staging_reuse"]["candidate_script"])
        self.assertEqual(len(data["languages"]), 9)
        images = data["images"]
        self.assertEqual(len(images), 300)
        instance_ids = {row["instance_id"] for row in images}
        self.assertEqual(len(instance_ids), 300)
        for row in images:
            self.assertTrue(row["required"])
            self.assertEqual(row["role"], "swebench_instance_image")
            self.assertEqual(row["image_transport"], "missing")
            self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
            self.assertNotIn("p0_digest_ref", row)
            self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_includes_multilingual_fail_closed_row(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("swebench_multilingual", manifests)
        self.assertEqual(manifests["swebench_multilingual"]["path"], "images/swemultilingual.yaml")
        self.assertIn("blocked", manifests["swebench_multilingual"]["status"])
        self.assertEqual(manifests["swebench_multilingual"]["policy"], "required_when_swemultilingual_enabled")

    def test_runner_dry_run_exposes_mini_swe_agent_relay_and_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "swebench-multilingual-2025-08-26"
            dataset.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "SWEML_DATASET_DIR": str(dataset),
                    "SWEML_OUTPUT_DIR": str(Path(td) / "run"),
                    "SWEML_MODEL": "gpt-5.4-mini",
                    "SWEML_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                    "SWEML_MAX_WORKERS": "3",
                    "SWEML_SLICE": "0:2",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--slice", "0:2"],
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
        self.assertEqual(payload["scaffold"], "mini-swe-agent")
        self.assertEqual(payload["model"], "gpt-5.4-mini")
        self.assertEqual(payload["openai_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["max_workers"], 3)
        self.assertEqual(payload["slice"], "0:2")
        self.assertIn("mini-swe-agent", " ".join(payload["planned_command"]))

    def test_runner_non_dry_run_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "swebench-multilingual-2025-08-26"
            dataset.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "SWEML_DATASET_DIR": str(dataset),
                    "SWEML_OUTPUT_DIR": str(Path(td) / "run"),
                    "SWEML_MODEL": "gpt-5.4-mini",
                    "SWEML_OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--mode", "smoke", "--slice", "0:2"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("fail-closed", proc.stderr)

    def test_strict_parser_recomputes_resolved_and_failure_classes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            ok = run_dir / "apache__druid-13704"
            ok.mkdir()
            (ok / "patch.diff").write_text("diff --git a/a b/a\n")
            (ok / "report.json").write_text(json.dumps({
                "instance_id": "apache__druid-13704",
                "repo": "apache/druid",
                "language": "java",
                "transport_status": "p0_proven",
                "scaffold": "mini-swe-agent",
                "agent_rc": 0,
                "timeout": False,
                "patch_path": str(ok / "patch.diff"),
                "eval_rc": 0,
                "fail_to_pass": {"required": 1, "passed": 1},
                "pass_to_pass": {"required": 2, "passed": 2},
            }))
            bad = run_dir / "vuejs__core-11915"
            bad.mkdir()
            (bad / "report.json").write_text(json.dumps({
                "instance_id": "vuejs__core-11915",
                "language": "typescript",
                "transport_status": "missing",
                "scaffold": "mini-swe-agent",
                "agent_rc": 0,
                "timeout": False,
                "eval_rc": 0,
                "fail_to_pass": {"required": 1, "passed": 0},
                "pass_to_pass": {"required": 1, "passed": 1},
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
        self.assertEqual(summary["bench_id"], "swebench_multilingual")
        self.assertEqual(summary["expected_tasks"], 2)
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(summary["resolved_count"], 1)
        self.assertEqual(summary["failed_count"], 1)
        self.assertIn("image_transport_unproven", summary["failures"][0]["failure_classes"])
        self.assertIn("resolved_false", summary["failures"][0]["failure_classes"])


if __name__ == "__main__":
    unittest.main()
