#!/usr/bin/env python3
"""RepoZero Path A full-400 orchestrator (native qwen-code).

Runs the RepoZero Py2JS OFFICIAL 400 valid_ids through
repozero_qwencode_driver.py (--mode agent): per-case repoarena-new container,
qwen-code in-container -> SERVING (.147 Coder), RepoZero official all_pass
judge. Low concurrency, per-case container isolation, resumable.

Design mirrors tools_repozero_codex_full.py's batch loop (ThreadPoolExecutor +
results.jsonl + resume + summary) but the per-case worker is the qwen driver
(one subprocess per case for crash isolation). The image is ensured ONCE up
front; per-case driver runs short-circuit on already_present.

Headline metric = all_pass_rate = (#cases all_pass) / 400  -> compare against
the arXiv anchor 54.70% (Mini-SWE-Agent + Claude-4.6-Sonnet). NOTE: we use Qwen
(free variable) + a native qwen-code scaffold (NOT Mini-SWE-Agent), so this is a
NEW measurement, not an official-cell match: report as "no official cell
matched; anchor = ruler + sanity band".

USAGE (serving free):
  python3 repozero_full400_orchestrator.py --run-name coder_full400_YYYYMMDD --workers 4
  # resume after interruption:
  python3 repozero_full400_orchestrator.py --run-name coder_full400_YYYYMMDD --workers 4 --resume
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRIVER = HERE / "repozero_qwencode_driver.py"

_spec = importlib.util.spec_from_file_location("rzdriver", DRIVER)
rz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rz)  # type: ignore


def run_one(case: str, out_root: Path, args) -> dict:
    slug = case.replace("/", "-").replace(".py", "")
    run_root = out_root / "cases" / slug
    cmd = [
        sys.executable, str(DRIVER), "--mode", "agent", "--case", case,
        "--run-root", str(run_root), "--no-verify-sha",
        "--rz-root", args.rz_root, "--image", args.image,
        "--base-url", args.base_url, "--model", args.model,
        "--rollout-timeout", str(args.rollout_timeout),
        "--max-session-turns", str(args.max_session_turns),
        "--eval-timeout", str(args.eval_timeout),
    ]
    t0 = time.time()
    row: dict = {"case": case}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.case_hard_timeout)
        rc = proc.returncode
        stderr_tail = (proc.stderr or "")[-600:]
    except subprocess.TimeoutExpired:
        rc, stderr_tail = -100, f"[case_hard_timeout {args.case_hard_timeout}s]"
    row["seconds"] = round(time.time() - t0, 1)
    sj = run_root / "summary.json"
    if sj.exists():
        try:
            s = json.loads(sj.read_text())
            a = s.get("agent", {})
            row.update({
                "all_pass": a.get("all_pass"), "reward": a.get("reward"),
                "passed": a.get("passed"), "total": a.get("total"),
                "entry_exists": a.get("entry_exists"), "agent_rc": a.get("agent_rc"),
                "timed_out": a.get("timed_out"),
                "assistant_turns": a.get("stream", {}).get("assistant_turns"),
                "run_root": str(run_root),
            })
            return row
        except Exception as exc:  # noqa: BLE001
            row["parse_error"] = repr(exc)
    row.update({"all_pass": False, "reward": 0, "error": "no summary.json",
                "driver_rc": rc, "stderr_tail": stderr_tail, "run_root": str(run_root)})
    return row


def load_completed(results_jsonl: Path) -> dict:
    done: dict = {}
    if not results_jsonl.exists():
        return done
    for line in results_jsonl.read_text().splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        # only treat as completed if the case actually produced a judged result
        if o.get("case") and o.get("error") is None:
            done[o["case"]] = o
    return done


def write_summary(out_root: Path, results: list[dict], started: float, args) -> dict:
    all_pass = sum(1 for r in results if r.get("all_pass"))
    judged = sum(1 for r in results if r.get("total"))
    summary = {
        "scope": "RepoZero_Py2JS_official_400 x qwen-code(native, in-container) x Coder",
        "model": args.model, "base_url": args.base_url, "workers": args.workers,
        "image": args.image, "cases_total": len(results),
        "cases_all_pass": all_pass,
        "all_pass_rate": round(all_pass / len(results), 4) if results else 0.0,
        "cases_judged": judged,
        "anchor": "54.70%+-2.55 Mini-SWE-Agent+Claude-4.6-Sonnet (ruler+sanity band; NEW measurement, no official cell)",
        "elapsed_seconds": round(time.time() - started, 1),
        "results": sorted(results, key=lambda r: r.get("case", "")),
    }
    (out_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description="RepoZero Path A full-400 orchestrator (native qwen-code)")
    p.add_argument("--rz-root", default=rz.DEFAULT_RZ_ROOT)
    p.add_argument("--image", default=rz.DEFAULT_IMAGE)
    p.add_argument("--shared-tar", default=rz.DEFAULT_SHARED_TAR)
    p.add_argument("--base-url", default=rz.DEFAULT_BASE_URL)
    p.add_argument("--model", default=rz.DEFAULT_MODEL)
    p.add_argument("--run-name", required=True)
    p.add_argument("--workers", type=int, default=4, help="parallel cases/containers (codex line: c=4 stable, c<=8 ok)")
    p.add_argument("--rollout-timeout", type=int, default=1500)
    p.add_argument("--max-session-turns", type=int, default=40)
    p.add_argument("--eval-timeout", type=int, default=10,
                   help="per-sample oracle/node timeout passed to the driver. THIS RUN USED 10s; "
                        "RepoZero OFFICIAL is 5s. See rejudge_official5s.json + AUDIT_NOTES.md for the "
                        "official-5s re-judge of all 400 already-generated .mjs.")
    p.add_argument("--case-hard-timeout", type=int, default=2400)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="debug: only first N cases")
    p.add_argument("--cases", nargs="*", default=None, help="explicit case list (else official 400)")
    args = p.parse_args()

    out_root = Path(rz.DEFAULT_RUNS_ROOT) / args.run_name
    out_root.mkdir(parents=True, exist_ok=True)
    results_jsonl = out_root / "results.jsonl"

    env = rz.docker_env()
    img = rz.ensure_image(args.image, args.shared_tar, env, verify_sha=False)
    print(json.dumps({"event": "image", **img}, ensure_ascii=False), flush=True)

    cases = args.cases if args.cases else rz.parse_official_cases(Path(args.rz_root))
    if args.limit:
        cases = cases[:args.limit]

    completed = load_completed(results_jsonl) if args.resume else {}
    results: list[dict] = [dict(completed[c]) for c in cases if c in completed]
    pending = [c for c in cases if c not in completed]

    print(json.dumps({"event": "start", "run_name": args.run_name, "model": args.model,
                      "base_url": args.base_url, "workers": args.workers,
                      "cases": len(cases), "pending": len(pending),
                      "resume_completed": len(results), "out_root": str(out_root)},
                     ensure_ascii=False), flush=True)

    lock = threading.Lock()
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, c, out_root, args): c for c in pending}
        for fut in concurrent.futures.as_completed(futs):
            c = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:  # noqa: BLE001
                res = {"case": c, "all_pass": False, "reward": 0, "error": repr(exc)}
            with lock:
                results.append(res)
                with results_jsonl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
                summ = write_summary(out_root, results, started, args)
            print(json.dumps({"event": "progress", "done": len(results), "total": len(cases),
                              "case": c, "all_pass": res.get("all_pass"),
                              "cases_all_pass": summ["cases_all_pass"],
                              "all_pass_rate": summ["all_pass_rate"]}, ensure_ascii=False), flush=True)

    summ = write_summary(out_root, results, started, args)
    print("SUMMARY", out_root / "summary.json", flush=True)
    print("ALL_PASS", summ["cases_all_pass"], "/", summ["cases_total"],
          "= {:.4f}".format(summ["all_pass_rate"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
