#!/usr/bin/env python3
"""Post-hoc reducer for TB2.1 x Coder x terminus-2, run tb21_coder_t2_c32_0710064916.

Invoked manually because the launcher chain aborted under `set -e` when the operator
SIGTERMed a tb process that had HUNG AFTER COMPLETION, so finalize_scores never ran.

HARD CONSTRAINTS (orchestrator ruling, 2026-07-10):
  (a) No rc is faked. full.rc and tb.exit_status are read, never written.
  (b) Scores are recomputed ONLY from the 89 per-trial results.json files.
      tb21_strict_summary.json is read for REPORTING ONLY (its infra_fail is polluted
      by tb_rc=143) and never feeds a score.
  (c) tb_rc=143 and infra_fail=89 are carried verbatim into the output, annotated.
"""
import json, os, sys, glob, hashlib, datetime as dt

RUN_ROOT = sys.argv[1]
BATCH_DIR = sys.argv[2]
OUT_STEM = sys.argv[3]
FULL_RC_PATH = sys.argv[4]

def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

# ---- (b) recompute from the 89 per-trial results.json ONLY
trials = sorted(glob.glob(os.path.join(RUN_ROOT, "*", "*", "results.json")))
assert len(trials) == 89, "expected 89 per-trial results.json, found %d" % len(trials)
rows = []
for p in trials:
    j = json.load(open(p))
    rows.append({
        "task_id": j["task_id"],
        "is_resolved": j["is_resolved"] is True,
        "failure_mode": j["failure_mode"],
        "tok_in": int(j.get("total_input_tokens") or 0),
        "tok_out": int(j.get("total_output_tokens") or 0),
        "per_trial_results_sha256": sha256(p),
    })
task_ids = [r["task_id"] for r in rows]
assert len(set(task_ids)) == 89, "duplicate task_ids"
resolved = sorted(r["task_id"] for r in rows if r["is_resolved"])
total = len(rows)
accuracy = len(resolved) / total

# ---- cross-check against the run-level results.json (must agree; not used as source)
top = json.load(open(os.path.join(RUN_ROOT, "results.json")))
crosscheck = {
    "top_results_json_sha256": sha256(os.path.join(RUN_ROOT, "results.json")),
    "top_n_resolved": top["n_resolved"],
    "top_accuracy": top["accuracy"],
    "top_resolved_ids_match_per_trial": sorted(top["resolved_ids"]) == resolved,
    "accuracy_match": abs(top["accuracy"] - accuracy) < 1e-15,
}
meta = json.load(open(os.path.join(RUN_ROOT, "run_metadata.json")))

# ---- (c) carry the red numbers verbatim, from their own sources
full_rc = open(FULL_RC_PATH).read().strip()
tb_exit = open(os.path.join(BATCH_DIR, "tb.exit_status")).read().strip()
strict = json.load(open(os.path.join(BATCH_DIR, "tb21_strict_summary.json")))
sc = strict["counts"]

END_TIME = meta["end_time"]                       # 2026-07-10T08:58:08.646521+00:00
SIGTERM  = "2026-07-10T09:15:37+00:00"
d_end = dt.datetime.fromisoformat(END_TIME)
d_sig = dt.datetime.fromisoformat(SIGTERM)
delta = d_sig - d_end

hung = {
    "verdict": "HUNG_AFTER_COMPLETION",
    "tb_rc": 143,
    "tb_rc_meaning": "128+15 = SIGTERM, sent by the operator to a process that had already "
                     "written every artifact. NOT a measurement failure.",
    "run_end_time_utc": END_TIME,
    "operator_sigterm_utc": SIGTERM,
    "sigterm_after_end_time_seconds": int(delta.total_seconds()),
    "sigterm_after_end_time_hms": str(delta),
    "evidence_of_completion_before_sigterm": [
        "89/89 unique per-trial results.json present",
        "run-level results.json + run_metadata.json written (end_time set)",
        "docker ps -q = 0 and docker ps -aq = 0",
        "tb process: 62 threads, 61 in futex_wait_queue_me (incl. main), 0 children, 0.0% CPU",
        "one ESTAB socket to 100.100.104.140:30001 (leaked LLM keep-alive)",
        "root cause: threading._shutdown() joining non-daemon threads",
    ],
    "downstream_artifacts_of_this_rc__NOT_infra_failures": {
        "strict_summary.infra_fail": sc["infra_fail"],
        "strict_summary.clean_pass": sc["clean_pass"],
        "why": "tb21_strict_batch_summary.py: infra_fail = bool(missing_artifact or fatal_timeout "
               "or tb_rc not in (0, None)); clean = (tb_rc == 0 and ...). A non-zero tb_rc therefore "
               "marks ALL 89 rows infra_fail and zeroes clean_pass, regardless of the run.",
        "uncontaminated_components": {
            "missing_artifact": sc["missing_artifact"],
            "parse_error": sc["parse_error"],
            "fatal_timeout": sc["timeout"],
            "fatal_timeout_tasks": [r["task_id"] for r in strict["rows"] if r.get("timeout")],
        },
    },
    "verdict_rule": "v5: a non-zero tb_rc must be interpreted RELATIVE TO end_time. A non-zero rc "
                    "produced after end_time is a process-lifecycle artifact, not a measurement "
                    "failure, and must not trigger `blocked`.",
}

from collections import Counter
payload = {
    "schema_version": "tb21.qwen_official_scores.v1+posthoc_reducer.v1",
    "generated_by": "surface:16 post-hoc reducer (finalize_scores never ran; see hung_after_completion)",
    "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "score_is_green": False,
    "score_note": "Qwen lane is a single pass@1 compatibility probe; no official TB2.1 Qwen anchor is claimed.",
    "config": {
        "bench": "terminal_bench_2_1_full89",
        "agent": "terminus-2",
        "model": meta["model_name"],
        "run_id": meta["run_id"],
        "concurrency": meta["n_concurrent_trials"],
        "attempts": meta["n_attempts"],
        "dataset": meta["dataset_path"],
        "commit_hash": meta["commit_hash"],
        "base_url": "http://100.100.104.140:30001/v1",
        "sampling_params_sent": {"temperature": 0.0},
        "sampling_params_not_sent": ["top_p", "top_k", "seed", "repetition_penalty"],
    },
    "score": {"resolved": len(resolved), "total": total, "accuracy": accuracy},
    "single_pass_at_1": accuracy,
    "raw_reducer_accuracy": top["accuracy"],
    "calipers_agree": crosscheck["accuracy_match"],
    "resolved_ids": resolved,
    "failure_mode": dict(Counter(r["failure_mode"] for r in rows)),
    "token_sum": {"input": sum(r["tok_in"] for r in rows), "output": sum(r["tok_out"] for r in rows)},
    "source": {
        "reduced_from": "89 per-trial results.json (NOT tb21_strict_summary.json)",
        "per_trial_count": len(trials),
        "crosscheck_against_run_level_results_json": crosscheck,
    },
    "exit_status_verbatim": {"full_rc": full_rc, "tb_exit_status": tb_exit},
    "hung_after_completion": hung,
}

json.dump(payload, open(OUT_STEM + "_scores.json", "w"), indent=1, sort_keys=False)

with open(OUT_STEM + "_scores.yaml", "w") as f:
    f.write("# RED-BUT-HONEST. This run's exit code is non-zero and stays non-zero.\n")
    f.write("# tb_rc: 143 (SIGTERM), delivered %s AFTER end_time. See hung_after_completion.\n" % hung["sigterm_after_end_time_hms"])
    f.write("# strict_summary.infra_fail: %d and clean_pass: %d are DOWNSTREAM ARTIFACTS of that rc.\n\n" % (sc["infra_fail"], sc["clean_pass"]))
    def emit(o, ind=0):
        pad = "  " * ind
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, (dict, list)):
                    f.write("%s%s:\n" % (pad, k)); emit(v, ind + 1)
                else:
                    f.write("%s%s: %s\n" % (pad, k, json.dumps(v)))
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    f.write("%s-\n" % pad); emit(v, ind + 1)
                else:
                    f.write("%s- %s\n" % (pad, json.dumps(v)))
    emit(payload)

with open(OUT_STEM + "_scores.md", "w") as f:
    f.write("# TB2.1 x Qwen3-Coder-30B-A3B-Instruct x terminus-2 — scores (post-hoc reducer)\n\n")
    f.write("> **This run's exit code is 143 and is reported as 143.** `finalize_scores` never ran\n")
    f.write("> because the launcher chain aborted under `set -e`. Scores below were recomputed from\n")
    f.write("> the 89 per-trial `results.json` files, never from the tb_rc-contaminated strict summary.\n\n")
    f.write("| field | value |\n|---|---|\n")
    f.write("| resolved / total | **%d / %d** |\n" % (len(resolved), total))
    f.write("| accuracy = single_pass_at_1 | **%.16f** (= %.2f%%) |\n" % (accuracy, accuracy * 100))
    f.write("| raw reducer accuracy (run_metadata) | %.16f |\n" % top["accuracy"])
    f.write("| calipers agree | %s |\n" % crosscheck["accuracy_match"])
    f.write("| full.rc | `%s` |\n| tb.exit_status | `%s` |\n" % (full_rc, tb_exit))
    f.write("| strict_summary.infra_fail | `%d` — **downstream artifact of tb_rc=143, not an infra failure** |\n" % sc["infra_fail"])
    f.write("| strict_summary.clean_pass | `%d` — same artifact |\n" % sc["clean_pass"])
    f.write("| missing_artifact | `%d` (uncontaminated) |\n" % sc["missing_artifact"])
    f.write("| fatal_timeout | `%d` %s (task-level, v4(a): not `blocked`) |\n" % (
        sc["timeout"], [r["task_id"] for r in strict["rows"] if r.get("timeout")]))
    f.write("| run end_time | `%s` |\n| operator SIGTERM | `%s` (**+%s**) |\n" % (END_TIME, SIGTERM, hung["sigterm_after_end_time_hms"]))
    f.write("\n## HUNG_AFTER_COMPLETION\n\n")
    for e in hung["evidence_of_completion_before_sigterm"]:
        f.write("- %s\n" % e)
    f.write("\n**v5 rule:** %s\n" % hung["verdict_rule"])
    f.write("\n## resolved_ids (%d)\n\n" % len(resolved))
    for t in resolved:
        f.write("- `%s`\n" % t)
    f.write("\n## failure_mode\n\n")
    for k, v in sorted(Counter(r["failure_mode"] for r in rows).items()):
        f.write("- `%s`: %d\n" % (k, v))
    f.write("\n%s\n" % payload["score_note"])

print("resolved=%d total=%d accuracy=%.16f" % (len(resolved), total, accuracy))
print("crosscheck:", json.dumps(crosscheck))
print("full_rc=%r tb_exit=%r" % (full_rc, tb_exit))
print("carried verbatim: infra_fail=%d clean_pass=%d missing_artifact=%d fatal_timeout=%d" % (
    sc["infra_fail"], sc["clean_pass"], sc["missing_artifact"], sc["timeout"]))
print("wrote: %s_scores.{json,md,yaml}" % OUT_STEM)
