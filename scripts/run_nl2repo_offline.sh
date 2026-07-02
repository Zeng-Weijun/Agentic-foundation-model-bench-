#!/usr/bin/env bash
set -euo pipefail

MODE="${NL2REPO_MODE:-smoke}"
TASK_ID="${NL2REPO_TASK_ID:-}"
SLICE="${NL2REPO_SLICE:-}"
MAX_WORKERS="${NL2REPO_MAX_WORKERS:-1}"
DATASET_DIR="${NL2REPO_DATASET_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/nl2repo-20260702}"
WHEELHOUSE_DIR="${NL2REPO_WHEELHOUSE_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/nl2repo/wheelhouse/pending}"
OUTPUT_DIR="${NL2REPO_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/nl2repo_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
SCAFFOLD="${NL2REPO_SCAFFOLD:-openhands-headless}"
MODEL="${NL2REPO_MODEL:-}"
OPENAI_BASE_URL="${NL2REPO_OPENAI_BASE_URL:-${OPENAI_BASE_URL:-}}"
IMAGE_MANIFEST="${NL2REPO_IMAGE_MANIFEST:-manifests/images/nl2repo.yaml}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_nl2repo_offline.sh [--dry-run] [--mode smoke|full] [--task-id ID] [--slice A:B] [--max-workers N]

Fail-closed NL2Repo offline runner skeleton. Standard scaffold is OpenHands
headless over EnvCommons/NL2RepoBench. Runtime requires verified task/OpenHands
image transport, verified wheelhouse, rootless worker Docker, and relay env.
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
    --slice)
      SLICE="${2:?missing value for --slice}"
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
    --wheelhouse-dir)
      WHEELHOUSE_DIR="${2:?missing value for --wheelhouse-dir}"
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
  *) echo "unsupported NL2Repo mode: $MODE" >&2; exit 64 ;;
esac
if ! [[ "$MAX_WORKERS" =~ ^[0-9]+$ ]] || [[ "$MAX_WORKERS" -lt 1 ]]; then
  echo "NL2REPO_MAX_WORKERS must be a positive integer" >&2
  exit 64
fi

DATASET_EXISTS=0
WHEELHOUSE_EXISTS=0
if [[ -d "$DATASET_DIR" ]]; then DATASET_EXISTS=1; fi
if [[ -d "$WHEELHOUSE_DIR" ]]; then WHEELHOUSE_EXISTS=1; fi
planned=(openhands headless --benchmark nl2repo --dataset-dir "$DATASET_DIR" --model "${MODEL:-TODO_MODEL}" --output-dir "$OUTPUT_DIR" --max-workers "$MAX_WORKERS" --no-public-network --wheelhouse "$WHEELHOUSE_DIR")
if [[ -n "$TASK_ID" ]]; then planned+=(--task-id "$TASK_ID"); fi
if [[ -n "$SLICE" ]]; then planned+=(--slice "$SLICE"); fi

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'NL2REPO_RUNNER_JSON' "$MODE" "$TASK_ID" "$SLICE" "$MAX_WORKERS" "$DATASET_DIR" "$WHEELHOUSE_DIR" "$OUTPUT_DIR" "$SCAFFOLD" "$MODEL" "$OPENAI_BASE_URL" "$IMAGE_MANIFEST" "$DATASET_EXISTS" "$WHEELHOUSE_EXISTS" "${planned[@]}"
import json, sys
mode, task_id, slice_value, max_workers, dataset_dir, wheelhouse_dir, output_dir = sys.argv[1:8]
scaffold, model, base_url, image_manifest, dataset_exists, wheelhouse_exists = sys.argv[8:14]
planned = sys.argv[14:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "nl2repo",
    "mode": mode,
    "task_id": task_id or None,
    "slice": slice_value or None,
    "max_workers": int(max_workers),
    "dataset_dir": dataset_dir,
    "dataset_exists": dataset_exists == "1",
    "wheelhouse_dir": wheelhouse_dir,
    "wheelhouse_exists": wheelhouse_exists == "1",
    "wheelhouse_required": True,
    "output_dir": output_dir,
    "scaffold": scaffold,
    "model": model,
    "openai_base_url": base_url,
    "image_manifest": image_manifest,
    "planned_command": planned,
    "fail_closed_until": [
        "nl2repo dataset and EnvCommons snapshot sha256 manifest exists",
        "108 task/OpenHands images have P0 digest or verified fallback tar sha",
        "wheelhouse manifest is verified and pip/uv no-index is enforced",
        "worker rootless-vfs preflight passes",
        "strict parser validates submit path and pytest reward",
    ],
}, sort_keys=True))
NL2REPO_RUNNER_JSON
  exit 0
fi

if [[ "$DATASET_EXISTS" != "1" ]]; then
  echo "NL2Repo dataset dir does not exist: $DATASET_DIR" >&2
  exit 66
fi
if [[ "$WHEELHOUSE_EXISTS" != "1" ]]; then
  echo "NL2Repo wheelhouse dir does not exist: $WHEELHOUSE_DIR" >&2
  exit 66
fi
cat >&2 <<'EOF'
NL2Repo offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: materialize dataset snapshot, 108 image transport proofs,
verified wheelhouse/no-index env, rootless-vfs worker gate, relay env, and strict parser.
EOF
exit 78
