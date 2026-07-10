#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/bench_common.sh"
bench_init tau2_paper_core

export NUM_TASKS="${NUM_TASKS:-all}"
export NUM_TRIALS="${NUM_TRIALS:-4}"
export MAX_CONCURRENCY="${MAX_CONCURRENCY:-2}"
export TAU2_TASK_SPLIT_NAME="${TAU2_TASK_SPLIT_NAME:-base}"

for domain in airline retail telecom; do
  child_dir="$BENCH_RUN_DIR/$domain"
  mkdir -p "$child_dir"
  env \
    BENCH_RUN_DIR="$child_dir" \
    TAU2_DOMAIN="$domain" \
    TAU2_SAVE_TO="bench_${MODEL_SLUG}_tau2_${domain}_${RUN_TAG}" \
    "$SCRIPT_DIR/run_tau2.sh"
done

bench_finish "$BENCH_RUN_DIR"
