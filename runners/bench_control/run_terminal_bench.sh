#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init terminal_bench

TB_ROOT="${TB_ROOT:-$NIPS_ROOT/shared_bench/terminal-bench}"
TB_BIN="${TB_BIN:-$TB_ROOT/.venv/bin/tb}"
bench_require_exe "$TB_BIN" "Terminal-Bench tb CLI"

# For code-agent evaluations, use the official installed Codex agent by default.
# Keep harness-level defaults unless explicitly overridden by TB_* variables.
TB_AGENT="${TB_AGENT:-codex}"
TB_AGENT_IMPORT_PATH="${TB_AGENT_IMPORT_PATH:-}"
TB_MODEL="${TB_MODEL:-$LITELLM_MODEL}"
TB_JOB_NAME="${TB_JOB_NAME:-tb_${MODEL_SLUG}_${RUN_TAG}}"
TB_DATASET_NAME="${TB_DATASET_NAME:-terminal-bench-core}"
TB_DATASET_VERSION="${TB_DATASET_VERSION:-2.0}"
TB_DATASET_PATH="${TB_DATASET_PATH:-$TB_ROOT/original-tasks}"
TB_N_CONCURRENT="${TB_N_CONCURRENT:-4}"
TB_GLOBAL_AGENT_TIMEOUT_SEC="${TB_GLOBAL_AGENT_TIMEOUT_SEC:-}"
TB_GLOBAL_TEST_TIMEOUT_SEC="${TB_GLOBAL_TEST_TIMEOUT_SEC:-}"
TB_GLOBAL_TIMEOUT_MULTIPLIER="${TB_GLOBAL_TIMEOUT_MULTIPLIER:-}"

cd "$TB_ROOT"

help_text="$("$TB_BIN" run --help 2>&1 || true)"
cmd=("$TB_BIN" run)

if [[ -n "$TB_AGENT_IMPORT_PATH" ]]; then
  if grep -q -- "--agent-import-path" <<<"$help_text"; then
    cmd+=(--agent-import-path "$TB_AGENT_IMPORT_PATH")
  else
    echo "Terminal-Bench CLI does not support --agent-import-path" >&2
    exit 2
  fi
else
  cmd+=(--agent "$TB_AGENT")
fi

cmd+=(--model "$TB_MODEL" --n-concurrent "$TB_N_CONCURRENT")

if [[ -n "${TB_AGENT_KWARGS:-}" ]]; then
  if ! grep -q -- "--agent-kwarg" <<<"$help_text"; then
    echo "Terminal-Bench CLI does not support --agent-kwarg" >&2
    exit 2
  fi
  # shellcheck disable=SC2206
  agent_kwargs=( $TB_AGENT_KWARGS )
  for agent_kwarg in "${agent_kwargs[@]}"; do
    cmd+=(--agent-kwarg "$agent_kwarg")
  done
fi

if grep -q -- "--job-name" <<<"$help_text"; then
  cmd+=(--job-name "$TB_JOB_NAME")
elif grep -q -- "--run-id" <<<"$help_text"; then
  cmd+=(--run-id "$TB_JOB_NAME")
fi
if grep -q -- "--dataset-path" <<<"$help_text"; then
  cmd+=(--dataset-path "$TB_DATASET_PATH")
elif grep -q -- "--dataset-name" <<<"$help_text"; then
  cmd+=(--dataset-name "$TB_DATASET_NAME")
  if grep -q -- "--dataset-version" <<<"$help_text"; then
    cmd+=(--dataset-version "$TB_DATASET_VERSION")
  fi
elif grep -q -- "--dataset " <<<"$help_text"; then
  cmd+=(--dataset "${TB_DATASET_NAME}==${TB_DATASET_VERSION}")
fi

if [[ -n "${TB_TASK_ID:-}" ]]; then
  cmd+=(--task-id "$TB_TASK_ID")
elif [[ -n "${TB_TASK_IDS:-}" ]]; then
  # Some tb versions accept repeated --task-id; if not, pass TB_EXTRA_ARGS.
  # shellcheck disable=SC2206
  task_ids=( $TB_TASK_IDS )
  for task_id in "${task_ids[@]}"; do
    cmd+=(--task-id "$task_id")
  done
elif [[ -n "${NUM_TASKS:-}" && "$NUM_TASKS" != "all" && "$NUM_TASKS" != "0" ]] && grep -q -- "--n-tasks" <<<"$help_text"; then
  cmd+=(--n-tasks "$NUM_TASKS")
fi

if [[ -n "$TB_GLOBAL_TIMEOUT_MULTIPLIER" ]] && grep -q -- "--global-timeout-multiplier" <<<"$help_text"; then
  cmd+=(--global-timeout-multiplier "$TB_GLOBAL_TIMEOUT_MULTIPLIER")
fi
if [[ -n "$TB_GLOBAL_AGENT_TIMEOUT_SEC" ]] && grep -q -- "--global-agent-timeout-sec" <<<"$help_text"; then
  cmd+=(--global-agent-timeout-sec "$TB_GLOBAL_AGENT_TIMEOUT_SEC")
fi
if [[ -n "$TB_GLOBAL_TEST_TIMEOUT_SEC" ]] && grep -q -- "--global-test-timeout-sec" <<<"$help_text"; then
  cmd+=(--global-test-timeout-sec "$TB_GLOBAL_TEST_TIMEOUT_SEC")
fi
if [[ -n "${TB_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $TB_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/terminal_bench.log"

artifact="$TB_ROOT/runs/$TB_JOB_NAME"
bench_finish "$artifact"
