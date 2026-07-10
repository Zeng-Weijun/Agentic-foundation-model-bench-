#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${1:-}"
SUITE_MODE="${2:-${BENCH_SUITE_MODE:-smoke}}"

if [[ -z "$CONFIG_PATH" ]]; then
  echo "Usage: $0 <config.yaml> [smoke|full]" >&2
  exit 2
fi
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Missing code model suite YAML config: $CONFIG_PATH" >&2
  exit 2
fi
case "$SUITE_MODE" in
  smoke|full) ;;
  *)
    echo "Invalid suite mode: $SUITE_MODE; expected smoke or full" >&2
    exit 2
    ;;
esac

eval "$(
  python - "$CONFIG_PATH" "$SUITE_MODE" <<'PY'
import os
import re
import shlex
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
mode = sys.argv[2]
cfg = yaml.safe_load(path.read_text()) or {}

suite = cfg.get("suite", {}) or {}
model = cfg.get("model", {}) or {}
agent = cfg.get("agent", {}) or {}
serving = cfg.get("serving", {}) or {}
workers = cfg.get("workers", {}) or {}
benchmarks = cfg.get("benchmarks", {}) or {}

exports = {
    "BENCH_CODE_MODEL_CONFIG": str(path),
    "BENCH_SUITE_MODE": mode,
}

def put(name, value):
    if value is None:
        return
    value = str(value)
    if value == "":
        return
    exports[name] = value

def slug(value):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return value or "model"

put("MODEL_NAME", model.get("served_name") or model.get("name"))
put("MODEL_SLUG", model.get("slug") or slug(str(model.get("served_name") or model.get("name") or "model")))
if model.get("litellm_model"):
    put("LITELLM_MODEL", model.get("litellm_model"))
elif model.get("served_name") or model.get("name"):
    put("LITELLM_MODEL", f"openai/{model.get('served_name') or model.get('name')}")
if model.get("base_url"):
    put("OPENAI_BASE_URL", model.get("base_url"))
    put("BASE_URL", model.get("base_url"))
if "api_key" in model:
    put("OPENAI_API_KEY", model.get("api_key"))
if "reasoning_effort" in model:
    # Empty reasoning_effort is intentional for local Qwen endpoints.
    exports["OPENAI_REASONING_EFFORT"] = str(model.get("reasoning_effort") or "")
    exports["REASONING_EFFORT"] = str(model.get("reasoning_effort") or "")
put("OPENAI_MODEL", model.get("openai_model") or model.get("served_name") or model.get("name"))
put("TEMPERATURE", model.get("temperature"))
put("MAX_TOKENS", model.get("max_tokens"))
put("MAX_INPUT_TOKENS", model.get("max_input_tokens"))
put("LOCAL_MODEL_PATH", model.get("path"))
put("LOCAL_MODEL_EXPECTED_SHARDS", model.get("expected_shards"))
put("LOCAL_MODEL_STATUS", model.get("status"))
put("SGLANG_VERSION", serving.get("sglang_version"))

if agent:
    put("CODE_AGENT_SCAFFOLD", agent.get("scaffold"))
    put("QWEN_CODE_VERSION", agent.get("qwen_code_version"))
    for raw_key, raw_value in (agent.get("env", {}) or {}).items():
        value = raw_value
        if isinstance(value, dict):
            value = value.get(mode)
        put(str(raw_key), value)
    terminal_bench = agent.get("terminal_bench", {}) or {}
    put("TB_AGENT", terminal_bench.get("agent"))
    put("TB_AGENT_IMPORT_PATH", terminal_bench.get("agent_import_path"))
    kwargs = terminal_bench.get("agent_kwargs")
    if isinstance(kwargs, dict):
        kwargs = " ".join(f"{k}={v}" for k, v in kwargs.items())
    put("TB_AGENT_KWARGS", kwargs)
    swebench = agent.get("swebench", {}) or {}
    subset = swebench.get("subset")
    if isinstance(subset, dict):
        subset = subset.get(mode)
    put("QWEN_NATIVE_SUBSET", subset)
    pull_missing = swebench.get("pull_missing_images")
    if pull_missing is not None:
        put("QWEN_NATIVE_PULL_MISSING", "1" if bool(pull_missing) else "0")
    limit = swebench.get("limit")
    if isinstance(limit, dict):
        limit = limit.get(mode)
    put("QWEN_NATIVE_LIMIT", limit)
    for raw_key, raw_value in (swebench.get("env", {}) or {}).items():
        value = raw_value
        if isinstance(value, dict):
            value = value.get(mode)
        put(str(raw_key), value)
    openhands = agent.get("openhands", {}) or {}
    for raw_key, raw_value in (openhands.get("env", {}) or {}).items():
        value = raw_value
        if isinstance(value, dict):
            value = value.get(mode)
        put(str(raw_key), value)
    mini_swe_agent = agent.get("mini_swe_agent", {}) or {}
    for raw_key, raw_value in (mini_swe_agent.get("env", {}) or {}).items():
        value = raw_value
        if isinstance(value, dict):
            value = value.get(mode)
        put(str(raw_key), value)

id_prefix = suite.get("id_prefix") or f"{exports.get('MODEL_SLUG', 'model')}_{mode}"
put("SUITE_ID_PREFIX", f"{id_prefix}_{mode}")
put("SUITE_OUTPUT_ROOT", suite.get("output_root"))

concurrency = suite.get("concurrency", {}) or {}
if isinstance(concurrency, dict):
    put("SUITE_CONCURRENCY", concurrency.get(mode))
else:
    put("SUITE_CONCURRENCY", concurrency)

bench_list = benchmarks.get(mode) or benchmarks.get("default") or suite.get("benches") or []
exports["SUITE_BENCHES"] = " ".join(str(item) for item in bench_list)

for key, env_name in {
    "full": "FULL_WORKERS",
    "docker": "DOCKER_WORKERS",
    "cocoa": "COCOA_WORKERS",
    "repo2env": "REPO2ENV_WORKERS",
}.items():
    value = workers.get(key)
    if isinstance(value, dict):
        value = value.get(mode)
    put(env_name, value)

for key, value in exports.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"

source "$SCRIPT_DIR/lib/bench_common.sh"
bench_source_env

export NIPS_ROOT="${NIPS_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026}"
export BENCH_OUTPUT_ROOT="${BENCH_OUTPUT_ROOT:-$NIPS_ROOT/bench/runs}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-${BASE_URL:-http://127.0.0.1:8503/v1}}"
export BASE_URL="${BASE_URL:-$OPENAI_BASE_URL}"
openai_base_host="${OPENAI_BASE_URL#*://}"
openai_base_host="${openai_base_host%%/*}"
openai_base_host="${openai_base_host%%:*}"
append_no_proxy() {
  local value="$1"
  [[ -z "$value" ]] && return 0
  case ",${NO_PROXY:-}," in
    *,"$value",*) ;;
    *) export NO_PROXY="${NO_PROXY:+$NO_PROXY,}$value" ;;
  esac
}
export NO_PROXY="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost,::1}}"
append_no_proxy "127.0.0.1"
append_no_proxy "localhost"
append_no_proxy "::1"
append_no_proxy "$openai_base_host"
export no_proxy="$NO_PROXY"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export PACKYAPI_KEY="${PACKYAPI_KEY:-$OPENAI_API_KEY}"
export PACKY_API_KEY="${PACKY_API_KEY:-$OPENAI_API_KEY}"
export API_KEY="${API_KEY:-$OPENAI_API_KEY}"
export OPENAI_REASONING_EFFORT="${OPENAI_REASONING_EFFORT:-${REASONING_EFFORT:-}}"
export REASONING_EFFORT="${REASONING_EFFORT:-$OPENAI_REASONING_EFFORT}"
export LITELLM_MODEL="${LITELLM_MODEL:-openai/${MODEL_NAME}}"
export TEMPERATURE="${TEMPERATURE:-0.0}"
export MAX_TOKENS="${MAX_TOKENS:-4096}"
export MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-32768}"
export SUITE_CONCURRENCY="${SUITE_CONCURRENCY:-1}"
export SUITE_OUTPUT_ROOT="${SUITE_OUTPUT_ROOT:-$BENCH_OUTPUT_ROOT/code_model_suites}"

if [[ -z "${SUITE_ID:-}" ]]; then
  export SUITE_ID="${SUITE_ID_PREFIX:-code_model_${BENCH_SUITE_MODE}}_$(date +%Y%m%d_%H%M%S)"
fi
export SUITE_OUTPUT_ROOT="$SUITE_OUTPUT_ROOT/$SUITE_ID"
mkdir -p "$SUITE_OUTPUT_ROOT/logs" "$SUITE_OUTPUT_ROOT/status"

model_path_state="not_checked"
if [[ -n "${LOCAL_MODEL_PATH:-}" ]]; then
  if [[ ! -d "$LOCAL_MODEL_PATH" ]]; then
    model_path_state="missing_dir"
  elif [[ ! -f "$LOCAL_MODEL_PATH/model.safetensors.index.json" ]]; then
    model_path_state="missing_index"
  else
    expected_count="$(
      python - "$LOCAL_MODEL_PATH/model.safetensors.index.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1]))
print(len(set(data.get("weight_map", {}).values())))
PY
    )"
    existing_count="$(find "$LOCAL_MODEL_PATH" -maxdepth 1 -name '*.safetensors' | wc -l | tr -d ' ')"
    missing_shards="$(
      python - "$LOCAL_MODEL_PATH/model.safetensors.index.json" "$LOCAL_MODEL_PATH" <<'PY'
import json
import sys
from pathlib import Path
idx = Path(sys.argv[1])
root = Path(sys.argv[2])
data = json.load(open(idx))
missing = [name for name in sorted(set(data.get("weight_map", {}).values())) if not (root / name).exists()]
print(" ".join(missing))
PY
    )"
    if [[ -n "$missing_shards" ]]; then
      model_path_state="missing_shards:${missing_shards}"
    else
      model_path_state="complete:${existing_count}/${expected_count}"
    fi
  fi
fi
export LOCAL_MODEL_PATH_STATE="$model_path_state"

write_suite_env() {
  {
    echo "suite_id=$SUITE_ID"
    echo "suite_mode=$BENCH_SUITE_MODE"
    echo "suite_benches=$SUITE_BENCHES"
    echo "suite_concurrency=$SUITE_CONCURRENCY"
    echo "model=$MODEL_NAME"
    echo "model_slug=${MODEL_SLUG:-}"
    echo "litellm_model=$LITELLM_MODEL"
    echo "base_url=$OPENAI_BASE_URL"
    echo "api_key_set=$([[ -n "${OPENAI_API_KEY:-}" && "${OPENAI_API_KEY:-}" != "EMPTY" ]] && echo yes || echo no)"
    echo "reasoning_effort=$OPENAI_REASONING_EFFORT"
    echo "temperature=$TEMPERATURE"
    echo "max_tokens=$MAX_TOKENS"
    echo "max_input_tokens=$MAX_INPUT_TOKENS"
    echo "local_model_path=${LOCAL_MODEL_PATH:-}"
    echo "local_model_status=${LOCAL_MODEL_STATUS:-}"
    echo "local_model_path_state=$LOCAL_MODEL_PATH_STATE"
    echo "full_workers=${FULL_WORKERS:-}"
    echo "docker_workers=${DOCKER_WORKERS:-}"
    echo "cocoa_workers=${COCOA_WORKERS:-}"
    echo "output_root=$SUITE_OUTPUT_ROOT"
    echo "config=$BENCH_CODE_MODEL_CONFIG"
    echo "created_at=$(date -Is)"
  } >"$SUITE_OUTPUT_ROOT/suite.env.summary"
}

bench_env_for() {
  local bench="$1"
  case "$BENCH_SUITE_MODE:$bench" in
    smoke:repozero_py2js)
      echo "REPOZERO_MODE=smoke REPOZERO_WORKERS=${FULL_WORKERS:-1} MAX_CONCURRENCY=${FULL_WORKERS:-1} REPOZERO_TIMEOUT_S=1200 REPOZERO_CODEX_ATTEMPTS=1 REPOZERO_CASES=base58/test1.py bech32/test1.py bencoder/test1.py fractions/test1.py"
      ;;
    full:repozero_py2js)
      echo "REPOZERO_MODE=full REPOZERO_WORKERS=${FULL_WORKERS:-2} MAX_CONCURRENCY=${FULL_WORKERS:-2} REPOZERO_TIMEOUT_S=1800 REPOZERO_CODEX_ATTEMPTS=1 REPOZERO_CASE_SOURCE=official REPOZERO_INCLUDE_EXCLUDED=0"
      ;;
    smoke:swebench_verified)
      echo "SWEBENCH_MODE=smoke MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} SWEBENCH_NUM_WORKERS=${SWEBENCH_NUM_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_EVAL_WORKERS=${SWEBENCH_EVAL_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_PER_INSTANCE_CALL_LIMIT=${SWEBENCH_PER_INSTANCE_CALL_LIMIT:-0} SWEBENCH_PER_INSTANCE_COST_LIMIT=${SWEBENCH_PER_INSTANCE_COST_LIMIT:-0}"
      ;;
    full:swebench_verified)
      echo "SWEBENCH_MODE=full MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} SWEBENCH_NUM_WORKERS=${SWEBENCH_NUM_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_EVAL_WORKERS=${SWEBENCH_EVAL_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_PER_INSTANCE_CALL_LIMIT=${SWEBENCH_PER_INSTANCE_CALL_LIMIT:-0} SWEBENCH_PER_INSTANCE_COST_LIMIT=${SWEBENCH_PER_INSTANCE_COST_LIMIT:-0}"
      ;;
    smoke:swebench_verified_swe_agent)
      echo "SWEBENCH_MODE=smoke MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} SWEBENCH_NUM_WORKERS=${SWEBENCH_NUM_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_EVAL_WORKERS=${SWEBENCH_EVAL_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_PER_INSTANCE_CALL_LIMIT=${SWEBENCH_PER_INSTANCE_CALL_LIMIT:-0} SWEBENCH_PER_INSTANCE_COST_LIMIT=${SWEBENCH_PER_INSTANCE_COST_LIMIT:-0}"
      ;;
    full:swebench_verified_swe_agent)
      echo "SWEBENCH_MODE=full MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} SWEBENCH_NUM_WORKERS=${SWEBENCH_NUM_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_EVAL_WORKERS=${SWEBENCH_EVAL_WORKERS:-${DOCKER_WORKERS:-1}} SWEBENCH_PER_INSTANCE_CALL_LIMIT=${SWEBENCH_PER_INSTANCE_CALL_LIMIT:-0} SWEBENCH_PER_INSTANCE_COST_LIMIT=${SWEBENCH_PER_INSTANCE_COST_LIMIT:-0}"
      ;;
    smoke:swebench_verified_openhands)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} OPENHANDS_EVAL_LIMIT=${OPENHANDS_EVAL_LIMIT:-2} OPENHANDS_NUM_WORKERS=${OPENHANDS_NUM_WORKERS:-${DOCKER_WORKERS:-1}} OPENHANDS_MAX_ITER=${OPENHANDS_MAX_ITER:-500} OPENHANDS_DATASET=${OPENHANDS_DATASET:-princeton-nlp/SWE-bench_Verified} OPENHANDS_SPLIT=${OPENHANDS_SPLIT:-test} OPENHANDS_N_RUNS=${OPENHANDS_N_RUNS:-1} OPENHANDS_MODE=${OPENHANDS_MODE:-swe} OPENHANDS_LLM_TIMEOUT_S=${OPENHANDS_LLM_TIMEOUT_S:-600}"
      ;;
    full:swebench_verified_openhands)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} OPENHANDS_EVAL_LIMIT=${OPENHANDS_EVAL_LIMIT:-500} OPENHANDS_NUM_WORKERS=${OPENHANDS_NUM_WORKERS:-${DOCKER_WORKERS:-1}} OPENHANDS_MAX_ITER=${OPENHANDS_MAX_ITER:-5000} OPENHANDS_DATASET=${OPENHANDS_DATASET:-princeton-nlp/SWE-bench_Verified} OPENHANDS_SPLIT=${OPENHANDS_SPLIT:-test} OPENHANDS_N_RUNS=${OPENHANDS_N_RUNS:-1} OPENHANDS_MODE=${OPENHANDS_MODE:-swe} OPENHANDS_LLM_TIMEOUT_S=${OPENHANDS_LLM_TIMEOUT_S:-600}"
      ;;
    smoke:swebench_verified_mini_swe_agent)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} MINI_SWE_SUBSET=${MINI_SWE_SUBSET:-verified} MINI_SWE_SPLIT=${MINI_SWE_SPLIT:-test} MINI_SWE_WORKERS=${MINI_SWE_WORKERS:-${DOCKER_WORKERS:-1}} MINI_SWE_SLICE=${MINI_SWE_SLICE:-0:2} MINI_SWE_ENVIRONMENT_CLASS=${MINI_SWE_ENVIRONMENT_CLASS:-docker}"
      ;;
    full:swebench_verified_mini_swe_agent)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-1}} MINI_SWE_SUBSET=${MINI_SWE_SUBSET:-verified} MINI_SWE_SPLIT=${MINI_SWE_SPLIT:-test} MINI_SWE_WORKERS=${MINI_SWE_WORKERS:-${DOCKER_WORKERS:-1}} MINI_SWE_ENVIRONMENT_CLASS=${MINI_SWE_ENVIRONMENT_CLASS:-docker}"
      ;;
    smoke:swebench_verified_qwen_code)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-4}} QWEN_NATIVE_SUBSET=${QWEN_NATIVE_SUBSET:-smoke_n20} QWEN_NATIVE_MAX_WORKERS=${QWEN_NATIVE_MAX_WORKERS:-${DOCKER_WORKERS:-4}} QWEN_NATIVE_BUILD_WORKERS=${QWEN_NATIVE_BUILD_WORKERS:-${DOCKER_WORKERS:-4}} QWEN_NATIVE_AGENT_TIMEOUT_S=${QWEN_NATIVE_AGENT_TIMEOUT_S:-28800} QWEN_NATIVE_VERIFIER_TIMEOUT_S=${QWEN_NATIVE_VERIFIER_TIMEOUT_S:-7200} QWEN_NATIVE_MAX_SESSION_TURNS=${QWEN_NATIVE_MAX_SESSION_TURNS:--1}"
      ;;
    full:swebench_verified_qwen_code)
      echo "MAX_CONCURRENCY=${MAX_CONCURRENCY:-${DOCKER_WORKERS:-6}} QWEN_NATIVE_SUBSET=${QWEN_NATIVE_SUBSET:-paper_n500} QWEN_NATIVE_MAX_WORKERS=${QWEN_NATIVE_MAX_WORKERS:-${DOCKER_WORKERS:-6}} QWEN_NATIVE_BUILD_WORKERS=${QWEN_NATIVE_BUILD_WORKERS:-${DOCKER_WORKERS:-6}} QWEN_NATIVE_AGENT_TIMEOUT_S=${QWEN_NATIVE_AGENT_TIMEOUT_S:-28800} QWEN_NATIVE_VERIFIER_TIMEOUT_S=${QWEN_NATIVE_VERIFIER_TIMEOUT_S:-7200} QWEN_NATIVE_MAX_SESSION_TURNS=${QWEN_NATIVE_MAX_SESSION_TURNS:--1}"
      ;;
    smoke:terminal_bench_2_0)
      echo "NUM_TASKS=1 MAX_CONCURRENCY=${DOCKER_WORKERS:-1} TB_AGENT=${TB_AGENT:-codex} TB_N_CONCURRENT=1"
      ;;
    full:terminal_bench_2_0)
      echo "NUM_TASKS=all MAX_CONCURRENCY=${DOCKER_WORKERS:-1} TB_AGENT=${TB_AGENT:-codex} TB_N_CONCURRENT=${TB_N_CONCURRENT:-4}"
      ;;
    smoke:tau2_paper_core)
      echo "NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=${FULL_WORKERS:-1} TAU2_TASK_SPLIT_NAME=base TAU2_MAX_STEPS=60"
      ;;
    full:tau2_paper_core)
      echo "NUM_TASKS=all NUM_TRIALS=4 MAX_CONCURRENCY=${FULL_WORKERS:-1} TAU2_TASK_SPLIT_NAME=base TAU2_MAX_STEPS=60"
      ;;
    smoke:vitabench_full)
      echo "NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=${FULL_WORKERS:-1} VITA_DOMAIN=delivery VITA_MAX_STEPS=120 VITA_ENABLE_THINK=0 VITA_LANGUAGE=english"
      ;;
    full:vitabench_full)
      echo "NUM_TASKS=all NUM_TRIALS=1 MAX_CONCURRENCY=${FULL_WORKERS:-1} VITA_MAX_STEPS=300 VITA_ENABLE_THINK=1 VITA_LANGUAGE=english"
      ;;
    smoke:cocoabench)
      echo "MAX_CONCURRENCY=${COCOA_WORKERS:-1} COCOA_WORKERS=${COCOA_WORKERS:-1} COCOA_TASKS_DIR=cocoabench-example-tasks COCOA_TASKS=linear-regime-estimation COCOA_MAX_ITERATIONS=20"
      ;;
    full:cocoabench)
      echo "MAX_CONCURRENCY=${COCOA_WORKERS:-1} COCOA_WORKERS=${COCOA_WORKERS:-1} COCOA_TASKS_DIR=cocoabench-head COCOA_TASKS=all COCOA_RUN_ALL=1 COCOA_MAX_ITERATIONS=50"
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
  local env_string rc

  mkdir -p "$bench_run_dir"
  if [[ ! -x "$script" ]]; then
    echo "missing executable: $script" | tee "$log" >&2
    echo "missing" >"$status_file"
    return 2
  fi

  echo "START $bench $(date -Is)" | tee "$log"
  env_string="$(bench_env_for "$bench")"
  read -r -a env_parts <<<"$env_string"
  set +e
  env "${env_parts[@]}" RUN_TAG="$SUITE_ID" BENCH_RUN_DIR="$bench_run_dir" "$script" >>"$log" 2>&1
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    echo "PASS $bench $(date -Is)" | tee -a "$log"
    echo "pass" >"$status_file"
  else
    echo "FAIL $bench rc=$rc $(date -Is)" | tee -a "$log"
    echo "fail:$rc" >"$status_file"
  fi
  return "$rc"
}

summarize_suite() {
  local summary="$SUITE_OUTPUT_ROOT/summary.tsv"
  : >"$summary"
  local bench status_file value
  for bench in $SUITE_BENCHES; do
    status_file="$SUITE_OUTPUT_ROOT/status/${bench}.status"
    value="not_started"
    [[ -f "$status_file" ]] && value="$(cat "$status_file")"
    printf '%s\t%s\t%s\n' "$bench" "$value" "$SUITE_OUTPUT_ROOT/logs/${bench}.log" >>"$summary"
  done
  cat "$summary"
}

write_suite_env
cp "$BENCH_CODE_MODEL_CONFIG" "$SUITE_OUTPUT_ROOT/config.snapshot.yaml"

if [[ "${BENCH_PRINT_CONFIG:-0}" == "1" ]]; then
  cat "$SUITE_OUTPUT_ROOT/suite.env.summary"
  echo
  echo "server_hint:"
  python - "$BENCH_CODE_MODEL_CONFIG" <<'PY'
import sys
from pathlib import Path
import yaml
cfg = yaml.safe_load(Path(sys.argv[1]).read_text()) or {}
server = cfg.get("serving", {}) or cfg.get("server", {}) or {}
for key in [
    "host_alias",
    "host_ip",
    "port",
    "sglang_version",
    "sglang_target_version",
    "install_command",
    "install_fallback_command",
    "launch_command",
    "fallback_launch_if_oom",
    "sglang_command",
    "vllm_command",
    "active_python",
    "active_sglang_version_checked",
    "model_native_context_length",
    "active_context_length",
    "previous_stable_context_length",
    "health_check",
]:
    if key in server:
        print(f"{key}={server[key]}")
PY
  exit 0
fi

if [[ "${BENCH_SKIP_MODEL_PATH_CHECK:-0}" != "1" ]]; then
  case "$LOCAL_MODEL_PATH_STATE" in
    complete:*) ;;
    not_checked) ;;
    *)
      echo "Local model path is not complete: $LOCAL_MODEL_PATH_STATE" >&2
      echo "Set BENCH_SKIP_MODEL_PATH_CHECK=1 only if the model is served from another path/host." >&2
      exit 2
      ;;
  esac
fi

status=0
running=0
for bench in $SUITE_BENCHES; do
  ( run_one "$bench" ) &
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
