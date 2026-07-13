#!/usr/bin/env python3
"""Reviewer B: recover TRUE per-sample verdict for the 8 cases that crashed
the driver during eval_case (raised subprocess.TimeoutExpired on a single
dexec_plain call, aborting judging of the REMAINING samples with
error='no summary.json' -> conservatively counted all_pass=False in the
committed 51/400). This re-implements eval_case's exact comparison logic but
catches TimeoutExpired PER-SAMPLE (treats that one sample as failed, same as
official semantics: a timed-out node run cannot match oracle stdout) and
continues to the remaining samples, to see the FULL passed/total instead of
whatever partial count existed when the crash killed the process.
Does NOT change scoring semantics (timeout==fail, matches conservative_rule
used elsewhere in this repo's own rejudge_official5s.py), only recovers full
visibility hidden by the driver crash.
"""
import importlib.util, json, subprocess
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "instruct2507_full400_20260713T151209Z"
rz_root = Path(rz.DEFAULT_RZ_ROOT)
env = rz.docker_env()

CASES = ["rsa/test5.py", "mpmath/test18.py"]  # spot-check 2 of the 8


def eval_case_resilient(name, rz_root, case, env, eval_timeout=10):
    lib, filename = case.split("/")
    stem = filename[:-3] if filename.endswith(".py") else filename
    exe_name = stem + "_executable"
    entry_name = stem + ".mjs"
    pkg_name = stem + "_pkg"
    container_pkg_dir = f"{rz.CONTAINER_OUTPUT}/packages/{lib}/{pkg_name}"
    testcase_file = rz_root / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    samples = rz.load_jsonl_cases(testcase_file, case)

    exists = rz.dexec_plain(name, ["test", "-f", f"{container_pkg_dir}/{entry_name}"], env, timeout=30).returncode == 0
    if not exists:
        return {"all_pass": False, "passed": 0, "total": len(samples), "note": "no entry file"}

    passed = 0
    n_timeout = 0
    fail_examples = []
    for params in samples:
        args = rz.args_from_params(params)
        try:
            py = rz.dexec_plain(name, [f"{rz.CONTAINER_DATASET}/{exe_name}"] + args, env, timeout=eval_timeout)
            js = rz.dexec_plain(name, ["node", entry_name] + args, env, timeout=eval_timeout, workdir=container_pkg_dir)
        except subprocess.TimeoutExpired as e:
            n_timeout += 1
            if len(fail_examples) < 3:
                fail_examples.append({"args": args, "TIMEOUT": True})
            continue
        ok = py.returncode == 0 and js.returncode == 0 and rz.normalized_lines(py.stdout or "") == rz.normalized_lines(js.stdout or "")
        if ok:
            passed += 1
        elif len(fail_examples) < 3:
            fail_examples.append({"args": args, "oracle_rc": py.returncode, "js_rc": js.returncode,
                                   "oracle_stdout": (py.stdout or "")[:200], "js_stdout": (js.stdout or "")[:200]})
    total = len(samples)
    return {"all_pass": passed == total and total > 0, "passed": passed, "total": total,
            "n_timeout_samples": n_timeout, "fail_examples": fail_examples}


out = []
for case in CASES:
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    name = f"reviewerB-recover-{slug}"
    print(f"\n=== RECOVER {case} (committed: all_pass=False, error='no summary.json') ===", flush=True)
    rec = {"case": case}
    try:
        rz.start_container(name, rz.DEFAULT_IMAGE, dataset_dir, output_root,
                           rz.DEFAULT_QWEN_ROOT, rz.DEFAULT_BASE_URL, rz.DEFAULT_MODEL, env)
        res = eval_case_resilient(name, rz_root, case, env, eval_timeout=10)
        rec.update(res)
        print(json.dumps(rec, indent=2, ensure_ascii=False), flush=True)
    except Exception as e:
        rec["error"] = repr(e)
        print("ERROR:", e, flush=True)
    finally:
        rz.run(["docker", "rm", "-f", name], env=env)
    out.append(rec)

print("\n===== RECOVERY SUMMARY =====")
for r in out:
    print(r["case"], "TRUE all_pass=", r.get("all_pass"), "passed=", r.get("passed"), "/", r.get("total"), "timeouts=", r.get("n_timeout_samples"))
(RUN / "reviewerB_crash_recovery.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
