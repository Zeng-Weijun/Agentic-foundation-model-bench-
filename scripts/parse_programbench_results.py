#!/usr/bin/env python3
"""Strict ProgramBench result parser skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PASSED = {"passed", "pass", "ok"}
SYSTEM_STATUSES = {"system_error", "error", "timeout", "infra_error"}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return data


def _find_submission(agent_dir: Path, instance_id: str) -> Path:
    return agent_dir / instance_id / "submission.tar.gz"


def _find_trace(agent_dir: Path, instance_id: str) -> Path | None:
    task_dir = agent_dir / instance_id
    candidates = [
        task_dir / f"{instance_id}.traj.json",
        task_dir / f"{instance_id}.traj.jsonl",
        task_dir / "trajectory.jsonl",
        task_dir / "traj.json",
    ]
    for path in candidates:
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def _instance_id_from_eval(path: Path) -> str:
    name = path.name
    suffix = ".eval.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return path.stem


def _classify_eval(data: dict[str, Any]) -> tuple[list[str], int, int, float]:
    classes: list[str] = []
    if data.get("error_code") not in (None, "", 0):
        classes.append("top_level_error")
    branch_errors = data.get("test_branch_errors") or {}
    if branch_errors:
        classes.append("branch_error")
    warnings = data.get("warnings") or []
    if warnings:
        classes.append("warnings_present")
    results = data.get("test_results")
    if not isinstance(results, list) or not results:
        classes.append("missing_test_results")
        return classes, 0, 0, 0.0
    total = 0
    passed = 0
    for row in results:
        if not isinstance(row, dict):
            classes.append("invalid_test_result")
            continue
        status = str(row.get("status") or "").lower()
        total += 1
        if status in PASSED:
            passed += 1
        elif status in SYSTEM_STATUSES:
            classes.append("system_error")
    score = passed / total if total else 0.0
    if total == 0:
        classes.append("missing_test_results")
    if passed != total:
        classes.append("resolved_false")
    return list(dict.fromkeys(classes)), total, passed, score


def parse_programbench(agent_dir: Path, eval_dir: Path, expected_tasks: int | None = None) -> dict[str, Any]:
    eval_paths = sorted(eval_dir.glob("**/*.eval.json"))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    resolved_count = 0
    attempted = 0
    infra_failures = 0
    score_sum = 0.0

    for eval_path in eval_paths:
        instance_id = _instance_id_from_eval(eval_path)
        failure_classes: list[str] = []
        data = _load_json(eval_path)
        submission = _find_submission(agent_dir, instance_id)
        trace = _find_trace(agent_dir, instance_id)
        if not submission.exists() or submission.stat().st_size == 0:
            failure_classes.append("missing_submission")
        else:
            attempted += 1
        if trace is None:
            failure_classes.append("missing_agent_trace")
        eval_classes, n_tests, n_passed, score = _classify_eval(data)
        failure_classes.extend(eval_classes)
        failure_classes = list(dict.fromkeys(failure_classes))
        score_sum += score
        infra = any(x in failure_classes for x in ["top_level_error", "branch_error", "system_error", "missing_test_results", "invalid_test_result"])
        if infra:
            infra_failures += 1
        resolved = not failure_classes and n_tests > 0 and n_passed == n_tests
        if resolved:
            resolved_count += 1
        row = {
            "instance_id": instance_id,
            "attempted": submission.exists() and submission.stat().st_size > 0,
            "agent_trace_ok": trace is not None,
            "eval_json_ok": True,
            "n_tests_active": n_tests,
            "n_passed": n_passed,
            "score": score,
            "resolved": resolved,
            "infra_failure": infra,
            "failure_classes": failure_classes,
            "submission_path": str(submission),
            "trace_path": str(trace) if trace else None,
            "eval_path": str(eval_path),
        }
        rows.append(row)
        if failure_classes:
            failures.append(row)

    expected = expected_tasks if expected_tasks is not None else len(eval_paths)
    if expected != len(eval_paths):
        failures.append({
            "instance_id": "__aggregate__",
            "failure_classes": [f"eval_json_count_mismatch:expected={expected}:actual={len(eval_paths)}"],
            "eval_path": str(eval_dir),
        })
    mean_score = score_sum / len(eval_paths) if eval_paths else 0.0
    return {
        "bench_id": "programbench",
        "expected_tasks": expected,
        "eval_json_count": len(eval_paths),
        "attempted_instances": attempted,
        "resolved_count": resolved_count,
        "infra_failure_count": infra_failures,
        "missing_submission_count": sum(1 for row in rows if "missing_submission" in row["failure_classes"]),
        "missing_eval_count": max(expected - len(eval_paths), 0),
        "mean_score": mean_score,
        "full_ready": expected == 200 and not failures,
        "failures": failures,
        "instances": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", required=True, type=Path)
    parser.add_argument("--eval-dir", required=True, type=Path)
    parser.add_argument("--expected-tasks", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = parse_programbench(args.agent_dir, args.eval_dir, args.expected_tasks)
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(
            "programbench "
            f"eval_json_count={summary['eval_json_count']} "
            f"resolved_count={summary['resolved_count']} "
            f"infra_failure_count={summary['infra_failure_count']} "
            f"full_ready={summary['full_ready']}"
        )
    return 0 if not summary["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
