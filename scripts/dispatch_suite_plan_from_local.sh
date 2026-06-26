#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'USAGE'
usage: scripts/dispatch_suite_plan_from_local.sh PLAN.json [options]

Executes a previously emitted suite dry-run JSON plan from the current local
control plane. Additional options are passed to agentic_bench_suite.py, for
example: --local-dispatch-host "$(hostname)" --output-dir /tmp/agentic_run
USAGE
  exit 2
fi

PLAN_PATH="$1"
shift

has_dispatch_host=0
for arg in "$@"; do
  if [[ "$arg" == "--local-dispatch-host" || "$arg" == --local-dispatch-host=* ]]; then
    has_dispatch_host=1
    break
  fi
done
if [[ "$has_dispatch_host" -eq 0 && -z "${AGENTIC_BENCH_LOCAL_DISPATCH_HOST:-}" ]]; then
  set -- "--local-dispatch-host" "$(hostname)" "$@"
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/agentic_bench_suite.py" --dispatch-plan "$PLAN_PATH" "$@"
