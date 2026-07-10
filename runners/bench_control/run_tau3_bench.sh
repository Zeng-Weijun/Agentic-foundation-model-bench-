#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/bench_common.sh"
bench_init tau3_bench

HARBOR_ROOT="${HARBOR_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor}"
TAU2_BENCH_ROOT="${TAU2_BENCH_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench}"
TAU3_MODE="${TAU3_MODE:-smoke}"
TAU3_LIMIT="${TAU3_LIMIT:-1}"
TAU3_DATASET_DIR="${TAU3_DATASET_DIR:-$HARBOR_ROOT/datasets/tau3-bench-${TAU3_MODE}}"
TAU3_JOBS_DIR="${TAU3_JOBS_DIR:-$BENCH_RUN_DIR/jobs}"
TAU3_N_CONCURRENT="${TAU3_N_CONCURRENT:-${MAX_CONCURRENCY:-1}}"
TAU3_N_ATTEMPTS="${TAU3_N_ATTEMPTS:-1}"
TAU3_MAX_RETRIES="${TAU3_MAX_RETRIES:-0}"
TAU3_AGENT="${TAU3_AGENT:-tau3_llm_agent}"
TAU3_AGENT_IMPORT_PATH="${TAU3_AGENT_IMPORT_PATH:-adapters.tau3-bench.tau3_llm_agent:Tau3LLMAgent}"
TAU3_AGENT_REASONING_EFFORT="${TAU3_AGENT_REASONING_EFFORT:-${OPENAI_REASONING_EFFORT:-medium}}"
TAU3_USER_MODEL="${TAU3_USER_MODEL:-${MODEL_NAME:-unused-no-model}}"
TAU3_USER_REASONING_EFFORT="${TAU3_USER_REASONING_EFFORT:-low}"
TAU3_NL_ASSERTIONS_MODEL="${TAU3_NL_ASSERTIONS_MODEL:-${MODEL_NAME:-unused-no-model}}"
TAU3_DIRECT_IMAGE="${TAU3_DIRECT_IMAGE:-tau3-smoke-main:20260626r2}"
TAU3_GENERATE_DATASET="${TAU3_GENERATE_DATASET:-1}"
TAU3_OVERWRITE_DATASET="${TAU3_OVERWRITE_DATASET:-0}"
TAU3_RUN_HARBOR="${TAU3_RUN_HARBOR:-1}"
HARBOR_PYTHON="${HARBOR_PYTHON:-3.12}"
HARBOR_BIN="${HARBOR_BIN:-}"

bench_require_path "$HARBOR_ROOT" "Harbor checkout"
bench_require_path "$TAU2_BENCH_ROOT" "local tau2/tau3 source checkout"
if [[ -n "$HARBOR_BIN" ]]; then
  bench_require_exe "$HARBOR_BIN" "Harbor CLI"
fi

mkdir -p "$BENCH_RUN_DIR" "$TAU3_JOBS_DIR"
{
  echo "harbor_root=$HARBOR_ROOT"
  echo "tau2_bench_root=$TAU2_BENCH_ROOT"
  echo "tau3_mode=$TAU3_MODE"
  echo "tau3_dataset_dir=$TAU3_DATASET_DIR"
  echo "tau3_limit=$TAU3_LIMIT"
  echo "tau3_n_concurrent=$TAU3_N_CONCURRENT"
  echo "tau3_jobs_dir=$TAU3_JOBS_DIR"
  echo "tau3_agent=$TAU3_AGENT"
  if [[ "$TAU3_AGENT" == "oracle" || "$TAU3_AGENT" == "oracle_direct" ]]; then
    echo "tau3_no_model_smoke=1"
  fi
  if [[ "$TAU3_AGENT" == "oracle_direct" ]]; then
    echo "tau3_direct_image=$TAU3_DIRECT_IMAGE"
  fi
} | tee -a "$BENCH_RUN_DIR/run.env.summary"

if [[ ! -d "$TAU3_DATASET_DIR" || "$TAU3_GENERATE_DATASET" == "1" ]]; then
  gen_cmd=(uv run tau3-bench --output-dir "$TAU3_DATASET_DIR")
  if [[ "$TAU3_MODE" == "smoke" && -n "$TAU3_LIMIT" ]]; then
    gen_cmd+=(--limit "$TAU3_LIMIT")
  fi
  if [[ "$TAU3_OVERWRITE_DATASET" == "1" || ! -d "$TAU3_DATASET_DIR" ]]; then
    gen_cmd+=(--overwrite)
  fi
  printf '%q ' env TAU2_BENCH_ROOT="$TAU2_BENCH_ROOT" "${gen_cmd[@]}" | tee "$BENCH_RUN_DIR/generate_dataset.command.sh"
  printf '
' | tee -a "$BENCH_RUN_DIR/generate_dataset.command.sh"
  (cd "$HARBOR_ROOT/adapters/tau3-bench" && env TAU2_BENCH_ROOT="$TAU2_BENCH_ROOT" "${gen_cmd[@]}") 2>&1 | tee "$BENCH_RUN_DIR/generate_dataset.log"
fi

find "$TAU3_DATASET_DIR" -mindepth 1 -maxdepth 1 -type d | sort > "$BENCH_RUN_DIR/tasks.list"
TASK_COUNT="$(wc -l < "$BENCH_RUN_DIR/tasks.list" | tr -d ' ')"
echo "tau3_task_count=$TASK_COUNT" | tee -a "$BENCH_RUN_DIR/run.env.summary"

if [[ "$TAU3_AGENT" == "oracle_direct" ]]; then
  if [[ "$TASK_COUNT" != "1" ]]; then
    echo "TAU3_AGENT=oracle_direct supports exactly one task, got $TASK_COUNT" >&2
    exit 2
  fi
  TAU3_DIRECT_TASK_DIR="$(head -n 1 "$BENCH_RUN_DIR/tasks.list")"
  TAU3_DIRECT_RUN_DIR="$TAU3_JOBS_DIR/direct_oracle/$(basename "$TAU3_DIRECT_TASK_DIR")"
  TAU3_RESULT_SUMMARY="$BENCH_RUN_DIR/tau3_result_summary.json"
  mkdir -p "$TAU3_DIRECT_RUN_DIR/logs/agent" "$TAU3_DIRECT_RUN_DIR/logs/verifier" "$TAU3_DIRECT_RUN_DIR/artifacts"
  direct_cmd=(
    docker run --rm --network none
    -e TAU2_BENCH_ROOT=/opt/tau2-bench
    -e TAU2_DATA_DIR=/opt/tau2-bench/data
    -e TAU2_NL_ASSERTIONS_MODEL=unused-no-model
    -v "$TAU3_DIRECT_TASK_DIR/tests:/tests:ro"
    -v "$TAU3_DIRECT_TASK_DIR/solution:/solution:ro"
    -v "$TAU3_DIRECT_RUN_DIR/logs:/logs"
    -v "$TAU3_DIRECT_RUN_DIR/artifacts:/artifacts"
    "$TAU3_DIRECT_IMAGE"
    bash -lc 'bash /solution/solve.sh && bash /tests/test.sh'
  )
  printf '%q ' env DOCKER_HOST="${DOCKER_HOST:-}" DOCKER_API_VERSION="${DOCKER_API_VERSION:-}" "${direct_cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
  printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
  if [[ "${DRY_RUN:-0}" == "1" || "$TAU3_RUN_HARBOR" == "0" ]]; then
    echo "tau3_direct_run=skipped" | tee -a "$BENCH_RUN_DIR/run.env.summary"
    bench_finish "$TAU3_DATASET_DIR"
    exit 0
  fi
  "${direct_cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/tau3_direct_oracle.log"
  direct_rc=${PIPESTATUS[0]}
  python3 - "$TAU3_DIRECT_RUN_DIR" "$TAU3_RESULT_SUMMARY" "$direct_rc" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
direct_rc = int(sys.argv[3])
result_path = run_dir / "logs" / "verifier" / "result.json"
reward_path = run_dir / "logs" / "verifier" / "reward.txt"
summary = {
    "schema_version": "agentic_bench.tau3_direct_result_summary.v1",
    "mode": "oracle_direct",
    "status": "missing_result",
    "direct_rc": direct_rc,
    "run_dir": str(run_dir),
    "result_path": str(result_path),
    "reward_path": str(reward_path),
    "reward": None,
    "verifier_status": None,
}
exit_code = 1
if result_path.exists():
    data = json.loads(result_path.read_text())
    reward = data.get("reward")
    verifier_status = data.get("status")
    summary["reward"] = reward
    summary["verifier_status"] = verifier_status
    if direct_rc == 0 and verifier_status == "passed" and float(reward or 0.0) == 1.0:
        summary["status"] = "passed"
        exit_code = 0
    elif direct_rc != 0:
        summary["status"] = "direct_command_failed"
    else:
        summary["status"] = "verifier_failed"
elif direct_rc != 0:
    summary["status"] = "direct_command_failed"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, sort_keys=True))
raise SystemExit(exit_code)
PY
  parse_rc=$?
  if [[ "$parse_rc" == "0" ]]; then
    echo "tau3_direct_run=executed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
    echo "tau3_result_status=passed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
    echo "tau3_result_summary=$TAU3_RESULT_SUMMARY" | tee -a "$BENCH_RUN_DIR/run.env.summary"
    bench_finish "$TAU3_DIRECT_RUN_DIR"
    exit 0
  fi
  echo "tau3_direct_run=executed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "tau3_result_status=failed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "tau3_result_summary=$TAU3_RESULT_SUMMARY" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "artifact=$TAU3_DIRECT_RUN_DIR" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "failed: $TAU3_DIRECT_RUN_DIR" >&2
  exit "$parse_rc"
fi

if [[ -n "$HARBOR_BIN" ]]; then
  harbor_base=("$HARBOR_BIN" run)
else
  harbor_base=(uv run --no-default-groups --no-group dev --python "$HARBOR_PYTHON" harbor run)
fi

if [[ "$TAU3_AGENT" == "oracle" ]]; then
  harbor_cmd=(
    "${harbor_base[@]}"
    -p "$TAU3_DATASET_DIR"
    -o "$TAU3_JOBS_DIR"
    -a oracle
    -k "$TAU3_N_ATTEMPTS"
    -n "$TAU3_N_CONCURRENT"
    -r "$TAU3_MAX_RETRIES"
    --no-force-build
    --yes
  )
  redacted_harbor_env=()
elif [[ "$TAU3_AGENT" == "tau3_llm_agent" ]]; then
  harbor_cmd=(
    "${harbor_base[@]}"
    -p "$TAU3_DATASET_DIR"
    -o "$TAU3_JOBS_DIR"
    -a tau3_llm_agent
    --agent-import-path "$TAU3_AGENT_IMPORT_PATH"
    -m "$MODEL_NAME"
    -k "$TAU3_N_ATTEMPTS"
    -n "$TAU3_N_CONCURRENT"
    -r "$TAU3_MAX_RETRIES"
    --ak "reasoning_effort=$TAU3_AGENT_REASONING_EFFORT"
    --ak "tau2_trial_index=0"
    --agent-include-logs "tau3-llm-agent*"
    --no-force-build
    --yes
  )
  redacted_harbor_env=(
    'OPENAI_API_KEY=${OPENAI_API_KEY}'
    'OPENAI_BASE_URL=${OPENAI_BASE_URL}'
    'TAU2_USER_MODEL=${TAU3_USER_MODEL}'
    'TAU2_USER_REASONING_EFFORT=${TAU3_USER_REASONING_EFFORT}'
    'TAU2_NL_ASSERTIONS_MODEL=${TAU3_NL_ASSERTIONS_MODEL}'
  )
else
  echo "Unsupported TAU3_AGENT: $TAU3_AGENT" >&2
  exit 2
fi
printf '%q ' env "${redacted_harbor_env[@]}" "${harbor_cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '
' | tee -a "$BENCH_RUN_DIR/command.sh"

if [[ "${DRY_RUN:-0}" == "1" || "$TAU3_RUN_HARBOR" == "0" ]]; then
  echo "tau3_harbor_run=skipped" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  bench_finish "$TAU3_DATASET_DIR"
  exit 0
fi

if [[ "$TAU3_AGENT" == "oracle" ]]; then
  (cd "$HARBOR_ROOT" && env     -u OPENAI_API_KEY     -u OPENAI_BASE_URL     -u BASE_URL     -u API_KEY     -u PACKYAPI_KEY     -u PACKY_API_KEY     -u LITELLM_MODEL     -u MODEL_NAME     "${harbor_cmd[@]}") 2>&1 | tee "$BENCH_RUN_DIR/tau3_harbor.log"
else
  (cd "$HARBOR_ROOT" && env     OPENAI_API_KEY="$OPENAI_API_KEY"     OPENAI_BASE_URL="$OPENAI_BASE_URL"     TAU2_USER_MODEL="$TAU3_USER_MODEL"     TAU2_USER_REASONING_EFFORT="$TAU3_USER_REASONING_EFFORT"     TAU2_NL_ASSERTIONS_MODEL="$TAU3_NL_ASSERTIONS_MODEL"     "${harbor_cmd[@]}") 2>&1 | tee "$BENCH_RUN_DIR/tau3_harbor.log"
fi

echo "tau3_harbor_run=executed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
TAU3_RESULT_SUMMARY="$BENCH_RUN_DIR/tau3_result_summary.json"
if python3 - "$TAU3_JOBS_DIR" "$TAU3_RESULT_SUMMARY" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

jobs_dir = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
result_paths = sorted(jobs_dir.glob("*/result.json"), key=lambda p: p.stat().st_mtime)
if not result_paths:
    summary = {
        "schema_version": "agentic_bench.tau3_result_summary.v1",
        "status": "missing_result",
        "jobs_dir": str(jobs_dir),
        "result_path": None,
        "n_total_trials": 0,
        "n_errors": 0,
        "successful_eval_trials": 0,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    raise SystemExit(2)

result_path = result_paths[-1]
data = json.loads(result_path.read_text())
stats = data.get("stats") or {}
evals = stats.get("evals") or {}
try:
    n_total_trials = int(data.get("n_total_trials") or stats.get("n_trials") or 0)
except (TypeError, ValueError):
    n_total_trials = 0
try:
    n_errors = int(stats.get("n_errors") or 0)
except (TypeError, ValueError):
    n_errors = 0
successful_eval_trials = 0
exception_stats = {}
for eval_name, eval_data in evals.items():
    if not isinstance(eval_data, dict):
        continue
    try:
        successful_eval_trials += int(eval_data.get("n_trials") or 0)
    except (TypeError, ValueError):
        pass
    if eval_data.get("exception_stats"):
        exception_stats[eval_name] = eval_data.get("exception_stats")

status = "passed"
exit_code = 0
if n_total_trials <= 0:
    status = "no_trials"
    exit_code = 1
elif n_errors > 0:
    status = "errors"
    exit_code = 1
elif successful_eval_trials <= 0:
    status = "no_successful_eval_trials"
    exit_code = 1

summary = {
    "schema_version": "agentic_bench.tau3_result_summary.v1",
    "status": status,
    "jobs_dir": str(jobs_dir),
    "result_path": str(result_path),
    "n_total_trials": n_total_trials,
    "n_errors": n_errors,
    "successful_eval_trials": successful_eval_trials,
    "exception_stats": exception_stats,
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, sort_keys=True))
raise SystemExit(exit_code)
PY
then
  echo "tau3_result_status=passed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "tau3_result_summary=$TAU3_RESULT_SUMMARY" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  bench_finish "$TAU3_JOBS_DIR"
else
  tau3_parse_rc=$?
  echo "tau3_result_status=failed" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "tau3_result_summary=$TAU3_RESULT_SUMMARY" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "artifact=$TAU3_JOBS_DIR" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "failed: $TAU3_JOBS_DIR" >&2
  exit "$tau3_parse_rc"
fi
