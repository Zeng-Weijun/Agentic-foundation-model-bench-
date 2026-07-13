#!/usr/bin/env python3
"""Reviewer B: official-5s-timeout re-judge, restricted to the 51 all_pass=true
cases in the committed 10s run (the ONLY cases that can possibly flip to fail
when tightening 10s->5s, per this repo's own conservative_rule precedent in
rejudge_official5s.py). Any flip is re-verified SERIALLY (contention-free) at
both 5s and 10s before being called a genuine official-5s penalty, exactly
matching the methodology already used+validated on the sibling Coder run.
"""
import importlib.util, json, subprocess, time
import concurrent.futures as cf
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "instruct2507_full400_20260713T151209Z"
rz_root = Path(rz.DEFAULT_RZ_ROOT)
env = rz.docker_env()
OUT_DIR = RUN / "reviewerB_5s_judges"
OUT_DIR.mkdir(exist_ok=True)

baseline = {}
with (RUN / "results.jsonl").open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        baseline[o["case"]] = o

pass_cases = sorted([c for c, o in baseline.items() if o.get("all_pass") is True])
print(f"all_pass=true cases in committed 10s run: {len(pass_cases)}", flush=True)


def eval_one(case, eval_timeout, cname):
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    out_dir = OUT_DIR / f"{slug}_{eval_timeout}s_{cname[-4:]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        rz.start_container(cname, rz.DEFAULT_IMAGE, dataset_dir, output_root,
                           rz.DEFAULT_QWEN_ROOT, rz.DEFAULT_BASE_URL, rz.DEFAULT_MODEL, env)
        res = rz.eval_case(cname, rz_root, case, out_dir, env, eval_timeout)
        return {"all_pass": bool(res.get("all_pass")), "passed": res.get("passed"), "total": res.get("total"), "timeout": False}
    except subprocess.TimeoutExpired as e:
        return {"all_pass": False, "timeout": True, "error": str(e)[:200]}
    except Exception as e:
        return {"all_pass": False, "timeout": False, "error": repr(e)[:200]}
    finally:
        rz.run(["docker", "rm", "-f", cname], env=env)


t0 = time.time()
p1 = {}
def work(case):
    slug = case.replace("/", "-").replace(".py", "")
    return case, eval_one(case, 5, f"rjB5-{slug}"[:120])

with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for case, rec in ex.map(work, pass_cases):
        p1[case] = rec
        print(f"[5s] {case}: all_pass={rec['all_pass']} passed={rec.get('passed')}/{rec.get('total')}", flush=True)

flips = [c for c in pass_cases if not p1[c]["all_pass"]]
print(f"\nflips (10s pass -> 5s-phase1 fail): {len(flips)}: {flips}", flush=True)

serial = {}
for case in flips:
    slug = case.replace("/", "-").replace(".py", "")
    r5 = eval_one(case, 5, f"rjB5s-{slug}"[:120])
    r10 = eval_one(case, 10, f"rjB10s-{slug}"[:120])
    serial[case] = {"serial_5s": r5, "serial_10s": r10}
    print(f"[serial-verify] {case}: 5s={r5['all_pass']} 10s={r10['all_pass']}", flush=True)

genuine = [c for c in flips if not serial[c]["serial_5s"]["all_pass"] and serial[c]["serial_10s"]["all_pass"]]
contention = [c for c in flips if serial[c]["serial_5s"]["all_pass"]]
n5_final = len(pass_cases) - len(genuine)

print("\n===== 5s-TIMEOUT SPOT-CHECK SUMMARY (restricted to the 51 committed passes) =====")
print(f"committed all_pass@10s: {len(pass_cases)}/400 = {round(100*len(pass_cases)/400,2)}%")
print(f"genuine 5s-timeout flips (would fail official 5s): {len(genuine)}: {genuine}")
print(f"contention artifacts (still pass serial 5s): {len(contention)}: {contention}")
print(f"implied official-5s headline: {n5_final}/400 = {round(100*n5_final/400,2)}%  (delta={n5_final-len(pass_cases)})")

out = {"pass_cases_10s": pass_cases, "phase1_5s": p1, "flips": flips, "serial": serial,
       "genuine_5s_flips": genuine, "contention_artifacts": contention,
       "implied_5s_headline": f"{n5_final}/400", "elapsed_s": round(time.time()-t0, 1)}
(RUN / "reviewerB_5s_check.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("wrote", RUN / "reviewerB_5s_check.json")
