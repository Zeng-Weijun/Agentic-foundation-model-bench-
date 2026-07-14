#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# run_repozero_offline.sh — RepoZero Py2JS OFFICIAL-400 offline runner
#
# Turnkey wrapper around the committed Path A runner that produced the sealed
# 98/400 = 24.5% Coder bundle:
#   experiments/runs/repozero_coder_full400_147/scripts/repozero_full400_orchestrator.py
#   experiments/runs/repozero_coder_full400_147/scripts/repozero_qwencode_driver.py
# The driver carries RepoZero's OWN official judge (`eval_case`): for every hidden
# testcase sample it runs the compiled Python oracle and `node <entry>.mjs`, then
# compares normalized-line stdout; per-case all_pass = every sample matches. No
# model participates in scoring.
#
# This mirrors the env-var + --dry-run structure of the sibling
# run_{deepswe,nl2repo,swebench_multilingual}_offline.sh skeletons, but — unlike
# those — it can also run for real (behind --execute), because RepoZero's runner
# is fully wired and self-contained on the shared FS.
#
# ---- BOTH judging calibers are switchable (the two disclosed RepoZero caveats) ----
#   --eval-timeout {10|5}   per-sample oracle/node wall passed straight to the driver.
#                           10s = the committed run  -> 98/400 = 24.50% all_pass.
#                           5s  = RepoZero OFFICIAL (evaluate/eval_py2js_docker.py L52 & L59)
#                                 -> 95/400 = 23.75% (serving-free re-judge of the same .mjs;
#                                    see scripts/rejudge_official5s.py, AUDIT_NOTES.md §2).
#   --eval-node  {node20|node18}
#                           node20 = the mounted qwen node v20.20.2 the run ACTUALLY used
#                                    (start_container puts it first on the container PATH; the
#                                    eval's `docker exec ... node` resolves to it) — WIRED.
#                           node18 = the image's native node v18.19.1 ("official image node").
#                                    Analytical floor 97/400 = 24.25% (only rsa/test11 flips;
#                                    AUDIT_NOTES.md §3). A full node18 re-run needs a driver
#                                    PATH override that is NOT wired here -> fail-closed pointer.
#
# ---- WHERE THIS RUNS ----
#   On the KVM bench pod (Docker + shared FS mounted), against sglang serving on pod
#   .147: :30001 = Qwen3-Coder-30B-A3B-Instruct, :30000 = Qwen3-30B-A3B-Instruct-2507.
#   Task containers use the default bridge (in-container qwen-code must reach serving);
#   the offline pod + prompt contract are the anti-cheat, not --network none.
#
# ---- ×Instruct ----
#   To reproduce RepoZero × Instruct-2507, point at :30000 and swap the model:
#     REPOZERO_BASE_URL=http://100.100.104.147:30000/v1 \
#     REPOZERO_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507 ... --execute
#   (No Instruct evidence bundle is committed yet — see REPRO_GAPS.md.)
# ============================================================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

MODE="${REPOZERO_MODE:-smoke}"
CASES="${REPOZERO_CASES:-}"
LIMIT="${REPOZERO_LIMIT:-}"
WORKERS="${REPOZERO_WORKERS:-4}"
EVAL_TIMEOUT="${REPOZERO_EVAL_TIMEOUT:-10}"
EVAL_NODE="${REPOZERO_EVAL_NODE:-node20}"
BASE_URL="${REPOZERO_BASE_URL:-${OPENAI_BASE_URL:-http://100.100.104.147:30001/v1}}"
MODEL="${REPOZERO_MODEL:-Qwen/Qwen3-Coder-30B-A3B-Instruct}"
RZ_ROOT="${REPOZERO_RZ_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero}"
IMAGE="${REPOZERO_IMAGE:-ghcr.io/jessezzzzz/repoarena-new:latest}"
SHARED_TAR="${REPOZERO_SHARED_TAR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar}"
QWEN_ROOT="${REPOZERO_QWEN_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/.npm-root}"
ORCH_DEFAULT="$REPO_ROOT/experiments/runs/repozero_coder_full400_147/scripts/repozero_full400_orchestrator.py"
ORCHESTRATOR="${REPOZERO_ORCHESTRATOR:-$ORCH_DEFAULT}"
RUN_NAME="${REPOZERO_RUN_NAME:-repozero_offline_$(date -u +%Y%m%dT%H%M%SZ)}"
PYTHON_BIN="${REPOZERO_PYTHON:-python3}"
RESUME=0
EXECUTE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_repozero_offline.sh [--dry-run|--execute] [--mode smoke|full]
         [--cases "lib/testN.py ..."] [--limit N] [--workers N]
         [--eval-timeout 10|5] [--eval-node node20|node18]
         [--base-url URL] [--model NAME] [--run-name NAME] [--resume]

RepoZero Py2JS OFFICIAL-400 offline runner. Wraps the committed Path A
orchestrator + driver (RepoZero's own oracle-vs-node all_pass judge; no model in
the judge). Default endpoint is :30001 (Qwen3-Coder); default caliber is the
committed 10s / qwen-node-v20 (98/400 = 24.5%).

Modes:
  smoke   run the first N cases (default N=4 unless --cases/--limit given).
  full    run all 400 official valid_ids.

Calibers (switchable):
  --eval-timeout 10   committed run  -> 98/400 = 24.50% all_pass (default).
  --eval-timeout 5    RepoZero OFFICIAL -> 95/400 = 23.75% (stricter, faithful).
  --eval-node node20  as-run mounted qwen node v20.20.2 (default, WIRED).
  --eval-node node18  official image node v18.19.1 -> floor 97/400 = 24.25%
                      (analytical, AUDIT_NOTES.md §3); full node18 re-run NOT wired.

Execution:
  --dry-run   print the resolved plan as JSON and exit (safe anywhere).
  --execute   actually run (KVM pod + shared-FS assets + live serving required).
              Without --execute (and without --dry-run) the script prints the plan
              and exits 0 (guard), so a bare invocation never hits shared serving.

Key env overrides: REPOZERO_{MODE,CASES,LIMIT,WORKERS,EVAL_TIMEOUT,EVAL_NODE,
  BASE_URL,MODEL,RZ_ROOT,IMAGE,SHARED_TAR,QWEN_ROOT,ORCHESTRATOR,RUN_NAME,PYTHON}.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --execute) EXECUTE=1; shift ;;
    --mode) MODE="${2:?missing value for --mode}"; shift 2 ;;
    --cases) CASES="${2:?missing value for --cases}"; shift 2 ;;
    --limit) LIMIT="${2:?missing value for --limit}"; shift 2 ;;
    --workers|--concurrency) WORKERS="${2:?missing value for --workers}"; shift 2 ;;
    --eval-timeout) EVAL_TIMEOUT="${2:?missing value for --eval-timeout}"; shift 2 ;;
    --eval-node) EVAL_NODE="${2:?missing value for --eval-node}"; shift 2 ;;
    --base-url) BASE_URL="${2:?missing value for --base-url}"; shift 2 ;;
    --model) MODEL="${2:?missing value for --model}"; shift 2 ;;
    --rz-root) RZ_ROOT="${2:?missing value for --rz-root}"; shift 2 ;;
    --image) IMAGE="${2:?missing value for --image}"; shift 2 ;;
    --shared-tar) SHARED_TAR="${2:?missing value for --shared-tar}"; shift 2 ;;
    --orchestrator) ORCHESTRATOR="${2:?missing value for --orchestrator}"; shift 2 ;;
    --run-name) RUN_NAME="${2:?missing value for --run-name}"; shift 2 ;;
    --resume) RESUME=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 64 ;;
  esac
done

case "$MODE" in
  smoke|full) ;;
  *) echo "unsupported RepoZero mode: $MODE" >&2; exit 64 ;;
esac
case "$EVAL_NODE" in
  node20|node18) ;;
  *) echo "unsupported --eval-node: $EVAL_NODE (want node20|node18)" >&2; exit 64 ;;
esac
if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [[ "$WORKERS" -lt 1 ]]; then
  echo "REPOZERO_WORKERS must be a positive integer (RepoZero serving is shared; keep <=8)" >&2
  exit 64
fi
if ! [[ "$EVAL_TIMEOUT" =~ ^[0-9]+$ ]] || [[ "$EVAL_TIMEOUT" -lt 1 ]]; then
  echo "--eval-timeout must be a positive integer (10 = committed, 5 = official)" >&2
  exit 64
fi
if [[ -n "$LIMIT" ]] && ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "--limit must be a non-negative integer" >&2
  exit 64
fi

# Effective limit: smoke defaults to first 4 cases unless an explicit case list or
# limit was given; full runs the whole official 400 (limit=0 = no cap).
EFFECTIVE_LIMIT="${LIMIT:-}"
if [[ -z "$EFFECTIVE_LIMIT" ]]; then
  if [[ "$MODE" == "smoke" && -z "$CASES" ]]; then EFFECTIVE_LIMIT=4; else EFFECTIVE_LIMIT=0; fi
fi

ORCH_EXISTS=0;   [[ -f "$ORCHESTRATOR" ]] && ORCH_EXISTS=1
RZ_ROOT_EXISTS=0; [[ -d "$RZ_ROOT" ]] && RZ_ROOT_EXISTS=1
IMAGE_TAR_EXISTS=0; [[ -f "$SHARED_TAR" ]] && IMAGE_TAR_EXISTS=1
QWEN_ROOT_EXISTS=0; [[ -d "$QWEN_ROOT" ]] && QWEN_ROOT_EXISTS=1

# ---- resolved orchestrator command (this is what --execute runs and --dry-run prints) ----
planned=("$PYTHON_BIN" "$ORCHESTRATOR"
  --run-name "$RUN_NAME" --workers "$WORKERS"
  --base-url "$BASE_URL" --model "$MODEL"
  --rz-root "$RZ_ROOT" --image "$IMAGE" --shared-tar "$SHARED_TAR"
  --eval-timeout "$EVAL_TIMEOUT")
if [[ "$EFFECTIVE_LIMIT" != "0" ]]; then planned+=(--limit "$EFFECTIVE_LIMIT"); fi
if [[ -n "$CASES" ]]; then planned+=(--cases $CASES); fi
if [[ "$RESUME" == "1" ]]; then planned+=(--resume); fi

if [[ "$DRY_RUN" == "1" ]]; then
  "$PYTHON_BIN" - <<'REPOZERO_RUNNER_JSON' "$MODE" "$WORKERS" "$EVAL_TIMEOUT" "$EVAL_NODE" "$BASE_URL" "$MODEL" "$RZ_ROOT" "$IMAGE" "$SHARED_TAR" "$QWEN_ROOT" "$ORCHESTRATOR" "$RUN_NAME" "$EFFECTIVE_LIMIT" "$CASES" "$ORCH_EXISTS" "$RZ_ROOT_EXISTS" "$IMAGE_TAR_EXISTS" "$QWEN_ROOT_EXISTS" "${planned[@]}"
import json, sys
(mode, workers, eval_timeout, eval_node, base_url, model, rz_root, image, shared_tar,
 qwen_root, orchestrator, run_name, limit, cases,
 orch_exists, rz_exists, tar_exists, qwen_exists) = sys.argv[1:19]
planned = sys.argv[19:]
caliber = {
    ("10", "node20"): "committed headline: 98/400 = 24.50% all_pass",
    ("5",  "node20"): "RepoZero official 5s: 95/400 = 23.75% (rejudge_official5s.py)",
    ("10", "node18"): "node-image floor: 97/400 = 24.25% (analytical, AUDIT_NOTES.md §3; NOT wired)",
}.get((eval_timeout, eval_node), "non-standard caliber combination")
print(json.dumps({
    "status": "dry_run",
    "bench_id": "repozero_py2js",
    "mode": mode,
    "denominator": "official 400 valid_ids (smoke = first N)",
    "workers": int(workers),
    "eval_timeout_s": int(eval_timeout),
    "eval_node": eval_node,
    "caliber": caliber,
    "base_url": base_url,
    "model": model,
    "served_identity_note": "sglang does NOT validate the model field; pin identity by "
                            "(port, /get_model_info model_path, random_seed), never the echoed name",
    "rz_root": rz_root,
    "image": image,
    "shared_tar": shared_tar,
    "qwen_root": qwen_root,
    "orchestrator": orchestrator,
    "run_name": run_name,
    "limit": int(limit),
    "cases": cases or None,
    "planned_command": planned,
    "execute_requires": [
        f"orchestrator present: {orch_exists == '1'} ({orchestrator})",
        f"RepoZero checkout present: {rz_exists == '1'} ({rz_root})",
        f"repoarena-new image tar present: {tar_exists == '1'} ({shared_tar})",
        f"qwen-native node root present: {qwen_exists == '1'} ({qwen_root})",
        "live sglang serving Qwen3-Coder at base_url (preflight /v1/models)",
        "Docker daemon reachable (per-case repoarena-new container, default bridge)",
    ],
    "node18_caveat": "eval-node=node18 is a documented floor only; the driver eval resolves "
                     "`node` to the mounted qwen v20 via PATH, so a real node18 run needs a "
                     "driver PATH override that is not wired -> --execute fails closed for node18",
}, indent=2, sort_keys=True))
REPOZERO_RUNNER_JSON
  exit 0
fi

# ---- node18 full re-run is not wired (see AUDIT_NOTES.md §3) ----
if [[ "$EVAL_NODE" == "node18" ]]; then
  cat >&2 <<EOF
--eval-node node18 selected: a FULL node18 re-run is not wired.
The committed driver's eval resolves \`node\` to the mounted qwen node v20.20.2
(start_container puts it first on the container PATH). node18 is the official
image node v18.19.1; its effect is a single-case 0.25pp seam (only rsa/test11
flips) giving the analytical floor 97/400 = 24.25%.
To reproduce the floor, follow experiments/runs/repozero_coder_full400_147/AUDIT_NOTES.md §3
(re-score the 10 crypto/RSA all_pass cases under image node18), or add a PATH
override in repozero_qwencode_driver.py::dexec_plain before wiring a full run.
EOF
  exit 78
fi

# ---- guard: real execution must be explicit ----
if [[ "$EXECUTE" != "1" ]]; then
  echo "[repozero] plan only. Re-run with --execute to launch (KVM pod + shared FS + live serving)." >&2
  printf '  %q' "${planned[@]}"; echo >&2
  exit 0
fi

# ---- preconditions ----
missing=0
[[ "$ORCH_EXISTS" == "1" ]]    || { echo "missing orchestrator: $ORCHESTRATOR" >&2; missing=1; }
[[ "$RZ_ROOT_EXISTS" == "1" ]] || { echo "missing RepoZero checkout: $RZ_ROOT" >&2; missing=1; }
[[ "$QWEN_ROOT_EXISTS" == "1" ]] || { echo "missing qwen-native node root: $QWEN_ROOT" >&2; missing=1; }
if [[ "$IMAGE_TAR_EXISTS" != "1" ]] && ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "repoarena-new not loaded and no shared tar at: $SHARED_TAR" >&2
  echo "  stage it with scripts/stage_repozero_image.sh --execute, or docker load the tar" >&2
  missing=1
fi
[[ "$missing" == "0" ]] || exit 66

# ---- serving preflight: base_url must actually serve the requested weights family ----
info_url="${BASE_URL%/v1}"
if ! curl -s --noproxy '*' --max-time 12 "$BASE_URL/models" >/dev/null 2>&1; then
  echo "[preflight][FAIL] $BASE_URL unreachable" >&2; exit 3
fi
want_family="Qwen3-Coder"; [[ "$MODEL" == *"Instruct-2507"* ]] && want_family="Qwen3-30B-A3B-Instruct-2507"
if ! curl -s --noproxy '*' --max-time 12 "$info_url/get_model_info" 2>/dev/null | grep -q "$want_family"; then
  echo "[preflight][WARN] $info_url/get_model_info does not report $want_family;" >&2
  echo "  pin identity by /get_model_info model_path + random_seed before trusting the score." >&2
fi
echo "[preflight][OK] $BASE_URL reachable; caliber: eval_timeout=${EVAL_TIMEOUT}s node=${EVAL_NODE}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"
ulimit -n 65535 2>/dev/null || true

echo "[repozero] launching: run_name=$RUN_NAME workers=$WORKERS mode=$MODE limit=$EFFECTIVE_LIMIT"
"${planned[@]}"
