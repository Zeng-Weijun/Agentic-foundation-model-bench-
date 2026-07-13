#!/usr/bin/env python3
"""Independent recompute of RepoZero x Instruct-2507 headline from results.jsonl.
Blind reviewer A (Claude). Does NOT trust summary.json aggregates."""
import json, sys, collections, re

RZ = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z"
rows = []
with open(RZ + "/results.jsonl") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            print("PARSE_ERROR line", i, e)

print("=== INDEPENDENT RECOMPUTE (results.jsonl) ===")
print("total_rows                :", len(rows))
cases = [r.get("case") for r in rows]
print("unique_case_count         :", len(set(cases)))
dups = [c for c, n in collections.Counter(cases).items() if n > 1]
print("duplicate_cases           :", dups if dups else "NONE")

all_pass_true = [r for r in rows if r.get("all_pass") is True]
reward_one = [r for r in rows if r.get("reward") == 1]
print("all_pass==true  count     :", len(all_pass_true))
print("reward==1       count     :", len(reward_one))
# cross-consistency: does all_pass==true set == reward==1 set?
ap_set = set(r["case"] for r in all_pass_true)
rw_set = set(r["case"] for r in reward_one)
print("all_pass_set == reward_set:", ap_set == rw_set)
if ap_set != rw_set:
    print("  in all_pass not reward:", ap_set - rw_set)
    print("  in reward not all_pass:", rw_set - ap_set)

# reward!=0/1 anomalies
weird = [r for r in rows if r.get("reward") not in (0, 1)]
print("reward not in {0,1}       :", [(r["case"], r["reward"]) for r in weird] if weird else "NONE")

# passed>0 but not all_pass (partial) — sanity
partials = [r for r in rows if r.get("passed", 0) > 0 and not r.get("all_pass")]
print("partial(passed>0,!all_pass):", len(partials))

print()
print("=== DENOMINATOR / JUDGE-STATE BREAKDOWN ===")
# entry_exists / timed_out / agent_rc
no_entry = [r for r in rows if not r.get("entry_exists", True)]
timed_out = [r for r in rows if r.get("timed_out")]
print("entry_exists==false       :", len(no_entry))
print("timed_out==true           :", len(timed_out))
# judged vs unjudged: look for a 'judged' style flag or total==0
total_zero = [r for r in rows if r.get("total", 0) == 0]
print("total==0 (no samples/crash):", len(total_zero), [r["case"] for r in total_zero])
# any error/skip markers
keys = set()
for r in rows:
    keys.update(r.keys())
print("all keys present in rows  :", sorted(keys))

print()
print("=== RATE COMPUTATIONS ===")
print("51/400 (10s, cases_total) :", round(51/400, 6))
print("recomputed all_pass/400   :", round(len(all_pass_true)/400, 6))
print("recomputed all_pass/392   :", round(len(all_pass_true)/392, 6))

print()
print("=== ALL_PASS=TRUE CASES (the 51) ===")
for r in sorted(all_pass_true, key=lambda x: x["case"]):
    print(f"  {r['case']:<28} passed={r.get('passed')}/{r.get('total')} rc={r.get('agent_rc')} turns={r.get('assistant_turns')} t={r.get('seconds')}")

print()
print("=== BY-PACKAGE all_pass rate ===")
by_pkg = collections.defaultdict(lambda: [0, 0])
for r in rows:
    pkg = r["case"].split("/")[0]
    by_pkg[pkg][1] += 1
    if r.get("all_pass"):
        by_pkg[pkg][0] += 1
for pkg in sorted(by_pkg, key=lambda p: (-by_pkg[p][0]/by_pkg[p][1], p)):
    passed, tot = by_pkg[pkg]
    print(f"  {pkg:<20} {passed}/{tot} = {passed/tot:.3f}")
