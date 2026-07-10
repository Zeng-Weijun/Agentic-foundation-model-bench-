#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/bench_common.sh"
bench_init vitabench_full

export NUM_TASKS="${NUM_TASKS:-all}"
export NUM_TRIALS="${NUM_TRIALS:-1}"
export MAX_CONCURRENCY="${MAX_CONCURRENCY:-2}"
export VITA_MAX_STEPS="${VITA_MAX_STEPS:-300}"
export VITA_ENABLE_THINK="${VITA_ENABLE_THINK:-1}"
export VITA_LANGUAGE="${VITA_LANGUAGE:-english}"

run_domain() {
  local domain="$1"
  local task_set="$2"
  local child_dir="$BENCH_RUN_DIR/$task_set"
  mkdir -p "$child_dir"
  env \
    BENCH_RUN_DIR="$child_dir" \
    VITA_DOMAIN="$domain" \
    VITA_TASK_SET_NAME="$task_set" \
    VITA_SAVE_TO="bench_${MODEL_SLUG}_vita_${task_set}_${RUN_TAG}" \
    "$SCRIPT_DIR/run_vitabench.sh"
}

run_domain delivery delivery
run_domain instore instore
run_domain ota ota
run_domain delivery,ota,instore cross_domain

bench_finish "$BENCH_RUN_DIR"
