#!/usr/bin/env python3
"""Strict MCP-Atlas local/replay smoke parser skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

THRESHOLD = 0.75


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


def _task_failure_reasons(row: dict[str, Any], server_profile: str) -> list[str]:
    reasons: list[str] = []
    if not row.get("prompt_present"):
        reasons.append("prompt_missing")
    if not isinstance(row.get("gtfa_claim_count"), int) or row.get("gtfa_claim_count", 0) <= 0:
        reasons.append("gtfa_claims_missing")
    if row.get("completion_status") != "ok":
        reasons.append("completion_not_ok")
    if not row.get("agent_response_present"):
        reasons.append("agent_response_missing")
    if not row.get("raw_conversation_history_present"):
        reasons.append("conversation_history_missing")
    if not isinstance(row.get("tool_call_count"), int) or row.get("tool_call_count", 0) < 1:
        reasons.append("tool_calls_missing")
    if row.get("tool_errors"):
        reasons.append("tool_errors_present")
    if row.get("judge_status") != "ok":
        reasons.append("judge_not_ok")
    score = row.get("coverage_score")
    if not isinstance(score, (int, float)):
        reasons.append("coverage_missing")
    elif float(score) < THRESHOLD:
        reasons.append("coverage_below_threshold")
    if row.get("coverage_details_count") != row.get("gtfa_claim_count"):
        reasons.append("coverage_details_incomplete")
    if not isinstance(row.get("agent_model_call_count"), int) or row.get("agent_model_call_count", 0) < 1:
        reasons.append("agent_model_calls_missing")
    if not isinstance(row.get("judge_model_call_count"), int) or row.get("judge_model_call_count", 0) < 1:
        reasons.append("judge_model_calls_missing")
    if server_profile in {"", "unknown"}:
        reasons.append("server_profile_unknown")
    return list(dict.fromkeys(reasons))


def parse_run(run_dir: Path, mode: str, server_profile: str, expected_tasks: int | None = None) -> dict[str, Any]:
    task_paths = sorted((run_dir / "tasks").glob("*.json")) if (run_dir / "tasks").exists() else []
    tasks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    completed = 0
    scored = 0
    pass_count = 0
    agent_calls = 0
    judge_calls = 0
    observed_servers: set[str] = set()

    for path in task_paths:
        row = _load(path)
        task_id = str(row.get("task_id") or path.stem)
        reasons = _task_failure_reasons(row, server_profile)
        completed += 1 if row.get("completion_status") == "ok" else 0
        if isinstance(row.get("coverage_score"), (int, float)):
            scored += 1
            if float(row["coverage_score"]) >= THRESHOLD:
                pass_count += 1
        agent_calls += int(row.get("agent_model_call_count") or 0)
        judge_calls += int(row.get("judge_model_call_count") or 0)
        observed_servers.update(str(x) for x in row.get("enabled_servers_observed") or [])
        parsed = {
            "task_id": task_id,
            "prompt_present": bool(row.get("prompt_present")),
            "gtfa_claim_count": row.get("gtfa_claim_count"),
            "enabled_tools_expected": row.get("enabled_tools_expected") or [],
            "enabled_servers_observed": row.get("enabled_servers_observed") or [],
            "completion_status": row.get("completion_status"),
            "agent_response_present": bool(row.get("agent_response_present")),
            "raw_conversation_history_present": bool(row.get("raw_conversation_history_present")),
            "tool_call_count": row.get("tool_call_count"),
            "tool_errors": row.get("tool_errors") or [],
            "judge_status": row.get("judge_status"),
            "coverage_score": row.get("coverage_score"),
            "coverage_details_count": row.get("coverage_details_count"),
            "passed_threshold_0_75": isinstance(row.get("coverage_score"), (int, float)) and float(row["coverage_score"]) >= THRESHOLD,
            "failure_reasons": reasons,
        }
        tasks.append(parsed)
        if reasons:
            failures.append(parsed)

    expected = expected_tasks if expected_tasks is not None else len(task_paths)
    aggregate_failures: list[str] = []
    if expected != len(task_paths):
        aggregate_failures.append(f"task_count_mismatch:expected={expected}:actual={len(task_paths)}")
    if mode == "full500" and len(task_paths) != 500:
        aggregate_failures.append("full500_requires_500_tasks")
    if mode != "full500":
        aggregate_failures.append("smoke_not_full500")
    if agent_calls < len(task_paths):
        aggregate_failures.append("agent_model_call_accounting_incomplete")
    if judge_calls < len(task_paths):
        aggregate_failures.append("judge_model_call_accounting_incomplete")

    full_score_valid = mode == "full500" and len(task_paths) == 500 and not failures and not aggregate_failures
    summary = {
        "bench_id": "mcp_atlas",
        "mode": mode,
        "selected_task_count": len(task_paths),
        "completed_task_count": completed,
        "scored_task_count": scored,
        "coverage_pass_count": pass_count,
        "coverage_pass_rate": pass_count / scored if scored else 0.0,
        "coverage_threshold": THRESHOLD,
        "agent_model_call_count": agent_calls,
        "judge_model_call_count": judge_calls,
        "mcp_server_profile": server_profile,
        "enabled_servers": sorted(observed_servers),
        "external_service_profile": "replay" if server_profile == "local_replay_smoke" else "unknown",
        "full_score_valid": full_score_valid,
        "failure_reasons": aggregate_failures,
        "failures": failures,
        "tasks": tasks,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=["smoke", "full500"], default="smoke")
    parser.add_argument("--server-profile", default="local_replay_smoke")
    parser.add_argument("--expected-tasks", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = parse_run(args.run_dir, args.mode, args.server_profile, args.expected_tasks)
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"mcp_atlas selected={summary['selected_task_count']} pass={summary['coverage_pass_count']} full_score_valid={summary['full_score_valid']}")
    return 0 if not summary["failures"] and not summary["failure_reasons"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
