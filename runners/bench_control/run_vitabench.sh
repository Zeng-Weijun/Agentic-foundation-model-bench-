#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init vitabench

VITA_ROOT="${VITA_ROOT:-$NIPS_ROOT/paper_reading/external_benchmarks/VitaBench}"
VITA_BIN="$VITA_ROOT/.venv/bin/vita"
bench_require_exe "$VITA_BIN" "VitaBench CLI"

VITA_DOMAIN="${VITA_DOMAIN:-delivery}"
if [[ "$VITA_DOMAIN" == *","* ]]; then
  VITA_TASK_SET_NAME="${VITA_TASK_SET_NAME:-cross_domain}"
else
  VITA_TASK_SET_NAME="${VITA_TASK_SET_NAME:-$VITA_DOMAIN}"
fi
VITA_MAX_STEPS="${VITA_MAX_STEPS:-300}"
VITA_SAVE_TO="${VITA_SAVE_TO:-bench_${MODEL_SLUG}_${VITA_TASK_SET_NAME}_${RUN_TAG}}"
VITA_AGENT_LLM="${VITA_AGENT_LLM:-$MODEL_NAME}"
VITA_USER_LLM="${VITA_USER_LLM:-$MODEL_NAME}"
VITA_EVALUATOR_LLM="${VITA_EVALUATOR_LLM:-$MODEL_NAME}"
VITA_LANGUAGE="${VITA_LANGUAGE:-english}"
LLM_ARGS_JSON="${VITA_LLM_ARGS_JSON:-$(bench_litellm_args_json)}"
EVAL_ARGS_JSON="${VITA_EVALUATOR_LLM_ARGS_JSON:-$LLM_ARGS_JSON}"
VITA_MODEL_CONFIG_PATH="${VITA_MODEL_CONFIG_PATH:-$BENCH_RUN_DIR/vita_models.yaml}"

python - "$VITA_MODEL_CONFIG_PATH" <<'PY'
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
model = os.environ["MODEL_NAME"]
base_url = os.environ["OPENAI_BASE_URL"].rstrip("/")
api_key = os.environ.get("OPENAI_API_KEY", "")
reasoning = os.environ.get("OPENAI_REASONING_EFFORT", "")
headers = [
    '    Accept: "*/*"',
    '    Content-Type: "application/json"',
]
if api_key and api_key != "EMPTY":
    headers.append(f'    Authorization: "Bearer {api_key}"')
reasoning_line = f'    reasoning_effort: "{reasoning}"\n' if reasoning else ""
content = f"""default:
  base_url: {base_url}/chat/completions
  temperature: {os.environ.get("TEMPERATURE", "0.0")}
  max_input_tokens: {os.environ.get("MAX_INPUT_TOKENS", "128000")}
  headers:
{chr(10).join(headers)}

models:
  - name: {model}
    max_tokens: {os.environ.get("MAX_TOKENS", "4096")}
    max_input_tokens: {os.environ.get("MAX_INPUT_TOKENS", "128000")}
{reasoning_line}    cost_1m_token_dollar:
      prompt_price: 0
      completion_price: 0
"""
path.write_text(content, encoding="utf-8")
path.chmod(0o600)
PY
export VITA_MODEL_CONFIG_PATH

cd "$VITA_ROOT"

cmd=(
  "$VITA_BIN" run
  --domain "$VITA_DOMAIN"
  --task-set-name "$VITA_TASK_SET_NAME"
  --agent-llm "$VITA_AGENT_LLM"
  --user-llm "$VITA_USER_LLM"
  --evaluator-llm "$VITA_EVALUATOR_LLM"
  --num-trials "$NUM_TRIALS"
  --max-steps "$VITA_MAX_STEPS"
  --max-concurrency "$MAX_CONCURRENCY"
  --save-to "$VITA_SAVE_TO"
  --language "$VITA_LANGUAGE"
)

if [[ -n "${NUM_TASKS:-}" && "$NUM_TASKS" != "all" && "$NUM_TASKS" != "0" ]]; then
  cmd+=(--num-tasks "$NUM_TASKS")
fi
if [[ "${VITA_USE_LLM_ARGS:-0}" == "1" ]]; then
  cmd+=(--agent-llm-args "$LLM_ARGS_JSON")
  cmd+=(--user-llm-args "$LLM_ARGS_JSON")
  cmd+=(--evaluator-llm-args "$EVAL_ARGS_JSON")
fi
if [[ -n "${VITA_EVALUATION_TYPE:-}" ]]; then
  cmd+=(--evaluation-type "$VITA_EVALUATION_TYPE")
fi
if [[ -n "${VITA_TASK_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  task_ids=( $VITA_TASK_IDS )
  cmd+=(--task-ids "${task_ids[@]}")
fi
if [[ "${VITA_ENABLE_THINK:-0}" == "1" ]]; then
  cmd+=(--enable-think)
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/vitabench.log"

artifact="$VITA_ROOT/data/simulations/$VITA_SAVE_TO"
bench_finish "$artifact"
