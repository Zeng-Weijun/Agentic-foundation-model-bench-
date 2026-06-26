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
exec "$PYTHON_BIN" "$SCRIPT_DIR/agentic_bench_suite.py" --dispatch-plan "$PLAN_PATH" "$@"
