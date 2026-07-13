#!/usr/bin/env python3
"""INDEPENDENT re-judge (blind reviewer A). Own harness, not the driver's eval_case.
Starts a hermetic (--network none) container from the official image, mounts the
dataset lib + the case's stored workspace_output, then for EVERY testcase sample
runs the oracle executable and `node <entry>.mjs` and compares normalized stdout
lines. Records passed/total, my all_pass verdict, and per-sample max latency to
assess 10s-vs-5s timeout sensitivity."""
import subprocess, json, os, time, traceback
from pathlib import Path
RZ_RUN = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z")
RZ_ROOT = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero")
IMAGE = "ghcr.io/jessezzzzz/repoarena-new:latest"
OUT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/reviewerA_rejudge_report.txt"
OUTJSON = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/reviewerA_rejudge.json"

buf = []
def w(*a): buf.append(" ".join(str(x) for x in a))

def normalized_lines(text):
    return ["".join(line.split()) for line in text.strip().splitlines() if line.strip()]

def load_samples(lib, case):
    f = RZ_ROOT / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    rows = []
    for line in open(f, encoding="utf-8"):
        if not line.strip():
            continue
        o = json.loads(line)
        if o.get("filename") == case:
            o.pop("filename", None); rows.append(o)
    return rows

def args_from(params):
    a = []
    for k, v in params.items():
        a += [f"--{k}", str(v)]
    return a

env = dict(os.environ)
for k in ("http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY"):
    env.pop(k, None)

def dexec(argv, timeout):
    t0 = time.time()
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout or "", p.stderr or "", time.time() - t0
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")), "TIMEOUT", time.time() - t0
    except Exception as e:
        return -2, "", repr(e), time.time() - t0

# results.jsonl expected verdicts
expected = {}
for line in open(RZ_RUN / "results.jsonl"):
    if line.strip():
        r = json.loads(line); expected[r["case"]] = r

CASES_TRUE = ["base58/test6.py","whoosh/test1.py","schedule/test1.py","fractions/test14.py",
              "boltons/test1.py","networkx/test1.py","rsa/test16.py","bidict/test2.py"]
CASES_FALSE = ["bech32/test1.py","base58/test1.py","idna/test1.py","yaml/test1.py"]

def rejudge(case, per_timeout=10):
    lib, fn = case.split("/")
    stem = fn[:-3]
    exe = stem + "_executable"; entry = stem + ".mjs"; pkg = stem + "_pkg"
    cont_pkg = f"/workspace/output/packages/{lib}/{pkg}"
    samples = load_samples(lib, case)
    casedir = RZ_RUN / "cases" / f"{lib}-{stem}"
    wsout = casedir / "workspace_output"
    dataset = RZ_ROOT / "Py2JS" / "dataset" / lib
    name = f"reviewerA-rj-{lib}-{stem}-{int(time.time()*1000)}"
    res = {"case": case, "samples": len(samples), "expected_all_pass": expected.get(case,{}).get("all_pass"),
           "expected_passed": expected.get(case,{}).get("passed"), "expected_total": expected.get(case,{}).get("total")}
    if not wsout.exists():
        res["error"] = "workspace_output MISSING"; return res
    rc,o,e,_ = dexec(["docker","run","-d","--rm","--network","none","--name",name,
        "-v",f"{dataset}:/workspace/dataset:ro","-v",f"{wsout}:/workspace/output:ro",
        IMAGE,"tail","-f","/dev/null"], 90)
    if rc != 0:
        res["error"] = "container_start_failed:" + e[:200]; return res
    try:
        rce,_,_,_ = dexec(["docker","exec",name,"test","-f",f"{cont_pkg}/{entry}"], 30)
        res["entry_exists"] = (rce == 0)
        passed10 = passed5 = 0
        max_lat = 0.0; flip_5s = 0; mism = []
        for params in samples:
            a = args_from(params)
            prc,po,pe,pt = dexec(["docker","exec",name,f"/workspace/dataset/{exe}"]+a, per_timeout+1)
            jrc,jo,je,jt = dexec(["docker","exec","-w",cont_pkg,name,"node",entry]+a, per_timeout+1)
            match = normalized_lines(po) == normalized_lines(jo)
            lat = max(pt, jt); max_lat = max(max_lat, lat)
            ok10 = (prc==0 and pt<=10 and jrc==0 and jt<=10 and match)
            ok5  = (prc==0 and pt<=5  and jrc==0 and jt<=5  and match)
            if ok10: passed10 += 1
            if ok5: passed5 += 1
            if ok10 and not ok5: flip_5s += 1
            if not ok10 and len(mism) < 3:
                mism.append({"args":a[:6],"oracle_rc":prc,"js_rc":jrc,"match":match,
                             "oracle_head":po[:120],"js_head":jo[:120],"js_err":je[:120]})
        res.update({"my_passed@10": passed10, "my_passed@5": passed5, "total": len(samples),
                    "my_all_pass@10": passed10==len(samples) and len(samples)>0,
                    "my_all_pass@5": passed5==len(samples) and len(samples)>0,
                    "max_sample_latency_s": round(max_lat,2), "samples_flip_at_5s": flip_5s,
                    "mismatch_examples": mism})
    finally:
        subprocess.run(["docker","rm","-f",name], capture_output=True, env=env)
    return res

allres = []
try:
    w("=== INDEPENDENT REJUDGE (reviewer A own harness, --network none) ===")
    w("image", IMAGE)
    for case in CASES_TRUE + CASES_FALSE:
        try:
            r = rejudge(case)
        except Exception:
            r = {"case": case, "error": traceback.format_exc()[-500:]}
        allres.append(r)
        agree = (r.get("my_all_pass@10") == r.get("expected_all_pass"))
        w(f"\n{case}: expected all_pass={r.get('expected_all_pass')} (passed {r.get('expected_passed')}/{r.get('expected_total')})")
        w(f"   MINE: all_pass@10={r.get('my_all_pass@10')} passed@10={r.get('my_passed@10')}/{r.get('total')} "
          f"all_pass@5={r.get('my_all_pass@5')} passed@5={r.get('my_passed@5')} maxlat={r.get('max_sample_latency_s')}s "
          f"flip5s={r.get('samples_flip_at_5s')} entry_exists={r.get('entry_exists')}")
        w(f"   AGREE_WITH_RESULTS_JSONL: {agree}   err={r.get('error')}")
        if r.get("mismatch_examples"):
            for m in r["mismatch_examples"]:
                w("     mism:", json.dumps(m))
    # summary
    agree_n = sum(1 for r in allres if r.get("my_all_pass@10")==r.get("expected_all_pass") and not r.get("error"))
    w(f"\n=== AGREEMENT: {agree_n}/{len(allres)} cases my@10 verdict == results.jsonl ===")
    flips = [r["case"] for r in allres if r.get("my_all_pass@10") and not r.get("my_all_pass@5")]
    w("cases that would FLIP true->false at 5s:", flips if flips else "NONE")
except Exception:
    w("REJUDGE_TOP_ERROR:\n" + traceback.format_exc())
finally:
    Path(OUT).write_text("\n".join(buf) + "\n")
    Path(OUTJSON).write_text(json.dumps(allres, indent=2) + "\n")
    print("REJUDGE_WROTE", len(allres), "cases")
