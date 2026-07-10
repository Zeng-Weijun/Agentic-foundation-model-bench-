#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init repozero_py2js

REPOZERO_ROOT="${REPOZERO_ROOT:-$NIPS_ROOT/repozero_eval/RepoZero}"
REPOZERO_MODE="${REPOZERO_MODE:-smoke}"
REPOZERO_WORKERS="${REPOZERO_WORKERS:-$MAX_CONCURRENCY}"
REPOZERO_TIMEOUT_S="${REPOZERO_TIMEOUT_S:-1200}"
REPOZERO_CODEX_ATTEMPTS="${REPOZERO_CODEX_ATTEMPTS:-1}"
REPOZERO_DOCKER_IMAGE="${REPOZERO_DOCKER_IMAGE:-ghcr.io/jessezzzzz/repoarena-new:latest}"
REPOZERO_CASE_SOURCE="${REPOZERO_CASE_SOURCE:-official}"
REPOZERO_RUN_NAME="${REPOZERO_RUN_NAME:-${MODEL_SLUG}_${RUN_TAG}_${REPOZERO_MODE}}"
bench_require_path "$REPOZERO_ROOT" "RepoZero checkout"

if [[ -z "${PACKYAPI_KEY:-}" && -n "${OPENAI_API_KEY:-}" && "$OPENAI_API_KEY" != "EMPTY" ]]; then
  export PACKYAPI_KEY="$OPENAI_API_KEY"
fi
export BASE_URL="${BASE_URL:-$OPENAI_BASE_URL}"
export API_KEY="${API_KEY:-$OPENAI_API_KEY}"

cd "$REPOZERO_ROOT"

case_args=()
cases_string=""
if [[ -n "${REPOZERO_CASES:-}" ]]; then
  cases_string="$REPOZERO_CASES"
elif [[ "$REPOZERO_MODE" == "smoke" ]]; then
  cases_string="base58/test1.py bech32/test1.py bencoder/test1.py fractions/test1.py"
fi

if [[ -n "$cases_string" ]]; then
  # shellcheck disable=SC2206
  raw_cases=( $cases_string )
  for case_name in "${raw_cases[@]}"; do
    if [[ "$case_name" != */* ]]; then
      case_name="$case_name/test1.py"
    fi
    case_args+=("$case_name")
  done
fi

if [[ -n "${REPOZERO_RUNNER:-}" ]]; then
  cmd=(python "$REPOZERO_RUNNER")
elif [[ -f tools_repozero_codex_full.py ]]; then
  cmd=(
    python tools_repozero_codex_full.py
    --repo-root "$REPOZERO_ROOT"
    --model "$MODEL_NAME"
    --base-url "$OPENAI_BASE_URL"
    --effort "${OPENAI_REASONING_EFFORT:-xhigh}"
    --workers "$REPOZERO_WORKERS"
    --timeout-s "$REPOZERO_TIMEOUT_S"
    --codex-attempts "$REPOZERO_CODEX_ATTEMPTS"
    --docker-image "$REPOZERO_DOCKER_IMAGE"
    --run-name "$REPOZERO_RUN_NAME"
    --case-source "$REPOZERO_CASE_SOURCE"
    --resume
  )
  if [[ "${REPOZERO_INCLUDE_EXCLUDED:-0}" == "1" ]]; then
    cmd+=(--include-excluded)
  fi
elif [[ -f tools_repozero_codex_smoke.py ]]; then
  cmd=(
    python tools_repozero_codex_smoke.py
    --repo-root "$REPOZERO_ROOT"
    --model "$MODEL_NAME"
    --base-url "$OPENAI_BASE_URL"
    --workers "$REPOZERO_WORKERS"
    --timeout-s "$REPOZERO_TIMEOUT_S"
    --docker-image "$REPOZERO_DOCKER_IMAGE"
  )
else
  cat >&2 <<'ERR'
Could not find a RepoZero Codex runner.
Expected one of:
  tools_repozero_codex_full.py
  tools_repozero_codex_smoke.py

Set REPOZERO_RUNNER=/path/to/project-specific-runner.py if this checkout uses
a different entry point.
ERR
  exit 2
fi

if [[ "${#case_args[@]}" -gt 0 ]]; then
  cmd+=(--cases "${case_args[@]}")
fi
if [[ -n "${REPOZERO_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra=( $REPOZERO_EXTRA_ARGS )
  cmd+=("${extra[@]}")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/repozero_py2js.log"

bench_finish "$REPOZERO_ROOT/Py2JS/output_codex/$REPOZERO_RUN_NAME"
