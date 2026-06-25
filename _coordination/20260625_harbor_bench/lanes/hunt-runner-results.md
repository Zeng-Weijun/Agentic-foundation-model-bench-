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
