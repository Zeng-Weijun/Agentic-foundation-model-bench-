#!/usr/bin/env python3
"""Independent Blind Reviewer B re-judge of 5 cases from
instruct2507_full400_20260713T151209Z. Uses the SAME start_container +
eval_case plumbing (already independently source-read and verified to
require BOTH oracle_rc==0 AND js_rc==0 AND normalized-line stdout equality),
but is a fresh invocation against the pre-existing agent .mjs artifacts
(no re-generation, no serving dependency, fully deterministic).
"""
import importlib.util, json, sys
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "instruct2507_full400_20260713T151209Z"
rz_root = Path(rz.DEFAULT_RZ_ROOT)
env = rz.docker_env()

# 3x claimed all_pass=true, 2x claimed all_pass=false (incl a NEAR-MISS to test discriminative power)
cases = [
    "boltons/test1.py",   # claimed all_pass=true 60/60
    "base58/test3.py",    # claimed all_pass=true 57/57
    "bidict/test12.py",   # claimed all_pass=true 60/60
    "base58/test1.py",    # claimed all_pass=false 4/60
    "bidict/test19.py",   # claimed all_pass=false 57/60 (near-miss discriminative test)
]

baseline = {}
with (RUN / "results.jsonl").open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        baseline[o["case"]] = o

out = []
for case in cases:
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    name = f"reviewerB-{slug}"
    b = baseline[case]
    print(f"\n=== {case} (baseline: all_pass={b.get('all_pass')} passed={b.get('passed')}/{b.get('total')}) ===", flush=True)
    rec = {"case": case, "baseline_all_pass": b.get("all_pass"), "baseline_passed": b.get("passed"), "baseline_total": b.get("total")}
    try:
        rz.start_container(name, rz.DEFAULT_IMAGE, dataset_dir, output_root,
                           rz.DEFAULT_QWEN_ROOT, rz.DEFAULT_BASE_URL, rz.DEFAULT_MODEL, env)
        (run_root / "reviewerB_judge").mkdir(parents=True, exist_ok=True)
        res = rz.eval_case(name, rz_root, case, run_root / "reviewerB_judge", env, eval_timeout=10)
        rec.update({"rejudge_all_pass": res.get("all_pass"), "rejudge_passed": res.get("passed"),
                    "rejudge_total": res.get("total"), "reward": res.get("reward"),
                    "fail_examples_sample": res.get("fail_examples", [])[:1]})
        match = (rec["rejudge_all_pass"] == rec["baseline_all_pass"]) and (rec["rejudge_passed"] == rec["baseline_passed"])
        rec["MATCHES_BASELINE"] = match
        print(json.dumps(rec, ensure_ascii=False, indent=2), flush=True)
    except Exception as e:
        rec.update({"error": repr(e)})
        print("ERROR:", e, flush=True)
    finally:
        rz.run(["docker", "rm", "-f", name], env=env)
    out.append(rec)

print("\n\n===== SUMMARY =====")
for r in out:
    print(r["case"], "MATCH=" , r.get("MATCHES_BASELINE"), "baseline=", r.get("baseline_all_pass"), "rejudge=", r.get("rejudge_all_pass"))

n_match = sum(1 for r in out if r.get("MATCHES_BASELINE"))
print(f"\n{n_match}/{len(out)} cases match baseline verdict")
(RUN / "reviewerB_rejudge5.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("wrote", RUN / "reviewerB_rejudge5.json")
