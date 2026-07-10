#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init swebench_verified_openhands

OPENHANDS_ROOT="${OPENHANDS_ROOT:-$NIPS_ROOT/shared_bench/openhands_qwen/OpenHands-0.54.0}"
OPENHANDS_PYTHON="${OPENHANDS_PYTHON:-$OPENHANDS_ROOT/.venv/bin/python}"
OPENHANDS_AGENT="${OPENHANDS_AGENT:-CodeActAgent}"
OPENHANDS_LLM_CONFIG="${OPENHANDS_LLM_CONFIG:-llm.qwen_sglang}"
OPENHANDS_EVAL_LIMIT="${OPENHANDS_EVAL_LIMIT:-2}"
OPENHANDS_NUM_WORKERS="${OPENHANDS_NUM_WORKERS:-${MAX_CONCURRENCY:-1}}"
OPENHANDS_MAX_ITER="${OPENHANDS_MAX_ITER:-100}"
OPENHANDS_LLM_TIMEOUT_S="${OPENHANDS_LLM_TIMEOUT_S:-600}"
OPENHANDS_DATASET="${OPENHANDS_DATASET:-princeton-nlp/SWE-bench_Verified}"
OPENHANDS_SPLIT="${OPENHANDS_SPLIT:-test}"
OPENHANDS_N_RUNS="${OPENHANDS_N_RUNS:-1}"
OPENHANDS_MODE="${OPENHANDS_MODE:-swe}"
OPENHANDS_OUTPUT_DIR="${OPENHANDS_OUTPUT_DIR:-$BENCH_RUN_DIR/openhands_outputs}"
OPENHANDS_CONFIG_TOML="${OPENHANDS_CONFIG_TOML:-$BENCH_RUN_DIR/config.toml}"
OPENHANDS_EVAL_NOTE="${OPENHANDS_EVAL_NOTE:-${RUN_TAG}}"

bench_require_path "$OPENHANDS_ROOT" "OpenHands checkout"
bench_require_exe "$OPENHANDS_PYTHON" "OpenHands python"

mkdir -p "$OPENHANDS_OUTPUT_DIR"

if [[ ! -f "$OPENHANDS_CONFIG_TOML" ]]; then
  cat >"$OPENHANDS_CONFIG_TOML" <<EOF
[core]
runtime = "docker"
default_agent = "$OPENHANDS_AGENT"
max_iterations = $OPENHANDS_MAX_ITER
disable_color = true

[llm.qwen_sglang]
model = "$LITELLM_MODEL"
base_url = "$OPENAI_BASE_URL"
api_key = "$OPENAI_API_KEY"
temperature = $TEMPERATURE
top_p = 1.0
max_input_tokens = $MAX_INPUT_TOKENS
max_output_tokens = $MAX_TOKENS
timeout = $OPENHANDS_LLM_TIMEOUT_S
num_retries = 5
retry_min_wait = 8
retry_max_wait = 64
drop_params = true
modify_params = false
native_tool_calling = true
caching_prompt = false
input_cost_per_token = 0.0
output_cost_per_token = 0.0

[agent]
enable_history_truncation = false
enable_condensation_request = false
enable_llm_editor = false
enable_editor = true
enable_cmd = true
enable_think = true
enable_finish = true

[agent.CodeActAgent]
enable_history_truncation = false

[condenser]
type = "noop"
EOF
fi
cp "$OPENHANDS_CONFIG_TOML" "$BENCH_RUN_DIR/openhands.config.snapshot.toml"
OPENHANDS_ROOT_CONFIG="$OPENHANDS_ROOT/config.toml"
OPENHANDS_ROOT_CONFIG_BACKUP="$BENCH_RUN_DIR/openhands.root_config.before.toml"
if [[ -f "$OPENHANDS_ROOT_CONFIG" ]]; then
  cp "$OPENHANDS_ROOT_CONFIG" "$OPENHANDS_ROOT_CONFIG_BACKUP"
else
  : > "$OPENHANDS_ROOT_CONFIG_BACKUP.missing"
fi

restore_openhands_root_config() {
  if [[ -f "$OPENHANDS_ROOT_CONFIG_BACKUP" ]]; then
    cp "$OPENHANDS_ROOT_CONFIG_BACKUP" "$OPENHANDS_ROOT_CONFIG"
  elif [[ -f "$OPENHANDS_ROOT_CONFIG_BACKUP.missing" ]]; then
    rm -f "$OPENHANDS_ROOT_CONFIG"
  fi
}
trap restore_openhands_root_config EXIT
cp "$OPENHANDS_CONFIG_TOML" "$OPENHANDS_ROOT_CONFIG"

cmd=(
  "$OPENHANDS_PYTHON" "$OPENHANDS_ROOT/evaluation/benchmarks/swe_bench/run_infer.py"
  --config-file "$OPENHANDS_CONFIG_TOML"
  --agent-cls "$OPENHANDS_AGENT"
  --llm-config "$OPENHANDS_LLM_CONFIG"
  --max-iterations "$OPENHANDS_MAX_ITER"
  --eval-num-workers "$OPENHANDS_NUM_WORKERS"
  --eval-note "$OPENHANDS_EVAL_NOTE"
  --eval-output-dir "$OPENHANDS_OUTPUT_DIR"
  --dataset "$OPENHANDS_DATASET"
  --split "$OPENHANDS_SPLIT"
  --mode "$OPENHANDS_MODE"
)

if [[ -n "$OPENHANDS_EVAL_LIMIT" ]]; then
  cmd+=(--eval-n-limit "$OPENHANDS_EVAL_LIMIT")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"

export PYTHONPATH="$OPENHANDS_ROOT${PYTHONPATH:+:$PYTHONPATH}"
cd "$OPENHANDS_ROOT"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/openhands.log"

output_jsonl="$(find "$OPENHANDS_OUTPUT_DIR" -type f -name 'output.jsonl' | sort | tail -n 1 || true)"
if [[ -z "$output_jsonl" ]]; then
  echo "Missing OpenHands output.jsonl under $OPENHANDS_OUTPUT_DIR" >&2
  exit 3
fi
ln -sfn "$(dirname "$output_jsonl")" "$BENCH_RUN_DIR/openhands_output"

if [[ "${OPENHANDS_SKIP_EVAL:-0}" != "1" ]]; then
  eval_cmd=(
    "$OPENHANDS_ROOT/evaluation/benchmarks/swe_bench/scripts/eval_infer.sh"
    "$output_jsonl"
    ""
    "$OPENHANDS_DATASET"
    "$OPENHANDS_SPLIT"
  )
  printf '%q ' "${eval_cmd[@]}" | tee "$BENCH_RUN_DIR/eval_command.sh"
  printf '\n' | tee -a "$BENCH_RUN_DIR/eval_command.sh"
  "${eval_cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/openhands_eval.log"
fi

python - "$BENCH_RUN_DIR" "$OPENHANDS_OUTPUT_DIR" "$output_jsonl" "$OPENHANDS_CONFIG_TOML" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
outdir = Path(sys.argv[2])
output_jsonl = Path(sys.argv[3])
cfg = Path(sys.argv[4])
manifest = {
    "agent": "openhands",
    "config_snapshot": str(run_dir / "openhands.config.snapshot.toml"),
    "source_config": str(cfg),
    "agent_trace_root": str(output_jsonl.parent),
    "agent_trace_symlink": str(run_dir / "openhands_output"),
    "output_jsonl": str(output_jsonl),
    "output_root": str(outdir),
    "log": str(run_dir / "openhands.log"),
    "eval_log": str(run_dir / "openhands_eval.log"),
    "command": str(run_dir / "command.sh"),
    "eval_command": str(run_dir / "eval_command.sh"),
}
(run_dir / "artifact_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

bench_finish "$output_jsonl"
