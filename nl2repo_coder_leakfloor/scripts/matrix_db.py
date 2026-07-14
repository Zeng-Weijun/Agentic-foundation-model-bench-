#!/usr/bin/env python3
import sys, subprocess, shutil
from pathlib import Path
DRV_DIR = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/nl2repo_merged_104/scripts"
sys.path.insert(0, DRV_DIR)
import nl2repo_qwencode_driver as drv
env = drv.docker_env()
meta = drv.read_task_meta(Path(drv.DEFAULT_SRC), "databases")
row = drv.load_manifest_row(Path(drv.DEFAULT_MANIFEST), "databases")
drv.ensure_image(row, env, verify_sha=False)
img = row["ghcr"]
WH = drv.DEFAULT_WHEELHOUSE

def fresh(name):
    subprocess.run(["docker","rm","-f",name], env=env, capture_output=True)
    subprocess.run(["docker","run","-d","--name",name,"--network=none","-w","/workspace","-u","root",
        "-e","PIP_NO_INDEX=1","-e","PIP_FIND_LINKS=/wheelhouse","-e","PYTHONPATH=/workspace",
        "-e","PYTHONDONTWRITEBYTECODE=1","-v",f"{WH}:/wheelhouse:ro", img,"tail","-f","/dev/null"],
        env=env, capture_output=True, timeout=180)

def ex(name, cmd):
    return subprocess.run(["docker","exec","-w","/workspace","-u","root",name,"bash","-c",cmd],
        env=env, text=True, capture_output=True, timeout=600)

def check(name, tag):
    d = ex(name, "ls /usr/local/lib/python3.11/site-packages/databases >/dev/null 2>&1 && echo DIR_EXISTS || echo DIR_GONE").stdout.strip()
    imp = ex(name, "python -c 'import databases;print(1)' 2>/dev/null | tail -1").stdout.strip() or "IMPORT_FAIL"
    pt = ex(name, "pytest --continue-on-collection-errors tests 2>&1 | tail -1").stdout.strip()
    print(f"[{tag}] site-pkg databases: {d} | import: {imp} | pytest: {pt}", flush=True)

# C1: pip install FIRST thing (no prior commands)
n="mx-c1"; fresh(n); ex(n,"pip install -e . >/tmp/c1.log 2>&1"); check(n,"C1 pip-install-first")
subprocess.run(["docker","rm","-f",n],env=env,capture_output=True)

# C2: docker cp {start.md} then pip install
n="mx-c2"; fresh(n)
st=Path("/tmp/mx_st"); shutil.rmtree(st,ignore_errors=True); st.mkdir(parents=True); shutil.copyfile(meta["start_md"], st/"start.md")
subprocess.run(["docker","cp",f"{st}/.",f"{n}:/workspace"],env=env,capture_output=True)
ex(n,"pip install -e . >/tmp/c2.log 2>&1"); check(n,"C2 dockercp-then-install")
subprocess.run(["docker","rm","-f",n],env=env,capture_output=True)

# C3: find + pip list first (like my probe), NO docker cp, then pip install
n="mx-c3"; fresh(n)
ex(n,"find /workspace -maxdepth 2 | sort >/dev/null; pip list >/dev/null 2>&1")
ex(n,"pip install -e . >/tmp/c3.log 2>&1"); check(n,"C3 probe-order-noCP")
subprocess.run(["docker","rm","-f",n],env=env,capture_output=True)

# C4: docker cp EMPTY dir then pip install (isolate: does any docker cp matter?)
n="mx-c4"; fresh(n)
ste=Path("/tmp/mx_empty"); shutil.rmtree(ste,ignore_errors=True); ste.mkdir(parents=True)
r=subprocess.run(["docker","cp",f"{ste}/.",f"{n}:/workspace"],env=env,capture_output=True,text=True)
print(f"[C4 empty docker cp rc={r.returncode}] {(r.stderr or '').strip()[:120]}", flush=True)
ex(n,"pip install -e . >/tmp/c4.log 2>&1"); check(n,"C4 emptyCP-then-install")
subprocess.run(["docker","rm","-f",n],env=env,capture_output=True)

subprocess.run(["docker","rmi",img],env=env,capture_output=True)
print("DONE")
