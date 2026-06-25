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
impact: One-command `--execute` currently reports `status: pass` from adapter process exit only. The recorded RepoZero smoke had adapter exit 0 and suite wrapper pass, but native benchmark evidence was `ALL_PASS_CASES 0 / 1` and `TESTS 0 / 60`. Any aggregator or dashboard that consumes only controller `summary.json` will publish a false green benchmark result, and there is no structured way to distinguish infra pass, benchmark fail, parse error, or score validity.
fix: Add a read-only result parser stage after each adapter run. Keep process status as `execution_status`, add `benchmark_status`, `result_path`, `primary_score`, `primary_score_unit`, `score_claim_valid`, `failure_category`, and suite-level counts. Write one normalized artifact under `<output_root>/results/<bench_id>.result.json`; keep existing `status` for backward compatibility.
evidence: `_run_one` returns only `bench_id/status/exit_code/timestamps/log_path`, and `_execute_plan` writes `summary = {"suite_id": ..., "status": status, "results": results}`. The RepoZero smoke report records `repozero_py2js_smoke pass exit_code: 0` while also recording `passed: 0`, `total: 60`, `all_pass: false`, and `TESTS 0 / 60`.

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

## Round 2 cross-lane review of hunt-runtime-images

Read `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` from head `c42f23c`.

CONFIRM #4: image preflight commands run the main checkout instead of the active worktree.
location: `manifests/suite.example.yaml:52-54`, `scripts/agentic_bench_suite.py:573-604`
static_repro: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only repozero_py2js_smoke --model-profile dev_proxy_gpt54mini_8130`
evidence: generated `runs[0].image_preflight.command` contains `cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`, not `.worktrees/bench-image-preflight-only`.
runner/parser note: this can also skew parser tests because image-preflight logs may come from a different script revision than the suite runner that later parses results.

CONFIRM #5: optional image audit can false-pass missing runtime manifests.
location: `hunt-runtime-images.md` #5; runner touchpoint `scripts/agentic_bench_suite.py:988-1011`
static_repro: not rerun against worker Docker this round; accepted runtime lane's worker evidence and confirmed suite only consumes checker rc/status.
evidence: suite optional handling only records `optional_fail` if the checker process returns nonzero. If `agentic_bench_images.py check` returns 0 for `optional_missing`, the suite has no independent fatal signal.
runner/parser note: normalized results need a separate `image_preflight_status` with optional-missing counts, not only adapter exit code.

CONFIRM #6: image-preflight-only cannot warm from registry/fallback tar or run smoke.
location: `scripts/agentic_bench_suite.py:586-598`
static_repro: `nl -ba scripts/agentic_bench_suite.py | sed -n "570,605p"`
evidence: generated checker argv appends only `check --image-manifest ... --asset-root ... --docker-host ... --json`; there is no `--pull`, `--load-fallback`, or `--run-smoke` path.
runner/parser note: parser should not infer `image_ready=true` from a cache-only check unless the preflight artifact records which readiness actions were actually allowed and run.

CONFIRM #7: Terminal-Bench 2.1 required image preflight is unreachable through suite selection.
location: `manifests/suite.example.yaml:281-289`
static_repro: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --image-preflight-only --only terminal_bench_2_1 --model-profile dev_proxy_gpt54mini_8130 --output-dir /tmp/hunt_runner_tb_empty_probe`
evidence: command exited `0` and wrote `image_preflight_summary.json` with `results: []`, `counts` all zero, and `status: 0`.
runner/parser note: this is not just an image issue. Empty selected plans must not produce a score/result artifact that looks like a successful no-op; the result layer needs `execution_status=not_run`, `benchmark_status=not_scored` or a nonzero empty-plan error.

CONFIRM #8: rootless restart-if-down gates restart on `docker info` only.
location: `scripts/check_rootless_docker_worker.sh:128-134`
static_repro: `nl -ba scripts/check_rootless_docker_worker.sh | sed -n "120,140p"`
evidence: `restart-if-down` prints `restart_skipped=docker_info_ok` when `docker_info_ok` succeeds; it does not gate on `/version` or Docker SDK readiness before skipping restart.
runner/parser note: CoCoA artifacts already show adapter pass with task-level Docker SDK EOF; parser should classify this as `infra_docker`, not model/task failure.

Round 1 status update: previous summary-order finding is superseded by main; `scripts/agentic_bench_suite.py` now sorts execute `summary.results` in manifest order before writing `summary.json`.

## Round 2 parser input contract gaps

COMMENT-READY for #1: tau2 has complete native result JSON inputs, but the suite parser still returns `no_parser`.
severity: MEDIUM
dedup: comment-on-#1
location: `scripts/agentic_bench_suite.py:1142-1157`, `reports/tau2_proxy_smoke_20260625.md:104-128`
static_repro: import `scripts/agentic_bench_suite.py` and call `_benchmark_result_for_run` with adapter `tau2`; it returns `parser_status=no_parser`, `benchmark_result.status=unknown`, `failure_category=native_artifact_missing`.
impact: The recorded tau2 smoke has three machine-readable `results.json` files, one each for airline, retail, and telecom. Current normalized output would hide completed simulations and rewards behind `unknown`, so score aggregation cannot distinguish completed reward `0.0` from missing artifacts.
fix: Add a `tau2` parser that discovers `artifact=` / `done:` paths or reconstructs expected `data/simulations/<save_to>/results.json` paths, parses `info.environment_info.domain_name`, `info.max_steps`, per-simulation `task_id`, `termination_reason`, `duration`, `reward_info`, costs, and computes average reward. Mark this smoke `score_claim_valid=false` because it is a three-domain one-task smoke.
evidence: Shared native paths exist for `bench_gpt-5.4-mini_tau2_{airline,retail,telecom}_dev_worker_smoke_dryrun/results.json`. Each has `tasks=1`, `simulations=1`, `max_steps=60`; terminations were `user_stop` with durations 39.12s, 75.12s, and 130.70s. The report records all sampled rewards as `0.0`.

ISSUE-READY: VitaBench native result artifacts include a bearer Authorization header unless parser redacts by allowlist
severity: HIGH
dedup: new
location: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/data/simulations/bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847`, `scripts/agentic_bench_suite.py:1142-1157`
static_repro: read the native VitaBench JSON and check only key presence: `info.user_info.llm_args.headers.Authorization in data`.
impact: VitaBench parser work is likely to inspect native JSON. If it copies `info` or raw simulation metadata into normalized results, reports, fixtures, or GitHub issue comments, it can leak a live API credential. This is a parser/trace contract bug even before score parsing: parser output must be safe to commit and paste.
fix: Use an explicit allowlist for VitaBench normalized fields. Redact any key matching `authorization`, `api_key`, `token`, `secret`, or bearer-like values before writing result artifacts. Prefer fixing the VitaBench runner to avoid persisting secrets in native output, but parser must still defend against historical artifacts.
evidence: Redacted probe printed `contains_secret_key_path info.user_info.llm_args.headers.Authorization` and header keys `Accept`, `Authorization`, `Content-Type`; no token value is needed or included here. The same artifact safely exposes parser fields: task `10711001`, `max_steps=20`, `simulations=1`, `termination_reason=max_steps`, `duration=78.09s`.

COMMENT-READY for #1: VitaBench capped smoke needs benchmark-status and score-claim semantics, not `unknown`.
severity: MEDIUM
dedup: comment-on-#1
location: `reports/vitabench_repozero_worker_preflight_20260625.md:164-221`, `reports/vitabench_suite_entry_20260625.md:64-124`, `scripts/agentic_bench_suite.py:1142-1157`
static_repro: `_benchmark_result_for_run` with adapter `vitabench` returns `parser_status=no_parser`, `status=unknown`, `failure_category=native_artifact_missing` despite the shared native result file existing.
impact: The one-task VitaBench smoke is a harness/model-path pass, but the selected task terminated by the deliberate `VITA_MAX_STEPS=20` cap and reward `0.0`. Current parser output cannot classify this as completed capped smoke, so downstream aggregation may treat it as missing artifact or ignore the cap.
fix: Add `vitabench` parser that reads runner `run.env.summary` and native simulation JSON, extracts domain/task set/task id/trial/max_steps/termination/reward/cost, sets `benchmark_status=fail` or `partial` by native reward policy, and sets `score_claim_valid=false` with reason `capped_steps`.
evidence: Existing report records exit code 0, `Successfully completed all simulations`, `Tasks: 1`, `Simulations: 1`, termination `MAX_STEPS`, reward `0.0`. Native shared JSON confirms task id `10711001`, `max_steps=20`, `termination_reason=max_steps`.

COMMENT-READY for #1: CoCoA parser must classify task JSON `status:error` as infra_docker, not adapter pass or missing artifact.
severity: HIGH
dedup: comment-on-#1
location: `reports/cocoabench_worker_smoke_20260625.md:143-178`, `reports/cocoabench_worker_smoke_20260625.md:220-260`, `scripts/agentic_bench_suite.py:1142-1157`
static_repro: `_benchmark_result_for_run` with adapter `cocoabench` returns `parser_status=no_parser` and `failure_category=native_artifact_missing`; compare with shared artifact `runs/dev_worker_smoke_dryrun/cocoabench/results/linear-regime-estimation.json`.
impact: The suite launcher and adapter exited 0 and wrote `status: pass`, but the task did not run successfully. The native task result says `status: error` and `Sandbox environment failed to become ready`; `statistics.txt` says `Total Tasks: 1`, `Passed: 0`, `Errors: 1`, `Success Rate: 0.00%`. Without a CoCoA parser, infra failures can be confused with model failures, or worse, adapter success.
fix: Add `cocoabench` parser that reads `run.env.summary` for artifact root, per-task JSON files for `status/error/task_name`, `statistics.txt` for counts and token/cost totals, and `work/*/run.log` for Docker SDK/compose failure classification. Map Docker socket EOF to `benchmark_status=infra_error`, `failure_category=infra_docker`, `score_claim_valid=false`.
evidence: Shared artifact `results/linear-regime-estimation.json` contains `status=error` and `error=Sandbox environment failed to become ready`; task log includes Docker compose connect failure on `/tmp/rl/run/docker.sock/v1.45/version` with EOF; cost is `$0.000000`, indicating the task failed before useful model scoring.

COMMENT-READY for #1: controller `/tmp` summaries/logs from existing smokes are not durable shared parser inputs.
severity: MEDIUM
dedup: comment-on-#1
location: `reports/repozero_suite_execute_preflight_smoke_20260625.md:35-40`, `reports/tau2_proxy_smoke_20260625.md:95-102`, `reports/cocoabench_worker_smoke_20260625.md:136-169`
static_repro: on `dev`, check `/tmp/agentic_tau2_proxy_smoke3/summary.json`, `/tmp/agentic_repozero_exec_74640d5/summary.json`, and `/tmp/agentic_cocoa_worker_smoke/summary.json`.
impact: Existing reports cite local controller `/tmp` paths for `summary.json` and logs, but those paths are not present on the shared `dev` control plane. Future parser re-ingest, cross-agent validation, and issue comments must either rely on prose or on partial native shared artifacts. This undermines #1 because the result parser contract needs reproducible controller inputs, not only ephemeral local tmp files.
fix: For all suite smokes intended as evidence, require `--output-dir` under the shared project run root or copy controller `run_manifest.json`, `summary.json`, logs, status files, and normalized `results/*.result.json` to a shared artifact directory. Reports should cite shared paths only.
evidence: SSH probe on `dev` reported `exists_on_dev False` for `/tmp/agentic_tau2_proxy_smoke3/summary.json`, `/tmp/agentic_tau2_proxy_smoke3/logs/tau2_paper_core.log`, `/tmp/agentic_repozero_exec_74640d5/summary.json`, `/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log`, `/tmp/agentic_cocoa_worker_smoke/summary.json`, and `/tmp/agentic_cocoa_worker_smoke/logs/cocoabench.log`.

COMMENT-READY for #1: SWE-bench Verified parser needs explicit scaffold artifact hints; existing score report roots are not resolvable in this worktree.
severity: MEDIUM
dedup: comment-on-#1
location: `reports/qwen3_coder_swebench_qwen_code_retry_cases_20260529.md:11-23`, `manifests/suite.example.yaml:170-265`
static_repro: check the two run roots named in the report under `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/code_model_suites/.../qwen_native_outputs/..._paper_n500`; both were absent in the current shared tree. `_benchmark_result_for_run` returns `no_parser` for `mini_swe_agent` and other SWE-bench adapters.
impact: The report has a useful prose score, `245/500 = 49.0%`, with `completed=486`, `errors=1`, and `empty_patch=14`, but parser implementation cannot depend on prose or stale roots. The suite has four SWE-bench scaffold rows with different native output conventions; without per-scaffold artifact hints, a normalized parser cannot prove denominator, selected split, resolved count, empty patch count, or trace paths.
fix: Add per-scaffold `result_parser` hints in the suite plan or runner-emitted `AGENTIC_RESULT_JSON` pointers: Qwen Code native output root, `preds.json`, official eval report JSON, corrected score JSON when applicable, and per-instance trace/patch/log paths. If the declared score artifact is absent, emit `parser_status=parse_error` and `failure_category=native_artifact_missing` instead of `unknown`.
evidence: Current shared tree has many unrelated `preds.json` files, but the exact two Qwen Code roots cited by the report returned `exists False`. Current parser only special-cases RepoZero; SWE-bench adapters fall through to `parser_status=no_parser`.

COMMENT-READY for #1 and #7: Terminal-Bench 2.1 parser cannot see a selected task because the suite returns an empty plan for the disabled row.
severity: MEDIUM
dedup: duplicate-of-#7 for selection/preflight; comment-on-#1 for parser consequence
location: `manifests/suite.example.yaml:281-289`, `reports/terminal_bench_2_1_smoke_plan_20260625.md:25-35`, `reports/terminal_bench_2_1_smoke_plan_20260625.md:90-122`
static_repro: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --image-preflight-only --only terminal_bench_2_1 --model-profile dev_proxy_gpt54mini_8130 --output-dir /tmp/hunt_runner_tb_empty_probe` exits 0 with empty `results`.
impact: The planned smoke has clear parser inputs once it runs: `TB_TASK_IDS=fix-git`, task YAML, selected image tag, wrapper env, and future native Terminal-Bench result JSON. But today the suite produces no run, no preflight result row, and no normalized result artifact for the explicitly requested bench. A consumer cannot distinguish disabled/not-run from a successful empty audit.
fix: Resolve #7 at suite selection level, then add a `terminal_bench_2_1` parser that records selected task id, preflight/image status, TB CLI status, task pass/fail, test exit, timeout, and infra blocker. Until executable, explicit `--only terminal_bench_2_1` should produce a structured `not_run` or nonzero empty-plan result, not silent success.
evidence: Runtime lane found direct image check fails for required `fix-git`; runner lane confirmed suite preflight-only for the disabled row writes empty summary with status 0.

COMMENT-READY for #1: DeepSWE has historical trace JSONL/logs outside the suite run root, but the suite smoke has no artifact root and no parser.
severity: MEDIUM
dedup: comment-on-#1
location: `manifests/suite.example.yaml:267-279`, `reports/agentic_bench_landscape_20260625.md:96`, `reports/next_result_parser_contract_20260625.md:598-644`
static_repro: dry-run for `--only deepswe` plans `BENCH_RUN_DIR=/mnt/shared-storage-user/.../runs/dev_worker_smoke_dryrun/deepswe`; that directory does not exist. `_benchmark_result_for_run` with adapter `deepswe` returns `parser_status=no_parser`.
impact: DeepSWE parser semantics are more complex than a scalar exit code: partial runs need completed/errored/running/pending counts, rewards, exception types, timeouts, costs, and trajectory paths. Existing historical artifacts under `swe/bench/deepswe/source/runs_smoke` contain JSONL and logs for Qwen smoke runs, but they are not linked to the suite `run_id` or `BENCH_RUN_DIR`, so current suite execution cannot produce a normalized DeepSWE status.
fix: Require the DeepSWE runner to emit an `AGENTIC_RESULT_JSON` pointer or write a run summary under `BENCH_RUN_DIR`, including task ids, selected max tasks, trial states, reward values, exception types, cost/tokens, and trajectory/log paths. Parser should classify missing suite run root as `parse_error/native_artifact_missing`, historical partial runs as `benchmark_status=partial`, and Docker/model relay startup failures as `infra_error`.
evidence: Bounded shared-path probe found DeepSWE task files and historical `qwen3coder_smoke_k1*.jsonl`/run logs under `swe/bench/deepswe/source`, but `runs/dev_worker_smoke_dryrun/deepswe` does not exist. A sampled historical JSONL line includes `reward=0.0`, `exit_reason=llm_query_error`, and large verifier output; the run log also shows offline package download failure, reinforcing the need for explicit infra-vs-model classification.

## Round 2 commands and exit codes

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Remote git status/log and lane reads from active worktree: rc 0; head `c42f23c` with `main`, `origin/main`, and `feat/image-preflight-only` aligned.
- Read `hunt-runtime-images.md`: rc 0.
- Read current `hunt-runner-results.md`: rc 0.
- Read parser implementation/tests/reports/manifests: rc 0.
- Native artifact probes for RepoZero, tau2, VitaBench, CoCoA: rc 0.
- Broad SWE score-artifact find: rc 0 but found no exact cited `selective_retry_corrected_score.json` under known report roots.
- Broad DeepSWE recursive probe was interrupted after it became too wide: rc 255, replaced by bounded `find -maxdepth` probes.
- Bounded DeepSWE artifact probe: rc 0.
- Static `_benchmark_result_for_run` probes for tau2, VitaBench, CoCoA, SWE-bench, DeepSWE, Terminal-Bench: rc 0, all returned `parser_status=no_parser`.
- Terminal-Bench 2.1 `--image-preflight-only --only` empty-plan probe: rc 0, confirming empty summary.

## Next runner/result subdomain

Next loop should turn the comment-ready #1 evidence into parser fixture proposals: one redacted VitaBench JSON fixture, three tau2 result JSON fixtures, one CoCoA infra-error task fixture, one DeepSWE partial/infra JSONL fixture, and a SWE-bench scaffold artifact-hint schema. Do not implement parser code in this lane unless ownership changes.

## Round 3 normalized result artifact probe

Read first in this round:

- `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`
- `_coordination/20260625_harbor_bench/HANDOFF.md`
- `_coordination/20260625_harbor_bench/DRIVER.md`

Current state observed from active worktree:

- Head: `c42f23c Record runtime image hunt issues`.
- Existing dirty file before this round: this ledger only.
- `_execute_plan()` now writes `results/<bench_id>.result.json`, but `_benchmark_result_for_run()` only has a RepoZero parser. All other adapters below return `parser_status=no_parser`, `status=unknown`, and `failure_category=native_artifact_missing` even when machine-readable native artifacts exist.
- Bounded shared artifact search found no durable `*.result.json` under `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench` at maxdepth 7. Existing smokes predate the normalized writer or used local `/tmp` controller output.

### Current parser fallback matrix

Static probe: import `scripts/agentic_bench_suite.py` and call `_benchmark_result_for_run()` with `exit_code=0` for each adapter.

| Bench row | Adapter | Current parser_status | Current benchmark status | Current failure_category |
|---|---|---|---|---|
| `tau2_paper_core` | `tau2` | `no_parser` | `unknown` | `native_artifact_missing` |
| `vitabench_delivery_one_task_smoke` | `vitabench` | `no_parser` | `unknown` | `native_artifact_missing` |
| `cocoabench` | `cocoabench` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_qwen_code_smoke` | `swebench_verified_qwen_code` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_mini_swe_agent` | `mini_swe_agent` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_swe_agent` | `swe_agent` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_openhands` | `openhands` | `no_parser` | `unknown` | `native_artifact_missing` |
| `deepswe` | `deepswe` | `no_parser` | `unknown` | `native_artifact_missing` |
| `terminal_bench_2_1` | `terminal_bench_2_1` | `no_parser` | `unknown` | `native_artifact_missing` |

### Native artifact parseability matrix

| Bench | Native artifact state | Safe fields confirmed | Parser gap |
|---|---|---|---|
| tau2 | Three shared `results.json` files exist for airline, retail, telecom. | each has `tasks=1`, `simulations=1`, `max_steps=60`, per-simulation `task_id`, `termination_reason=user_stop`, duration, and reward `0.0`. | Should parse as completed smoke with reward metrics, not `unknown`. |
| VitaBench | One shared native JSON exists for delivery task `10711001`. | `tasks=1`, `simulations=1`, `max_steps=20`, `termination_reason=max_steps`, duration `78.09s`, reward `0.0`. | Should parse as capped smoke, but must redact secrets before normalizing. |
| CoCoA | Shared task result JSON and `statistics.txt` exist. | task `linear-regime-estimation`, `status=error`, `error=Sandbox environment failed to become ready`, statistics file present. | Should parse as `infra_error/infra_docker`, not `unknown`. |
| SWE-bench Verified | Report has prose score, but the two cited Qwen Code roots are absent in the current shared tree. | `cited_roots_exist=[false,false]`. Many unrelated `preds.json` files exist elsewhere, but not the cited score artifact. | Needs explicit scaffold result pointers; cannot claim score from prose or stale roots. |
| DeepSWE | Historical JSONL trace exists outside suite run root. | sampled trace has `docker_image`, `exp_name=qwen3coder_smoke_k1`, `reward=0.0`, `exit_reason=llm_query_error`, `test_output` present, empty `trajectory_steps`. | Needs runner-emitted suite run summary or `AGENTIC_RESULT_JSON`; current suite `BENCH_RUN_DIR` does not exist. |
| Terminal-Bench 2.1 | Planned artifacts only; selected `fix-git/task.yaml` exists, but no native result root. | `task_yaml_exists=true`, suite result root absent, native result absent. | Parser should emit structured `not_run`/infra-blocked once selection issue #7 is fixed; no task score is parseable yet. |

ISSUE-FILED: #9 VitaBench result parser must redact native Authorization headers before emitting normalized artifacts
severity: HIGH
dedup: filed as #9
location: `scripts/agentic_bench_suite.py:1130-1182`; native artifact `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/data/simulations/bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847`
static_repro: `python3 - <<'PY'` read the VitaBench native JSON, inspect only key presence under `info.user_info.llm_args.headers`, and print `authorization_header_key_present=True`; do not print the value.
impact: Current suite code does not parse VitaBench yet, so today's normalized result would be `no_parser/unknown`. The native VitaBench artifact is still unsafe input for a future parser: it persists an `Authorization` header under `info.user_info.llm_args.headers`. A naive parser that copies native `info`, `llm_args`, headers, or raw simulation blobs into `agentic_bench.result.v1`, fixtures, reports, or GitHub comments can leak a live credential while trying to fix #1.
fix: Implement VitaBench parser with an explicit allowlist, not recursive copying. Safe fields should be limited to metadata and score fields such as `timestamp`, `info.git_commit`, `info.num_trials`, `info.max_steps`, selected domain/task identifiers, per-simulation `task_id`, `termination_reason`, `reward_info`, `duration`, `agent_cost`, and `user_cost`. Add a generic redaction pass for all result artifacts that replaces values for case-insensitive key matches including `authorization`, `api_key`, `token`, `secret`, `headers`, and bearer-like strings. Add a fixture containing only a synthetic secret value and assert normalized output contains neither the value nor unsafe parent objects.
evidence: Redacted probe output: `path_exists True`, `authorization_header_key_present True`, `unsafe_parent_path info.user_info.llm_args.headers`, and safe parser fields `task_id=10711001`, `max_steps=20`, `termination_reason=max_steps`, `duration=78.09s`, `reward=0.0`. No token value was printed or written.

COMMENT-READY for #1: Non-RepoZero normalized artifacts currently collapse parseable native results into no_parser/unknown
severity: HIGH
dedup: comment-on-#1
location: `scripts/agentic_bench_suite.py:1130-1157`, `scripts/agentic_bench_suite.py:1160-1182`
static_repro: `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'` import `scripts/agentic_bench_suite.py`, call `_benchmark_result_for_run()` for tau2, VitaBench, CoCoA, SWE-bench adapters, DeepSWE, and Terminal-Bench 2.1 with `exit_code=0`.
impact: The normalized result writer exists, but most one-command suite rows still produce semantic `unknown` rather than benchmark status. For tau2/VitaBench/CoCoA/DeepSWE this loses parseable native evidence; for SWE-bench it hides missing/stale artifact roots; for Terminal-Bench it hides not-run/planned state. Downstream aggregation cannot distinguish model failure, capped smoke, infra Docker failure, missing artifact, or planned-not-run.
fix: Add parser registry keyed by adapter/benchmark with explicit source discovery and per-bench status mapping. Until a parser exists, emit `parser_status=no_parser` but use a more accurate `benchmark_status=not_scored` and `failure_category=parser_unsupported`, not `native_artifact_missing`, because native artifacts may exist but parser support is absent.
evidence: Static parser probe returned `no_parser unknown native_artifact_missing` for all of `tau2_paper_core`, `vitabench_delivery_one_task_smoke`, `cocoabench`, `swebench_verified_qwen_code_smoke`, `swebench_verified_mini_swe_agent`, `swebench_verified_swe_agent`, `swebench_verified_openhands`, `deepswe`, and `terminal_bench_2_1`.

## Round 3 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0, output truncated by tool after reading.
- `ssh dev 'cd <active worktree> && pwd && git status --short && git rev-parse --short HEAD && git log --oneline -5'`: rc 0; head `c42f23c`; only this ledger was dirty.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `_coordination/20260625_harbor_bench/DRIVER.md`: rc 0.
- Tail current `hunt-runner-results.md`: rc 0.
- First parser-status probe: rc 1 due shell quoting of Python f-string field names; no repo files changed.
- Re-run parser-status probe with `PYTHONDONTWRITEBYTECODE=1` and safer printing: rc 0; all non-RepoZero rows above returned `no_parser/unknown`.
- Inspect parser implementation lines `1092-1225`: rc 0.
- Bounded search for shared `*.result.json` under `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`: rc 0; no paths printed.
- Native artifact parseability probe for tau2/VitaBench/CoCoA/DeepSWE/SWE-bench/Terminal-Bench: rc 0; printed only safe fields and secret key presence, not secret values.
- VitaBench redaction-specific key-path probe: rc 0; printed only `authorization_header_key_present=True` and allowlist candidates.

## Next runner/result subdomain

Next loop should draft concrete fixture contracts for the parser registry without changing production code: fixture path names, required expected normalized JSON snippets, and per-bench parser ownership. Prioritize VitaBench redaction fixture before any Vita parser implementation.
## Round 4 parser fixture and secret-redaction probe

Scope for this round:

- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Write set observed: this ledger only. Production code and manifests were inspected but not edited.
- No benchmark execution, no model request, no Docker mutation, and no secret value printing.
- Handoff now says #9 tracks the VitaBench native Authorization-header redaction risk, so new Vita evidence below is `comment-on-#9`, not a duplicate issue.

### Static parser state re-confirmed

Current `scripts/agentic_bench_suite.py` has process/result artifact plumbing but still only parses RepoZero:

- `_redact_env()` at `scripts/agentic_bench_suite.py:480-498` redacts runtime env values, but there is no equivalent generic sanitizer for native result documents.
- `_repozero_benchmark_result()` at `scripts/agentic_bench_suite.py:1145-1173` is the only concrete parser.
- `_benchmark_result_for_run()` at `scripts/agentic_bench_suite.py:1176-1203` returns `parser_status=no_parser`, `benchmark_result.status=unknown`, and `failure_category=native_artifact_missing` for every non-RepoZero adapter with exit code 0.
- `_attach_benchmark_result()` at `scripts/agentic_bench_suite.py:1206-1228` writes `agentic_bench.result.v1`; a future parser that copies raw native objects would persist them under `results/<bench_id>.result.json`.

Static probe matrix, exit code 0:

| Bench row | Adapter | Current parser_status | Current benchmark status | Current failure_category |
|---|---|---|---|---|
| `tau2_paper_core` | `tau2` | `no_parser` | `unknown` | `native_artifact_missing` |
| `vitabench_delivery_one_task_smoke` | `vitabench` | `no_parser` | `unknown` | `native_artifact_missing` |
| `cocoabench` | `cocoabench` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_qwen_code_smoke` | `swebench_verified_qwen_code` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_mini_swe_agent` | `mini_swe_agent` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_swe_agent` | `swe_agent` | `no_parser` | `unknown` | `native_artifact_missing` |
| `swebench_verified_openhands` | `openhands` | `no_parser` | `unknown` | `native_artifact_missing` |
| `deepswe` | `deepswe` | `no_parser` | `unknown` | `native_artifact_missing` |
| `terminal_bench_2_1` | `terminal_bench_2_1` | `no_parser` | `unknown` | `native_artifact_missing` |

### Native artifact probe results

Safe read-only artifact probe, exit code 0:

| Bench | Existing native input | Safe evidence | Parser contract gap |
|---|---|---|---|
| VitaBench | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/data/simulations/bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847` | key path present: `info.user_info.llm_args.headers.Authorization`; parent keys: `Accept`, `Authorization`, `Content-Type`; `tasks=1`, `simulations=1`, `task_id=10711001`, `max_steps=20`, `termination_reason=max_steps`, reward value is zero. | Must parse by allowlist and redact by path/key before writing normalized result, fixtures, or issue comments. |
| tau2 | Three `results.json` files under `tau2-bench/data/simulations/bench_gpt-5.4-mini_tau2_{airline,retail,telecom}_dev_worker_smoke_dryrun/` | each exists; each has one task, one simulation, `max_steps=60`, `termination_reason=user_stop`, reward value zero. | Parseable smoke evidence currently normalizes as `no_parser/unknown`. |
| CoCoA | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/results/linear-regime-estimation.json` plus `statistics.txt` | task result exists; `status=error`; error says sandbox environment failed to become ready; stats are `Total Tasks: 1`, `Passed: 0`, `Failed: 0`, `Errors: 1`. | Should normalize as `infra_error` with Docker/sandbox category, not unknown or model failure. |
| DeepSWE | Historical JSONL `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe/source/runs_smoke/traj_k1/qwen3coder_smoke_k1.jsonl`; suite run dir absent. | first row has `exp_name=qwen3coder_smoke_k1`, a SWE-bench image ref, reward zero, `exit_reason=llm_query_error`, test-output field present, and zero trajectory steps; `runs/dev_worker_smoke_dryrun/deepswe` is absent. | Historical JSONL is parseable only as a fixture; suite execution needs an `AGENTIC_RESULT_JSON` pointer or `BENCH_RUN_DIR` summary. |
| SWE-bench Verified | Existing prose report cites Qwen Code roots, but the two checked roots are absent in the shared tree. | both cited native roots checked in this round returned `exists=False`. | Parser must require artifact hints and must fail closed as `parse_error/native_artifact_missing` when declared score artifacts are absent. |
| Terminal-Bench 2.1 | YAML task exists for `fix-git`, but suite native result root is absent. | `task_yaml_exists=True`, `native_result_root_exists=False`. | Parser fixture should represent planned/not-run or image-preflight-blocked state without inventing a score numerator. |

### Parser fixture contracts to implement later

Do not store the raw VitaBench native JSON as a fixture. Store minimized synthetic fixtures that preserve schema shape and safe field names but use non-secret sentinel values.

1. `tests/fixtures/result_parsers/vitabench_delivery_redaction/native_result.json`

Input contract:

- Include top-level `timestamp`, `info.max_steps=20`, `tasks` with one delivery task id, and `simulations` with one `task_id=10711001`, reward zero, and `termination_reason=max_steps`.
- Include a synthetic `info.user_info.llm_args.headers.Authorization` key only to prove redaction. The value must be a harmless sentinel, not copied from the native artifact.
- Include sibling header names `Accept` and `Content-Type` to ensure the parser removes the unsafe parent object, not just one key.

Expected normalized result:

- `parser.status=parsed`, `benchmark_result.status=fail`, `benchmark_result.metric=reward`, `benchmark_result.reward_avg=0.0`.
- `score_claim.valid_for_leaderboard=false`, `score_claim.reason=capped_steps`, `failure.failure_category=capped_steps`.
- `cases[0].case_id=10711001`, `cases[0].termination_reason=max_steps`, and artifact pointers recorded under `source.native_artifacts`.
- No `info.user_info`, `llm_args`, header object, or header value is copied into the normalized result. A redaction metadata entry may name the path only.
- A recursive serialized-output assertion must fail if the output contains known secretish keys as data fields or the synthetic sentinel value.

2. `tests/fixtures/result_parsers/cocoabench_infra_error/`

Input contract:

- `results/linear-regime-estimation.json` with `task_name=linear-regime-estimation`, `status=error`, and the sandbox-ready error string.
- `results/statistics.txt` with `Total Tasks: 1`, `Passed: 0`, `Failed: 0`, `Errors: 1`.
- Optional `work/.../run.log` excerpt minimized to the Docker/SDK/compose readiness failure, with no environment dump.

Expected normalized result:

- `execution.status=pass` when adapter exit code is 0, but `benchmark_result.status=infra_error`.
- `failure.infra_error=true`, `failure.failure_category=infra_docker` or `infra_sandbox_startup` if a narrower category is added.
- `score_claim.valid_for_leaderboard=false`, `score_claim.reason=infra_blocked`, `tasks_total=1`, `tasks_passed=0`, and no model-failure category.

3. `tests/fixtures/result_parsers/deepswe_historical_jsonl_llm_query_error/`

Input contract:

- One pruned JSONL row derived from the historical schema with safe fields only: `exp_name`, `docker_image`, `reward`, `exit_reason=llm_query_error`, `trajectory_steps=[]`, and boolean markers for verifier output presence.
- Do not include full prompts, full test output, environment dumps, or tokens.
- Include a missing suite `BENCH_RUN_DIR` case separately to exercise parser discovery failure.

Expected normalized result:

- Historical row fixture: `parser.status=parsed`, `benchmark_result.status=infra_error` or `partial` only if mixed pending/running rows are present; for single `llm_query_error`, prefer `infra_error` with `failure.failure_category=infra_model_endpoint`.
- Missing suite run dir fixture: `parser.status=parse_error`, `benchmark_result.status=parse_error`, `failure.failure_category=native_artifact_missing`.
- `score_claim.valid_for_leaderboard=false` and no copied verifier text.

4. SWE-bench artifact-hint schema fixture

Input contract:

- A synthetic suite row or parser plan with:
  - `result_parser.id=swebench_qwen_code` or scaffold-specific equivalent.
  - `artifact_hints.native_output_root`.
  - `artifact_hints.corrected_score_json` for `selective_retry_corrected_score.json` when available.
  - `artifact_hints.official_eval_report_json` for official SWE-bench eval output when available.
  - `artifact_hints.preds_json`, `artifact_hints.trajectory_root`, `artifact_hints.patch_root`, `artifact_hints.selected_instances`, and `artifact_hints.denominator`.

Expected normalized result:

- If declared artifacts exist: parse `resolved_count`, denominator, completed/error/empty-patch counts, and per-instance paths.
- If declared artifacts are absent, as with the checked roots this round: `parser.status=parse_error`, `benchmark_result.status=parse_error`, `failure.failure_category=native_artifact_missing`, `score_claim.valid_for_leaderboard=false`.
- Never parse a leaderboard score from prose alone as `parsed`; at most `parser.status=partial` with invalid score claim.

5. `tests/fixtures/result_parsers/terminal_bench_2_1_native_absent/`

Input contract:

- `task.yaml` path for a selected task exists.
- Native result root is absent.
- Optional image-preflight summary fixture can state required image missing or known-bad load.

Expected normalized result:

- Disabled/not-selected bench: no result artifact should be emitted.
- Explicitly selected but preflight-blocked bench: `execution.status=not_run` or adapter `fail` depending call path, `benchmark_result.status=infra_error`, `failure.failure_category=infra_image_preflight`, no task numerator, invalid score claim.
- Explicitly selected adapter pass with absent native result: `parser.status=parse_error`, `benchmark_result.status=parse_error`, `failure.failure_category=native_artifact_missing`.

COMMENT-READY for #9: Add a VitaBench redaction fixture before implementing the native parser
severity: HIGH
dedup: comment-on-#9
location: `scripts/agentic_bench_suite.py:480-498`, `scripts/agentic_bench_suite.py:1176-1203`, `scripts/agentic_bench_suite.py:1206-1228`; native artifact path above
static_repro: Read the native VitaBench JSON and print only whether `info.user_info.llm_args.headers.Authorization` exists plus safe fields such as task id, max steps, termination reason, and reward. Do not print the value.
impact: #1 requires non-RepoZero parsers, and VitaBench is one of the first parseable smokes. Without a redaction fixture, a future parser can make #1 green while leaking a credential from the native `info.user_info.llm_args.headers` object into normalized result JSON, checked-in fixtures, reports, or GitHub comments.
fix: Implement the VitaBench parser with an explicit allowlist and add a generic result redaction pass before writing `agentic_bench.result.v1`. Add a synthetic redaction fixture that includes the unsafe key path with a harmless sentinel value and asserts the normalized output contains neither the sentinel nor copied header/user-info objects. Permit path names in redaction metadata only.
evidence: Safe probe returned `unsafe_key_path_present True`, `unsafe_parent_path info.user_info.llm_args.headers`, parent keys `Accept,Authorization,Content-Type`, `tasks=1`, `simulations=1`, `task_id=10711001`, `max_steps=20`, `termination_reason=max_steps`, and zero reward. No secret value was printed or written.

COMMENT-READY for #1: Add bench-specific parser fixtures for native artifacts that currently normalize as unknown
severity: HIGH
dedup: comment-on-#1
location: `scripts/agentic_bench_suite.py:1176-1203`; `reports/next_result_parser_contract_20260625.md:271-507`
static_repro: Import `scripts/agentic_bench_suite.py` with `PYTHONDONTWRITEBYTECODE=1`, call `_benchmark_result_for_run()` for tau2, VitaBench, CoCoA, SWE-bench adapters, DeepSWE, and Terminal-Bench 2.1 with `exit_code=0`, then compare to the native artifact probes above.
impact: The suite now emits normalized result files, but non-RepoZero rows still lose benchmark semantics. Parseable tau2/VitaBench/CoCoA/DeepSWE inputs are flattened to `unknown`, while SWE-bench and Terminal-Bench missing artifacts are also flattened to the same `unknown/native_artifact_missing` state. Aggregation cannot distinguish model failure, capped smoke, infra sandbox failure, missing declared score artifact, and not-run/preflight-blocked state.
fix: Add a parser registry plus fixture-first tests for VitaBench redaction, CoCoA infra error, DeepSWE historical JSONL and missing run dir, SWE-bench artifact hints, and Terminal-Bench 2.1 native absence. Until parser support exists, use `failure_category=parser_unsupported` for unsupported adapters and reserve `native_artifact_missing` for declared artifacts that were actually looked up and absent.
evidence: Static parser matrix above returned `no_parser/unknown/native_artifact_missing` for all inspected non-RepoZero adapters, while read-only native artifact probes found parseable tau2, VitaBench, CoCoA, and DeepSWE historical inputs and distinct missing-artifact states for SWE-bench and Terminal-Bench 2.1.

### Cross-lane runtime alignment

CONFIRM runtime Round 2 comments for #6/#7: Terminal-Bench 2.1 parser fixtures should not depend on the current `fix-git` target as a scoreable smoke. The runtime ledger shows several load-smoked TB2.1 images but the existing suite row is disabled and the current `fix-git` tar is known bad. Parser-side consequence is `comment-on-#1` for native-result absence and `duplicate/comment-on-#7` for selection reachability, not a new runner issue.

DUPLICATE note: VitaBench redaction is already filed as #9. This round adds fixture-ready detail and code-location evidence for #9 rather than opening another issue.

## Round 4 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0 in this task before remote work; output was read, with tool truncation.
- `ssh dev 'cd <image-warmup-policy> && pwd && git status --short && git rev-parse --short HEAD && git log --oneline -5 && tail -n 80 <ledger>'`: rc 0; head `c42f23c`; worktree already had concurrent dirty production files and this ledger before this round.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`, `DRIVER.md`, and `lanes/hunt-runtime-images.md`: rc 0.
- Inspect parser/result code, suite manifest rows, and result tests with `rg`, `nl`, and `sed`: rc 0.
- Static `_benchmark_result_for_run()` probe for non-RepoZero adapters: rc 0; all returned `no_parser/unknown/native_artifact_missing`.
- First native artifact probe: rc 127 due shell quoting before successful parsing; no repo files changed and no secret value was printed.
- Re-run native artifact probe by streaming Python over SSH stdin: rc 0; printed only safe fields and VitaBench risky key-path presence.
- Read `reports/next_result_parser_contract_20260625.md` benchmark-specific contract sections: rc 0.

## Next runner/result subdomain

Next loop should inspect whether current adapter logs reliably emit artifact pointer lines (`artifact=`, `done:`, `run_dir=`, or future `AGENTIC_RESULT_JSON`) for tau2, VitaBench, CoCoA, RepoZero, and DeepSWE. The parser registry cannot be robust until source discovery is deterministic and redacted.
## Round 4 validation evidence

- Append Round 4 ledger section via remote Python over SSH stdin: rc 0.
- `git status --short -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md && git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; only the lane ledger is modified in the assigned path and diff whitespace check passed.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0 through an inverted check; no trailing whitespace matches.
- Strict secret-pattern scan for token-like strings in the ledger: rc 0 through an inverted check; no matches printed.
- Tail final ledger for sanity: rc 0.
## Round 5 adapter artifact pointer/result contract

Scope for this round:

- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` at pushed commit `edae6f2`.
- Write set: this ledger only. No production code, manifests, Docker state, benchmark execution, or model calls.
- Static/bounded reads only: suite dry-run JSON, shared legacy wrappers under `/data/nips/bench`, current branch scripts/reports, and existing run artifacts.
- Secret policy: probes reported key-path/presence only; no token values were printed or written.

### Current suite pointer surface

The suite always exports a `BENCH_RUN_DIR`, but it does not expose parser hints in the run manifest:

- `_remote_body()` creates `BENCH_RUN_DIR`, `cd`s to `bench_root`, and executes `./<adapter_script>`; see `scripts/agentic_bench_suite.py:523-538`.
- `build_run_plan()` sets `BENCH_RUN_DIR=<run_root>/<suite_id>/<bench_id>` and `RUN_TAG=<suite_id>`; see `scripts/agentic_bench_suite.py:788-799`.
- Dry-run probe for enabled rows found `has_bench_run_dir=True` for RepoZero, VitaBench, CoCoA, DeepSWE, all SWE-bench scaffolds, and `terminal_bench_2_1_image_smoke`, but `has_result_parser_field=False` and `has_artifact_hints=False` for all of them.
- No `AGENTIC_RESULT_JSON` emission exists in current `scripts/`, `manifests/`, or reports except as a proposed future contract in `reports/next_result_parser_contract_20260625.md`.

`/data/nips/bench/lib/bench_common.sh:223-227` defines the legacy pointer contract:

- append `artifact=<path>` to `$BENCH_RUN_DIR/run.env.summary`.
- print `done: <path>` to stdout.

That is useful but not enough for every adapter because some wrappers write richer `artifact_manifest.json`, some only point at a parent directory, and some sidecar files under `BENCH_RUN_DIR` are secret-bearing.

### Adapter pointer matrix

| Adapter / bench | Pointer emitted by wrapper | Existing artifact evidence | Parser blocker / redaction risk |
|---|---|---|---|
| RepoZero Py2JS | `run_repozero_py2js.sh:96-100` writes `command.sh`, `repozero_py2js.log`, then `bench_finish <RepoZero/Py2JS/output_codex/run_name>`. | Existing `run.env.summary` has `artifact=/mnt/.../RepoZero/Py2JS/output_codex/gpt-5.4-mini_dev_worker_smoke_dryrun_smoke`; no `artifact_manifest.json`. | Pointer is stable enough for current RepoZero parser, but normalized result still does not record native artifact root. |
| VitaBench | `run_vitabench.sh:101-106` writes `command.sh`, `vitabench.log`, then `bench_finish <VitaBench/data/simulations/save_to>`. | Historical `run.env.summary` has a native simulation artifact path. Existing `vita_models.yaml` has a secret-pattern match; native simulation JSON also has `info.user_info.llm_args.headers.Authorization` from prior #9 evidence. | Parser can discover native result from `artifact=`, but must avoid copying `vita_models.yaml`, raw `info.user_info`, or raw headers. Dedup to #9 for Vita-native header risk. |
| CoCoA | `run_cocoabench.sh:149-153` writes `command.sh`, `cocoabench.log`, then `bench_finish $COCOA_OUTPUT_DIR`; config intentionally writes empty `api_key` at line 66. | Existing `run.env.summary` points to `.../cocoabench/results`; task result and `statistics.txt` exist. No `artifact_manifest.json`. | Pointer is sufficient for a parser; absence of manifest means parser must know CoCoA result file conventions under the results dir. |
| tau3-bench | `run_tau3_bench.sh:30-39` writes run metadata; `run_tau3_bench.sh:86-89` can `bench_finish $TAU3_DATASET_DIR` when Harbor run is skipped; real Harbor run logs to `tau3_harbor.log` and `bench_finish $TAU3_JOBS_DIR` at lines 92-94. | Existing verification summaries show `tau3_harbor_run=skipped` and `artifact=<dataset_dir>`. Command artifacts use placeholder API-key assignments, not non-placeholder values. | A parser must not treat a skipped-Harbor dataset artifact as a benchmark result. Need explicit `tau3_harbor_run` state and jobs/result discovery, not just `artifact=`. |
| DeepSWE | `run_deepswe.sh:247-289` writes `artifact_manifest.json` and `bench_finish <Pier result.json>` only after Pier result exists. `run_deepswe.sh:147-159` writes secret-bearing `pier.env`. | Historical `artifact_manifest.json` includes safe keys: `pier_job_dir`, `result_json`, `pier_log`, `command`, `env_summary`, and summary counts. Historical `pier.env` has a secret-pattern match. Current suite `runs/dev_worker_smoke_dryrun/deepswe` does not exist. | Parser should prefer `artifact_manifest.json` and `result_json`; never copy `pier.env`. For missing suite run dirs, report `parse_error/native_artifact_missing`. |
| SWE-bench Qwen Code | `run_swebench_verified_qwen_code.sh:42-48` passes `--base-url`, `--api-key`, output parent, namespace, and run name; `run_swebench_verified_qwen_code.sh:74-78` writes full command and `bench_finish <out_parent/run_name>`. | No current suite run dir exists for `swebench_verified_qwen_code_smoke`. Static code shows `command.sh` would include the expanded `--api-key` argument. | Strong secret-sidecar risk plus missing score artifact contract. Parser must require explicit score/preds/artifact hints and must not read `command.sh` as raw evidence. |
| SWE-bench mini-swe-agent | `run_swebench_verified_mini_swe_agent.sh:60-83` writes `artifact_manifest.json` with `predictions`, `agent_trace_root`, config snapshot, log, and command, then `bench_finish $MINI_SWE_OUTPUT_DIR`. | No current suite run dir exists. | Pointer contract is good if the run succeeds; parser still needs score/eval report mapping from predictions to native verifier result. |
| SWE-agent scaffold | `run_swebench_verified_swe_agent.sh` execs `run_swebench_verified.sh`; `run_swebench_verified.sh:137-160` writes `artifact_manifest.json` with `predictions`, trace root, eval log, and command, then `bench_finish <preds.json>`. | No current suite run dir exists. Static config substitution stores `api_key: $OPENAI_API_KEY` as a placeholder in the generated config, not the value. | Parser can use manifest after success, but current suite does not parse non-RepoZero and does not handle missing/new stale run dirs. |
| OpenHands scaffold | `run_swebench_verified_openhands.sh:28-71` writes config TOML under `BENCH_RUN_DIR`; the here-doc expands `api_key = "$OPENAI_API_KEY"`. `run_swebench_verified_openhands.sh:135-163` writes `artifact_manifest.json`, then `bench_finish <output.jsonl>`. | No current suite run dir exists. | Strong secret-sidecar risk in config snapshot plus need to parse output/eval logs. Parser must not copy config TOML and must redact any config-derived fields. |
| Terminal-Bench 2.1 image smoke | repo wrapper `scripts/run_terminal_bench_2_1_smoke.sh:124-132` prints `run_dir`, image, runner, and docker host. Shared runner writes `artifact_manifest.json` at `run_terminal_bench_2_1.sh:119-136`, exits nonzero before `bench_finish` when `tb_rc != 0`, and only calls `bench_finish $artifact` at line 141 on success. | Enabled suite row is `terminal_bench_2_1_image_smoke`, but `adapter_status=pending_adapter`, so `--execute` refuses before adapter launch. Current suite run dir does not exist. | Parser cannot observe TB2.1 native results through suite today. Even after wiring, current `_benchmark_result_for_run()` short-circuits nonzero adapter exits and would ignore a TB `artifact_manifest.json` written before nonzero exit. |

ISSUE-FILED: #10 Secret-bearing adapter sidecars under BENCH_RUN_DIR must be excluded from normalized parser sources
severity: HIGH
dedup: filed as #10
location: `/data/nips/bench/run_vitabench.sh:25-61`, `/data/nips/bench/run_deepswe.sh:147-159`, `/data/nips/bench/run_swebench_verified_qwen_code.sh:42-78`, `/data/nips/bench/run_swebench_verified_openhands.sh:28-71`, `scripts/agentic_bench_suite.py:1206-1228`
static_repro: Statically inspect the listed wrapper lines, then run a safe key-presence probe over existing artifacts that prints only `secret_pattern_present` booleans for historical `vita_models.yaml`, tau3 command files, DeepSWE `artifact_manifest.json`, and DeepSWE `pier.env`.
impact: Parser work for #1 will naturally read `BENCH_RUN_DIR` to find logs, manifests, and native result pointers. Several adapters either already persist secret-bearing sidecars under that directory or would do so on their first suite execution. A parser or GitHub issue comment that copies raw `command.sh`, model configs, env files, config snapshots, or raw native metadata can leak live credentials while trying to normalize benchmark results.
fix: Implement parser source allowlists per adapter. Only read `run.env.summary`, `artifact_manifest.json`, selected native result files, and short safe log excerpts. Add a generic recursive sanitizer before writing `agentic_bench.result.v1` that removes secretish keys/values and refuses to serialize sidecar file contents. Change wrappers over time to write placeholders in `command.sh`/config snapshots instead of values, especially Qwen Code and OpenHands. Keep `pier.env` and Vita model config out of parser-visible artifacts.
evidence: Safe probe returned `secret_pattern_present=True` for existing Vita `vita_models.yaml` and existing DeepSWE `pier.env`; DeepSWE `artifact_manifest.json` returned `secret_pattern_present=False` and safe keys only; tau3 verification command files had API-key assignment placeholders with `nonplaceholder_count=0`. Static code shows Qwen Code writes an expanded `--api-key` argument to `command.sh`, and OpenHands writes expanded `api_key` into `config.toml`. No secret value was printed.

COMMENT-READY for #1: Adapter result discovery needs a first-class pointer contract, not only legacy artifact lines
severity: HIGH
dedup: comment-on-#1
location: `scripts/agentic_bench_suite.py:1176-1203`, `/data/nips/bench/lib/bench_common.sh:223-227`, `/data/nips/bench/run_tau3_bench.sh:86-94`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh:117-141`
static_repro: Build a dry-run plan for `manifests/suite.example.yaml`, inspect enabled runs for `result_parser` and `artifact_hints`, then inspect adapter wrappers for `bench_finish`, `artifact_manifest.json`, and nonzero-exit behavior.
impact: Legacy `artifact=` and `done:` lines give parsers a starting point, but they do not distinguish native score artifacts from skipped setup artifacts, nor do they survive all failure modes. tau3 can exit 0 with `artifact=<dataset_dir>` when Harbor execution is skipped; Terminal-Bench writes an `artifact_manifest.json` before returning `tb_rc`, but the suite currently classifies any nonzero adapter exit as `parser_status=not_run` and never attempts to parse that manifest. Downstream aggregation will keep mixing setup success, native score absence, infra failure, and benchmark failure.
fix: Add `result_parser` and `artifact_hints` to run plans or require `AGENTIC_RESULT_JSON` from adapters. Parser execution should run even on nonzero adapter exits in a read-only mode, so infra/result artifacts can classify `infra_error`, `parse_error`, or partial benchmark status. Each adapter should emit a structured pointer with `artifact_kind` such as `native_score`, `native_result_dir`, `setup_dataset_only`, `trace_root`, or `image_preflight_only`.
evidence: Dry-run probe returned `has_result_parser_field=False` and `has_artifact_hints=False` for all inspected rows. `bench_common.sh` only emits text `artifact=`/`done:`. Existing tau3 verification summaries have `tau3_harbor_run=skipped` and `artifact=<dataset_dir>`. The TB2.1 shared runner writes manifest pointers before nonzero exit, but `scripts/agentic_bench_suite.py:1176-1187` returns `parser_status=not_run` for any nonzero execution result.

COMMENT-READY for #2: Fixed BENCH_RUN_DIR makes adapter pointer files stale or overwritten across invocations
severity: HIGH
dedup: comment-on-#2
location: `scripts/agentic_bench_suite.py:788-789`
static_repro: Build a dry-run plan and inspect `runtime_env.BENCH_RUN_DIR`; each bench resolves to `<run_root>/<suite_id>/<bench_id>` with `RUN_TAG=<suite_id>`, not an invocation-unique path.
impact: Adapter pointer files such as `run.env.summary`, `artifact_manifest.json`, command logs, and native symlinks are overwritten or left stale across repeated `--execute` attempts for the same suite/bench. Parser discovery from `BENCH_RUN_DIR` can silently parse an earlier run after a failed launch, or concurrent agents can race on the same pointer file.
fix: Implement #2 before broad parser rollout: add an invocation id or timestamp under `BENCH_RUN_DIR` and make summary/result artifacts point at the exact invocation directory. Keep a stable latest symlink only as convenience, never as parser source of truth.
evidence: Dry-run table showed stable paths like `/mnt/.../runs/dev_worker_smoke_dryrun/repozero_py2js_smoke`, `/mnt/.../runs/dev_worker_smoke_dryrun/cocoabench`, and `/mnt/.../runs/dev_worker_smoke_dryrun/deepswe` for every invocation of the same suite row.

COMMENT-READY for #9: Vita redaction must cover both native result headers and wrapper model config
severity: HIGH
dedup: comment-on-#9
location: `/data/nips/bench/run_vitabench.sh:25-61`, `/data/nips/bench/run_vitabench.sh:101-106`
static_repro: Inspect `run_vitabench.sh` model-config generation and safely check existing `vita_models.yaml` for token-pattern presence without printing the value.
impact: #9 already covers `info.user_info.llm_args.headers.Authorization` inside the native VitaBench simulation JSON. The wrapper also writes `vita_models.yaml` under `BENCH_RUN_DIR` with an Authorization header when `OPENAI_API_KEY` is set. A future parser that scans the entire run dir or embeds command/config sidecars can leak the same credential even if the native simulation parser is allowlisted.
fix: Extend #9 acceptance criteria: Vita parser may read `run.env.summary`, `vitabench.log` excerpts, and the native simulation JSON through a strict allowlist, but must never copy `vita_models.yaml` or raw `info.user_info.llm_args.headers`. Add a fixture asserting both native JSON and wrapper config secret carriers are excluded from normalized output.
evidence: Safe probe found existing `vita_models.yaml` with `secret_pattern_present=True`; prior #9 evidence found native key path `info.user_info.llm_args.headers.Authorization`. No secret value was printed.

### Round 5 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; output read before remote work, tool truncated display.
- Memory quick search in `/Users/Zhuanz1/.codex/memories/MEMORY.md`: rc 0; no actionable current repo note was used.
- `ssh dev 'cd <image-warmup-policy> && pwd && git rev-parse --short HEAD && git status --short && git log --oneline -5 && sed ... HANDOFF.md && sed ... DRIVER.md'`: rc 0; head `edae6f2`.
- `rg --files` for repo run scripts and pointer search over scripts/manifests/reports/coordination: rc 0; repo has suite launcher plus TB smoke wrapper, while legacy adapters are under `/data/nips/bench`.
- Read runtime lane and current runner-results ledger tail: rc 0.
- Inspect suite command construction and local wrappers with `nl`/`sed`: rc 0.
- First dry-run JSON parser probe: rc 1 due shell quoting; no files changed.
- Re-run dry-run JSON probe via SSH stdin: rc 0; enabled rows have `BENCH_RUN_DIR` but no `result_parser` or `artifact_hints`.
- List `/data/nips/bench` and run scripts: rc 0.
- Read `/data/nips/bench/run_repozero_py2js.sh`, `run_vitabench.sh`, `run_cocoabench.sh`, `run_tau3_bench.sh`, `run_deepswe.sh`, SWE-bench wrappers, `lib/bench_common.sh`, and shared TB2.1 runner: rc 0.
- Existing run artifact presence probe first attempt: rc 127 due shell quoting; rerun via SSH stdin rc 0.
- Bounded `find` for relevant summaries/artifact manifests under shared `nips2026`: rc 0; found historical Vita, tau3, and DeepSWE run summaries/manifests.
- Safe secret-pattern probe over selected existing artifacts: rc 0; printed only booleans/counts, not values.
- Two safe summary/manifest probes first attempts: rc 1 due shell quoting; rerun via SSH stdin rc 0.
- `rg -n "result_parser|artifact_hints|AGENTIC_RESULT_JSON|artifact_manifest" manifests scripts reports`: rc 0; only design docs mention parser hints/AGENTIC_RESULT_JSON.

## Next runner/result subdomain

Next loop should inspect normalized result aggregation and summary status when parser artifacts exist but adapter exit is nonzero. Use synthetic/local controller fixtures only; do not run benchmarks. Focus on whether `_attach_benchmark_result()` can parse side artifacts for Terminal-Bench/DeepSWE infra failures without turning them into `adapter_crash`.
## Round 5 validation evidence

- Append Round 5 ledger section via remote Python over SSH stdin: rc 0.
- `git status --short && git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; only this lane ledger is modified in the worktree, and diff whitespace check passed.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` under an inverted check: rc 0; no trailing whitespace matches.
- Strict token-pattern scan for token-like values in the ledger under an inverted check: rc 0; no matches printed.
- Tail final ledger for sanity: rc 0.

## Round 6 synthetic nonzero exit side-artifact fixtures

Scope for this round:

- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` at pushed commit `57eb2ce`.
- Write set: this ledger only. No production code, manifests, Docker state, benchmark execution, or model calls.
- Method: static code reads plus temporary controller fixtures under `/tmp`, imported with `PYTHONDONTWRITEBYTECODE=1`.
- Secret policy: synthetic fixtures used harmless local paths only; no token values were printed or written.

### Confirmed behavior

Current result attachment has an early nonzero-exit guard:

- `_benchmark_result_for_run()` computes `execution_status` from `exit_code`, and for any nonzero value returns `parser_status=not_run`, `status=infra_error`, `metric=adapter_exit_code`, `failure_category=adapter_crash`; see `scripts/agentic_bench_suite.py:1251-1262`.
- `_attach_benchmark_result()` calls that function before writing `agentic_bench.result.v1`; see `scripts/agentic_bench_suite.py:1281-1315`.
- `_run_one()` only returns `bench_id`, status, `exit_code`, timestamps, and `log_path`; it does not return `BENCH_RUN_DIR`, `artifact_manifest.json`, `run.env.summary`, or `AGENTIC_RESULT_JSON` pointers; see `scripts/agentic_bench_suite.py:1017-1024`.

Terminal-Bench 2.1 is the concrete side-artifact case:

- The repo wrapper exports `BENCH_RUN_DIR` before launching the shared runner; see `scripts/run_terminal_bench_2_1_smoke.sh:227-253`.
- The shared runner captures `tb_rc`, writes `artifact_manifest.json` with `artifact`, `results`, `run_metadata`, `terminal_bench_log`, and `exit_status`, then exits with `tb_rc` when nonzero; see `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh:111-141`.

DeepSWE is slightly different today:

- `/data/nips/bench/run_deepswe.sh:247-289` writes `artifact_manifest.json` only after `Pier result.json` exists, so many launcher crashes will still have no manifest.
- If a DeepSWE adapter variant or partial Pier wrapper does emit a manifest/log pointer before returning nonzero, the suite has the same parser short-circuit and will ignore it.

Synthetic fixture results:

| Case | Side `artifact_manifest.json` existed | Log mentioned manifest | Adapter exit | Normalized parser status | Normalized benchmark status | Failure category | Result recorded manifest/run dir |
|---|---:|---:|---:|---|---|---|---|
| `terminal_bench_2_1` | yes | yes | 7 | `not_run` | `infra_error` | `adapter_crash` | no |
| `deepswe` | yes | yes | 2 | `not_run` | `infra_error` | `adapter_crash` | no |

COMMENT-READY for #1: Nonzero adapter exits skip existing side artifacts and collapse native infra evidence to `adapter_crash`
severity: HIGH
dedup: comment-on-#1; not a new issue because #1 already tracks execution-status versus benchmark-status/result parser semantics. Not #2: fixed run dirs can make this worse, but the synthetic fixture reproduces in a fresh temp dir with no staleness. Not #10: any future fix must obey #10 parser source allowlists/redaction, but this finding is about parser non-execution.
location: `scripts/agentic_bench_suite.py:1017-1024`, `scripts/agentic_bench_suite.py:1251-1262`, `scripts/agentic_bench_suite.py:1281-1315`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh:111-141`, `/data/nips/bench/run_deepswe.sh:247-289`
static_repro: Import `scripts/agentic_bench_suite.py` with `PYTHONDONTWRITEBYTECODE=1`; create a temp `BENCH_RUN_DIR` containing `artifact_manifest.json` and a temp controller log containing `BENCH_RUN_DIR=...`, `artifact=...`, `done: ...`, and `AGENTIC_RESULT_JSON {"artifact_manifest": ...}`; call `_attach_benchmark_result()` with `exit_code=7` for Terminal-Bench and `exit_code=2` for DeepSWE; inspect the emitted normalized result JSON.
impact: Terminal-Bench can produce useful native infra evidence before returning nonzero, including the TB output root, `results.json`, run metadata, harness log, and exit-status sidecar. The suite discards that evidence and emits only `adapter_crash`, so aggregation cannot distinguish harness test failure, image/runtime failure, timeout, native parser failure, and wrapper crash. The same contract bug blocks DeepSWE-like partial-result adapters whenever a side artifact exists but the adapter process returns nonzero. Downstream comments and dashboards lose the exact native path needed to reproduce the failure.
fix: Split execution failure from parser discovery. `_attach_benchmark_result()` should always run a read-only result-discovery phase that can inspect safe pointer sources even when `exit_code != 0`: explicit `AGENTIC_RESULT_JSON`, `BENCH_RUN_DIR` from the run plan, `run.env.summary`, and allowlisted `artifact_manifest.json`. Parser output should preserve `execution.status=fail` while setting `benchmark_result.status` to `infra_error`, `parse_error`, `partial`, or `fail` based on native evidence. If no pointer exists, keep `adapter_crash`; if a pointer exists but parsing fails, use `native_artifact_parse_error` or a bench-specific infra category. Do not copy raw sidecar contents; apply the #10 allowlist/redaction contract before serialization.
evidence: Synthetic probe returned `side_manifest_exists=true` and `log_mentions_manifest=true` for both Terminal-Bench and DeepSWE cases, but both normalized results had `result_parser_status=not_run`, `benchmark_status=infra_error`, `failure_category=adapter_crash`, `result_mentions_artifact_manifest=false`, and `result_mentions_bench_run_dir=false`.

DUPLICATE note for #2: This round did not open a run-dir uniqueness issue. However, because `_run_one()` does not carry `BENCH_RUN_DIR` into `execution_result`, the eventual #2 fix should also make the exact invocation run directory available to `_attach_benchmark_result()` instead of forcing parsers to recover it from logs.

DUPLICATE note for #10: Nonzero-exit parsing must not broaden parser input to arbitrary `BENCH_RUN_DIR` files. Safe sources for this path are structured pointer lines, `run.env.summary`, and allowlisted `artifact_manifest.json` keys; raw env/config/command sidecars remain excluded by #10.

### Round 6 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; output read before remote work, tool display truncated.
- Attempted to read the local `superpowers:systematic-debugging` skill because this is a bug-hunt/debugging lane: rc 1, skill file path was absent; continued with the user-mandated workflow and static/synthetic probes.
- `ssh dev 'cd <image-warmup-policy> && pwd && git rev-parse --short HEAD && git status --short && git log --oneline -5'`: rc 0; head `57eb2ce`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and `DRIVER.md`: rc 0.
- Inspect `_benchmark_result_for_run()`, `_attach_benchmark_result()`, and `_run_one()` with `nl`/`sed`: rc 0.
- Search tests and suite code for `artifact_manifest`, `not_run`, `adapter_crash`, `exit_code`, and `benchmark_result`: rc 0; current tests cover RepoZero status separation and image-preflight failure but not nonzero adapter exits with side artifacts.
- Initial Terminal-Bench shared-runner path probe used the wrong `nips2026/.../swe` prefix: rc 1; corrected path probe rc 0.
- Broad shared-storage `find` for Terminal-Bench runners was interrupted after exceeding the bounded-read intent: rc 255; replaced by repo-indexed `git ls-files`/`rg` and direct known-path reads, rc 0.
- Read `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh:100-141`, `scripts/run_terminal_bench_2_1_smoke.sh:200-253`, and `/data/nips/bench/run_deepswe.sh:230-289`: rc 0.
- Synthetic `_attach_benchmark_result()` fixture for Terminal-Bench and DeepSWE nonzero exits with existing `artifact_manifest.json`: rc 0; safe JSON output is summarized above.
- Read existing runner-results ledger tail and dedup markers with `tail`/`rg`: rc 0.

## Next runner/result subdomain

Next loop should inspect summary aggregation semantics when parser output is present but `execution_status=fail`: whether `summary.json` should order, count, and expose `benchmark_status` independently from process status, and whether one-command YAML semantics should allow a suite to return nonzero while still producing parseable normalized results.

## Round 6 validation evidence

- Append Round 6 ledger section via remote Python over SSH stdin: rc 0.
- `git status --short && git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0 for the ledger whitespace check. Status also showed concurrent/unowned dirty files outside this lane: `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_images.py`, and untracked `scripts/__pycache__/...`; this lane did not edit or revert them.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` under an inverted check: rc 0; no trailing whitespace matches.
- Strict token-pattern scan for token-like values in the ledger under an inverted check: rc 0; no matches printed.
- Tail final ledger for sanity: rc 0.
- Extra status probe with `git status --short --untracked-files=all` and `find scripts/__pycache__`: rc 0; untracked bytecode files are for image-preflight/test modules, not the suite module imported in this round.

- Final status after validation also showed additional untracked `scripts/__pycache__/agentic_bench_suite.cpython-310.pyc`, `test_agentic_bench_suite.cpython-310.pyc`, and `test_offline_images_manifest.cpython-310.pyc`. They are outside this lane's write scope and were not edited or reverted.


## Round 7 summary aggregation with nonzero execution and parser output

Scope for this round:

- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, observed head `9dffbe8`.
- Write set: this ledger only. No production code, manifests, tests, Docker state, benchmark execution, or model calls.
- Method: static code reads plus temporary synthetic controller fixtures under `/data/tmp` with `PYTHONDONTWRITEBYTECODE=1`.
- Cross-lane scope: read `hunt-runtime-images.md` for image-preflight interactions. Runtime Round 6 confirms the current enabled TB2.1 one-task smoke is `gcode-to-text`, while full TB2.1 image readiness remains partial and must stay gated by image preflight.
- Unowned worktree state observed before writing: untracked `_coordination/20260625_harbor_bench/inventory/tb2_shared_tars_sha256_20260626.tsv.tmp` and `scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc`. This lane did not edit or revert them.

### Static summary semantics

Current execute summary shape:

- `_attach_benchmark_result()` writes per-run `execution_status`, `benchmark_status`, `score_claim_valid`, `result_path`, and optional `failure_category`; see `scripts/agentic_bench_suite.py:1281-1315`.
- `_execute_plan()` sets suite `status=1` if any result has `exit_code != 0`, sorts results by manifest order, and writes `summary = {"suite_id", "status", "results"}`; see `scripts/agentic_bench_suite.py:1326-1342`.
- There are no suite-level `execution_status_counts`, `benchmark_status_counts`, `failure_category_counts`, or `score_claim_counts` in execute `summary.json`.
- By contrast, `_execute_image_preflights()` writes an explicit `counts` map and image-preflight metadata; see `scripts/agentic_bench_suite.py:1176-1207`.

Synthetic future-parser probe:

- Monkeypatched `_run_one()` to return nonzero execution results for Terminal-Bench 2.1, DeepSWE, tau3, and SWE-bench Qwen Code rows.
- Monkeypatched `_benchmark_result_for_run()` to simulate future parsers returning benchmark statuses while `exit_code != 0`.
- `_execute_plan()` returned rc `1`, `summary.status=1`, `summary.keys=[results,status,suite_id]`, `has_counts=false`, and `order_preserved=true`.
- Per-row and per-result-file fields did preserve the independent status split:

| Bench | Exit | Execution status | Benchmark status | Failure category |
|---|---:|---|---|---|
| `terminal_bench_2_1_image_smoke` | 7 | `fail` | `infra_error` | `infra_image_preflight` |
| `deepswe_smoke` | 2 | `fail` | `partial` | `partial_trace_with_harness_error` |
| `tau3_smoke` | 5 | `fail` | `infra_error` | `harbor_runtime_error` |
| `swebench_verified_qwen_code_smoke` | 11 | `fail` | `fail` | `official_eval_failed` |

Interpretation:

- Per-row summary fields can preserve `benchmark_status` independently from process status once a parser is allowed to run on nonzero execution results.
- Suite-level aggregation still cannot answer basic one-command questions without consumers re-scanning every result row: how many adapter executions failed, how many benchmark statuses are `fail` versus `infra_error` versus `partial`, and whether any score claim is valid.

COMMENT-READY for #1: execute `summary.json` needs status/count maps once parsers can run on nonzero adapter exits
severity: MEDIUM
dedup: comment-on-#1. Not #2 because the synthetic probe used fresh temp output dirs and did not depend on invocation uniqueness. Not #10 because no parser sidecar contents or secret-bearing files were read.
location: `scripts/agentic_bench_suite.py:1281-1315`, `scripts/agentic_bench_suite.py:1326-1342`, `scripts/agentic_bench_suite.py:1176-1207`, `reports/next_result_parser_contract_20260625.md:63-73`, `reports/next_result_parser_contract_20260625.md:218-231`
static_repro: Import `scripts/agentic_bench_suite.py` with `PYTHONDONTWRITEBYTECODE=1`, monkeypatch `_run_one()` to return nonzero execution results for Terminal-Bench, DeepSWE, tau3, and SWE-bench rows, monkeypatch `_benchmark_result_for_run()` to return parsed benchmark statuses, then call `_execute_plan()` and read `summary.json`.
impact: A future fixed parser can emit correct per-row `benchmark_status` while the suite process still returns nonzero for failed execution. However, the suite-level summary still exposes only one integer `status` plus raw rows. Dashboards, one-command YAML wrappers, and issue bots must implement their own counting logic and can easily regress to treating `summary.status=1` as a generic adapter failure or treating row `status=fail:<rc>` as the benchmark result. This matters for Terminal-Bench image/runtime errors, DeepSWE partial traces, tau3 Harbor failures, and SWE-bench official eval failures, which need different follow-up actions.
fix: Keep `summary.status` as the process-return aggregate for CLI compatibility, but add explicit deterministic aggregates: `execution_status_counts`, `benchmark_status_counts`, `parser_status_counts`, `failure_category_counts`, `score_claim_valid_counts`, and optionally `process_failed_count`. Keep `results` sorted by manifest order. Do not make parser output change the CLI rc unless a future explicit gate such as `--require-benchmark-pass` is enabled.
evidence: Synthetic probe returned `execute_rc=1`, `summary_status=1`, `has_counts=false`, `order_preserved=true`, while each row and result doc preserved `execution_status=fail` with independent parsed `benchmark_status` values `infra_error`, `partial`, `infra_error`, and `fail`.

### Image-preflight interaction inside full execute

Synthetic execute-path preflight probe:

- Built a one-row Terminal-Bench-like plan with a required synthetic image preflight command that exits `7` and an adapter command that would create a marker if launched.
- `_run_one()` returned `status=fail:image_preflight:7` and the adapter marker was absent, proving the adapter did not run.
- `_attach_benchmark_result()` still normalized the result as `parser_status=not_run`, `benchmark_status=infra_error`, `failure_category=adapter_crash`, and `short_failure_note=adapter exited 7`.
- `summary.json` again had no `counts` field.

COMMENT-READY for #1/#6: required image-preflight failure in `--execute` is normalized as `adapter_crash`
severity: HIGH
dedup: comment-on-#1 for execution/benchmark/parser status semantics; comment-on-#6 because the concrete trigger is image-preflight warmup/check failure. Related to #8 when the failing preflight is rootless Docker readiness, but this repro does not require Docker. Not #10 because no sidecar content is parsed.
location: `scripts/agentic_bench_suite.py:986-1010`, `scripts/agentic_bench_suite.py:1251-1262`, `scripts/agentic_bench_suite.py:1281-1315`, `scripts/agentic_bench_suite.py:1326-1342`, `reports/next_result_parser_contract_20260625.md:589-595`
static_repro: Import `scripts/agentic_bench_suite.py` with `PYTHONDONTWRITEBYTECODE=1`; build a one-run plan for `terminal_bench_2_1_image_smoke` with `image_preflight.required=true` and `command_argv=["bash","-lc","printf preflight_failed; exit 7"]`; set the adapter command to touch a marker; call `_execute_plan()`; inspect `summary.json` and `results/<bench>.result.json`.
impact: For Terminal-Bench 2.1 and SWE-bench adapters, required image preflight is the gate that should distinguish missing image, bad fallback tar, registry pull failure, rootless Docker readiness, and runnable adapter failure. In full `--execute`, a preflight failure prevents the adapter from launching but is reported as `adapter_crash`. Aggregation and triage lose the fact that this was an image/runtime readiness failure, so the next action can be misrouted to parser/adapter owners instead of image-preflight/runtime owners.
fix: Carry structured preflight state from `_run_one()` into `_attach_benchmark_result()`, for example `execution_result["preflight_status"]`, `preflight_exit_code`, and `preflight_phase="image_preflight"`. Map `status.startswith("fail:image_preflight:")` to `failure_category=infra_image_preflight`, `parser_status=not_run`, `benchmark_status=infra_error`, and `score_claim_valid=false`. Add execute-summary counts consistent with `image_preflight_summary.json` so full `--execute` and `--image-preflight-only` classify the same failure the same way.
evidence: Synthetic probe returned `adapter_marker_exists=false`, `row_status=fail:image_preflight:7`, `row_execution_status=fail`, `row_benchmark_status=infra_error`, `row_failure_category=adapter_crash`, `result_parser_status=not_run`, `result_short_failure_note="adapter exited 7"`, and `summary_has_counts=false`.

### Round 7 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first as required, tool display truncated.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Attempted to read the listed `superpowers:systematic-debugging` skill path: rc 1, file absent; continued with the user-mandated workflow and bounded synthetic probes.
- Memory quick search in `/Users/Zhuanz1/.codex/memories/MEMORY.md` for current repo/bench terms: rc 0; no actionable current repo note was used.
- Active worktree status and runtime lane read: rc 0; branch `feat/image-warmup-policy`, head `9dffbe8`; runtime lane Round 6 image-preflight context consumed.
- Read `_benchmark_result_for_run()`, `_attach_benchmark_result()`, `_execute_plan()`, `_run_one()`, and `_execute_image_preflights()` with `nl`/`sed`: rc 0.
- Read focused tests and result-parser contract lines for status split and TB2.1 blocked-state expectations: rc 0.
- Grep for `summary.json`, `benchmark_status`, `execution_status`, `adapter_crash`, and image preflight references across suite/tests/report/current ledger: rc 0.
- Future-parser nonzero synthetic `_execute_plan()` probe over Terminal-Bench, DeepSWE, tau3, and SWE-bench rows: rc 0; safe JSON output summarized above.
- Required image-preflight failure synthetic `_execute_plan()` probe: rc 0; safe JSON output summarized above.
- Pre-append status/dedup grep: rc 0; observed unowned untracked files listed in this section and existing #1/#6/#10 dedup markers in the ledger.

## Next runner/result subdomain

Next loop should inspect whether current normalized result artifacts have enough stable identifiers for cross-run aggregation: `suite_id`, `run_id`, `bench_id`, adapter, model profile, invocation/run directory, native artifact pointer, image preflight summary pointer, and parser version. Focus on what is missing from `agentic_bench.result.v1` before #2 introduces invocation-unique run dirs.


## Round 7 validation evidence

- Append Round 7 ledger section via remote Python over SSH stdin: rc 0.
- `git status --short --untracked-files=all && git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0 for ledger diff whitespace. Status also showed concurrent/unowned changes outside this lane: `_coordination/20260625_harbor_bench/HANDOFF.md`, `_coordination/20260625_harbor_bench/inventory/swe_dev_data_inventory_20260626.md`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, untracked `_coordination/20260625_harbor_bench/inventory/tb2_shared_tars_sha256_20260626.tsv`, and untracked `scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc`. This lane did not edit or revert them.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` under an inverted check: rc 0; no trailing whitespace matches.
- Strict token-pattern scan for token-like values in the ledger under an inverted check: rc 0; no matches printed.
- Tail final ledger for sanity: rc 0.


## Round 8 normalized result identity and provenance contract

Scope for this round:

- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, observed head `25820b4`.
- Write set: this ledger only. No production code, manifests, tests, Docker state, benchmark execution, or model calls.
- Method: static code reads, dry-run JSON inspection, and one temporary synthetic `_attach_benchmark_result()` fixture under `/data/tmp` with `PYTHONDONTWRITEBYTECODE=1`.
- Secret policy: synthetic fixture used harmless paths and no token-like values; result scan below printed only key presence and booleans.

### Static data flow

The suite run plan already carries most identity/provenance fields needed by cross-run aggregation:

- `build_run_plan()` derives `profile_id`, `worker_host`, `run_id`, and `run_dir`; see `scripts/agentic_bench_suite.py:786-823`.
- The run manifest stores `worker_host`, `worker_id`, `run_root`, `run_dir`, `model`, redacted `runtime_env`, params, command, and optional `image_preflight`; see `scripts/agentic_bench_suite.py:860-909`.
- `_execute_plan()` writes the whole plan to `<output_root>/run_manifest.json`; see `scripts/agentic_bench_suite.py:1323-1325`.

The normalized result writer drops most of that metadata:

- `_attach_benchmark_result()` writes only top-level `schema_version`, `suite_id`, `run_id`, `bench_id`, `bench`, `adapter`, an `execution` object with process/log fields, and `benchmark_result`; see `scripts/agentic_bench_suite.py:1281-1299`.
- It does not include a `parser` object, `source` object, model/profile field, worker field, run directory, invocation id, native artifact pointer, image-preflight summary pointer, or parser version.
- Current test coverage only asserts the status split and RepoZero numeric result fields; it does not assert provenance fields; see `scripts/test_agentic_bench_suite.py:430-470`.

The design report already describes the missing shape:

- Suggested `agentic_bench.result.v1` includes `parser.id`, `parser.version`, `parser.parsed_at`, and a `source` section with controller summary/log, run manifest, native artifact root, and native artifacts; see `reports/next_result_parser_contract_20260625.md:100-119`.
- Parser source discovery should record native artifacts instead of relying on prose/log inference; see `reports/next_result_parser_contract_20260625.md:650-670`.

Dry-run evidence from the live suite row:

- `repozero_py2js_smoke` dry-run has `model.profile_id=dev_proxy_gpt54mini_8130`, the explicit `worker_host`, `worker_id=worker-j9jjd`, `run_dir`, `runtime_env.BENCH_RUN_DIR`, and a populated `image_preflight` object.
- The run-plan keys include `model`, `worker_host`, `worker_id`, `run_dir`, `runtime_env`, and `image_preflight`, proving the data is available before result emission.

Synthetic normalized result probe:

- Input `run` included `model.profile_id`, `worker_host`, `worker_id`, `run_dir`, `runtime_env.BENCH_RUN_DIR`, `image_preflight`, `result_parser`, and `artifact_hints` with a harmless native artifact path and `artifact_manifest.json` path.
- The controller output dir also contained a synthetic `image_preflight_summary.json`.
- The emitted `agentic_bench.result.v1` had top-level keys only: `adapter`, `bench`, `bench_id`, `benchmark_result`, `execution`, `run_id`, `schema_version`, `suite_id`.
- Missing paths were all true for: top-level `model`, `model_profile`, `worker_host`, `worker_id`, `run_dir`, `runtime_env`, `parser`, `source`, `image_preflight`; nested `execution.image_preflight_status`, `execution.run_dir`; nested `benchmark_result.parser_id`, `benchmark_result.parser_version`.
- The result text did not mention the native artifact root, `artifact_manifest.json`, `image_preflight_summary.json`, or worker id. The model profile appeared only as a substring inside `run_id`, not as a first-class field.

ISSUE-READY: normalized result artifacts are not self-contained enough for cross-run aggregation
severity: HIGH
dedup: new issue candidate unless #1 is intentionally expanded beyond status/parser semantics. Related but not duplicate of #1 because per-row `execution_status`/`benchmark_status` can be correct while provenance is still missing. Related but not duplicate of #2 because invocation-unique dirs will create the missing stable `invocation_id`/run-dir value, but this result writer still has to persist it. Related but not duplicate of #10 because #10 constrains which source files and fields are safe to read; this issue requires safe provenance pointers, not raw sidecar contents.
location: `scripts/agentic_bench_suite.py:786-823`, `scripts/agentic_bench_suite.py:860-909`, `scripts/agentic_bench_suite.py:1281-1299`, `scripts/agentic_bench_suite.py:1323-1341`, `reports/next_result_parser_contract_20260625.md:100-119`, `reports/next_result_parser_contract_20260625.md:650-670`, `scripts/test_agentic_bench_suite.py:430-470`
static_repro: Build a dry-run plan for `repozero_py2js_smoke` and observe that the run manifest has model/profile, worker, run dir, runtime env, and image-preflight metadata. Then import `scripts/agentic_bench_suite.py` with `PYTHONDONTWRITEBYTECODE=1`, call `_attach_benchmark_result()` with a synthetic run containing `model`, `worker_host`, `worker_id`, `run_dir`, `runtime_env.BENCH_RUN_DIR`, `image_preflight`, `result_parser`, and `artifact_hints`, and inspect the emitted `results/<bench_id>.result.json`.
impact: A standalone normalized result file cannot be aggregated safely across runs, workers, models, parser versions, or native artifact sources. Consumers must join against `run_manifest.json` by `run_id`, but `run_id` is not invocation-unique today (#2), and moved/copied result files lose their controller context. The current artifact cannot answer which model profile produced the score, which worker/rootless context ran it, which exact `BENCH_RUN_DIR` or native artifact was parsed, whether image preflight passed, or which parser version produced the benchmark status. This blocks reliable cross-run comparisons for RepoZero, tau3, SWE-bench, DeepSWE, Terminal-Bench, and any future parser registry.
fix: Make `agentic_bench.result.v1` self-contained with allowlisted provenance fields. Add a `run` or `identity` object with `suite_id`, `run_id`, future `invocation_id`, `bench_id`, `adapter`, `model_profile_id`, `model_name`, `worker_id`, `worker_host`, `execution_host`, `run_dir`, and `bench_run_dir`. Add a `parser` object with `id`, `version`, `status`, `parsed_at`, and warnings. Add a `source` object with `run_manifest_path`, `controller_summary_path`, `controller_log_path`, `image_preflight_summary_path`, and `native_artifacts` pointer records. Native artifacts must be pointers/statuses only unless parser-specific allowlists and #10 redaction approve fields. Keep `run_id` for compatibility but do not rely on it as unique after #2.
evidence: Dry-run JSON showed the run has `model.profile_id=dev_proxy_gpt54mini_8130`, `worker_id=worker-j9jjd`, `run_dir`, `runtime_env.BENCH_RUN_DIR`, and populated `image_preflight`. Synthetic result probe returned `result_top_keys=[adapter,bench,bench_id,benchmark_result,execution,run_id,schema_version,suite_id]`, `execution_keys=[adapter_status,ended_at,exit_code,log_path,started_at,status]`, no `parser` or `source`, no explicit model/worker/run-dir fields, no native artifact pointer, and no image-preflight summary pointer.

COMMENT-READY for #2: invocation-unique dirs should be persisted in result artifacts, not only run manifests
severity: HIGH
dedup: comment-on-#2
location: `scripts/agentic_bench_suite.py:812-823`, `scripts/agentic_bench_suite.py:1284-1299`
static_repro: Inspect current `run_id`/`run_dir` construction and the result writer. `run_id` is derived from `suite_id + bench_id + profile_id`; `run_dir` is `<run_root>/<suite_id>/<bench_id>`; result JSON stores `run_id` but no `run_dir`, `BENCH_RUN_DIR`, or invocation id.
impact: Even after #2 adds a unique invocation directory, downstream aggregation will still be forced to recover the exact native run directory from logs or `run_manifest.json` unless `agentic_bench.result.v1` carries that field. Result files copied into reports, issue comments, or dashboards can become detached from the only artifact that explains which invocation they represent.
fix: When implementing #2, add `invocation_id`, `run_dir`, and `bench_run_dir` to the normalized result artifact and summary rows. Include `run_manifest_path` as a source pointer so consumers can verify the full redacted run plan.
evidence: Synthetic result probe had input `run_dir` and `runtime_env.BENCH_RUN_DIR`, but both `top_run_dir` and `execution_run_dir` were absent in the emitted result JSON.

COMMENT-READY for #10: provenance fix must use source pointers and allowlists, not raw run-dir serialization
severity: HIGH
dedup: comment-on-#10
location: `scripts/agentic_bench_suite.py:888-889`, `scripts/agentic_bench_suite.py:1284-1299`
static_repro: `build_run_plan()` stores redacted `runtime_env` in the run manifest, while prior lane evidence shows multiple adapters write secret-bearing sidecars under `BENCH_RUN_DIR`. The current result writer avoids copying them, but also omits safe pointers.
impact: The fix for result provenance could regress into #10 if it serializes raw `runtime_env`, command files, config files, or sidecar contents. The right contract is pointer-oriented: record where a parser looked and what role/status each source had, but do not inline arbitrary file contents.
fix: Add a typed `source.native_artifacts[]` list with `role`, `path`, `status`, optional sha/size where cheap, and parser-specific safe summaries. Reuse `_redact_env()` for any environment metadata and add recursive sanitizer before writing normalized results.
evidence: Synthetic result probe included harmless `artifact_hints`, but current writer ignored them. The recommended fix is to persist sanitized pointer records, not to copy arbitrary hint/source payloads.

### Round 8 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first as required, tool display truncated.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Found and read `superpowers:systematic-debugging` skill: `find .../systematic-debugging/SKILL.md` rc 0; `cat` rc 0.
- Active worktree status and branch/head probe: rc 0; branch `feat/image-warmup-policy`, head `25820b4`; observed concurrent/unowned `scripts/test_agentic_bench_images.py` and `scripts/__pycache__` changes.
- Read run-plan construction, result writer, RepoZero parser, and execute summary code with `nl`/`sed`: rc 0.
- Grep for model/profile/worker/run-dir/parser/source/native-artifact/image-preflight fields across suite/tests/report/current ledger: rc 0.
- Dry-run JSON inspection for `repozero_py2js_smoke`: rc 0; printed only field names/paths and no secrets.
- Read result contract lines and current focused tests: rc 0.
- Synthetic `_attach_benchmark_result()` provenance fixture under `/data/tmp`: rc 0; safe JSON output summarized above.
- Read `_execute_plan()` write points and current ledger dedup tail/grep: rc 0.

## Next runner/result subdomain

Next loop should inspect parser provenance for actual adapter families: for RepoZero, tau3, SWE-bench, Terminal-Bench, and DeepSWE, define the minimal safe `source.native_artifacts[]` roles and statuses needed so #10 allowlists and this result-provenance issue can be implemented without over-reading `BENCH_RUN_DIR`.


## Round 8 validation evidence

- Append Round 8 ledger section via remote Python over SSH stdin: rc 0.
- `git status --short --untracked-files=all && git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0 for ledger diff whitespace. Status also showed concurrent/unowned changes outside this lane: `_coordination/20260625_harbor_bench/HANDOFF.md`, `scripts/README.md`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_images.py`, and untracked `scripts/__pycache__/...`. This lane did not edit or revert them.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` under an inverted check: rc 0; no trailing whitespace matches.
- Strict token-pattern scan for token-like values in the ledger under an inverted check: rc 0; no matches printed.
- Tail final ledger for sanity: rc 0.

## Round 9 source.native_artifacts roles/status map for #12 provenance and #10 redaction

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then `_coordination/20260625_harbor_bench/HANDOFF.md`.
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, observed head `ccf74ac` during this loop.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker execution, benchmark execution, or model requests.
- Target benches: RepoZero, tau3, SWE-bench, Terminal-Bench 2.1, and DeepSWE.

No new ISSUE-READY block from this loop.

Dedup judgment: this is COMMENT-READY implementation detail for #12 and #10. It is related to #1 because parsers must keep benchmark status independent of process status, and related to #2 because invocation-unique run dirs must populate these pointers, but it is not a distinct root-cause issue. Static evidence shows the current suite writes no `source.native_artifacts` object at all in `agentic_bench.result.v1`, while the wrapper artifacts already have enough per-bench pointer material to define safe roles.

COMMENT-READY for #12/#10: define typed `source.native_artifacts[]` records per adapter, with pointer-first provenance and explicit unsafe exclusions

severity: HIGH

dedup: comment-on-#12 for normalized-result provenance. comment-on-#10 for the source allowlist/redaction boundary. comment-on-#1 only where parser discovery must run even when adapter exit is nonzero. Not #2 except that future invocation ids and unique run dirs should be persisted as parent identity fields.

location: `reports/next_result_parser_contract_20260625.md:662-670`, `scripts/agentic_bench_suite.py:1220-1248`, `scripts/agentic_bench_suite.py:1251-1278`, `scripts/agentic_bench_suite.py:1281-1300`, `/data/nips/bench/lib/bench_common.sh:223-227`, `/data/nips/bench/run_repozero_py2js.sh:96-100`, `/data/nips/bench/run_tau3_bench.sh:30-39`, `/data/nips/bench/run_tau3_bench.sh:55-57`, `/data/nips/bench/run_tau3_bench.sh:75-94`, `/data/nips/bench/run_deepswe.sh:147-159`, `/data/nips/bench/run_deepswe.sh:218-245`, `/data/nips/bench/run_deepswe.sh:247-289`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified.sh:168-186`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_mini_swe_agent.sh:116-135`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_openhands.sh:427-446`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh:111-141`, `scripts/run_terminal_bench_2_1_smoke.sh:200-253`

static_repro:

- The contract report already proposes `source.native_artifacts[]` pointer records with `role`, `path`, and `status`, but production result writing currently serializes only top-level suite/run/bench/adapter and `execution` plus `benchmark_result`; no `source`, parser identity, native-artifact status, model profile, worker, or run-dir provenance is emitted.
- Current production parser coverage is RepoZero-only: `_repozero_benchmark_result()` parses score lines from text, `_benchmark_result_for_run()` returns `not_run/infra_error` immediately on nonzero adapter exit, then falls back to `no_parser/unknown` for non-RepoZero adapters. That means Terminal-Bench/DeepSWE nonzero executions can have usable manifests but still lose benchmark-native evidence.
- `bench_finish` emits only `artifact=<path>` and `done: <path>`. Several wrappers also write richer `artifact_manifest.json` files; those are safer parser entry points than recursively copying `BENCH_RUN_DIR` or native run directories.

Minimal shared record contract:

- Required fields per record: `role`, `path`, `status`, `required`, and `read_policy`.
- Useful optional fields: `exists`, `size_bytes`, `sha256`, `parser_action`, `status_reason`, and a parser-specific `summary` object containing only allowlisted scalar counts/ids.
- Safe status vocabulary: `parsed`, `parsed_summary`, `parsed_excerpt`, `referenced_not_read`, `missing`, `not_emitted`, `not_run`, `setup_only`, `infra_blocked`, `parse_error`, `unsafe_excluded`, and `redacted_excluded`.
- Safe read policies: `allowlist_json`, `allowlist_text_regex`, `pointer_only`, `metadata_only`, and `exclude_secret_or_transcript`.
- Prohibited behavior for #10: no raw serialization of env files, command sidecars, configs, model transcripts, generated patches, tool logs, or arbitrary native directories. It is acceptable to name an unsafe path and mark it `redacted_excluded` or `unsafe_excluded`; do not inline its contents.

RepoZero minimal records:

- `repozero_run_env_summary`: `path=$BENCH_RUN_DIR/run.env.summary`, `status=parsed_summary`, `read_policy=allowlist_text_regex`; parse only `artifact=` and `done:` pointer lines.
- `repozero_native_artifact_root`: path from `artifact=` or `bench_finish`, `status=referenced_not_read` when present; the generated output tree can contain code and test material, so the normalized result should store the pointer and cheap metadata only.
- `repozero_score_log`: `path=$BENCH_RUN_DIR/repozero_py2js.log` or controller log path, `status=parsed_excerpt`, `read_policy=allowlist_text_regex`; extract only `ALL_PASS_CASES`, `TESTS`, and a bounded `fail_example` string with redaction.
- `repozero_command`: `path=$BENCH_RUN_DIR/command.sh`, `status=unsafe_excluded`, `read_policy=exclude_secret_or_transcript`; this is useful as a pointer but should not be copied.
- Impact/fix: this keeps the current RepoZero parser behavior but gives #12 enough provenance to distinguish parsed score lines from unparsed native output roots.

tau3 minimal records:

- `tau3_run_env_summary`: `path=$BENCH_RUN_DIR/run.env.summary`, `status=parsed_summary`, `read_policy=allowlist_text_regex`; parse `tau3_mode`, `tau3_dataset_dir`, `tau3_limit`, `tau3_n_concurrent`, `tau3_jobs_dir`, `tau3_task_count`, `tau3_harbor_run`, and `artifact=`.
- `tau3_tasks_list`: `path=$BENCH_RUN_DIR/tasks.list`, `status=parsed_summary`, `read_policy=metadata_only`; record count and optionally task-directory basenames, not dataset file contents.
- `tau3_dataset_root`: path from `tau3_dataset_dir` or skipped `artifact=`, `status=setup_only` when `tau3_harbor_run=skipped`; this is not a benchmark score artifact.
- `tau3_jobs_root`: path from `tau3_jobs_dir` or success `artifact=`, `status=referenced_not_read` until a Harbor-native score file is identified; `status=missing` when Harbor was expected to run but no job root exists.
- `tau3_harbor_log`: `path=$BENCH_RUN_DIR/tau3_harbor.log`, `status=parsed_excerpt`, `read_policy=allowlist_text_regex`; extract bounded infra/error/summary lines only.
- `tau3_command`: `path=$BENCH_RUN_DIR/command.sh`, `status=unsafe_excluded` despite wrapper redaction; command sidecars should remain pointers under #10.
- Impact/fix: prevents a dry-run or `TAU3_RUN_HARBOR=0` dataset pointer from being reported as a parsed benchmark result. It also gives #1 a way to represent `not_run/setup_only` separately from `unknown`.

SWE-bench minimal records:

- `swebench_artifact_manifest`: `path=$BENCH_RUN_DIR/artifact_manifest.json`, `status=parsed`, `read_policy=allowlist_json`; supported manifest shapes are SWE-agent, mini-swe-agent, and OpenHands.
- `swebench_predictions` or `swebench_output_jsonl`: path from manifest key `predictions` or `output_jsonl`, `status=parsed_summary`, `read_policy=allowlist_json`; record instance ids/counts and whether predictions exist, but do not inline patches, model messages, or full outputs.
- `swebench_eval_log`: path from manifest key `swebench_eval_log` or `eval_log`, `status=parsed_excerpt`, `read_policy=allowlist_text_regex`; extract resolved/failed/error totals if present and bounded failure categories.
- `swebench_agent_trace_root`: path from manifest key `agent_trace_root`, `status=referenced_not_read`, `read_policy=pointer_only`; traces may contain model transcripts and tool outputs.
- `swebench_eval_logs_root`: path from mini-swe-agent manifest, `status=referenced_not_read` or `parsed_summary` only when a specific official report file is allowlisted.
- `swebench_exit_status`: path from SWE-agent manifest key `sweagent_exit_status` when present, `status=parsed_summary`, `read_policy=allowlist_text_regex`.
- `swebench_config_snapshot`, `source_config`, `command`, and `eval_command`: `status=unsafe_excluded` or `redacted_excluded`; OpenHands config and command/config sidecars can carry model routing and credential-adjacent state, so normalized output should not copy them.
- Impact/fix: all three SWE-bench scaffolds already expose manifests and predictions/eval-log pointers. The parser should summarize official outputs while treating traces/configs/patch content as pointer-only or excluded.

Terminal-Bench 2.1 minimal records:

- `terminal_bench_artifact_manifest`: `path=$BENCH_RUN_DIR/artifact_manifest.json`, `status=parsed`, `read_policy=allowlist_json`; this file is created before the wrapper exits nonzero on `tb_rc`, so parser discovery must not depend on `bench_finish`.
- `terminal_bench_exit_status`: path from manifest key `exit_status`, `status=parsed_summary`, `read_policy=allowlist_text_regex`; parse only numeric `tb_rc`.
- `terminal_bench_results_json`: path from manifest key `results`, `status=parsed_summary` if present, `status=missing` if absent; parse only task ids/pass counts/scores/error categories from a future allowlist.
- `terminal_bench_run_metadata`: path from manifest key `run_metadata`, `status=parsed_summary` if present; parse only stable run/task metadata, not agent transcripts.
- `terminal_bench_artifact_root`: path from manifest key `artifact`, `status=referenced_not_read`, `read_policy=pointer_only`.
- `terminal_bench_log`: path from manifest key `terminal_bench_log`, `status=parsed_excerpt`, `read_policy=allowlist_text_regex`; extract bounded infra/error lines only.
- `terminal_bench_command`: path from manifest key `command`, `status=unsafe_excluded`.
- `terminal_bench_smoke_env_exports`: the repo smoke wrapper prints env exports and the runner path in dry-run; those are suite/controller evidence, not native artifacts. Do not copy env values into normalized native artifacts.
- Impact/fix: this is the clearest #1/#12 interaction. A failed TB2 adapter can still leave `artifact_manifest.json`, `tb.exit_status`, and partial native output, but current `_benchmark_result_for_run()` returns `not_run` before looking. The parser must read allowlisted pointers from `BENCH_RUN_DIR` even when execution status is fail.

DeepSWE minimal records:

- `deepswe_artifact_manifest`: `path=$BENCH_RUN_DIR/artifact_manifest.json`, `status=parsed` when present, `read_policy=allowlist_json`; this manifest contains `result_json`, `pier_job_dir`, `pier_job_symlink`, `pier_log`, `command`, `env_summary`, and a safe wrapper-computed summary.
- `deepswe_result_json`: path from manifest key `result_json`, `status=parsed_summary`, `read_policy=allowlist_json`; parse only `n_total_trials`, `n_trial_results`, stats, task ids, and high-level verifier status. Do not inline trajectories, prompts, tool transcripts, or generated patch content.
- `deepswe_pier_job_dir` and `deepswe_pier_job_symlink`: paths from manifest, `status=referenced_not_read`, `read_policy=pointer_only`.
- `deepswe_pier_log`: path from manifest key `pier_log`, `status=parsed_excerpt`, `read_policy=allowlist_text_regex`; bounded infra/error excerpts only.
- `deepswe_env_summary`: path from manifest key `env_summary` or `$BENCH_RUN_DIR/run.env.summary`, `status=parsed_summary`, `read_policy=allowlist_text_regex`; record non-secret run shape such as agent, mode, task count, concurrency, job dir, and whether relay/proxy fields were set, not raw credential-bearing env.
- `deepswe_command`: path from manifest key `command`, `status=unsafe_excluded`.
- `deepswe_pier_env`: `path=$BENCH_RUN_DIR/pier.env`, `status=redacted_excluded`, `read_policy=exclude_secret_or_transcript`; wrapper writes `OPENAI_API_KEY` and optionally `MSWEA_API_KEY`, so normalized output may record presence/path only and must never copy values.
- Impact/fix: when `result.json` exists, DeepSWE already writes a compact safe summary into `artifact_manifest.json`. When Pier fails before manifest creation, the parser should still report `pier.log` and `pier.env` statuses from `BENCH_RUN_DIR` without reading the secret env file.

Cross-lane runtime/images check:

- Read the current runtime lane. Its latest Round 8 is about static image-manifest lint and promotion gates for TB2.1/SWE image transport. That does not conflict with this parser map. Parser output should optionally point to `image_preflight_summary_path` at the top-level `source` object, but image manifest rows are not `source.native_artifacts` for benchmark scoring.
- Runtime image-preflight failures should map into benchmark status as `infra_blocked` or `not_run` with image-preflight source pointers; native artifacts should still be discovered if an adapter started and wrote them before failure.

Implementation map for normalized output:

- Add parent `identity` or `run` fields per #12: `suite_id`, `run_id`, future `invocation_id`, `bench_id`, `adapter`, `model_profile_id`, `model_name`, worker/execution host, controller `run_dir`, and remote `BENCH_RUN_DIR`.
- Add `parser`: `id`, `version`, `status`, `parsed_at`, `warnings`, and `redactions` with key paths only.
- Add `source`: `run_manifest_path`, `controller_summary_path`, `controller_log_path`, optional `image_preflight_summary_path`, and `native_artifacts[]` records from the bench-specific role map above.
- Let `execution.status` remain process-level. Let `benchmark_result.status` be `pass`, `fail`, `infra_error`, `infra_blocked`, `not_run`, `parse_error`, or `unknown`, based on parsed native evidence and explicit missing/unsafe statuses.
- Tests should assert both positive pointer parsing and negative redaction: no `Authorization`, API key, bearer token, raw `pier.env`, raw OpenHands config, raw command files, model transcript text, or patch body appears in normalized output.

### Round 9 command evidence

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions after locating the active cached skill path: rc 0.
- Active worktree status: rc 0; branch `feat/image-warmup-policy`, observed head `ccf74ac`; status later showed unowned untracked `scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc`, left untouched.
- Read existing result contract, runner ledger Round 8, and parser/source grep evidence: rc 0.
- Read `bench_common.sh`, RepoZero, tau3, DeepSWE, SWE-agent, mini-swe-agent, OpenHands, Terminal-Bench shared runner, and repo TB2 smoke wrapper line ranges listed above: rc 0.
- Read current suite parser/result writer line ranges and runtime-images lane tail for cross-lane dedup: rc 0.
- First ledger append attempt had a local shell quoting failure and exited rc 127 before writing; tail check confirmed Round 9 had not been appended. Retried append via remote Python stdin: rc 0.

Next runner/results subdomain: fixture-ready parser expectations for these role maps. Start with a synthetic `source.native_artifacts[]` expected-output fixture for Terminal-Bench nonzero-with-manifest and DeepSWE failure-before-result, because those exercise #1, #10, and #12 together without running benchmarks.

## Round 9 validation evidence

- `git status --short --untracked-files=all`: rc 0. Status showed this lane's modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` plus concurrent/unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` and `scripts/test_agentic_bench_images.py`; those files were not touched by this lane.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- First `rg` token-pattern scanner had shell quoting damage in the regex and printed a shell error despite outer rc 0, so it was ignored. Corrected remote Python scanner: rc 0, `secret_pattern_scan=no_matches`.
- `git diff --stat --` and `git diff --numstat --` for this ledger after Round 9 append: rc 0, `113 insertions` before this validation block.

## Round 10 fixture-ready parser expectations for Terminal-Bench and DeepSWE

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Active branch/head observed at start: `feat/image-warmup-policy` / `ce2adf2 Add registry image lint gate`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, or model requests.
- Focus: fixture-ready parser expectations for Terminal-Bench 2.1 nonzero-with-`artifact_manifest.json` and DeepSWE failure-before-result/manifest cases.

No new ISSUE-READY block from this loop.

Dedup judgment: this is implementation/test-spec detail for #1, #10, and #12. It is not a new issue because Round 5/Round 9 already established that current `_benchmark_result_for_run()` short-circuits nonzero adapter exits and that normalized results lack `source.native_artifacts[]`. It is not #2 except that fixture expected output should include future invocation/run-dir provenance once #2 lands.

Static root-cause evidence:

- `scripts/agentic_bench_suite.py:979-1024` records process status and controller log path from `_run_one()`, but `_benchmark_result_for_run()` returns `parser_status=not_run`, `status=infra_error`, and `failure_category=adapter_crash` for any nonzero exit before looking at `BENCH_RUN_DIR` or `artifact_manifest.json` (`scripts/agentic_bench_suite.py:1251-1262`).
- `_attach_benchmark_result()` writes `agentic_bench.result.v1` without `parser`, `source`, run-dir, or native-artifact provenance (`scripts/agentic_bench_suite.py:1281-1300`).
- Terminal-Bench 2.1 wrapper writes `run.env.summary`, `command.sh`, `terminal_bench.log`, `tb.exit_status`, and `artifact_manifest.json` before returning nonzero on `tb_rc` (`run_terminal_bench_2_1.sh:87-139`). It calls `bench_finish` only on success (`run_terminal_bench_2_1.sh:138-141`), so a parser must not require `artifact=`/`done:` for this failure mode.
- DeepSWE wrapper writes secret-bearing `pier.env` before launching Pier (`run_deepswe.sh:147-159`), writes safe `run.env.summary` and redacted command path material (`run_deepswe.sh:218-245`), then only writes `artifact_manifest.json` after `job_dir/result.json` exists (`run_deepswe.sh:247-289`). If Pier exits nonzero, or if `result.json` is absent, the manifest is not emitted.
- Current contract doc already requires parsers to record found and missing artifacts in `source.native_artifacts[]` (`reports/next_result_parser_contract_20260625.md:662-670`).

COMMENT-READY test-spec table for #1/#10/#12:

| Fixture | Synthetic files to add later | Expected execution/benchmark split | Required `source.native_artifacts[]` records | Redaction negative assertions |
|---|---|---|---|---|
| `tests/fixtures/result_parsers/terminal_bench_2_1_nonzero_with_manifest/` | `run_manifest.json`; `execution_result.json`; `bench_run/artifact_manifest.json`; `bench_run/tb.exit_status`; `bench_run/terminal_bench.log`; `bench_run/command.sh`; `native_run/results.json`; `native_run/run_metadata.json`; `expected.result.json` | `execution.status=fail`, `execution.exit_code=2`, `execution.adapter_status=fail:2`; `parser.id=terminal_bench_2_1`, `parser.status=parsed`; `benchmark_result.parser_status=parsed`, `benchmark_result.status=fail`, `benchmark_result.metric=accuracy`, `benchmark_result.score=0.0`, `benchmark_result.passed=false`, `benchmark_result.score_claim_valid=true`, `benchmark_result.tasks_passed=0`, `benchmark_result.tasks_total=1`, `benchmark_result.failure_category=task_unresolved` | `terminal_bench_artifact_manifest`: `parsed` / `allowlist_json`; `terminal_bench_exit_status`: `parsed_summary` / `allowlist_text_regex`; `terminal_bench_results_json`: `parsed_summary` / `allowlist_json`; `terminal_bench_run_metadata`: `parsed_summary` / `allowlist_json`; `terminal_bench_artifact_root`: `referenced_not_read` / `pointer_only`; `terminal_bench_log`: `parsed_excerpt` / `allowlist_text_regex`; `terminal_bench_command`: `unsafe_excluded` / `exclude_secret_or_transcript` | Serialized normalized JSON must not contain `UNIT_SENTINEL_TERMINAL`, raw `instruction`, raw `agent_kwargs`, raw command content, or any key/value from `command.sh`. It may contain the path to `command.sh` only as an unsafe-excluded source record. |
| `tests/fixtures/result_parsers/deepswe_nonzero_before_result_no_manifest/` | `run_manifest.json`; `execution_result.json`; `bench_run/run.env.summary`; `bench_run/pier.log`; `bench_run/pier.env`; `bench_run/command.sh`; deliberately no `bench_run/artifact_manifest.json`; deliberately no `bench_run/pier_jobs/deepswe_unit/result.json`; `expected.result.json` | `execution.status=fail`, `execution.exit_code=1`, `execution.adapter_status=fail:1`; `parser.id=deepswe`, `parser.status=partial`; `benchmark_result.parser_status=partial`, `benchmark_result.status=infra_error`, `benchmark_result.metric=native_artifact_presence`, `benchmark_result.passed=false`, `benchmark_result.score_claim_valid=false`, `benchmark_result.failure_category=deepswe_pier_failed_before_result`, `benchmark_result.short_failure_note` bounded to a sanitized Pier error summary | `deepswe_env_summary`: `parsed_summary` / `allowlist_text_regex`; `deepswe_artifact_manifest`: `not_emitted` / `allowlist_json`; `deepswe_result_json`: `not_emitted` / `allowlist_json`; `deepswe_pier_job_dir`: `missing` / `pointer_only`; `deepswe_pier_log`: `parsed_excerpt` / `allowlist_text_regex`; `deepswe_pier_env`: `redacted_excluded` / `exclude_secret_or_transcript`; `deepswe_command`: `unsafe_excluded` / `exclude_secret_or_transcript` | Serialized normalized JSON must not contain `UNIT_SENTINEL_DEEPSWE`, `OPENAI_API_KEY`, `MSWEA_API_KEY`, `OPENAI_API_BASE`, raw `pier.env` contents, raw command content, or unbounded `pier.log`. It may contain `pier.env` as a path with `redacted_excluded`. |

Terminal-Bench fixture content contract:

- `run_manifest.json` should mirror the suite run shape, with `suite_id=unit_parser_fixture`, `bench_id=terminal_bench_2_1_image_smoke`, `bench=terminal_bench_2_1`, `adapter=terminal_bench_2_1`, `adapter_status=wired_legacy`, `runtime_env.BENCH_RUN_DIR=<fixture>/bench_run`, `params.TB_TASK_IDS=gcode-to-text`, `worker_id=worker-j9jjd`, and a redacted model profile. Do not include live credentials.
- `execution_result.json` should represent the controller-side `_run_one()` result: `status=fail:2`, `exit_code=2`, and a controller log path. This is the reproducer for #1: process failed, but native TB score artifacts are still present.
- `bench_run/artifact_manifest.json` should use the wrapper keys from `run_terminal_bench_2_1.sh:124-134`: `agent`, `benchmark`, `artifact`, `artifact_symlink`, `command`, `terminal_bench_log`, `exit_status`, `results`, and `run_metadata`.
- `bench_run/tb.exit_status` should contain only `tb_rc=2`.
- `native_run/results.json` should use the observed Terminal-Bench top-level shape from existing artifacts: `accuracy`, `id`, `n_resolved`, `n_unresolved`, `pass_at_k`, `resolved_ids`, `unresolved_ids`, and `results`. The synthetic row should include only safe scalar fields needed by the parser, for example `task_id=gcode-to-text`, `is_resolved=false`, `failure_mode=unit_unresolved`, token counts, and timestamps. It should include a raw `instruction` value containing `UNIT_SENTINEL_TERMINAL` to prove the parser does not copy prompts/instructions.
- `native_run/run_metadata.json` should include only safe metadata keys observed in existing artifacts, such as `run_id`, `dataset_name`, `dataset_path`, `dataset_version`, `task_ids`, `n_concurrent_trials`, `n_attempts`, `agent_name`, and `model_name`. If it includes `agent_kwargs` with `UNIT_SENTINEL_TERMINAL`, the expected normalized result must omit that object entirely.
- `expected.result.json` should assert the normalized output keeps `execution.status=fail` while deriving `benchmark_result.status=fail` from native results, not `infra_error` from the process exit alone.

DeepSWE fixture content contract:

- `run_manifest.json` should mirror a DeepSWE suite row, with `bench_id=deepswe`, `bench=deepswe`, `adapter=deepswe`, `adapter_status=wired_legacy`, `runtime_env.BENCH_RUN_DIR=<fixture>/bench_run`, `params.DEEPSWE_MODE=smoke`, and `params.MAX_CONCURRENCY=1`.
- `execution_result.json` should represent `_run_one()` returning `status=fail:1`, `exit_code=1`, and a controller log path.
- `bench_run/run.env.summary` should include only safe wrapper keys from `run_deepswe.sh:218-240`: `deepswe_root`, `deepswe_commit`, `deepswe_task_count`, `pier_bin`, `deepswe_agent`, `deepswe_model`, `deepswe_model_class`, `deepswe_mode`, `deepswe_n_tasks`, `deepswe_n_concurrent`, `deepswe_jobs_dir`, `deepswe_job_name`, `deepswe_host_api_relay`, `deepswe_relay_upstream_proxy_set`, and `deepswe_set_mswea_api_key`. It should not contain actual URLs with credentials.
- `bench_run/pier.log` should include a short synthetic infra error and `UNIT_SENTINEL_DEEPSWE` in a line that must be redacted or dropped from `short_failure_note`. The expected result may include a bounded sanitized category such as `pier failed before result.json`.
- `bench_run/pier.env` should contain short synthetic placeholders for secret-bearing keys to prove the parser never reads or serializes the file. The expected result should record only the path and `redacted_excluded` status.
- `bench_run/command.sh` should contain the `--env-file $BENCH_RUN_DIR/pier.env` pattern, but the expected result should record only a pointer with `unsafe_excluded`.
- There must be no `bench_run/artifact_manifest.json` and no `pier_jobs/deepswe_unit/result.json`. The parser should treat this as a partial parse of safe sidecars, not `no_parser`, not `unknown`, and not a score claim.

Minimal tests to add before implementation:

1. `test_terminal_bench_nonzero_with_manifest_parses_native_result`: load the Terminal-Bench fixture, call the future parser/result attachment entry point with `execution_result.exit_code=2`, then assert the exact execution/benchmark split and `score_claim_valid=true` from `results.json`.
2. `test_terminal_bench_nonzero_with_manifest_records_sources`: assert every expected Terminal-Bench source record has the exact `role`, `status`, `required`, and `read_policy`, and that `terminal_bench_command` is `unsafe_excluded`.
3. `test_terminal_bench_parser_does_not_copy_prompts_or_command_sidecars`: serialize the normalized result and assert `UNIT_SENTINEL_TERMINAL`, raw `instruction`, raw `agent_kwargs`, and command contents are absent.
4. `test_deepswe_nonzero_before_manifest_records_partial_sources`: load the DeepSWE fixture, call the parser/result attachment entry point with `execution_result.exit_code=1`, then assert `parser.status=partial`, `benchmark_result.status=infra_error`, and source records for `artifact_manifest`/`result_json` are `not_emitted` while `pier_env` is `redacted_excluded`.
5. `test_deepswe_partial_parser_does_not_read_pier_env`: serialize the normalized result and assert `UNIT_SENTINEL_DEEPSWE`, env key names, and raw `pier.env`/`command.sh` contents are absent.
6. `test_nonzero_exit_does_not_short_circuit_parser_discovery_when_bench_run_dir_exists`: a narrow regression test for #1 using either fixture should fail against current `scripts/agentic_bench_suite.py:1251-1262` until parser discovery is moved before the process-status fallback.

Implementation notes for the next code lane:

- Add fixture paths under `tests/fixtures/result_parsers/` rather than embedding large JSON strings in `scripts/test_agentic_bench_suite.py`; keep fixtures minimal and synthetic.
- Add a parser discovery helper that accepts `run` and `execution_result`, resolves `BENCH_RUN_DIR` from `run.runtime_env.BENCH_RUN_DIR`, and only reads allowlisted files. It should run even when `execution_result.exit_code != 0`.
- Keep `execution.status` process-level. Do not change suite rc semantics: `_execute_plan()` should still return nonzero when adapter exit is nonzero, while the normalized result can hold a parsed benchmark failure or infra failure.
- Add a recursive sanitizer before writing result JSON, and make tests inspect the serialized JSON string, not only Python objects.
- Do not add fixture files containing live paths or real native artifacts. Paths can be relative inside the fixture root or synthetic `/tmp/unit/...` placeholders.

### Round 10 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, display truncated by tool.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- `ssh swe_dev 'cd ...image-warmup-policy && pwd && git branch --show-current && git rev-parse --short HEAD && git log -1 --oneline && git status --short --untracked-files=all'`: rc 0; branch `feat/image-warmup-policy`, head `ce2adf2`, status clean at that moment.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read current runner ledger tail: rc 0.
- Three initial `rg` commands failed because `rg` is unavailable on `swe_dev`: rc 127; reran with `grep`/`find`.
- Grep and `nl`/`sed` reads for `scripts/agentic_bench_suite.py` and `scripts/test_agentic_bench_suite.py`: rc 0.
- Resolved wrapper real paths with `readlink -f`: rc 0.
- Read Terminal-Bench wrapper, DeepSWE wrapper, `bench_common.sh`, and result-contract report line ranges: rc 0.
- Read runtime-images lane tail and manifest suite entries for Terminal-Bench/DeepSWE: rc 0.
- Broad existing-artifact `find` probes were interrupted after they ran too long: rc 255. The Terminal-Bench scan printed only file paths, not file contents or secrets; the DeepSWE scan produced no output before interruption.
- Bounded Terminal-Bench JSON shape probe over one existing `results.json` and `run_metadata.json`: rc 0; printed only top-level keys and nested key names, no instruction/model output content.

## Round 10 validation evidence

- `git status --short --untracked-files=all`: rc 0; only this lane ledger was modified at validation time.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.
- `git diff --stat --` and `git diff --numstat --` for this ledger after the Round 10 append: rc 0, `80 insertions` before this validation block.
- Post-validation final status note: a later `git status --short --untracked-files=all` returned rc 0 and showed concurrent/unowned `manifests/images/swebench_verified_django10097.yaml` modified outside this lane; this lane did not touch it.

## Round 11 registry lint and fallback-load provenance review

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Active branch/head observed: `feat/image-warmup-policy` / `abac24d Record SWE transport follow-up dispatch`; history includes `bacbde3 Materialize SWE django fallback transport` and `ce2adf2 Add registry image lint gate`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, or model requests.
- Focus: adversarial result/provenance review for registry lint plus worker fallback-load/image-smoke path.

No new ISSUE-READY block from this loop.

Dedup judgment: the structured-result gap is a #12 provenance comment, with #1 impact when image preflight blocks adapter execution. The static-lint fallback-tar weakness is a #6 comment, not a new issue, because the worker runtime `check --load-fallback --run-smoke` path still catches tar missing/mismatch, identity mismatch, and smoke failure. The SWE image identity part is #11 context. No #8-specific new finding, except that worker/rootless readiness is still a runtime input. No #10 secret-redaction issue was found in the image-check JSON itself; result parsers should still treat logs as source artifacts and apply the existing #10 sanitizer if any log excerpts are copied.

Root-cause evidence:

- `scripts/agentic_bench_images.py:488-619` returns rich `agentic_bench.image_check.v1` JSON with `counts.tar_verified`, `counts.loaded`, `counts.smoke_passed`, `counts.identity_mismatch`, and per-image `fallback`, `inspect_attempts`, `load_status`, `present_ref`, and `smoke_status` fields.
- `scripts/agentic_bench_images.py:978-982` makes the CLI fail on `errors`, `tar_mismatch`, `identity_mismatch`, `missing`, or `tar_missing`, so the checker itself does not fake-green smoke failure, identity mismatch, or missing fallback tar.
- `scripts/agentic_bench_suite.py:1062-1140` runs image preflight commands and records only coarse `status`, `exit_code`, `fatal`, timestamps, and `log_path`; it does not parse the checker JSON from stdout.
- `scripts/agentic_bench_suite.py:1198-1208` writes `agentic_bench.image_preflight_summary.v1` with counts by pass/fail and result rows, but those rows do not include checker counts or per-image fallback/load/smoke/identity details.
- `scripts/agentic_bench_suite.py:1281-1300` writes `agentic_bench.result.v1` without any `source`, `image_preflight`, `image_preflight_summary_path`, image manifest id/path, checker JSON digest, or per-image fallback provenance. Execute `summary.json` only carries the enriched execution row from `_attach_benchmark_result()` (`scripts/agentic_bench_suite.py:1333-1341`).

COMMENT-READY for #12/#6/#11: structured suite summaries and normalized results should preserve image-check evidence, not only a log pointer

severity: HIGH

dedup: comment-on-#12 for normalized result provenance and result artifact self-containment; comment-on-#6 because fallback-load/run-smoke evidence is the worker warmup proof; comment-on-#11 because identity mismatch/remediation for SWE django10097 must be auditable. Not a new issue because checker JSON already contains the raw evidence and #12 already covers missing normalized/source provenance.

location: `scripts/agentic_bench_images.py:488-619`, `scripts/agentic_bench_images.py:978-982`, `scripts/agentic_bench_suite.py:1062-1140`, `scripts/agentic_bench_suite.py:1198-1208`, `scripts/agentic_bench_suite.py:1281-1300`, `scripts/agentic_bench_suite.py:1333-1341`, `manifests/images/swebench_verified_django10097.yaml:16-43`, `manifests/bench_registry.yaml:51-59`

static_repro:

- Existing verification `image_preflight_summary.json` files for RepoZero and TB2.1 have top-level keys `counts`, `fail_on_optional`, `include_optional`, `results`, `schema_version`, `status`, and `suite_id`; their first result row keys are only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`. They have no `image_check`, `image_check_summary`, `loaded`, `load_status`, `smoke_passed`, `identity_mismatch`, or `fallback` fields.
- The corresponding preflight logs do contain the checker JSON payload markers: `schema_version`, `agentic_bench.image_check.v1`, `loaded`, `smoke_status`, and `fallback` were present in the sampled logs. This means evidence exists only as parseable log stdout, not as structured suite summary or normalized result provenance.
- Synthetic checker probe with stale/wrong initial image identity, verified fallback tar, successful `docker load`, and passing smoke returned `counts.present=1`, `counts.tar_verified=1`, `counts.loaded=1`, `counts.smoke_passed=1`, `counts.identity_mismatch=0`, per-image `status=present`, `load_status=loaded`, `smoke_status=passed`, `present_ref=example/runtime:latest`, and `inspect_identity_statuses=['mismatch','match']`. The checker preserves enough evidence to know fallback replaced a wrong alias, but the suite summary would currently collapse that to `status=pass` plus a log path.
- Synthetic smoke-failure probe returned `counts.errors=1`, per-image `status=present`, and `smoke_status=failed`; the CLI would return rc 2 via `counts.errors`, so the checker does not fake-green image smoke. A downstream consumer reading only per-image `status=present` would need `smoke_status`/`counts.errors`, which are not promoted into suite result rows today.
- Current `lint-registry` for `required_for_swebench_django10097_promotion_smoke` returns rc 0 with `required_images=2`, `required_with_fallback_sha=2`, and `required_without_offline_transport=0`; both SWE rows have fallback sha and no internal digest ref. Combined TB2+SWE promotion lint currently returns rc 1 with `required_images=91`, `required_with_digest_ref=1`, `required_with_fallback_sha=53`, and `required_without_offline_transport=38`; the remaining failures are TB2.

Impact:

- After a worker run such as the SWE django10097 fallback proof, a human can recover the important facts by opening the preflight log, but a dashboard, aggregator, issue closer, or normalized `agentic_bench.result.v1` consumer cannot tell from structured artifacts that the worker first saw an identity mismatch, loaded the verified fallback tar, re-inspected to the expected identity, and then passed smoke.
- If an adapter runs after image preflight succeeds, the normalized benchmark result has no first-class pointer to the image-preflight summary/log or image manifest. If the adapter is blocked by image preflight, #1 currently reports a process-level failure but not a structured image-preflight cause with per-image evidence.
- This weakens reproducibility comments for #6/#11: `pass` in `image_preflight_summary.json` means only that the checker process returned 0, not which image rows were loaded, verified, pulled, smoked, or repaired from identity mismatch.

Exact missing structured fields to add under #12:

- In `image_preflight_summary.results[]`: add `image_check_schema_version`, `image_check_manifest`, `image_check_bench_id`, `image_check_counts`, and an allowlisted `image_check_images[]` list with `id`, `role`, `required`, `status`, `present_ref`, `load_status`, `pull_status`, `smoke_status`, `fallback.sha256_status`, `fallback.tar_paths` or safe path basenames, `fallback.sha256`, and `inspect_attempts[].ref/returncode/identity_status/actual_image_id/expected_image_ids`.
- In `agentic_bench.result.v1`: add `source.image_preflight_summary_path`, `source.image_preflight_log_path`, `source.image_manifest_paths[]`, `source.image_check_artifacts[]`, and an `image_preflight` object with `status`, `exit_code`, `policy`, `required`, `counts`, and the same per-image allowlist when available.
- In execute `summary.json` rows: add `image_preflight_status`, `image_preflight_log_path`, `image_check_counts`, and `image_check_result_path` or `image_check_json_pointer`. Do not rely on `status=pass` and `log_path` alone.
- For blocked adapters, map benchmark failure category to `image_preflight_failed` or `image_preflight_blocked` rather than the generic `adapter_crash` from `_benchmark_result_for_run()`.

COMMENT-READY for #6: `lint-registry` is presence-of-transport metadata, not proof that fallback tar exists or hashes at lint time

severity: MEDIUM

dedup: comment-on-#6. Not a new issue because runtime `check --load-fallback` still verifies actual tar presence and sha before load, and returns nonzero on `tar_missing`/`tar_mismatch`. This is a static promotion-gate caveat.

location: `scripts/agentic_bench_images.py:328-384`, `scripts/agentic_bench_images.py:690-777`, `scripts/agentic_bench_images.py:918-933`

static_repro: A synthetic manifest with `required: true`, `fallback_tar: missing/runtime.tar`, and a `fallback_tar_sha256` field returns `lint_status=ok`, `required_with_fallback_sha=1`, and `required_without_offline_transport=0` under `lint_image_manifest(..., require_offline_transport=True)`. The lint path checks for an internal digest ref or configured fallback checksum, not whether the tar exists or whether its hash matches. The runtime checker path does compute `_fallback_status()` and would fail later with `tar_missing` or `tar_mismatch`.

impact: As a static registry gate, `lint-registry` can mark a manifest transport-ready when the manifest contains a checksum field but the referenced tar is absent or stale. That does not fake-green worker fallback load or smoke, but it can produce a misleading promotion-stage green before runtime check. Current SWE django10097 has real fallback paths and the handoff records worker smoke evidence; the caveat matters for future TB2/SWE promotion rows.

fix: Keep `lint-registry` as the cheap metadata gate, but either rename/report it as `configured_offline_transport` or add an optional `--verify-fallback-files` mode that resolves fallback tar paths, checks presence, and verifies sha256 without Docker. Promotion should require both static configured transport and a worker `check --load-fallback --run-smoke --json` artifact before calling rows ready.

Cross-lane runtime/images check:

- Runtime lane Round 10/11 focuses on making TB2/SWE transport concrete. It does not contradict this runner/results finding. The runtime ledger proves the transport path can be made real; this lane says the result/provenance layer must preserve the resulting checker JSON structurally.
- Current handoff says SWE django10097 worker smoke ended with `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, and `identity_mismatch=0`. Those exact fields should become machine-readable in suite summary/result artifacts instead of living only in handoff text and checker logs.

### Round 11 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, display truncated by tool.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Remote worktree status/head/history check: rc 0; branch `feat/image-warmup-policy`, head `abac24d`, history includes `bacbde3` and `ce2adf2`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read current runner and runtime lane ledger tails: rc 0.
- Grep/nl reads for `scripts/agentic_bench_images.py`, `scripts/agentic_bench_suite.py`, `manifests/images/swebench_verified_django10097.yaml`, `manifests/bench_registry.yaml`, and focused tests: rc 0.
- Bounded probes over existing `image_preflight_summary.json` and preflight logs: rc 0; printed only keys, counts, booleans, and paths.
- Initial JSON pipe probes for lint-registry had quoting/pipe issues and exited rc 1; rerun with temp files succeeded. SWE-only lint returned `LINT_RC=0`; TB2+SWE lint returned `LINT_RC=1` with counts quoted above.
- Synthetic checker probe for identity mismatch repaired by fallback load and smoke pass: rc 0; counts and statuses quoted above.
- Synthetic smoke-failure probe: rc 0; counts and statuses quoted above.
- Synthetic static lint missing-tar-with-sha probe: rc 0; `lint_status=ok` despite absent tar path, proving the static lint caveat.

Next runner/results subdomain: specify the exact JSON parser for image-check stdout in preflight logs and the allowlisted result fields to persist in `image_preflight_summary.json` and `agentic_bench.result.v1`, without copying raw Docker stderr or full command output.

## Round 11 validation evidence

- `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; concurrent/unowned changes were present in `_coordination/20260625_harbor_bench/HANDOFF.md`, `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`, `manifests/images/README.md`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_protein_assembly_20260626.tsv`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.
- `git diff --stat --` and `git diff --numstat --` for this ledger after the Round 11 append: rc 0, `85 insertions` before this validation block.

## Round 12 image-preflight provenance fixture-ready tests

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Active branch/head observed: `feat/image-warmup-policy` / `65448e4 Record verify fallback follow-up dispatch`; recent history includes `12fe709 Verify fallback files in registry lint`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, or model requests.
- Focus: turn the image-preflight provenance gap into fixture-ready parser tests for identity-mismatch repaired by fallback load and image smoke failure.

No new ISSUE-READY block from this loop.

Dedup judgment: this is test-spec detail for #12 result provenance, #6 image warmup evidence, #11 image identity evidence, #10 redaction, and #1 execution-vs-benchmark split for preflight-blocked runs. It is not a new issue because Round 11 already confirmed checker evidence exists and the suite/result layer drops it. The previous static-lint fallback-file caveat is now superseded by `--verify-fallback-files` in `12fe709` and should remain a closed #6 follow-up, not a reopened finding.

Static root-cause evidence refreshed:

- `scripts/agentic_bench_images.py:328-411` now supports `verify_fallback_files`; when enabled, lint counts `fallback_tar_verified`, `fallback_tar_missing`, and `fallback_tar_mismatch`, and treats missing/mismatched fallback files as missing offline transport.
- `scripts/agentic_bench_images.py:600-613` records `smoke_status` and increments `counts.errors` on smoke failure, but also stores raw `smoke_stderr` in the native checker JSON. That makes a parser allowlist mandatory; raw checker JSON must not be copied wholesale into normalized results.
- `scripts/agentic_bench_images.py:628-643` emits the rich `agentic_bench.image_check.v1` payload with manifest, bench id, mode, counts, and per-image records.
- `scripts/agentic_bench_images.py:1022-1029` returns rc `2` for checker `errors`, `tar_mismatch`, or `identity_mismatch`, rc `1` for `missing` or `tar_missing`, and rc `1` for optional missing only when requested. The checker itself does not fake-green smoke failure.
- `scripts/agentic_bench_suite.py:1027-1057` streams checker stdout/stderr into preflight logs and writes only cached command rc for deduped waiters.
- `scripts/agentic_bench_suite.py:1079-1139` records only coarse per-bench preflight `status`, `exit_code`, `fatal`, timestamps, and `log_path`.
- `scripts/agentic_bench_suite.py:1198-1209` writes `agentic_bench.image_preflight_summary.v1` with coarse pass/fail counts and result rows; it does not parse or promote `agentic_bench.image_check.v1` from logs.
- `scripts/agentic_bench_suite.py:1251-1262` still short-circuits any nonzero execution into `parser_status=not_run`, `status=infra_error`, `failure_category=adapter_crash`; this is the existing #1 interaction for required image-preflight failures.
- `scripts/agentic_bench_suite.py:1281-1300` writes `agentic_bench.result.v1` without `source`, `image_preflight`, `image_preflight_summary_path`, or image-check provenance.
- Existing tests cover required preflight blocking (`scripts/test_agentic_bench_suite.py:404-428`), preflight-only summary output (`scripts/test_agentic_bench_suite.py:502-547`), transport concurrency/dedupe (`scripts/test_agentic_bench_suite.py:548-688`), and fallback-file lint verification (`scripts/test_agentic_bench_images.py:503-543`, `scripts/test_agentic_bench_images.py:546+`). They do not yet assert checker-JSON promotion into summary/result artifacts.

COMMENT-READY fixture contract for #12/#6/#11/#10/#1:

| Fixture | Minimal files | Purpose | Expected parser status | Dedup |
|---|---|---|---|---|
| `tests/fixtures/image_preflight/identity_mismatch_repaired_by_fallback/` | `preflight.log`, `checker.json`, `run_manifest.json`, `expected.image_preflight_summary.subset.json`, `expected.result.subset.json` | Proves a stale/wrong local image identity was repaired by verified fallback load, then smoke passed, and this is visible in structured artifacts. | `image_check_parse_status=parsed`, `image_preflight.status=pass`, `benchmark_result` unchanged by image preflight. | #12 provenance with #6/#11 evidence; not a new issue. |
| `tests/fixtures/image_preflight/smoke_failure/` | `preflight.log`, `checker.json`, `run_manifest.json`, `expected.image_preflight_summary.subset.json`, `expected.result.subset.json` | Proves a required image smoke failure blocks execution while preserving checker evidence and redacting raw stderr. | `image_check_parse_status=parsed`, `image_preflight.status=fail`, `benchmark_result.status=infra_blocked`, `failure_category=image_preflight_failed`. | #1 execution/benchmark split plus #10 redaction; not a new issue. |

### Fixture A: identity mismatch repaired by fallback load

`preflight.log` should contain harmless wrapper text plus exactly one JSON object whose `schema_version` is `agentic_bench.image_check.v1`. The parser should locate the JSON object even if command lines or status text appear before/after it.

Minimal `checker.json` content:

```json
{
  "schema_version": "agentic_bench.image_check.v1",
  "manifest": "manifests/images/unit_identity_repair.yaml",
  "bench_id": "unit_identity_repair",
  "asset_root": "/tmp/agentic-bench-fixture/assets",
  "docker_host": "unix:///tmp/rl/run/docker.sock",
  "mode": {
    "skip_docker": false,
    "allow_pull": false,
    "load_fallback": true,
    "run_smoke": true,
    "fail_on_optional_missing": false
  },
  "counts": {
    "present": 1,
    "missing": 0,
    "unchecked": 0,
    "errors": 0,
    "tar_verified": 1,
    "tar_missing": 0,
    "tar_mismatch": 0,
    "loaded": 1,
    "pulled": 0,
    "smoke_passed": 1,
    "optional_missing": 0,
    "identity_mismatch": 0
  },
  "images": [
    {
      "id": "unit_eval_base",
      "role": "swebench_eval_base",
      "required": true,
      "local_refs": ["unit/eval-base:latest"],
      "image_refs": [],
      "expected_image_ids": ["sha256:expectedbase"],
      "expected_repo_digests": ["unit/eval-base@sha256:expectedrepo"],
      "inspect_attempts": [
        {
          "ref": "unit/eval-base:latest",
          "returncode": 0,
          "identity_status": "mismatch",
          "actual_image_id": "sha256:wrongwrapper",
          "actual_repo_digests": ["unit/wrapper@sha256:wrongrepo"],
          "expected_image_ids": ["sha256:expectedbase"],
          "expected_repo_digests": ["unit/eval-base@sha256:expectedrepo"]
        },
        {
          "ref": "unit/eval-base:latest",
          "returncode": 0,
          "identity_status": "match",
          "actual_image_id": "sha256:expectedbase",
          "actual_repo_digests": ["unit/eval-base@sha256:expectedrepo"],
          "expected_image_ids": ["sha256:expectedbase"],
          "expected_repo_digests": ["unit/eval-base@sha256:expectedrepo"]
        }
      ],
      "fallback": {
        "tar_paths": ["/tmp/agentic-bench-fixture/assets/images/unit/eval-base.tar"],
        "present_paths": ["/tmp/agentic-bench-fixture/assets/images/unit/eval-base.tar"],
        "missing_paths": [],
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sha256_actual": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sha256_status": "match"
      },
      "status": "present",
      "load_status": "loaded",
      "present_ref": "unit/eval-base:latest",
      "smoke_status": "passed"
    }
  ]
}
```

Expected `image_preflight_summary.json` subset after parsing:

```json
{
  "schema_version": "agentic_bench.image_preflight_summary.v1",
  "status": 0,
  "counts": {"pass": 1, "fail": 0, "optional_fail": 0},
  "results": [
    {
      "bench_id": "unit_identity_repair",
      "status": "pass",
      "exit_code": 0,
      "fatal": false,
      "policy": "required",
      "required": true,
      "image_check_parse_status": "parsed",
      "image_check_counts": {
        "present": 1,
        "errors": 0,
        "tar_verified": 1,
        "loaded": 1,
        "smoke_passed": 1,
        "identity_mismatch": 0
      },
      "image_checks": [
        {
          "command_index": 0,
          "schema_version": "agentic_bench.image_check.v1",
          "manifest": "manifests/images/unit_identity_repair.yaml",
          "bench_id": "unit_identity_repair",
          "parse_status": "parsed",
          "counts": {"tar_verified": 1, "loaded": 1, "smoke_passed": 1, "identity_mismatch": 0},
          "images": [
            {
              "id": "unit_eval_base",
              "role": "swebench_eval_base",
              "required": true,
              "status": "present",
              "present_ref": "unit/eval-base:latest",
              "load_status": "loaded",
              "smoke_status": "passed",
              "fallback": {
                "sha256_status": "match",
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "tar_basenames": ["eval-base.tar"]
              },
              "inspect_attempts": [
                {"ref": "unit/eval-base:latest", "returncode": 0, "identity_status": "mismatch", "actual_image_id": "sha256:wrongwrapper", "expected_image_ids": ["sha256:expectedbase"]},
                {"ref": "unit/eval-base:latest", "returncode": 0, "identity_status": "match", "actual_image_id": "sha256:expectedbase", "expected_image_ids": ["sha256:expectedbase"]}
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

Expected `agentic_bench.result.v1` subset for a full execute run that passed preflight and then ran the adapter:

```json
{
  "schema_version": "agentic_bench.result.v1",
  "bench_id": "unit_identity_repair",
  "execution": {"status": "pass", "adapter_status": "pass", "exit_code": 0},
  "source": {
    "image_preflight_summary_path": "controller/image_preflight_summary.json",
    "image_preflight_log_path": "controller/logs/unit_identity_repair.image_preflight.log",
    "image_manifest_paths": ["manifests/images/unit_identity_repair.yaml"],
    "image_check_artifacts": [
      {"role": "image_check_stdout_json", "status": "parsed", "path": "controller/logs/unit_identity_repair.image_preflight.log", "json_pointer": "$.results[0].image_checks[0]", "read_policy": "allowlist_json"}
    ]
  },
  "image_preflight": {
    "status": "pass",
    "exit_code": 0,
    "required": true,
    "policy": "required",
    "parse_status": "parsed",
    "counts": {"tar_verified": 1, "loaded": 1, "smoke_passed": 1, "identity_mismatch": 0, "errors": 0},
    "images": [
      {"id": "unit_eval_base", "status": "present", "load_status": "loaded", "smoke_status": "passed", "fallback": {"sha256_status": "match"}}
    ]
  }
}
```

Exact assertions for Fixture A:

- `summary.status == 0`; `summary.results[0].status == "pass"`; `summary.results[0].image_check_parse_status == "parsed"`.
- `summary.results[0].image_check_counts.loaded == 1`, `tar_verified == 1`, `smoke_passed == 1`, `identity_mismatch == 0`, and `errors == 0`.
- `summary.results[0].image_checks[0].images[0].inspect_attempts[*].identity_status == ["mismatch", "match"]`.
- `result.image_preflight.status == "pass"` and `result.source.image_check_artifacts[0].read_policy == "allowlist_json"`.
- Serialized summary/result do not contain raw Docker load stdout/stderr or full command text; only allowlisted refs, ids, digest/status fields, and safe path basenames are present.

### Fixture B: smoke failure with redacted stderr

Minimal `checker.json` content should be the same outer shape, but with one present image whose smoke fails:

```json
{
  "schema_version": "agentic_bench.image_check.v1",
  "manifest": "manifests/images/unit_smoke_failure.yaml",
  "bench_id": "unit_smoke_failure",
  "asset_root": "/tmp/agentic-bench-fixture/assets",
  "docker_host": "unix:///tmp/rl/run/docker.sock",
  "mode": {"skip_docker": false, "allow_pull": false, "load_fallback": false, "run_smoke": true, "fail_on_optional_missing": false},
  "counts": {"present": 1, "missing": 0, "unchecked": 0, "errors": 1, "tar_verified": 0, "tar_missing": 0, "tar_mismatch": 0, "loaded": 0, "pulled": 0, "smoke_passed": 0, "optional_missing": 0, "identity_mismatch": 0},
  "images": [
    {
      "id": "unit_smoke_image",
      "role": "terminal_bench_task_image",
      "required": true,
      "local_refs": ["unit/smoke:latest"],
      "inspect_attempts": [{"ref": "unit/smoke:latest", "returncode": 0, "identity_status": "not_configured", "actual_image_id": "sha256:smokeimage"}],
      "status": "present",
      "present_ref": "unit/smoke:latest",
      "smoke_status": "failed",
      "smoke_stderr": "unit smoke failed; AUTH_SENTINEL_SHOULD_NOT_APPEAR"
    }
  ]
}
```

Expected `image_preflight_summary.json` subset after parsing:

```json
{
  "schema_version": "agentic_bench.image_preflight_summary.v1",
  "status": 1,
  "counts": {"pass": 0, "fail": 1, "optional_fail": 0},
  "results": [
    {
      "bench_id": "unit_smoke_failure",
      "status": "fail:2",
      "exit_code": 2,
      "fatal": true,
      "policy": "required",
      "required": true,
      "image_check_parse_status": "parsed",
      "image_check_counts": {"present": 1, "errors": 1, "smoke_passed": 0},
      "image_checks": [
        {
          "command_index": 0,
          "schema_version": "agentic_bench.image_check.v1",
          "manifest": "manifests/images/unit_smoke_failure.yaml",
          "bench_id": "unit_smoke_failure",
          "parse_status": "parsed",
          "counts": {"present": 1, "errors": 1, "smoke_passed": 0},
          "images": [
            {"id": "unit_smoke_image", "role": "terminal_bench_task_image", "required": true, "status": "present", "present_ref": "unit/smoke:latest", "smoke_status": "failed", "smoke_stderr_redacted": true}
          ],
          "redactions": [
            {"path": "images[0].smoke_stderr", "reason": "raw_smoke_stderr_excluded"}
          ]
        }
      ]
    }
  ]
}
```

Expected `agentic_bench.result.v1` subset for a full execute run blocked by required preflight:

```json
{
  "schema_version": "agentic_bench.result.v1",
  "bench_id": "unit_smoke_failure",
  "execution": {"status": "fail", "adapter_status": "fail:image_preflight:2", "exit_code": 2},
  "benchmark_result": {"parser_status": "not_run", "status": "infra_blocked", "metric": "image_preflight", "passed": false, "score_claim_valid": false, "failure_category": "image_preflight_failed"},
  "source": {
    "image_preflight_summary_path": "controller/image_preflight_summary.json",
    "image_preflight_log_path": "controller/logs/unit_smoke_failure.image_preflight.log",
    "image_manifest_paths": ["manifests/images/unit_smoke_failure.yaml"],
    "native_artifacts": [],
    "image_check_artifacts": [
      {"role": "image_check_stdout_json", "status": "parsed", "path": "controller/logs/unit_smoke_failure.image_preflight.log", "json_pointer": "$.results[0].image_checks[0]", "read_policy": "allowlist_json"}
    ]
  },
  "image_preflight": {
    "status": "fail",
    "exit_code": 2,
    "required": true,
    "policy": "required",
    "parse_status": "parsed",
    "counts": {"present": 1, "errors": 1, "smoke_passed": 0},
    "images": [{"id": "unit_smoke_image", "status": "present", "smoke_status": "failed", "smoke_stderr_redacted": true}],
    "redactions": [{"path": "images[0].smoke_stderr", "reason": "raw_smoke_stderr_excluded"}]
  }
}
```

Exact assertions for Fixture B:

- `summary.status == 1`; `summary.results[0].status == "fail:2"`; `summary.results[0].fatal is True`.
- `summary.results[0].image_check_parse_status == "parsed"`; `image_check_counts.errors == 1`; `image_check_counts.smoke_passed == 0`.
- `result.execution.status == "fail"` and `result.execution.adapter_status == "fail:image_preflight:2"`.
- `result.benchmark_result.status == "infra_blocked"`; `failure_category == "image_preflight_failed"`; `score_claim_valid is False`.
- `result.image_preflight.images[0].smoke_status == "failed"` and `smoke_stderr_redacted is True`.
- Serialized summary/result must not contain `AUTH_SENTINEL_SHOULD_NOT_APPEAR`, raw `smoke_stderr`, raw command lines, raw Docker stderr/stdout, raw env values, or any adapter/model transcript text. It may contain the safe redaction key path `images[0].smoke_stderr`.

Parser behavior required by the fixtures:

- Parse only JSON objects with `schema_version == "agentic_bench.image_check.v1"` from preflight logs; ignore command/status lines and malformed surrounding text.
- If multiple preflight commands exist, preserve all parsed checker payloads as `image_checks[]` with stable `command_index` and aggregate a bounded `image_check_counts` object at the result row level.
- Treat raw checker fields as untrusted native artifacts. Promote only allowlisted scalar/list fields: schema version, manifest, bench id, mode booleans, counts, image id/role/required/status/present ref, load/pull/smoke statuses, fallback sha status/sha/tar basename, and inspect identity status/id fields.
- Never copy raw `smoke_stderr`, `load_stderr`, `pull_stderr`, full command strings, env values, or stdout/stderr bodies into `image_preflight_summary.json` or `agentic_bench.result.v1`.
- A required preflight failure should not become generic `adapter_crash`. It should keep process status in `execution`, classify benchmark status as `infra_blocked`, and preserve parsed image-check evidence under `image_preflight` and `source.image_check_artifacts[]`.
- A passing preflight that repaired identity through fallback load should be distinguishable from an image that was already correct: the normalized output must preserve at least `loaded=1`, `fallback.sha256_status=match`, and the `inspect_attempts` identity progression.

Minimal tests to add before implementation:

1. `test_image_preflight_log_parser_extracts_identity_repair_check_json`: load Fixture A `preflight.log`, assert exactly one parsed check and identity statuses `["mismatch", "match"]`.
2. `test_image_preflight_summary_promotes_identity_repair_fields`: synthesize `_execute_image_preflights()` output from Fixture A, assert the expected summary subset above while preserving existing coarse fields.
3. `test_result_artifact_includes_image_preflight_provenance_on_pass`: attach a synthetic passing execution result plus Fixture A summary, assert `source.image_preflight_summary_path`, `source.image_check_artifacts[]`, and `image_preflight.counts.loaded == 1`.
4. `test_image_preflight_log_parser_redacts_smoke_stderr`: load Fixture B, assert `smoke_stderr` is excluded and only `smoke_stderr_redacted` plus a redaction key path remain.
5. `test_preflight_smoke_failure_blocks_benchmark_without_adapter_crash`: attach Fixture B to a synthetic `fail:image_preflight:2` execution and assert `benchmark_result.status == "infra_blocked"`, not `infra_error`/`adapter_crash`.
6. `test_serialized_image_preflight_results_are_secret_clean`: serialize both expected summaries/results and assert absence of `AUTH_SENTINEL_SHOULD_NOT_APPEAR`, raw stderr field names, raw command text, and known secret-bearing env key names except allowed redaction key paths.

Cross-lane runtime/images check:

- Runtime-images latest ledger remains focused on concrete TB2/SWE transport population and worker image readiness. It does not contradict this runner/results contract.
- `12fe709` closes the static `fallback_tar_sha256`-without-file gap by adding `--verify-fallback-files`; Round 12 should therefore focus on making the existing runtime checker proof machine-readable, not on another transport gate.
- The fixture expectations above are compatible with future P0 digest-only or fallback-tar transport. The result layer should report what the checker observed (`pulled`, `loaded`, `tar_verified`, `smoke_passed`, identity statuses), independent of how the manifest row was statically linted.

### Round 12 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first before remote work.
- Read `superpowers:using-superpowers` and `superpowers:systematic-debugging` instructions: rc 0.
- Remote status/head/history check on `swe_dev`: rc 0; branch `feat/image-warmup-policy`, observed head `65448e4`, with `12fe709` in history, status output empty at that moment.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read current runner ledger tail: rc 0.
- Grep for `verify_fallback`, `fallback_sha`, `image_preflight`, and `agentic_bench.image_check`: rc 0.
- `nl`/`sed` reads for `scripts/agentic_bench_images.py`, `scripts/agentic_bench_suite.py`, `scripts/test_agentic_bench_images.py`, and `scripts/test_agentic_bench_suite.py`: rc 0.
- Read current runtime-images lane tail for cross-lane dedup: rc 0.
- First append attempt failed locally due shell quoting before remote write: rc 1; no ledger write occurred.
- Pre-append `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.

## Round 12 validation evidence

- `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch2_20260626.tsv` and `scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc` were present and left untouched.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.

## Round 13 batch2 image-check provenance red-test map

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` before code/evidence inspection.
- Active branch/head observed: `feat/image-warmup-policy` / `eb552a3 Materialize TB2 low-risk transport batch`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: cross-check Round 12 image-check provenance contract against current scripts/tests and the new batch2 worker evidence JSON, then reduce it to the minimal red tests an implementation agent should add.

No new ISSUE-READY block from this loop.

Dedup judgment: all findings remain covered by existing issues. Summary/result provenance is #12, image warmup proof is #6, image identity evidence is #11, redaction is #10, and required preflight failure classification is #1. The current head adds real batch2 evidence but does not introduce a separate root cause. It gives a better fixture for the already-known #12/#6/#11 gap.

Current batch2 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_check_20260626.json`.
- It is already a native checker payload: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_lowrisk_batch2_worker_smoke`.
- Counts: `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, `pulled=0`.
- Images: four required `terminal_bench_task_runtime` rows for `tb2_openssl_selfsigned_cert`, `tb2_regex_chess`, `tb2_schemelike_metacircular_eval`, and `tb2_sqlite_db_truncate`.
- Each image has `status=present`, `load_status=loaded`, `smoke_status=passed`, `fallback.sha256_status=match`, and inspect attempts ending in `identity_status=match`.
- No image in this evidence file has stderr fields, so it is the right happy-path provenance fixture. Redaction still needs a synthetic smoke-failure fixture with `smoke_stderr`.

Static current-code cross-check:

- `scripts/agentic_bench_images.py:600-613` can include raw `smoke_stderr` on smoke failure, so any normalizer must use an allowlist and redaction rather than copying checker JSON wholesale.
- `scripts/agentic_bench_images.py:628-643` returns all fields needed for the provenance contract in `agentic_bench.image_check.v1`.
- `scripts/agentic_bench_images.py:1018-1029` returns nonzero for smoke errors, tar/identity mismatch, missing images, or requested optional-missing failure. The checker does not fake-green the image smoke.
- `scripts/agentic_bench_suite.py:1027-1057` caches only preflight return codes. The owner log receives checker stdout; cached waiters write only `[image_preflight_cached] ... rc=N`. If implementation parses only per-run logs, identical preflight commands can lose provenance for cached rows.
- `scripts/agentic_bench_suite.py:1079-1139` stores only coarse preflight row fields: `bench_id`, `required`, `policy`, `status`, `exit_code`, `fatal`, timestamps, and `log_path`.
- `scripts/agentic_bench_suite.py:1198-1209` writes `agentic_bench.image_preflight_summary.v1`, but does not parse/promote checker JSON into `image_check_counts`, `image_checks`, or source pointers.
- `scripts/agentic_bench_suite.py:1251-1262` classifies any nonzero execution as `benchmark_result.status=infra_error` and `failure_category=adapter_crash`, including `fail:image_preflight:2`.
- `scripts/agentic_bench_suite.py:1281-1300` writes `agentic_bench.result.v1` without `source`, `image_preflight`, `image_preflight_summary_path`, or `image_check_artifacts`.
- Existing tests cover adapter blocking, RepoZero benchmark-vs-execution split, preflight-only coarse summary, preflight concurrency/dedupe, and fallback-file lint. They do not assert checker JSON promotion, normalized result image-preflight provenance, `image_preflight_failed` classification, or positive redaction while preserving parsed smoke-failure status.

Synthetic current-behavior probe:

- Feeding the batch2 worker JSON through `_execute_image_preflights()` as a preflight command stdout returns rc 0 and writes a log containing `agentic_bench.image_check.v1`, but the summary row keys remain only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`.
- In that successful probe, `image_check_counts in row == False` and `image_checks in row == False`.
- A synthetic `_attach_benchmark_result()` call with `status=fail:image_preflight:2` and `exit_code=2` still writes `benchmark_result.status=infra_error`, `failure_category=adapter_crash`, with no `source` and no `image_preflight` object.
- This probe confirms the Round 12 contract is still red against current head, and the red tests below should fail before implementation.

### Minimal red tests for the implementation agent

1. `test_image_preflight_summary_promotes_batch2_checker_json_from_log`

- Fixture input: copy or distill `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_check_20260626.json` into a stable test fixture such as `scripts/fixtures/image_preflight/tb2_lowrisk_batch2_worker_check.json`.
- Test shape: run `_execute_image_preflights()` with a temp command that prints this JSON and exits 0. Do not invoke Docker or the real checker.
- Expected current failure: summary row lacks `image_check_counts` and `image_checks`.
- Required assertions after implementation:
  - `rc == 0`, `summary.status == 0`, `summary.results[0].status == "pass"`.
  - `summary.results[0].image_check_parse_status == "parsed"`.
  - `summary.results[0].image_check_counts.tar_verified == 4`, `loaded == 4`, `present == 4`, `smoke_passed == 4`, `identity_mismatch == 0`, `errors == 0`.
  - `len(summary.results[0].image_checks[0].images) == 4`.
  - Every promoted image has `required is True`, `role == "terminal_bench_task_runtime"`, `status == "present"`, `load_status == "loaded"`, `smoke_status == "passed"`, `fallback.sha256_status == "match"`, and final inspect identity status `match`.
  - Promoted fallback paths are either safe basenames or approved pointer fields; raw stdout/stderr bodies are absent.

2. `test_result_artifact_includes_image_preflight_provenance_on_pass`

- Fixture input: same batch2 checker JSON and the image-preflight summary produced by test 1, plus a synthetic passing adapter execution.
- Expected current failure: `agentic_bench.result.v1` has no `source` object and no `image_preflight` object.
- Required assertions after implementation:
  - `result.execution.status == "pass"` and normal benchmark parser semantics remain unchanged.
  - `result.source.image_preflight_summary_path` points at `controller/image_preflight_summary.json`.
  - `result.source.image_preflight_log_path` points at the preflight log.
  - `result.source.image_manifest_paths` contains the checker manifest path.
  - `result.source.image_check_artifacts[0]` has `role=image_check_stdout_json`, `status=parsed`, `read_policy=allowlist_json`, and a stable `json_pointer` into the summary.
  - `result.image_preflight.status == "pass"`, `parse_status == "parsed"`, and `result.image_preflight.counts.loaded == 4`, `tar_verified == 4`, `smoke_passed == 4`.

3. `test_required_image_preflight_failure_is_infra_blocked_not_adapter_crash`

- Fixture input: synthetic execution result with `status=fail:image_preflight:2`, `exit_code=2`, and a parsed image-check failure summary. A tiny synthetic checker JSON with `counts.errors=1`, `smoke_passed=0`, and one `smoke_status=failed` image is enough.
- Expected current failure: `_attach_benchmark_result()` writes `benchmark_result.status=infra_error` and `failure_category=adapter_crash`.
- Required assertions after implementation:
  - `result.execution.status == "fail"` and `result.execution.adapter_status == "fail:image_preflight:2"`.
  - `result.benchmark_result.parser_status == "not_run"`.
  - `result.benchmark_result.status == "infra_blocked"`.
  - `result.benchmark_result.metric == "image_preflight"`.
  - `result.benchmark_result.score_claim_valid is False`.
  - `result.benchmark_result.failure_category == "image_preflight_failed"`.
  - Parsed `image_preflight` evidence is still present under `result.image_preflight` and `source.image_check_artifacts[]`.

4. `test_image_check_parser_redacts_smoke_stderr_but_preserves_failure_status`

- Fixture input: synthetic `agentic_bench.image_check.v1` with one required image, `status=present`, `smoke_status=failed`, `counts.errors=1`, and raw `smoke_stderr` containing a sentinel such as `AUTH_SENTINEL_SHOULD_NOT_APPEAR`.
- Expected current failure: there is no positive parsed/redacted image-check field at all. A test that asserts only sentinel absence would falsely pass today, so it must also assert parsed failure status.
- Required assertions after implementation:
  - `image_check_parse_status == "parsed"`.
  - The promoted image has `smoke_status == "failed"` and `smoke_stderr_redacted is True`.
  - `redactions[]` includes a key-path-only entry such as `images[0].smoke_stderr`.
  - Serialized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` do not contain the sentinel, raw `smoke_stderr` value, raw Docker stdout/stderr, raw command lines, env values, or model/adapter transcript text.

5. Cache-path guard if the implementation parses through `_execute_image_preflights()`

- This is not a separate issue, but it is a cheap regression guard for the existing command-cache path at `scripts/agentic_bench_suite.py:1027-1057`.
- Test shape: two runs share the exact same preflight command that prints the batch2 checker JSON and exits 0, with `image_preflight_concurrency > 1`.
- Required assertions after implementation:
  - `summary.image_preflight_unique_commands == 1` remains true.
  - Both result rows have `image_check_parse_status == "parsed"` and identical allowlisted `image_check_counts`, even though only one subprocess executed.
  - Cached rows must not be limited to a bare `[image_preflight_cached] ... rc=0` log pointer with no structured image-check evidence.

Implementation notes for red-test authors:

- Keep batch2 as the happy-path real fixture because it exercises `tar_verified`, `loaded`, `smoke_passed`, fallback sha match, and worker rootless fallback load without needing Docker in unit tests.
- Keep redaction as a synthetic failure fixture because the batch2 evidence intentionally has no stderr fields.
- Do not make test fixtures depend on mutable `_coordination/` paths at runtime. Copy a distilled JSON fixture under a test fixture directory or generate it inline from a small allowlisted dict.
- Assertions should inspect serialized JSON strings as well as Python objects, because #10 is about what gets written to disk.
- Do not make the normalized result copy the whole checker JSON. Preserve an allowlisted subset and safe source pointers.

Cross-lane runtime/images check:

- Runtime-images Round 12 confirms batch2 materialized four low-risk TB2 transports and warns that worker direct P0 pull still fails under the rootless daemon while fallback load/run-smoke passes.
- This runner/results lane has no contradiction with #6/#8 runtime notes. The batch2 JSON proves the fallback-load path is valid; this lane says suite summaries and normalized results need to retain that proof structurally.
- The P0 pull failure remains #8/runtime readiness, not a runner/result parser issue.

### Round 13 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Remote handoff/head/status command: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `eb552a3 Materialize TB2 low-risk transport batch`, and no status output at that moment.
- Read current runner ledger Round 12 tail: rc 0.
- Read current runtime-images lane tail: rc 0.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_check_20260626.json`: rc 0; printed only schema, counts, image ids/roles/statuses, key names, fallback sha statuses, inspect identity statuses, and stderr-field presence.
- Grep for image-check provenance/result fields across scripts/reports/ledger: rc 0, with harmless `grep: tests: No such file or directory` because this repo keeps tests under `scripts/test_*.py`.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_suite.py`, and `scripts/test_agentic_bench_images.py`: rc 0.
- Listed batch2 evidence files in `_coordination/20260625_harbor_bench/inventory`: rc 0.
- First synthetic probe had outer rc 0 but generated preflight subprocess rc 1 due a one-liner quoting mistake; it was ignored and rerun.
- Corrected synthetic probe with a temp helper script: rc 0. It confirmed `_execute_image_preflights()` returns summary status pass while omitting `image_check_counts`/`image_checks`, and `_attach_benchmark_result()` maps `fail:image_preflight:2` to `infra_error`/`adapter_crash` with no `source` or `image_preflight` object.

## Round 13 validation evidence

- `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; concurrent/unowned `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch3_worker_check_20260626.json`, and `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch3_20260626.tsv` were present and left untouched.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.

## Round 14 one-command runner contract after TB2 batch3

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` before code/evidence inspection.
- Active branch/head observed: `feat/image-warmup-policy` / `c7a0eef Materialize TB2 low-risk transport batch 3`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: one-command runner contract after batch3: image-preflight provenance, adapter-blocked status, invocation-unique outputs, summary ordering, and redaction.

No new ISSUE-READY block from this loop.

Dedup judgment: all observed gaps remain covered by existing issues. Image-preflight provenance is #12 with #6/#11 evidence, adapter-blocked status is #1, invocation-unique output roots and run dirs are #2, and redaction is #10. Summary ordering is already fixed by the manifest-order sort and covered by current tests, so there is no #3 regression. Batch3 adds a stronger happy-path fixture but no new root cause.

Current batch3 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch3_worker_check_20260626.json`.
- It is already a native checker payload: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_lowrisk_batch3_worker_smoke`.
- Counts: `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, `pulled=0`.
- Images: five required `terminal_bench_task_runtime` rows for `tb2_raman_fitting`, `tb2_regex_log`, `tb2_rstan_to_pystan`, `tb2_sparql_university`, and `tb2_sqlite_with_gcov`.
- Each promoted image has `status=present`, `load_status=loaded`, `smoke_status=passed`, `fallback.sha256_status=match`, and inspect attempts ending in `identity_status=match`.
- No image in this evidence file has stderr fields. Use it as the current real happy-path fixture; keep a synthetic smoke-failure fixture for #10 redaction.

Current-code cross-check:

- Deterministic invocation paths remain: `scripts/agentic_bench_suite.py:812-823` builds `run_id` from `suite_id + bench_id + profile_id`, `run_dir` as `<run_root>/<suite_id>/<bench_id>`, and `RUN_TAG` as `suite_id`. There is no invocation id.
- Controller output root is deterministic too: `scripts/agentic_bench_suite.py:970-976` returns `<run_root>/<suite_id>/_controller` when no explicit `--output-dir` is given.
- Required preflight is run before the adapter in full execute mode (`scripts/agentic_bench_suite.py:979-1024`), but a failing preflight returns only `status=fail:image_preflight:N`, `exit_code`, timestamps, and log path.
- Image-preflight-only summary rows remain coarse: `scripts/agentic_bench_suite.py:1079-1139` records only status/exit/fatal/timestamps/log path, and `scripts/agentic_bench_suite.py:1198-1209` writes no `image_check_counts`, `image_checks`, or checker source pointer.
- Nonzero execution still short-circuits parser/result classification: `scripts/agentic_bench_suite.py:1251-1262` maps every nonzero to `benchmark_result.status=infra_error` and `failure_category=adapter_crash`, including image-preflight failures.
- Normalized result docs still omit provenance: `scripts/agentic_bench_suite.py:1281-1300` writes no `source`, `image_preflight`, `image_preflight_summary_path`, invocation id, run dir, model profile, worker id, parser object, or image-check artifact pointer.
- Execute summary ordering is no longer a live bug: `scripts/agentic_bench_suite.py:1338-1341` sorts persisted results back to manifest order, and `scripts/test_agentic_bench_suite.py:472-500` covers this behavior.
- The checker can emit raw smoke stderr on failure (`scripts/agentic_bench_images.py:600-613`), while `agentic_bench.image_check.v1` contains the provenance payload needed by a normalizer (`scripts/agentic_bench_images.py:628-643`). A parser must allowlist/redact instead of copying the checker JSON wholesale.

Synthetic current-behavior probe:

- Feeding the batch3 worker JSON through `_execute_image_preflights()` as preflight stdout returns rc 0 and writes a log containing `agentic_bench.image_check.v1`.
- The resulting `image_preflight_summary.json` row still has only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`.
- `image_check_counts in row == False` and `image_checks in row == False`.
- `_local_output_root()` returns the same controller output root for two plans with the same `suite_id` and `run_root`.
- `_attach_benchmark_result()` with `status=fail:image_preflight:2`, `exit_code=2` still writes `benchmark_result.status=infra_error`, `failure_category=adapter_crash`, with no `source` or `image_preflight` object.

### Minimal red-test recommendations

1. `test_image_preflight_summary_promotes_batch3_checker_json_from_log`

- Fixture input: distill `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch3_worker_check_20260626.json` into a stable unit fixture. Do not load the mutable `_coordination` path at test runtime.
- Test shape: `_execute_image_preflights()` with a temp command that prints the fixture JSON and exits 0. No Docker or real checker invocation.
- Expected current failure: summary row lacks `image_check_counts` and `image_checks`.
- Required assertions after implementation:
  - `rc == 0`, `summary.status == 0`, row `status == "pass"`.
  - `row.image_check_parse_status == "parsed"`.
  - `row.image_check_counts.tar_verified == 5`, `loaded == 5`, `present == 5`, `smoke_passed == 5`, `identity_mismatch == 0`, `errors == 0`.
  - `len(row.image_checks[0].images) == 5`.
  - Every promoted image is required, has role `terminal_bench_task_runtime`, `status=present`, `load_status=loaded`, `smoke_status=passed`, `fallback.sha256_status=match`, and final inspect identity status `match`.
  - Raw Docker stdout/stderr, full command text, and env values are absent from serialized summary output.

2. `test_result_artifact_includes_batch3_image_preflight_provenance_on_pass`

- Fixture input: the batch3 happy-path checker JSON and a synthetic passing adapter execution.
- Expected current failure: `agentic_bench.result.v1` has no `source`, no `image_preflight`, and no image-check artifact pointer.
- Required assertions after implementation:
  - `result.execution.status == "pass"`.
  - `result.source.image_preflight_summary_path` points at `controller/image_preflight_summary.json`.
  - `result.source.image_preflight_log_path` points at the preflight log.
  - `result.source.image_manifest_paths[]` includes the checker manifest path.
  - `result.source.image_check_artifacts[0]` has `role=image_check_stdout_json`, `status=parsed`, `read_policy=allowlist_json`, and a stable `json_pointer` into the summary.
  - `result.image_preflight.status == "pass"`, `parse_status == "parsed"`, and counts preserve `loaded=5`, `tar_verified=5`, `smoke_passed=5`.

3. `test_required_image_preflight_failure_is_infra_blocked_not_adapter_crash`

- Fixture input: synthetic execution result with `status=fail:image_preflight:2`, `exit_code=2`, plus a parsed image-check failure summary containing one required image with `smoke_status=failed` and `counts.errors=1`.
- Expected current failure: `benchmark_result.status=infra_error` and `failure_category=adapter_crash`.
- Required assertions after implementation:
  - `execution.status == "fail"`, `execution.adapter_status == "fail:image_preflight:2"`.
  - `benchmark_result.parser_status == "not_run"`.
  - `benchmark_result.status == "infra_blocked"`.
  - `benchmark_result.metric == "image_preflight"`.
  - `benchmark_result.score_claim_valid is False`.
  - `benchmark_result.failure_category == "image_preflight_failed"`.
  - Parsed image-preflight evidence remains present under `result.image_preflight` and `source.image_check_artifacts[]`.

4. `test_image_check_parser_redacts_smoke_stderr_but_preserves_failure_status`

- Fixture input: synthetic `agentic_bench.image_check.v1` containing raw `smoke_stderr` with a sentinel such as `AUTH_SENTINEL_SHOULD_NOT_APPEAR`.
- Expected current failure: there is no positive parsed/redacted image-check field at all. A sentinel-only absence assertion would falsely pass today.
- Required assertions after implementation:
  - `image_check_parse_status == "parsed"`.
  - Promoted image retains `smoke_status == "failed"`.
  - Promoted image has `smoke_stderr_redacted is True`.
  - `redactions[]` records only safe key paths, for example `images[0].smoke_stderr`.
  - Serialized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` do not contain the sentinel, raw `smoke_stderr`, raw command lines, Docker stderr/stdout bodies, env values, or model/adapter transcript text.

5. `test_invocation_unique_controller_and_bench_run_dirs_are_persisted`

- Dedup: comment-ready for #2, not a new issue.
- Test shape: build two plans for the same `suite_id`, `bench_id`, `profile_id`, and `run_root` without overriding `--output-dir`.
- Expected current failure: `BENCH_RUN_DIR`, `run_dir`, `RUN_TAG`, and `_local_output_root()` are identical across invocations.
- Required assertions after #2 implementation:
  - Both plans keep stable `suite_id`, `bench_id`, and profile metadata.
  - Each invocation has a distinct `invocation_id`.
  - `runtime_env.BENCH_RUN_DIR`, `run_dir`, and controller output root include that invocation id or another unique component.
  - `agentic_bench.result.v1` and `summary.json` persist `invocation_id`, `run_dir`, and `bench_run_dir`, not only `run_id`.
  - Any convenience `latest` symlink is never the parser source of truth.

6. `test_image_preflight_cached_command_rows_get_same_parsed_provenance`

- Dedup: #12/#6 guard around the existing command cache at `scripts/agentic_bench_suite.py:1027-1057`.
- Test shape: two rows share the same preflight command that prints batch3 checker JSON and exits 0, with `image_preflight_concurrency > 1`.
- Expected current behavior: only return codes are cached; there is no parsed provenance on either row.
- Required assertions after implementation:
  - `summary.image_preflight_unique_commands == 1` remains true.
  - Both rows get `image_check_parse_status == "parsed"` and identical allowlisted counts.
  - The cached row is not limited to `[image_preflight_cached] ... rc=0` with no image-check evidence.

7. Summary ordering regression coverage

- No new red test is needed for execute summary ordering because `scripts/test_agentic_bench_suite.py:472-500` already covers manifest order and the code sorts at `scripts/agentic_bench_suite.py:1338-1341`.
- Keep the existing test. If image-check parsing adds per-row provenance, add the batch3 promotion test with two rows ordered slow/fast to ensure the new parsed fields do not reintroduce completion-order persistence.

Cross-lane runtime/images check:

- Runtime-images Round 13 says batch3 materialized five additional TB2 transports and worker fallback-load/run-smoke passed; the handoff updates verified fallback counts to TB2 60 and combined TB2+SWE 62.
- Runtime lane still treats direct P0 worker pull as #8/rootless runtime readiness, not as a runner/parser issue.
- Runner/results should preserve the batch3 fallback-load evidence structurally, but should not reinterpret P0 pull failures or transport readiness beyond the checker JSON counts and source pointers.

### Round 14 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Remote handoff/head/status command: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `c7a0eef Materialize TB2 low-risk transport batch 3`.
- Read current runner ledger tail: rc 0.
- Read current runtime-images lane tail: rc 0.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch3_worker_check_20260626.json`: rc 0; printed only schema, counts, image ids/roles/statuses, key names, fallback sha statuses, inspect identity statuses, and stderr-field presence.
- Grep for image-check provenance, invocation, run-root, ordering, and summary/result fields across scripts/reports/ledger: rc 0.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_suite.py`, and `scripts/test_agentic_bench_images.py`: rc 0.
- Listed batch2/batch3 evidence files in `_coordination/20260625_harbor_bench/inventory`: rc 0.
- Bounded synthetic controller probe with batch3 JSON: rc 0. It confirmed summary status pass while omitting `image_check_counts`/`image_checks`, deterministic repeat controller output roots, and `fail:image_preflight:2` mapping to `infra_error`/`adapter_crash` with no `source` or `image_preflight` object.

## Round 14 validation evidence

- `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; concurrent/unowned `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch4_20260626.tsv` was present and left untouched.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.

## Round 15 one-command runner contract after TB2 batch4

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` before code/evidence inspection.
- Active branch/head observed: `feat/image-warmup-policy` / `5a4e0a7 Record TB2 batch4 runtime audit`.
- Wrote only this runner/results/parser ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: after batch4, check whether one-command runner artifacts can consume worker fallback smoke image-check JSON, preserve it in normalized results, and keep invocation-unique run dirs when suite concurrency is 40-50.

No new ISSUE-READY block from this loop.

Dedup judgment: the concrete gaps remain existing issues. Missing image-check promotion and result provenance is #12, with runtime evidence from #6/#11. Required image-preflight failure classification remains #1. Deterministic output roots and `BENCH_RUN_DIR` remain #2. Checker JSON redaction/allowlist remains #10. Worker P0 pull versus fallback readiness remains runtime #8 and is not a runner/results parser bug. Batch4 gives a stronger fixture because the worker fallback-load proof now exists, but it does not add a distinct root cause.

Current batch4 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch4_worker_check_20260626.json`.
- It is a native checker payload: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_lowrisk_batch4_worker_smoke`.
- Counts: `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, `pulled=0`.
- Images: five required `terminal_bench_task_runtime` rows: `tb2_password_recovery`, `tb2_path_tracing_reverse`, `tb2_query_optimize`, `tb2_sanitize_git_repo`, and `tb2_tune_mjcf`.
- Every row has `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and final inspect identity `match`.
- Important redaction nuance: even this happy-path fallback-load proof has nested `inspect_attempts[].stderr` on the first missing-image probe before `docker load`. The current observed content is a Docker missing-image diagnostic, not a secret, but a future normalizer must not copy nested raw stderr wholesale. Promote status, return code, refs, and identity fields by allowlist; either omit nested stderr or replace it with `stderr_redacted=true` plus a safe key path.

Current-code cross-check:

- `scripts/agentic_bench_suite.py:812-823` still builds `run_id` from `suite_id + bench_id + profile_id`, `run_dir` as `<run_root>/<suite_id>/<bench_id>`, and `RUN_TAG` as `suite_id`. There is no invocation id.
- `scripts/agentic_bench_suite.py:970-976` still chooses `<run_root>/<suite_id>/_controller` when `--output-dir` is not provided. Repeated one-command executions of the same suite collide even if `suite_concurrency` is 40-50.
- `scripts/agentic_bench_suite.py:1027-1057` dedupes identical image-preflight commands by returning only the cached return code to waiting rows. The owner log contains checker stdout; cached rows get only `[image_preflight_cached] ... rc=N`. A parser that reads only each row log will lose batch4 proof for cached rows.
- `scripts/agentic_bench_suite.py:1079-1139` records coarse preflight row fields only: status, exit code, fatality, timestamps, policy, required, and log path.
- `scripts/agentic_bench_suite.py:1198-1209` writes `agentic_bench.image_preflight_summary.v1` without parsing/promoting `agentic_bench.image_check.v1` into `image_check_counts`, `image_checks`, safe source pointers, checker digest, or redaction metadata.
- `scripts/agentic_bench_suite.py:1251-1262` still maps every nonzero execution to `benchmark_result.status=infra_error` and `failure_category=adapter_crash`, including `fail:image_preflight:2`.
- `scripts/agentic_bench_suite.py:1281-1300` writes `agentic_bench.result.v1` without `source`, `image_preflight`, `image_preflight_summary_path`, image-check artifact pointers, invocation id, `run_dir`, model profile, worker id, or parser version.
- `scripts/agentic_bench_suite.py:1338-1341` still sorts execute summary rows in manifest order, and `scripts/test_agentic_bench_suite.py:472-500` covers that behavior. No summary-order regression found.
- `scripts/test_agentic_bench_suite.py:548-689` covers image-preflight concurrency cap and command dedupe at suite concurrency 40, but it does not assert parsed image-check provenance for owner or cached rows.
- `scripts/agentic_bench_images.py:600-613` can emit raw `smoke_stderr` on smoke failure, and batch4 proves nested inspect stderr can exist on a passing fallback-load path. This keeps #10 relevant for both failure and success fixtures.
- `scripts/agentic_bench_images.py:628-643` already returns enough structured checker data for the runner to preserve safe provenance if a parser/normalizer is added.

Synthetic controller probe at suite concurrency 50:

- A temp helper printed the existing batch4 worker checker JSON; no Docker, benchmark, or model call was made.
- `_execute_image_preflights()` returned rc 0 with `summary.status=0`, `counts.pass=3`, `image_preflight_concurrency=4`, and `image_preflight_unique_commands=1` for three rows sharing the same preflight command.
- Persisted result order stayed manifest order: `tb2_a`, `tb2_b`, `tb2_c`.
- The first summary row keys were only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`; `image_check_counts in row == False` and `image_checks in row == False`.
- `_local_output_root()` returned the same path for repeated plans with the same suite/run root: `/tmp/.../runs/round15_probe/_controller`.
- A synthetic `fail:image_preflight:2` execution still enriched as `execution_status=fail`, `benchmark_status=infra_error`, and `failure_category=adapter_crash`.
- The normalized result document keys remained `adapter`, `bench`, `bench_id`, `benchmark_result`, `execution`, `run_id`, `schema_version`, and `suite_id`; it had no `source` and no `image_preflight` object.

### Minimal red-test recommendations after batch4

1. `test_image_preflight_summary_promotes_batch4_worker_check_json_under_concurrency_50`

- Fixture input: distill `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch4_worker_check_20260626.json` into a stable unit fixture. Do not read mutable `_coordination/` at test runtime.
- Test shape: three plan rows share one preflight command that prints the fixture JSON and exits 0; set `suite_concurrency=50` and `image_preflight_concurrency=4`.
- Expected current failure: summary rows lack `image_check_counts` and `image_checks`.
- Required assertions after implementation:
  - `summary.status == 0`, `summary.counts.pass == 3`, `summary.image_preflight_concurrency == 4`, and `summary.image_preflight_unique_commands == 1`.
  - Every row, including cached-command rows, has `image_check_parse_status == "parsed"`.
  - Every row has allowlisted `image_check_counts` with `tar_verified == 5`, `loaded == 5`, `present == 5`, `smoke_passed == 5`, `identity_mismatch == 0`, and `errors == 0`.
  - Promoted images preserve `id`, `role`, `required`, `status`, `load_status`, `smoke_status`, fallback `sha256_status`, final identity `match`, and safe fallback pointer metadata.
  - Serialized summary output must not contain nested raw `inspect_attempts[].stderr`, raw Docker stdout/stderr bodies, full command text, env values, or model/adapter transcript text.

2. `test_result_artifact_includes_batch4_image_preflight_provenance_on_pass`

- Fixture input: the batch4 happy-path checker fixture and a synthetic passing adapter execution.
- Expected current failure: `agentic_bench.result.v1` has no `source`, no `image_preflight`, and no image-check artifact pointer.
- Required assertions after implementation:
  - `result.execution.status == "pass"` and existing benchmark parser behavior is unchanged.
  - `result.source.image_preflight_summary_path` points at `controller/image_preflight_summary.json`.
  - `result.source.image_preflight_log_path` points at the owner preflight log or shared parsed artifact, not a cached row log that only contains `rc=0`.
  - `result.source.image_manifest_paths[]` includes the checker manifest path or manifest id from the checker JSON.
  - `result.source.image_check_artifacts[]` includes `role=image_check_stdout_json`, `status=parsed`, `read_policy=allowlist_json`, and a stable `json_pointer` or shared artifact pointer.
  - `result.image_preflight.status == "pass"`, `parse_status == "parsed"`, and counts preserve `loaded=5`, `tar_verified=5`, and `smoke_passed=5`.

3. `test_cached_preflight_rows_keep_shared_parsed_provenance`

- Dedup: #12/#6 guard around `scripts/agentic_bench_suite.py:1027-1057`, not a new issue.
- Test shape: use the same batch4 fixture command for at least two rows, with `image_preflight_concurrency > 1`.
- Expected current failure: there is no parsed provenance on any row; a naive future parser could also parse only the owner row and leave cached rows with bare return-code evidence.
- Required assertions after implementation:
  - `summary.image_preflight_unique_commands == 1` remains true.
  - Owner and cached rows both get parsed counts and source pointers.
  - Cached rows identify the shared parsed checker artifact instead of claiming an independent native JSON was read from their per-row cached log.

4. `test_invocation_unique_controller_and_bench_dirs_at_concurrency_50`

- Dedup: #2, not a new issue.
- Test shape: build or execute two plans with the same `suite_id`, `bench_id`, `profile_id`, and `run_root`, using `suite_concurrency=50`.
- Expected current failure: `_local_output_root()`, `run_dir`, `BENCH_RUN_DIR`, and `RUN_TAG` repeat.
- Required assertions after #2 implementation:
  - Each invocation has a distinct `invocation_id`.
  - Controller output root and `BENCH_RUN_DIR` include the invocation id or another collision-proof component.
  - `summary.json` and `agentic_bench.result.v1` persist `invocation_id`, controller output root, remote `BENCH_RUN_DIR`, `run_id`, `suite_id`, `bench_id`, `model_profile`, and worker/execution host.
  - Any convenience `latest` pointer is not the parser source of truth.

5. `test_required_image_preflight_failure_is_infra_blocked_with_preserved_checker_evidence`

- Dedup: #1/#12/#10.
- Fixture input: synthetic `fail:image_preflight:2` execution plus a parsed image-check failure fixture with one required image and `smoke_status=failed`.
- Expected current failure: result uses `benchmark_result.status=infra_error` and `failure_category=adapter_crash`.
- Required assertions after implementation:
  - `execution.status == "fail"` and `execution.adapter_status == "fail:image_preflight:2"`.
  - `benchmark_result.status == "infra_blocked"`, `metric == "image_preflight"`, `score_claim_valid is False`, and `failure_category == "image_preflight_failed"`.
  - Parsed, redacted image-preflight evidence still appears under `result.image_preflight` and `source.image_check_artifacts[]`.

6. `test_image_check_allowlist_redacts_nested_stderr_on_success_and_smoke_stderr_on_failure`

- Dedup: #10.
- Fixture input: batch4 success fixture for nested `inspect_attempts[].stderr` plus a small synthetic smoke-failure fixture containing a sentinel in `smoke_stderr`.
- Expected current failure: there is no positive parsed/redacted output at all.
- Required assertions after implementation:
  - The success fixture still reports fallback load and final identity match while omitting nested raw inspect stderr.
  - The failure fixture still reports `smoke_status=failed`, `errors=1`, and `smoke_stderr_redacted=true`.
  - Serialized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` do not contain the sentinel, raw `smoke_stderr`, raw nested `stderr`, raw Docker stdout/stderr, full command strings, env values, or model/adapter transcript text.

Cross-lane runtime/images check:

- Runtime-images ledger now records that batch4 worker proof exists and reports `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, and `errors=0`.
- This confirms batch4 is no longer worker-smoke-pending. The runner/results gap is preserving that proof in one-command suite artifacts, not re-running it.
- No contradiction found with runtime lane #6/#8. The result layer should report what the checker observed from fallback-load/run-smoke. It should not mark worker P0 direct pull ready until runtime #8 says that path works.

### Round 15 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first before remote work in the pre-compaction portion of this round.
- Remote handoff/head command on `swe_dev`: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `5a4e0a7`.
- Attempted to read the advertised `superpowers:systematic-debugging` skill path under cache `7fd3161c`: rc 1 because that cache path was absent.
- `find /Users/Zhuanz1/.codex/plugins/cache/openai-curated/superpowers -path '*/systematic-debugging/SKILL.md'`: rc 0; located current cache path `d08f0354`.
- Read current `superpowers:systematic-debugging` instructions from cache `d08f0354`: rc 0.
- Read runner ledger tail: rc 0.
- Read runtime-images lane tail: rc 0.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch4_worker_check_20260626.json`: rc 0; printed schema, counts, row keys, safe row summaries, image ids/statuses, fallback sha statuses, identity sequences, and nested-stderr presence. No secret value was printed.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_suite.py`, and `scripts/test_agentic_bench_images.py`: rc 0.
- Grep for image-check/result provenance/invocation fields across scripts and ledgers: rc 0.
- `git status --short --untracked-files=all` before append: rc 0; observed untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch5_20260626.tsv`, left untouched.
- Bounded synthetic controller probe with batch4 JSON, `suite_concurrency=50`, and `image_preflight_concurrency=4`: rc 0; confirmed omitted parsed checker fields, deterministic output root, and generic adapter-crash classification for `fail:image_preflight:2`.
- First remote append attempt using nested heredocs: rc 127; quoting broke before any successful write, and this corrected stdin append was used instead.

## Round 15 validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.
- `git status --short --untracked-files=all`: rc 0. This lane modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; unowned `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` was also modified in the shared worktree, and untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch5_20260626.tsv` plus `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch5_worker_check_20260626.json` were present by final status. They were left untouched.
- Final `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; ledger diff was 144 inserted lines.

## Round 16 batch5 image-check provenance under suite concurrency 50

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and this runner/results ledger before the Round16 checks.
- Active branch/head observed: `feat/image-warmup-policy` / `7f48601 Record TB2 batch5 handoff`.
- Wrote only this runner/results/provenance ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: whether one-command runner artifacts preserve batch5 `agentic_bench.image_check.v1` evidence under `suite_concurrency=40-50`, especially cached preflight rows, `image_preflight_summary.json`, `agentic_bench.result.v1`, output-root/invocation uniqueness, and redaction allowlists.

No new ISSUE-READY block from this loop.

Dedup judgment: this is COMMENT-READY / fixture-ready evidence for existing issues. Batch5 does not change the root cause. Missing image-check promotion and result provenance remain #12; required preflight failure classification remains #1; deterministic output roots and `BENCH_RUN_DIR` remain #2; raw checker stderr fields require #10 allowlist/redaction. Runtime lane #6/#8 context remains compatible: batch5 proves fallback-load/run-smoke readiness, not direct P0 pull readiness.

Current batch5 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch5_worker_check_20260626.json`.
- Native checker schema: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_lowrisk_batch5_worker_smoke`.
- Counts: `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, `pulled=0`.
- Images: five required `terminal_bench_task_runtime` rows: `tb2_overfull_hbox`, `tb2_polyglot_c_py`, `tb2_polyglot_rust_c`, `tb2_winning_avg_corewars`, and `tb2_write_compressor`.
- Every image row has `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and final inspect identity `match`.
- Every image row also has a nested `inspect_attempts[0].stderr` from the pre-load missing-image probe. I recorded only key paths and value lengths, not values. This makes batch5 a better success-path #10 fixture than batch2/batch3, because success still contains raw nested stderr that a normalizer must not copy wholesale.
- No top-level secret-like key names were observed in the batch5 checker JSON. That is not sufficient for safety; parsers still need allowlist extraction because `pull_stderr`, `load_stderr`, `smoke_stderr`, and nested `inspect_attempts[].stderr` can exist by code path.

Current-code cross-check at head `7f48601`:

- `git diff --stat 5a4e0a7..7f48601 -- scripts ...` showed no script changes; batch5 changed handoff, inventory JSON/TSV, the TB2 image manifest, and coordination ledgers.
- `scripts/agentic_bench_suite.py:812-823` still builds `run_id` from `suite_id + bench_id + profile_id`, `run_dir` as `<run_root>/<suite_id>/<bench_id>`, and `RUN_TAG` as `suite_id`; there is no invocation id.
- `scripts/agentic_bench_suite.py:970-976` still chooses `<run_root>/<suite_id>/_controller` when `--output-dir` is omitted. Repeated one-command runs of the same suite can collide, independent of `suite_concurrency=40-50`.
- `scripts/agentic_bench_suite.py:1027-1057` still caches identical preflight commands by storing only a future return code. Owner rows receive checker stdout; cached rows receive only `[image_preflight_cached] ... rc=N`.
- `scripts/agentic_bench_suite.py:1079-1139` still records only coarse preflight fields: `bench_id`, `required`, `policy`, `status`, `exit_code`, `fatal`, timestamps, and `log_path`.
- `scripts/agentic_bench_suite.py:1198-1209` still writes `agentic_bench.image_preflight_summary.v1` without `image_check_counts`, `image_checks`, checker source pointers, checker digest, redaction metadata, or a shared parsed artifact pointer.
- `scripts/agentic_bench_suite.py:1251-1262` still maps all nonzero execution to `benchmark_result.status=infra_error` and `failure_category=adapter_crash`, including `fail:image_preflight:2`.
- `scripts/agentic_bench_suite.py:1281-1300` still writes `agentic_bench.result.v1` with no `source`, no `image_preflight`, no `image_preflight_summary_path`, no image-check artifact pointer, no invocation id, no `run_dir`, no model profile, no worker id, and no parser version.
- Existing suite tests still cover RepoZero benchmark-vs-execution split, manifest-order summary sorting, image-preflight-only execution, concurrency cap, command dedupe, optional preflight handling, and fallback-file lint. They do not assert checker JSON promotion, cached-row shared provenance, normalized result image-preflight provenance, invocation-unique directories, image-preflight-failure classification, or positive redaction while preserving parsed failure/success status.
- `scripts/agentic_bench_images.py:574-598` can store raw `pull_stderr` or `load_stderr`, `scripts/agentic_bench_images.py:600-613` can store raw `smoke_stderr`, and batch5 proves `_docker_inspect()` attempts can contribute nested raw `stderr`. #10 should cover all of these, not only `smoke_stderr`.

Synthetic controller probe at `suite_concurrency=50`:

- A temp helper printed the existing batch5 worker checker JSON; no Docker, benchmark, or model call was made.
- `_execute_image_preflights()` returned rc 0 with `summary.status=0`, `counts.pass=3`, `image_preflight_concurrency=4`, and `image_preflight_unique_commands=1` for three rows sharing the same preflight command.
- Persisted result order stayed manifest order: `tb2_owner_probe`, `tb2_cached_probe_a`, `tb2_cached_probe_b`.
- All three summary rows had only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`.
- `row_has_image_check_counts == [False, False, False]` and `row_has_image_checks == [False, False, False]`.
- Owner log marker: `contains_schema=true`, `contains_cached_marker=false`.
- Cached row markers: `contains_schema=false`, `contains_cached_marker=true` for both cached rows.
- `_local_output_root()` returned the same controller output root for repeated plan construction: `/tmp/.../runs/round16_probe/_controller`.
- Synthetic `fail:image_preflight:2` still enriched as `execution_status=fail`, `benchmark_status=infra_error`, and `failure_category=adapter_crash`.
- The normalized result document keys remained `adapter`, `bench`, `bench_id`, `benchmark_result`, `execution`, `run_id`, `schema_version`, and `suite_id`; it had no `source` and no `image_preflight` object.

### COMMENT-READY for #12/#10/#2/#1

Batch5 fixture recommendation:

- Use a distilled `tb2_lowrisk_batch5_worker_check` fixture for success-path image-preflight provenance because it exercises `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, fallback sha match, final identity match, and nested raw inspect stderr on a passing path.
- Add a three-row suite fixture where all rows share the same preflight command and `suite_concurrency=50`, `image_preflight_concurrency=4`. Expected after implementation: owner and cached rows all expose parsed provenance through a shared parsed artifact pointer or summary JSON pointer, even though only the owner row log contains the checker JSON.
- Required `image_preflight_summary.json` assertions: `image_check_parse_status=parsed`, counts preserve `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`; promoted image rows preserve safe fields only: `id`, `role`, `required`, `status`, `load_status`, `smoke_status`, fallback `sha256_status`, safe fallback basename or pointer, final identity status, and safe inspect return codes/refs.
- Required `agentic_bench.result.v1` assertions: include `source.image_preflight_summary_path`, `source.image_preflight_log_path` or shared parsed artifact path, `source.image_manifest_paths[]`, `source.image_check_artifacts[]` with `read_policy=allowlist_json`, and an `image_preflight` object with status/counts/images. Do not make cached rows point only at their cached log as if it contained native JSON.
- Required #2 assertions: repeated one-command invocations with the same `suite_id`, `bench_id`, `profile_id`, and `run_root` must produce distinct `invocation_id`, controller root, remote `BENCH_RUN_DIR`, and result/summary provenance fields.
- Required #1 assertion: a synthetic `fail:image_preflight:2` with parsed checker failure evidence must classify as `benchmark_result.status=infra_blocked`, `metric=image_preflight`, `failure_category=image_preflight_failed`, and `score_claim_valid=false`, while preserving process status in `execution`.
- Required #10 assertions: serialized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` must not contain raw `inspect_attempts[].stderr`, `pull_stderr`, `load_stderr`, `smoke_stderr`, raw Docker stdout/stderr bodies, full command strings, env values, model transcripts, or adapter transcripts. Positive assertions must still prove the parser retained `load_status=loaded`, `smoke_status=passed`, and final identity match for batch5.

Cross-lane runtime/images check:

- Runtime-images Round15 records that batch5 materialized five generic TB2 rows and that worker fallback-load/run-smoke JSON reports `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, and `pulled=0`.
- No contradiction found. Runtime lane correctly treats batch5 as fallback-ready and still not P0-pull-ready under #8. Runner/results should preserve that observed checker evidence structurally without reinterpreting direct registry readiness.
- The next runtime lane is service-row isolation; this runner/results lane should keep focusing on how those future worker-check JSON payloads become normalized result provenance and how service smoke stderr/stdout is redacted.

### Round 16 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Skill discovery for `systematic-debugging` and `verification-before-completion`: rc 0; both resolved under cache `d08f0354`.
- Memory quick search for relevant workflow/coordination terms in `/Users/Zhuanz1/.codex/memories/MEMORY.md`: rc 0; used only to retain the strict remote/coordination workflow pattern.
- Remote handoff/head/ledger command: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `7f48601`, and read the current runner ledger tail plus round index.
- Read `superpowers:systematic-debugging` and `superpowers:verification-before-completion` instructions: rc 0.
- `git status --short --untracked-files=all && git log --oneline -8`: rc 0; status output was empty before this ledger append, and recent log started at `7f48601` then `7ba6b3b`.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch5_worker_check_20260626.json`: rc 0; printed schema, counts, image ids/statuses, fallback sha statuses, identity sequences, nested-stderr key presence, and value lengths only. No secret value was printed.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_suite.py`, and `scripts/test_agentic_bench_images.py`: rc 0.
- Grep for image-check/result provenance/invocation fields across scripts and this ledger: rc 0.
- Batch5 stderr-key scan with bounded Python: rc 0; no top-level secret-like keys, and five nested `inspect_attempts[].stderr` key paths were detected by key and length only.
- Bounded synthetic controller probe with batch5 JSON, `suite_concurrency=50`, and `image_preflight_concurrency=4`: rc 0; confirmed owner log contains checker JSON, cached row logs do not, summary rows omit parsed checker fields, output root is deterministic, and `fail:image_preflight:2` remains generic adapter-crash classification.
- `git diff --stat 5a4e0a7..7f48601 -- scripts manifests ...`: rc 0; no script changes, batch5 changes are handoff/inventory/manifest/ledger artifacts.
- `git diff --name-only 5a4e0a7..7f48601`: rc 0; confirmed batch5 touched handoff, inventory JSON/TSV, both lane ledgers, and the TB2 image manifest.
- Runtime lane grep for Round15/batch5/#12: rc 0; confirmed no contradiction and fallback-ready/not-P0-ready runtime interpretation.

## Round 16 validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Token-pattern scan over this ledger using a bounded Python regex scanner: rc 0, `secret_pattern_scan=no_matches`.
- `git status --short --untracked-files=all`: rc 0. This lane modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; concurrent/unowned `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` was modified, and untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_service_batch6_20260626.tsv`, `_coordination/20260625_harbor_bench/inventory/tb2_service_batch6_worker_check_20260626.json`, plus `scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc` were present by final status. They were left untouched.
- Final `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; ledger diff was 93 inserted lines.

## Round 17 service and vulnerable-secret image-check provenance/redaction

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and this runner/results ledger before the Round17 checks.
- Active branch/head observed: `feat/image-warmup-policy` / `5eb8822 Record TB2 batch6 handoff`.
- Wrote only this runner/results/provenance ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: from the one-command runner angle, determine how service batch6 and vulnerable-secret image-check evidence can enter normalized result/provenance/redaction, especially raw stderr/logs, secret-bearing task artifacts, cached preflight rows, `image_preflight_summary.json`, and `agentic_bench.result.v1`.

No new ISSUE-READY block from this loop.

Dedup judgment: Round17 is COMMENT-READY / fixture-ready evidence for existing issues. Missing image-check promotion and normalized source provenance remain #12; required preflight failure status remains #1; invocation-unique output roots and remote `BENCH_RUN_DIR` remain #2; raw checker stderr and secret-bearing Terminal-Bench artifacts remain #10. The service and vulnerable-secret artifacts add concrete fixtures, not a distinct root cause.

Concurrent/unowned state noted:

- Before this ledger append, `git status --short --untracked-files=all` reported an unowned modification to `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` and untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_secret_batch7_20260626.tsv` plus `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`.
- I read those batch7 artifacts as existing evidence because they were present in the active shared worktree, but did not modify them.

Current service batch6 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_service_batch6_worker_check_20260626.json`.
- Native checker schema: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_service_batch6_worker_smoke`.
- Mode: `allow_pull=false`, `load_fallback=true`, `run_smoke=true`, `skip_docker=false`, `fail_on_optional_missing=false`.
- Counts: `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, and `pulled=0`.
- Images: two required `terminal_bench_task_runtime` rows, `tb2_nginx_request_logging` and `tb2_pypi_server`.
- Both rows have `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and one fallback path present.
- Both rows also have nested `inspect_attempts[0].stderr` on the first missing-image probe before fallback load. I recorded only the key path and value length, not the raw value.
- The checker JSON row does not itself carry the full smoke command/network policy, so normalized provenance needs an image-manifest pointer or a copied allowlist of manifest smoke metadata. This is #12, not a new issue.
- The handoff explicitly says these service rows are image-transport ready only; `--network none` smoke is not a claim that real Terminal-Bench service behavior has been executed. Normalized results should preserve that distinction instead of turning image smoke pass into benchmark pass.

Current vulnerable-secret evidence shape:

- Evidence file present in the worktree but untracked at this head: `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`.
- Native checker schema: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_secret_batch7_worker_smoke`.
- Counts: `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, and `pulled=0`.
- Image row: required `tb2_vulnerable_secret`, role `terminal_bench_task_runtime`, `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`.
- The row has nested `inspect_attempts[0].stderr` by key path and length only. No raw stderr value was printed.
- The related unowned manifest diff changes `tb2_vulnerable_secret` from missing shared tar to `p0_digest_plus_fallback_tar` with a digest ref and verified fallback tar sha. I did not edit or stage it.
- A targeted path inventory of the Terminal-Bench 2.1 `vulnerable-secret` task tree found task source/solution/test files (`task.yaml`, `solution.sh`, `vulnerable.c`, tests, and Docker files). These are secret-bearing task materials and must not be copied into normalized output.
- A targeted path inventory of a prior `vulnerable-secret` run found `commands.txt`, pane dumps, agent/test logs, cast files, `results.json`, verifier CTRF JSON, and reward text. Ten sampled files were classified as raw log/cast-like and one as structured JSON, based on filename/role only. Their content was not opened or printed in that command.
- Parser implication: image-check normalization must not broaden into Terminal-Bench task directories or historical run logs. It should consume only the checker JSON plus explicit source pointers; Terminal-Bench native parser work should separately allowlist `results.json`-like structured artifacts and keep logs/casts/task source as pointer-only, secret-sensitive artifacts.

Current-code cross-check at head `5eb8822`:

- `scripts/agentic_bench_suite.py:24`, `scripts/agentic_bench_suite.py:237-258`, and `scripts/agentic_bench_suite.py:481-499` enforce config/env secret policy and runtime-env redaction, but that redaction does not apply to native checker JSON, raw adapter logs, Terminal-Bench task source, casts, or historical native artifacts.
- `scripts/agentic_bench_suite.py:812-823` still builds deterministic `run_id`, `BENCH_RUN_DIR`, and `RUN_TAG` without invocation uniqueness.
- `scripts/agentic_bench_suite.py:970-976` still maps a suite to `<run_root>/<suite_id>/_controller` when `--output-dir` is omitted.
- `scripts/agentic_bench_suite.py:1027-1057` still de-duplicates identical image-preflight commands by sharing only a return-code future. The log that contains checker stdout is whichever row becomes command owner under concurrency, not necessarily the first manifest row.
- `scripts/agentic_bench_suite.py:1079-1139` records only coarse per-row preflight status fields.
- `scripts/agentic_bench_suite.py:1198-1209` writes `agentic_bench.image_preflight_summary.v1` without parsed `agentic_bench.image_check.v1` counts, image rows, checker artifact digest, image manifest pointer, redaction metadata, or shared parsed artifact pointer.
- `scripts/agentic_bench_suite.py:1251-1262` still maps all nonzero executions to `benchmark_result.status=infra_error` and `failure_category=adapter_crash`, including required image-preflight failures.
- `scripts/agentic_bench_suite.py:1281-1300` still writes `agentic_bench.result.v1` without `source`, `image_preflight`, `image_preflight_summary_path`, image-check artifact pointers, invocation id, `run_dir`, model profile, worker id, or parser version.
- `scripts/agentic_bench_images.py:574-598` can emit raw `pull_stderr` or `load_stderr`; `scripts/agentic_bench_images.py:600-613` can emit raw `smoke_stderr`; service batch6 and vulnerable-secret batch7 prove nested inspect stderr can also exist on successful fallback-load paths.
- Existing suite tests cover RepoZero execution-vs-benchmark split, summary order, image-preflight-only execution, concurrency cap, command dedupe, optional preflight handling, and manifest lint. They do not assert parsed image-check provenance, cached-row shared provenance, normalized result image-preflight provenance, Terminal-Bench artifact source roles, or positive redaction constraints for checker/task artifacts.

Synthetic controller probe at `suite_concurrency=50` using service batch6 JSON:

- A temp helper printed the existing service batch6 worker checker JSON; no Docker, benchmark, or model call was made.
- Corrected probe command returned rc 0; `_execute_image_preflights()` returned `probe_rc=0`, `summary.status=0`, `counts.pass=3`, and `image_preflight_unique_commands=1` for three rows sharing the same checker command.
- All three summary rows had only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`.
- `has_image_check_counts=false` and `has_native_pointer=false` on the summary result row.
- The command-owner log under concurrency was `tb2_service_cached_a.image_preflight.log`, not the row named `tb2_service_owner`. It contained `agentic_bench.image_check.v1` and no cached marker.
- The other two row logs contained `[image_preflight_cached]` and no checker schema. This proves a per-row-log parser can miss native evidence for cached rows unless the suite materializes a shared parsed artifact or source pointer.
- A synthetic `_attach_benchmark_result()` call for `fail:image_preflight:7` still produced `execution_status=fail`, `benchmark_status=infra_error`, and a result document with top-level keys only `adapter`, `bench`, `bench_id`, `benchmark_result`, `execution`, `run_id`, `schema_version`, and `suite_id`.
- That result document had no `source` and no `image_preflight` object.

### COMMENT-READY fixture/test map for #12/#10/#1/#2

1. `test_service_batch6_image_check_promoted_with_cached_rows`

- Fixture input: distilled `tb2_service_batch6_worker_check` JSON with two images, each `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and nested inspect stderr key paths.
- Test shape: three suite rows share one required preflight command that prints the fixture; set `suite_concurrency=50` and `image_preflight_concurrency=4`.
- Required assertions after implementation: `summary.status == 0`, `counts.pass == 3`, `image_preflight_unique_commands == 1`, and every row has `image_check_parse_status == "parsed"` with shared parsed provenance, even cached rows.
- Required safe fields: preserve `id`, `role`, `required`, `status`, `load_status`, `smoke_status`, fallback `sha256_status`, safe fallback pointer or digest, final inspect identity status, and checker counts.
- Negative assertions: serialized summary/result outputs must not include nested raw `inspect_attempts[].stderr`, raw Docker stdout/stderr bodies, full task logs, full task source, env values, model transcripts, or adapter transcripts.

2. `test_vulnerable_secret_image_check_fixture_redacts_and_excludes_task_artifacts`

- Fixture input: distilled `tb2_secret_batch7_worker_check` JSON plus a synthetic sentinel inserted into nested inspect stderr and smoke/load/pull stderr variants.
- Required assertions after implementation: `image_preflight.status == "pass"`, `parse_status == "parsed"`, `counts.loaded == 1`, `counts.present == 1`, `counts.smoke_passed == 1`, `counts.errors == 0`, and image row `id == "tb2_vulnerable_secret"` with role `terminal_bench_task_runtime`.
- Negative assertions: `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` must not contain the sentinel, raw `inspect_attempts[].stderr`, `pull_stderr`, `load_stderr`, `smoke_stderr`, raw Docker stdout/stderr, contents of `task.yaml`, `solution.sh`, `vulnerable.c`, test files, casts, pane dumps, `commands.txt`, or raw agent/test logs.
- Source assertion: task materials and historical logs, if referenced, must appear only as `source.native_artifacts[]` entries with `read_policy=pointer_only`, `secret_sensitive=true`, and `status=not_read` or `excluded_by_policy`.

3. `test_terminal_bench_source_roles_keep_image_check_separate_from_task_results`

- Expected `source.native_artifacts[]` roles:
  - `image_preflight_summary_json`: `status=parsed`, `read_policy=normalized_summary`.
  - `image_check_stdout_json` or `image_check_artifact_json`: `status=parsed`, `read_policy=allowlist_json`, with a content digest or shared artifact pointer.
  - `image_manifest_yaml`: `status=referenced`, `read_policy=allowlist_config`, used to reconstruct smoke policy and manifest id.
  - `terminal_bench_results_json`: `status=candidate_native_result` or `parsed` only when a Terminal-Bench benchmark parser explicitly owns it, `read_policy=allowlist_json`.
  - `terminal_bench_raw_log`, `terminal_bench_cast`, `terminal_bench_pane_dump`, `terminal_bench_commands_txt`, and `terminal_bench_task_source`: `status=not_read` or `excluded_by_policy`, `read_policy=pointer_only`, `secret_sensitive=true`.
- This is #12/#10 fixture work, not a new bug.

4. `test_required_image_preflight_failure_becomes_infra_blocked_not_adapter_crash`

- Fixture input: required image-check failure with a parsed checker JSON and synthetic `fail:image_preflight:N` execution.
- Expected current failure: `_benchmark_result_for_run()` reports `infra_error`/`adapter_crash` before looking for image-check evidence.
- Required assertions after implementation: `execution.status == "fail"`, `execution.adapter_status == "fail:image_preflight:N"`, `benchmark_result.status == "infra_blocked"`, `metric == "image_preflight"`, `failure_category == "image_preflight_failed"`, and `score_claim_valid == false`, while preserving parsed, redacted image-check evidence under `image_preflight` and `source`.
- Dedup: #1 plus #12/#10.

5. `test_invocation_unique_controller_and_bench_dirs_with_cached_preflight_rows`

- Fixture input: two invocations of the same suite id, bench ids, model profile, and run root at `suite_concurrency=50`.
- Required assertions after #2 implementation: distinct `invocation_id`, controller root, remote `BENCH_RUN_DIR`, summary path, and result paths; result docs include `suite_id`, `run_id`, `bench_id`, `model_profile`, worker/execution host, invocation id, controller output root, and native artifact pointers.
- Cached preflight rows should point to the shared parsed checker artifact for their invocation, not to stale output from a previous invocation.

Cross-lane runtime/images check:

- Runtime-images Round16 agrees that service batch6 proves fallback-load/run-smoke readiness for `nginx-request-logging` and `pypi-server`, not direct P0 pull readiness and not actual service benchmark execution.
- The vulnerable-secret batch7 artifacts present in this worktree show fallback-load/run-smoke readiness for `tb2_vulnerable_secret`; because they are unowned/untracked relative to `5eb8822`, this runner lane treats them as existing evidence for redaction fixtures, not as a branch-state claim.
- No contradiction found with runtime lane #6/#8. Runner/results should preserve what the checker observed, identify fallback-vs-pull provenance, and avoid interpreting image smoke as benchmark task success.

### Round 17 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Read `superpowers:systematic-debugging` and `superpowers:verification-before-completion` instruction files from cache `d08f0354`: rc 0.
- Memory quick search for relevant workflow/coordination terms in `/Users/Zhuanz1/.codex/memories/MEMORY.md`: rc 0; used only to retain strict remote/coordination workflow pattern.
- Remote handoff/head/ledger command on `swe_dev`: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `5eb8822`, and read this runner ledger tail plus round index.
- `git status --short --untracked-files=all && git log --oneline -10 && git diff --stat 7f48601..5eb8822 ...`: rc 0; status was initially clean, and the batch6 diff touched handoff, service inventory, and manifest artifacts.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_service_batch6_worker_check_20260626.json`: rc 0; printed schema, counts, row ids/statuses, fallback sha statuses, and raw-field key paths/lengths only.
- Grep for `vulnerable-secret`/secret-related strings across manifests/scripts/coordination artifacts: rc 0; printed only filenames, config keys, and issue/handoff text, not secret values.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_suite.py`, `HANDOFF.md`, and manifest line ranges: rc 0.
- Runtime-images ledger tail read: rc 0; used to cross-check service batch6 readiness and vulnerable-secret runtime-lane handoff.
- Broad vulnerable-secret path search session: rc 0; listed task/prior artifact paths only.
- Bounded Python scan over candidate vulnerable-secret task directories: rc 0; printed file names, sizes, and secretish file counts only, not contents.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json` and service batch6 JSON: rc 0; printed schema, counts, row ids/statuses, fallback sha statuses, and raw-field key paths/lengths only.
- `git status --short --untracked-files=all && git rev-parse --short HEAD && git ls-files ...batch7...`: rc 0; observed unowned manifest modification and untracked batch7 files, with head still `5eb8822`.
- Targeted prior-run/task artifact inventory for `vulnerable-secret`: rc 0; printed filenames, roles, and sizes only. It found 11 prior-run files, including raw log/cast-like artifacts and one `results.json`, and 10 task-tree files, including task source/solution/test materials.
- First synthetic service probe command returned shell rc 0 but internal `probe_rc=1` due a temporary helper quoting error (`encoding=utf-8`). This was classified as invalid probe evidence and superseded.
- Corrected synthetic service probe using batch6 JSON at `suite_concurrency=50`: rc 0; confirmed `probe_rc=0`, `summary.status=0`, `counts.pass=3`, `image_preflight_unique_commands=1`, no parsed checker fields/pointers in summary rows, nondeterministic owner log under command cache, and no `source`/`image_preflight` in the normalized result document.

## Round 17 validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Bounded secret-pattern scan over this ledger: rc 0, `secret_pattern_scan=no_matches`.
- `git status --short --untracked-files=all`: rc 0. This lane modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; unowned `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` and `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` were also modified in the shared worktree, and untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_secret_batch7_20260626.tsv` plus `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json` were present. They were left untouched.
- `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; Round17 ledger diff was 132 inserted lines before this validation block.

## Round 18 batch7 secret plus future batch8 image-check provenance/redaction

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and this runner/results ledger before Round18 checks.
- Active branch/head observed: `feat/image-warmup-policy` / `ce4f268 Record TB2 batch7 handoff`.
- Wrote only this runner/results/provenance ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: from the one-command runner angle, audit how `agentic_bench.image_check.v1` JSON enters normalized result/provenance/redaction for batch7 secret evidence, future batch8 medium generic evidence, cached preflight rows, and raw stderr/log allowlists.

### ISSUE-READY: controller image-preflight logs persist raw checker stdout before parser redaction

severity: High for secret-sensitive tasks; medium for generic image checks.

dedup: Related to #10, but not a duplicate unless #10 is explicitly broadened beyond parser source allowlists and normalized result serialization. Existing #10 covers secret-bearing adapter sidecars and future parser allowlists. This finding is earlier in the data flow: the suite writes raw checker stdout into durable controller preflight logs before any parser or sanitizer can run. Related to #12 because the fix should materialize a safe parsed image-check artifact pointer. Not #1 or #2.

location:

- `scripts/agentic_bench_suite.py:1047-1054`: the command-cache owner runs the image preflight with `stdout=handle` and `stderr=subprocess.STDOUT`, so whatever the checker prints is persisted in `logs/<bench>.image_preflight.log`.
- `scripts/agentic_bench_suite.py:1056-1059`: cached waiters only log `[image_preflight_cached] ... rc=N`, making the owner log the sole raw checker-output sink under concurrency.
- `scripts/agentic_bench_suite.py:1109-1117`: `_run_image_preflight_one()` passes the per-bench log handle into `_cached_preflight_command_returncode()`.
- `scripts/agentic_bench_images.py:574-598`: native checker rows can include nested `inspect_attempts[].stderr`, `pull_stderr`, and `load_stderr`.
- `scripts/agentic_bench_images.py:600-613`: native checker rows can include raw `smoke_stderr` on smoke failure.
- `scripts/agentic_bench_images.py:628-643`: the checker returns the raw `agentic_bench.image_check.v1` payload containing those fields.

static_repro:

- Use a temp copy of committed `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`.
- Insert an unprinted synthetic sensitive sentinel into `images[0].inspect_attempts[0].stderr` and `images[0].smoke_stderr`.
- Run `_execute_image_preflights()` with three rows sharing one required preflight command, `suite_concurrency=50`, and `image_preflight_concurrency=4`; the helper prints the mutated checker JSON and exits 0. No Docker, benchmark, or model call is involved.
- Observed: `probe_rc=0`, `summary.status=0`, `counts.pass=3`, `image_preflight_unique_commands=1`, `summary_has_sentinel=False`, `result_has_sentinel=False`, but `any_log_has_sentinel=True`.
- The log with the raw checker JSON was nondeterministically `tb2_secret_cached_a.image_preflight.log`; the other two row logs had only cached markers. This shows both the log leak and the cached-row provenance ambiguity.

impact:

- A one-command runner output can contain raw checker stderr in `controller/logs/*.image_preflight.log` even if future normalized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` serializers are correctly redacted.
- For `vulnerable-secret`, runtime lane explicitly treats task/log content as secret/log-sensitive. The current batch7 JSON has only Docker missing-image stderr, but the code path would also persist future `pull_stderr`, `load_stderr`, `smoke_stderr`, or nested stderr bodies to logs.
- Cached preflight rows make this harder to audit: the row that owns the shared command is scheduler-dependent, so a parser or reviewer cannot infer which row log is the canonical native checker source from manifest order alone.

fix:

- Do not stream raw image-check JSON stdout/stderr into generic controller logs. Capture checker stdout/stderr into a bounded temp artifact per unique preflight command, parse `agentic_bench.image_check.v1`, and write an allowlisted/redacted `image_check_artifact.json` or embed the safe subset in `image_preflight_summary.json`.
- Log only a short sanitized status line, the safe parsed artifact pointer, parse status, counts, and redaction counts. If raw capture must be retained for debugging, store it outside default one-command artifacts or mark it `secret_sensitive=true`, `read_policy=restricted_raw`, and exclude it from normal collection.
- Add command-cache metadata so owner and cached rows point to the same parsed artifact rather than relying on whichever row log happened to capture stdout.
- Add regression tests that insert a sentinel into nested inspect stderr and smoke stderr, assert no preflight log/summary/result contains it, and assert parsed status/counts still survive.

evidence:

- Synthetic probe stdout showed `any_log_has_sentinel True`, `summary_has_sentinel False`, `result_has_sentinel False`, `image_preflight_unique_commands 1`, and one owner log with `has_schema=true`, `has_sentinel=true`, `has_cached_marker=false`.
- Current batch7 checker JSON is tracked at head `ce4f268`, has `schema_version=agentic_bench.image_check.v1`, row `tb2_vulnerable_secret`, and a real nested `inspect_attempts[0].stderr` key path by presence/length only.
- Existing tests at `scripts/test_agentic_bench_suite.py:548-689` cover concurrency cap and command dedupe, but do not assert raw preflight-log redaction or shared parsed artifact pointers.

### Batch7 tracked evidence and parser fixture contract

Current batch7 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`, tracked at head `ce4f268`.
- Native checker schema: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_secret_batch7_worker_smoke`.
- Mode: `allow_pull=false`, `load_fallback=true`, `run_smoke=true`, `skip_docker=false`, `fail_on_optional_missing=false`.
- Counts: `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, and `pulled=0`.
- Image row: required `tb2_vulnerable_secret`, role `terminal_bench_task_runtime`, `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, one fallback path present.
- Raw-field presence: no top-level raw stdout/stderr keys, but nested `inspect_attempts[0].stderr` exists. I recorded only key path and length, not value.
- Sensitive-key scan over JSON keys found no `secret`, `token`, `authorization`, `password`, or `api_key` key paths. That is not enough for safety; raw values still require an allowlist because stderr bodies can contain arbitrary text.

Fixture-ready tests:

1. `test_batch7_secret_image_check_promotes_safe_fields_and_excludes_raw_logs`

- Fixture input: distilled batch7 checker JSON.
- Expected normalized fields: `image_preflight.status="pass"`, `parse_status="parsed"`, counts above, image row id/role/required/status/load/smoke/fallback sha status, and safe source pointer to the image manifest/check artifact.
- Negative assertions: no raw nested stderr, `pull_stderr`, `load_stderr`, `smoke_stderr`, task file contents, prior Terminal-Bench run logs/casts/panes, env values, adapter transcripts, or model transcripts in serialized `image_preflight_summary.json`, `summary.json`, `agentic_bench.result.v1`, or default collected preflight logs.
- Source policy assertions: Terminal-Bench task source and historical raw logs, if referenced, are `source.native_artifacts[]` pointer-only with `secret_sensitive=true` and `status=not_read` or `excluded_by_policy`.

2. `test_batch7_secret_cached_preflight_rows_share_parsed_artifact`

- Fixture input: same batch7 checker JSON printed by one shared preflight command across at least three rows with `suite_concurrency=50`.
- Expected after implementation: `image_preflight_unique_commands==1`, all rows have parsed counts, and all rows point to the same parsed checker artifact or JSON pointer.
- Negative assertion: no row is considered less proven merely because its own log contains only `[image_preflight_cached]`.

3. `test_required_secret_preflight_failure_is_infra_blocked_not_adapter_crash`

- Fixture input: batch7-like checker JSON with a synthetic required image failure and an execution result `fail:image_preflight:N`.
- Expected after implementation: `execution.status="fail"`, `benchmark_result.status="infra_blocked"`, `metric="image_preflight"`, `failure_category="image_preflight_failed"`, `score_claim_valid=false`, and parsed redacted image-check evidence preserved.
- Dedup: #1/#12/#10.

### Future batch8 medium generic/data contract

No batch8 inventory JSON exists yet in `_coordination/20260625_harbor_bench/inventory/` at this head. Runtime lane identifies the remaining medium/generic candidates separately from secret, service, QEMU, torch/pytorch, and largest-data rows. Relevant currently untransported manifest rows include:

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:779`: `tb2_path_tracing`, currently `image_transport=swe_dev_cache_identity`, `fallback_transport=none`, `fallback_status=missing_shared_tar`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:848`: `tb2_prove_plus_comm`, currently `image_transport=swe_dev_cache_identity`, `fallback_transport=none`, `fallback_status=missing_shared_tar`.
- Runtime lane also lists medium/data rows such as `mteb-retrieve`, `multi-source-data-merger`, `portfolio-optimization`, `reshard-c4-data`, `sam-cell-seg`, `train-fasttext`, and `video-processing`, while keeping QEMU and torch/pytorch separate.

Fixture-ready future batch8 tests:

1. `test_batch8_medium_generic_image_check_promotes_multirow_counts`

- Synthetic fixture rows: at minimum `tb2_path_tracing` and `tb2_prove_plus_comm`, both role `terminal_bench_task_runtime`, required true, fallback sha match, `load_status=loaded`, `status=present`, `smoke_status=passed`.
- Expected counts: `tar_verified == row_count`, `loaded == row_count`, `present == row_count`, `smoke_passed == row_count`, `identity_mismatch == 0`, `errors == 0`, `pulled == 0` when worker evidence uses fallback load.
- Required provenance: preserve fallback-vs-pull mode, image ids/roles/statuses, safe fallback pointer or basename, manifest pointer, and checker artifact digest/pointer.
- Negative assertions: no raw Docker stdout/stderr, full command text, env values, task source, model transcript, or adapter transcript in default normalized artifacts/logs.

2. `test_batch8_medium_generic_does_not_inherit_secret_task_policy_but_keeps_raw_stderr_allowlist`

- Purpose: medium generic rows are not `vulnerable-secret`, but they can still produce raw `inspect_attempts[].stderr`, `pull_stderr`, `load_stderr`, or `smoke_stderr` from Docker/runtime failures.
- Expected source policy: task files are not automatically marked secret-sensitive solely by task id, but raw checker stderr remains `read_policy=redacted_field` or excluded by allowlist.
- If any medium task has benchmark logs/casts in future artifacts, parser must still use pointer-only source records until a Terminal-Bench native result parser owns a structured result file.

3. `test_batch8_cached_rows_do_not_depend_on_owner_log_order`

- Same cached command shape as batch7, but fixture has multiple medium images.
- Expected after implementation: owner and cached rows all point to the shared parsed checker artifact for the current invocation, and the log owner name is not part of correctness.
- Dedup: #12/#2 plus the new log-redaction issue above.

Cross-lane runtime/images check:

- Runtime-images Round17 agrees that `vulnerable-secret` is fallback-ready and should remain isolated from task/log inspection; it explicitly says checker stderr and task/log content must not be copied by result/provenance layers.
- Runtime lane's next suggested split is to choose from the remaining 16 rows while keeping QEMU, torch/pytorch, largest data, and medium generic/data rows separated. This matches the future batch8 contract above.
- No contradiction found. Runner/results should preserve structured image-readiness evidence, not reinterpret fallback smoke as Terminal-Bench task success or worker P0-pull readiness.

### Round 18 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Skill discovery for `systematic-debugging`, `verification-before-completion`, and `using-superpowers`: rc 0.
- Read `superpowers:systematic-debugging`, `superpowers:verification-before-completion`, and `superpowers:using-superpowers` instruction files from cache `d08f0354`: rc 0.
- Memory quick search for relevant workflow/coordination terms in `/Users/Zhuanz1/.codex/memories/MEMORY.md`: rc 0; used only to retain strict remote/coordination workflow pattern.
- Remote handoff/head/ledger command on `swe_dev`: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `ce4f268`, and read this runner ledger tail plus round index.
- `git status --short --untracked-files=all && git log --oneline -12 && git diff --stat 5eb8822..ce4f268 ...`: rc 0; status output was empty before this ledger append, and batch7 diff touched handoff, batch7 TSV/JSON, and the TB2 image manifest. No script changes in that range.
- Inventory file listing for batch7/batch8/medium/path/prove artifacts: rc 0; only batch7 TSV and worker-check JSON were present.
- Handoff/runtime-lane grep for batch7/batch8/medium/path/prove/vulnerable-secret: rc 0; used to cross-check remaining-row and next-batch context.
- Bounded Python inspection of batch7 secret and batch6 service worker-check JSON: rc 0; printed schema, counts, row ids/statuses, fallback sha statuses, raw-field key paths/lengths, and sensitive-key path presence only. No raw stderr or secret value was printed.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, and `scripts/test_agentic_bench_suite.py`: rc 0.
- Manifest grep/line reads for `tb2_vulnerable_secret`, `tb2_path_tracing`, `tb2_prove_plus_comm`, and related rows: rc 0.
- An ad hoc manifest parse for missing transport candidates returned rc 0 but used a broader criterion than the registry lint gate and overcounted rows that have fallback sha but no digest ref. It was not used as authoritative evidence; handoff/runtime verified lint remains the source for the remaining 16 rows.
- Corrected manifest line read for `tb2_prove_plus_comm`, `tb2_rstan_to_pystan`, `tb2_sam_cell_seg`, and `tb2_vulnerable_secret`: rc 0; used to avoid relying on a mixed unnumbered `sed` snippet.
- Synthetic secret-sentinel controller probe using a temp mutated batch7 checker JSON at `suite_concurrency=50`: rc 0; confirmed raw sentinel presence in one controller preflight log and absence from summary/result. The sentinel value was not printed.
- Cross-ledger grep for #10/raw checker/preflight log/stderr: rc 0; confirmed prior rounds covered normalized parser redaction but not this exact controller log emission repro.
- Runtime-images ledger tail read: rc 0; no contradiction found.

## Round 18 validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Bounded secret-pattern scan over this ledger: rc 0, `secret_pattern_scan=no_matches`.
- `git status --short --untracked-files=all`: rc 0. This lane modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; unowned `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` was also modified in the shared worktree and left untouched.
- `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; Round18 ledger diff was 139 inserted lines before this validation block.

### Round 18 issue filing

- Filed GitHub issue #13 for the controller image-preflight raw-log sink: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13
- Dedup retained: related to #10/#12, but distinct because the leak occurs before parser/result redaction.

## Round 19 batch8 image-check provenance and #13 follow-up

Scope held:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only over `ssh swe_dev` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and this runner/results ledger before Round19 checks.
- Active branch/head observed: `feat/image-warmup-policy` / `6ade6f2 Record TB2 batch8 issue comments`.
- Wrote only this runner/results/provenance ledger. No production code, manifests, tests, Docker, benchmark execution, model requests, commits, or pushes.
- Focus: #13 raw image-preflight checker output before parser redaction, batch8 worker JSON provenance, and safe one-command runner artifacts that preserve image-check counts without copying raw stderr/log content.

No new ISSUE-READY block from this loop.

Dedup judgment: batch8 is COMMENT-READY / fixture-ready evidence for #12 and #13, with #10 constraints. #13 already tracks the raw controller `.image_preflight.log` sink, and the Round19 synthetic batch8 replay reproduces the same root cause with a multirow checker payload. #12 covers missing structured image-check counts/source pointers in `image_preflight_summary.json` and `agentic_bench.result.v1`. #10 covers downstream parser/source allowlists and redaction. No distinct #1/#2 root cause was found in this loop.

Current batch8 evidence shape:

- Evidence file: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch8_worker_check_20260626.json`, tracked at head `6ade6f2`.
- Native checker schema: `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_medium_batch8_worker_smoke`.
- Mode: `allow_pull=false`, `load_fallback=true`, `run_smoke=true`, `skip_docker=false`, `fail_on_optional_missing=false`.
- Counts: `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, `missing=0`, and `pulled=0`.
- Images: two required `terminal_bench_task_runtime` rows, `tb2_path_tracing` and `tb2_prove_plus_comm`.
- Both rows have `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and one fallback path present.
- Both rows have nested `inspect_attempts[0].stderr` by key path and length only. I did not print raw stderr values.
- Sensitive-key path scan over the JSON found no `secret`, `token`, `authorization`, `password`, or `api_key` key paths. That does not remove the need for #10/#13 handling because stderr bodies can contain arbitrary text.
- Manifest rows now show P0 digest plus verified fallback tar transport: `tb2_path_tracing` at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:779-790` and `tb2_prove_plus_comm` at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:851-862`.

Current-code cross-check:

- No script changes were introduced from `ce4f268` to `6ade6f2`; batch8 changed handoff, batch8 TSV/JSON, and the TB2 image manifest.
- `scripts/agentic_bench_suite.py:1047-1054` still streams the command-cache owner image-preflight stdout/stderr directly to `logs/<bench>.image_preflight.log`.
- `scripts/agentic_bench_suite.py:1056-1059` still writes only a cached return-code marker for non-owner rows.
- `scripts/agentic_bench_suite.py:1198-1209` still writes `agentic_bench.image_preflight_summary.v1` with coarse row status fields only; it does not persist `image_check_counts`, image rows, redaction metadata, checker artifact digests, or shared parsed artifact pointers.
- `scripts/agentic_bench_suite.py:1281-1300` still writes `agentic_bench.result.v1` without `source`, `image_preflight`, `image_check_artifacts`, or image-preflight summary pointers.
- `scripts/agentic_bench_images.py:574-598` can produce raw `inspect_attempts[].stderr`, `pull_stderr`, and `load_stderr`; `scripts/agentic_bench_images.py:600-613` can produce raw `smoke_stderr`; `scripts/agentic_bench_images.py:628-643` returns those fields in native checker JSON.
- `scripts/test_agentic_bench_suite.py:548-689` covers image-preflight concurrency cap and command de-duplication, but not raw preflight-log redaction, safe parsed checker artifacts, or shared parsed pointers for cached rows.

Synthetic batch8 #13 replay:

- A temp helper printed a mutated copy of the batch8 checker JSON with an unprinted synthetic sentinel inserted into nested inspect stderr and smoke stderr fields for both images. No Docker, benchmark, or model call was made.
- `_execute_image_preflights()` ran three rows sharing one required preflight command with `suite_concurrency=50` and `image_preflight_concurrency=4`.
- Observed: `probe_rc=0`, `summary.status=0`, `counts.pass=3`, and `image_preflight_unique_commands=1`.
- Observed: `summary_has_sentinel=false`, but `any_log_has_sentinel=true`.
- Observed owner/cached split: `tb2_batch8_owner.image_preflight.log` had `has_schema=true`, `has_sentinel=true`, and no cached marker; the two cached row logs had cached markers, no checker schema, and no sentinel.
- Observed summary rows had only `bench_id`, `ended_at`, `exit_code`, `fatal`, `log_path`, `policy`, `required`, `started_at`, and `status`; no `image_check_counts`, no native pointer, and no parsed artifact pointer.
- Interpretation: this is a direct #13 reproduction for batch8 and a #12 evidence gap. It is not a new issue because #13 now owns the raw log-sink root cause.

COMMENT-READY fixture map for #12/#13/#10:

1. `test_batch8_medium_image_check_summary_promotes_safe_counts`

- Fixture input: distilled `tb2_medium_batch8_worker_check_20260626.json`.
- Expected normalized summary fields after implementation: `image_check_parse_status="parsed"`, `image_check_counts.tar_verified == 2`, `loaded == 2`, `present == 2`, `smoke_passed == 2`, `identity_mismatch == 0`, `errors == 0`, and `pulled == 0`.
- Expected image allowlist: each row preserves `id`, `role`, `required`, `status`, `load_status`, `smoke_status`, fallback `sha256_status`, safe fallback pointer/basename or digest, final inspect identity status, and safe image refs/ids.
- Negative assertions: serialized `image_preflight_summary.json`, `summary.json`, and `agentic_bench.result.v1` contain no raw nested stderr, `pull_stderr`, `load_stderr`, `smoke_stderr`, raw Docker stdout/stderr bodies, full command text, env values, task source, task logs, adapter transcripts, or model transcripts.

2. `test_batch8_preflight_logs_do_not_persist_raw_checker_payload_after_13_fix`

- Fixture input: batch8 checker JSON with a synthetic sentinel in nested inspect stderr and smoke/load/pull stderr variants.
- Expected after #13 fix: no default controller `*.image_preflight.log` contains the sentinel or raw checker JSON body.
- Positive assertions: logs contain only a sanitized status line, parse status, safe parsed artifact pointer, redaction count, and checker counts; the safe parsed artifact contains allowlisted fields only.
- Cached-row assertion: owner and cached rows all point to the same parsed checker artifact for the invocation. Correctness must not depend on which row happened to own the command-cache future.

3. `test_batch8_result_artifact_carries_image_preflight_source_without_raw_logs`

- Fixture input: a synthetic passing adapter execution plus batch8 parsed image-check summary.
- Expected `agentic_bench.result.v1`: includes `source.image_preflight_summary_path`, `source.image_check_artifacts[]` with `role=image_check_artifact_json`, `status=parsed`, `read_policy=allowlist_json`, a content digest or stable JSON pointer, and an `image_preflight` object with status/counts/images.
- Negative assertion: `source.image_preflight_log_path`, if present, points to a sanitized log or marks any raw log as `secret_sensitive=true` and `read_policy=restricted_raw`; it must not be treated as parser input for raw JSON.

4. `test_batch8_checker_failure_keeps_execution_and_benchmark_status_separate`

- Fixture input: batch8-like checker JSON with one required image failure and synthetic `fail:image_preflight:N` execution.
- Expected after implementation: process status remains `execution.status="fail"`; benchmark status is `infra_blocked`; `metric="image_preflight"`; `failure_category="image_preflight_failed"`; `score_claim_valid=false`; parsed/redacted image evidence is still present.
- Dedup: #1/#12/#10/#13.

Cross-lane runtime/images check:

- Handoff now records that batch8 materialized `path-tracing` and `prove-plus-comm`, with worker fallback-load/run-smoke counts matching the JSON inspected here.
- Runtime lane Round18 predicted these rows as medium-generic candidates and required fallback tar plus worker fallback-load/network-none smoke rather than P0-only or real benchmark execution. Batch8 artifacts satisfy that runtime assumption.
- Handoff also notes issue comments posted for #6/#8/#12/#13 after batch8. No contradiction found.
- Runner/results interpretation remains: batch8 proves image transport readiness via fallback-load and network-none smoke. It is not worker direct-P0 readiness, not benchmark/task success, and not permission to copy raw checker stderr/logs.

### Round 19 command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0; read first, output truncated by tool.
- Skill discovery for `systematic-debugging`, `verification-before-completion`, and `using-superpowers`: rc 0.
- Read `superpowers:systematic-debugging`, `superpowers:verification-before-completion`, and `superpowers:using-superpowers` instruction files from cache `d08f0354`: rc 0.
- Memory quick search for relevant workflow/coordination terms in `/Users/Zhuanz1/.codex/memories/MEMORY.md`: rc 0; used only to retain strict remote/coordination workflow pattern.
- Remote handoff/head/ledger command on `swe_dev`: rc 0; read `_coordination/20260625_harbor_bench/HANDOFF.md`, observed branch `feat/image-warmup-policy`, head `6ade6f2`, and read this runner ledger tail plus round index.
- `git status --short --untracked-files=all && git log --oneline -12 && find ...batch8...`: rc 0; status output was empty before this ledger append, and batch8 TSV/JSON were present.
- `git diff --stat ce4f268..6ade6f2 -- scripts manifests ...`: rc 0; batch8 changed handoff, batch8 TSV/JSON, and the TB2 image manifest. No script changes in that range.
- Handoff/runtime-lane grep for batch8/path/prove/#13/checker output: rc 0; used to cross-check issue and runtime assumptions.
- Bounded Python inspection of `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch8_worker_check_20260626.json`: rc 0; printed schema, counts, row ids/statuses, fallback sha statuses, raw-field key paths/lengths, and sensitive-key path presence only. No raw stderr or secret value was printed.
- Manifest line reads for `tb2_path_tracing` and `tb2_prove_plus_comm`: rc 0.
- `nl`/`sed` reads for `scripts/agentic_bench_suite.py`, `scripts/agentic_bench_images.py`, and `scripts/test_agentic_bench_suite.py`: rc 0.
- Synthetic batch8 secret-sentinel controller replay at `suite_concurrency=50`: rc 0; confirmed raw sentinel presence in one controller preflight log, absence from summary JSON, missing structured image-check counts/pointers, and cached-row owner split. The sentinel value was not printed.
- Cross-ledger/test grep for image-check artifact/count/log redaction terms: rc 0; confirmed current tests cover dedupe but not #13 redaction or #12 parsed pointers.
- Runtime-images ledger tail read: rc 0; no contradiction found.

## Round 19 validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Bounded secret-pattern scan over this ledger: rc 0, `secret_pattern_scan=no_matches`.
- `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`.
- `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0; Round19 ledger diff was 98 inserted lines before this validation block.

## Round 20 batch9 image-check provenance and raw-log sink follow-up

### Scope

- Lane: runner/results/provenance ledger-only audit for batch9 worker-check evidence, #13 raw image-preflight log sink, and #12 safe normalized result artifacts.
- Worktree/head verified: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, head `d1895a2`.
- No production code, manifests, tests, Docker, benchmark, or model execution was performed. Only this ledger was edited.

### Dedup judgment

No new ISSUE-READY block in this round. Batch9 gives fresh multirow evidence for the existing #12/#13 contract gaps:

- #13 owns the confirmed root cause that the suite streams checker stdout/stderr into durable `controller/logs/*.image_preflight.log` before parser redaction.
- #12 owns the missing normalized image-check provenance in `image_preflight_summary.json` and `agentic_bench.result.v1`.
- #10 remains the downstream allowlist/redaction constraint for raw checker fields and any future Terminal-Bench task/native artifacts.
- Not #1: this round did not find a new execution-vs-benchmark status ordering bug.
- Not #2: command-cache owner selection affects provenance, but no new invocation-unique output root bug was found.

### Batch9 worker JSON safe facts

Artifact inspected: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch9_worker_check_20260626.json`.

- `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_medium_batch9_worker_smoke`.
- Mode: `allow_pull=false`, `load_fallback=true`, `run_smoke=true`, `skip_docker=false`, `fail_on_optional_missing=false`.
- Counts: `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `pulled=0`, `missing=0`, `identity_mismatch=0`, `tar_missing=0`, `tar_mismatch=0`, `optional_missing=0`, `unchecked=0`, `errors=0`.
- Rows: `tb2_portfolio_optimization`, `tb2_sam_cell_seg`, `tb2_train_fasttext`, and `tb2_video_processing`.
- Every row has `role=terminal_bench_task_runtime`, `required=true`, `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and one present fallback path.
- Every row has two inspect attempts. The first attempt has `returncode=1` and a nested `stderr` key by path/length only. I did not print raw stderr values.
- Manifest anchors for these rows are `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:824`, `:1019`, `:1133`, and `:1163`.

Interpretation: batch9 proves fallback-load plus network-none smoke readiness for four medium/data rows. It is not evidence of benchmark task success, direct worker P0 pull readiness, or permission to copy raw checker stderr/log bodies into one-command artifacts.

### Static code and test anchors

- `scripts/agentic_bench_suite.py:1047-1054` still runs the command-cache owner with `stdout=handle` and `stderr=subprocess.STDOUT`, so checker JSON printed to stdout is persisted in one row log.
- `scripts/agentic_bench_suite.py:1056-1059` still makes cached waiters log only `[image_preflight_cached] ... rc=N`, so cached rows do not own the native checker payload.
- `scripts/agentic_bench_suite.py:1198-1209` still writes `agentic_bench.image_preflight_summary.v1` with coarse pass/fail counts and per-row process status only; it does not preserve parsed image-check counts, image ids, fallback sha status, redaction metadata, or a shared parsed checker artifact pointer.
- `scripts/agentic_bench_suite.py:1281-1300` still writes `agentic_bench.result.v1` without `source`, `image_preflight`, image-check artifact pointers, parser version, invocation id, or image-preflight summary pointer.
- `scripts/agentic_bench_images.py:574-598` can emit raw `inspect_attempts[].stderr`, `pull_stderr`, and `load_stderr`; `scripts/agentic_bench_images.py:600-613` can emit raw `smoke_stderr`; `scripts/agentic_bench_images.py:628-643` returns those fields in native checker JSON.
- `scripts/test_agentic_bench_suite.py:502-689` covers required preflight-only execution, transport concurrency cap, and dedupe, but still has no red test for #13 raw log redaction or #12 safe parsed image-check provenance.

### Synthetic batch9 controller replay

I used a temp copy of the batch9 checker JSON and inserted an unprinted synthetic marker into nested raw checker `inspect_attempts[0].stderr` fields. Then I ran `_execute_image_preflights()` directly with four runs, `suite_concurrency=50`, `image_preflight_concurrency=4`, and one identical command that emits the temp checker JSON. This was a controller-only synthetic probe: no Docker, benchmark, or model call.

Observed safe booleans and counts:

- `probe_rc=0` and `summary.status=0`.
- `summary.counts={pass: 4, fail: 0, optional_fail: 0, skipped_no_preflight: 0, skipped_optional: 0}`.
- `image_preflight_unique_commands=1`.
- `summary_has_checker_counts=false` and `summary_has_native_pointer=false`.
- `summary_has_raw_marker=false`.
- `any_log_has_raw_marker=true`.
- The four summary result rows contain only `bench_id`, timestamps, `exit_code`, `fatal`, `log_path`, `policy`, `required`, and `status`.

Interpretation: batch9 reproduces the same #13/#12 split as batch8 and batch7. The raw checker payload is durable in the nondeterministic command-owner log, while the summary has neither raw content nor the safe structured counts/pointers needed for provenance.

### COMMENT-READY fixture guidance

1. `test_batch9_medium_image_check_summary_promotes_safe_counts`

- Fixture input: distilled batch9 `agentic_bench.image_check.v1` JSON with the four rows above.
- Expected summary fields after #12 implementation: `image_check_parse_status="parsed"`, shared parsed artifact pointer/digest, and `image_check_counts.tar_verified == loaded == present == smoke_passed == 4`; `pulled == missing == identity_mismatch == tar_missing == tar_mismatch == errors == 0`.
- Expected image rows in safe output: id, role, required, status, load status, smoke status, fallback sha status, and present fallback path count or digest. Do not include raw Docker stderr bodies.

2. `test_batch9_preflight_logs_do_not_persist_raw_checker_payload_after_13_fix`

- Fixture input: batch9 checker JSON with synthetic markers inserted into `inspect_attempts[].stderr`, plus variants for `pull_stderr`, `load_stderr`, and `smoke_stderr`.
- Expected after #13 fix: no default `controller/logs/*.image_preflight.log`, `image_preflight_summary.json`, `summary.json`, or `agentic_bench.result.v1` contains the marker or raw checker JSON body.
- Positive assertion: logs keep only a sanitized status line, parse status, safe artifact pointer, redaction count, and allowlisted counts.

3. `test_batch9_cached_preflight_rows_share_parsed_checker_artifact`

- Fixture setup: four runs at `suite_concurrency=50` with identical preflight command, matching the synthetic replay above.
- Expected after implementation: every row has a stable pointer to the same parsed checker artifact even though only one command owner executed the native checker.
- Required provenance fields: unique preflight command id or digest, parsed artifact path/digest, source manifest path, parser version, worker/docker host identity as a redacted or allowlisted value, and parse status.

4. `test_batch9_result_artifact_carries_safe_image_preflight_source`

- Expected `agentic_bench.result.v1`: add `image_preflight` with status/counts/images, plus `source.image_preflight_summary_path` and `source.image_check_artifacts[]` entries with `role=image_check_artifact_json`, `status=parsed`, `read_policy=allowlist_json`, and a content digest or stable pointer.
- Redaction assertions: no nested raw stderr, raw Docker stdout/stderr bodies, command environment values, adapter transcripts, model transcripts, task source, task logs, or benchmark run logs in normalized artifacts.

5. `test_batch9_terminal_bench_data_rows_remain_transport_only`

- Purpose: `portfolio-optimization`, `sam-cell-seg`, `train-fasttext`, and `video-processing` are data/ML-like task images. Image-check normalization should not infer Terminal-Bench task success or read task materials just because fallback-load smoke passed.
- Expected source policy: task files and any future Terminal-Bench native logs remain pointer-only until a Terminal-Bench result parser owns an allowlisted structured result artifact.

### Runtime lane cross-check

Runtime lane notes before batch9 recommended exactly this four-row batch and warned that these are data/ML-like rows, not task-result evidence. Handoff after batch9 says the full registry fallback lint now has `required_without_offline_transport=0` and that 10 TB2 `missing_shared_tar` rows remain. This does not contradict the runner lane: runner artifacts still need safe parsed image-check provenance and raw log redaction before one-command outputs are self-auditing.

### Command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- `grep` memory quick pass for this workspace context: rc 0.
- Skill instruction reads for systematic debugging, using-superpowers, and verification-before-completion: rc 0.
- Remote handoff/head/ledger read in the active worktree: rc 0; verified branch `feat/image-warmup-policy` and head `d1895a2`.
- `git status --short --untracked-files=all` plus batch9 file inventory: rc 0; worktree initially had no status output.
- Bounded Python inspection of batch9 worker JSON: first attempt rc 1 due a local f-string quoting mistake after printing safe counts; corrected inspection rc 0. No raw stderr or secret value was printed.
- TSV/manifest line reads for batch9 rows: rc 0.
- Runtime-lane grep for batch9 and #13/#12 context: rc 0.
- Static code/test line reads for suite/image checker/preflight tests: rc 0.
- Synthetic batch9 controller replay with an unprinted marker in nested raw checker stderr: rc 0; confirmed raw marker in one preflight log, absent from summary, and missing structured checker counts/pointers.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing whitespace scan on this ledger: rc 0, no matches.
- Bounded secret scan on this ledger for key-like values, bearer values, authorization values, and long secretish assignments: rc 0, no matches.
- `git status --short --untracked-files=all`: rc 0 after removing the temporary `scripts/__pycache__/agentic_bench_suite.cpython-310.pyc` produced by the synthetic import; only this ledger remains modified.

## Round 21 batch10 image-check provenance and mteb worker-load failure

### Scope

- Lane: runner/results/provenance ledger-only audit for batch10 worker-check evidence, the mteb worker-load failure, #13 raw image-preflight log sink, and #12 safe normalized result artifacts.
- Worktree/head verified: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, head `250f017`.
- No production code, manifests, tests, handoff, issue records, Docker, benchmark, or model execution was performed. Only this ledger was edited.

### Dedup decision

No new ISSUE-READY block in this round.

- Batch10 promoted `tb2_reshard_c4_data` and `tb2_pytorch_model_cli` with fallback-load/run-smoke evidence. This is fresh COMMENT-READY evidence for #12 and #13, not a new root cause.
- `tb2_mteb_retrieve` was exported/pushed according to handoff text, but not promoted because worker fallback load failed twice on the rootless daemon. This is covered by #8 for worker/rootless Docker readiness and by #12/#13 for preserving failed image-check provenance without raw stdout/stderr leakage. It is not a Terminal-Bench task-result failure and does not need a runner/results ISSUE-READY block unless a future suite execution drops or misclassifies the failed image-preflight artifact.
- #6 remains the transport-population umbrella for remaining TB2 rows. #10 remains the raw/native artifact allowlist constraint. #1 remains relevant for status split when a required image preflight blocks adapter execution, but this round did not find a new ordering/status bug.
- #2 was not implicated: no new invocation-output uniqueness problem was observed.

### Batch10 worker JSON safe facts

Artifact inspected: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch10_worker_check_20260626.json`.

- `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_medium_batch10_worker_smoke`.
- Mode: `allow_pull=false`, `load_fallback=true`, `run_smoke=true`, `skip_docker=false`, `fail_on_optional_missing=false`.
- Counts: `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `pulled=0`, `missing=0`, `identity_mismatch=0`, `tar_missing=0`, `tar_mismatch=0`, `optional_missing=0`, `unchecked=0`, `errors=0`.
- Rows: `tb2_pytorch_model_cli` and `tb2_reshard_c4_data`.
- Every row has `role=terminal_bench_task_runtime`, `required=true`, `status=present`, `load_status=loaded`, `smoke_status=passed`, fallback `sha256_status=match`, and one present fallback path.
- Every row has two inspect attempts. The first attempt has `returncode=1` and a nested `stderr` key by path/length only. I did not transcribe raw stderr values into this ledger.
- Sensitive-key scan over JSON keys found no `secret`, `token`, `authorization`, `password`, `api_key`, or `credential` key paths. That is not sufficient for safety because raw stderr fields can contain arbitrary text and remain #10/#13 scope.

Interpretation: batch10 proves fallback-load plus network-none smoke readiness for the two promoted rows. It is not proof of benchmark/task success, direct worker P0 pull readiness, or permission to copy raw checker stdout/stderr into one-command artifacts.

### TSV, manifest, and remaining-gap facts

- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_medium_batch10_20260626.tsv` contains exactly the two promoted rows, `reshard-c4-data` and `pytorch-model-cli`.
- Manifest anchors: `tb2_pytorch_model_cli` at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:884` has `image_transport: p0_digest_plus_fallback_tar`, digest ref, fallback tar, fallback sha, and `fallback_status: p0_digest_and_fallback_tar_verified`. `tb2_reshard_c4_data` at line `995` has the same promoted status shape.
- `tb2_mteb_retrieve` at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:680` still has `image_transport: swe_dev_cache_identity`, `fallback_transport: none`, and `fallback_status: missing_shared_tar`.
- Static manifest scan after batch10 found 8 `missing_shared_tar` rows: `tb2_install_windows_3_11`, `tb2_mteb_retrieve`, `tb2_multi_source_data_merger`, `tb2_pytorch_model_recovery`, `tb2_qemu_alpine_ssh`, `tb2_qemu_startup`, `tb2_torch_pipeline_parallelism`, and `tb2_torch_tensor_parallelism`.
- The batch10 worker JSON contains only `tb2_pytorch_model_cli` and `tb2_reshard_c4_data`; it does not contain mteb.
- Handoff lines for batch10 distinguish the promoted image-transport smoke from benchmark/task success, record the remaining 8 unpromoted rows, and explicitly classify mteb as a worker-load failure pending rootless Docker resolution.

### mteb worker-load failure assessment

The mteb failure should remain COMMENT-READY for existing issues, not a new runner/results issue:

- The observed failure is in worker image transport, before Terminal-Bench task execution. Normalized benchmark result should therefore use an infra/image-preflight status, not a Terminal-Bench pass/fail score.
- The failure is a rootless Docker load/readiness problem and belongs with #8 unless runtime/images lane confirms a distinct daemon or archive corruption root cause.
- The provenance gap is already #12: future suite/controller output should preserve a structured failed-load artifact even when the adapter is blocked.
- The redaction/logging gap is already #13/#10: future failed-load stderr must not be copied into default logs or normalized JSON; it should be summarized by allowlisted status fields plus a restricted raw-artifact pointer if raw capture is retained.
- Current mteb evidence is present in handoff text but not in a machine-readable batch10 worker JSON row because it was intentionally not promoted. That is acceptable for this coordination-only batch, but implementation tests should exercise the failure case directly with a synthetic checker JSON row.

### Current runner/result code anchors

- `scripts/agentic_bench_suite.py:1047-1054` still streams the command-cache owner image-preflight stdout/stderr directly to `logs/<bench>.image_preflight.log`.
- `scripts/agentic_bench_suite.py:1056-1059` still makes cached waiters log only `[image_preflight_cached] ... rc=N`.
- `scripts/agentic_bench_suite.py:1118-1135` records required preflight command failure as `fail:<rc>` and fatal, but does not parse or attach safe checker details.
- `scripts/agentic_bench_suite.py:1198-1209` still writes `agentic_bench.image_preflight_summary.v1` with coarse pass/fail counts and per-row process status only; it does not preserve parsed image-check counts, failed-load status, image ids, fallback sha status, redaction metadata, or a shared parsed checker artifact pointer.
- `scripts/agentic_bench_suite.py:1281-1300` still writes `agentic_bench.result.v1` without `source`, `image_preflight`, image-check artifact pointers, parser version, invocation id, or image-preflight summary pointer.
- `scripts/agentic_bench_images.py:574-598` can emit raw `inspect_attempts[].stderr`, `pull_stderr`, and `load_stderr`; `scripts/agentic_bench_images.py:600-613` can emit raw `smoke_stderr`; `scripts/agentic_bench_images.py:628-643` returns those fields in native checker JSON.
- Existing tests cover required preflight blocking, preflight-only execution, transport concurrency cap, and command dedupe. They still do not assert redacted failed-load image-check provenance or shared parsed artifact pointers for cached rows.

### COMMENT-READY normalized result contract for failed image preflight

Future parser/result implementation should preserve these allowlisted fields for fallback-load failures without raw stdout/stderr leakage:

1. `image_preflight`

- `status`: `fail` or `blocked` for required preflight failure.
- `parse_status`: `parsed` when the checker emitted parseable `agentic_bench.image_check.v1`; `missing` or `parse_error` otherwise.
- `failure_category`: `image_preflight_failed` with a more specific `failure_reason`, for example `worker_docker_load_failed`, `fallback_tar_missing`, `fallback_tar_mismatch`, `identity_mismatch`, `smoke_failed`, or `image_missing`.
- `mode`: allowlisted booleans for `allow_pull`, `load_fallback`, `run_smoke`, `skip_docker`, and `fail_on_optional_missing`.
- `counts`: preserve `tar_verified`, `loaded`, `present`, `smoke_passed`, `pulled`, `missing`, `identity_mismatch`, `tar_missing`, `tar_mismatch`, `optional_missing`, `unchecked`, and `errors`.
- `images[]`: preserve `id`, `role`, `required`, `status`, `pull_status`, `load_status`, `smoke_status`, `fallback.sha256_status`, `fallback.present_path_count`, `fallback.tar_digest` or configured sha, `source_image_id`, `expected_repo_digest`, and safe present/local ref identifiers. Exclude raw stderr/stdout bodies.

2. `execution` and `benchmark_result`

- `execution.status`: `fail` when adapter execution is blocked by required image preflight.
- `execution.adapter_status`: keep `fail:image_preflight:<rc>` or equivalent preflight-blocked status.
- `benchmark_result.status`: `infra_blocked`, not benchmark pass/fail.
- `benchmark_result.metric`: `image_preflight`.
- `benchmark_result.failure_category`: `image_preflight_failed`.
- `benchmark_result.score_claim_valid`: `false`.

3. `source`

- `source.image_preflight_summary_path`: pointer to the safe controller summary.
- `source.image_check_artifacts[]`: `role=image_check_artifact_json`, `status=parsed` or `parse_error`, `read_policy=allowlist_json`, stable path, content digest, parser version, and redaction count.
- `source.native_artifacts[]` for raw preflight logs or raw checker captures, if retained: `role=image_preflight_raw_log` or `image_check_raw_capture`, `status=not_read` or `restricted`, `read_policy=restricted_raw`, and `secret_sensitive=true`.
- `source.promotion_attempts[]` or equivalent for pre-promotion worker-load failures such as mteb: row id, worker id or class, transport mode, safe failure category, attempt count, artifact pointer/digest if available, and redacted raw-log pointer only.

### COMMENT-READY fixture guidance

1. `test_batch10_promoted_rows_preserve_safe_image_check_counts`

- Fixture input: distilled batch10 `agentic_bench.image_check.v1` JSON with `tb2_pytorch_model_cli` and `tb2_reshard_c4_data`.
- Expected: `parse_status="parsed"`, `image_check_counts.tar_verified == loaded == present == smoke_passed == 2`, `pulled == missing == identity_mismatch == tar_missing == tar_mismatch == errors == 0`, and two image rows with id/role/status/load/smoke/fallback sha status.
- Negative assertions: no raw nested stderr, raw Docker stdout/stderr bodies, command env, adapter transcripts, model transcripts, task source, task logs, or benchmark run logs in `image_preflight_summary.json`, `summary.json`, or `agentic_bench.result.v1`.

2. `test_mteb_worker_load_failure_is_infra_blocked_with_redacted_source`

- Fixture input: synthetic `agentic_bench.image_check.v1` with row `tb2_mteb_retrieve`, fallback sha verified, `load_status="failed"`, no `present_ref`, `smoke_status` absent/not_run, `errors > 0`, and a synthetic marker in `load_stderr`.
- Expected: required preflight blocks adapter execution; `execution.status="fail"`; `execution.adapter_status` starts with `fail:image_preflight:`; `benchmark_result.status="infra_blocked"`; `metric="image_preflight"`; `failure_category="image_preflight_failed"`; `score_claim_valid=false`.
- Expected image-preflight fields: `failure_reason="worker_docker_load_failed"`, parsed counts and image row survive, and raw stderr is excluded from default serialized artifacts.
- Expected source policy: raw failure capture appears only as a pointer with `read_policy=restricted_raw`, `secret_sensitive=true`, and a redaction count; the safe checker artifact uses `read_policy=allowlist_json`.

3. `test_batch10_cached_preflight_rows_share_failed_or_passed_parsed_artifact`

- Fixture setup: multiple runs at `suite_concurrency=50` with identical preflight command, covering both batch10 pass and mteb-style failure payloads.
- Expected: every row points to the same parsed checker artifact per unique command, regardless of which row owns the command-cache future.
- Negative assertion: neither owner nor cached-row logs persist raw checker JSON after #13 fix.

4. `test_transport_readiness_is_not_terminal_bench_task_success`

- Fixture input: batch10 promoted rows plus a synthetic Terminal-Bench native result absence.
- Expected: image warmup success records only image transport readiness. Benchmark/task score remains `unknown` or parser-specific absent until a Terminal-Bench native result parser consumes an allowlisted structured task result.

### Runtime lane cross-check

Runtime-images Round20 recommended 10A as `mteb-retrieve`, `reshard-c4-data`, and `pytorch-model-cli`, while warning that smoke must remain image-only and fallback tar mandatory. Batch10 materialized only the two rows that passed worker fallback-load/run-smoke; mteb was left unpromoted after worker load failure. This aligns with the runner lane: promoted rows are safe image-readiness evidence, and mteb is a worker transport/provenance case for #8/#12/#13, not Terminal-Bench task evidence.

### Command evidence

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Skill instruction reads for using-superpowers, systematic-debugging, and verification-before-completion: rc 0.
- Memory quick grep for workspace/coordination context: rc 0.
- Remote handoff/head/ledger read in the active worktree: rc 0; verified branch `feat/image-warmup-policy`, head `250f017`, and initially clean status.
- Batch10 artifact inventory with `find`: rc 0; found batch10 worker JSON, batch10 TSV, and runtime ledger.
- Handoff grep for batch10/mteb/#12/#13/#8 context: rc 0.
- Runtime-images ledger grep for batch10/mteb/transport context: rc 0.
- `git log --oneline -15`: rc 0; confirmed batch10 commits `0b546ef`, `8a204ba`, and `250f017` on this branch.
- Bounded Python inspection of batch10 worker JSON: rc 0; printed schema, counts, row ids/statuses, raw-field key paths/lengths, and sensitive-key path counts only.
- TSV and manifest line reads for `mteb-retrieve`, `pytorch-model-cli`, and `reshard-c4-data`: rc 0.
- `git diff --stat/name-only d1895a2..250f017` for scripts/manifests/coordination inventory/handoff: rc 0; batch10 changed handoff, batch10 TSV/JSON, and TB2 generated cache manifest, not production scripts.
- Static manifest scan for remaining `missing_shared_tar` rows and worker JSON row ids: rc 0; confirmed 8 remaining rows and `worker_json_has_mteb=false`.
- Current suite/image checker/test line reads: rc 0.
- One broad grep for mteb/batch10 context overmatched checker JSON raw stderr lines; those payloads were not transcribed into this ledger and were not used as evidence. Subsequent evidence uses structured JSON key/path/count inspection only.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: rc 0.
- Trailing whitespace scan on this ledger: rc 0, no matches.
- Bounded secret scan on this ledger for key-like values, bearer values, authorization values, and long secretish assignments: rc 0, no matches.
- `find scripts -path "*/__pycache__/*" -o -name "*.pyc"`: rc 0 initially found one untracked cache file under `scripts/__pycache__`; it was removed and the empty directory was removed if possible.
- Final status after cleanup still shows this ledger modified plus unrelated concurrent modifications in manifests/reports. I did not edit, revert, stage, commit, or push those unrelated files.
- A later pycache scan returned rc 1 after two cache files reappeared under `scripts/__pycache__`; both were removed. A follow-up pycache scan returned rc 0 with no matches.
