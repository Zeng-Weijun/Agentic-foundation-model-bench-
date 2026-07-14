#!/usr/bin/env python3
"""NL2Repo base-image LEAK-FLOOR probe (Claude, correction recheck for credibility point #9).

Faithful: calls the DRIVER'S OWN run_scoring (the official post_processor port) with an
EMPTY staging dir (zero model source). run_scoring does exactly what the headline scoring
does -- start fresh base image, `docker cp staging/. :/workspace`, run test_shell
(pip install -e . + pytest), analyze_pytest -- so the ONLY difference vs the headline run
is that the model contributed nothing.

CRITICAL: the `docker cp staging/. :/workspace` overlay (even of an EMPTY dir) triggers an
overlay copy-up that REVIVES the base image's whiteout-hidden reference source. So this
faithfully measures the base-image leak floor (verified: databases empty->142/154, matching
the pre-fix 0.922 false-positive; the same mechanism A+B confirmed on the Instruct family).

leak_floor_passed = tests that pass with ZERO model contribution.
honest_passed(task)      = max(recorded_passed - leak_floor_passed, 0)   [task's rule]
honest_success_rate(task)= min(honest_passed / total, 1)
"""
import sys, os, json, shutil
from pathlib import Path

DRV_DIR = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/nl2repo_merged_104/scripts"
sys.path.insert(0, DRV_DIR)
import nl2repo_qwencode_driver as drv


def leakfloor(task, run_root, network="none", cmd_timeout=1800, verify_sha=False, keep_image=False):
    env = drv.docker_env()
    meta = drv.read_task_meta(Path(drv.DEFAULT_SRC), task)
    row = drv.load_manifest_row(Path(drv.DEFAULT_MANIFEST), task)
    out = Path(run_root) / task
    out.mkdir(parents=True, exist_ok=True)
    img = drv.ensure_image(row, env, verify_sha=verify_sha)
    # EMPTY staging = zero model source. strip on empty is a no-op (kept for symmetry).
    staging = out / "empty_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    drv.strip_workspace(staging, meta["py_test_file_list"])
    cname = f"nl2repo-leakfloor-{task}".replace("_", "-")[:120]
    # DRIVER'S OWN official scoring, empty model source (does the leak-reviving docker cp)
    score = drv.run_scoring(row["ghcr"], cname, staging, meta, out, env,
                            drv.DEFAULT_WHEELHOUSE, network, cmd_timeout, keep_image=keep_image)
    pr = score["pytest_results"]
    res = {"task": task, "leak_floor_passed": pr["passed"], "leak_floor_failed": pr["failed"],
           "leak_floor_errors": pr["errors"], "total": meta["test_case_count"],
           "leak_floor_success_rate": score["success_rate"],
           "command_exit_codes": score["command_exit_codes"],
           "ghcr": row["ghcr"], "image_status": img.get("status")}
    (out / "leakfloor.json").write_text(json.dumps(res, indent=2) + "\n")
    print(f"LEAKFLOOR {task} passed={res['leak_floor_passed']}/{res['total']} "
          f"sr={res['leak_floor_success_rate']} exit={res['command_exit_codes']}", flush=True)
    return res


if __name__ == "__main__":
    run_root = os.environ.get("LF_RUN_ROOT", "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/leakfloor_coder")
    to = int(os.environ.get("LF_CMD_TIMEOUT", "1800"))
    keep = os.environ.get("LF_KEEP_IMAGE", "0") == "1"
    for task in sys.argv[1:]:
        try:
            leakfloor(task, run_root, cmd_timeout=to, keep_image=keep)
        except Exception as e:
            print(f"LEAKFLOOR_ERROR {task}: {type(e).__name__}: {e}", flush=True)
