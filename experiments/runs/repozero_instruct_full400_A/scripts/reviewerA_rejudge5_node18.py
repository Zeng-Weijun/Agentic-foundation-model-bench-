#!/usr/bin/env python3
"""Re-judge the 5 node20-dependent all_pass cases under the RepoZero image's
OFFICIAL node 18 (/usr/bin/node) to get the exact strict-node18 headline."""
import subprocess, json, os, time
from pathlib import Path
RZ_RUN = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z")
RZ_ROOT = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero")
IMAGE = "ghcr.io/jessezzzzz/repoarena-new:latest"
OUT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/reviewerA_rejudge5_node18.txt"
CASES = ["base58/test3.py","base58/test6.py","bencoder/test3.py","bidict/test3.py","bidict/test5.py"]
buf=[]
def w(*a): buf.append(" ".join(str(x) for x in a))
env=dict(os.environ)
for k in ("http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY"): env.pop(k,None)
def run(argv,t=12):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=t,env=env); return p.returncode,p.stdout or "",p.stderr or ""
    except Exception as e: return -1,"",repr(e)
def nlines(t): return ["".join(l.split()) for l in t.strip().splitlines() if l.strip()]
def samples_for(lib,case):
    f=RZ_ROOT/"Py2JS"/"testcases_60"/f"testcase_{lib}.jsonl"
    return [json.loads(l) for l in open(f) if l.strip() and json.loads(l).get("filename")==case]

for case in CASES:
    lib,fn=case.split("/"); stem=fn[:-3]
    wsout=RZ_RUN/"cases"/f"{lib}-{stem}"/"workspace_output"
    dataset=RZ_ROOT/"Py2JS"/"dataset"/lib
    cont_pkg=f"/workspace/output/packages/{lib}/{stem}_pkg"
    name=f"reviewerA-n18-{lib}-{stem}-{int(time.time()*1000)}"
    samples=samples_for(lib,case)
    rc,o,e=run(["docker","run","-d","--rm","--network","none","--name",name,
        "-v",f"{dataset}:/workspace/dataset:ro","-v",f"{wsout}:/workspace/output:ro",
        IMAGE,"tail","-f","/dev/null"],60)
    if rc!=0:
        w(case,"CONTAINER_FAIL",e[:150]); continue
    try:
        p18=0; p20img=0; first_err=""
        # show the helper .js head to see export vs module.exports
        rcj,oj,ej=run(["docker","exec",name,"sh","-c",f"head -3 {cont_pkg}/*.js 2>/dev/null"])
        for prm in samples:
            a=[]
            for k,v in prm.items():
                if k!="filename": a+=[f"--{k}",str(v)]
            prc,po,pe=run(["docker","exec",name,f"/workspace/dataset/{stem}_executable"]+a)
            j18rc,j18o,j18e=run(["docker","exec","-w",cont_pkg,name,"/usr/bin/node",f"{stem}.mjs"]+a)
            if prc==0 and j18rc==0 and nlines(po)==nlines(j18o): p18+=1
            elif not first_err: first_err=(j18e or "")[:200]
        w(f"{case}: node18 passed={p18}/{len(samples)} all_pass@node18={p18==len(samples) and len(samples)>0}")
        w(f"   helper.js head: {oj.strip()[:200]!r}")
        if first_err: w(f"   node18 first_err: {first_err!r}")
    finally:
        run(["docker","rm","-f",name])
Path(OUT).write_text("\n".join(buf)+"\n")
print("REJUDGE5_DONE")
