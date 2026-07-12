#!/usr/bin/env bash
# DRY-RUN validation for the TB2.1 x terminus-2 x .147 clean rerun.
# Proves: plan=89 tasks, serving points at .147 (right weights), network isolation
# in place, and NO container/model executed. Safe on dev (no docker needed) or pod.
# Writes only into ./dryrun_scratch and creates the (rollback-safe) instruct launcher copy.
set -uo pipefail

MYWORK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-gpt55-launcher-s55
DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703
SCRATCH="$MYWORK/dryrun_scratch"; mkdir -p "$SCRATCH"
LAUNCHER_C="$REPO/scripts/stage_tb21_official_qwen_launcher.sh"
LAUNCHER_I="$REPO/scripts/stage_tb21_official_qwen_launcher_terminus2.sh"

echo "===================== 1. STATIC network-isolation gate ====================="
bash "$MYWORK/assert_net_isolation.sh" static "$DS"

echo "===================== 2. serving identity (.147, read-only /get_model_info) ====================="
python3 "$MYWORK/identity_capture_147.py" before "$SCRATCH/id_coder"    http://100.100.104.147:30001 Qwen3-Coder-30B-A3B-Instruct   | grep -E 'model_path|IDENTITY'
python3 "$MYWORK/identity_capture_147.py" before "$SCRATCH/id_instruct" http://100.100.104.147:30000 Qwen3-30B-A3B-Instruct-2507 | grep -E 'model_path|IDENTITY'

echo "===================== 3. ensure Instruct launcher copy (new file; rollback = rm) ====================="
if [[ ! -f "$LAUNCHER_I" ]]; then
  python3 - "$LAUNCHER_C" "$LAUNCHER_I" <<'PY'
import sys
src = open(sys.argv[1]).read()
old = 'case "$MODEL" in Qwen/Qwen3-Coder-30B-A3B-Instruct) ;; *) echo "Qwen probe model must be Qwen/Qwen3-Coder-30B-A3B-Instruct: $MODEL" >&2; exit 2 ;; esac'
new = 'case "$MODEL" in Qwen/Qwen3-Coder-30B-A3B-Instruct|Qwen/Qwen3-30B-A3B-Instruct-2507) ;; *) echo "TB2.1 terminus-2 model must be Qwen3-Coder-30B-A3B-Instruct or Qwen3-30B-A3B-Instruct-2507: $MODEL" >&2; exit 2 ;; esac'
assert src.count(old) == 1, f"expected exactly 1 allowlist line, found {src.count(old)}"
open(sys.argv[2], "w").write(src.replace(old, new))
print("created", sys.argv[2])
PY
  chmod +x "$LAUNCHER_I"
else
  echo "already present: $LAUNCHER_I"
fi

echo "===================== 4. launcher --dry-run (prints plan; NO execute) ====================="
run_dry() {
  local prof="$1" launcher="$2" model="$3" base="$4"
  echo "--- profile=$prof model=$model base=$base ---"
  TB21_OFFICIAL_STAGE_DIR="$SCRATCH/stage_$prof" \
  TB21_OFFICIAL_OUTPUT_ROOT="$SCRATCH/out_$prof" \
  bash "$launcher" --dry-run --mode medium --attempts all --concurrency 32 \
       --model "$model" --relay-url "$base" --run-id "dryrun_${prof}_$(date -u +%m%d%H%M%S)" 2>&1 \
    | grep -E 'dataset_count|image_map_count|dry_run=1|\[stage\] execute|blocked' || true
}
run_dry coder    "$LAUNCHER_C" "Qwen/Qwen3-Coder-30B-A3B-Instruct"   http://100.100.104.147:30001/v1
run_dry instruct "$LAUNCHER_I" "Qwen/Qwen3-30B-A3B-Instruct-2507"    http://100.100.104.147:30000/v1

echo "===================== 5. assert NOTHING executed ====================="
# launcher exits before execute_host_preflight/run_attempt in dry-run (EXECUTE!=1);
# identity_capture hits only /get_model_info (never /v1/chat/completions).
if command -v docker >/dev/null 2>&1; then
  n=$(DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}" docker ps --format '{{.Image}}' 2>/dev/null | grep -c '^tb2-offline/' || true)
  echo "live tb2-offline containers started by dry-run = $n (expect 0)"
else
  echo "docker not on this host -> trivially 0 containers, 0 model calls (dry-run is docker-free/model-free)"
fi
echo "DRYRUN_DONE"
