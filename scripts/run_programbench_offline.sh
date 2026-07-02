#!/usr/bin/env bash
set -euo pipefail

MODE="${PROGRAMBENCH_MODE:-smoke}"
FILTER="${PROGRAMBENCH_FILTER:-}"
SLICE="${PROGRAMBENCH_SLICE:-}"
WORKERS="${PROGRAMBENCH_WORKERS:-1}"
BRANCH_WORKERS="${PROGRAMBENCH_BRANCH_WORKERS:-1}"
DOCKER_CPUS="${PROGRAMBENCH_DOCKER_CPUS:-4}"
SOURCE_ROOT="${PROGRAMBENCH_SOURCE_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/sources/ProgramBench}"
BLOB_DIR="${PROGRAMBENCH_BLOB_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/programbench/ProgramBench-Tests/de0ddfb637590c7ecb54fa0b5301f6dc7dfbcee5}"
OUTPUT_DIR="${PROGRAMBENCH_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/programbench_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
MODEL="${PROGRAMBENCH_MODEL:-${MODEL:-}}"
OPENAI_BASE_URL="${PROGRAMBENCH_OPENAI_BASE_URL:-${OPENAI_BASE_URL:-}}"
IMAGE_MANIFEST="${PROGRAMBENCH_IMAGE_MANIFEST:-manifests/images/programbench.yaml}"
DOCKER_HOST_VALUE="${DOCKER_HOST:-}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_programbench_offline.sh [--dry-run] [--mode smoke|infer|eval|summary|full] [--filter REGEX] [--slice A:B] [--workers N]

Fail-closed ProgramBench offline runner skeleton. Inference uses mini-swe-agent
`mini-extra programbench`; evaluation uses `programbench eval` with hidden
behavioral tests from PROGRAMBENCH_BLOB_DIR. Non-dry-run is disabled until the
HF test snapshot, 200 image transports, runner env/wheelhouse, and rootless-vfs
worker gate are all proven.
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
    --filter)
      FILTER="${2:?missing value for --filter}"
      shift 2
      ;;
    --slice)
      SLICE="${2:?missing value for --slice}"
      shift 2
      ;;
    --workers|--concurrency)
      WORKERS="${2:?missing value for --workers}"
      shift 2
      ;;
    --branch-workers)
      BRANCH_WORKERS="${2:?missing value for --branch-workers}"
      shift 2
      ;;
    --docker-cpus)
      DOCKER_CPUS="${2:?missing value for --docker-cpus}"
      shift 2
      ;;
    --source-root)
      SOURCE_ROOT="${2:?missing value for --source-root}"
      shift 2
      ;;
    --blob-dir)
      BLOB_DIR="${2:?missing value for --blob-dir}"
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
  smoke|infer|eval|summary|full) ;;
  *) echo "unsupported ProgramBench mode: $MODE" >&2; exit 64 ;;
esac
if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [[ "$WORKERS" -lt 1 ]]; then
  echo "PROGRAMBENCH_WORKERS must be a positive integer" >&2
  exit 64
fi
if ! [[ "$BRANCH_WORKERS" =~ ^[0-9]+$ ]] || [[ "$BRANCH_WORKERS" -lt 1 ]]; then
  echo "PROGRAMBENCH_BRANCH_WORKERS must be a positive integer" >&2
  exit 64
fi

SOURCE_EXISTS=0
BLOB_EXISTS=0
VFS_DOCKER_HOST=0
if [[ -d "$SOURCE_ROOT" ]]; then SOURCE_EXISTS=1; fi
if [[ -d "$BLOB_DIR" ]]; then BLOB_EXISTS=1; fi
if [[ "$DOCKER_HOST_VALUE" == unix:///tmp/rl-vfs/run/docker-shim.sock ]]; then VFS_DOCKER_HOST=1; fi

infer=(mini-extra programbench --model "${MODEL:-TODO_MODEL}" --workers "$WORKERS" --environment-class docker --output "$OUTPUT_DIR/agent_output" --no-public-network)
if [[ -n "$FILTER" ]]; then infer+=(--filter "$FILTER"); fi
if [[ -n "$SLICE" ]]; then infer+=(--slice "$SLICE"); fi

eval_cmd=(programbench eval "$OUTPUT_DIR/agent_output" --output "$OUTPUT_DIR/eval" --workers "$WORKERS" --branch-workers "$BRANCH_WORKERS" --docker-cpus "$DOCKER_CPUS" --image-tag task_cleanroom_v6)

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'PROGRAMBENCH_RUNNER_JSON' "$MODE" "$FILTER" "$SLICE" "$WORKERS" "$BRANCH_WORKERS" "$DOCKER_CPUS" "$SOURCE_ROOT" "$BLOB_DIR" "$OUTPUT_DIR" "$MODEL" "$OPENAI_BASE_URL" "$IMAGE_MANIFEST" "$DOCKER_HOST_VALUE" "$SOURCE_EXISTS" "$BLOB_EXISTS" "$VFS_DOCKER_HOST" "${infer[@]}" __EVAL__ "${eval_cmd[@]}"
import json, sys
mode, filter_value, slice_value, workers, branch_workers, docker_cpus = sys.argv[1:7]
source_root, blob_dir, output_dir, model, base_url, image_manifest, docker_host = sys.argv[7:14]
source_exists, blob_exists, vfs_docker_host = sys.argv[14:17]
rest = sys.argv[17:]
sep = rest.index("__EVAL__")
infer = rest[:sep]
eval_cmd = rest[sep + 1:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "programbench",
    "mode": mode,
    "filter": filter_value or None,
    "slice": slice_value or None,
    "workers": int(workers),
    "branch_workers": int(branch_workers),
    "docker_cpus": int(docker_cpus),
    "source_root": source_root,
    "source_exists": source_exists == "1",
    "blob_dir": blob_dir,
    "blob_dir_exists": blob_exists == "1",
    "output_dir": output_dir,
    "agent_scaffold": "mini-swe-agent",
    "model": model,
    "openai_base_url": base_url,
    "image_manifest": image_manifest,
    "docker_host": docker_host,
    "vfs_docker_host": vfs_docker_host == "1",
    "hidden_behavioral_tests_required": True,
    "eval_environment": {
        "PROGRAMBENCH_BLOB_DIR": blob_dir,
        "PROGRAMBENCH_HF_REVISION": "",
        "PROGRAMBENCH_DOCKER_EXECUTABLE": "docker",
    },
    "planned_infer_command": infer,
    "planned_eval_command": eval_cmd,
    "fail_closed_until": [
        "ProgramBench-Tests HF snapshot with SHA256SUMS is materialized",
        "200 official task images have P0 digest proof or verified fallback tar sha",
        "programbench/mini-swe-agent runner image or wheelhouse is verified",
        "worker rootless-vfs Docker host is verified",
        "strict parser validates submission, trajectory, eval JSON, and all active tests",
    ],
}, sort_keys=True))
PROGRAMBENCH_RUNNER_JSON
  exit 0
fi

cat >&2 <<'EOF'
ProgramBench offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: materialize ProgramBench-Tests snapshot, prove all 200
image transports, package mini-swe-agent/programbench runner env, verify
rootless-vfs Docker, and run a one-task infrastructure canary.
EOF
exit 78
