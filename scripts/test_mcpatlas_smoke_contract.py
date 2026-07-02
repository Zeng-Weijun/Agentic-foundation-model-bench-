#!/usr/bin/env python3
"""Focused contract tests for MCP-Atlas local/replay smoke enablement."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


def _compact_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _compact_i64(value: int) -> bytes:
    encoded = (value << 1) ^ (value >> 63)
    return _compact_varint(encoded)


def _fake_parquet_with_num_rows(num_rows: int) -> bytes:
    footer = bytes([0x15]) + _compact_varint(2) + bytes([0x26]) + _compact_i64(num_rows) + bytes([0])
    return b"PAR1" + footer + len(footer).to_bytes(4, "little") + b"PAR1"

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "snapshot_mcp_atlas_dataset.sh"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_mcp_atlas_offline.sh"
PARSER_SCRIPT = REPO_ROOT / "scripts" / "parse_mcp_atlas_results.py"
IMAGE_MANIFEST = REPO_ROOT / "manifests" / "images" / "mcp_atlas.yaml"
REGISTRY = REPO_ROOT / "manifests" / "bench_registry.yaml"
CONTRACT_DOC = REPO_ROOT / "docs" / "mcp_atlas_smoke_contract.md"


class MCPAtlasSmokeContractTest(unittest.TestCase):
    def test_snapshot_dry_run_reports_public_hf_parquet_and_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "datasets"
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
        self.assertEqual(payload["bench_id"], "mcp_atlas")
        self.assertEqual(payload["hf_dataset"], "ScaleAI/MCP-Atlas")
        self.assertEqual(payload["parquet_file"], "MCP-Atlas.parquet")
        self.assertEqual(payload["expected_task_count"], 500)
        self.assertEqual(payload["sample_task_count"], 10)
        self.assertGreater(len(proc.stdout.splitlines()), 1)
        self.assertEqual(payload["content_length"], 15638757)
        self.assertEqual(payload["etag"], "89dcacffef7a52ab656bee3ccea653ab754f4314c63418956b483cf620966217")
        self.assertTrue(payload["dataset_path"].endswith("ScaleAI-MCP-Atlas/MCP-Atlas.parquet"))
        self.assertIn("sha256", payload["sha256_path"])
        self.assertIn("row_count", payload["verification_fields"])


    def test_snapshot_materializes_local_fixture_and_writes_sha_row_count(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file_root = root / "hf_files"
            file_root.mkdir()
            files = {
                ".gitattributes": b"*.parquet filter=lfs\n",
                "README.md": b"# MCP Atlas\n",
                "MCP-Atlas.parquet": _fake_parquet_with_num_rows(3),
            }
            for rel, data in files.items():
                (file_root / rel).write_bytes(data)
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps({
                "sha": "fixture-revision",
                "siblings": [
                    {"rfilename": rel, "size": len(data)}
                    for rel, data in sorted(files.items())
                ],
            }))
            out_root = root / "datasets"
            env = os.environ.copy()
            env.update({
                "MCP_ATLAS_EXPECTED_TASK_COUNT": "3",
                "MCP_ATLAS_HF_REVISION": "fixture-revision",
                "MCP_ATLAS_CONTENT_LENGTH": str(len(files["MCP-Atlas.parquet"])),
            })
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
            self.assertEqual(payload["row_count"], 3)
            dataset_path = Path(payload["dataset_path"])
            self.assertTrue(dataset_path.is_file())
            self.assertTrue(Path(payload["sha256_path"]).is_file())
            self.assertTrue(Path(payload["row_count_path"]).is_file())
            rows = json.loads(Path(payload["row_count_path"]).read_text())
            self.assertEqual(rows["row_count"], 3)
            self.assertEqual(len((dataset_path.parent / "SHA256SUMS").read_text().splitlines()), 3)

    def test_snapshot_refuses_when_metadata_size_exceeds_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps({
                "sha": "fixture-revision",
                "siblings": [{"rfilename": "MCP-Atlas.parquet", "size": 12345}],
            }))
            env = os.environ.copy()
            env["MCP_ATLAS_HF_REVISION"] = "fixture-revision"
            proc = subprocess.run(
                [
                    "bash",
                    str(SNAPSHOT_SCRIPT),
                    "--output-root",
                    str(root / "datasets"),
                    "--metadata-json",
                    str(metadata_path),
                    "--download-base-url",
                    (root / "hf_files").as_uri() + "/",
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

    def test_image_manifest_declares_single_runtime_fail_closed_and_smoke_profile(self) -> None:
        data = yaml.safe_load(IMAGE_MANIFEST.read_text())
        self.assertEqual(data["schema_version"], "agentic_bench.image_manifest.v1")
        self.assertEqual(data["bench_id"], "mcp_atlas")
        self.assertEqual(data["status"], "blocked_until_local_replay_smoke_assets_materialized")
        self.assertFalse(data["full_ready"])
        self.assertEqual(data["expected_full_task_count"], 500)
        self.assertEqual(data["smoke_contract"]["max_tasks"], 5)
        self.assertEqual(data["smoke_contract"]["server_profile"], "local_replay_smoke")
        self.assertEqual(data["smoke_contract"]["external_service_profile"], "replay")
        self.assertIn("calculator", data["smoke_contract"]["allowed_servers"])
        self.assertIn("memory", data["smoke_contract"]["allowed_servers"])
        self.assertIn("filesystem", data["smoke_contract"]["allowed_servers"])
        self.assertIn("arxiv", data["full_blockers"]["requires_mirror_or_replay"])
        self.assertIn("ddg-search", data["full_blockers"]["requires_mirror_or_replay"])
        images = data["images"]
        self.assertEqual(len(images), 1)
        row = images[0]
        self.assertEqual(row["id"], "mcp_atlas_agent_environment_1_2_5")
        self.assertEqual(row["source_image"], "ghcr.io/scaleapi/mcp-atlas:1.2.5")
        self.assertEqual(row["linux_amd64_manifest_digest"], "sha256:17ebc85b99914125f61696bf3c1052b965d9b472ba7ba3d188b2d4513f0a4b62")
        self.assertTrue(row["required"])
        self.assertEqual(row["image_transport"], "missing")
        self.assertEqual(row["registry_status"], "missing_p0_digest_and_verified_fallback")
        self.assertNotIn("p0_digest_ref", row)
        self.assertNotIn("fallback_tar_sha256", row)

    def test_registry_includes_mcp_atlas_fail_closed_row(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text())
        manifests = {row["id"]: row for row in data["image_manifests"]}
        self.assertIn("mcp_atlas", manifests)
        self.assertEqual(manifests["mcp_atlas"]["path"], "images/mcp_atlas.yaml")
        self.assertIn("blocked", manifests["mcp_atlas"]["status"])
        self.assertEqual(manifests["mcp_atlas"]["policy"], "required_when_mcp_atlas_smoke_enabled")

    def test_runner_dry_run_exposes_local_replay_smoke_and_two_model_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dataset = Path(td) / "ScaleAI-MCP-Atlas" / "MCP-Atlas.parquet"
            dataset.parent.mkdir(parents=True)
            dataset.write_bytes(b"PAR1placeholder")
            env = os.environ.copy()
            env.update(
                {
                    "MCP_ATLAS_DATASET": str(dataset),
                    "MCP_ATLAS_OUTPUT_DIR": str(Path(td) / "run"),
                    "MCP_ATLAS_AGENT_MODEL": "gpt-5.4-mini",
                    "MCP_ATLAS_JUDGE_MODEL": "gpt-5.4-mini",
                    "MCP_ATLAS_AGENT_BASE_URL": "http://100.96.1.101:18540/v1",
                    "MCP_ATLAS_JUDGE_BASE_URL": "http://100.96.1.101:18540/v1",
                    "DOCKER_HOST": "unix:///tmp/rl-vfs/run/docker-shim.sock",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--dry-run", "--mode", "smoke", "--task-limit", "5", "--server-profile", "local_replay_smoke"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "dry_run")
        self.assertEqual(payload["bench_id"], "mcp_atlas")
        self.assertEqual(payload["mode"], "smoke")
        self.assertEqual(payload["task_limit"], 5)
        self.assertEqual(payload["server_profile"], "local_replay_smoke")
        self.assertEqual(payload["external_service_profile"], "replay")
        self.assertEqual(payload["agent_model"], "gpt-5.4-mini")
        self.assertEqual(payload["judge_model"], "gpt-5.4-mini")
        self.assertEqual(payload["agent_base_url"], "http://100.96.1.101:18540/v1")
        self.assertEqual(payload["judge_base_url"], "http://100.96.1.101:18540/v1")
        self.assertIn("calculator", payload["enabled_servers"])
        self.assertLessEqual(len(payload["selected_task_ids"]), 5)
        self.assertFalse(payload["full_score_valid"])
        self.assertIn("full500_external_service_closure_missing", payload["full_blockers"])
        self.assertNotIn("API_KEY", json.dumps(payload))

    def test_runner_non_dry_run_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env.update(
                {
                    "MCP_ATLAS_DATASET": str(Path(td) / "MCP-Atlas.parquet"),
                    "MCP_ATLAS_OUTPUT_DIR": str(Path(td) / "run"),
                    "MCP_ATLAS_AGENT_MODEL": "gpt-5.4-mini",
                    "MCP_ATLAS_JUDGE_MODEL": "gpt-5.4-mini",
                    "MCP_ATLAS_AGENT_BASE_URL": "http://100.96.1.101:18540/v1",
                    "MCP_ATLAS_JUDGE_BASE_URL": "http://100.96.1.101:18540/v1",
                    "DOCKER_HOST": "unix:///tmp/rl-vfs/run/docker-shim.sock",
                }
            )
            proc = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), "--mode", "smoke", "--task-limit", "5", "--server-profile", "local_replay_smoke"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 78)
        self.assertIn("fail-closed", proc.stderr)

    def test_strict_parser_claim_coverage_and_false_green_guards(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "tasks").mkdir()
            (run_dir / "tasks" / "task_pass.json").write_text(json.dumps({
                "task_id": "task_pass",
                "prompt_present": True,
                "gtfa_claim_count": 4,
                "enabled_tools_expected": ["calculator_add"],
                "enabled_servers_observed": ["calculator"],
                "completion_status": "ok",
                "agent_response_present": True,
                "raw_conversation_history_present": True,
                "tool_call_count": 1,
                "tool_errors": [],
                "judge_status": "ok",
                "coverage_score": 0.8,
                "coverage_details_count": 4,
                "agent_model_call_count": 2,
                "judge_model_call_count": 1,
            }))
            (run_dir / "tasks" / "task_fail.json").write_text(json.dumps({
                "task_id": "task_fail",
                "prompt_present": True,
                "gtfa_claim_count": 2,
                "enabled_tools_expected": ["memory_search"],
                "enabled_servers_observed": ["memory"],
                "completion_status": "ok",
                "agent_response_present": True,
                "raw_conversation_history_present": True,
                "tool_call_count": 1,
                "tool_errors": [],
                "judge_status": "ok",
                "coverage_score": 0.5,
                "coverage_details_count": 2,
                "agent_model_call_count": 1,
                "judge_model_call_count": 1,
            }))
            proc = subprocess.run(
                ["python3", str(PARSER_SCRIPT), "--run-dir", str(run_dir), "--mode", "smoke", "--server-profile", "local_replay_smoke", "--expected-tasks", "2", "--json"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["bench_id"], "mcp_atlas")
        self.assertEqual(summary["mode"], "smoke")
        self.assertEqual(summary["selected_task_count"], 2)
        self.assertEqual(summary["completed_task_count"], 2)
        self.assertEqual(summary["scored_task_count"], 2)
        self.assertEqual(summary["coverage_pass_count"], 1)
        self.assertEqual(summary["coverage_threshold"], 0.75)
        self.assertFalse(summary["full_score_valid"])
        self.assertEqual(summary["agent_model_call_count"], 3)
        self.assertEqual(summary["judge_model_call_count"], 2)
        failures = {row["task_id"]: row for row in summary["failures"]}
        self.assertIn("task_fail", failures)
        self.assertIn("coverage_below_threshold", failures["task_fail"]["failure_reasons"])

    def test_contract_doc_names_smoke_not_full_and_external_server_blockers(self) -> None:
        text = CONTRACT_DOC.read_text()
        self.assertIn("local/replay smoke", text)
        self.assertIn("not a full500 claim", text)
        self.assertIn("calculator", text)
        self.assertIn("filesystem", text)
        self.assertIn("memory", text)
        self.assertIn("arxiv", text)
        self.assertIn("ddg-search", text)
        self.assertIn("weather", text)
        self.assertIn("coverage >= 0.75", text)


if __name__ == "__main__":
    unittest.main()
