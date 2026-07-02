#!/usr/bin/env bash
set -euo pipefail

MODE="${TAU3_MODE:-smoke}"
TASK_LIMIT="${TAU3_TASK_LIMIT:-}"
CONCURRENCY="${TAU3_CONCURRENCY:-1}"
DATASET_DIR="${TAU3_DATASET_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/tau3-v1.0.0}"
OUTPUT_DIR="${TAU3_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/tau3_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
HARBOR_ROOT="${TAU3_HARBOR_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor}"
AGENT_MODEL="${TAU3_AGENT_MODEL:-${MODEL_NAME:-}}"
USER_MODEL="${TAU3_USER_MODEL:-}"
JUDGE_MODEL="${TAU3_NL_ASSERTIONS_MODEL:-}"
AGENT_BASE_URL="${TAU3_AGENT_BASE_URL:-${OPENAI_BASE_URL:-}}"
USER_BASE_URL="${TAU3_USER_BASE_URL:-${OPENAI_BASE_URL:-}}"
JUDGE_BASE_URL="${TAU3_JUDGE_BASE_URL:-${OPENAI_BASE_URL:-}}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_tau3_offline.sh [--dry-run] [--mode smoke|oracle_full|full] [--task-limit N] [--concurrency N]

Skeleton offline runner for tau3-bench. It intentionally refuses non-dry-run
execution until the full 375-task dataset snapshot, P0/fallback image transport,
rootless-vfs worker preflight, and strict parser gates are implemented.

Required model surfaces for model runs:
  TAU3_AGENT_MODEL / TAU3_AGENT_BASE_URL
  TAU3_USER_MODEL / TAU3_USER_BASE_URL
  TAU3_NL_ASSERTIONS_MODEL / TAU3_JUDGE_BASE_URL when NL assertions are enabled
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
    --task-limit)
      TASK_LIMIT="${2:?missing value for --task-limit}"
      shift 2
      ;;
    --concurrency)
      CONCURRENCY="${2:?missing value for --concurrency}"
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
  smoke|oracle_full|full) ;;
  *) echo "unsupported TAU3 mode: $MODE" >&2; exit 64 ;;
esac

if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || [[ "$CONCURRENCY" -lt 1 ]]; then
  echo "TAU3_CONCURRENCY must be a positive integer" >&2
  exit 64
fi

if [[ -n "$TASK_LIMIT" ]] && ! [[ "$TASK_LIMIT" =~ ^[0-9]+$ ]]; then
  echo "--task-limit must be a non-negative integer" >&2
  exit 64
fi

if [[ ! -d "$DATASET_DIR" ]]; then
  echo "tau3 dataset dir does not exist: $DATASET_DIR" >&2
  exit 66
fi

planned=(uv run harbor run -p "$DATASET_DIR/harbor_dataset/tau3-bench" -a "${TAU3_AGENT:-tau3_llm_agent}" -m "${AGENT_MODEL:-TODO_AGENT_MODEL}" --output-dir "$OUTPUT_DIR" --concurrency "$CONCURRENCY")
if [[ -n "$TASK_LIMIT" ]]; then
  planned+=(--task-limit "$TASK_LIMIT")
fi

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'RUNNER_JSON' "$MODE" "$TASK_LIMIT" "$CONCURRENCY" "$DATASET_DIR" "$OUTPUT_DIR" "$HARBOR_ROOT" "$AGENT_MODEL" "$USER_MODEL" "$JUDGE_MODEL" "$AGENT_BASE_URL" "$USER_BASE_URL" "$JUDGE_BASE_URL" "${planned[@]}"
import json, sys
mode, task_limit, concurrency, dataset_dir, output_dir, harbor_root = sys.argv[1:7]
agent_model, user_model, judge_model, agent_base, user_base, judge_base = sys.argv[7:13]
planned = sys.argv[13:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "tau3_bench",
    "mode": mode,
    "task_limit": int(task_limit) if task_limit else None,
    "concurrency": int(concurrency),
    "dataset_dir": dataset_dir,
    "harbor_root": harbor_root,
    "output_dir": output_dir,
    "agent_model": agent_model,
    "user_simulator_model": user_model,
    "judge_model": judge_model,
    "agent_base_url": agent_base,
    "user_simulator_base_url": user_base,
    "judge_base_url": judge_base,
    "planned_command": planned,
    "fail_closed_until": [
        "tau3 dataset snapshot sha256 manifest exists",
        "full main/runtime images have P0 digest or verified fallback tar sha",
        "worker rootless-vfs preflight passes",
        "strict parser validates reward and DB/runtime state",
    ],
}, sort_keys=True))
RUNNER_JSON
  exit 0
fi

cat >&2 <<'EOF'
tau3 offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: materialize dataset snapshot, full image transport,
rootless-vfs worker gate, dual relay env, and strict parser integration.
EOF
exit 78
