#!/usr/bin/env bash
set -euo pipefail
: "${RUN_ROOT:?}"
WT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51"
PY="/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python"
cd "$WT"
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/health"
{
  echo "launch_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "run_root=$RUN_ROOT"
  echo "host=$(hostname)"
  echo "cwd=$(pwd)"
  echo "concurrency=20"
  echo "base_url=http://100.100.104.140:30001/v1"
  echo "model=Qwen/Qwen3-Coder-30B-A3B-Instruct"
  echo "reasoning_effort=ABSENT"
  df -h /
  df -ih /
} > "$RUN_ROOT/launch_info.txt"
export RUN_ROOT
export DOCKER_HOST=unix:///var/run/docker.sock
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export SWEV_BASE_URL="http://100.100.104.140:30001/v1"
export SWEV_MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
export SWEV_REASONING_EFFORT=""
export SWEV_CONCURRENCY=20
export SWEV_RUN_ROOT="$RUN_ROOT"
export SWEV_KEEP_IMAGES=1
export SWEV_MIN_FREE_PCT=10
export SWEV_MIN_FREE_GB=350
export SWEV_DISK_GUARD_PATH=/
export SWEV_QWEN_CODE_VERSION=0.15.6
export SWEV_AGENT_SCAFFOLD=qwencode
export SWEV_PREHEAT_ALL=0
export HF_HUB_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HOME="/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface"
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.140"
export NO_PROXY="$no_proxy"
("$RUN_ROOT/disk_watch.sh" > "$RUN_ROOT/logs/disk_watch.stdout.log" 2>&1 & echo $! > "$RUN_ROOT/disk_watch.pid")
set +e
"$PY" scripts/full500_qwencode_orchestrator_v21.py \
  --run-root "$RUN_ROOT" \
  --base-url "http://100.100.104.140:30001/v1" \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct" \
  --reasoning-effort "" \
  --agent-scaffold qwencode \
  --qwen-code-version 0.15.6 \
  --concurrency 20 \
  --min-free-pct 10 \
  --min-free-gb 350 \
  --disk-guard-path / \
  --keep-images \
  > "$RUN_ROOT/logs/runner.log" 2>&1
rc=$?
set -e
echo "$rc" > "$RUN_ROOT/runner.rc"
touch "$RUN_ROOT/runner.done"
python3 "$RUN_ROOT/health_scan.py" >> "$RUN_ROOT/health/health_scan.log" 2>&1 || true
exit "$rc"
