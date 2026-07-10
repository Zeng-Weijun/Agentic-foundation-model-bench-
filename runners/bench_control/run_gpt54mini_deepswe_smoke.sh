#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export BENCH_MODEL_PROFILE="${BENCH_MODEL_PROFILE:-gpt54mini_8130}"
export DEEPSWE_MODE="${DEEPSWE_MODE:-smoke}"
export DEEPSWE_N_TASKS="${DEEPSWE_N_TASKS:-1}"
export DEEPSWE_SAMPLE_SEED="${DEEPSWE_SAMPLE_SEED:-0}"
export DEEPSWE_N_CONCURRENT="${DEEPSWE_N_CONCURRENT:-1}"
exec "$SCRIPT_DIR/run_deepswe.sh" "$@"
