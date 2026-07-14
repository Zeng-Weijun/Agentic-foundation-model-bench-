#!/usr/bin/env python3
"""Diagnostic: reproduce the databases pre-fix 142 vs my probe 0 discrepancy.
(A) call the DRIVER's own run_scoring with {start.md}-only staging (== pre-fix input), twice.
(B) step-through import resolution in a fresh base container."""
import sys, shutil, json, subprocess
from pathlib import Path
DRV_DIR = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/nl2repo_merged_104/scripts"
sys.path.insert(0, DRV_DIR)
import nl2repo_qwencode_driver as drv

env = drv.docker_env()
meta = drv.read_task_meta(Path(drv.DEFAULT_SRC), "databases")
row = drv.load_manifest_row(Path(drv.DEFAULT_MANIFEST), "databases")
drv.ensure_image(row, env, verify_sha=False)
img = row["ghcr"]

# (A) driver run_scoring on {start.md}-only, two independent fresh containers
for trial in (1, 2):
    staging = Path(f"/tmp/lf_db_staging_{trial}"); shutil.rmtree(staging, ignore_errors=True); staging.mkdir(parents=True)
    shutil.copyfile(meta["start_md"], staging / "start.md")
    drv.strip_workspace(staging, meta["py_test_file_list"])
    out = Path(f"/tmp/lf_db_out_{trial}"); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    score = drv.run_scoring(img, f"nl2repo-lftest-databases-{trial}", staging, meta, out, env,
                            drv.DEFAULT_WHEELHOUSE, "none", 600, keep_image=True)
    print(f"[A trial{trial}] DRIVER run_scoring {{start.md}}-only: passed={score['pytest_results']['passed']}/"
          f"{meta['test_case_count']} sr={score['success_rate']} exit={score['command_exit_codes']}", flush=True)

# (B) step-through import resolution in a fresh base container
def d(cmd, name="nl2repo-lfdiag-db"):
    return subprocess.run(["docker", "exec", "-e", "PYTHONPATH=/workspace", name, "bash", "-c", cmd],
                          env=env, text=True, capture_output=True, timeout=300)
subprocess.run(["docker", "rm", "-f", "nl2repo-lfdiag-db"], env=env, capture_output=True)
subprocess.run(["docker", "run", "-d", "--name", "nl2repo-lfdiag-db", "--network=none", "-u", "root",
                "-e", "PIP_NO_INDEX=1", "-e", "PIP_FIND_LINKS=/wheelhouse", "-e", "PYTHONPATH=/workspace",
                "-v", f"{drv.DEFAULT_WHEELHOUSE}:/wheelhouse:ro", "-w", "/workspace", img, "tail", "-f", "/dev/null"],
               env=env, capture_output=True, timeout=180)
print("[B1] BEFORE pip install -> import databases:", d("python -c 'import databases,os;print(databases.__file__)' 2>&1 | tail -1").stdout.strip())
print("[B2] pip show databases (loc+files record):", d("pip show -f databases 2>&1 | grep -iE 'Location|Version' | head -3").stdout.strip().replace("\n","; "))
print("[B3] site-packages databases dir exists?:", d("ls -d /usr/local/lib/python3.11/site-packages/databases 2>&1 | tail -1").stdout.strip())
r = d("cd /workspace && pip install -e . 2>&1 | tail -4")
print("[B4] pip install -e . tail:", r.stdout.strip().replace("\n"," | "))
print("[B5] AFTER pip install -> site-packages databases dir exists?:", d("ls /usr/local/lib/python3.11/site-packages/databases 2>&1 | head -3 | tr '\\n' ' '").stdout.strip())
print("[B6] AFTER pip install -> import databases:", d("python -c 'import databases;print(databases.__file__)' 2>&1 | tail -1").stdout.strip())
print("[B7] pytest result:", d("cd /workspace && pytest --continue-on-collection-errors tests 2>&1 | tail -1").stdout.strip())
subprocess.run(["docker", "rm", "-f", "nl2repo-lfdiag-db"], env=env, capture_output=True)
subprocess.run(["docker", "rmi", img], env=env, capture_output=True)
print("DONE")
