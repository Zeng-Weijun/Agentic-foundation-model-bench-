#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/bench_common.sh"

bench_source_env

SUITE_ID="${SUITE_ID:-smoke_$(date +%Y%m%d_%H%M%S)}"
SUITE_CONCURRENCY="${SUITE_CONCURRENCY:-3}"
SUITE_BENCHES="${SUITE_BENCHES:-tau2 vitabench terminal_bench cocoabench repozero_py2js swebench_verified}"
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
    echo "output_root=$SUITE_OUTPUT_ROOT"
    echo "created_at=$(date -Is)"
  } >"$out"
}

bench_env_for() {
  local bench="$1"
  case "$bench" in
    tau2)
      echo "NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=1 TAU2_DOMAIN=airline TAU2_MAX_STEPS=20"
      ;;
    vitabench)
      echo "NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=1 VITA_DOMAIN=delivery VITA_MAX_STEPS=20"
      ;;
    terminal_bench)
      echo "NUM_TASKS=1 MAX_CONCURRENCY=1 TB_AGENT=terminus TB_TASK_ID=analyze-access-logs TB_GLOBAL_AGENT_TIMEOUT_SEC=300 TB_GLOBAL_TEST_TIMEOUT_SEC=120"
      ;;
    repo2env)
      echo "MAX_CONCURRENCY=1 REPO2ENV_MODE=agentic_tiny REPO2ENV_MAX_TRIALS=1 REPO2ENV_MAX_SETUP_STEPS=4 REPO2ENV_MAX_VERIFY_STEPS=3"
      ;;
    cocoabench)
      echo "MAX_CONCURRENCY=1 COCOA_WORKERS=1 COCOA_TASKS_DIR=cocoabench-example-tasks COCOA_TASKS=linear-regime-estimation COCOA_MAX_ITERATIONS=20"
      ;;
    repozero_py2js)
      echo "MAX_CONCURRENCY=1 REPOZERO_WORKERS=1 REPOZERO_MODE=smoke REPOZERO_CASES=base58/test1.py REPOZERO_TIMEOUT_S=900 REPOZERO_CODEX_ATTEMPTS=1"
      ;;
    swebench_verified)
      echo "MAX_CONCURRENCY=1 SWEBENCH_NUM_WORKERS=1 SWEBENCH_EVAL_WORKERS=1 SWEBENCH_INSTANCE_REGEX=^astropy__astropy-12907$ SWEBENCH_INSTANCE_IDS=astropy__astropy-12907 SWEBENCH_PER_INSTANCE_CALL_LIMIT=80"
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
  local status_file status bench value
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
