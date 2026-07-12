#!/usr/bin/env bash
set -euo pipefail

# Stage/execute wrapper for the TB2.1 x Qwen terminus-2 probe line.
# Default is dry-run. Do not use --execute until lead/orchestrator sends GO.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$DEFAULT_REPO_ROOT}"
if [[ -d "$DEFAULT_REPO_ROOT/.worktrees" ]]; then
  DEFAULT_SHARED_REPO_ROOT="$DEFAULT_REPO_ROOT"
else
  DEFAULT_SHARED_REPO_ROOT="$(cd "$DEFAULT_REPO_ROOT/../.." && pwd)"
fi
SHARED_REPO_ROOT="${TB21_SHARED_REPO_ROOT:-$DEFAULT_SHARED_REPO_ROOT}"
POD_A_ENDPOINT="${POD_A_ENDPOINT:-env-kvm-15238487-rlgbn.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn}"
POD_A_SSH_OPTS="${POD_A_SSH_OPTS:--CAXY}"
RUNNER="${TB21_PRIVILEGED_RUNNER:-$REPO_ROOT/scripts/run_terminal_bench_2_1_full89_batched_privileged_offline.sh}"
if [[ ! -x "$RUNNER" && -x "$SHARED_REPO_ROOT/.worktrees/tb21-image-fixes-r3/scripts/run_terminal_bench_2_1_full89_batched_privileged_offline.sh" ]]; then
  RUNNER="$SHARED_REPO_ROOT/.worktrees/tb21-image-fixes-r3/scripts/run_terminal_bench_2_1_full89_batched_privileged_offline.sh"
fi
IMAGE_MANIFEST="${TB21_FULL89_IMAGE_MANIFEST:-$SHARED_REPO_ROOT/.worktrees/tb21-image-fixes-r3/manifests/images/terminal_bench_2_1_full89_p0_closure_r7.yaml}"
IMAGE_MAP_BUILDER="${TB21_IMAGE_MAP_BUILDER:-$REPO_ROOT/scripts/build_tb21_prebuilt_image_map.py}"
if [[ ! -f "$IMAGE_MAP_BUILDER" && -f "$SHARED_REPO_ROOT/scripts/build_tb21_prebuilt_image_map.py" ]]; then
  IMAGE_MAP_BUILDER="$SHARED_REPO_ROOT/scripts/build_tb21_prebuilt_image_map.py"
fi
DATASET="${TB21_FULL89_DATASET:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703}"
STAGE_DIR="${TB21_OFFICIAL_STAGE_DIR:-$REPO_ROOT/_coordination/20260625_harbor_bench/reports/tb21_official_qwen_staged}"
IMAGE_MAP="${TB21_FULL89_IMAGE_MAP:-$STAGE_DIR/tb21_prebuilt_image_map_full89_r7_official_qwen.json}"
OUTPUT_ROOT="${TB21_OFFICIAL_OUTPUT_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda}"
SCORES_DIR="${TB21_OFFICIAL_SCORES_DIR:-$REPO_ROOT/reports/scores}"
RELAY_URL="${TB21_RELAY_URL:-http://100.103.228.120:30000/v1}"
API_ENV="${TB21_API_ENV:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/api_config.env}"
MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
MODE="medium"
ATTEMPTS=1
ATTEMPTS_SPEC="all"
CONCURRENCY_TIERS="32 64 89 100"
CONCURRENCY=32
EXECUTE=0
TIMEOUT_MULTIPLIER="1.0"
TIMEOUT_SEC=7200
ASSUMED_FULL500_CONCURRENCY="${TB21_ASSUMED_FULL500_CONCURRENCY:-50}"
RELAY_CAP="${TB21_RELAY_TOTAL_CAP:-150}"
RUN_ID="${TB21_OFFICIAL_RUN_ID:-tb21_qwen_official_$(date -u +%Y%m%dt%H%M%sz)}"
SCRIPT_REL="scripts/stage_tb21_official_qwen_launcher.sh"

usage() {
  cat <<USAGE
Usage: $0 [--dry-run|--execute] [--mode medium|xhigh] [--attempts all|1]
          [--concurrency 32|64|89|100] [--model Qwen/Qwen3-Coder-30B-A3B-Instruct] [--relay-url URL]
          [--timeout-sec 7200] [--run-id ID]

TB2.1 Qwen probe contract:
  agent/model: terminus-2 / Qwen/Qwen3-Coder-30B-A3B-Instruct
  attempts: 89 tasks x 1 single pass@1 sample; reducer reports single_pass_at_1
  timeout: global-timeout-multiplier=$TIMEOUT_MULTIPLIER, timeout-sec=$TIMEOUT_SEC
  concurrency staging: 32 -> 64 -> 89 -> 100; default dry-run prints all tiers, --execute runs selected tier
  output: new runs root $OUTPUT_ROOT and scores under $SCORES_DIR
  qwen_reference: single pass@1 compatibility probe; no TB2.1 official Qwen anchor is claimed.
  model traffic: dev relay $RELAY_URL
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|--print-only) EXECUTE=0; shift ;;
    --execute) EXECUTE=1; shift ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --attempt|--attempts|--round|--rounds) ATTEMPTS_SPEC="${2:-}"; shift 2 ;;
    --attempt-count) ATTEMPTS="${2:-}"; shift 2 ;;
    --concurrency|-c) CONCURRENCY="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --relay-url|--api-base) RELAY_URL="${2:-}"; shift 2 ;;
    --timeout-sec) TIMEOUT_SEC="${2:-}"; shift 2 ;;
    --timeout-multiplier) TIMEOUT_MULTIPLIER="${2:-}"; shift 2 ;;
    --run-id|--tag) RUN_ID="${2:-}"; shift 2 ;;
    --runner) RUNNER="${2:-}"; shift 2 ;;
    --image-manifest|--manifest) IMAGE_MANIFEST="${2:-}"; shift 2 ;;
    --dataset) DATASET="${2:-}"; shift 2 ;;
    --image-map) IMAGE_MAP="${2:-}"; shift 2 ;;
    --output-root) OUTPUT_ROOT="${2:-}"; shift 2 ;;
    --scores-dir) SCORES_DIR="${2:-}"; shift 2 ;;
    --pod-endpoint) POD_A_ENDPOINT="${2:-}"; shift 2 ;;
    --assumed-full500-concurrency) ASSUMED_FULL500_CONCURRENCY="${2:-}"; shift 2 ;;
    --relay-cap) RELAY_CAP="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$MODE" in medium|xhigh) ;; *) echo "mode must be medium or xhigh: $MODE" >&2; exit 2 ;; esac
case "$MODEL" in Qwen/Qwen3-Coder-30B-A3B-Instruct) ;; *) echo "Qwen probe model must be Qwen/Qwen3-Coder-30B-A3B-Instruct: $MODEL" >&2; exit 2 ;; esac
case "$CONCURRENCY" in ''|*[!0-9]*) echo "concurrency must be a positive integer" >&2; exit 2 ;; esac
case "$ATTEMPTS" in ''|*[!0-9]*) echo "attempt count must be an integer" >&2; exit 2 ;; esac
case "$ASSUMED_FULL500_CONCURRENCY" in ''|*[!0-9]*) echo "assumed full500 concurrency must be an integer" >&2; exit 2 ;; esac
case "$RELAY_CAP" in ''|*[!0-9]*) echo "relay cap must be an integer" >&2; exit 2 ;; esac
case "$TIMEOUT_SEC" in ''|*[!0-9]*) echo "timeout-sec must be an integer" >&2; exit 2 ;; esac
if [[ "$ATTEMPTS" -ne 1 ]]; then echo "official attempt count must be 1" >&2; exit 2; fi
if [[ "$TIMEOUT_MULTIPLIER" != "1.0" ]]; then echo "official timeout multiplier must be 1.0" >&2; exit 2; fi
if [[ "$TIMEOUT_SEC" -lt 7200 ]]; then echo "timeout-sec must be >= official 7200" >&2; exit 2; fi
case " $CONCURRENCY_TIERS " in *" $CONCURRENCY "*) ;; *) echo "concurrency must be one of staged tiers: $CONCURRENCY_TIERS" >&2; exit 2 ;; esac
if [[ $(( CONCURRENCY + ASSUMED_FULL500_CONCURRENCY )) -gt "$RELAY_CAP" && "${TB21_ALLOW_RELAY_OVER_CAP:-0}" != "1" ]]; then
  echo "blocked: relay concurrency budget exceeded: tb21=$CONCURRENCY full500=$ASSUMED_FULL500_CONCURRENCY cap=$RELAY_CAP" >&2
  echo "set TB21_ALLOW_RELAY_OVER_CAP=1 only with lead approval" >&2
  exit 24
fi

cd "$REPO_ROOT"
mkdir -p "$STAGE_DIR" "$SCORES_DIR"
LEDGER="$STAGE_DIR/${RUN_ID}_${MODE}_c${CONCURRENCY}_ledger.json"
SCORES_JSON="$SCORES_DIR/${RUN_ID}_${MODE}_c${CONCURRENCY}_scores.json"
SCORES_MD="$SCORES_DIR/${RUN_ID}_${MODE}_c${CONCURRENCY}_scores.md"
SCORES_YAML="$SCORES_DIR/${RUN_ID}_${MODE}_c${CONCURRENCY}_scores.yaml"

resolve_attempts() {
  if [[ "$ATTEMPTS_SPEC" == "all" ]]; then
    printf '1\n'
    return
  fi
  local spec="${ATTEMPTS_SPEC//,/ }"
  local r
  for r in $spec; do
    case "$r" in 1) printf '%s\n' "$r" ;; *) echo "attempt must be 1 or all: $r" >&2; exit 2 ;; esac
  done
}

ensure_image_map() {
  [[ -x "$RUNNER" ]] || { echo "blocked: privileged runner missing or not executable: $RUNNER" >&2; exit 24; }
  [[ -f "$IMAGE_MANIFEST" ]] || { echo "blocked: r7 image manifest missing: $IMAGE_MANIFEST" >&2; exit 24; }
  [[ -d "$DATASET" ]] || { echo "blocked: r7 dataset missing: $DATASET" >&2; exit 24; }
  if [[ ! -f "$IMAGE_MAP" ]]; then
    if [[ ! -f "$IMAGE_MAP_BUILDER" ]]; then
      echo "blocked: image map missing and build_tb21_prebuilt_image_map.py unavailable: $IMAGE_MAP" >&2
      exit 24
    fi
    python3 "$IMAGE_MAP_BUILDER" "$IMAGE_MANIFEST" --prefer local --task-root "$DATASET" --output "$IMAGE_MAP" >/dev/null
  fi
  python3 - "$DATASET" "$IMAGE_MAP" <<'PY_VALIDATE'
import json, sys
from pathlib import Path

dataset = Path(sys.argv[1])
image_map = Path(sys.argv[2])
tasks = sorted(p.name for p in dataset.iterdir() if p.is_dir() and ((p / "task.yaml").is_file() or (p / "task.toml").is_file()))
if len(tasks) != 89:
    raise SystemExit(f"blocked: dataset task count is {len(tasks)}, expected 89: {dataset}")
mapping = json.loads(image_map.read_text())
if len(mapping) != 89:
    raise SystemExit(f"blocked: image map count is {len(mapping)}, expected 89: {image_map}")
missing = sorted(set(tasks) - set(mapping))
extra = sorted(set(mapping) - set(tasks))
if missing or extra:
    raise SystemExit(f"blocked: image map mismatch missing={missing} extra={extra}")
print(json.dumps({"dataset_count": len(tasks), "image_map_count": len(mapping), "image_map": str(image_map)}, sort_keys=True))
PY_VALIDATE
}

write_checklist() {
  local checklist="$STAGE_DIR/${RUN_ID}_${MODE}_c${CONCURRENCY}_preflight.md"
  cat > "$checklist" <<CHECKLIST
# TB2.1 Qwen launch preflight

Status: staged only. Do not launch until orchestrator sends GO.

- Reference: Qwen lane is a single pass@1 compatibility probe; no official TB2.1 Qwen anchor is claimed.
- This launch: 1 independent pass@1 sample over 89 tasks; reducer reports single_pass_at_1, with +/-4-5pp sampling drift expected.
- Timeout: global-timeout-multiplier=1.0; task timeout env set to $TIMEOUT_SEC seconds.
- Concurrency staging: 32 -> 64 -> 89 -> 100. This staged command uses c=$CONCURRENCY.
- Pod: Pod A $POD_A_ENDPOINT with privileged dockerd at unix:///var/run/docker.sock.
- Dataset: $DATASET.
- Image manifest: $IMAGE_MANIFEST.
- Image map: $IMAGE_MAP.
- Runner: $RUNNER.
- Ledger: $LEDGER.
- Scores: $SCORES_JSON / $SCORES_MD / $SCORES_YAML.
- Relay: $RELAY_URL via dev relay; API env source: $API_ENV; API key presence is checked at execute time and never logged.
- Relay budget guard: TB2.1 $CONCURRENCY + assumed SWE-V full500 $ASSUMED_FULL500_CONCURRENCY <= $RELAY_CAP.
CHECKLIST
  echo "checklist=$checklist"
}

print_tmux_commands() {
  echo "[stage] local tmux launch commands after orchestrator GO:"
  local tier session remote_cmd
  for tier in $CONCURRENCY_TIERS; do
    session="tb21_qwen_${MODE}_c${tier}"
    remote_cmd="cd $REPO_ROOT && bash $SCRIPT_REL --execute --mode $MODE --attempts all --concurrency $tier --model $MODEL --relay-url $RELAY_URL --run-id $RUN_ID"
    printf '[stage] tier=%s remote_cmd=%s
' "$tier" "$remote_cmd"
    printf '[stage] tier=%s command=tmux new-session -d -s %s "ssh %s %s bash -lc %q"
' "$tier" "$session" "$POD_A_SSH_OPTS" "$POD_A_ENDPOINT" "$remote_cmd"
  done
}

execute_host_preflight() {
  if [[ -z "${OPENAI_API_KEY:-${API_KEY:-}}" && -f "$API_ENV" ]]; then
    set -a
    # Source without echoing secrets; --relay-url still controls OPENAI_BASE_URL during run_attempt.
    source "$API_ENV" >/dev/null 2>&1 || true
    set +a
  fi
  export DOCKER_HOST="unix:///var/run/docker.sock"
  export TB21_ALLOW_PRIVILEGED_DOCKER=1
  ulimit -n 65535 || true
  local nofile
  nofile=$(ulimit -n)
  if [[ "$nofile" -lt 65535 ]]; then
    echo "blocked: ulimit -n is $nofile, expected >=65535" >&2
    exit 24
  fi
  [[ -S /var/run/docker.sock ]] || { echo "blocked: /var/run/docker.sock missing" >&2; exit 24; }
  docker info >/dev/null
  local effective_api_key="${OPENAI_API_KEY:-${API_KEY:-}}"
  if [[ -z "$effective_api_key" || "$effective_api_key" == "EMPTY" ]]; then
    echo "blocked: OPENAI_API_KEY/API_KEY missing for terminus-2" >&2
    exit 24
  fi
  export OPENAI_API_KEY="$effective_api_key"
}

init_ledger() {
  python3 scripts/tb21_qwen_official_ledger.py init \
    --ledger "$LEDGER" \
    --run-id "$RUN_ID" \
    --agent terminus-2 \
    --model "$MODEL" \
    --mode "$MODE" \
    --attempts "$ATTEMPTS" \
    --concurrency "$CONCURRENCY" \
    --timeout-multiplier "$TIMEOUT_MULTIPLIER" \
    --timeout-sec "$TIMEOUT_SEC" \
    --dataset "$DATASET" \
    --image-manifest "$IMAGE_MANIFEST" \
    --output-root "$OUTPUT_ROOT" \
    --relay-url "$RELAY_URL"
}

record_attempt() {
  local attempt="$1"
  local attempt_root="$2"
  python3 scripts/tb21_qwen_official_ledger.py record --ledger "$LEDGER" --attempt "$attempt" --run-root "$attempt_root"
}

finalize_scores() {
  python3 scripts/tb21_qwen_official_ledger.py finalize \
    --ledger "$LEDGER" \
    --scores-json "$SCORES_JSON" \
    --scores-md "$SCORES_MD" \
    --scores-yaml "$SCORES_YAML"
}

run_attempt() {
  local attempt="$1"
  local tag="${RUN_ID}_attempt${attempt}_${MODE}_c${CONCURRENCY}"
  local attempt_output_root="$OUTPUT_ROOT/$RUN_ID/${MODE}_c${CONCURRENCY}/attempt_${attempt}"
  local attempt_run_root="$attempt_output_root/tb21_batched_terminus-2_${tag}"
  if [[ -f "$attempt_run_root/attempt.done" ]]; then
    echo "[stage] attempt=$attempt already_done run_root=$attempt_run_root"
    record_attempt "$attempt" "$attempt_run_root"
    return 0
  fi
  export DOCKER_HOST="unix:///var/run/docker.sock"
  export TB21_ALLOW_PRIVILEGED_DOCKER=1
  export TB21_PRIVILEGED_DOCKER_HOST="unix:///var/run/docker.sock"
  export TB21_FULL89_IMAGE_MANIFEST="$IMAGE_MANIFEST"
  export TB21_FULL89_IMAGE_MAP="$IMAGE_MAP"
  export TB21_FULL89_DATASET="$DATASET"
  export TB21_BATCH_SIZE=89
  export TB21_BATCH_START=1
  export TB21_BATCH_LIMIT=0
  export TB21_FULL_CONCURRENCY="$CONCURRENCY"
  export TB21_FULL_TAG="$tag"
  export TB21_BATCH_DIR="$STAGE_DIR/batches_${tag}"
  export TB21_BATCH_PLAN_JSON="$TB21_BATCH_DIR/plan.json"
  export TB21_RUNTIME_CLOSURE_REPORT_DIR="$STAGE_DIR/runtime_closure_${tag}"
  export TB21_BIND_PAYLOAD_PREFLIGHT_JSON="$STAGE_DIR/tb21_bind_payload_preflight_${tag}.json"
  export BENCH_OUTPUT_ROOT="$attempt_output_root"
  export TB_AGENT=terminus-2
  export TB_MANIFEST_AGENT=terminus-2
  export MODEL_NAME="$MODEL"
  export LITELLM_MODEL="openai/$MODEL"
  export TB_MODEL="openai/$MODEL"
  export OPENAI_BASE_URL="$RELAY_URL"
  export BASE_URL="$RELAY_URL"
  export TB_GLOBAL_TIMEOUT_MULTIPLIER="$TIMEOUT_MULTIPLIER"
  export TB_GLOBAL_AGENT_TIMEOUT_SEC="$TIMEOUT_SEC"
  export TB_GLOBAL_TEST_TIMEOUT_SEC="$TIMEOUT_SEC"
  export TB21_EXPECT_CLEAN=0
  export TB21_ALLOW_ORACLE_SCORE=0
  export TB21_STRICT_CLOSURE_GATE=1
  export TB21_STATIC_RUNTIME_CLOSURE_GATE=1
  export TB21_BIND_PAYLOAD_PREFLIGHT=1
  export TB21_PREHEAT_PULL=1
  export TB21_PREHEAT_FORCE_PULL=0
  export TB21_PREHEAT_LOAD_FALLBACK=1
  export TB21_PREHEAT_PULL_ATTEMPTS=3
  export TB21_PREHEAT_MAX_ATTEMPTS=2
  export TB21_RESTART_DOCKER_AFTER_BATCH=0
  export TB21_RUN_CLEANUP_HELPER=0
  export TB21_REMOVE_BATCH_IMAGES=0
  export TB_DOCKER_SDK_TIMEOUT_SEC=300
  export TB_DOCKER_SDK_API_VERSION=1.45
  export TB2_OFFLINE_TEST_BOOTSTRAP=1
  export TB2_SKIP_DATASET_REBUILD=1
  export TB2_USE_PREBUILT_IMAGES=1
  export TB_EXTRA_ARGS="${TB_EXTRA_ARGS:-}"
  if [[ "$MODE" == "xhigh" ]]; then
    export OPENAI_REASONING_EFFORT=xhigh
    export REASONING_EFFORT=xhigh
    export TB_AGENT_KWARGS="api_base=$RELAY_URL temperature=0.0 reasoning_effort=xhigh"
  else
    unset OPENAI_REASONING_EFFORT || true
    unset REASONING_EFFORT || true
    export TB_AGENT_KWARGS="api_base=$RELAY_URL temperature=0.0"
  fi
  echo "[stage] execute attempt=$attempt tag=$tag run_root=$attempt_run_root mode=$MODE concurrency=$CONCURRENCY timeout_multiplier=$TIMEOUT_MULTIPLIER timeout_sec=$TIMEOUT_SEC"
  if [[ "$MODE" == "medium" ]]; then
    env OPENAI_REASONING_EFFORT= REASONING_EFFORT= BENCH_DISABLE_REASONING_EFFORT_DEFAULT=1 TB21_SOURCE_REMOTE_BASHRC=0 bash "$RUNNER"
  else
    bash "$RUNNER"
  fi
  record_attempt "$attempt" "$attempt_run_root"
  touch "$attempt_run_root/attempt.done"
}

ensure_image_map
write_checklist
init_ledger
print_tmux_commands
if [[ "$EXECUTE" != "1" ]]; then
  echo "[stage] dry_run=1 run_id=$RUN_ID model=$MODEL agent=terminus-2 attempts=$ATTEMPTS single_pass_at_1=enabled qwen_no_official_anchor=1 single_run=1 mode=$MODE selected_concurrency=$CONCURRENCY tiers=[$CONCURRENCY_TIERS] timeout_multiplier=$TIMEOUT_MULTIPLIER timeout_sec=$TIMEOUT_SEC output_root=$OUTPUT_ROOT ledger=$LEDGER"
  exit 0
fi
execute_host_preflight
for attempt in $(resolve_attempts); do
  run_attempt "$attempt"
done
finalize_scores
echo "[stage] done execute=1 run_id=$RUN_ID mode=$MODE concurrency=$CONCURRENCY ledger=$LEDGER scores=$SCORES_JSON"
