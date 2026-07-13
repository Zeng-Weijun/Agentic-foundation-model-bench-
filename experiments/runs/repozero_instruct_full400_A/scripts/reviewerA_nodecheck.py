#!/usr/bin/env python3
"""Diagnose base58/test6 disagreement: node version / ESM .js handling.
Faithfully replicate the driver container (qwen node mounted + PATH prepended)
and compare node18 (image) vs node20 (qwen) on the SAME stored .mjs+.js."""
import subprocess, json, os, time
from pathlib import Path
RZ_RUN = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z")
RZ_ROOT = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero")
IMAGE = "ghcr.io/jessezzzzz/repoarena-new:latest"
QWEN_ROOT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/.npm-root"
QWEN_BIN = "/opt/qwen-native/.npm-root/node_modules/node/bin"
OUT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/reviewerA_nodecheck.txt"
buf=[];
def w(*a): buf.append(" ".join(str(x) for x in a))
env=dict(os.environ)
for k in ("http_proxy","https_proxy","HTTP_PROXY","HTTPS_PROXY"): env.pop(k,None)
def run(argv,t=30):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=t,env=env); return p.returncode,p.stdout or "",p.stderr or ""
    except Exception as e: return -1,"",repr(e)

case="base58/test6.py"; lib="base58"; stem="test6"
wsout=RZ_RUN/"cases"/"base58-test6"/"workspace_output"
dataset=RZ_ROOT/"Py2JS"/"dataset"/lib
cont_pkg=f"/workspace/output/packages/{lib}/{stem}_pkg"
name=f"reviewerA-nodecheck-{int(time.time())}"
# faithful container: qwen mount + PATH prepend (mirror driver container_env)
PATH_FAITHFUL=f"{QWEN_BIN}:/opt/qwen-native/.npm-root/node_modules/.bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
rc,o,e=run(["docker","run","-d","--rm","--name",name,"-e",f"PATH={PATH_FAITHFUL}",
    "-v",f"{dataset}:/workspace/dataset:ro","-v",f"{wsout}:/workspace/output:ro",
    "-v",f"{QWEN_ROOT}:/opt/qwen-native/.npm-root:ro",IMAGE,"tail","-f","/dev/null"],60)
w("container start rc",rc,e[:200])
try:
    # which node does bare `node` resolve to (container default PATH = qwen first)?
    w("\n[default `node` in container (qwen PATH prepended, = what the run's judge used)]")
    for probe in [["node","--version"],["which","node"],["/usr/bin/node","--version"]]:
        rc,o,e=run(["docker","exec",name]+probe); w("  ",probe,"->",o.strip(),e.strip()[:80])
    # sample args
    testcase_file=RZ_ROOT/"Py2JS"/"testcases_60"/"testcase_base58.jsonl"
    samples=[json.loads(l) for l in open(testcase_file) if l.strip() and json.loads(l).get("filename")==case]
    p=samples[0]; args=[]
    for k,v in p.items():
        if k!="filename": args+=[f"--{k}",str(v)]
    w("\n[sample args]",args)
    # oracle
    rc,o,e=run(["docker","exec",name,f"/workspace/dataset/{stem}_executable"]+args)
    w("oracle rc",rc,"out",repr(o[:120]))
    # node via bare `node` (qwen v20)
    rc,o,e=run(["docker","exec","-w",cont_pkg,name,"node",f"{stem}.mjs"]+args)
    w("\n[bare `node` (qwen v20)] rc",rc,"out",repr(o[:120]),"err",repr(e[:160]))
    # node via image /usr/bin/node (v18)
    rc,o,e=run(["docker","exec","-w",cont_pkg,name,"/usr/bin/node",f"{stem}.mjs"]+args)
    w("\n[/usr/bin/node (image v18)] rc",rc,"out",repr(o[:120]),"err",repr(e[:200]))
finally:
    run(["docker","rm","-f",name])
Path(OUT).write_text("\n".join(buf)+"\n")
print("NODECHECK_DONE")
