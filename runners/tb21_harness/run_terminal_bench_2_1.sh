#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/lib/bench_common.sh"
bench_init "${BENCH_NAME:-terminal_bench_2_1_qwen_code}"

TB_ROOT="${TB_ROOT:-$NIPS_ROOT/shared_bench/terminal-bench}"
TB_BIN="${TB_BIN:-$TB_ROOT/.venv/bin/tb}"
TB_2_1_SOURCE_PATH="${TB_2_1_SOURCE_PATH:-$NIPS_ROOT/shared_bench/terminal-bench-2.1/tasks}"
TB_DATASET_PATH="${TB_DATASET_PATH:-$NIPS_ROOT/shared_bench/terminal-bench-2.1-yaml}"
TB_DATASET_NAME="${TB_DATASET_NAME:-terminal-bench/terminal-bench-2-1}"
TB_AGENT_IMPORT_PATH="${TB_AGENT_IMPORT_PATH:-}"
TB_MODEL="${TB_MODEL:-$LITELLM_MODEL}"
TB_JOB_NAME="${TB_JOB_NAME:-tb21_${MODEL_SLUG}_${TB_MODE:-run}_${RUN_TAG}}"
TB_N_CONCURRENT="${TB_N_CONCURRENT:-$MAX_CONCURRENCY}"
TB_GLOBAL_TIMEOUT_MULTIPLIER="${TB_GLOBAL_TIMEOUT_MULTIPLIER:-1.0}"

bench_require_exe "$TB_BIN" "Terminal-Bench tb CLI"
bench_require_path "$TB_2_1_SOURCE_PATH" "Terminal-Bench 2.1 source tasks"
bench_append_no_proxy_host "$OPENAI_BASE_URL"
entry_dir="$(cd -- "$(dirname -- "${BENCH_ENTRYPOINT_SH:-$0}")" && pwd)"
export PYTHONPATH="$entry_dir${PYTHONPATH:+:$PYTHONPATH}"
export QWEN_CODE_VERSION="${QWEN_CODE_VERSION:-}"
export TB2_USE_PREBUILT_IMAGES="${TB2_USE_PREBUILT_IMAGES:-0}"
export TB_CODEX_NVM_CACHE_DIR="${TB_CODEX_NVM_CACHE_DIR:-$BENCH_ROOT/terminalbench2.1/qwen-code/cache/terminal_bench_qwen_nvm}"
export TB_SHARED_UV_CACHE_DIR="${TB_SHARED_UV_CACHE_DIR:-$BENCH_ROOT/terminalbench2.1/qwen-code/cache/terminal_bench_uv}"
export TB_SHARED_HF_CACHE_DIR="${TB_SHARED_HF_CACHE_DIR:-$BENCH_ROOT/terminalbench2.1/qwen-code/cache/terminal_bench_huggingface}"

if [[ "${TB2_SKIP_DATASET_REBUILD:-0}" == "1" && -d "$TB_DATASET_PATH" ]] && find "$TB_DATASET_PATH" -mindepth 2 -maxdepth 2 -name task.yaml -print -quit | grep -q .; then
  echo "tb_dataset_rebuild=skipped path=$TB_DATASET_PATH"
else
  "$BENCH_ROOT/shared/scripts/build_terminal_bench_2_1_yaml_dataset.sh" "$TB_2_1_SOURCE_PATH" "$TB_DATASET_PATH"
fi
if [[ -n "${TB2_RUNTIME_CLOSURE_REPAIR:-}" ]]; then
  python3 "$TB2_RUNTIME_CLOSURE_REPAIR" --dataset "$TB_DATASET_PATH" --execute
fi

cd "$TB_ROOT"
help_text="$("$TB_BIN" run --help 2>&1 || true)"
cmd=("$TB_BIN" run)

if [[ -n "$TB_AGENT_IMPORT_PATH" ]]; then
  cmd+=(--agent-import-path "$TB_AGENT_IMPORT_PATH")
else
  cmd+=(--agent "${TB_AGENT:-qwen-coder}")
fi
cmd+=(--model "$TB_MODEL" --n-concurrent "$TB_N_CONCURRENT")

if grep -q -- "--run-id" <<<"$help_text"; then
  cmd+=(--run-id "$TB_JOB_NAME")
elif grep -q -- "--job-name" <<<"$help_text"; then
  cmd+=(--job-name "$TB_JOB_NAME")
fi
if grep -q -- "--output-path" <<<"$help_text"; then
  cmd+=(--output-path "$TB_ROOT/runs")
fi
if grep -q -- "--dataset-path" <<<"$help_text"; then
  cmd+=(--dataset-path "$TB_DATASET_PATH")
else
  cmd+=(--dataset "$TB_DATASET_NAME")
fi

if [[ -n "${TB_TASK_IDS:-}" ]]; then
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
if [[ -n "${TB_GLOBAL_AGENT_TIMEOUT_SEC:-}" ]] && grep -q -- "--global-agent-timeout-sec" <<<"$help_text"; then
  cmd+=(--global-agent-timeout-sec "$TB_GLOBAL_AGENT_TIMEOUT_SEC")
fi
if [[ -n "${TB_GLOBAL_TEST_TIMEOUT_SEC:-}" ]] && grep -q -- "--global-test-timeout-sec" <<<"$help_text"; then
  cmd+=(--global-test-timeout-sec "$TB_GLOBAL_TEST_TIMEOUT_SEC")
fi
if [[ -n "${TB_AGENT_KWARGS:-}" ]]; then
  # shellcheck disable=SC2206
  agent_kwargs=( $TB_AGENT_KWARGS )
  for agent_kwarg in "${agent_kwargs[@]}"; do
    cmd+=(--agent-kwarg "$agent_kwarg")
  done
fi
if [[ -n "${TB_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $TB_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

mkdir -p "$BENCH_RUN_DIR"
config_snapshot_source="${BENCH_CONFIG_YAML:-$entry_dir/config.yaml}"
cp "$config_snapshot_source" "$BENCH_RUN_DIR/config.snapshot.yaml" 2>/dev/null || true
{
  echo "tb_root=$TB_ROOT"
  echo "tb_bin=$TB_BIN"
  echo "tb_source=$TB_2_1_SOURCE_PATH"
  echo "tb_dataset_path=$TB_DATASET_PATH"
  echo "tb_dataset_name=$TB_DATASET_NAME"
  echo "tb_agent_import_path=$TB_AGENT_IMPORT_PATH"
  echo "tb_model=$TB_MODEL"
  echo "tb_job_name=$TB_JOB_NAME"
  echo "tb_n_concurrent=$TB_N_CONCURRENT"
  echo "tb_task_ids=${TB_TASK_IDS:-}"
  if [[ "${TB_MANIFEST_AGENT:-}" == "qwen-code" || "${TB_AGENT:-}" == "qwen-coder" || -n "$QWEN_CODE_VERSION" ]]; then
    echo "qwen_code_version=$QWEN_CODE_VERSION"
    echo "tb_nvm_cache=$TB_CODEX_NVM_CACHE_DIR"
    echo "tb_uv_cache=$TB_SHARED_UV_CACHE_DIR"
    echo "tb_hf_cache=$TB_SHARED_HF_CACHE_DIR"
  fi
} | tee -a "$BENCH_RUN_DIR/run.env.summary"

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
set +e
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/terminal_bench.log"
tb_rc="${PIPESTATUS[0]}"
set -e
echo "tb_rc=$tb_rc" | tee "$BENCH_RUN_DIR/tb.exit_status"

artifact="$TB_ROOT/runs/$TB_JOB_NAME"
ln -sfn "$artifact" "$BENCH_RUN_DIR/tb_run_output" 2>/dev/null || true
python3 - "$BENCH_RUN_DIR" "$artifact" <<'PYMAN'
import os
import json, sys
from pathlib import Path
run_dir=Path(sys.argv[1]); artifact=Path(sys.argv[2])
manifest={
  "agent": os.environ.get("TB_MANIFEST_AGENT", "qwen-code"),
  "benchmark": "terminal-bench-2.1",
  "artifact": str(artifact),
  "artifact_symlink": str(run_dir / "tb_run_output"),
  "command": str(run_dir / "command.sh"),
  "terminal_bench_log": str(run_dir / "terminal_bench.log"),
  "exit_status": str(run_dir / "tb.exit_status"),
  "results": str(artifact / "results.json"),
  "run_metadata": str(artifact / "run_metadata.json"),
}
(run_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
PYMAN

if [[ "$tb_rc" != "0" ]]; then
  exit "$tb_rc"
fi
bench_finish "$artifact"
