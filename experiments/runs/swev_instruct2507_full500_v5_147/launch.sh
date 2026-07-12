#!/usr/bin/env bash
# SWE-V x Instruct-2507 FULL 500 — v5 clean run under serving .147:30000 (same-base training anchor)
# Verified recipe from 07-09 swev_instruct2507_qwencode_full500 (orchestrator_v21, qwencode 0.15.6), base .140->.147.
set -uo pipefail
WT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51
PY=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python
BASE=http://100.100.104.147:30000/v1
INFO=http://100.100.104.147:30000
TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_full500_v5_147_${TS}
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/serving"
cd "$WT"
curl -s --max-time 8 --noproxy "*" "$INFO/get_model_info"  > "$RUN_ROOT/serving/get_model_info_before.json"
curl -s --max-time 8 --noproxy "*" "$INFO/get_server_info" > "$RUN_ROOT/serving/get_server_info_before.json"
grep -q Qwen3-30B-A3B-Instruct-2507 "$RUN_ROOT/serving/get_model_info_before.json" || { echo "FATAL: serving identity mismatch (:30000 not Instruct-2507)"; exit 3; }
export DOCKER_HOST=unix:///var/run/docker.sock
export OPENAI_API_KEY=EMPTY
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface
export SWEV_INCLUDE_DEFERRED=1
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.147"
export NO_PROXY="$no_proxy"
{ echo "launch_ts=$TS"; echo "host=$(hostname)"; echo "base_url=$BASE model=Instruct-2507 qwen_code=0.15.6 concurrency=10 full500 include_deferred=1"; } > "$RUN_ROOT/launch_info.txt"
"$PY" scripts/full500_qwencode_orchestrator_v21.py \
  --run-root "$RUN_ROOT" --base-url "$BASE" \
  --model "Qwen/Qwen3-30B-A3B-Instruct-2507" --reasoning-effort "" \
  --agent-scaffold qwencode --qwen-code-version 0.15.6 \
  --concurrency 10 --min-free-pct 8 --min-free-gb 250 --disk-guard-path / --keep-images \
  > "$RUN_ROOT/logs/runner.log" 2>&1
rc=$?
echo "$rc" > "$RUN_ROOT/runner.rc"; touch "$RUN_ROOT/runner.done"
curl -s --max-time 8 --noproxy "*" "$INFO/get_model_info"  > "$RUN_ROOT/serving/get_model_info_after.json"
curl -s --max-time 8 --noproxy "*" "$INFO/get_server_info" > "$RUN_ROOT/serving/get_server_info_after.json"
echo "[instruct2507-full500] DONE rc=$rc results=$(wc -l < $RUN_ROOT/results.jsonl 2>/dev/null || echo 0)/500 run_root=$RUN_ROOT"
