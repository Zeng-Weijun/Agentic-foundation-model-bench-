#!/usr/bin/env python3
"""Aggregate NL2Repo Path A per-task results into the benchmark metrics.

macro_mean_success_rate = mean over tasks of min(passed/total, 1)   [upstream metric]
micro_pass_rate         = sum(passed) / sum(total)
Writes aggregate.json + prints a per-task table.
"""
import argparse
import glob
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", required=True)
    args = ap.parse_args()

    rows = []
    for sp in sorted(glob.glob(os.path.join(args.run_root, "*", "summary.json"))):
        try:
            d = json.load(open(sp))
        except Exception:
            continue
        ag = d.get("agent") or {}
        pr = ag.get("pytest_results") or {}
        rows.append({
            "task": d.get("task"),
            "passed": pr.get("passed"), "failed": pr.get("failed"),
            "errors": pr.get("errors"), "total": pr.get("total"),
            "success_rate": ag.get("success_rate"),
            "workspace_files": ag.get("workspace_files"),
            "assistant_turns": (ag.get("stream") or {}).get("assistant_turns"),
            "agent_seconds": ag.get("agent_seconds"), "timed_out": ag.get("timed_out"),
            "command_exit_codes": ag.get("command_exit_codes"),
        })

    n = len(rows)
    done = [r for r in rows if r["success_rate"] is not None]
    mean_sr = sum(r["success_rate"] for r in done) / len(done) if done else 0.0
    tot_pass = sum((r["passed"] or 0) for r in done)
    tot_cases = sum((r["total"] or 0) for r in done)
    micro = tot_pass / tot_cases if tot_cases else 0.0
    solved = sum(1 for r in done if (r["success_rate"] or 0) >= 1.0)

    print(f"run_root={args.run_root}")
    print(f"tasks_with_summary={n}  scored={len(done)}  fully_solved(sr=1.0)={solved}")
    print(f"macro_mean_success_rate={mean_sr:.4f}")
    print(f"micro_pass_rate(sum passed/sum total)={micro:.4f}  ({tot_pass}/{tot_cases})")
    print()
    print(f"{'task':26} {'pass/total':>12} {'rate':>7} {'turns':>6} {'sec':>8} to")
    for r in sorted(rows, key=lambda x: (x["success_rate"] is None, -(x["success_rate"] or 0))):
        sr = r["success_rate"]
        srs = f"{sr:.3f}" if sr is not None else "  -  "
        pt = f"{r['passed']}/{r['total']}"
        print(f"{(r['task'] or '?'):26} {pt:>12} {srs:>7} {str(r['assistant_turns']):>6} "
              f"{str(r['agent_seconds']):>8} {'Y' if r['timed_out'] else ''}")

    out = {
        "run_root": args.run_root, "tasks_with_summary": n, "scored": len(done),
        "fully_solved": solved, "macro_mean_success_rate": mean_sr,
        "micro_pass_rate": micro, "total_passed": tot_pass, "total_cases": tot_cases,
        "rows": rows,
    }
    json.dump(out, open(os.path.join(args.run_root, "aggregate.json"), "w"), indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
