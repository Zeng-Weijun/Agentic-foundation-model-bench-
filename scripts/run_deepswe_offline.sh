#!/usr/bin/env bash
set -euo pipefail

MODE="${DEEPSWE_MODE:-smoke}"
TASK_ID="${DEEPSWE_TASK_ID:-}"
MAX_TASKS="${DEEPSWE_MAX_TASKS:-}"
MAX_WORKERS="${DEEPSWE_MAX_WORKERS:-1}"
DATASET_DIR="${DEEPSWE_DATASET_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/deepswe-v1.1}"
OUTPUT_DIR="${DEEPSWE_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/deepswe_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
AGENT="${DEEPSWE_AGENT:-mini-swe-agent}"
MODEL="${DEEPSWE_MODEL:-}"
OPENAI_BASE_URL="${DEEPSWE_OPENAI_BASE_URL:-${OPENAI_BASE_URL:-}}"
IMAGE_MANIFEST="${DEEPSWE_IMAGE_MANIFEST:-manifests/images/deepswe.yaml}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_deepswe_offline.sh [--dry-run] [--mode smoke|full] [--task-id ID] [--max-tasks N] [--max-workers N]

Fail-closed DeepSWE offline runner skeleton. Standard scaffold is Pier with
mini-swe-agent. The agent model must use the approved OpenAI-compatible relay;
task containers remain offline. Non-dry-run is disabled until dataset snapshot,
113 image transport proofs, worker rootless-vfs, and parser gates are wired.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --mode)
      MODE="${2:?missing value for --mode}"
      shift 2
      ;;
    --task-id)
      TASK_ID="${2:?missing value for --task-id}"
      shift 2
      ;;
    --max-tasks)
      MAX_TASKS="${2:?missing value for --max-tasks}"
      shift 2
      ;;
    --max-workers|--concurrency)
      MAX_WORKERS="${2:?missing value for --max-workers}"
      shift 2
      ;;
    --dataset-dir)
      DATASET_DIR="${2:?missing value for --dataset-dir}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

case "$MODE" in
  smoke|full) ;;
  *) echo "unsupported DeepSWE mode: $MODE" >&2; exit 64 ;;
esac

if ! [[ "$MAX_WORKERS" =~ ^[0-9]+$ ]] || [[ "$MAX_WORKERS" -lt 1 ]]; then
  echo "DEEPSWE_MAX_WORKERS must be a positive integer" >&2
  exit 64
fi
if [[ -n "$MAX_TASKS" ]] && ! [[ "$MAX_TASKS" =~ ^[0-9]+$ ]]; then
  echo "--max-tasks must be a non-negative integer" >&2
  exit 64
fi
DATASET_TASKS_EXISTS=0
if [[ -d "$DATASET_DIR/tasks" ]]; then
  DATASET_TASKS_EXISTS=1
fi

project_path="$DATASET_DIR/tasks"
if [[ -n "$TASK_ID" ]]; then
  project_path="$DATASET_DIR/tasks/$TASK_ID"
fi
planned=(pier run -p "$project_path" --agent "$AGENT" --model "${MODEL:-TODO_MODEL}" --output-dir "$OUTPUT_DIR" --max-workers "$MAX_WORKERS")
if [[ -n "$MAX_TASKS" ]]; then
  planned+=(--n-tasks "$MAX_TASKS")
fi

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'DEEPSWE_RUNNER_JSON' "$MODE" "$TASK_ID" "$MAX_TASKS" "$MAX_WORKERS" "$DATASET_DIR" "$OUTPUT_DIR" "$AGENT" "$MODEL" "$OPENAI_BASE_URL" "$IMAGE_MANIFEST" "$DATASET_TASKS_EXISTS" "${planned[@]}"
import json, sys
mode, task_id, max_tasks, max_workers, dataset_dir, output_dir = sys.argv[1:7]
agent, model, base_url, image_manifest, dataset_tasks_exists = sys.argv[7:12]
planned = sys.argv[12:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "deepswe",
    "mode": mode,
    "task_id": task_id or None,
    "max_tasks": int(max_tasks) if max_tasks else None,
    "max_workers": int(max_workers),
    "dataset_dir": dataset_dir,
    "output_dir": output_dir,
    "agent": agent,
    "model": model,
    "openai_base_url": base_url,
    "image_manifest": image_manifest,
    "dataset_tasks_exists": dataset_tasks_exists == "1",
    "planned_command": planned,
    "fail_closed_until": [
        "deepswe dataset snapshot sha256 manifest exists",
        "113 task images have P0 digest or verified fallback tar sha",
        "worker rootless-vfs preflight passes",
        "strict parser validates behavior verifier and trajectory evidence",
    ],
}, sort_keys=True))
DEEPSWE_RUNNER_JSON
  exit 0
fi

if [[ "$DATASET_TASKS_EXISTS" != "1" ]]; then
  echo "DeepSWE dataset tasks dir does not exist: $DATASET_DIR/tasks" >&2
  exit 66
fi

cat >&2 <<'EOF'
DeepSWE offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: materialize dataset snapshot, 113 image transport proofs,
rootless-vfs worker gate, relay env, and strict parser integration.
EOF
exit 78
