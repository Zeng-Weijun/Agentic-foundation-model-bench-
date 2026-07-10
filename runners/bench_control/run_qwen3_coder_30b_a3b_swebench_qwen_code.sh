#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-smoke}"
CONFIG="$SCRIPT_DIR/configs/code_models/qwen3_coder_30b_a3b_instruct_swebench_qwen_code.yaml"

case "$MODE" in
  smoke|full) ;;
  *)
    echo "Usage: $0 [smoke|full]" >&2
    exit 2
    ;;
esac

exec "$SCRIPT_DIR/run_code_model_suite_from_yaml.sh" "$CONFIG" "$MODE"
