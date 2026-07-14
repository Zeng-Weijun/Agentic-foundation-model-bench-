#!/usr/bin/env python3
"""Compute Coder HONEST macro/micro after base-image leak-floor subtraction.

honest_passed(task)  = max(recorded_passed - leak_floor_passed, 0)   [task's rule]
honest_sr(task)      = min(honest_passed / total, 1)
denominator          = 95 model-valid (= 101 scored tasks minus the 6 install-infra fake-0),
                       identical to the headline 0.1555 口径.
"""
import json, csv, os
from pathlib import Path

M = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/nl2repo_merged_104")
LF = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/leakfloor_coder")
head = json.load(open(M / "headline.json"))
install_infra = set(head["install_infra_fake0"])   # 6 excluded from the 95
isolated = set(head["isolated_infra_judging"])      # 3 not in tsv anyway

rows = {}
with open(M / "per_task.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        rows[r["task"]] = {"source": r["source"], "passed": int(r["passed"]),
                            "total": int(r["total"]), "sr": float(r["success_rate"])}

# the 95 model-valid = all scored tasks except the 6 install-infra fake-0
model_valid = [t for t in rows if t not in install_infra]
assert len(model_valid) == head["n_model_valid"], (len(model_valid), head["n_model_valid"])

floors = {}
for p in LF.glob("*/leakfloor.json"):
    d = json.load(open(p))
    floors[d["task"]] = d

# sanity: reproduce recorded macro/micro over the 95
rec_sr_sum = sum(rows[t]["sr"] for t in model_valid)
rec_pass = sum(rows[t]["passed"] for t in model_valid)
rec_tot = sum(rows[t]["total"] for t in model_valid)
print(f"[sanity] recorded macro_95 = {rec_sr_sum/95:.6f} (headline 0.155454)  micro_95 = {rec_pass}/{rec_tot} = {rec_pass/rec_tot:.6f} (headline 0.084365)")

# honest
nonzero = sorted([t for t in model_valid if rows[t]["passed"] > 0], key=lambda t: -rows[t]["sr"])
missing = [t for t in nonzero if t not in floors]
print(f"[coverage] nonzero={len(nonzero)}  floors_measured={len(floors)}  missing_floor={len(missing)} {missing if missing else ''}")

hon_sr_sum = 0.0
hon_pass = 0
leaked, genuine, partial = [], [], []
print("\n%-26s %-6s %5s %5s %8s %6s %8s  %s" % ("task","src","pass","tot","rec_sr","floor","hon_sr","verdict"))
for t in nonzero:
    rec_p, tot, sr = rows[t]["passed"], rows[t]["total"], rows[t]["sr"]
    if t in floors:
        fl = floors[t]["leak_floor_passed"]
        hp = max(rec_p - fl, 0)
        hsr = min(hp / tot, 1.0) if tot else 0.0
        # verdict
        if fl == 0:
            v = "genuine(no-leak)"; genuine.append(t)
        elif hp == 0:
            v = "LEAK-ZEROED"; leaked.append(t)
        else:
            v = "partial-leak"; partial.append(t)
    else:
        fl = "?"; hp = rec_p; hsr = sr; v = "UNMEASURED(kept=rec)"
    hon_sr_sum += hsr
    hon_pass += hp
    fls = f"{fl}" if fl != "?" else "?"
    print("%-26s %-6s %5d %5d %8.4f %6s %8.4f  %s" % (t, rows[t]["source"], rec_p, tot, sr, fls, hsr, v))

# zero-sr model-valid tasks contribute 0 (unchanged)
strict_macro = hon_sr_sum / 95
# generous bound: credit the "shadow" leak-zeroed tasks (rec<floor) at their recorded sr
shadow = [t for t in leaked if floors[t]["leak_floor_passed"] > rows[t]["passed"]]   # rec<floor
exact  = [t for t in leaked if floors[t]["leak_floor_passed"] == rows[t]["passed"]]  # rec==floor (pure)
gen_add = sum(rows[t]["sr"] for t in shadow) / 95
generous_macro = strict_macro + gen_add
print(f"\nHONEST macro_95 (STRICT, rec-floor)   = {strict_macro:.6f}   (recorded 0.155454)   delta = {strict_macro-0.155454:+.6f}")
print(f"HONEST micro_95 (STRICT)              = {hon_pass}/{rec_tot} = {hon_pass/rec_tot:.6f}   (recorded 0.084365)")
print(f"HONEST macro_95 (GENEROUS, credit {len(shadow)} shadow) = {generous_macro:.6f}")
print(f"pure-leak exact-match rec==floor ({len(exact)}): {sorted(exact)}")
print(f"shadow rec<floor ({len(shadow)}): {sorted(shadow)}")
print(f"partial-leak floor<rec ({len(partial)}): {sorted(partial)}")
print(f"genuine no-leak floor==0 ({len(genuine)}): {len(genuine)} tasks")

# emit markdown table (only leak-affected tasks) + json
leakrows = sorted([t for t in nonzero if floors[t]["leak_floor_passed"] > 0], key=lambda t: -rows[t]["sr"])
md = ["| task | src | recorded pass/total (sr) | leak_floor pass/total | honest sr | class |",
      "|---|---|---|---|---|---|"]
for t in leakrows:
    rp, tot, sr = rows[t]["passed"], rows[t]["total"], rows[t]["sr"]
    fl = floors[t]["leak_floor_passed"]; hp = max(rp-fl,0); hsr = min(hp/tot,1.0)
    cls = "PURE-LEAK (rec==floor)" if fl==rp else ("shadow-zeroed (rec<floor)" if fl>rp else "partial (floor<rec)")
    md.append(f"| {t} | {rows[t]['source']} | {rp}/{tot} ({sr:.4f}) | {fl}/{tot} ({fl/tot:.4f}) | {hsr:.4f} | {cls} |")
Path(LF/"leak_table.md").write_text("\n".join(md)+"\n")
out = {"recorded_macro_95":0.155454,"recorded_micro_95":0.084365,
       "honest_macro_95_strict":round(strict_macro,6),"honest_micro_95_strict":round(hon_pass/rec_tot,6),
       "honest_macro_95_generous":round(generous_macro,6),
       "delta_strict":round(strict_macro-0.155454,6),
       "pure_leak_exact":sorted(exact),"shadow_zeroed":sorted(shadow),"partial_leak":sorted(partial),
       "n_genuine_no_leak":len(genuine),"n_nonzero":len(nonzero),"n_floors":len(floors),
       "leak_floors":{t:{"recorded_passed":rows[t]["passed"],"total":rows[t]["total"],
                         "leak_floor_passed":floors[t]["leak_floor_passed"],
                         "recorded_sr":rows[t]["sr"],
                         "honest_sr":round(min(max(rows[t]["passed"]-floors[t]["leak_floor_passed"],0)/rows[t]["total"],1.0),6)}
                      for t in leakrows}}
Path(LF/"honest_summary.json").write_text(json.dumps(out,indent=2)+"\n")
print(f"\nWROTE {LF}/leak_table.md and honest_summary.json")
