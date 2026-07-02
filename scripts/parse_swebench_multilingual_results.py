#!/usr/bin/env python3
"""Strict SWE-bench Multilingual result parser skeleton."""

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


def _test_group_passed(group: Any) -> bool:
    if not isinstance(group, dict):
        return False
    required = group.get("required")
    passed = group.get("passed")
    return isinstance(required, int) and isinstance(passed, int) and passed >= required


def parse_run(run_dir: Path, expected_tasks: int | None = None) -> dict[str, Any]:
    report_paths = sorted(run_dir.glob("**/report.json"))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    resolved_count = 0

    for report_path in report_paths:
        failure_classes: list[str] = []
        try:
            data = _load_json(report_path)
        except Exception as exc:  # pragma: no cover
            failures.append({"instance_id": None, "report_path": str(report_path), "failure_classes": [f"invalid_json:{exc}"]})
            continue

        instance_id = str(data.get("instance_id") or report_path.parent.name)
        transport = data.get("transport_status")
        fail_to_pass_ok = _test_group_passed(data.get("fail_to_pass"))
        pass_to_pass_ok = _test_group_passed(data.get("pass_to_pass"))
        eval_rc = data.get("eval_rc")
        agent_rc = data.get("agent_rc")
        timeout = bool(data.get("timeout"))
        patch_exists = _path_exists(data.get("patch_path"), report_path)

        if transport not in {"p0_proven", "fallback_verified"}:
            failure_classes.append("image_transport_unproven")
        if agent_rc not in {0, None}:
            failure_classes.append("agent_error")
        if timeout:
            failure_classes.append("agent_timeout")
        if not patch_exists:
            failure_classes.append("missing_patch_file")
        if eval_rc != 0:
            failure_classes.append("eval_error")
        if not fail_to_pass_ok or not pass_to_pass_ok:
            failure_classes.append("resolved_false")

        resolved = not failure_classes
        if resolved:
            resolved_count += 1
        row = {
            "instance_id": instance_id,
            "repo": data.get("repo"),
            "language": data.get("language"),
            "transport_status": transport,
            "scaffold": data.get("scaffold"),
            "agent_rc": agent_rc,
            "timeout": timeout,
            "patch_path": data.get("patch_path"),
            "eval_rc": eval_rc,
            "fail_to_pass": data.get("fail_to_pass"),
            "pass_to_pass": data.get("pass_to_pass"),
            "resolved": resolved,
            "failure_classes": failure_classes,
            "report_path": str(report_path),
        }
        rows.append(row)
        if failure_classes:
            failures.append(row)

    expected = expected_tasks if expected_tasks is not None else len(report_paths)
    if expected != len(report_paths):
        failures.append({
            "instance_id": "__aggregate__",
            "report_path": str(run_dir),
            "failure_classes": [f"result_count_mismatch:expected={expected}:actual={len(report_paths)}"],
        })

    return {
        "bench_id": "swebench_multilingual",
        "expected_tasks": expected,
        "result_count": len(report_paths),
        "resolved_count": resolved_count,
        "failed_count": len(failures),
        "full_ready": expected == 300 and not failures,
        "failures": failures,
        "instances": rows,
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
        print(f"swebench_multilingual result_count={summary['result_count']} failed_count={summary['failed_count']} full_ready={summary['full_ready']}")
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
