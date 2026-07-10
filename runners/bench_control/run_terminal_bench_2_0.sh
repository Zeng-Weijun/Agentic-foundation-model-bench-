#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export TB_2_0_SOURCE_PATH="${TB_2_0_SOURCE_PATH:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.0}"
export TB_DATASET_PATH="${TB_DATASET_PATH:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.0-yaml}"
export TB_DATASET_NAME="${TB_DATASET_NAME:-terminal-bench}"
export TB_DATASET_VERSION="${TB_DATASET_VERSION:-2.0}"
export NUM_TASKS="${NUM_TASKS:-all}"

if [[ -z "${PYTHON_BIN:-}" && -x /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/python3 ]]; then
  export PYTHON_BIN=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/python3
fi

"$SCRIPT_DIR/scripts/build_terminal_bench_2_0_yaml_dataset.sh" "$TB_2_0_SOURCE_PATH" "$TB_DATASET_PATH"

exec "$SCRIPT_DIR/run_terminal_bench.sh" "$@"
