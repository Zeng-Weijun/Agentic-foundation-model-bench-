#!/usr/bin/env bash
set -euo pipefail

BENCH_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

bench_source_env() {
  set +u
  local preserve_vars=(
	    BENCH_MODEL_PROFILE
	    MODEL_NAME MODEL_SLUG LITELLM_MODEL
	    OPENAI_BASE_URL BASE_URL OPENAI_API_KEY PACKYAPI_KEY PACKY_API_KEY API_KEY
	    HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy
	    OPENAI_REASONING_EFFORT REASONING_EFFORT
    TEMPERATURE MAX_TOKENS MAX_INPUT_TOKENS
    LOCAL_MODEL_PATH LOCAL_MODEL_STATUS LOCAL_MODEL_EXPECTED_SHARDS LOCAL_MODEL_PATH_STATE
    NUM_TASKS NUM_TRIALS MAX_CONCURRENCY
    SUITE_ID SUITE_CONCURRENCY SUITE_BENCHES SUITE_OUTPUT_ROOT
    FULL_WORKERS DOCKER_WORKERS COCOA_WORKERS REPO2ENV_WORKERS
    COCOA_USE_ENCRYPTED_TASKS
    SWEBENCH_MODE SWEBENCH_DATASET SWEBENCH_DATASET_HF SWEBENCH_SPLIT
    SWEBENCH_LIMIT SWEBENCH_INSTANCE_IDS SWEBENCH_INSTANCE_REGEX
    SWEBENCH_TEMPLATE_CFG SWEBENCH_NUM_WORKERS SWEBENCH_EVAL_WORKERS
    SWEBENCH_PER_INSTANCE_CALL_LIMIT SWEBENCH_PER_INSTANCE_COST_LIMIT
    SWEBENCH_TOTAL_COST_LIMIT SWEBENCH_SKIP_EVAL SWEBENCH_OUT_BASE
    SWE_AGENT_ROOT SWEAGENT_BIN SWE_TEMPLATE_CFG SWEBENCH_PY
    TB_DATASET_PATH TB_DATASET_NAME TB_DATASET_VERSION
    TB_AGENT TB_AGENT_IMPORT_PATH TB_AGENT_KWARGS TB_TASK_ID TB_TASK_IDS
    TB_N_CONCURRENT TB_GLOBAL_TIMEOUT_MULTIPLIER
    TB_GLOBAL_AGENT_TIMEOUT_SEC TB_GLOBAL_TEST_TIMEOUT_SEC TB_EXTRA_ARGS
    TB_CODEX_NVM_CACHE_DIR CODEX_MODEL_PROVIDER
    OPENAI_MODEL QWEN_CODE_VERSION QWEN_NATIVE_SUBSET
    OPENHANDS_ROOT OPENHANDS_CONFIG_NAME OPENHANDS_CONFIG_TOML
    OPENHANDS_AGENT OPENHANDS_EVAL_LIMIT OPENHANDS_NUM_WORKERS
    OPENHANDS_MAX_ITER OPENHANDS_DATASET OPENHANDS_SPLIT
    OPENHANDS_N_RUNS OPENHANDS_MODE OPENHANDS_LLM_CONFIG
    OPENHANDS_PYTHON OPENHANDS_OUTPUT_DIR OPENHANDS_EVAL_NOTE
    OPENHANDS_SKIP_EVAL
    MINI_SWE_BIN MINI_SWE_CONFIG MINI_SWE_MODEL MINI_SWE_SUBSET
    MINI_SWE_SPLIT MINI_SWE_WORKERS MINI_SWE_SLICE MINI_SWE_FILTER
    MINI_SWE_OUTPUT_DIR MINI_SWE_ENVIRONMENT_CLASS MINI_SWE_EXTRA_ARGS
    DEEPSWE_ROOT PIER_BIN DEEPSWE_AGENT DEEPSWE_MODEL DEEPSWE_MODEL_CLASS
    DEEPSWE_REASONING_EFFORT DEEPSWE_COST_LIMIT DEEPSWE_MODE
    DEEPSWE_N_TASKS DEEPSWE_TASK_NAME DEEPSWE_EXCLUDE_TASK_NAME
    DEEPSWE_SAMPLE_SEED DEEPSWE_N_CONCURRENT DEEPSWE_N_ATTEMPTS
    DEEPSWE_JOBS_DIR DEEPSWE_JOB_NAME DEEPSWE_ENVIRONMENT
    DEEPSWE_PIER_VENV DEEPSWE_UV_CACHE_DIR DEEPSWE_PYTHON
    DEEPSWE_PYPI_INDEX_URL
    DEEPSWE_HOST_API_RELAY DEEPSWE_RELAY_LISTEN_HOST DEEPSWE_RELAY_PORT
    DEEPSWE_RELAY_CONTAINER_HOST DEEPSWE_RELAY_UPSTREAM_PROXY
    DEEPSWE_UPSTREAM_OPENAI_BASE_URL
    DEEPSWE_TIMEOUT_MULTIPLIER DEEPSWE_AGENT_TIMEOUT_MULTIPLIER
    DEEPSWE_VERIFIER_TIMEOUT_MULTIPLIER DEEPSWE_FORCE_INSTALL
    DEEPSWE_SET_MSWEA_API_KEY DEEPSWE_DELETE DEEPSWE_EXTRA_ARGS
    MSWEA_COST_TRACKING
    SGLANG_VERSION CODE_AGENT_SCAFFOLD
  )
  local -A preserved_env=()
  local var
  for var in "${preserve_vars[@]}"; do
    if [[ ${!var+x} ]]; then
      preserved_env["$var"]="${!var}"
    fi
  done

  source ~/.bashrc >/dev/null 2>&1 || true
  if [[ -f /data/nips/shared_bench/api_config.env ]]; then
    source /data/nips/shared_bench/api_config.env >/dev/null 2>&1 || true
  fi
  if [[ -f "$BENCH_SCRIPT_DIR/model.env" ]]; then
    source "$BENCH_SCRIPT_DIR/model.env"
  fi
  if [[ -n "${BENCH_MODEL_PROFILE:-}" ]]; then
    local profile_path="$BENCH_SCRIPT_DIR/profiles/${BENCH_MODEL_PROFILE}.env"
    if [[ ! -f "$profile_path" ]]; then
      echo "Missing BENCH_MODEL_PROFILE file: $profile_path" >&2
      exit 2
    fi
    source "$profile_path"
  fi
  if [[ -f "$BENCH_SCRIPT_DIR/.env" ]]; then
    source "$BENCH_SCRIPT_DIR/.env"
  fi
  for var in "${!preserved_env[@]}"; do
    export "$var=${preserved_env[$var]}"
  done
  set -u
}

bench_append_no_proxy_host() {
  local base_url="${1:-}"
  local host

  host="${base_url#*://}"
  host="${host%%/*}"
  host="${host%%:*}"
  export NO_PROXY="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost,::1}}"

  local value
  for value in 127.0.0.1 localhost ::1 "$host"; do
    [[ -z "$value" ]] && continue
    case ",$NO_PROXY," in
      *,"$value",*) ;;
      *) NO_PROXY="$NO_PROXY,$value" ;;
    esac
  done
  export NO_PROXY
  export no_proxy="$NO_PROXY"
}

bench_slug() {
  python - "$1" <<'PY'
import re
import sys

value = sys.argv[1].strip()
value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
value = value.strip("._-")
print(value or "model")
PY
}

bench_init() {
  local bench_name="$1"
  bench_source_env

  export NIPS_ROOT="${NIPS_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026}"
  export MODEL_NAME="${MODEL_NAME:-gpt-5.4}"
  export MODEL_SLUG="${MODEL_SLUG:-$(bench_slug "$MODEL_NAME")}"
  export RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
  export BENCH_OUTPUT_ROOT="${BENCH_OUTPUT_ROOT:-$NIPS_ROOT/bench/runs}"
  export BENCH_RUN_DIR="${BENCH_RUN_DIR:-$BENCH_OUTPUT_ROOT/${bench_name}/${MODEL_SLUG}_${RUN_TAG}}"
  export OPENAI_BASE_URL="${OPENAI_BASE_URL:-${BASE_URL:-http://8.130.49.170/v1}}"
  export OPENAI_API_KEY="${OPENAI_API_KEY:-${PACKYAPI_KEY:-${PACKY_API_KEY:-${API_KEY:-EMPTY}}}}"
  export PACKYAPI_KEY="${PACKYAPI_KEY:-$OPENAI_API_KEY}"
  export PACKY_API_KEY="${PACKY_API_KEY:-$OPENAI_API_KEY}"
  export API_KEY="${API_KEY:-$OPENAI_API_KEY}"
  export BASE_URL="${BASE_URL:-$OPENAI_BASE_URL}"
  bench_append_no_proxy_host "$OPENAI_BASE_URL"
  export OPENAI_REASONING_EFFORT="${OPENAI_REASONING_EFFORT:-${REASONING_EFFORT:-xhigh}}"
  export LITELLM_MODEL="${LITELLM_MODEL:-openai/${MODEL_NAME}}"
  export TEMPERATURE="${TEMPERATURE:-0.0}"
  export MAX_TOKENS="${MAX_TOKENS:-4096}"
  export MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-128000}"
  export MAX_CONCURRENCY="${MAX_CONCURRENCY:-1}"
  export NUM_TASKS="${NUM_TASKS:-1}"
  export NUM_TRIALS="${NUM_TRIALS:-1}"

  mkdir -p "$BENCH_RUN_DIR"
  bench_log_env "$bench_name"
}

bench_log_env() {
  local bench_name="$1"
  {
    echo "bench=$bench_name"
    echo "run_dir=$BENCH_RUN_DIR"
    echo "model=$MODEL_NAME"
    echo "litellm_model=$LITELLM_MODEL"
    echo "base_url=$OPENAI_BASE_URL"
    echo "reasoning_effort=$OPENAI_REASONING_EFFORT"
    echo "num_tasks=$NUM_TASKS"
    echo "num_trials=$NUM_TRIALS"
    echo "max_concurrency=$MAX_CONCURRENCY"
    echo "created_at=$(date -Is)"
  } | tee "$BENCH_RUN_DIR/run.env.summary"
}

bench_require_path() {
  local path="$1"
  local label="$2"
  if [[ ! -e "$path" ]]; then
    echo "Missing $label: $path" >&2
    exit 2
  fi
}

bench_require_exe() {
  local path="$1"
  local label="$2"
  if [[ ! -x "$path" ]]; then
    echo "Missing executable $label: $path" >&2
    exit 2
  fi
}

bench_litellm_args_json() {
  python - <<'PY'
import json
import os

args = {
    "temperature": float(os.environ.get("TEMPERATURE", "0.0")),
    "max_tokens": int(os.environ.get("MAX_TOKENS", "4096")),
    "max_input_tokens": int(os.environ.get("MAX_INPUT_TOKENS", "128000")),
}
base_url = os.environ.get("OPENAI_BASE_URL")
if base_url:
    args["base_url"] = base_url
    args["api_base"] = base_url

reasoning = os.environ.get("OPENAI_REASONING_EFFORT")
if reasoning:
    args["reasoning_effort"] = reasoning

if os.environ.get("BENCH_PASS_API_KEY_IN_ARGS", "0") == "1":
    key = os.environ.get("OPENAI_API_KEY", "")
    if key and key != "EMPTY":
        args["api_key"] = key
        args["headers"] = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

print(json.dumps(args, separators=(",", ":")))
PY
}

bench_run() {
  echo "+ $*" | tee -a "$BENCH_RUN_DIR/command.log"
  "$@"
}

bench_finish() {
  local artifact="$1"
  echo "artifact=$artifact" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  echo "done: $artifact"
}
