#!/usr/bin/env python3
"""Strict DeepSWE behavior-verifier parser skeleton."""

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


def _verifier(data: dict[str, Any]) -> dict[str, Any]:
    verifier = data.get("verifier") or data.get("verifier_result") or {}
    return verifier if isinstance(verifier, dict) else {}


def _path_exists(value: Any, result_path: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    p = Path(value)
    if p.is_absolute():
        return p.exists()
    return (result_path.parent / p).exists()


def parse_run(run_dir: Path, expected_tasks: int | None = None) -> dict[str, Any]:
    result_paths = sorted(run_dir.glob("**/result.json"))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    resolved_count = 0

    for result_path in result_paths:
        reasons: list[str] = []
        try:
            data = _load_json(result_path)
        except Exception as exc:  # pragma: no cover
            failures.append({"task_id": None, "result_path": str(result_path), "reasons": [f"invalid_json:{exc}"]})
            continue

        task_id = str(data.get("task_id") or result_path.parent.name)
        verifier = _verifier(data)
        rc = verifier.get("rc", data.get("verifier_rc"))
        reward = verifier.get("reward", data.get("reward"))
        resolved = verifier.get("resolved", data.get("resolved"))
        transport = data.get("transport_status")

        if data.get("agent") != "mini-swe-agent":
            reasons.append("unexpected_or_missing_agent")
        if not data.get("model"):
            reasons.append("missing_model")
        if data.get("agent_exit_status") not in {"submitted", "completed"}:
            reasons.append("agent_not_submitted")
        if transport not in {"p0_proven", "fallback_verified"}:
            reasons.append("image_transport_unproven")
        if rc is None:
            reasons.append("missing_verifier_rc")
        if reward is None:
            reasons.append("missing_reward")
        if resolved is None:
            reasons.append("missing_resolved")
        if not _path_exists(data.get("patch_path"), result_path):
            reasons.append("missing_patch_path")
        if not _path_exists(data.get("trajectory_path"), result_path):
            reasons.append("missing_trajectory_path")

        passed = rc == 0 and reward == 1.0 and resolved is True and not reasons
        if passed:
            resolved_count += 1

        row = {
            "task_id": task_id,
            "result_path": str(result_path),
            "agent": data.get("agent"),
            "model": data.get("model"),
            "verifier_rc": rc,
            "reward": reward,
            "resolved": resolved,
            "passed": passed,
            "reasons": reasons,
        }
        rows.append(row)
        if reasons or not passed:
            failures.append(row)

    expected = expected_tasks if expected_tasks is not None else len(result_paths)
    if expected != len(result_paths):
        failures.append({
            "task_id": "__aggregate__",
            "result_path": str(run_dir),
            "reasons": [f"result_count_mismatch:expected={expected}:actual={len(result_paths)}"],
        })

    return {
        "bench_id": "deepswe",
        "expected_tasks": expected,
        "result_count": len(result_paths),
        "resolved_count": resolved_count,
        "failed_count": len(failures),
        "full_ready": expected == 113 and not failures,
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
        print(f"deepswe result_count={summary['result_count']} failed_count={summary['failed_count']} full_ready={summary['full_ready']}")
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
