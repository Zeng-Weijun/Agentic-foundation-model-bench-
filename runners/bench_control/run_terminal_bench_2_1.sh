#!/usr/bin/env bash
set -euo pipefail
export TB_AGENT="${TB_AGENT:-terminus-2}"
export TB_EXTRA_ARGS="${TB_EXTRA_ARGS:---no-rebuild}"
exec /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh "$@"
