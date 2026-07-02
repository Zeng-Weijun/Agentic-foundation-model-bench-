#!/usr/bin/env bash
set -euo pipefail

MODE="${SWEML_MODE:-smoke}"
SLICE="${SWEML_SLICE:-}"
INSTANCE_IDS="${SWEML_INSTANCE_IDS:-}"
MAX_WORKERS="${SWEML_MAX_WORKERS:-1}"
DATASET_DIR="${SWEML_DATASET_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swebench-multilingual-2025-08-26}"
OUTPUT_DIR="${SWEML_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swebench_multilingual_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
SCAFFOLD="${SWEML_SCAFFOLD:-mini-swe-agent}"
MODEL="${SWEML_MODEL:-}"
OPENAI_BASE_URL="${SWEML_OPENAI_BASE_URL:-${OPENAI_BASE_URL:-}}"
IMAGE_MANIFEST="${SWEML_IMAGE_MANIFEST:-manifests/images/swemultilingual.yaml}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_swebench_multilingual_offline.sh [--dry-run] [--mode smoke|gold|full] [--slice A:B] [--instance-ids CSV] [--max-workers N]

Fail-closed SWE-bench Multilingual offline runner skeleton. Default scaffold is
mini-swe-agent, using the common SWE-bench harness semantics and approved model
relay. Non-dry-run is disabled until dataset snapshot, 300 image transports,
gold-patch canary, worker rootless-vfs, and strict parser gates are wired.
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
    --slice)
      SLICE="${2:?missing value for --slice}"
      shift 2
      ;;
    --instance-ids)
      INSTANCE_IDS="${2:?missing value for --instance-ids}"
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
  smoke|gold|full) ;;
  *) echo "unsupported SWE-Multilingual mode: $MODE" >&2; exit 64 ;;
esac
if ! [[ "$MAX_WORKERS" =~ ^[0-9]+$ ]] || [[ "$MAX_WORKERS" -lt 1 ]]; then
  echo "SWEML_MAX_WORKERS must be a positive integer" >&2
  exit 64
fi

DATASET_EXISTS=0
if [[ -d "$DATASET_DIR" ]]; then
  DATASET_EXISTS=1
fi

planned=(mini-swe-agent run-swebench --dataset-path "$DATASET_DIR" --split test --model "${MODEL:-TODO_MODEL}" --output-dir "$OUTPUT_DIR" --workers "$MAX_WORKERS")
if [[ -n "$SLICE" ]]; then
  planned+=(--slice "$SLICE")
fi
if [[ -n "$INSTANCE_IDS" ]]; then
  planned+=(--instance-ids "$INSTANCE_IDS")
fi

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'SWEML_RUNNER_JSON' "$MODE" "$SLICE" "$INSTANCE_IDS" "$MAX_WORKERS" "$DATASET_DIR" "$OUTPUT_DIR" "$SCAFFOLD" "$MODEL" "$OPENAI_BASE_URL" "$IMAGE_MANIFEST" "$DATASET_EXISTS" "${planned[@]}"
import json, sys
mode, slice_value, instance_ids, max_workers, dataset_dir, output_dir = sys.argv[1:7]
scaffold, model, base_url, image_manifest, dataset_exists = sys.argv[7:12]
planned = sys.argv[12:]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "swebench_multilingual",
    "mode": mode,
    "slice": slice_value or None,
    "instance_ids": instance_ids or None,
    "max_workers": int(max_workers),
    "dataset_dir": dataset_dir,
    "dataset_exists": dataset_exists == "1",
    "output_dir": output_dir,
    "scaffold": scaffold,
    "model": model,
    "openai_base_url": base_url,
    "image_manifest": image_manifest,
    "planned_command": planned,
    "fail_closed_until": [
        "swebench multilingual dataset snapshot sha256 manifest exists",
        "300 instance images have P0 digest or verified fallback tar sha",
        "gold-patch canary passes",
        "worker rootless-vfs preflight passes",
        "strict parser validates FAIL_TO_PASS and PASS_TO_PASS",
    ],
}, sort_keys=True))
SWEML_RUNNER_JSON
  exit 0
fi

if [[ "$DATASET_EXISTS" != "1" ]]; then
  echo "SWE-Multilingual dataset dir does not exist: $DATASET_DIR" >&2
  exit 66
fi
cat >&2 <<'EOF'
SWE-bench Multilingual offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: materialize dataset snapshot, 300 image transport proofs,
gold-patch validation, rootless-vfs worker gate, relay env, and strict parser.
EOF
exit 78
