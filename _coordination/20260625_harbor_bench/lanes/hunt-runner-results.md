# hunt-runner-results lane

updated: 2026-06-25T15:56:00Z
agent: continuous bug-hunt agent B / hunt-runner-results
scope: suite runner, result parser, execution_status vs benchmark_status, trace/harness contract, score aggregation, one-command YAML semantics
write_scope: this file only

## Round 1 inventory

Read before inspection:

- `_coordination/20260625_harbor_bench/DRIVER.md`
- `_coordination/20260625_harbor_bench/HANDOFF.md`

Confirmed non-findings:

- `scripts/agentic_bench_suite.py` currently has `--image-preflight-only`, `_execute_image_preflights`, optional audit flags, and `image_preflight_summary.json` output.
- `python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_image_preflight_only_runs_required_preflight_without_adapter` passed on the active worktree.
- `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --image-preflight-only --only tau2_paper_core --output-dir /tmp/no_image_preflight_check_hunt_runner_results` exited 0 and wrote `skipped_no_preflight` for a bench with no image manifest.

## Independent findings

ISSUE-READY: suite execute summary can mark infrastructure pass while benchmark score failed
severity: HIGH
dedup: new
location: `scripts/agentic_bench_suite.py:907-952`, `scripts/agentic_bench_suite.py:1092-1112`, `reports/repozero_suite_execute_preflight_smoke_20260625.md:90-123`
static_repro: `nl -ba scripts/agentic_bench_suite.py | sed -n "907,1112p"` and `nl -ba reports/repozero_suite_execute_preflight_smoke_20260625.md | sed -n "90,123p"`
impact: One-command `--execute` currently reports `status: pass` from adapter process exit only. A recorded RepoZero smoke had a successful wrapper process but a failing native benchmark outcome; the numeric model result was removed from the current publication tree on 2026-07-21. Any aggregator or dashboard that consumes only controller `summary.json` can still publish a false green benchmark result, and there is no structured way to distinguish infra pass, benchmark fail, parse error, or score validity.
fix: Add a read-only result parser stage after each adapter run. Keep process status as `execution_status`, add `benchmark_status`, `result_path`, `primary_score`, `primary_score_unit`, `score_claim_valid`, `failure_category`, and suite-level counts. Write one normalized artifact under `<output_root>/results/<bench_id>.result.json`; keep existing `status` for backward compatibility.
evidence: `_run_one` returns only `bench_id/status/exit_code/timestamps/log_path`, and `_execute_plan` writes `summary = {"suite_id": ..., "status": status, "results": results}`. The retained report now records only that wrapper/process success disagreed with the native benchmark outcome; the old model-backed counts were purged.

ISSUE-READY: BENCH_RUN_DIR and RUN_TAG collide across repeated suite executions
severity: MEDIUM
dedup: new
location: `scripts/agentic_bench_suite.py:743-753`, `reports/repozero_suite_execute_preflight_smoke_20260625.md:74-108`
static_repro: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only repozero_py2js_smoke --model-profile dev_proxy_gpt54mini_8130 | python3 -c 'import json,sys; p=json.load(sys.stdin); r=p["runs"][0]; e=r["runtime_env"]; print(r["run_id"]); print(r["run_dir"]); print(e["BENCH_RUN_DIR"]); print(e["RUN_TAG"])'`
impact: `run_id`, `run_dir`, `BENCH_RUN_DIR`, and `RUN_TAG` are deterministic for `suite_id + bench_id + profile`, not for a single invocation. Re-running the same one-command smoke or full suite can reuse the same native artifact directory. RepoZero evidence is especially risky because the recorded adapter command includes `--run-name gpt-5.4-mini_dev_worker_smoke_dryrun_smoke` and `--resume`; stale or partially overwritten native artifacts can be mistaken for the current run, and result parsers will not have an invocation-unique artifact root.
fix: Introduce a controller invocation id, for example timestamp or UUID, and include it in `BENCH_RUN_DIR`, `RUN_TAG`, and adapter-facing run names while retaining stable `suite_id`, `bench_id`, and `profile_id` as metadata. Record the invocation id in `run_manifest.json`, `summary.json`, and normalized result artifacts.
evidence: Dry-run output for RepoZero on this worktree printed `run_id=dev_worker_smoke_dryrun__repozero_py2js_smoke__dev_proxy_gpt54mini_8130`, `run_dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/repozero_py2js_smoke`, `BENCH_RUN_DIR` equal to the same path, and `RUN_TAG=dev_worker_smoke_dryrun`. The recorded RepoZero artifact path is the same suite/bench location, with native output under a stable run-name.

ISSUE-READY: execute summary result order is completion-order, not manifest-order
severity: LOW
dedup: new
location: `scripts/agentic_bench_suite.py:1103-1112`
static_repro: Import `scripts/agentic_bench_suite.py`, call `_execute_plan` with `suite_concurrency: 2` and two toy local commands where the first sleeps longer than the second; then read `summary.json`.
impact: Score aggregation and trace comparison are harder to make deterministic because `summary.results` can reorder between runs depending on scheduler timing. This is inconsistent with `_execute_image_preflights`, which sorts results back to manifest order before writing `image_preflight_summary.json`. Consumers should key by `bench_id`, but the controller should not make stable summary diffs or human review depend on concurrent completion timing.
fix: Mirror `_execute_image_preflights`: build an order map from `plan["runs"]` and sort `results` before writing `summary.json`. Keep live console output as completion-order if desired, but persist manifest-order.
evidence: A toy `_execute_plan` probe with plan order `slow_first`, `fast_second` printed and wrote `result_order= ['fast_second', 'slow_first']` because the summary appends futures from `as_completed` without sorting.

## Cross-check of hunt-runtime-images

Attempted read:

```bash
test -f _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md && sed -n "1,260p" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md || echo MISSING_RUNTIME_LANE
```

Result: `MISSING_RUNTIME_LANE`.

CONFIRM/REFUTE/DUPLICATE notes: blocked until `hunt-runtime-images.md` exists. I did not infer runtime-image findings from absent lane content.

## Next runner/result subdomain

Next round should inspect parser inputs per benchmark family without executing benchmarks: RepoZero native summary files, tau2 controller/native logs, VitaBench one-task output, SWE-bench verified reports, Terminal-Bench 2.1 planned artifacts, and DeepSWE traces. Goal is to turn the normalized parser contract into bench-specific issue-ready parser gaps while preserving separation between `execution_status`, `benchmark_status`, and score validity.
