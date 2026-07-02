#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
OUTPUT_ROOT="${PROGRAMBENCH_OUTPUT_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/programbench}"
SOURCE_ROOT="${PROGRAMBENCH_SOURCE_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/sources/ProgramBench}"
HF_DATASET="${PROGRAMBENCH_HF_DATASET:-programbench/ProgramBench-Tests}"
HF_REVISION="${PROGRAMBENCH_HF_REVISION:-de0ddfb637590c7ecb54fa0b5301f6dc7dfbcee5}"
EXPECTED_TASK_COUNT="${PROGRAMBENCH_EXPECTED_TASK_COUNT:-200}"
EXPECTED_TEST_ARCHIVE_COUNT="${PROGRAMBENCH_EXPECTED_TEST_ARCHIVE_COUNT:-1832}"
EXCLUDED_FIXTURE="${PROGRAMBENCH_EXCLUDED_FIXTURE:-testorg__calculator.abc1234}"
SOURCE_COMMIT="${PROGRAMBENCH_SOURCE_COMMIT:-31952f0c261db73f1f864542e8aa1cb3d010c817}"
MAX_BYTES="${PROGRAMBENCH_MAX_BYTES:-10737418240}"
METADATA_JSON=""
DOWNLOAD_BASE_URL=""
DOWNLOAD_WORKERS="${PROGRAMBENCH_DOWNLOAD_WORKERS:-4}"

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_programbench_tests.sh [--dry-run] [--output-root DIR] [--source-root DIR]
       [--metadata-json FILE] [--download-base-url URL] [--max-bytes BYTES] [--workers N]

Fail-closed ProgramBench HF ProgramBench-Tests snapshot contract. Dry-run prints
shared-storage layout and command shape. Non-dry-run materializes the pinned HF
snapshot with Python standard library only, writes SHA256SUMS, and generates the
official task manifest while excluding the local test fixture.
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
    --metadata-json)
      METADATA_JSON="${2:?missing value for --metadata-json}"
      shift 2
      ;;
    --download-base-url)
      DOWNLOAD_BASE_URL="${2:?missing value for --download-base-url}"
      shift 2
      ;;
    --max-bytes)
      MAX_BYTES="${2:?missing value for --max-bytes}"
      shift 2
      ;;
    --workers)
      DOWNLOAD_WORKERS="${2:?missing value for --workers}"
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

DATASET_DIR="$OUTPUT_ROOT/ProgramBench-Tests/$HF_REVISION"
SHA256_MANIFEST="$DATASET_DIR/SHA256SUMS"
TASK_MANIFEST="$DATASET_DIR/programbench_full200_tasks.json"
METADATA_OUT="$DATASET_DIR/METADATA.json"

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'PROGRAMBENCH_SNAPSHOT_JSON' "$OUTPUT_ROOT" "$SOURCE_ROOT" "$DATASET_DIR" "$SHA256_MANIFEST" "$TASK_MANIFEST" "$HF_DATASET" "$HF_REVISION" "$EXPECTED_TASK_COUNT" "$EXPECTED_TEST_ARCHIVE_COUNT" "$EXCLUDED_FIXTURE" "$SOURCE_COMMIT" "$MAX_BYTES"
import json, sys
(output_root, source_root, dataset_dir, sha256_manifest, task_manifest, hf_dataset,
 hf_revision, expected_task_count, expected_test_archive_count, excluded_fixture,
 source_commit, max_bytes) = sys.argv[1:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "programbench",
    "source_repo": "https://github.com/facebookresearch/ProgramBench",
    "source_root": source_root,
    "source_commit": source_commit,
    "hf_dataset": hf_dataset,
    "hf_revision": hf_revision,
    "expected_task_count": int(expected_task_count),
    "expected_test_archive_count": int(expected_test_archive_count),
    "excluded_fixture": excluded_fixture,
    "dataset_dir": dataset_dir,
    "sha256_manifest": sha256_manifest,
    "task_manifest": task_manifest,
    "max_bytes": int(max_bytes),
    "dockerhub_namespace": "programbench",
    "docker_tag": "task_cleanroom_v6",
    "planned_materialize_command": [
        "bash", "scripts/snapshot_programbench_tests.sh",
        "--output-root", output_root,
        "--max-bytes", max_bytes,
    ],
    "fail_closed_note": "non-dry-run first checks HF metadata total bytes and refuses if it exceeds max_bytes",
}, indent=2, sort_keys=True))
PROGRAMBENCH_SNAPSHOT_JSON
  exit 0
fi

python3 - <<'PROGRAMBENCH_SNAPSHOT' \
  "$OUTPUT_ROOT" "$SOURCE_ROOT" "$DATASET_DIR" "$SHA256_MANIFEST" "$TASK_MANIFEST" "$METADATA_OUT" \
  "$HF_DATASET" "$HF_REVISION" "$EXPECTED_TASK_COUNT" "$EXPECTED_TEST_ARCHIVE_COUNT" "$EXCLUDED_FIXTURE" \
  "$SOURCE_COMMIT" "$MAX_BYTES" "$METADATA_JSON" "$DOWNLOAD_BASE_URL" "$DOWNLOAD_WORKERS"
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.parse
import urllib.request

(
    output_root,
    source_root,
    dataset_dir,
    sha256_manifest,
    task_manifest,
    metadata_out,
    hf_dataset,
    hf_revision,
    expected_task_count,
    expected_test_archive_count,
    excluded_fixture,
    source_commit,
    max_bytes,
    metadata_json,
    download_base_url,
    download_workers,
) = sys.argv[1:]

expected_task_count = int(expected_task_count)
expected_test_archive_count = int(expected_test_archive_count)
max_bytes = int(max_bytes)
download_workers = max(1, int(download_workers))
dataset_path = Path(dataset_dir)
sha_path = Path(sha256_manifest)
task_manifest_path = Path(task_manifest)
metadata_path = Path(metadata_out)
source_path = Path(source_root)


def fail(message: str, rc: int = 78) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(rc)


def open_json_url(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "programbench-snapshot/20260702"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def load_metadata() -> dict:
    if metadata_json:
        return json.loads(Path(metadata_json).read_text())
    quoted_dataset = urllib.parse.quote(hf_dataset, safe="/")
    url = f"https://huggingface.co/api/datasets/{quoted_dataset}/revision/{hf_revision}?blobs=true"
    return open_json_url(url)


def sibling_size(row: dict) -> int:
    value = row.get("size")
    if value is None:
        value = (row.get("lfs") or {}).get("size")
    if value is None:
        fail(f"missing size metadata for {row.get('rfilename')}")
    return int(value)


def sibling_name(row: dict) -> str:
    name = row.get("rfilename")
    if not name or name.startswith("/") or ".." in Path(name).parts:
        fail(f"unsafe or empty rfilename in HF metadata: {name!r}")
    return name


metadata = load_metadata()
if metadata.get("sha") and metadata["sha"] != hf_revision:
    fail(f"HF metadata sha mismatch: expected {hf_revision}, got {metadata['sha']}")

siblings = sorted(metadata.get("siblings") or [], key=lambda row: sibling_name(row))
if not siblings:
    fail("HF metadata contains no siblings")

entries = []
for row in siblings:
    name = sibling_name(row)
    size = sibling_size(row)
    entries.append({"name": name, "size": size})

total_bytes = sum(row["size"] for row in entries)
if total_bytes > max_bytes:
    fail(f"HF snapshot metadata total {total_bytes} bytes exceeds max bytes {max_bytes}")

task_ids = sorted({row["name"].split("/", 1)[0] for row in entries if "/" in row["name"] and not row["name"].startswith(".")})
if excluded_fixture in task_ids:
    task_ids.remove(excluded_fixture)

test_archive_count = sum(1 for row in entries if row["name"].endswith(".tar.gz") and "/tests/" in row["name"])
if len(task_ids) != expected_task_count:
    fail(f"task count mismatch: expected {expected_task_count}, got {len(task_ids)}")
if test_archive_count != expected_test_archive_count:
    fail(f"test archive count mismatch: expected {expected_test_archive_count}, got {test_archive_count}")

if not download_base_url:
    quoted_dataset = urllib.parse.quote(hf_dataset, safe="/")
    download_base_url = f"https://huggingface.co/datasets/{quoted_dataset}/resolve/{hf_revision}/"
if not download_base_url.endswith("/"):
    download_base_url += "/"

dataset_path.mkdir(parents=True, exist_ok=True)


def url_for(name: str) -> str:
    return download_base_url + urllib.parse.quote(name, safe="/")


def download_one(row: dict) -> dict:
    name = row["name"]
    expected_size = row["size"]
    target = dataset_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == expected_size:
        pass
    else:
        tmp = target.with_name(target.name + ".part")
        if tmp.exists():
            tmp.unlink()
        req = urllib.request.Request(url_for(name), headers={"User-Agent": "programbench-snapshot/20260702"})
        with urllib.request.urlopen(req, timeout=300) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        actual_size = tmp.stat().st_size
        if actual_size != expected_size:
            tmp.unlink(missing_ok=True)
            fail(f"downloaded size mismatch for {name}: expected {expected_size}, got {actual_size}")
        tmp.replace(target)
    h = hashlib.sha256()
    with target.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return {"name": name, "size": expected_size, "sha256": h.hexdigest()}

start = time.time()
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=download_workers) as pool:
    futures = {pool.submit(download_one, row): row for row in entries}
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())

results.sort(key=lambda row: row["name"])
sha_lines = [f"{row['sha256']}  ./{row['name']}" for row in results]
sha_path.write_text("\n".join(sha_lines) + "\n")

by_task = {task_id: {"task_id": task_id, "file_count": 0, "test_archive_count": 0, "bytes": 0} for task_id in task_ids}
for row in entries:
    if "/" not in row["name"]:
        continue
    task_id = row["name"].split("/", 1)[0]
    if task_id == excluded_fixture or task_id not in by_task:
        continue
    by_task[task_id]["file_count"] += 1
    by_task[task_id]["bytes"] += row["size"]
    if row["name"].endswith(".tar.gz") and "/tests/" in row["name"]:
        by_task[task_id]["test_archive_count"] += 1

task_manifest_payload = {
    "schema_version": "programbench.tests_snapshot.v1",
    "bench_id": "programbench",
    "status": "snapshot_complete",
    "hf_dataset": hf_dataset,
    "hf_revision": hf_revision,
    "source_repo": "https://github.com/facebookresearch/ProgramBench",
    "source_root": source_root,
    "source_commit": source_commit,
    "excluded_fixture": excluded_fixture,
    "task_count": len(task_ids),
    "expected_task_count": expected_task_count,
    "test_archive_count": test_archive_count,
    "expected_test_archive_count": expected_test_archive_count,
    "total_bytes": total_bytes,
    "tasks": [by_task[task_id] for task_id in task_ids],
}
task_manifest_path.write_text(json.dumps(task_manifest_payload, indent=2, sort_keys=True) + "\n")

metadata_payload = {
    "schema_version": "programbench.snapshot_metadata.v1",
    "bench_id": "programbench",
    "status": "snapshot_complete",
    "hf_dataset": hf_dataset,
    "hf_revision": hf_revision,
    "metadata_sha": metadata.get("sha"),
    "source_root": source_root,
    "source_root_exists": source_path.exists(),
    "source_commit": source_commit,
    "dataset_dir": str(dataset_path),
    "sha256_manifest": str(sha_path),
    "task_manifest": str(task_manifest_path),
    "file_count": len(results),
    "task_count": len(task_ids),
    "test_archive_count": test_archive_count,
    "total_bytes": total_bytes,
    "excluded_fixture": excluded_fixture,
    "download_workers": download_workers,
    "elapsed_seconds": round(time.time() - start, 3),
}
metadata_path.write_text(json.dumps(metadata_payload, indent=2, sort_keys=True) + "\n")

print(json.dumps(metadata_payload, sort_keys=True))
PROGRAMBENCH_SNAPSHOT
