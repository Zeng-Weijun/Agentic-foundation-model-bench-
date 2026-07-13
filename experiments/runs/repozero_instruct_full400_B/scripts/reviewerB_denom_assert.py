#!/usr/bin/env python3
"""Reviewer B: final denominator + reward-set assertions (no trust in summary.json aggregates)."""
import ast, json, collections
from pathlib import Path

RZ_ROOT = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero")
RUN = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z")

# 1. official valid_ids (denominator ground truth)
tree = ast.parse((RZ_ROOT / "run_py2js_docker" / "run_all_docker.py").read_text())
valid_ids = None
excluded_ids = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "valid_ids":
                valid_ids = ast.literal_eval(node.value)
            if isinstance(t, ast.Name) and t.id == "excluded_ids":
                excluded_ids = ast.literal_eval(node.value)
valid_set = set(valid_ids)
print("OFFICIAL valid_ids count:", len(valid_ids), "unique:", len(valid_set))
print("OFFICIAL excluded_ids:", excluded_ids)

rows = []
with (RUN / "results.jsonl").open() as f:
    for line in f:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

run_cases = [r["case"] for r in rows]
run_set = set(run_cases)
print("\nRUN results.jsonl: total_rows =", len(rows), "unique_cases =", len(run_set))
dups = [c for c, n in collections.Counter(run_cases).items() if n > 1]
print("duplicate cases:", dups if dups else "NONE")

print("\nDENOM SET-EQUALITY CHECK:")
print("run_set == official valid_set :", run_set == valid_set)
print("in run but not in official    :", sorted(run_set - valid_set))
print("in official but missing in run:", sorted(valid_set - run_set))
if excluded_ids:
    included_excluded = run_set & set(excluded_ids)
    print("excluded_ids present in run (should be 0, or included=conservative):", sorted(included_excluded))

all_pass_true = [r for r in rows if r.get("all_pass") is True]
reward_one = [r for r in rows if r.get("reward") == 1]
ap_set = {r["case"] for r in all_pass_true}
rw_set = {r["case"] for r in reward_one}
weird_reward = [(r["case"], r.get("reward")) for r in rows if r.get("reward") not in (0, 1)]

print("\nSCORE ASSERTIONS:")
print("all_pass==True count :", len(all_pass_true))
print("reward==1     count  :", len(reward_one))
print("all_pass_set == reward_set:", ap_set == rw_set)
print("reward values outside {0,1}:", weird_reward if weird_reward else "NONE")
print("all_pass rate = %d/%d = %.4f" % (len(all_pass_true), len(rows), len(all_pass_true)/len(rows)))

errors = [r for r in rows if "error" in r]
print("\nrows with error (judge crash) :", len(errors), sorted(r["case"] for r in errors))
print("cases_judged (no error key)   :", len(rows) - len(errors))

# node18 vs node20 known flips (from this review's own remote container re-execution)
node18_flips_confirmed = ["base58/test3.py", "base58/test6.py", "bencoder/test3.py", "bidict/test3.py", "bidict/test5.py"]
timeout_5s_genuine_flips = ["deepdiff/test1.py", "networkx/test1.py"]
crash_recovered_true_pass = ["rsa/test5.py"]  # was counted as fail (reward=0) due to driver crash, TRUE verdict = pass 20/20

print("\nSTRICT-OFFICIAL SENSITIVITY (from this review's own remote re-execution):")
print("  node18 flips (pass->fail, all 5/5 confirmed independently)      :", node18_flips_confirmed)
print("  5s-timeout genuine flips (pass->fail, contention-controlled)     :", timeout_5s_genuine_flips)
print("  strict(node18 + 5s) implied headline = 51 - 5 - 2 = 44/400 = %.4f (estimate, non-overlapping sets, not exhaustively re-verified in combination)" % (44/400))
print("  crash-row recovered TRUE pass (currently counted as fail)        :", crash_recovered_true_pass, "-> partially offsets in the other direction")
