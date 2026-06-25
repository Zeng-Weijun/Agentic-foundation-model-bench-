#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PORT="${BENCH_PROXY_PORT:-18540}"
BIND="${BENCH_PROXY_BIND:-0.0.0.0}"
UPSTREAM="${BENCH_PROXY_UPSTREAM:-http://8.130.49.170}"
LOG="${BENCH_PROXY_LOG:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/dev_relay_proxy_${PORT}.log}"

mkdir -p "$(dirname "$LOG")"
export BENCH_PROXY_LOG="$LOG"
exec python3 "$SCRIPT_DIR/openai_relay_proxy.py" \
  --bind "$BIND" \
  --port "$PORT" \
  --upstream "$UPSTREAM"
