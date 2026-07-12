#!/usr/bin/env bash
# SWE-bench Multilingual FULL 300 x Qwen (qwencode) — REAL run against serving .147.
#   usage: bash launch_full300_qwencode_147.sh <coder|instruct2507>
#   SAFETY: prints the plan and EXITS unless FULL300_ALLOW=YES is set (no accidental launch).
#   concurrency via SWEML_CONCURRENCY (default 8); tune vs live serving load.
set -uo pipefail
B=/mnt/shared-storage-user/mineru2-shared/zengweijun
WT_ML=$B/nips2026/agentic-foundation-model-bench/repo/.worktrees/swemultilingual-v21-agent51
BASE_RUNNER=$B/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51/scripts/full500_qwencode_orchestrator_v21.py
ADAPTER=$WT_ML/scripts/full300_swemultilingual_qwencode_orchestrator_v21.py
PY=$B/conda_envs/swebench/bin/python
DATASET_ROOT=$B/nips2026/shared_bench/swebench-multilingual-2025-08-26
P0_MAP=$B/nips2026/agentic-foundation-model-bench/runs/swemultilingual_p0_stage_20260706/swemultilingual_p0_map_full300_20260712.json
FULL_IDS=$WT_ML/manifests/candidates/swemultilingual_full300_instance_ids_20260712.txt
QWEN_ROOT=$B/nips2026/shared_bench/qwen_native_swebench/.npm-root-0.16.2
CONC="${SWEML_CONCURRENCY:-8}"; PRE="${SWEML_PREHEAT_CONCURRENCY:-4}"

WHICH="${1:-}"; case "$WHICH" in
  coder)        BASE_URL=http://100.100.104.147:30001/v1; MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct;  SUF=Qwen3-Coder-30B-A3B-Instruct;;
  instruct2507) BASE_URL=http://100.100.104.147:30000/v1; MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507;   SUF=Qwen3-30B-A3B-Instruct-2507;;
  *) echo "usage: $0 <coder|instruct2507>"; exit 2;;
esac
INFO="${BASE_URL%/v1}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
RR=$B/nips2026/agentic-foundation-model-bench/runs/sweml_${WHICH}_qwencode_full300_147_${TS}

echo "[full300] which=$WHICH base_url=$BASE_URL model=$MODEL concurrency=$CONC run_root=$RR"
echo "[full300] p0_map=$P0_MAP ids=$FULL_IDS orchestrator=$ADAPTER (EXPECTED_COUNT=300)"
if [ "${FULL300_ALLOW:-}" != "YES" ]; then
  echo "[full300] DRY GUARD: set FULL300_ALLOW=YES to actually launch. No run performed."; exit 0
fi

mkdir -p "$RR/logs" "$RR/serving"
# v5 serving BEFORE (identity guard)
curl -s --noproxy '*' --max-time 10 "$INFO/get_model_info"  > "$RR/serving/get_model_info_before.json"
curl -s --noproxy '*' --max-time 10 "$INFO/get_server_info" > "$RR/serving/get_server_info_before.json"
grep -q "$SUF" "$RR/serving/get_model_info_before.json" || { echo "FATAL: serving identity mismatch ($SUF)"; exit 3; }
export DOCKER_HOST=unix:///var/run/docker.sock OPENAI_API_KEY=EMPTY
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HOME=$B/.cache/huggingface
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.147,100.97.118.137"
export NO_PROXY="$no_proxy"

env SWEML_DATASET_ROOT="$DATASET_ROOT" SWEML_EXPECTED_COUNT=300 SWEML_AGENT_DOCKER_NETWORK=bridge \
  SWEML_QWENCODE_BASE_RUNNER="$BASE_RUNNER" SWEV_P0_MAP="$P0_MAP" SWEV_INSTANCES_FILE="$FULL_IDS" \
  SWEV_QWEN_ROOT="$QWEN_ROOT" SWEV_BASE_URL="$BASE_URL" SWEV_MODEL="$MODEL" \
  "$PY" "$ADAPTER" \
    --run-root "$RR" --p0-map "$P0_MAP" --instances-file "$FULL_IDS" \
    --base-url "$BASE_URL" --model "$MODEL" --reasoning-effort "" \
    --max-output-tokens 65536 --context-limit 262144 --litellm-provider openai \
    --agent-scaffold qwencode --qwen-root "$QWEN_ROOT" --qwen-code-version 0.16.2 \
    --concurrency "$CONC" --preheat-all --preheat-concurrency "$PRE" --include-deferred --keep-images \
    > "$RR/logs/runner.log" 2>&1
rc=$?; echo "$rc" > "$RR/runner.rc"; touch "$RR/runner.done"
# v5 serving AFTER (before sglang closes)
curl -s --noproxy '*' --max-time 10 "$INFO/get_model_info"  > "$RR/serving/get_model_info_after.json"
curl -s --noproxy '*' --max-time 10 "$INFO/get_server_info" > "$RR/serving/get_server_info_after.json"
n=$(wc -l < "$RR/results.jsonl" 2>/dev/null || echo 0)
echo "[full300] DONE rc=$rc results=$n/300 run_root=$RR ; per-language in $RR/score_summary.json"
