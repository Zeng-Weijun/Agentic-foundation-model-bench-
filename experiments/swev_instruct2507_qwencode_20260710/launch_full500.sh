#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
export RUN_ROOT="$PWD"
export OPENAI_API_KEY=EMPTY
export LITELLM_LOCAL_MODEL_COST_MAP=true
export SWEV_BASE_URL=http://100.100.104.140:30000/v1
export SWEV_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
export SWEV_REASONING_EFFORT=
export SWEV_AGENT_SCAFFOLD=qwencode
export SWEV_QWEN_CODE_VERSION=0.15.6
export SWEV_CONCURRENCY=16
export SWEV_INCLUDE_DEFERRED=1
export SWEV_KEEP_IMAGES=1
export SWEV_MIN_FREE_PCT=10
export SWEV_MIN_FREE_GB=80
export SWEV_CONTEXT_LIMIT=262144
export SWEV_MAX_OUTPUT_TOKENS=65536
export MONITOR_INTERVAL_SECONDS=600
PY=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python
RUNNER=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51/scripts/full500_qwencode_orchestrator_v21.py
printf 'launch_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee logs/launch.env
printf 'run_root=%s\nmodel=%s\nbase_url=%s\nconcurrency=%s\n' "$RUN_ROOT" "$SWEV_MODEL" "$SWEV_BASE_URL" "$SWEV_CONCURRENCY" | tee -a logs/launch.env
$PY ./capture_serving_info.py before | tee logs/model_identity_before.log
$PY ./disk_identity_monitor.py > logs/disk_identity_monitor.log 2>&1 &
MON_PID=$!
echo "$MON_PID" > monitor.pid
set +e
$PY "$RUNNER" \
  --run-root "$RUN_ROOT" \
  --base-url "$SWEV_BASE_URL" \
  --model "$SWEV_MODEL" \
  --agent-scaffold qwencode \
  --qwen-code-version 0.15.6 \
  --concurrency 16 \
  --include-deferred \
  --keep-images \
  --min-free-pct 10 \
  --min-free-gb 80 \
  > logs/full500.log 2>&1
RC=$?
set -e
kill "$MON_PID" 2>/dev/null || true
wait "$MON_PID" 2>/dev/null || true
printf 'runner_rc=%s\nfinished_utc=%s\n' "$RC" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee logs/runner.rc
$PY ./capture_serving_info.py after | tee logs/model_identity_after.log || echo 'after_model_capture_failed' | tee logs/model_identity_after.failed
$PY ./summarize_ledger.py | tee logs/ledger_summary.log || true
sha256sum logs/full500.log logs/launch.env logs/runner.rc serving/get_model_info_before.json serving/get_model_info_after.json serving/get_server_info_before.json serving/get_server_info_after.json preflight/stress_30000_c20x3_summary.json results.jsonl 2>/dev/null > SHA256SUMS || true
exit "$RC"
