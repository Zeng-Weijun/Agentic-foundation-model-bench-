#!/usr/bin/env python3
"""Serving-FREE re-judge of ALL 400 already-generated .mjs at the OFFICIAL 5s
per-sample eval timeout.

WHY: the full400 run used the driver default --eval-timeout=10s
(driver.py argparse default; orchestrator.py passed 10). RepoZero's OWN
evaluate/eval_py2js_docker.py hardcodes subprocess timeout=5 (lines 52 & 59).
10s is 2x looser than official and can only ADMIT passes the official 5s would
reject (a sample whose oracle/node runs 5-10s). So the committed 98/400=24.5%
is an UPPER bound relative to the official 5s harness.

This script isolates the single eval-timeout variable: same image, same
already-generated .mjs, same rz_root, SAME eval node (qwen-mounted node v20 that
the run's eval actually used via dexec_plain -> container PATH), only
eval_timeout 10 -> 5. It re-runs RepoZero's own eval_case (oracle-executable
stdout vs `node <entry>.mjs` stdout, normalized-line equality across every
testcase sample -> per-case all_pass) for all 400 cases and reports the 5s
headline X/400 next to the committed 10s 98/400.

Method (rigor for the eval-timeout boundary):
  Phase 1 (parallel, N workers): eval every case at 5s.
  Phase 2 (serial, contention-free): any case that was all_pass at 10s but NOT
    all_pass in Phase-1 5s is re-verified SERIALLY at 5s AND 10s (one container,
    no CPU contention). This distinguishes a GENUINE >5s per-sample cost (fails
    5s, passes 10s serially -> real official-5s penalty) from a Phase-1
    contention artifact (passes 5s serially -> keep as pass). The final 5s
    verdict for a flipped case uses the contention-free serial result.
  Conservative rule: any case whose oracle/node exceeds 5s (TimeoutExpired) is
    counted all_pass=False, matching official (that sample cannot match).

Deterministic + faithful. NO model / NO serving in the judge.
"""
import concurrent.futures as cf
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "coder_full400_20260712T210354Z"
RZ_ROOT = Path(rz.DEFAULT_RZ_ROOT)
IMAGE = rz.DEFAULT_IMAGE
QWEN_ROOT = rz.DEFAULT_QWEN_ROOT
BASE_URL = rz.DEFAULT_BASE_URL
MODEL = rz.DEFAULT_MODEL

OUT_JUDGES = RUN / "rejudge_official5s_judges"
OUT_JSON = RUN / "rejudge_official5s.json"
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def load_baseline_10s():
    """case -> (all_pass, passed, total) from the committed 10s run record."""
    base = {}
    with (RUN / "results.jsonl").open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            base[o["case"]] = (bool(o.get("all_pass")), o.get("passed"), o.get("total"))
    return base


def eval_one(case, eval_timeout, name, out_dir, env):
    """Start a fresh container for `case`, run eval_case at `eval_timeout`.
    Returns dict with all_pass/passed/total or timeout/error (conservative False)."""
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = RZ_ROOT / "Py2JS" / "dataset" / lib
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"case": case, "eval_timeout": eval_timeout}
    try:
        rz.start_container(name, IMAGE, dataset_dir, output_root,
                           QWEN_ROOT, BASE_URL, MODEL, env)
        res = rz.eval_case(name, RZ_ROOT, case, out_dir, env, eval_timeout)
        rec.update({"all_pass": bool(res.get("all_pass")), "passed": res.get("passed"),
                    "total": res.get("total"), "timeout": False, "error": None})
    except subprocess.TimeoutExpired as e:
        cmd = e.cmd if isinstance(e.cmd, list) else [str(e.cmd)]
        side = "oracle" if any("_executable" in str(c) for c in cmd) else ("node" if "node" in cmd else "unknown")
        rec.update({"all_pass": False, "passed": None, "total": None, "timeout": True,
                    "timeout_side": side, "error": f"TimeoutExpired@{eval_timeout}s side={side} cmd={cmd}"})
    except Exception as e:  # noqa: BLE001
        rec.update({"all_pass": False, "passed": None, "total": None, "timeout": False,
                    "error": repr(e)})
    finally:
        rz.run(["docker", "rm", "-f", name], env=env)
    return rec


def main():
    env = rz.docker_env()
    base10 = load_baseline_10s()
    cases = list(base10.keys())
    assert len(cases) == 400, f"expected 400 cases, got {len(cases)}"
    OUT_JUDGES.mkdir(parents=True, exist_ok=True)

    # ---- Phase 1: all 400 at 5s, parallel ----
    t0 = time.time()
    p1 = {}
    done = 0

    def work(case):
        slug = case.replace("/", "-").replace(".py", "")
        return case, eval_one(case, 5, f"rj5-{slug}"[:120], OUT_JUDGES / slug, env)

    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for case, rec in ex.map(work, cases):
            p1[case] = rec
            done += 1
            if done % 25 == 0 or done == len(cases):
                npass = sum(1 for r in p1.values() if r["all_pass"])
                print(f"[phase1 5s] {done}/400  all_pass_so_far={npass}  elapsed={round(time.time()-t0)}s", flush=True)

    # ---- identify flips: all_pass@10s but NOT all_pass@5s(phase1) ----
    flips = [c for c in cases if base10[c][0] and not p1[c]["all_pass"]]
    anomalies = [c for c in cases if (not base10[c][0]) and p1[c]["all_pass"]]  # fail@10s -> pass@5s (should be empty)
    print(f"[flips] pass@10s->fail@5s(phase1) = {len(flips)}: {flips}", flush=True)
    print(f"[anomalies] fail@10s->pass@5s(phase1) = {len(anomalies)}: {anomalies}", flush=True)

    # ---- Phase 2: serial contention-free re-verify of each flip at 5s AND 10s ----
    serial = {}
    for case in flips:
        slug = case.replace("/", "-").replace(".py", "")
        r5 = eval_one(case, 5, f"rj5s-{slug}"[:120], OUT_JUDGES / (slug + "_serial5"), env)
        r10 = eval_one(case, 10, f"rj10s-{slug}"[:120], OUT_JUDGES / (slug + "_serial10"), env)
        serial[case] = {"serial_5s": r5, "serial_10s": r10}
        print(f"[phase2 serial] {case}  5s_all_pass={r5['all_pass']} (to={r5.get('timeout')})  "
              f"10s_all_pass={r10['all_pass']}", flush=True)

    # ---- final 5s verdict per case ----
    rows = []
    for case in cases:
        ap10, pa10, to10 = base10[case]
        p1r = p1[case]
        final5 = p1r["all_pass"]
        note = ""
        if case in serial:
            # contention-free serial 5s is authoritative for the flipped case
            final5 = serial[case]["serial_5s"]["all_pass"]
            if final5:
                note = "phase1_5s_fail_was_CONTENTION (serial 5s passes) -> counted PASS@5s"
            elif serial[case]["serial_10s"]["all_pass"]:
                note = "GENUINE >5s per-sample cost (serial: 5s fail, 10s pass) -> official-5s penalty"
            else:
                note = "serial 5s fail AND serial 10s fail (does not reproduce 10s pass) -> investigate"
        rows.append({
            "case": case,
            "all_pass_10s": ap10, "passed_10s": pa10, "total_10s": to10,
            "all_pass_5s": bool(final5),
            "passed_5s": p1r.get("passed"), "total_5s": p1r.get("total"),
            "timeout_5s": p1r.get("timeout"), "timeout_side_5s": p1r.get("timeout_side"),
            "error_5s": p1r.get("error"),
            "phase1_5s_all_pass": p1r["all_pass"],
            "serial_verify": serial.get(case),
            "note": note,
        })

    n10 = sum(1 for r in rows if r["all_pass_10s"])
    n5 = sum(1 for r in rows if r["all_pass_5s"])
    genuine = [r["case"] for r in rows if "GENUINE" in r["note"]]
    contention = [r["case"] for r in rows if "CONTENTION" in r["note"]]
    investigate = [r["case"] for r in rows if "investigate" in r["note"]]

    out = {
        "meta": {
            "purpose": "official 5s eval-timeout re-judge of the already-generated 400 .mjs (serving-free)",
            "run": str(RUN),
            "image": IMAGE,
            "eval_node": "qwen-mounted node v20.20.2 (SAME node the run's eval used via dexec_plain->container PATH); "
                         "isolates ONLY the eval-timeout variable 10s->5s",
            "eval_timeout_run_10s": 10,
            "eval_timeout_official_5s": 5,
            "official_hardcode_ref": "RepoZero/evaluate/eval_py2js_docker.py lines 52 & 59 (subprocess timeout=5)",
            "phase1_workers": WORKERS,
            "conservative_rule": "any sample exceeding 5s (TimeoutExpired) => case all_pass=False (official cannot match a timed-out sample)",
            "generated_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seconds_total": round(time.time() - t0, 1),
        },
        "headline": {
            "denominator": 400,
            "all_pass_10s": n10, "rate_10s": round(n10 / 400, 4),
            "all_pass_5s": n5, "rate_5s": round(n5 / 400, 4),
            "delta_cases": n5 - n10,
            "flips_pass10s_to_fail5s": flips,
            "flip_genuine_5s_timeout": genuine,
            "flip_contention_artifact_kept_pass": contention,
            "flip_investigate": investigate,
            "anomalies_fail10s_to_pass5s": anomalies,
        },
        "cases": sorted(rows, key=lambda r: r["case"]),
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print("\n===== REJUDGE OFFICIAL 5s DONE =====", flush=True)
    print(f"10s (committed): {n10}/400 = {round(100*n10/400,2)}%", flush=True)
    print(f" 5s (official) : {n5}/400 = {round(100*n5/400,2)}%   delta={n5-n10}", flush=True)
    print(f"genuine 5s-timeout flips: {genuine}", flush=True)
    print(f"contention flips kept-pass: {contention}", flush=True)
    print(f"investigate: {investigate}", flush=True)
    print(f"anomalies(fail10->pass5): {anomalies}", flush=True)
    print(f"wrote {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
