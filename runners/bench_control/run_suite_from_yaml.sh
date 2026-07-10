#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${1:-$SCRIPT_DIR/configs/gpt54mini_ab_cocoa_full.yaml}"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Missing suite YAML config: $CONFIG_PATH" >&2
  exit 2
fi

eval "$(
  python - "$CONFIG_PATH" <<'PY'
import shlex
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
cfg = yaml.safe_load(path.read_text()) or {}

suite = cfg.get("suite", {}) or {}
model = cfg.get("model", {}) or {}
workers = cfg.get("workers", {}) or {}
benches = cfg.get("benches", []) or []

exports = {}

if model.get("profile"):
    exports["BENCH_MODEL_PROFILE"] = str(model["profile"])
if model.get("name"):
    exports["MODEL_NAME"] = str(model["name"])
if model.get("litellm_model"):
    exports["LITELLM_MODEL"] = str(model["litellm_model"])
if model.get("base_url"):
    exports["OPENAI_BASE_URL"] = str(model["base_url"])
if model.get("reasoning_effort"):
    exports["OPENAI_REASONING_EFFORT"] = str(model["reasoning_effort"])

if suite.get("id"):
    exports["SUITE_ID"] = str(suite["id"])
else:
    prefix = str(suite.get("id_prefix", "yaml_suite")).strip()
    exports["SUITE_ID_PREFIX"] = prefix
if suite.get("concurrency") is not None:
    exports["SUITE_CONCURRENCY"] = str(suite["concurrency"])
if suite.get("output_root"):
    exports["SUITE_OUTPUT_ROOT"] = str(suite["output_root"])
if benches:
    exports["SUITE_BENCHES"] = " ".join(str(item) for item in benches)

worker_map = {
    "full": "FULL_WORKERS",
    "docker": "DOCKER_WORKERS",
    "cocoa": "COCOA_WORKERS",
}
for key, env_name in worker_map.items():
    if workers.get(key) is not None:
        exports[env_name] = str(workers[key])

print(f"export BENCH_SUITE_CONFIG={shlex.quote(str(path))}")
for key, value in exports.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"

if [[ -z "${SUITE_ID:-}" && -n "${SUITE_ID_PREFIX:-}" ]]; then
  export SUITE_ID="${SUITE_ID_PREFIX}_$(date +%Y%m%d_%H%M%S)"
fi

if [[ "${BENCH_PRINT_CONFIG:-0}" == "1" ]]; then
  {
    echo "BENCH_SUITE_CONFIG=$BENCH_SUITE_CONFIG"
    echo "BENCH_MODEL_PROFILE=${BENCH_MODEL_PROFILE:-}"
    echo "MODEL_NAME=${MODEL_NAME:-}"
    echo "OPENAI_BASE_URL=${OPENAI_BASE_URL:-}"
    echo "OPENAI_REASONING_EFFORT=${OPENAI_REASONING_EFFORT:-}"
    echo "SUITE_ID=${SUITE_ID:-}"
    echo "SUITE_CONCURRENCY=${SUITE_CONCURRENCY:-}"
    echo "SUITE_BENCHES=${SUITE_BENCHES:-}"
    echo "FULL_WORKERS=${FULL_WORKERS:-}"
    echo "DOCKER_WORKERS=${DOCKER_WORKERS:-}"
    echo "COCOA_WORKERS=${COCOA_WORKERS:-}"
  }
  exit 0
fi

exec "$SCRIPT_DIR/run_ab_cocoa_full_suite.sh"
