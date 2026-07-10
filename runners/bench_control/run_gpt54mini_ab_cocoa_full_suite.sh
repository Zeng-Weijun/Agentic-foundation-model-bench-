#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${1:-$SCRIPT_DIR/configs/gpt54mini_ab_cocoa_full.yaml}"

exec "$SCRIPT_DIR/run_suite_from_yaml.sh" "$CONFIG_PATH"
