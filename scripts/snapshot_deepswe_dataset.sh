#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="https://github.com/datacurve-ai/deep-swe"
SOURCE_COMMIT="578129c"
DATA_VERSION="v1.1"
EXPECTED_TASK_COUNT=113
OUTPUT_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench"
SOURCE_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_deepswe_dataset.sh [--dry-run] [--output-root DIR] [--source-root DIR]

Snapshots the local DeepSWE v1.1 task corpus into:

  <output-root>/deepswe-v1.1/

The script is pinned to the public DeepSWE source contract from the feasibility
report. It does not download in dry-run mode. Non-dry-run copies the already
materialized shared checkout and writes METADATA.json plus SHA256SUMS.
EOF
}

emit_plan_json() {
  local status="$1"
  local dataset_dir="$OUTPUT_ROOT/deepswe-$DATA_VERSION"
  cat <<EOF
{
  "status": "$status",
  "bench_id": "deepswe",
  "source_repo": "$SOURCE_REPO",
  "source_commit": "$SOURCE_COMMIT",
  "data_version": "$DATA_VERSION",
  "source_root": "$SOURCE_ROOT",
  "dataset_dir": "$dataset_dir",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "language_counts": {"TypeScript": 35, "Go": 34, "Python": 34, "Rust": 5, "JavaScript": 5},
  "sha256_manifest": "$dataset_dir/SHA256SUMS",
  "layout": {
    "tasks": "$dataset_dir/tasks",
    "metadata": "$dataset_dir/METADATA.json"
  }
}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --output-root)
      OUTPUT_ROOT="${2:?missing value for --output-root}"
      shift 2
      ;;
    --source-root)
      SOURCE_ROOT="${2:?missing value for --source-root}"
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

if [[ "$DRY_RUN" == "1" ]]; then
  emit_plan_json dry_run
  exit 0
fi

if [[ ! -d "$SOURCE_ROOT/tasks" ]]; then
  echo "DeepSWE source task root missing: $SOURCE_ROOT/tasks" >&2
  exit 66
fi

actual_commit="$(git -C "$SOURCE_ROOT" rev-parse --short HEAD 2>/dev/null || true)"
if [[ "$actual_commit" != "$SOURCE_COMMIT" ]]; then
  echo "DeepSWE source commit mismatch: expected $SOURCE_COMMIT got ${actual_commit:-unknown}" >&2
  exit 65
fi

actual_count="$(find "$SOURCE_ROOT/tasks" -mindepth 2 -maxdepth 2 -name task.toml | wc -l | tr -d ' ')"
if [[ "$actual_count" != "$EXPECTED_TASK_COUNT" ]]; then
  echo "DeepSWE task count mismatch: expected $EXPECTED_TASK_COUNT got $actual_count" >&2
  exit 65
fi

DATASET_DIR="$OUTPUT_ROOT/deepswe-$DATA_VERSION"
rm -rf "$DATASET_DIR"
mkdir -p "$DATASET_DIR"
cp -a "$SOURCE_ROOT/tasks" "$DATASET_DIR/tasks"
cat > "$DATASET_DIR/METADATA.json" <<EOF
{
  "bench_id": "deepswe",
  "source_repo": "$SOURCE_REPO",
  "source_commit": "$SOURCE_COMMIT",
  "data_version": "$DATA_VERSION",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "language_counts": {"TypeScript": 35, "Go": 34, "Python": 34, "Rust": 5, "JavaScript": 5},
  "tasks": "tasks"
}
EOF
(
  cd "$DATASET_DIR"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

emit_plan_json snapshot_complete
