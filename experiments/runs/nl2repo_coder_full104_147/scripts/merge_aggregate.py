#!/usr/bin/env python3
"""Merge the original full-104 run with the stdin-fix rerun of the argv-overflow tasks.

For each task, prefer the rerun summary (the corrected result) when present, else the
original. Compute the benchmark headline over the union.

  macro_mean_success_rate = mean over tasks of success_rate ( = min(passed/total,1) )
  micro_pass_rate         = sum(passed)/sum(total)

Writes merged_aggregate.json + per_task.tsv + prints the table. Does NOT mutate inputs.
"""
import argparse, glob, json, os


def load_run(root):
    out = {}
    for sp in glob.glob(os.path.join(root, "*", "summary.json")):
        try:
            d = json.load(open(sp))
        except Exception:
            continue
        if d.get("task"):
            out[d["task"]] = (d, os.path.dirname(sp))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True, help="original full-104 run root")
    ap.add_argument("--override", default="", help="stdin-fix rerun root (wins per-task)")
    ap.add_argument("--out", required=True, help="output dir for merged artifacts")
    ap.add_argument("--expect", type=int, default=104)
    args = ap.parse_args()

    prim = load_run(args.primary)
    ovr = load_run(args.override) if args.override else {}
    tasks = sorted(set(prim) | set(ovr))

    rows = []
    for t in tasks:
        src = "rerun" if t in ovr else "orig"
        d, D = ovr.get(t) or prim[t]
        a = d.get("agent", {}) or {}
        pr = a.get("pytest_results", {}) or {}
        rows.append({
            "task": t, "source": src,
            "passed": pr.get("passed"), "total": pr.get("total"),
            "success_rate": a.get("success_rate"),
            "assistant_turns": (a.get("stream") or {}).get("assistant_turns"),
            "agent_seconds": a.get("agent_seconds"),
            "command_exit_codes": a.get("command_exit_codes"),
            "workspace_files": a.get("workspace_files"),
            "timed_out": a.get("timed_out"),
            "summary_dir": D,
        })

    done = [r for r in rows if r["success_rate"] is not None]
    n = len(rows)
    macro = sum(r["success_rate"] for r in done) / len(done) if done else 0.0
    tot_p = sum((r["passed"] or 0) for r in done)
    tot_c = sum((r["total"] or 0) for r in done)
    micro = tot_p / tot_c if tot_c else 0.0
    solved = sum(1 for r in done if (r["success_rate"] or 0) >= 1.0)
    nonzero = sum(1 for r in done if (r["success_rate"] or 0) > 0)

    os.makedirs(args.out, exist_ok=True)
    summary = {
        "primary_run": args.primary, "override_run": args.override,
        "denom": args.expect, "tasks_scored": len(done), "tasks_total": n,
        "from_rerun": sorted(t for t in tasks if t in ovr),
        "macro_mean_success_rate": round(macro, 6),
        "micro_pass_rate": round(micro, 6),
        "total_passed": tot_p, "total_cases": tot_c,
        "fully_solved_sr1": solved, "nonzero_tasks": nonzero,
        "rows": rows,
    }
    json.dump(summary, open(os.path.join(args.out, "merged_aggregate.json"), "w"), indent=2)
    with open(os.path.join(args.out, "per_task.tsv"), "w") as fh:
        fh.write("task\tsource\tpassed\ttotal\tsuccess_rate\tturns\tagent_seconds\tcmd_exit\ttimed_out\n")
        for r in sorted(rows, key=lambda x: (-(x["success_rate"] or 0), x["task"])):
            fh.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                r["task"], r["source"], r["passed"], r["total"], r["success_rate"],
                r["assistant_turns"], r["agent_seconds"], r["command_exit_codes"], r["timed_out"]))

    print("MERGED over %d tasks (scored=%d, denom=%d)" % (n, len(done), args.expect))
    print("  macro_mean_success_rate = %.4f" % macro)
    print("  micro_pass_rate         = %.4f (%d/%d)" % (micro, tot_p, tot_c))
    print("  fully_solved(sr=1.0)=%d  nonzero=%d  from_rerun=%d" % (solved, nonzero, len(summary["from_rerun"])))
    print("  from_rerun:", summary["from_rerun"])
    if n != args.expect:
        print("  WARNING: task count %d != expected %d" % (n, args.expect))


if __name__ == "__main__":
    main()
