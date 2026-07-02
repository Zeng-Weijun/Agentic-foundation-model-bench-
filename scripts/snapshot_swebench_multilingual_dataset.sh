#!/usr/bin/env bash
set -euo pipefail

DATASET_ID="SWE-bench/SWE-bench_Multilingual"
HF_SHA="2b7aced941b4873e9cad3e76abbae93f481d1beb"
SPLIT="test"
DATASET_VERSION="2025-08-26"
EXPECTED_TASK_COUNT=300
REPO_COUNT=42
OUTPUT_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench"
SOURCE_URL="https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual/resolve/main/data/test-00000-of-00001.parquet"
DRY_RUN=0
SOURCE_PARQUET=""

usage() {
  cat <<'EOF'
Usage: scripts/snapshot_swebench_multilingual_dataset.sh [--dry-run] [--output-root DIR] [--source-parquet FILE]

Snapshots SWE-bench Multilingual test split into:

  <output-root>/swebench-multilingual-2025-08-26/

Dry-run performs no network or file writes. Non-dry-run either copies
--source-parquet or downloads the pinned public HF parquet using Python stdlib,
then writes METADATA.json and SHA256SUMS. Run non-dry-run only on an
internet-enabled staging host, never on offline workers.
EOF
}

emit_plan_json() {
  local status="$1"
  local dataset_dir="$OUTPUT_ROOT/swebench-multilingual-$DATASET_VERSION"
  cat <<EOF
{
  "status": "$status",
  "bench_id": "swebench_multilingual",
  "dataset_id": "$DATASET_ID",
  "hf_sha": "$HF_SHA",
  "split": "$SPLIT",
  "source_url": "$SOURCE_URL",
  "dataset_version": "$DATASET_VERSION",
  "dataset_dir": "$dataset_dir",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "repo_count": $REPO_COUNT,
  "languages": ["C", "C++", "Go", "Java", "JavaScript", "TypeScript", "PHP", "Ruby", "Rust"],
  "official_language_distribution": {"C": 30, "C++": 12, "Go": 42, "Java": 43, "JavaScript/TypeScript": 43, "PHP": 43, "Ruby": 44, "Rust": 43},
  "sha256_manifest": "$dataset_dir/SHA256SUMS",
  "layout": {
    "parquet": "$dataset_dir/data/test-00000-of-00001.parquet",
    "metadata": "$dataset_dir/METADATA.json",
    "language_manifest": "$dataset_dir/language_manifest.json",
    "row_count": "$dataset_dir/ROW_COUNT.json"
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
    --source-parquet)
      SOURCE_PARQUET="${2:?missing value for --source-parquet}"
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

DATASET_DIR="$OUTPUT_ROOT/swebench-multilingual-$DATASET_VERSION"
mkdir -p "$DATASET_DIR/data"
PARQUET="$DATASET_DIR/data/test-00000-of-00001.parquet"

if [[ -n "$SOURCE_PARQUET" ]]; then
  if [[ ! -f "$SOURCE_PARQUET" ]]; then
    echo "source parquet not found: $SOURCE_PARQUET" >&2
    exit 66
  fi
  cp "$SOURCE_PARQUET" "$PARQUET"
else
  python3 - <<'PY' "$SOURCE_URL" "$PARQUET"
import sys, urllib.request
url, out = sys.argv[1:3]
req = urllib.request.Request(url, headers={"User-Agent": "agentic-bench-snapshot"})
with urllib.request.urlopen(req, timeout=120) as resp, open(out, "wb") as fh:
    fh.write(resp.read())
PY
fi

cat > "$DATASET_DIR/METADATA.json" <<EOF
{
  "bench_id": "swebench_multilingual",
  "dataset_id": "$DATASET_ID",
  "hf_sha": "$HF_SHA",
  "split": "$SPLIT",
  "dataset_version": "$DATASET_VERSION",
  "expected_task_count": $EXPECTED_TASK_COUNT,
  "repo_count": $REPO_COUNT,
  "languages": ["C", "C++", "Go", "Java", "JavaScript", "TypeScript", "PHP", "Ruby", "Rust"],
  "official_language_distribution": {"C": 30, "C++": 12, "Go": 42, "Java": 43, "JavaScript/TypeScript": 43, "PHP": 43, "Ruby": 44, "Rust": 43},
  "parquet": "data/test-00000-of-00001.parquet"
}
EOF
python3 - <<'PY' "$DATASET_DIR/language_manifest.json"
import json, sys
payload = {
    "status": "pending_derivation_from_dataset_snapshot",
    "note": "HF rows do not contain language; derive task_id->language from official page or harness TestSpec map before enabling full run.",
    "languages": ["C", "C++", "Go", "Java", "JavaScript", "TypeScript", "PHP", "Ruby", "Rust"],
}
open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
python3 - <<'PY' "$PARQUET" "$DATASET_DIR/ROW_COUNT.json" "$EXPECTED_TASK_COUNT"
import json
import struct
import sys
from pathlib import Path

parquet_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
expected = int(sys.argv[3])
data = parquet_path.read_bytes()
if len(data) < 12 or data[:4] != b"PAR1" or data[-4:] != b"PAR1":
    raise SystemExit(f"invalid parquet magic: {parquet_path}")
meta_len = struct.unpack("<I", data[-8:-4])[0]
meta_start = len(data) - 8 - meta_len
if meta_start < 4:
    raise SystemExit(f"invalid parquet metadata length: {meta_len}")
meta = data[meta_start:meta_start + meta_len]

STOP = 0
TRUE = 1
FALSE = 2
BYTE = 3
I16 = 4
I32 = 5
I64 = 6
DOUBLE = 7
BINARY = 8
LIST = 9
SET = 10
MAP = 11
STRUCT = 12

def read_varint(buf, i):
    shift = 0
    value = 0
    while True:
        if i >= len(buf):
            raise ValueError("varint truncated")
        b = buf[i]
        i += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, i
        shift += 7
        if shift > 70:
            raise ValueError("varint too long")

def zigzag_decode(value):
    return (value >> 1) ^ -(value & 1)

def read_i(buf, i):
    raw, i = read_varint(buf, i)
    return zigzag_decode(raw), i

def skip_value(buf, i, typ):
    if typ in (TRUE, FALSE):
        return i
    if typ == BYTE:
        return i + 1
    if typ in (I16, I32, I64):
        _, i = read_varint(buf, i)
        return i
    if typ == DOUBLE:
        return i + 8
    if typ == BINARY:
        n, i = read_varint(buf, i)
        return i + n
    if typ == STRUCT:
        return skip_struct(buf, i)
    if typ in (LIST, SET):
        if i >= len(buf):
            raise ValueError("list header truncated")
        header = buf[i]
        i += 1
        elem_type = header & 0x0F
        size = header >> 4
        if size == 15:
            size, i = read_varint(buf, i)
        for _ in range(size):
            i = skip_value(buf, i, elem_type)
        return i
    if typ == MAP:
        size, i = read_varint(buf, i)
        if size == 0:
            return i
        if i >= len(buf):
            raise ValueError("map type header truncated")
        types = buf[i]
        i += 1
        key_type = types >> 4
        val_type = types & 0x0F
        for _ in range(size):
            i = skip_value(buf, i, key_type)
            i = skip_value(buf, i, val_type)
        return i
    raise ValueError(f"unsupported compact thrift type {typ}")

def skip_struct(buf, i):
    field_id = 0
    while True:
        if i >= len(buf):
            raise ValueError("struct truncated")
        header = buf[i]
        i += 1
        typ = header & 0x0F
        if typ == STOP:
            return i
        delta = header >> 4
        if delta:
            field_id += delta
        else:
            field_id, i = read_i(buf, i)
        i = skip_value(buf, i, typ)

def read_file_metadata_num_rows(buf):
    i = 0
    field_id = 0
    while True:
        if i >= len(buf):
            raise ValueError("metadata struct truncated")
        header = buf[i]
        i += 1
        typ = header & 0x0F
        if typ == STOP:
            break
        delta = header >> 4
        if delta:
            field_id += delta
        else:
            field_id, i = read_i(buf, i)
        if field_id == 3 and typ == I64:
            value, i = read_i(buf, i)
            return value
        i = skip_value(buf, i, typ)
    raise ValueError("FileMetaData.num_rows not found")

row_count = read_file_metadata_num_rows(meta)
payload = {
    "status": "verified_from_parquet_footer",
    "row_count": row_count,
    "expected_task_count": expected,
    "matches_expected": row_count == expected,
    "parquet": "data/test-00000-of-00001.parquet",
}
out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if row_count != expected:
    raise SystemExit(f"SWE-bench Multilingual row count mismatch: expected {expected} got {row_count}")
PY
(
  cd "$DATASET_DIR"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

emit_plan_json snapshot_complete
