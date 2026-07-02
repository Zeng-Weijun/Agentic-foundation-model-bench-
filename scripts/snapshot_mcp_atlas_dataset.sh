#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
OUTPUT_ROOT="${MCP_ATLAS_OUTPUT_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets}"
SOURCE_ROOT="${MCP_ATLAS_SOURCE_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/sources/mcp-atlas}"
HF_DATASET="${MCP_ATLAS_HF_DATASET:-ScaleAI/MCP-Atlas}"
HF_REVISION="${MCP_ATLAS_HF_REVISION:-b5bcde2236c0b8772020e13dea4e481241e78677}"
PARQUET_FILE="MCP-Atlas.parquet"
CONTENT_LENGTH="${MCP_ATLAS_CONTENT_LENGTH:-15638757}"
ETAG="89dcacffef7a52ab656bee3ccea653ab754f4314c63418956b483cf620966217"
EXPECTED_TASK_COUNT="${MCP_ATLAS_EXPECTED_TASK_COUNT:-500}"
SAMPLE_TASK_COUNT="10"
SOURCE_COMMIT="b290e672645791fea0bcb23e2c0f4fec50715cca"
MAX_BYTES="${MCP_ATLAS_MAX_BYTES:-10737418240}"
METADATA_JSON=""
DOWNLOAD_BASE_URL=""

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_mcp_atlas_dataset.sh [--dry-run] [--output-root DIR]
       [--metadata-json FILE] [--download-base-url URL] [--max-bytes BYTES]

Fail-closed MCP-Atlas dataset snapshot contract for HF ScaleAI/MCP-Atlas
MCP-Atlas.parquet. Non-dry-run materializes the pinned HF parquet snapshot,
writes SHA256SUMS, verifies row_count, and refuses metadata over max-bytes.
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

DATASET_DIR="$OUTPUT_ROOT/ScaleAI-MCP-Atlas"
DATASET_PATH="$DATASET_DIR/$PARQUET_FILE"
SHA256_PATH="$DATASET_PATH.sha256"
ROW_COUNT_PATH="$DATASET_PATH.row_count.json"
SHA256_MANIFEST="$DATASET_DIR/SHA256SUMS"
METADATA_OUT="$DATASET_DIR/METADATA.json"

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'MCP_ATLAS_SNAPSHOT_JSON' "$OUTPUT_ROOT" "$SOURCE_ROOT" "$DATASET_PATH" "$SHA256_PATH" "$ROW_COUNT_PATH" "$HF_DATASET" "$HF_REVISION" "$PARQUET_FILE" "$CONTENT_LENGTH" "$ETAG" "$EXPECTED_TASK_COUNT" "$SAMPLE_TASK_COUNT" "$SOURCE_COMMIT" "$MAX_BYTES" "$SHA256_MANIFEST" "$METADATA_OUT"
import json, sys
(output_root, source_root, dataset_path, sha256_path, row_count_path, hf_dataset,
 hf_revision, parquet_file, content_length, etag, expected_task_count, sample_task_count,
 source_commit, max_bytes, sha256_manifest, metadata_out) = sys.argv[1:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "mcp_atlas",
    "source_repo": "https://github.com/scaleapi/mcp-atlas.git",
    "source_root": source_root,
    "source_commit": source_commit,
    "hf_dataset": hf_dataset,
    "hf_revision": hf_revision,
    "parquet_file": parquet_file,
    "dataset_path": dataset_path,
    "sha256_path": sha256_path,
    "sha256_manifest": sha256_manifest,
    "metadata_path": metadata_out,
    "row_count_path": row_count_path,
    "expected_task_count": int(expected_task_count),
    "sample_task_count": int(sample_task_count),
    "content_length": int(content_length),
    "max_bytes": int(max_bytes),
    "etag": etag,
    "verification_fields": ["sha256", "row_count", "content_length", "etag"],
    "planned_materialize_command": [
        "bash", "scripts/snapshot_mcp_atlas_dataset.sh",
        "--output-root", output_root,
        "--max-bytes", max_bytes,
    ],
    "fail_closed_note": "non-dry-run first checks HF metadata total bytes and refuses if it exceeds max_bytes",
}, indent=2, sort_keys=True))
MCP_ATLAS_SNAPSHOT_JSON
  exit 0
fi

python3 - <<'MCP_ATLAS_SNAPSHOT' \
  "$DATASET_DIR" "$DATASET_PATH" "$SHA256_PATH" "$ROW_COUNT_PATH" "$SHA256_MANIFEST" "$METADATA_OUT" \
  "$HF_DATASET" "$HF_REVISION" "$PARQUET_FILE" "$CONTENT_LENGTH" "$ETAG" "$EXPECTED_TASK_COUNT" \
  "$SAMPLE_TASK_COUNT" "$SOURCE_ROOT" "$SOURCE_COMMIT" "$MAX_BYTES" "$METADATA_JSON" "$DOWNLOAD_BASE_URL"
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time
import urllib.parse
import urllib.request

(
    dataset_dir,
    dataset_path,
    sha256_path,
    row_count_path,
    sha256_manifest,
    metadata_out,
    hf_dataset,
    hf_revision,
    parquet_file,
    content_length,
    etag,
    expected_task_count,
    sample_task_count,
    source_root,
    source_commit,
    max_bytes,
    metadata_json,
    download_base_url,
) = sys.argv[1:]

expected_task_count = int(expected_task_count)
sample_task_count = int(sample_task_count)
content_length = int(content_length)
max_bytes = int(max_bytes)
dataset_dir_path = Path(dataset_dir)
dataset_path = Path(dataset_path)
sha256_path = Path(sha256_path)
row_count_path = Path(row_count_path)
sha256_manifest = Path(sha256_manifest)
metadata_out = Path(metadata_out)


def fail(message: str, rc: int = 78) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(rc)


def read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    result = 0
    while True:
        if pos >= len(buf):
            raise ValueError("truncated compact varint")
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift > 70:
            raise ValueError("compact varint too long")


def zigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def read_i16(buf: bytes, pos: int) -> tuple[int, int]:
    value, pos = read_varint(buf, pos)
    return zigzag(value), pos


def skip_value(buf: bytes, pos: int, ctype: int) -> int:
    if ctype in (1, 2):
        return pos
    if ctype == 3:
        return pos + 1
    if ctype in (4, 5, 6):
        _, pos = read_varint(buf, pos)
        return pos
    if ctype == 7:
        return pos + 8
    if ctype == 8:
        length, pos = read_varint(buf, pos)
        return pos + length
    if ctype in (9, 10):
        header = buf[pos]
        pos += 1
        size = header >> 4
        elem_type = header & 0x0F
        if size == 15:
            size, pos = read_varint(buf, pos)
        for _ in range(size):
            pos = skip_value(buf, pos, elem_type)
        return pos
    if ctype == 11:
        size, pos = read_varint(buf, pos)
        if size:
            type_byte = buf[pos]
            pos += 1
            key_type = type_byte >> 4
            value_type = type_byte & 0x0F
            for _ in range(size):
                pos = skip_value(buf, pos, key_type)
                pos = skip_value(buf, pos, value_type)
        return pos
    if ctype == 12:
        last_field = 0
        while True:
            field_header = buf[pos]
            pos += 1
            ftype = field_header & 0x0F
            if ftype == 0:
                return pos
            delta = field_header >> 4
            if delta == 0:
                _, pos = read_i16(buf, pos)
            else:
                last_field += delta
            pos = skip_value(buf, pos, ftype)
    raise ValueError(f"unsupported compact thrift type {ctype}")


def parquet_num_rows(path: Path) -> int:
    with path.open("rb") as fh:
        if fh.read(4) != b"PAR1":
            raise ValueError("missing parquet header magic")
        fh.seek(-8, 2)
        footer_len = struct.unpack("<i", fh.read(4))[0]
        if fh.read(4) != b"PAR1":
            raise ValueError("missing parquet footer magic")
        fh.seek(-(8 + footer_len), 2)
        footer = fh.read(footer_len)
    pos = 0
    last_field = 0
    while True:
        header = footer[pos]
        pos += 1
        ctype = header & 0x0F
        if ctype == 0:
            raise ValueError("num_rows field not found")
        delta = header >> 4
        if delta == 0:
            field_id, pos = read_i16(footer, pos)
        else:
            field_id = last_field + delta
        last_field = field_id
        if field_id == 3 and ctype == 6:
            value, pos = read_varint(footer, pos)
            return zigzag(value)
        pos = skip_value(footer, pos, ctype)


def metadata() -> dict:
    if metadata_json:
        return json.loads(Path(metadata_json).read_text())
    quoted = urllib.parse.quote(hf_dataset, safe="/")
    url = f"https://huggingface.co/api/datasets/{quoted}/revision/{hf_revision}?blobs=true"
    req = urllib.request.Request(url, headers={"User-Agent": "mcp-atlas-snapshot/20260702"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def sibling_name(row: dict) -> str:
    name = row.get("rfilename")
    if not name or name.startswith("/") or ".." in Path(name).parts:
        fail(f"unsafe or empty rfilename: {name!r}")
    return name


def sibling_size(row: dict) -> int:
    size = row.get("size")
    if size is None:
        size = (row.get("lfs") or {}).get("size")
    if size is None:
        fail(f"missing size metadata for {row.get('rfilename')}")
    return int(size)

start = time.time()
info = metadata()
if info.get("sha") and info["sha"] != hf_revision:
    fail(f"HF metadata sha mismatch: expected {hf_revision}, got {info['sha']}")
entries = sorted([{"name": sibling_name(row), "size": sibling_size(row)} for row in info.get("siblings", [])], key=lambda row: row["name"])
if not entries:
    fail("HF metadata contains no siblings")
total_bytes = sum(row["size"] for row in entries)
if total_bytes > max_bytes:
    fail(f"HF snapshot metadata total {total_bytes} bytes exceeds max bytes {max_bytes}")
parquet_entries = [row for row in entries if row["name"] == parquet_file]
if len(parquet_entries) != 1:
    fail(f"expected exactly one {parquet_file} entry, got {len(parquet_entries)}")
if parquet_entries[0]["size"] != content_length:
    fail(f"parquet content length mismatch: expected {content_length}, got {parquet_entries[0]['size']}")

if not download_base_url:
    quoted = urllib.parse.quote(hf_dataset, safe="/")
    download_base_url = f"https://huggingface.co/datasets/{quoted}/resolve/{hf_revision}/"
if not download_base_url.endswith("/"):
    download_base_url += "/"

dataset_dir_path.mkdir(parents=True, exist_ok=True)
results = []
for row in entries:
    target = dataset_dir_path / row["name"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != row["size"]:
        tmp = target.with_name(target.name + ".part")
        tmp.unlink(missing_ok=True)
        url = download_base_url + urllib.parse.quote(row["name"], safe="/")
        req = urllib.request.Request(url, headers={"User-Agent": "mcp-atlas-snapshot/20260702"})
        with urllib.request.urlopen(req, timeout=300) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        if tmp.stat().st_size != row["size"]:
            tmp.unlink(missing_ok=True)
            fail(f"downloaded size mismatch for {row['name']}: expected {row['size']}, got {tmp.stat().st_size}")
        tmp.replace(target)
    h = hashlib.sha256()
    with target.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    results.append({"name": row["name"], "size": row["size"], "sha256": h.hexdigest()})

results.sort(key=lambda row: row["name"])
sha256_manifest.write_text("\n".join(f"{row['sha256']}  ./{row['name']}" for row in results) + "\n")
parquet_sha = next(row["sha256"] for row in results if row["name"] == parquet_file)
sha256_path.write_text(f"{parquet_sha}  {parquet_file}\n")
row_count = parquet_num_rows(dataset_path)
if row_count != expected_task_count:
    fail(f"row count mismatch: expected {expected_task_count}, got {row_count}")
row_payload = {
    "schema_version": "mcp_atlas.row_count.v1",
    "bench_id": "mcp_atlas",
    "parquet_file": parquet_file,
    "row_count": row_count,
    "expected_task_count": expected_task_count,
}
row_count_path.write_text(json.dumps(row_payload, indent=2, sort_keys=True) + "\n")
metadata_payload = {
    "schema_version": "mcp_atlas.snapshot_metadata.v1",
    "bench_id": "mcp_atlas",
    "status": "snapshot_complete",
    "hf_dataset": hf_dataset,
    "hf_revision": hf_revision,
    "metadata_sha": info.get("sha"),
    "dataset_dir": str(dataset_dir_path),
    "dataset_path": str(dataset_path),
    "sha256_path": str(sha256_path),
    "sha256_manifest": str(sha256_manifest),
    "row_count_path": str(row_count_path),
    "source_root": source_root,
    "source_commit": source_commit,
    "file_count": len(results),
    "total_bytes": total_bytes,
    "parquet_size": parquet_entries[0]["size"],
    "parquet_sha256": parquet_sha,
    "row_count": row_count,
    "expected_task_count": expected_task_count,
    "sample_task_count": sample_task_count,
    "elapsed_seconds": round(time.time() - start, 3),
}
metadata_out.write_text(json.dumps(metadata_payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(metadata_payload, sort_keys=True))
MCP_ATLAS_SNAPSHOT
