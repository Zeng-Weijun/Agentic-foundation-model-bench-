#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/configs/code_models/swebench_agents/qwen3_coder_30b_a3b_instruct_mini_swe_agent.yaml"
MODE="${1:-smoke}"

exec "$SCRIPT_DIR/run_code_model_suite_from_yaml.sh" "$CONFIG" "$MODE"
