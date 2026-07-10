#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init cocoabench

COCOA_ROOT="${COCOA_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/cocoa-agent}"
COCOA_TASKS_DIR="${COCOA_TASKS_DIR:-cocoabench-example-tasks}"
COCOA_EFFECTIVE_TASKS_DIR="$COCOA_TASKS_DIR"
COCOA_OUTPUT_DIR="${COCOA_OUTPUT_DIR:-$BENCH_RUN_DIR/results}"
COCOA_WORK_DIR="${COCOA_WORK_DIR:-$BENCH_RUN_DIR/work}"
COCOA_CONFIG="$BENCH_RUN_DIR/cocoa_config.json"
COCOA_WORKERS="${COCOA_WORKERS:-$MAX_CONCURRENCY}"
COCOA_MAX_ITERATIONS="${COCOA_MAX_ITERATIONS:-50}"
COCOA_USE_RESPONSES_API="${COCOA_USE_RESPONSES_API:-0}"
COCOA_TASKS="${COCOA_TASKS:-linear-regime-estimation}"
COCOA_USE_ENCRYPTED_TASKS="${COCOA_USE_ENCRYPTED_TASKS:-auto}"
bench_require_path "$COCOA_ROOT" "cocoa-agent checkout"

if [[ "$COCOA_TASKS_DIR" = /* ]]; then
  cocoa_tasks_probe="$COCOA_TASKS_DIR"
else
  cocoa_tasks_probe="$COCOA_ROOT/$COCOA_TASKS_DIR"
fi

if [[ "$COCOA_USE_ENCRYPTED_TASKS" == "auto" ]]; then
  if find "$cocoa_tasks_probe" -maxdepth 2 -name 'task.yaml.enc' -print -quit | grep -q .; then
    COCOA_USE_ENCRYPTED_TASKS=1
  else
    COCOA_USE_ENCRYPTED_TASKS=0
  fi
fi

case "$COCOA_USE_ENCRYPTED_TASKS" in
  1|true|TRUE|yes|YES) COCOA_USE_ENCRYPTED_TASKS=1 ;;
  0|false|FALSE|no|NO) COCOA_USE_ENCRYPTED_TASKS=0 ;;
  *)
    echo "Invalid COCOA_USE_ENCRYPTED_TASKS=$COCOA_USE_ENCRYPTED_TASKS; use auto, 1, or 0" >&2
    exit 2
    ;;
esac
export COCOA_USE_ENCRYPTED_TASKS

if [[ -x "$COCOA_ROOT/.venv/bin/python" ]]; then
  cocoa_python=("$COCOA_ROOT/.venv/bin/python")
elif [[ -x /root/.local/bin/uv ]]; then
  cocoa_python=(/root/.local/bin/uv run python)
else
  cocoa_python=(python)
fi

python - "$COCOA_CONFIG" <<'PY'
import json
import os
import sys

cfg = {
    "agent_type": "cocoa",
    "log_level": os.environ.get("COCOA_LOG_LEVEL", "INFO"),
    "use_encrypted_tasks": os.environ.get("COCOA_USE_ENCRYPTED_TASKS", "0") == "1",
    "controller": {
        "type": os.environ.get("COCOA_CONTROLLER_TYPE", "gpt"),
        "args": {
            "model": os.environ["MODEL_NAME"],
            "base_url": os.environ.get("OPENAI_BASE_URL", ""),
            "api_key": "",
            "reasoning_effort": os.environ.get("OPENAI_REASONING_EFFORT", "xhigh"),
            "use_responses_api": os.environ.get("COCOA_USE_RESPONSES_API", "0") == "1",
            "cleanup_old_user_images": False,
        },
    },
    "sandbox": {
        "client_type": "unified",
        "docker_port": int(os.environ.get("COCOA_DOCKER_PORT", "8084")),
        "max_iterations": int(os.environ.get("COCOA_MAX_ITERATIONS", "50")),
    },
}
open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(cfg, indent=2, sort_keys=True))
PY

cd "$COCOA_ROOT"
mkdir -p "$COCOA_OUTPUT_DIR" "$COCOA_WORK_DIR"

if [[ "$COCOA_USE_ENCRYPTED_TASKS" == "1" ]]; then
  cocoa_required_task_file="task.yaml.enc"
else
  cocoa_required_task_file="task.yaml"
fi
{
  echo "cocoa_use_encrypted_tasks=$COCOA_USE_ENCRYPTED_TASKS"
  echo "cocoa_required_task_file=$cocoa_required_task_file"
} | tee -a "$BENCH_RUN_DIR/run.env.summary"

if [[ -n "$COCOA_TASKS" && "$COCOA_TASKS" != "all" ]]; then
  # shellcheck disable=SC2206
  tasks=( $COCOA_TASKS )
  COCOA_EFFECTIVE_TASKS_DIR="$BENCH_RUN_DIR/selected_cocoa_tasks"
  rm -rf "$COCOA_EFFECTIVE_TASKS_DIR"
  mkdir -p "$COCOA_EFFECTIVE_TASKS_DIR"
  for task_name in "${tasks[@]}"; do
    src="$cocoa_tasks_probe/$task_name"
    if [[ ! -d "$src" ]]; then
      echo "Missing CoCoA task directory: $src" >&2
      exit 2
    fi
    if [[ ! -f "$src/$cocoa_required_task_file" ]]; then
      echo "CoCoA task $task_name is not supported by this runner mode: missing $cocoa_required_task_file" >&2
      exit 2
    fi
    ln -s "$(cd "$src" && pwd)" "$COCOA_EFFECTIVE_TASKS_DIR/$task_name"
  done
else
  COCOA_EFFECTIVE_TASKS_DIR="$BENCH_RUN_DIR/supported_cocoa_tasks"
  rm -rf "$COCOA_EFFECTIVE_TASKS_DIR"
  mkdir -p "$COCOA_EFFECTIVE_TASKS_DIR"
  supported=0
  skipped=0
  while IFS= read -r -d '' src; do
    task_name="$(basename "$src")"
    if [[ -f "$src/$cocoa_required_task_file" ]]; then
      ln -s "$(cd "$src" && pwd)" "$COCOA_EFFECTIVE_TASKS_DIR/$task_name"
      supported=$((supported + 1))
    else
      skipped=$((skipped + 1))
    fi
  done < <(find "$cocoa_tasks_probe" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
  if (( supported == 0 )); then
    echo "No CoCoA tasks with $cocoa_required_task_file found under $cocoa_tasks_probe" >&2
    exit 2
  fi
  {
    echo "cocoa_supported_tasks=$supported"
    echo "cocoa_skipped_unsupported_tasks=$skipped"
  } | tee -a "$BENCH_RUN_DIR/run.env.summary"
fi

if [[ "${COCOA_PREPARE_ONLY:-0}" == "1" ]]; then
  echo "cocoa_effective_tasks_dir=$COCOA_EFFECTIVE_TASKS_DIR" | tee -a "$BENCH_RUN_DIR/run.env.summary"
  bench_finish "$COCOA_EFFECTIVE_TASKS_DIR"
  exit 0
fi

cmd=("${cocoa_python[@]}" parallel_inference.py --config "$COCOA_CONFIG" --tasks-dir "$COCOA_EFFECTIVE_TASKS_DIR" --output-dir "$COCOA_OUTPUT_DIR" --work-dir "$COCOA_WORK_DIR" --workers "$COCOA_WORKERS" --model "$MODEL_NAME")

if [[ "${COCOA_RUN_ALL:-0}" == "1" ]]; then
  cmd+=(--run-all)
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/cocoabench.log"

bench_finish "$COCOA_OUTPUT_DIR"
