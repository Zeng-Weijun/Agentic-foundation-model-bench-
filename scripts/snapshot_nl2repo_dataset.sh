#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_REPO="https://github.com/multimodal-art-projection/NL2RepoBench.git"
UPSTREAM_COMMIT="781a1da1ee41fb8edb0bed22f586d69111610edf"
ENVCOMMONS_REPO="https://github.com/EnvCommons/NL2RepoBench.git"
ENVCOMMONS_COMMIT="61d26cc0abd084ece8f5d805dcbd3f806a291f15"
TASK_COUNT_UPSTREAM=104
TASK_COUNT_ENVCOMMONS_EXECUTABLE=103
DECLARED_TEST_COUNT=25640
TASK_LIST_SHA256="88d33cf19a9e01ecbe5acee306cdeda7b148e11c821e1bc46f45d07392af197f"
SNAPSHOT_ID="20260702"
OUTPUT_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench"
UPSTREAM_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/sources/NL2RepoBench"
ENVCOMMONS_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/sources/EnvCommons-NL2RepoBench"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_nl2repo_dataset.sh [--dry-run] [--output-root DIR] [--upstream-root DIR] [--envcommons-root DIR]

Snapshots the already-materialized NL2Repo upstream and EnvCommons metadata into:

  <output-root>/nl2repo-20260702/

Dry-run performs no writes/downloads. Non-dry-run copies local shared checkouts,
records METADATA.json, and writes SHA256SUMS. It does not pip install or build.
EOF
}

emit_plan_json() {
  local status="$1"
  local dataset_dir="$OUTPUT_ROOT/nl2repo-$SNAPSHOT_ID"
  cat <<EOF
{
  "status": "$status",
  "bench_id": "nl2repo",
  "upstream_repo": "$UPSTREAM_REPO",
  "upstream_commit": "$UPSTREAM_COMMIT",
  "envcommons_repo": "$ENVCOMMONS_REPO",
  "envcommons_commit": "$ENVCOMMONS_COMMIT",
  "dataset_dir": "$dataset_dir",
  "task_count_upstream": $TASK_COUNT_UPSTREAM,
  "task_count_envcommons_executable": $TASK_COUNT_ENVCOMMONS_EXECUTABLE,
  "excluded_envcommons_task": "arxiv-mcp-server",
  "declared_test_count": $DECLARED_TEST_COUNT,
  "task_list_sha256": "$TASK_LIST_SHA256",
  "categories": ["System Tools", "Data Analysis & Processing", "Testing", "Utility Libraries", "Web Development", "Networking Tools", "Database Interaction", "Machine Learning", "Batch File Processing"],
  "sha256_manifest": "$dataset_dir/SHA256SUMS",
  "layout": {
    "upstream_test_files": "$dataset_dir/upstream/test_files",
    "envcommons_source": "$dataset_dir/envcommons",
    "task_list": "$dataset_dir/TASK_LIST.txt",
    "task_manifest": "$dataset_dir/TASK_MANIFEST.json",
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
    --upstream-root)
      UPSTREAM_ROOT="${2:?missing value for --upstream-root}"
      shift 2
      ;;
    --envcommons-root)
      ENVCOMMONS_ROOT="${2:?missing value for --envcommons-root}"
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

if [[ ! -d "$UPSTREAM_ROOT/test_files" ]]; then
  echo "NL2Repo upstream test_files missing: $UPSTREAM_ROOT/test_files" >&2
  exit 66
fi
if [[ ! -d "$ENVCOMMONS_ROOT" ]]; then
  echo "NL2Repo EnvCommons source missing: $ENVCOMMONS_ROOT" >&2
  exit 66
fi
upstream_commit="$(git -C "$UPSTREAM_ROOT" rev-parse HEAD 2>/dev/null || true)"
if [[ "$upstream_commit" != "$UPSTREAM_COMMIT" ]]; then
  echo "upstream commit mismatch: expected $UPSTREAM_COMMIT got ${upstream_commit:-unknown}" >&2
  exit 65
fi
envcommons_commit="$(git -C "$ENVCOMMONS_ROOT" rev-parse HEAD 2>/dev/null || true)"
if [[ "$envcommons_commit" != "$ENVCOMMONS_COMMIT" ]]; then
  echo "EnvCommons commit mismatch: expected $ENVCOMMONS_COMMIT got ${envcommons_commit:-unknown}" >&2
  exit 65
fi
actual_count="$(find "$UPSTREAM_ROOT/test_files" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
if [[ "$actual_count" != "$TASK_COUNT_UPSTREAM" ]]; then
  echo "task count mismatch: expected $TASK_COUNT_UPSTREAM got $actual_count" >&2
  exit 65
fi

DATASET_DIR="$OUTPUT_ROOT/nl2repo-$SNAPSHOT_ID"
rm -rf "$DATASET_DIR"
mkdir -p "$DATASET_DIR/upstream" "$DATASET_DIR/envcommons"
cp -a "$UPSTREAM_ROOT/test_files" "$DATASET_DIR/upstream/test_files"
cp -a "$ENVCOMMONS_ROOT/." "$DATASET_DIR/envcommons/"
cat > "$DATASET_DIR/METADATA.json" <<EOF
{
  "bench_id": "nl2repo",
  "upstream_repo": "$UPSTREAM_REPO",
  "upstream_commit": "$UPSTREAM_COMMIT",
  "envcommons_repo": "$ENVCOMMONS_REPO",
  "envcommons_commit": "$ENVCOMMONS_COMMIT",
  "task_count_upstream": $TASK_COUNT_UPSTREAM,
  "task_count_envcommons_executable": $TASK_COUNT_ENVCOMMONS_EXECUTABLE,
  "excluded_envcommons_task": "arxiv-mcp-server",
  "declared_test_count": $DECLARED_TEST_COUNT,
  "task_list_sha256": "$TASK_LIST_SHA256"
}
EOF
python3 - <<'NLMANIFEST' "$DATASET_DIR" "$TASK_COUNT_UPSTREAM" "$TASK_COUNT_ENVCOMMONS_EXECUTABLE" "$DECLARED_TEST_COUNT" "$TASK_LIST_SHA256"
import hashlib
import json
import sys
from pathlib import Path

dataset_dir = Path(sys.argv[1])
expected_total = int(sys.argv[2])
expected_executable = int(sys.argv[3])
expected_tests = int(sys.argv[4])
expected_sha = sys.argv[5]
source_tasks = dataset_dir / "upstream" / "test_files"
task_ids = sorted(p.name for p in source_tasks.iterdir() if p.is_dir())
if len(task_ids) != expected_total:
    raise SystemExit(f"NL2Repo task count mismatch: expected {expected_total} got {len(task_ids)}")
joined = "\n".join(task_ids)
actual_sha = hashlib.sha256(joined.encode()).hexdigest()
if actual_sha != expected_sha:
    raise SystemExit(f"NL2Repo task list sha mismatch: expected {expected_sha} got {actual_sha}")
excluded = ["arxiv-mcp-server"]
executable = [task for task in task_ids if task not in excluded]
if len(executable) != expected_executable:
    raise SystemExit(f"NL2Repo executable task count mismatch: expected {expected_executable} got {len(executable)}")
test_count = 0
missing_count_files = []
for task in task_ids:
    count_path = source_tasks / task / "test_case_count.txt"
    if not count_path.exists():
        missing_count_files.append(task)
        continue
    test_count += int(count_path.read_text().strip())
if missing_count_files:
    raise SystemExit(f"NL2Repo missing test_case_count.txt for {missing_count_files[:5]}")
if test_count != expected_tests:
    raise SystemExit(f"NL2Repo declared test count mismatch: expected {expected_tests} got {test_count}")
(dataset_dir / "TASK_LIST.txt").write_text(joined, encoding="utf-8")
manifest = {
    "status": "verified_from_upstream_test_files",
    "task_count_upstream": len(task_ids),
    "task_count_envcommons_executable": len(executable),
    "excluded_envcommons_task": excluded[0],
    "declared_test_count": test_count,
    "task_list_sha256": actual_sha,
    "task_ids": task_ids,
    "executable_task_ids": executable,
}
(dataset_dir / "TASK_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
NLMANIFEST
(
  cd "$DATASET_DIR"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

emit_plan_json snapshot_complete
