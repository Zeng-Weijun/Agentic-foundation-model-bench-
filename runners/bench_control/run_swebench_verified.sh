#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init swebench_verified

SWE_AGENT_ROOT="${SWE_AGENT_ROOT:-/data/swe/SWE-agent}"
SWEBENCH_PY="${SWEBENCH_PY:-/data/conda_envs/swebench/bin/python}"
SWEAGENT_BIN="${SWEAGENT_BIN:-/data/conda_envs/sweagent/bin/sweagent}"
SWE_TEMPLATE_CFG="${SWE_TEMPLATE_CFG:-$SWE_AGENT_ROOT/local_configs/verified_smoke5_gpt55_nodownload_20260427_v4.yaml}"
SWEBENCH_DATASET="${SWEBENCH_DATASET:-/data/swe/datasets/SWE-bench_Verified/data/test-00000-of-00001.parquet}"
SWEBENCH_OUT_BASE="${SWEBENCH_OUT_BASE:-$(readlink -f "$SWE_AGENT_ROOT/trajectories")}"
SWEBENCH_NUM_WORKERS="${SWEBENCH_NUM_WORKERS:-$MAX_CONCURRENCY}"
SWEBENCH_EVAL_WORKERS="${SWEBENCH_EVAL_WORKERS:-2}"
SWEBENCH_SHORT_TAG="$(
  python - "$RUN_TAG" <<'PY'
import re
import sys

parts = [p for p in sys.argv[1].split("_") if p]
tag = "_".join(parts[-2:]) if len(parts) >= 2 else sys.argv[1]
tag = re.sub(r"[^A-Za-z0-9_.-]+", "_", tag).strip("._-")
print(tag or "run")
PY
)"
SWEBENCH_SUFFIX="${SWEBENCH_SUFFIX:-swev_${SWEBENCH_SHORT_TAG}}"
SWEBENCH_CFG="$BENCH_RUN_DIR/${SWEBENCH_SUFFIX}.yaml"
SWEBENCH_INSTANCE_REGEX="${SWEBENCH_INSTANCE_REGEX:-^(astropy__astropy-12907|matplotlib__matplotlib-20488|sympy__sympy-12096|scikit-learn__scikit-learn-10844|sphinx-doc__sphinx-10435)$}"
export SWEBENCH_SUFFIX
export SWEBENCH_INSTANCE_REGEX

bench_require_path "$SWE_AGENT_ROOT" "SWE-agent checkout"
bench_require_exe "$SWEAGENT_BIN" "sweagent"
bench_require_exe "$SWEBENCH_PY" "SWE-bench python"
bench_require_path "$SWE_TEMPLATE_CFG" "SWE-agent template config"

export http_proxy="${http_proxy:-http://httpproxy-headless.kubebrain.svc.pjlab.local:3128}"
export https_proxy="${https_proxy:-$http_proxy}"
export HTTP_PROXY="${HTTP_PROXY:-$http_proxy}"
export HTTPS_PROXY="${HTTPS_PROXY:-$https_proxy}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost,::1,100.96.0.0/12}"
export no_proxy="${no_proxy:-$NO_PROXY}"
export PYTHONPATH="/data/swe/pyhooks${PYTHONPATH:+:$PYTHONPATH}"

python - "$SWE_TEMPLATE_CFG" "$SWEBENCH_CFG" <<'PY'
import os
import re
import sys
from pathlib import Path

src, dst = map(Path, sys.argv[1:3])
text = src.read_text()
suffix = os.environ["SWEBENCH_SUFFIX"]
model = os.environ.get("LITELLM_MODEL") or os.environ["MODEL_NAME"]
base_url = os.environ["OPENAI_BASE_URL"]
reasoning = os.environ.get("OPENAI_REASONING_EFFORT", "")
max_input_tokens = os.environ.get("MAX_INPUT_TOKENS", "")
max_output_tokens = os.environ.get("MAX_TOKENS", "")
instance_regex = os.environ.get("SWEBENCH_INSTANCE_REGEX", "")

text = re.sub(r"^suffix: .*$", f"suffix: {suffix}", text, flags=re.M)
text = re.sub(r"^    name: .*$", f"    name: {model}", text, flags=re.M)
text = re.sub(r"^    api_base: .*$", f"    api_base: {base_url}", text, flags=re.M)
text = re.sub(r"^    api_key: .*$", "    api_key: $OPENAI_API_KEY", text, flags=re.M)
if max_input_tokens:
    if re.search(r"^    max_input_tokens: .*$", text, flags=re.M):
        text = re.sub(r"^    max_input_tokens: .*$", f"    max_input_tokens: {max_input_tokens}", text, flags=re.M)
    else:
        text = re.sub(r"^(    api_key: .*)$", rf"\1\n    max_input_tokens: {max_input_tokens}", text, count=1, flags=re.M)
if max_output_tokens:
    if re.search(r"^    max_output_tokens: .*$", text, flags=re.M):
        text = re.sub(r"^    max_output_tokens: .*$", f"    max_output_tokens: {max_output_tokens}", text, flags=re.M)
    else:
        anchor = "max_input_tokens" if max_input_tokens else "api_key"
        text = re.sub(rf"^(    {anchor}: .*)$", rf"\1\n    max_output_tokens: {max_output_tokens}", text, count=1, flags=re.M)
text = re.sub(r"^    total_cost_limit: .*$", f"    total_cost_limit: {os.environ.get('SWEBENCH_TOTAL_COST_LIMIT', '10000.0')}", text, flags=re.M)
text = re.sub(r"^    per_instance_cost_limit: .*$", f"    per_instance_cost_limit: {os.environ.get('SWEBENCH_PER_INSTANCE_COST_LIMIT', '8')}", text, flags=re.M)
text = re.sub(r"^    per_instance_call_limit: .*$", f"    per_instance_call_limit: {os.environ.get('SWEBENCH_PER_INSTANCE_CALL_LIMIT', '200')}", text, flags=re.M)
if max_output_tokens:
    if re.search(r"^    completion_kwargs:\s*$", text, flags=re.M):
        if re.search(r"^      max_tokens: .*$", text, flags=re.M):
            text = re.sub(r"^      max_tokens: .*$", f"      max_tokens: {max_output_tokens}", text, flags=re.M)
        else:
            text = re.sub(r"^    completion_kwargs:\s*$", f"    completion_kwargs:\n      max_tokens: {max_output_tokens}", text, count=1, flags=re.M)
    elif re.search(r"^    temperature: .*$", text, flags=re.M):
        text = re.sub(r"^(    temperature: .*)$", rf"\1\n    completion_kwargs:\n      max_tokens: {max_output_tokens}", text, count=1, flags=re.M)
if reasoning:
    text = re.sub(r"^      reasoning_effort: .*$", f"      reasoning_effort: {reasoning}", text, flags=re.M)

if os.environ.get("SWEBENCH_MODE", "smoke") == "full":
    text = re.sub(r"^  filter: .*\n", "", text, flags=re.M)
elif instance_regex:
    if re.search(r"^  filter: .*$", text, flags=re.M):
        text = re.sub(r"^  filter: .*$", f"  filter: {instance_regex}", text, flags=re.M)
    else:
        text = text.replace("  evaluate: false\n", f"  evaluate: false\n  filter: {instance_regex}\n")

dst.write_text(text)
PY

cd "$SWE_AGENT_ROOT"

run_log="$BENCH_RUN_DIR/sweagent.log"
eval_log="$BENCH_RUN_DIR/swebench_eval.log"
: > "$run_log"
: > "$eval_log"

bench_run "$SWEAGENT_BIN" run-batch --config "$SWEBENCH_CFG" --num_workers "$SWEBENCH_NUM_WORKERS" \
  2>&1 | tee -a "$run_log"

outdir="$(find "$SWEBENCH_OUT_BASE" -type d -name "*__${SWEBENCH_SUFFIX}" | sort | tail -n 1 || true)"
if [[ -z "$outdir" || ! -f "$outdir/preds.json" ]]; then
  echo "Missing SWE-agent output dir/preds.json for suffix: $SWEBENCH_SUFFIX" >&2
  exit 3
fi
ln -sfn "$outdir" "$BENCH_RUN_DIR/sweagent_output"

if [[ "${SWEBENCH_SKIP_EVAL:-0}" != "1" ]]; then
  eval_cmd=(
    "$SWEBENCH_PY" -m swebench.harness.run_evaluation
    --dataset_name "$SWEBENCH_DATASET"
    --split test
    --predictions_path "$outdir/preds.json"
    --max_workers "$SWEBENCH_EVAL_WORKERS"
    --run_id "${SWEBENCH_SUFFIX}_eval"
  )
  if [[ "${SWEBENCH_MODE:-smoke}" != "full" ]]; then
    # shellcheck disable=SC2206
    ids=( ${SWEBENCH_INSTANCE_IDS:-astropy__astropy-12907 matplotlib__matplotlib-20488 sympy__sympy-12096 scikit-learn__scikit-learn-10844 sphinx-doc__sphinx-10435} )
    eval_cmd+=(--instance_ids "${ids[@]}")
  fi
  printf '%q ' "${eval_cmd[@]}" | tee "$BENCH_RUN_DIR/eval_command.sh"
  printf '\n' | tee -a "$BENCH_RUN_DIR/eval_command.sh"
  "${eval_cmd[@]}" 2>&1 | tee -a "$eval_log"
fi

python - "$BENCH_RUN_DIR" "$SWEBENCH_CFG" "$outdir" <<'PY'
import json
import sys
from pathlib import Path

run_dir, cfg, outdir = map(Path, sys.argv[1:4])
manifest = {
    "agent": "swe-agent",
    "config_snapshot": str(cfg),
    "agent_trace_root": str(outdir),
    "agent_trace_symlink": str(run_dir / "sweagent_output"),
    "predictions": str(outdir / "preds.json"),
    "sweagent_log": str(run_dir / "sweagent.log"),
    "swebench_eval_log": str(run_dir / "swebench_eval.log"),
    "command_log": str(run_dir / "command.log"),
    "eval_command": str(run_dir / "eval_command.sh"),
}
(run_dir / "artifact_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

bench_finish "$outdir/preds.json"
