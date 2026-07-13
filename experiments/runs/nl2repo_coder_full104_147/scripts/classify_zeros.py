#!/usr/bin/env python3
"""Full fake-zero taxonomy over the 104 NL2Repo tasks (merged: rerun overrides primary).

For every task pick the authoritative summary (rerun if present, else primary, else ISOLATED),
then classify each zero/absent task:
  ISOLATED_infra      : no summary at all (transport/manifest defect, driver crash) -> not model-0
  ISOLATED_judging    : agent ran but scoring hung/timed out (no summary) -> not model-0
  WHEELHOUSE_GAP      : agent ran, pip install failed on a MISSING dep offline -> install-infra fake-0
  MODEL_BUILD_FAIL    : agent ran, pip install failed on the model's own source/build -> REAL model-0
  MODEL_TEST_FAIL     : agent ran, install ok (or PYTHONPATH), pytest ran, 0/total passed -> REAL model-0
Also reports the honest macro over the VALID (non-isolated) tasks and over all 104.
"""
import json, glob, os, re, sys

PA = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA"
PRIMARY = open(PA + "/runs/LATEST_FULL104_RUN_ROOT.txt").read().strip()
OVERRIDE = open(PA + "/runs/LATEST_RERUN_FIXED.txt").read().strip()
MAN = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/nl2repo/nl2repo_transport_manifest.jsonl"
ALL_TASKS = [json.loads(l)["task"] for l in open(MAN) if l.strip()]
STDLIB_HANG = {}

WHEEL_GAP_PAT = re.compile(r"No matching distribution found for|Could not find a version that satisfies|No matching distribution", re.I)


def find_summary(task):
    for root in (OVERRIDE, PRIMARY):
        for d in sorted(glob.glob(os.path.join(root, task + "_agent_*"))):
            sp = os.path.join(d, "summary.json")
            if os.path.exists(sp):
                return sp, d, ("rerun" if root == OVERRIDE else "orig")
    return None, None, None


def pip_install_log(D):
    for c in sorted(glob.glob(os.path.join(D, "agent", "cmd_*.txt"))):
        head = open(c, errors="replace").read(4000)
        if "pip install" in head.lower():
            return open(c, errors="replace").read()
    return ""


rows = []
for t in ALL_TASKS:
    sp, D, src = find_summary(t)
    if sp is None:
        rows.append({"task": t, "sr": None, "cls": "ISOLATED_infra_or_judging", "src": "none"})
        continue
    d = json.load(open(sp)); a = d.get("agent", {}) or {}; pr = a.get("pytest_results", {}) or {}
    sr = a.get("success_rate"); turns = (a.get("stream") or {}).get("assistant_turns")
    ce = a.get("command_exit_codes") or []
    ts = d.get("test_shell", [])
    inst_rc = None
    for i, c in enumerate(ts):
        if "pip install" in c.lower() and i < len(ce):
            inst_rc = ce[i]
    cls = "OK_nonzero" if (sr or 0) > 0 else "?"
    if (sr or 0) == 0:
        if not turns:
            cls = "ISOLATED_argv_overflow(uncorrected)"
        elif inst_rc not in (0, None):
            log = pip_install_log(D)
            cls = "WHEELHOUSE_GAP(install-infra fake-0)" if WHEEL_GAP_PAT.search(log) else "MODEL_BUILD_FAIL(real-0)"
        else:
            cls = "MODEL_TEST_FAIL(real-0)"
    rows.append({"task": t, "sr": sr, "turns": turns, "inst_rc": inst_rc, "cls": cls, "src": src,
                 "passed": pr.get("passed"), "total": pr.get("total")})

valid = [r for r in rows if r["sr"] is not None]
isolated = [r for r in rows if r["sr"] is None]
macro_valid = sum(r["sr"] for r in valid) / len(valid) if valid else 0.0
macro_104_iso0 = sum((r["sr"] or 0) for r in rows) / len(rows)
tp = sum((r.get("passed") or 0) for r in valid); tc = sum((r.get("total") or 0) for r in valid)
micro = tp / tc if tc else 0.0

from collections import Counter
cc = Counter(r["cls"] for r in rows)
print("=== TAXONOMY ===")
for k, v in sorted(cc.items(), key=lambda x: -x[1]):
    print("  %-42s %d" % (k, v))
print()
print("valid(scored) tasks:", len(valid), "| isolated:", len(isolated), "| total denom:", len(rows))
print("ISOLATED tasks:", [r["task"] for r in isolated])
model_true0 = [r["task"] for r in rows if "real-0" in r["cls"]]
wheel_gap = [r["task"] for r in rows if "WHEELHOUSE_GAP" in r["cls"]]
print("model_true_0 count:", len(model_true0))
print("wheelhouse_gap(install-infra fake-0) count:", len(wheel_gap), wheel_gap)
print()
print("macro_mean_success_rate over VALID(%d) = %.4f" % (len(valid), macro_valid))
print("macro over ALL 104 (isolated=0)        = %.4f" % macro_104_iso0)
print("micro_pass_rate (valid)                = %.4f (%d/%d)" % (micro, tp, tc))
print()
print("=== all zeros / isolated detail ===")
for r in sorted(rows, key=lambda x: (x["sr"] is not None, x["sr"] or 0)):
    if (r["sr"] or 0) == 0:
        print("  %-24s sr=%-9s turns=%-5s inst_rc=%-5s %s [%s]" % (
            r["task"], r["sr"], r.get("turns"), r.get("inst_rc"), r["cls"], r["src"]))

json.dump({"rows": rows, "macro_valid": macro_valid, "macro_104_iso0": macro_104_iso0,
           "micro_valid": micro, "valid": len(valid), "isolated": len(isolated),
           "isolated_tasks": [r["task"] for r in isolated],
           "model_true0": model_true0, "wheelhouse_gap": wheel_gap},
          open(PA + "/runs/nl2repo_merged_104/taxonomy.json", "w"), indent=2)
print("\nwrote taxonomy.json")
