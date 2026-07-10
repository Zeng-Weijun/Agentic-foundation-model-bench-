#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init swebench_verified_mini_swe_agent

MINI_SWE_BIN="${MINI_SWE_BIN:-$(command -v mini-extra || true)}"
MINI_SWE_MODEL="${MINI_SWE_MODEL:-$LITELLM_MODEL}"
MINI_SWE_SUBSET="${MINI_SWE_SUBSET:-verified}"
MINI_SWE_SPLIT="${MINI_SWE_SPLIT:-test}"
MINI_SWE_WORKERS="${MINI_SWE_WORKERS:-${MAX_CONCURRENCY:-1}}"
MINI_SWE_OUTPUT_DIR="${MINI_SWE_OUTPUT_DIR:-$BENCH_RUN_DIR/mini_swe_agent_outputs}"
MINI_SWE_ENVIRONMENT_CLASS="${MINI_SWE_ENVIRONMENT_CLASS:-docker}"
MINI_SWE_CONFIG="${MINI_SWE_CONFIG:-$BENCH_SCRIPT_DIR/configs/code_models/swebench_agents/mini_swe_agent_swebench_qwen3_coder_30b_a3b.yaml}"

bench_require_path "$MINI_SWE_CONFIG" "mini-swe-agent overlay config"
if [[ -z "$MINI_SWE_BIN" || ! -x "$MINI_SWE_BIN" ]]; then
  {
    echo "mini-swe-agent is not installed on this host."
    echo "Install command recorded in the suite YAML; expected executable: mini-extra."
  } | tee "$BENCH_RUN_DIR/mini_swe_agent_missing.log" >&2
  exit 2
fi

mkdir -p "$MINI_SWE_OUTPUT_DIR"
cp "$MINI_SWE_CONFIG" "$BENCH_RUN_DIR/mini_swe_agent.config.snapshot.yaml"

export OPENAI_API_KEY
export OPENAI_BASE_URL
export MSWEA_COST_TRACKING="${MSWEA_COST_TRACKING:-ignore_errors}"

cmd=(
  "$MINI_SWE_BIN" swebench
  --model "$MINI_SWE_MODEL"
  --subset "$MINI_SWE_SUBSET"
  --split "$MINI_SWE_SPLIT"
  --workers "$MINI_SWE_WORKERS"
  --output "$MINI_SWE_OUTPUT_DIR"
  --config swebench.yaml
  --config "$MINI_SWE_CONFIG"
  --environment-class "$MINI_SWE_ENVIRONMENT_CLASS"
)

if [[ -n "${MINI_SWE_SLICE:-}" ]]; then
  cmd+=(--slice "$MINI_SWE_SLICE")
fi
if [[ -n "${MINI_SWE_FILTER:-}" ]]; then
  cmd+=(--filter "$MINI_SWE_FILTER")
fi
if [[ -n "${MINI_SWE_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $MINI_SWE_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

printf '%q ' "${cmd[@]}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"
"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/mini_swe_agent.log"

python - "$BENCH_RUN_DIR" "$MINI_SWE_OUTPUT_DIR" "$MINI_SWE_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
outdir = Path(sys.argv[2])
cfg = Path(sys.argv[3])
manifest = {
    "agent": "mini-swe-agent",
    "config_snapshot": str(run_dir / "mini_swe_agent.config.snapshot.yaml"),
    "source_config": str(cfg),
    "agent_trace_root": str(outdir),
    "predictions": str(outdir / "preds.json"),
    "log": str(run_dir / "mini_swe_agent.log"),
    "command": str(run_dir / "command.sh"),
}
(run_dir / "artifact_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

bench_finish "$MINI_SWE_OUTPUT_DIR"
