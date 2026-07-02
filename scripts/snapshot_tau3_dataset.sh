#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="https://github.com/sierra-research/tau2-bench.git"
SOURCE_REF="v1.0.0"
SOURCE_COMMIT="17e07b1da2bbc0cadfddeea36412686e0604127b"
VERSION="v1.0.0"
EXPECTED_TASK_COUNT=375
OUTPUT_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench"
TMP_ROOT="${TMPDIR:-/data/tmp}/tau3-snapshot"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_tau3_dataset.sh [--dry-run] [--output-root DIR] [--tmp-root DIR]

Snapshots the official tau3 dataset source from sierra-research/tau2-bench at
v1.0.0 / 17e07b1da2bbc0cadfddeea36412686e0604127b into:

  <output-root>/tau3-v1.0.0/

The non-dry-run path performs network git fetch/clone and is intended only for
an internet-enabled dev host. It writes SHA256SUMS for the copied snapshot.
EOF
}

emit_plan_json() {
  local status="$1"
  local dataset_dir="$OUTPUT_ROOT/tau3-$VERSION"
  cat <<EOF
{
  "status": "$status",
  "bench_id": "tau3_bench",
  "source_repo": "$SOURCE_REPO",
  "source_ref": "$SOURCE_REF",
  "source_commit": "$SOURCE_COMMIT",
  "dataset_dir": "$dataset_dir",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "domain_counts": {"airline": 50, "retail": 114, "telecom": 114, "banking_knowledge": 97},
  "sha256_manifest": "$dataset_dir/SHA256SUMS",
  "layout": {
    "source_checkout": "$dataset_dir/source/tau2-bench",
    "official_data": "$dataset_dir/official_data/tau2",
    "harbor_dataset": "$dataset_dir/harbor_dataset/tau3-bench",
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
    --tmp-root)
      TMP_ROOT="${2:?missing value for --tmp-root}"
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

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 69
fi

DATASET_DIR="$OUTPUT_ROOT/tau3-$VERSION"
SRC_DIR="$DATASET_DIR/source/tau2-bench"
OFFICIAL_DIR="$DATASET_DIR/official_data/tau2"
HARBOR_DST="$DATASET_DIR/harbor_dataset/tau3-bench"
HARBOR_SRC="/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench"

mkdir -p "$DATASET_DIR/source" "$DATASET_DIR/official_data" "$DATASET_DIR/harbor_dataset" "$TMP_ROOT"

if [[ ! -d "$SRC_DIR/.git" ]]; then
  rm -rf "$SRC_DIR"
  git clone --branch "$SOURCE_REF" --depth 1 "$SOURCE_REPO" "$SRC_DIR"
fi

git -C "$SRC_DIR" fetch --depth 1 origin "$SOURCE_COMMIT" || true
git -C "$SRC_DIR" checkout --detach "$SOURCE_COMMIT"
actual_commit="$(git -C "$SRC_DIR" rev-parse HEAD)"
if [[ "$actual_commit" != "$SOURCE_COMMIT" ]]; then
  echo "source commit mismatch: expected $SOURCE_COMMIT got $actual_commit" >&2
  exit 65
fi

rm -rf "$OFFICIAL_DIR"
mkdir -p "$OFFICIAL_DIR"
cp -a "$SRC_DIR/data/tau2/." "$OFFICIAL_DIR/"

if [[ -d "$HARBOR_SRC" ]]; then
  rm -rf "$HARBOR_DST"
  mkdir -p "$HARBOR_DST"
  cp -a "$HARBOR_SRC/." "$HARBOR_DST/"
else
  echo "warning: Harbor generated dataset not found at $HARBOR_SRC" >&2
fi

cat > "$DATASET_DIR/METADATA.json" <<EOF
{
  "bench_id": "tau3_bench",
  "version": "$VERSION",
  "source_repo": "$SOURCE_REPO",
  "source_ref": "$SOURCE_REF",
  "source_commit": "$SOURCE_COMMIT",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "domain_counts": {"airline": 50, "retail": 114, "telecom": 114, "banking_knowledge": 97},
  "official_data": "official_data/tau2",
  "harbor_dataset": "harbor_dataset/tau3-bench"
}
EOF

(
  cd "$DATASET_DIR"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

emit_plan_json snapshot_complete
