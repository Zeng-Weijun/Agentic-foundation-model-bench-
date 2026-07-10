#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export BENCH_MODEL_PROFILE="${BENCH_MODEL_PROFILE:-gpt54mini_8130}"
export SUITE_CONCURRENCY="${SUITE_CONCURRENCY:-3}"
exec "$SCRIPT_DIR/run_smoke_suite.sh" "$@"
