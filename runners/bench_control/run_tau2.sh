#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init tau2

TAU2_ROOT="${TAU2_ROOT:-$NIPS_ROOT/paper_reading/external_benchmarks/tau2-bench}"
TAU2_BIN="$TAU2_ROOT/.venv/bin/tau2"
bench_require_exe "$TAU2_BIN" "tau2 CLI"

TAU2_DOMAIN="${TAU2_DOMAIN:-airline}"
TAU2_TASK_SPLIT_NAME="${TAU2_TASK_SPLIT_NAME:-}"
TAU2_MAX_STEPS="${TAU2_MAX_STEPS:-60}"
TAU2_SAVE_TO="${TAU2_SAVE_TO:-bench_${MODEL_SLUG}_${TAU2_DOMAIN}_${RUN_TAG}}"
TAU2_AGENT_LLM="${TAU2_AGENT_LLM:-$LITELLM_MODEL}"
TAU2_USER_LLM="${TAU2_USER_LLM:-$LITELLM_MODEL}"
LLM_ARGS_JSON="${TAU2_LLM_ARGS_JSON:-$(bench_litellm_args_json)}"

cd "$TAU2_ROOT"

cmd=(
  "$TAU2_BIN" run
  --domain "$TAU2_DOMAIN"
  --agent-llm "$TAU2_AGENT_LLM"
  --user-llm "$TAU2_USER_LLM"
  --agent-llm-args "$LLM_ARGS_JSON"
  --user-llm-args "$LLM_ARGS_JSON"
  --num-trials "$NUM_TRIALS"
  --max-steps "$TAU2_MAX_STEPS"
  --max-concurrency "$MAX_CONCURRENCY"
  --save-to "$TAU2_SAVE_TO"
)

if [[ -n "$TAU2_TASK_SPLIT_NAME" ]]; then
  cmd+=(--task-split-name "$TAU2_TASK_SPLIT_NAME")
fi
if [[ -n "${NUM_TASKS:-}" && "$NUM_TASKS" != "all" && "$NUM_TASKS" != "0" ]]; then
  cmd+=(--num-tasks "$NUM_TASKS")
fi
if [[ -n "${TAU2_TASK_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  task_ids=( $TAU2_TASK_IDS )
  cmd+=(--task-ids "${task_ids[@]}")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/tau2.log"

artifact="$TAU2_ROOT/data/simulations/$TAU2_SAVE_TO/results.json"
bench_finish "$artifact"
