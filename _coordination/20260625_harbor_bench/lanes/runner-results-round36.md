# Round36 runner/results one-command parser review

## Scope

Report-only review of the one-command suite execute/result path after image warmup. No production code, manifests, tests, Docker actions, benchmarks, or model calls were run. Bounded probes were static reads, suite dry-runs/readiness reports, existing-unit tests, and synthetic local controller executions.

Remote worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`

Observed branch/head: `feat/image-warmup-policy` at `684b479` (`Tighten bench readiness guardrails`).

## PASS: readiness/dry-run guardrails expose warmed-image helper rows without making full targets ready

- Location: `scripts/agentic_bench_suite.py:967-1033`, `scripts/agentic_bench_suite.py:1074-1260`.
- Evidence: `build_readiness_report()` uses full entries for aggregation when full entries exist, while dry-run `build_run_plan()` records `run_dir`, redacted `runtime_env.BENCH_RUN_DIR`, image preflight manifests, worker rootless Docker env, and adapter command provenance.
- Probe: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --target-benches RepoZero,tau3-bench,swe-bench-verified,DeepSWE --json` returned rc 1 because the selected target set still has blocked full entries. Parsed output:
  - `repozero`: ready, aggregation ready 1.
  - `tau3_bench`: blocked, aggregation ready 0, full blockers include disabled/pending adapter and tau3 full guardrails.
  - `swebench_verified_multi`: blocked, aggregation ready 0, blocker `image_manifest_not_materialized`.
  - `deepswe`: blocked, aggregation ready 0, blocker `image_manifest_not_materialized`.
- Probe: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only tau3_bench_oracle_direct_smoke,swebench_verified_django10097_swe_agent_image_smoke,repozero_py2js_smoke --json` returned rc 0 and selected 3 runs:
  - `repozero_py2js_smoke`, script `run_repozero_py2js.sh`, preflight `manifests/images/repozero.yaml`, policy `required`.
  - `swebench_verified_django10097_swe_agent_image_smoke`, script `run_swebench_verified_swe_agent.sh`, preflight `manifests/images/swebench_verified_django10097.yaml`, policy `required`.
  - `tau3_bench_oracle_direct_smoke`, script `run_tau3_bench.sh`, preflight `manifests/images/tau3_oracle_direct_smoke.yaml`, policy `required`.
- Review result: PASS for readiness/dry-run semantics. These paths do not overclaim full benchmark readiness.

## COMMENT-READY: highest-impact blocker remains missing native-artifact parser/provenance for non-RepoZero adapters

- Dedup: existing #1/#12. This is not a new root cause; current head still reproduces the known execution-vs-benchmark/native-provenance gap. It is still the highest-impact runner/results blocker after images warm because one-command `--execute` can finish adapter work and still emit normalized results that say `no_parser/unknown` or `not_run/adapter_crash` while native result summaries exist.
- Primary code locations:
  - `scripts/agentic_bench_suite.py:1578-1607` has only a RepoZero benchmark parser.
  - `scripts/agentic_bench_suite.py:1609-1636` short-circuits nonzero adapter exits before reading native artifacts, then falls back to `parser_status=no_parser`, `status=unknown`, and `failure_category=native_artifact_missing` for successful non-RepoZero adapters.
  - `scripts/agentic_bench_suite.py:1639-1658` writes `agentic_bench.result.v1` with only suite/run/bench/adapter plus execution and benchmark_result; it omits `run_dir`, `runtime_env.BENCH_RUN_DIR`, `artifact_manifest.json`, `tau3_result_summary.json`, and `source.native_artifacts[]` provenance even though the plan has `run_dir` and redacted runtime env at `scripts/agentic_bench_suite.py:1215-1225`.
- Real runner evidence:
  - `/data/nips/bench/lib/bench_common.sh:223-227` writes `artifact=<path>` and `done: <path>` for all wrappers that call `bench_finish()`.
  - `/data/nips/bench/run_tau3_bench.sh:114-158` writes `tau3_result_summary.json` for oracle-direct mode and exits nonzero on failed verifier/direct command; `/data/nips/bench/run_tau3_bench.sh:224-310` writes a Harbor `tau3_result_summary.json` with `n_total_trials`, `n_errors`, and `successful_eval_trials`, then exits nonzero on native failure states.
  - `/data/nips/bench/run_deepswe.sh:251-289` writes `artifact_manifest.json` with `result_json` and summary counts after a Pier result exists.
  - `/data/nips/bench/run_swebench_verified.sh:137-160`, `/data/nips/bench/run_swebench_verified_mini_swe_agent.sh:60-83`, and `/data/nips/bench/run_swebench_verified_openhands.sh:135-163` write `artifact_manifest.json` for SWE-agent, mini-swe-agent, and OpenHands outputs.
  - `/data/nips/bench/run_terminal_bench.sh:99-104`, `/data/nips/bench/run_vitabench.sh:101-106`, and `/data/nips/bench/run_tau2.sh:46-51` at least expose command logs plus `artifact=`/`done:` pointers.
- Deterministic repro A, successful non-RepoZero adapter with native artifacts:
  - Synthetic plan executed a `tau3_bench_oracle_direct_smoke` command that wrote `tau3_result_summary.json` with `status=passed` and `artifact_manifest.json`, then exited 0.
  - `_execute_plan()` returned rc 0 and `summary.status=0`.
  - Normalized row had `execution_status=pass`, `benchmark_status=unknown`, `failure_category=native_artifact_missing`.
  - Per-run result had `benchmark_result.parser_status=no_parser` and no top-level `source` field. Native manifest and summary files existed.
- Deterministic repro B, nonzero adapter with native summary:
  - Synthetic plan executed a `tau3_bench` command that wrote `tau3_result_summary.json` with `status=errors`, `n_total_trials=1`, `n_errors=1`, `successful_eval_trials=0`, wrote `artifact_manifest.json`, then exited 7.
  - `_execute_plan()` returned rc 1 and `summary.status=1`.
  - Normalized row had `execution_status=fail`, adapter status `fail:7`, `benchmark_status=infra_error`, `failure_category=adapter_crash`.
  - Per-run result had `benchmark_result.parser_status=not_run` and `short_failure_note=adapter exited 7`. Native manifest and summary files existed.
- Impact:
  - After images are warmed, the one-command suite can launch the intended adapters, but `summary.json` and `agentic_bench.result.v1` cannot reliably answer whether tau3/SWE-bench/DeepSWE/Terminal-Bench/VitaBench/tau2 benchmark work passed, failed, partially ran, or produced parseable native artifacts.
  - For tau3 specifically, a valid verifier failure or Harbor run with native error counts collapses to opaque `adapter_crash`; a valid pass collapses to `unknown/no_parser`.
  - Downstream orchestration cannot safely decide whether to file a model-quality failure, an infra failure, a parser gap, or a retry from one-command outputs alone.
- Fix proposal:
  1. Add a parser registry keyed by adapter/bench id. First fixture should cover tau3 because current image-smoke helper is warmed and native summaries are small and already schema-tagged.
  2. Run native result discovery before adapter-exit classification decides benchmark status. Preserve `execution.status=fail` for nonzero exits, but still parse allowlisted native summaries from `run.run_dir`, redacted `runtime_env.BENCH_RUN_DIR`, `run.env.summary`, explicit `artifact=`/`done:` lines, `artifact_manifest.json`, or `AGENTIC_RESULT_JSON` when present.
  3. Add `source.native_artifacts[]` to `agentic_bench.result.v1` with role/status/read_policy. Safe examples: `tau3_result_summary` as `allowlist_json`, native artifact root as `pointer_only`, raw logs/config/commands as `restricted_raw` or `excluded_by_policy`.
  4. For tau3 direct pass, emit `benchmark_result.parser_status=parsed`, `status=pass`, `passed=true`, `metric=reward`, `reward=1.0`, `verifier_status=passed`, `score_claim_valid=true` only when the native schema supports it.
  5. For tau3 Harbor/native failure summaries, preserve `n_total_trials`, `n_errors`, `successful_eval_trials`, bounded `exception_stats` keys, and classify as benchmark/harness failure instead of generic `adapter_crash`.
  6. Add redaction tests that assert result JSON never copies raw `run.env.summary`, command files, model config files, raw task logs, or env secret values.

## PASS: existing RepoZero parser behavior is still covered

- Location: `scripts/test_agentic_bench_suite.py:619-660`.
- Probe: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_execute_plan_parses_repozero_benchmark_status_separately scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_execute_plan_writes_summary_results_in_manifest_order` returned rc 0, 2 tests OK.
- Review result: PASS for the one parser that exists today. This does not reduce the non-RepoZero parser gap above.

## ISSUE-READY findings

None new. The confirmed blocker is COMMENT-READY for existing #1/#12 rather than a distinct new issue.

## Commands and exit codes

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_read_round36 && wc -l /tmp/codex_workflow_read_round36`: rc 0, read 973 lines.
- `ssh dev 'cd <worktree> && pwd && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all && git log --oneline -5'`: rc 0, branch `feat/image-warmup-policy`, head `684b479`.
- Static grep/read of suite execute/result parser path and tests: rc 0.
- Static grep/read of `/data/nips/bench` and shared runner scripts for `BENCH_RUN_DIR`, `artifact_manifest.json`, `tau3_result_summary`, `artifact=`, and `done:`: rc 0. One overly broad helper grep was interrupted after staying slow; it produced no evidence and no file changes.
- Synthetic successful tau3-native-artifact `_execute_plan()` repro: rc 0, current normalized output summarized above.
- Synthetic nonzero tau3-native-artifact `_execute_plan()` repro: rc 0 for the probe command itself; suite execution under test returned rc 1 as expected, current normalized output summarized above.
- Readiness probe for RepoZero/tau3/SWE-bench/DeepSWE: rc 1, expected blocked target set, parsed evidence summarized above.
- Dry-run probe for RepoZero/SWE django10097/tau3 helper rows: rc 0, parsed evidence summarized above.
- Focused unit tests for RepoZero parser and summary ordering: rc 0, 2 tests OK.

## Next implementation test to add first

`test_tau3_native_summary_parsed_from_bench_run_dir_even_when_adapter_nonzero`: create a temp `BENCH_RUN_DIR` with `tau3_result_summary.json` and `artifact_manifest.json`; run `_execute_plan()` with adapter `tau3_bench` and command exit 7; assert normalized result keeps `execution.status=fail` but parses the native summary with `parser_status=parsed`, preserves tau3 counts, records `source.native_artifacts[]`, and does not serialize raw sidecar contents.
