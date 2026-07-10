#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init swebench_verified_qwen_code

QWEN_NATIVE_ROOT="${QWEN_NATIVE_ROOT:-$NIPS_ROOT/shared_bench/qwen_native_swebench}"
QWEN_NATIVE_RUNNER="${QWEN_NATIVE_RUNNER:-$QWEN_NATIVE_ROOT/scripts/run_qwen_code_swebench.py}"
QWEN_NATIVE_PYTHON="${QWEN_NATIVE_PYTHON:-/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/aci_evolve/bin/python}"
QWEN_NATIVE_SUBSET="${QWEN_NATIVE_SUBSET:-${SWEBENCH_QWEN_SUBSET:-smoke_n20}}"
QWEN_NATIVE_OUT_PARENT="${QWEN_NATIVE_OUT_PARENT:-$BENCH_RUN_DIR/qwen_native_outputs}"
QWEN_NATIVE_NAMESPACE="${QWEN_NATIVE_NAMESPACE:-swebench}"
QWEN_NATIVE_QWEN_ROOT="${QWEN_NATIVE_QWEN_ROOT:-$QWEN_NATIVE_ROOT/.npm-root}"
QWEN_NATIVE_MAX_WORKERS="${QWEN_NATIVE_MAX_WORKERS:-${MAX_CONCURRENCY:-4}}"
QWEN_NATIVE_BUILD_WORKERS="${QWEN_NATIVE_BUILD_WORKERS:-${QWEN_NATIVE_MAX_WORKERS}}"
QWEN_NATIVE_AGENT_TIMEOUT_S="${QWEN_NATIVE_AGENT_TIMEOUT_S:-28800}"
QWEN_NATIVE_VERIFIER_TIMEOUT_S="${QWEN_NATIVE_VERIFIER_TIMEOUT_S:-7200}"
QWEN_NATIVE_MAX_SESSION_TURNS="${QWEN_NATIVE_MAX_SESSION_TURNS:--1}"
QWEN_NATIVE_RUN_NAME="${QWEN_NATIVE_RUN_NAME:-qwen_code_${MODEL_SLUG}_${RUN_TAG}_${QWEN_NATIVE_SUBSET}}"
OPENAI_MODEL="${OPENAI_MODEL:-$MODEL_NAME}"

bench_require_path "$QWEN_NATIVE_RUNNER" "Qwen native SWE-bench runner"
bench_require_exe "$QWEN_NATIVE_PYTHON" "Qwen native SWE-bench python"
bench_require_path "$QWEN_NATIVE_QWEN_ROOT" "Qwen Code npm root"

export OPENAI_BASE_URL
export OPENAI_API_KEY
export OPENAI_MODEL
export NO_PROXY="127.0.0.1,localhost,::1,100.96.0.0/12,100.103.11.77,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"

cmd=(
  "$QWEN_NATIVE_PYTHON"
  "$QWEN_NATIVE_RUNNER"
  --subset "$QWEN_NATIVE_SUBSET"
  --max-workers "$QWEN_NATIVE_MAX_WORKERS"
  --build-workers "$QWEN_NATIVE_BUILD_WORKERS"
  --agent-timeout-s "$QWEN_NATIVE_AGENT_TIMEOUT_S"
  --verifier-timeout-s "$QWEN_NATIVE_VERIFIER_TIMEOUT_S"
  --max-session-turns "$QWEN_NATIVE_MAX_SESSION_TURNS"
  --max-output-tokens "$MAX_TOKENS"
  --base-url "$OPENAI_BASE_URL"
  --api-key "$OPENAI_API_KEY"
  --model "$OPENAI_MODEL"
  --qwen-root "$QWEN_NATIVE_QWEN_ROOT"
  --out-parent "$QWEN_NATIVE_OUT_PARENT"
  --namespace "$QWEN_NATIVE_NAMESPACE"
  --run-name "$QWEN_NATIVE_RUN_NAME"
)

if [[ "${QWEN_NATIVE_PULL_MISSING:-0}" == "1" ]]; then
  cmd+=(--pull-missing)
fi
if [[ "${QWEN_NATIVE_INCLUDE_TEST_NAMES:-0}" == "1" ]]; then
  cmd+=(--include-test-names)
fi
if [[ "${QWEN_NATIVE_SKIP_EXISTING:-0}" == "1" ]]; then
  cmd+=(--skip-existing)
fi
if [[ "${QWEN_NATIVE_PREPARE_ONLY:-0}" == "1" ]]; then
  cmd+=(--prepare-only)
fi
if [[ -n "${QWEN_NATIVE_INSTANCE_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  instance_ids=( $QWEN_NATIVE_INSTANCE_IDS )
  for instance_id in "${instance_ids[@]}"; do
    cmd+=(--instance-id "$instance_id")
  done
fi
if [[ -n "${QWEN_NATIVE_LIMIT:-}" ]]; then
  cmd+=(--limit "$QWEN_NATIVE_LIMIT")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/swebench_verified_qwen_code.log"

bench_finish "$QWEN_NATIVE_OUT_PARENT/$QWEN_NATIVE_RUN_NAME"
