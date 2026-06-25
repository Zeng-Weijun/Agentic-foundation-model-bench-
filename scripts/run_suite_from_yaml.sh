#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DEFAULT_SUITE="$REPO_ROOT/manifests/suite.example.yaml"

if [[ $# -gt 0 && "${1:0:1}" != "-" ]]; then
  SUITE_YAML="$1"
  shift
else
  SUITE_YAML="$DEFAULT_SUITE"
fi

PYTHON_BIN="${PYTHON:-python3}"
exec "$PYTHON_BIN" "$SCRIPT_DIR/agentic_bench_suite.py" "$SUITE_YAML" "$@"
