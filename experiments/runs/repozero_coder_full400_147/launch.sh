#!/usr/bin/env bash
# ============================================================================
# full400_launch.sh — RepoZero Path A OFFICIAL 400 x qwen-code(native) x Coder
# Run ON KVM (env-kvm-57740737-bzw56). Detached (setsid), resumable, low c.
#   launch:  bash full400_launch.sh
#   resume:  RESUME=1 bash full400_launch.sh
#   tune:    WORKERS=6 RUN_NAME=coder_full400_rerun bash full400_launch.sh
# Serving .147:30001 (Coder) is SHARED — keep WORKERS low (4; <=8) so we do not
# starve any concurrent Coder job. Preflight curls /v1/models first.
# ============================================================================
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUN_NAME="${RUN_NAME:-coder_full400_$(date -u +%Y%m%dT%H%M%SZ)}"
WORKERS="${WORKERS:-4}"
BASE_URL="${BASE_URL:-http://100.100.104.147:30001/v1}"
MODEL="${MODEL:-Qwen/Qwen3-Coder-30B-A3B-Instruct}"
LOG="$HERE/runs/${RUN_NAME}.launch.log"
mkdir -p "$HERE/runs"

# preflight: serving reachable + serving Coder
if ! curl -s --noproxy '*' --max-time 12 "$BASE_URL/models" | grep -q "Qwen3-Coder"; then
  echo "[preflight][FAIL] $BASE_URL not serving Qwen3-Coder (or unreachable)"; exit 1
fi
echo "[preflight][OK] $BASE_URL serving Coder"
ulimit -n 65535 2>/dev/null || true
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"

echo "[launch] run_name=$RUN_NAME workers=$WORKERS base=$BASE_URL"
echo "[launch] log=$LOG"
setsid bash -c "cd '$HERE' && python3 repozero_full400_orchestrator.py \
  --run-name '$RUN_NAME' --workers '$WORKERS' --base-url '$BASE_URL' --model '$MODEL' \
  ${RESUME:+--resume} > '$LOG' 2>&1" &
echo "[launch] pid=$!"
echo "[launch] follow:  tail -f $LOG"
echo "[launch] summary: $HERE/runs/$RUN_NAME/summary.json"
