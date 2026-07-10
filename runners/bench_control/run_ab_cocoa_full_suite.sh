#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/bench_common.sh"

bench_source_env

FULL_WORKERS="${FULL_WORKERS:-2}"
DOCKER_WORKERS="${DOCKER_WORKERS:-2}"
COCOA_WORKERS="${COCOA_WORKERS:-1}"
REPO2ENV_WORKERS="${REPO2ENV_WORKERS:-1}"
SUITE_ID="${SUITE_ID:-ab_cocoa_full_$(date +%Y%m%d_%H%M%S)}"
SUITE_CONCURRENCY="${SUITE_CONCURRENCY:-2}"
SUITE_BENCHES="${SUITE_BENCHES:-swebench_verified terminal_bench_2_0 repozero_py2js tau2_paper_core vitabench_full cocoabench}"
SUITE_OUTPUT_ROOT="${SUITE_OUTPUT_ROOT:-${BENCH_OUTPUT_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs}/suites/$SUITE_ID}"
mkdir -p "$SUITE_OUTPUT_ROOT/logs" "$SUITE_OUTPUT_ROOT/status"

write_suite_env() {
  local out="$SUITE_OUTPUT_ROOT/suite.env.summary"
  {
    echo "suite_id=$SUITE_ID"
    echo "suite_concurrency=$SUITE_CONCURRENCY"
    echo "suite_benches=$SUITE_BENCHES"
    echo "model=${MODEL_NAME:-}"
    echo "litellm_model=${LITELLM_MODEL:-}"
    echo "base_url=${OPENAI_BASE_URL:-${BASE_URL:-}}"
    echo "reasoning_effort=${OPENAI_REASONING_EFFORT:-${REASONING_EFFORT:-}}"
    echo "full_workers=$FULL_WORKERS"
    echo "docker_workers=$DOCKER_WORKERS"
    echo "cocoa_workers=$COCOA_WORKERS"
    echo "output_root=$SUITE_OUTPUT_ROOT"
    echo "created_at=$(date -Is)"
  } >"$out"
}

bench_env_for() {
  local bench="$1"
  case "$bench" in
    swebench_verified)
      echo "SWEBENCH_MODE=full MAX_CONCURRENCY=$DOCKER_WORKERS SWEBENCH_NUM_WORKERS=$DOCKER_WORKERS SWEBENCH_EVAL_WORKERS=$DOCKER_WORKERS SWEBENCH_PER_INSTANCE_CALL_LIMIT=200 SWEBENCH_PER_INSTANCE_COST_LIMIT=8"
      ;;
    terminal_bench_2_0)
      echo "NUM_TASKS=all MAX_CONCURRENCY=$DOCKER_WORKERS TB_AGENT=${TB_AGENT:-codex} TB_N_CONCURRENT=${TB_N_CONCURRENT:-4}"
      ;;
    repozero_py2js)
      echo "MAX_CONCURRENCY=$FULL_WORKERS REPOZERO_WORKERS=$FULL_WORKERS REPOZERO_MODE=full REPOZERO_TIMEOUT_S=1800 REPOZERO_CODEX_ATTEMPTS=1 REPOZERO_CASE_SOURCE=official REPOZERO_INCLUDE_EXCLUDED=0"
      ;;
    repo2env)
      echo "MAX_CONCURRENCY=$REPO2ENV_WORKERS REPO2ENV_WORKERS=$REPO2ENV_WORKERS REPO2ENV_MODE=small_real_agentic REPO2ENV_MAX_TRIALS=3 REPO2ENV_MAX_SETUP_STEPS=20 REPO2ENV_MAX_VERIFY_STEPS=10 REPO2ENV_NETWORK=diagnostic"
      ;;
    tau2_paper_core)
      echo "NUM_TASKS=all NUM_TRIALS=4 MAX_CONCURRENCY=$FULL_WORKERS TAU2_TASK_SPLIT_NAME=base TAU2_MAX_STEPS=60"
      ;;
    vitabench_full)
      echo "NUM_TASKS=all NUM_TRIALS=1 MAX_CONCURRENCY=$FULL_WORKERS VITA_MAX_STEPS=300 VITA_ENABLE_THINK=1 VITA_LANGUAGE=english"
      ;;
    cocoabench)
      echo "MAX_CONCURRENCY=$COCOA_WORKERS COCOA_WORKERS=$COCOA_WORKERS COCOA_TASKS_DIR=cocoabench-head COCOA_TASKS=all COCOA_RUN_ALL=1 COCOA_MAX_ITERATIONS=50"
      ;;
    *)
      echo "MAX_CONCURRENCY=1"
      ;;
  esac
}

run_one() {
  local bench="$1"
  local script="$SCRIPT_DIR/run_${bench}.sh"
  local log="$SUITE_OUTPUT_ROOT/logs/${bench}.log"
  local status_file="$SUITE_OUTPUT_ROOT/status/${bench}.status"
  local bench_run_dir="$SUITE_OUTPUT_ROOT/$bench"

  mkdir -p "$SUITE_OUTPUT_ROOT/logs" "$SUITE_OUTPUT_ROOT/status"
  if [[ ! -x "$script" ]]; then
    echo "missing executable: $script" | tee "$log" >&2
    echo "missing" >"$status_file"
    return 2
  fi

  echo "START $bench $(date -Is)" | tee "$log"
  local env_string
  local rc
  env_string="$(bench_env_for "$bench")"
  read -r -a env_parts <<<"$env_string"
  set +e
  env "${env_parts[@]}" RUN_TAG="$SUITE_ID" BENCH_RUN_DIR="$bench_run_dir" "$script" >>"$log" 2>&1
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    echo "PASS $bench $(date -Is)" | tee -a "$log"
    echo "pass" >"$status_file"
    return 0
  fi
  echo "FAIL $bench rc=$rc $(date -Is)" | tee -a "$log"
  echo "fail:$rc" >"$status_file"
  return "$rc"
}

summarize_suite() {
  local summary="$SUITE_OUTPUT_ROOT/summary.tsv"
  : >"$summary"
  local status_file bench value
  for bench in $SUITE_BENCHES; do
    status_file="$SUITE_OUTPUT_ROOT/status/${bench}.status"
    if [[ -f "$status_file" ]]; then
      value="$(cat "$status_file")"
    else
      value="not_started"
    fi
    printf '%s\t%s\t%s\n' "$bench" "$value" "$SUITE_OUTPUT_ROOT/logs/${bench}.log" >>"$summary"
  done
  cat "$summary"
}

write_suite_env

status=0
running=0
for bench in $SUITE_BENCHES; do
  (
    run_one "$bench"
  ) &
  running=$((running + 1))
  if (( running >= SUITE_CONCURRENCY )); then
    if ! wait -n; then
      status=1
    fi
    running=$((running - 1))
  fi
done

while (( running > 0 )); do
  if ! wait -n; then
    status=1
  fi
  running=$((running - 1))
done

summarize_suite | tee "$SUITE_OUTPUT_ROOT/summary.printed.tsv"
exit "$status"
