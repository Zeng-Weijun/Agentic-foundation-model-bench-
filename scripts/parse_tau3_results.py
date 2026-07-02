#!/usr/bin/env python3
"""Strict tau3 result parser skeleton.

This parser is intentionally conservative: missing reward detail or runtime/DB
state marks the run invalid even if a numeric reward is present.
"""

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


def _reward_from(data: dict[str, Any]) -> float | None:
    verifier = data.get("verifier_result")
    if not isinstance(verifier, dict):
        return None
    rewards = verifier.get("rewards")
    if isinstance(rewards, dict) and isinstance(rewards.get("reward"), (int, float)):
        return float(rewards["reward"])
    if isinstance(verifier.get("reward"), (int, float)):
        return float(verifier["reward"])
    return None


def _reward_info(data: dict[str, Any]) -> dict[str, Any] | None:
    verifier = data.get("verifier_result")
    if not isinstance(verifier, dict):
        return None
    info = verifier.get("reward_info") or verifier.get("info")
    return info if isinstance(info, dict) else None


def _runtime_state(data: dict[str, Any], result_path: Path) -> dict[str, Any] | None:
    state = data.get("runtime_state")
    if isinstance(state, dict):
        return state
    sibling = result_path.parent / "tau3_runtime_state.json"
    if sibling.exists():
        loaded = _load_json(sibling)
        return loaded if isinstance(loaded, dict) else None
    return None


def _has_db_state(info: dict[str, Any] | None) -> bool:
    if not info:
        return False
    keys = {str(k).lower() for k in info.keys()}
    return any("db" in key or "database" in key for key in keys)


def parse_run(run_dir: Path, expected_tasks: int | None = None) -> dict[str, Any]:
    result_paths = sorted(run_dir.glob("**/result.json"))
    tasks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    passed_count = 0

    for result_path in result_paths:
        reasons: list[str] = []
        try:
            data = _load_json(result_path)
        except Exception as exc:  # pragma: no cover - defensive path
            failures.append({"result_path": str(result_path), "task_id": None, "reasons": [f"invalid_json:{exc}"]})
            continue

        task_id = str(data.get("task_id") or result_path.parent.name)
        reward = _reward_from(data)
        info = _reward_info(data)
        state = _runtime_state(data, result_path)

        if reward is None:
            reasons.append("missing_reward")
        elif reward not in (0.0, 1.0):
            reasons.append("non_binary_reward")
        if info is None:
            reasons.append("missing_reward_info")
        if not _has_db_state(info):
            reasons.append("missing_db_state_evidence")
        if state is None:
            reasons.append("missing_runtime_state")
        else:
            if not isinstance(state.get("messages"), list):
                reasons.append("missing_runtime_messages")
            if state.get("num_errors") not in (0, None):
                reasons.append("runtime_errors_present")

        if reward == 1.0 and not reasons:
            passed_count += 1

        task_row = {
            "task_id": task_id,
            "result_path": str(result_path),
            "reward": reward,
            "passed": reward == 1.0 and not reasons,
            "reasons": reasons,
        }
        tasks.append(task_row)
        if reasons:
            failures.append(task_row)

    expected = expected_tasks if expected_tasks is not None else len(result_paths)
    if expected != len(result_paths):
        failures.append({
            "task_id": "__aggregate__",
            "result_path": str(run_dir),
            "reasons": [f"result_count_mismatch:expected={expected}:actual={len(result_paths)}"],
        })

    return {
        "bench_id": "tau3_bench",
        "expected_tasks": expected,
        "result_count": len(result_paths),
        "passed_count": passed_count,
        "failed_count": len(failures),
        "reward_mean": round(sum((row["reward"] or 0.0) for row in tasks) / len(tasks), 6) if tasks else 0.0,
        "full_ready": expected == 375 and not failures,
        "failures": failures,
        "tasks": tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--expected-tasks", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = parse_run(args.run_dir, args.expected_tasks)
    if args.json:
        print(json.dumps(summary, indent=None, sort_keys=True))
    else:
        print(f"tau3 result_count={summary['result_count']} failed_count={summary['failed_count']} full_ready={summary['full_ready']}")
    return 0 if summary["failed_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
