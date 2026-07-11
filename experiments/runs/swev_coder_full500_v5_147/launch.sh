#!/usr/bin/env bash
# SWE-V x Coder FULL 500 — v5 clean rerun under serving .147 (Task#20 evidence-complete)
# Verified recipe (orchestrator_v21, qwencode 0.15.6) — same as 07-09 48.6%, base .140->.147.
set -uo pipefail
WT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51
PY=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python
BASE=http://100.100.104.147:30001/v1
INFO=http://100.100.104.147:30001
TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_v5_147_${TS}
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/serving"
cd "$WT"
# ---- v5 serving BEFORE capture (identity + full server args) ----
curl -s --max-time 8 --noproxy "*" "$INFO/get_model_info"  > "$RUN_ROOT/serving/get_model_info_before.json"
curl -s --max-time 8 --noproxy "*" "$INFO/get_server_info" > "$RUN_ROOT/serving/get_server_info_before.json"
grep -q Qwen3-Coder-30B-A3B-Instruct "$RUN_ROOT/serving/get_model_info_before.json" || { echo "FATAL: serving identity mismatch"; exit 3; }
export DOCKER_HOST=unix:///var/run/docker.sock
export OPENAI_API_KEY=EMPTY
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.147"
export NO_PROXY="$no_proxy"
{ echo "launch_ts=$TS"; echo "host=$(hostname)"; echo "base_url=$BASE model=Qwen3-Coder qwen_code=0.15.6 concurrency=15 full500"; } > "$RUN_ROOT/launch_info.txt"
"$PY" scripts/full500_qwencode_orchestrator_v21.py \
  --run-root "$RUN_ROOT" --base-url "$BASE" \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct" --reasoning-effort "" \
  --agent-scaffold qwencode --qwen-code-version 0.15.6 \
  --concurrency 15 --min-free-pct 8 --min-free-gb 300 --disk-guard-path / --keep-images \
  > "$RUN_ROOT/logs/runner.log" 2>&1
rc=$?
echo "$rc" > "$RUN_ROOT/runner.rc"; touch "$RUN_ROOT/runner.done"
# ---- v5 serving AFTER capture (before anyone closes sglang) ----
curl -s --max-time 8 --noproxy "*" "$INFO/get_model_info"  > "$RUN_ROOT/serving/get_model_info_after.json"
curl -s --max-time 8 --noproxy "*" "$INFO/get_server_info" > "$RUN_ROOT/serving/get_server_info_after.json"
nres=$(wc -l < "$RUN_ROOT/results.jsonl" 2>/dev/null || echo 0)
echo "[full500] DONE rc=$rc results=$nres/500 run_root=$RUN_ROOT"
