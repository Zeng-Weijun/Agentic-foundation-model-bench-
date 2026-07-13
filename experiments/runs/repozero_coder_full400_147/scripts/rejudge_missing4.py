#!/usr/bin/env python3
"""Serving-FREE re-judge of the 4 cases that crashed during eval_case
(orchestrator recorded error='no summary.json'). The agent .mjs already
exists on disk; eval_case is oracle-exe-stdout vs node-stdout (no model).
This recovers the TRUE verdict those 4 cases were denied by the driver crash.
Deterministic + faithful: same image, same rz_root, same eval_timeout=10 the run used.
"""
import importlib.util, json
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "coder_full400_20260712T210354Z"
rz_root = Path(rz.DEFAULT_RZ_ROOT)
env = rz.docker_env()
cases = ["rsa/test5.py", "rsa/test2.py", "rsa/test17.py", "mpmath/test14.py"]

out = []
for case in cases:
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    name = f"rejudge-{slug}"
    rec = {"case": case, "run_root": str(run_root)}
    try:
        rz.start_container(name, rz.DEFAULT_IMAGE, dataset_dir, output_root,
                           rz.DEFAULT_QWEN_ROOT, rz.DEFAULT_BASE_URL, rz.DEFAULT_MODEL, env)
        res = rz.eval_case(name, rz_root, case, run_root / "agent", env, 10)
        rec.update({"all_pass": res.get("all_pass"), "passed": res.get("passed"),
                    "total": res.get("total"), "reward": res.get("reward"),
                    "fail_examples_n": len(res.get("fail_examples", []))})
    except Exception as e:  # crash reproduced => genuine bad-output fail
        rec.update({"all_pass": False, "reward": 0, "rejudge_error": repr(e)})
    finally:
        rz.run(["docker", "rm", "-f", name], env=env)
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)

(RUN / "rejudge_missing4.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
npass = sum(1 for r in out if r.get("all_pass"))
print(f"REJUDGE_DONE pass={npass}/4 wrote={RUN/'rejudge_missing4.json'}", flush=True)
