# Next Result Parser Contract - 2026-06-25

## Scope

Report-only design lane. No code, manifests, benchmark state, Docker state, or
remote artifacts were modified.

Goal: define the next normalized result-parser contract for `suite --execute`
outputs, starting from the RepoZero smoke where the suite wrapper returned
`pass` while the selected benchmark case scored `0/60`.

Inspected evidence:

- `scripts/agentic_bench_suite.py`
- `manifests/suite.example.yaml`
- `reports/repozero_suite_execute_preflight_smoke_20260625.md`
- `/tmp/agentic_repozero_exec_74640d5/summary.json`
- `/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log`
- `reports/tau2_proxy_smoke_20260625.md`
- `/tmp/agentic_tau2_proxy_smoke3/summary.json`
- `/tmp/agentic_tau2_proxy_smoke3/logs/tau2_paper_core.log`
- `reports/vitabench_repozero_worker_preflight_20260625.md`
- `reports/qwen3_coder_swebench_qwen_code_retry_cases_20260529.md`
- `reports/terminal_bench_2_1_smoke_plan_20260625.md`
- `reports/all_bench_offline_gap_matrix_20260625.md`
- `reports/agentic_bench_landscape_20260625.md`
- `reports/rootless_worker_research_20260625.md`
- `reports/trace_manifest_template.yaml`
- `manifests/runs.schema.json`

## Problem

The current suite controller records adapter execution, not benchmark semantics.
`scripts/agentic_bench_suite.py` writes:

```json
{
  "suite_id": "dev_worker_smoke_dryrun",
  "status": 0,
  "results": [
    {
      "bench_id": "repozero_py2js_smoke",
      "status": "pass",
      "exit_code": 0,
      "log_path": "/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log"
    }
  ]
}
```

That is true at the adapter/process layer. It is false as a benchmark success
claim for the just-recorded RepoZero smoke:

```text
ALL_PASS_CASES 0 / 1
TESTS 0 / 60
case=base58/test1.py all_pass=false codex_returncode=1
fail_example=missing generated entry file
```

The next contract must make this split first-class:

- `execution_status`: did the suite launch the adapter and receive an expected
  process result?
- `benchmark_status`: did the benchmark task/case pass according to native
  metric semantics?
- `score_claim`: is this result valid as a model-quality score, or only as an
  infrastructure smoke?

## Design Principles

1. Keep adapter exit status and benchmark score separate. A zero adapter exit can
   coexist with `benchmark_status: fail`.
2. Parsers must be read-only. They may read controller logs, run manifests, and
   native artifacts, but must not call models, run benchmarks, pull images, mutate
   Docker, install packages, or rerun verifiers.
3. Parser output should be deterministic JSON. Any raw free-text evidence should
   be stored as artifact pointers or short excerpts, not as the primary source of
   truth.
4. Parsing failure is its own state. Do not collapse `parse_error`,
   `infra_error`, and `benchmark_fail`.
5. Score validity must be explicit. Smoke subsets, capped-step runs, incomplete
   runs, and infra-blocked runs must set `score_claim.valid_for_leaderboard=false`.
6. The controller summary should remain useful for orchestration, but score
   consumers should read the normalized result artifact, not infer from
   `status: pass`.

## Normalized Result Artifact

Write one result artifact per selected bench:

```text
<output_root>/results/<bench_id>.result.json
```

Suggested schema:

```json
{
  "schema_version": "agentic_bench.result.v1",
  "suite_id": "dev_worker_smoke_dryrun",
  "run_id": "dev_worker_smoke_dryrun__repozero_py2js_smoke__dev_proxy_gpt54mini_8130",
  "bench_id": "repozero_py2js_smoke",
  "benchmark": "repozero_py2js",
  "adapter": "repozero_py2js",
  "parser": {
    "id": "repozero_py2js",
    "version": "2026-06-25",
    "status": "parsed",
    "parsed_at": "2026-06-25T15:22:00Z",
    "warnings": []
  },
  "source": {
    "controller_summary_path": "/tmp/agentic_repozero_exec_74640d5/summary.json",
    "controller_log_path": "/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log",
    "run_manifest_path": "/tmp/agentic_repozero_exec_74640d5/run_manifest.json",
    "native_artifact_root": "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/output_codex/gpt-5.4-mini_dev_worker_smoke_dryrun_smoke",
    "native_artifacts": []
  },
  "execution": {
    "suite_process_status": "pass",
    "adapter_exit_code": 0,
    "adapter_status": "pass",
    "image_preflight_status": "present",
    "started_at": "2026-06-25T15:21:40Z",
    "ended_at": "2026-06-25T15:21:49Z",
    "duration_s": 9.0
  },
  "benchmark_result": {
    "status": "fail",
    "completed": true,
    "metric": "tests_passed",
    "primary_score": 0.0,
    "score_unit": "fraction",
    "passed": false,
    "resolved": false,
    "numerator": 0,
    "denominator": 60,
    "tasks_passed": 0,
    "tasks_total": 1,
    "tests_passed": 0,
    "tests_total": 60,
    "reward_avg": null
  },
  "score_claim": {
    "valid_for_leaderboard": false,
    "scope": "smoke_subset",
    "reason": "single_case_smoke",
    "selected_task_ids": ["base58/test1.py"],
    "full_split_total": null
  },
  "failure": {
    "infra_error": false,
    "timeout": false,
    "failure_category": "agent_generation_failed",
    "short_failure_note": "RepoZero case failed all tests; generated entry file missing."
  },
  "cases": []
}
```

Required top-level fields:

- `schema_version`
- `suite_id`
- `run_id`
- `bench_id`
- `benchmark`
- `adapter`
- `parser`
- `source`
- `execution`
- `benchmark_result`
- `score_claim`
- `failure`
- `cases`

## Controller Summary Extension

Keep the current process-level shape for compatibility, but add result pointers
and semantic status:

```json
{
  "bench_id": "repozero_py2js_smoke",
  "status": "pass",
  "exit_code": 0,
  "log_path": "/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log",
  "result_path": "/tmp/agentic_repozero_exec_74640d5/results/repozero_py2js_smoke.result.json",
  "execution_status": "pass",
  "benchmark_status": "fail",
  "score_claim_valid": false,
  "primary_score": 0.0,
  "primary_score_unit": "fraction",
  "failure_category": "agent_generation_failed"
}
```

Recommended suite-level aggregates:

```json
{
  "status": 0,
  "execution_status": "pass",
  "benchmark_status": "fail",
  "score_claim_valid": false,
  "counts": {
    "runs": 1,
    "execution_pass": 1,
    "benchmark_pass": 0,
    "benchmark_fail": 1,
    "infra_error": 0,
    "parse_error": 0
  }
}
```

This preserves the current `status: 0` behavior while preventing downstream
consumers from treating adapter pass as benchmark pass. A future explicit gate
such as `--require-benchmark-pass` can choose to return nonzero when
`benchmark_status != pass`.

## Parser Placement

Minimal integration point:

1. `_run_one()` executes image preflight.
2. `_run_one()` executes the adapter and captures `log_path`.
3. `_run_one()` calls a read-only parser for benches that declare or infer one.
4. Parser writes `<output_root>/results/<bench_id>.result.json`.
5. `_execute_plan()` adds result fields to `summary.json`.

Avoid making parsers part of dry-run command rendering. Dry-run should only show
the planned parser ID and expected artifact hints.

Because this controller currently runs on the local Mac while native artifacts
often live under remote/shared `/mnt/...`, each parser should support two modes:

- `log_only`: parse controller log lines and artifact pointers captured locally.
- `remote_artifact`: run a read-only parser command on the execution host via the
  same SSH path, then return normalized JSON to the local controller.

Adapters should eventually emit one controller-log line to simplify parsing:

```text
AGENTIC_RESULT_JSON {"schema_version":"agentic_bench.native_result_pointer.v1", ...}
```

Until wrappers are updated, parsers should use log regexes plus native artifact
paths.

## Suite Manifest Hook

Future optional per-bench field:

```yaml
result_parser:
  id: repozero_py2js
  required: true
  mode: log_then_artifacts
  score_scope: smoke_subset
  artifact_hints:
    - source: controller_log
      regex: "^artifact=(?P<native_artifact_root>.+)$"
```

If absent, infer by `benchmark`/`adapter` for the known legacy rows. For disabled
or pending adapters, do not validate parser artifact paths until the bench is
enabled and selected.

## Status Vocabulary

`execution.adapter_status`:

- `pass`: adapter process returned the expected success code.
- `fail`: adapter process returned nonzero.
- `not_run`: adapter was skipped before launch.

`benchmark_result.status`:

- `pass`: selected benchmark tasks satisfy native success criteria.
- `fail`: selected tasks completed but did not satisfy success criteria.
- `partial`: some selected tasks completed and some remain missing/incomplete.
- `infra_error`: task could not be scored because infrastructure failed.
- `parse_error`: parser could not determine native result semantics.
- `not_scored`: parser intentionally has no native score for this run.

`score_claim.reason` examples:

- `full_split`: complete declared benchmark split.
- `smoke_subset`: selected smoke subset only.
- `capped_steps`: step/time cap intentionally prevents quality interpretation.
- `incomplete_run`: run stopped before declared denominator completed.
- `infra_blocked`: infrastructure failure before model/verifier semantics.
- `parse_error`: result artifact unavailable or unsupported.

`failure.failure_category` examples:

- `none`
- `agent_generation_failed`
- `verifier_failed`
- `empty_submission`
- `timeout`
- `capped_steps`
- `infra_docker`
- `infra_image_preflight`
- `infra_model_endpoint`
- `adapter_crash`
- `native_artifact_missing`
- `parser_unsupported`

## Parser Contracts By Benchmark

### RepoZero / Py2JS

Parser ID: `repozero_py2js`

Observed sources:

- Controller log JSON case lines:
  - `case`
  - `entry`
  - `passed`
  - `total`
  - `all_pass`
  - `fail_examples`
  - `codex_returncode`
  - `codex_timeout`
  - `codex_attempts`
  - `seconds`
  - `log`
  - `prompt`
  - `output_dir`
- Progress JSON line:
  - `cases_all_pass`
  - `tests_passed`
  - `tests_total`
- Footer lines:
  - `ALL_PASS_CASES <passed> / <total>`
  - `TESTS <passed> / <total>`
  - `artifact=<path>`

Normalized fields:

```json
{
  "benchmark_result": {
    "status": "fail",
    "metric": "tests_passed",
    "primary_score": 0.0,
    "numerator": 0,
    "denominator": 60,
    "tasks_passed": 0,
    "tasks_total": 1,
    "tests_passed": 0,
    "tests_total": 60,
    "passed": false
  },
  "cases": [
    {
      "case_id": "base58/test1.py",
      "passed": false,
      "tests_passed": 0,
      "tests_total": 60,
      "agent_returncode": 1,
      "agent_timeout": false,
      "attempts": 1,
      "duration_s": 5.03,
      "failure_category": "agent_generation_failed",
      "short_failure_note": "missing generated entry file",
      "artifacts": {
        "prompt_path": ".../prompt.txt",
        "agent_log_path": ".../codex.log",
        "output_dir": ".../test1_pkg"
      }
    }
  ]
}
```

Pass condition: every selected case has `all_pass=true`; equivalently
`ALL_PASS_CASES == total_cases` and `TESTS passed == total`.

For the current smoke, normalized status must be:

- `execution_status=pass`
- `benchmark_status=fail`
- `score_claim.valid_for_leaderboard=false`
- `score_claim.reason=smoke_subset`
- `failure.infra_error=false`
- `failure.failure_category=agent_generation_failed`

### tau2

Parser ID: `tau2`

Observed sources:

- Controller log lines:
  - `artifact=<...>/results.json`
  - `done: <...>/results.json`
  - human reward summaries.
- Native JSON paths:
  - `tau2-bench/data/simulations/<save_to>/results.json`

Native fields to extract:

- domain or task split from path/config.
- `tasks` count.
- `simulations` count.
- per-simulation task id.
- reward or score.
- termination reason.
- duration if present.
- step count if present.

Normalized metric:

- `metric=reward`
- `primary_score=average_reward`
- `reward_avg`
- `tasks_total=number of parsed simulations`
- `tasks_passed=count(reward >= 1.0)` unless native success boolean exists.

Smoke caveat:

- The recorded tau2 smoke completed one simulation per domain with reward `0.0`.
- Parser should mark `benchmark_result.status=fail` or `partial` for quality, but
  `execution.adapter_status=pass`.
- `score_claim.valid_for_leaderboard=false` because it is a three-domain smoke,
  not a declared full benchmark split.

Failure classification:

- Reward `0.0` with completed simulation: `agent_task_failed`, not infra.
- Missing `results.json`: `native_artifact_missing`.
- Runner timeout or no simulation: `timeout` or `adapter_crash` depending on
  process exit/log evidence.

### VitaBench

Parser ID: `vitabench`

Observed sources:

- Runner `run.env.summary`, which records model/base URL/task/trial/concurrency
  and artifact path.
- Runner `command.sh`.
- Runner `vitabench.log`.
- Native simulation JSON path:
  - `VitaBench/data/simulations/<save_to>`

Native fields to extract:

- top-level `timestamp`.
- `tasks` count.
- `simulations` count.
- per-simulation task id.
- domain/task set from task metadata or manifest params.
- reward.
- termination reason, including `max_steps`.
- step count and max-step cap if present.

Normalized metric:

- `metric=reward`
- `primary_score=average_reward`
- `reward_avg`
- `tasks_passed=count(reward >= 1.0)` unless native success boolean exists.

Smoke caveat:

- The recorded VitaBench one-task delivery smoke used `VITA_MAX_STEPS=20` and
  terminated by `max_steps` with reward `0.0`.
- Parser must set `score_claim.valid_for_leaderboard=false` and
  `score_claim.reason=capped_steps`.
- `failure.failure_category=capped_steps` is appropriate when the cap is the
  explicit termination reason; do not label it an infra failure.

### SWE-bench Verified

Parser ID: one of:

- `swebench_qwen_code`
- `swebench_mini_swe_agent`
- `swebench_swe_agent`
- `swebench_openhands`

Observed sources:

- Existing score report:
  - corrected score `245/500 = 49.0%`
  - `completed=486`
  - `errors=1`
  - `empty_patch=14`
  - `selective_retry_corrected_score.json`
- README/native pointers:
  - `SWE-agent/trajectories/*__<suffix>/preds.json`
  - scaffold-specific trace roots.

Preferred parser order:

1. Read a machine-readable score artifact if present, such as
   `selective_retry_corrected_score.json`.
2. Read official SWE-bench evaluation report JSON if present.
3. Read scaffold-native predictions plus verifier report.
4. Fall back to report/log parsing only as `parser.status=partial`.

Normalized metric:

- `metric=resolved`
- `primary_score=resolved_count / denominator`
- `numerator=resolved_count`
- `denominator=selected_instances`
- `resolved_rate`
- `tasks_passed=resolved_count`
- `tasks_total=selected_instances`

Per-case fields:

- `instance_id`
- `resolved`
- `completed`
- `empty_patch`
- `patch_bytes`
- `agent_returncode`
- `verifier_status`
- `failure_category`
- `trajectory_path`
- `patch_path`
- `preds_path`
- `verifier_log_path`

Score validity:

- Full Verified score is valid only when denominator and split are explicit
  (`500` for SWE-bench Verified full test) and the parser can prove all selected
  instances are accounted for.
- Smoke slices such as `MINI_SWE_SLICE: "0:1"` must set
  `valid_for_leaderboard=false` and `reason=smoke_subset`.
- Empty patches should be counted as completed or failed according to native
  report semantics, but always surfaced in `failure_category=empty_submission`.

### Terminal-Bench

Parser IDs:

- `terminal_bench_2_0`
- `terminal_bench_2_1`

Observed sources:

- Suite rows and wrapper params:
  - `TB_TASK_IDS`
  - `TB_N_CONCURRENT`
  - `TB2_USE_PREBUILT_IMAGES`
  - `BENCH_RUN_DIR`
- `scripts/run_terminal_bench_2_1_smoke.sh` writes `smoke_wrapper.env` before
  invoking the shared runner.
- Existing reports show the current TB2.1 lane is mostly pre-execute because the
  selected `fix-git` image and worker TB CLI are blocked.

Parser source expectations:

- Prefer Terminal-Bench native result JSON or JSONL when the shared runner writes
  it under `BENCH_RUN_DIR`.
- If only logs exist, parse:
  - selected task ids.
  - per-task pass/fail.
  - test command exit code.
  - pytest/test summary if present.
  - agent timeout/test timeout.
  - image-load/preflight status.

Normalized metric:

- `metric=task_pass`
- `primary_score=tasks_passed / tasks_total`
- `tasks_passed`
- `tasks_total`
- optional `tests_passed` and `tests_total` when native output exposes them.

Pass condition:

- A task passes only when the Terminal-Bench harness awards task credit. In most
  cases this means all required tests pass, not merely that the agent process
  exits successfully.

Current TB2.1 blocked state should normalize as:

- `execution_status=not_run` or `fail` depending on whether the adapter launched.
- `benchmark_status=infra_error`
- `failure_category=infra_image_preflight` for image load failure, or
  `infra_python_env` for the broken TB CLI venv.
- `score_claim.valid_for_leaderboard=false`
- no task success numerator.

### DeepSWE

Parser ID: `deepswe`

Observed sources:

- Existing local GPT-5.4-mini report records:
  - `n_completed_trials=11`
  - `n_errored_trials=11`
  - `n_running_trials=10`
  - `n_pending_trials=92`
  - all completed rewards `0.0`
  - exceptions: `AgentTimeoutError`, `NonZeroAgentExitCodeError`
  - cost about `$46.55`
- Suite row uses `DEEPSWE_MODE=smoke` and `DEEPSWE_MAX_TASKS=1`.

Parser source expectations:

- Prefer native DeepSWE/mini-swe-agent run summary JSON if present.
- Parse per-trial directories for:
  - task id.
  - reward.
  - exception type.
  - completed/running/pending/error state.
  - timeout.
  - step count.
  - cost/tokens.
  - trajectory path.
  - verifier/log path.

Normalized metric:

- `metric=reward_or_resolved`
- `primary_score=average_reward` when reward is the native metric.
- `tasks_passed=count(reward >= 1.0)` unless native success boolean exists.
- Also record `n_completed_trials`, `n_errored_trials`, `n_running_trials`, and
  `n_pending_trials`.

Score validity:

- Any run with pending/running trials after stop must set
  `benchmark_result.status=partial` and `score_claim.valid_for_leaderboard=false`.
- Completed trials with reward `0.0` and timeout exceptions are model/runtime
  failures, not valid full-score evidence.
- If rootless Docker or `host.docker.internal` relay prevents task startup, classify
  as `infra_error`, not model failure.

## Artifact Discovery Rules

Parsers should discover native artifacts in this order:

1. Explicit `result_parser.artifact_hints` from suite manifest.
2. `AGENTIC_RESULT_JSON` pointer line in controller log.
3. Known log patterns:
   - `artifact=<path>`
   - `done: <path>`
   - `run_dir=<path>`
   - `BENCH_RUN_DIR=<path>`
4. `run_manifest.json` runtime env:
   - `BENCH_RUN_DIR`
   - benchmark-specific params such as `VITA_SAVE_TO`, `REPOZERO_CASES`,
     `TB_TASK_IDS`, `MINI_SWE_SLICE`, `DEEPSWE_MAX_TASKS`.
5. Known native directory conventions from README/reports.

Every parser must record both found and missing artifacts:

```json
"source": {
  "native_artifacts": [
    {"role": "repozero_case_json_line", "path": "controller_log:line110", "status": "parsed"},
    {"role": "native_artifact_root", "path": "/mnt/.../output_codex/...", "status": "referenced_not_read"}
  ]
}
```

`referenced_not_read` is important when the local Mac controller cannot directly
read remote `/mnt/...` paths.

## Tests To Add Later

No tests were changed in this report-only lane. When implementation starts, add
fixtures before parser code:

1. RepoZero log fixture from the current smoke. Expected:
   - adapter execution pass.
   - benchmark fail.
   - `tests_passed=0`, `tests_total=60`.
   - `score_claim.valid_for_leaderboard=false`.
2. tau2 log fixture with three `artifact=` lines and synthetic `results.json`
   files. Expected average reward and per-domain cases.
3. VitaBench synthetic simulation JSON with `termination_reason=max_steps`.
   Expected `failure_category=capped_steps`.
4. SWE-bench synthetic corrected score JSON. Expected `245/500` style
   normalization plus empty-patch count.
5. Terminal-Bench infra-blocked fixture. Expected `benchmark_status=infra_error`
   and no false task pass.
6. DeepSWE partial-run fixture. Expected `benchmark_status=partial`,
   pending/running counts, timeout exceptions, and invalid leaderboard claim.

## Immediate Recommendation

Implement RepoZero first because the current smoke has an unambiguous adapter-pass
and benchmark-fail case. The first parser should be able to consume only
`/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log` and produce a
normalized result showing:

```text
execution_status=pass
benchmark_status=fail
tests=0/60
tasks=0/1
score_claim.valid_for_leaderboard=false
failure_category=agent_generation_failed
```

After that, wire tau2 and VitaBench because both already have successful harness
smokes with reward `0.0` and native simulation paths. SWE-bench, Terminal-Bench,
and DeepSWE should follow once their native artifact discovery is explicit enough
to avoid parsing fragile prose reports.
