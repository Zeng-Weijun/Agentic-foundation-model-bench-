#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

BENCHES="${BENCHES:-tau2 vitabench terminal_bench cocoabench}"
status=0

for bench in $BENCHES; do
  echo "=== running $bench ==="
  script="$SCRIPT_DIR/run_${bench}.sh"
  if [[ ! -x "$script" ]]; then
    echo "missing executable: $script" >&2
    status=1
    continue
  fi
  if ! "$script"; then
    echo "FAILED: $bench" >&2
    status=1
  fi
done

exit "$status"
