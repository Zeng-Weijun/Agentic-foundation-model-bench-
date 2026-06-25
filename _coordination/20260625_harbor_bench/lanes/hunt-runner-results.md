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
