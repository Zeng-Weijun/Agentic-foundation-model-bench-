#!/usr/bin/env python3
"""Strict NL2Repo pytest reward parser skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


def _path_exists(value: Any, result_path: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    p = Path(value)
    return p.exists() if p.is_absolute() else (result_path.parent / p).exists()


def parse_run(run_dir: Path, expected_tasks: int | None = None) -> dict[str, Any]:
    result_paths = sorted(run_dir.glob("**/result.json"))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    resolved_count = 0

    for result_path in result_paths:
        failure_classes: list[str] = []
        try:
            data = _load_json(result_path)
        except Exception as exc:  # pragma: no cover
            failures.append({"task_id": None, "result_path": str(result_path), "failure_classes": [f"invalid_json:{exc}"]})
            continue

        task_id = str(data.get("task_id") or result_path.parent.name)
        transport = data.get("transport_status")
        wheelhouse = data.get("wheelhouse_status")
        submit_called = data.get("submit_called") is True
        total_commands = data.get("test_commands_total")
        done_commands = data.get("test_commands_completed")
        passed = data.get("passed_tests")
        failed = data.get("failed_tests")
        errors = data.get("error_tests")
        total = data.get("total_tests")
        reward = data.get("reward")
        agent_status = data.get("agent_status")

        if transport not in {"p0_proven", "fallback_verified"}:
            failure_classes.append("image_transport_unproven")
        if wheelhouse != "verified":
            failure_classes.append("wheelhouse_missing")
        if agent_status != "submitted":
            failure_classes.append("agent_error")
        if not submit_called:
            failure_classes.append("submit_not_called")
        if not isinstance(total_commands, int) or not isinstance(done_commands, int) or done_commands < total_commands:
            failure_classes.append("test_commands_incomplete")
        if not all(isinstance(x, int) for x in (passed, failed, errors, total)):
            failure_classes.append("pytest_counts_missing")
        elif passed + failed + errors > total:
            failure_classes.append("pytest_counts_inconsistent")
        if reward != 1.0 or failed != 0 or errors != 0 or passed != total:
            failure_classes.append("resolved_false")
        if not _path_exists(data.get("patch_or_workspace_archive"), result_path):
            failure_classes.append("missing_workspace_archive")
        if not _path_exists(data.get("trajectory_path"), result_path):
            failure_classes.append("missing_trajectory_path")

        resolved = not failure_classes
        if resolved:
            resolved_count += 1
        row = {
            "task_id": task_id,
            "transport_status": transport,
            "wheelhouse_status": wheelhouse,
            "agent_status": agent_status,
            "submit_called": submit_called,
            "test_commands_total": total_commands,
            "test_commands_completed": done_commands,
            "passed_tests": passed,
            "failed_tests": failed,
            "error_tests": errors,
            "total_tests": total,
            "reward": reward,
            "resolved": resolved,
            "failure_classes": failure_classes,
            "result_path": str(result_path),
        }
        rows.append(row)
        if failure_classes:
            failures.append(row)

    expected = expected_tasks if expected_tasks is not None else len(result_paths)
    if expected != len(result_paths):
        failures.append({
            "task_id": "__aggregate__",
            "result_path": str(run_dir),
            "failure_classes": [f"result_count_mismatch:expected={expected}:actual={len(result_paths)}"],
        })

    return {
        "bench_id": "nl2repo",
        "expected_tasks": expected,
        "result_count": len(result_paths),
        "resolved_count": resolved_count,
        "failed_count": len(failures),
        "full_ready": expected in (103, 104) and not failures,
        "failures": failures,
        "tasks": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--expected-tasks", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = parse_run(args.run_dir, args.expected_tasks)
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"nl2repo result_count={summary['result_count']} failed_count={summary['failed_count']} full_ready={summary['full_ready']}")
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
