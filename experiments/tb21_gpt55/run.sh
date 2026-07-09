#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Reproduce: TB2.1 x GPT-5.5 x terminus-2, single pass@1, c89, medium/default
#
#   canonical run_id : tb21_gpt55_official_medium_c89_single_20260704t195417z
#   expected score   : 63/89 = 70.8%   (corrected; raw reducer 62/89 is DO-NOT-QUOTE)
#   official anchor  : 78.2% +/- 2.4   (5-run mean -- NOT comparable to one sample)
#
# Per orchestrator ruling 2026-07-09 (C1 = ACK), this is a RE-MEASUREMENT under
# today's environment, not a strict reproduction: the canonical runner file is git
# untracked and was rewritten on 2026-07-07, so it cannot be restored.
#
# Intended difference from the canonical run:
#   relay   canonical http://100.96.122.22:18540/v1  ->  here http://100.96.122.87:18540/v1
# Two further changes exist only to PRESERVE canonical semantics, both declared in
# config.yaml -> deviations_from_canonical:
#   - TB21_ENABLE_KVM_DEVICE=0  (today's runner defaults it to 1; canonical was no-KVM)
#   - a fresh run_id / canary tag (never overwrite the preserved 70.8% artifacts)
# Plus, per C2 = option A, the two closure-gate helpers were vendored into the r3
# worktree; their sha256 are recorded in config.yaml -> closure_gate_helpers.
#
# Every constant lives in ./config.yaml. This script holds none of its own.
# No API key is read, printed, or stored here: it is sourced on the pod from the
# api_config.env recorded in config.yaml.
#
# Usage:
#   ./run.sh --dry-run              # full89: print resolved env + remote command
#   ./run.sh --preflight-only       # full89: read-only remote gate checks, launch nothing
#   ./run.sh --execute              # full89: preflight, then launch via the stage launcher
#   ./run.sh --canary --dry-run     # canary: print the 3-task plan + runner env
#   ./run.sh --canary               # canary: preflight, build subset manifest, launch 3 tasks
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CONFIG="${TB21_REPRO_CONFIG:-$SCRIPT_DIR/config.yaml}"
MODE_ACTION=""
CANARY=0
RUN_ID_OVERRIDE=""

usage() { sed -n '4,33p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|--print-only) MODE_ACTION="dry-run"; shift ;;
    --preflight-only)       MODE_ACTION="preflight"; shift ;;
    --execute)              MODE_ACTION="execute"; shift ;;
    --canary)               CANARY=1; shift ;;
    --config)               CONFIG="${2:-}"; shift 2 ;;
    --run-id)               RUN_ID_OVERRIDE="${2:-}"; shift 2 ;;
    -h|--help)              usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# Defaults differ by lane, on purpose:
#   full89 with no action  -> dry-run  (never launch 89 tasks by accident)
#   --canary with no action -> go      (the canary IS the requested action)
if [[ -z "$MODE_ACTION" ]]; then
  if [[ "$CANARY" == 1 ]]; then MODE_ACTION="execute"; else MODE_ACTION="dry-run"; fi
fi

[[ -f "$CONFIG" ]] || { echo "blocked: config not found: $CONFIG" >&2; exit 24; }

# --- config reader -----------------------------------------------------------
cfg() {
  python3 - "$CONFIG" "$1" <<'PY'
import sys, yaml
node = yaml.safe_load(open(sys.argv[1]))
for part in sys.argv[2].split("."):
    if not isinstance(node, dict) or part not in node:
        sys.exit(f"blocked: config key missing: {sys.argv[2]}")
    node = node[part]
if isinstance(node, (dict, list)):
    sys.exit(f"blocked: config key is not a scalar: {sys.argv[2]}")
if node is None or str(node) == "ABSENT":
    sys.exit(f"blocked: config key is ABSENT: {sys.argv[2]}")
print(node)
PY
}
cfg_list() {  # space-separated
  python3 - "$CONFIG" "$1" <<'PY'
import sys, yaml
node = yaml.safe_load(open(sys.argv[1]))
for part in sys.argv[2].split("."):
    node = node[part]
print(" ".join(str(x) for x in node))
PY
}

BENCH="$(cfg bench)"
MODEL="$(cfg model)"
AGENT="$(cfg harness.agent)"
CONCURRENCY="$(cfg concurrency)"
TIMEOUT_SEC="$(cfg timeout_sec)"
TIMEOUT_MULTIPLIER="$(cfg timeout_multiplier)"
N_ATTEMPTS="$(cfg n_attempts)"
DATASET="$(cfg dataset)"
IMAGE_MANIFEST="$(cfg image_manifest)"
IMAGE_MAP="$(cfg image_map)"
RUNNER="$(cfg runner)"
RELAY_URL="$(cfg relay_endpoint)"
RELAY_CANONICAL="$(cfg relay_endpoint_canonical)"
API_ENV="$(cfg relay_api_env)"
API_KEY_VAR="$(cfg relay_api_key_var)"

LAUNCHER_ROOT="$(cfg launcher.repo_root)"
LAUNCHER_REL="$(cfg launcher.script_rel)"
LAUNCH_MODE="$(cfg launcher.mode)"
ATTEMPTS_SPEC="$(cfg launcher.attempts_spec)"

POD_SSH="$(cfg execution_host.ssh)"
KVM_DEVICE="$(cfg env_overrides.TB21_ENABLE_KVM_DEVICE)"
STATIC_GATE="$(cfg static_runtime_closure_gate)"

RUN_ID_PREFIX="$(cfg run_id_prefix)"
CANONICAL_RUN_ID="$(cfg canonical.run_id)"
EXPECTED_RESOLVED="$(cfg score_reference.corrected_resolved)"
EXPECTED_TOTAL="$(cfg score_reference.corrected_total)"
EXPECTED_PCT="$(cfg score_reference.corrected_pct)"

STAMP="$(date -u +%Y%m%dt%H%M%SZ)"
RUN_ID="${RUN_ID_OVERRIDE:-${RUN_ID_PREFIX}_${STAMP}}"
if [[ "$RUN_ID" == "$CANONICAL_RUN_ID" ]]; then
  echo "blocked: refusing to reuse the canonical run_id -- it would overwrite the preserved ${EXPECTED_PCT} artifacts" >&2
  exit 24
fi

[[ "$N_ATTEMPTS" == "1" ]]            || { echo "blocked: official attempt count must be 1, got $N_ATTEMPTS" >&2; exit 24; }
[[ "$TIMEOUT_MULTIPLIER" == "1.0" ]]  || { echo "blocked: official timeout multiplier must be 1.0, got $TIMEOUT_MULTIPLIER" >&2; exit 24; }
[[ "$TIMEOUT_SEC" -ge 7200 ]]         || { echo "blocked: timeout-sec must be >= 7200, got $TIMEOUT_SEC" >&2; exit 24; }

# ================================ CANARY ======================================
if [[ "$CANARY" == 1 ]]; then
  CANARY_TASKS="$(cfg_list canary.tasks)"
  CANARY_BATCH_SIZE="$(cfg canary.batch_size)"
  CANARY_CONC="$(cfg canary.concurrency)"
  CANARY_OUT_ROOT="$(cfg canary.output_root)"
  CANARY_STAGE_ROOT="$(cfg canary.stage_root)"
  CANARY_TAG_PREFIX="$(cfg canary.tag_prefix)"
  CANARY_TAG="${CANARY_TAG_PREFIX}_${STAMP}"
  CANARY_TAG_LC="$(printf '%s' "$CANARY_TAG" | tr '[:upper:]' '[:lower:]')"

  STAGE_DIR="$CANARY_STAGE_ROOT/$CANARY_TAG_LC"
  SUBSET_MANIFEST="$STAGE_DIR/terminal_bench_2_1_canary3_p0_closure_r7.yaml"
  LAUNCH_SH="$STAGE_DIR/launch.sh"
  CANARY_LOG="$STAGE_DIR/canary.log"
  RUNNER_ROOT="$(dirname "$(dirname "$RUNNER")")"

  # Runner env = launcher_exported_env_reference  +  medium-mode blanking
  #              +  canary.env_overrides  +  resolved paths.  Built in python so
  #              config stays the single source of truth.
  CANARY_ENV="$(python3 - "$CONFIG" "$SUBSET_MANIFEST" "$IMAGE_MAP" "$DATASET" "$RELAY_URL" "$CANARY_TAG_LC" "$CANARY_OUT_ROOT" "$STAGE_DIR" <<'PY'
import sys, yaml, shlex
cfg = yaml.safe_load(open(sys.argv[1]))
subset, imap, dataset, relay, tag, outroot, stage = sys.argv[2:9]
env = dict(cfg["launcher_exported_env_reference"])
for k, v in cfg["reasoning_effort_mechanics"]["env_blanked"].items():
    env[k] = v
env.update(cfg["canary"]["env_overrides"])
env.update({
    "TB21_FULL89_IMAGE_MANIFEST": subset,
    "TB21_FULL89_IMAGE_MAP": imap,
    "TB21_FULL89_DATASET": dataset,
    "OPENAI_BASE_URL": relay,
    "BASE_URL": relay,
    "TB_AGENT_KWARGS": f"api_base={relay} temperature=0.0",
    "TB_GLOBAL_TIMEOUT_MULTIPLIER": str(cfg["timeout_multiplier"]),
    "TB_GLOBAL_AGENT_TIMEOUT_SEC": str(cfg["timeout_sec"]),
    "TB_GLOBAL_TEST_TIMEOUT_SEC": str(cfg["timeout_sec"]),
    "TB21_FULL_TAG": tag,
    "BENCH_OUTPUT_ROOT": outroot,
    "TB21_BATCH_DIR": f"{stage}/batches",
    "TB21_BATCH_PLAN_JSON": f"{stage}/batches/plan.json",
    "TB21_RUNTIME_CLOSURE_REPORT_DIR": f"{stage}/reports",
    "TB21_BIND_PAYLOAD_PREFLIGHT_JSON": f"{stage}/reports/bind_payload_preflight_{tag}.json",
})
# never emit REPO_ROOT: the runner must derive it from its own script path
env.pop("REPO_ROOT", None)
print(" ".join(f"{k}={shlex.quote(str(v))}" for k, v in sorted(env.items())))
PY
)"

  cat <<PLAN
[canary] config              = $CONFIG
[canary] canonical_run_id    = $CANONICAL_RUN_ID   (baseline ${EXPECTED_RESOLVED}/${EXPECTED_TOTAL} = ${EXPECTED_PCT})
[canary] tag                 = $CANARY_TAG_LC
[canary] tasks (3)           = $CANARY_TASKS
[canary] bench / model/agent = $BENCH / $MODEL / $AGENT
[canary] effort              = ${LAUNCH_MODE}/default (no reasoning_effort arg)
[canary] batch_size / conc   = $CANARY_BATCH_SIZE / $CANARY_CONC
[canary] timeout             = multiplier $TIMEOUT_MULTIPLIER / ${TIMEOUT_SEC}s
[canary] attempts            = $N_ATTEMPTS
[canary] dataset (full 89)   = $DATASET
[canary] parent manifest     = $IMAGE_MANIFEST
[canary] subset manifest     = $SUBSET_MANIFEST
[canary] image_map (full 89) = $IMAGE_MAP
[canary] runner              = $RUNNER
[canary] runner REPO_ROOT    = $RUNNER_ROOT
[canary] relay (canonical)   = $RELAY_CANONICAL
[canary] relay (this run)    = $RELAY_URL     <-- ONLY intended deviation
[canary] kvm_device          = $KVM_DEVICE   <-- guard: runner default is 1
[canary] static_closure_gate = $STATIC_GATE  <-- canonical value, helpers vendored (C2/A)
[canary] stage dir           = $STAGE_DIR
[canary] log                 = $CANARY_LOG
[canary] api_env             = $API_ENV (key var $API_KEY_VAR; sourced on pod, never printed)

[canary] runner env:
$(echo "$CANARY_ENV" | tr ' ' '\n' | sed 's/^/[canary]   /')
PLAN

  if [[ "$MODE_ACTION" == "dry-run" ]]; then
    echo "[canary] dry_run=1 nothing launched"
    exit 0
  fi

  echo "[canary] --- remote preflight + subset manifest build ---"
  PRE=$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$POD_SSH" bash -s <<PF
set -uo pipefail
export NO_PROXY='*' no_proxy='*'
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
set -o noglob

[[ -S /var/run/docker.sock ]] && echo "sock=ok" || echo "sock=missing"
docker info >/dev/null 2>&1 && echo "docker=ok" || echo "docker=fail"
[[ -d "$DATASET" ]] && echo "dataset=ok" || echo "dataset=missing"
[[ -f "$IMAGE_MANIFEST" ]] && echo "manifest=ok" || echo "manifest=missing"
[[ -f "$IMAGE_MAP" ]] && echo "image_map=ok" || echo "image_map=missing"
[[ -x "$RUNNER" ]] && echo "runner=ok" || echo "runner=missing_or_not_executable"
[[ -f "$RUNNER_ROOT/scripts/build_tb21_full89_closure_matrix.py" ]] && echo "closure_helper=ok" || echo "closure_helper=missing"
[[ -f "$RUNNER_ROOT/scripts/tb21_runtime_closure_static_gate.py" ]] && echo "closure_gate_py=ok" || echo "closure_gate_py=missing"

set -a; source "$API_ENV" >/dev/null 2>&1 || true; set +a
[[ -n "\${$API_KEY_VAR:-}" ]] && echo "api_key=present" || echo "api_key=missing"

code=\$(curl -sS --noproxy '*' -m 12 -o /dev/null -w '%{http_code}' "${RELAY_URL%/v1}/v1/models" 2>/dev/null || echo 000)
echo "relay_http=\$code"

mkdir -p "$STAGE_DIR/batches" "$STAGE_DIR/reports"
python3 - "$IMAGE_MANIFEST" "$SUBSET_MANIFEST" $CANARY_TASKS <<'PYSUB'
import sys, yaml
src, dst, *want = sys.argv[1:]
data = yaml.safe_load(open(src))
imgs = data.get("images") or []
have = {str(r.get("task") or r.get("id")): r for r in imgs}
missing = [t for t in want if t not in have]
if missing:
    raise SystemExit(f"subset_manifest=FAIL missing_tasks={missing}")
sel = [have[t] for t in want]
out = dict(data)
out["status"] = "canary3_subset_of_" + str(data.get("status"))
out["parent_manifest"] = src
out["images"] = sel
out["coverage"] = {"images_in_subset": len(sel), "total_parent_images": len(imgs)}
yaml.safe_dump(out, open(dst, "w"), sort_keys=False, allow_unicode=False)
print(f"subset_manifest=ok images={len(sel)} tasks={[str(r.get('task')) for r in sel]}")
PYSUB
PF
) || { echo "blocked: canary preflight ssh failed" >&2; exit 24; }
  echo "$PRE" | sed 's/^/[preflight] /'

  fail=0
  for want in sock=ok docker=ok dataset=ok manifest=ok image_map=ok runner=ok \
              closure_helper=ok closure_gate_py=ok api_key=present; do
    echo "$PRE" | grep -qx "$want" || { echo "blocked: preflight expected '$want'" >&2; fail=1; }
  done
  echo "$PRE" | grep -q "^subset_manifest=ok images=3" || { echo "blocked: subset manifest not built with exactly 3 images" >&2; fail=1; }
  relay_code=$(echo "$PRE" | sed -n 's/^relay_http=//p')
  case "$relay_code" in 200|401) ;; *) echo "blocked: relay returned '$relay_code'" >&2; fail=1 ;; esac
  [[ "$fail" == "0" ]] || { echo "[canary] preflight FAILED -- nothing launched" >&2; exit 24; }

  echo "[canary] preflight OK -- writing remote launch script"
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$POD_SSH" "cat > $LAUNCH_SH" <<LAUNCH
#!/usr/bin/env bash
set -uo pipefail
export NO_PROXY='*' no_proxy='*'
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
# API key: sourced here, never echoed. Do not add 'set -x' to this script.
set -a; source "$API_ENV" >/dev/null 2>&1 || true; set +a
if [[ -z "\${$API_KEY_VAR:-}" ]]; then echo "blocked: $API_KEY_VAR missing" >&2; exit 24; fi
ulimit -n 65535 2>/dev/null || true
echo "[canary] start \$(date -u +%FT%TZ) tag=$CANARY_TAG_LC ulimit_n=\$(ulimit -n)"
env $CANARY_ENV bash "$RUNNER"
rc=\$?
echo "[canary] runner_rc=\$rc end \$(date -u +%FT%TZ)"
echo "\$rc" > "$STAGE_DIR/runner.rc"
exit \$rc
LAUNCH

  # setsid + nohup: survives SSH drops (a dropped ssh once killed a whole pilot run).
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$POD_SSH" \
    "chmod +x $LAUNCH_SH && cd $STAGE_DIR && setsid nohup bash $LAUNCH_SH > $CANARY_LOG 2>&1 < /dev/null & echo started_pid=\$!"

  echo "[canary] launched tag=$CANARY_TAG_LC"
  echo "[canary] log:      $CANARY_LOG"
  echo "[canary] rc file:  $STAGE_DIR/runner.rc"
  echo "[canary] tail with: ssh $POD_SSH tail -f $CANARY_LOG"
  exit 0
fi

# ================================ FULL 89 =====================================
read -r -d '' REMOTE_ENV <<EOF || true
TB21_PRIVILEGED_RUNNER=$RUNNER
TB21_FULL89_IMAGE_MANIFEST=$IMAGE_MANIFEST
TB21_FULL89_IMAGE_MAP=$IMAGE_MAP
TB21_FULL89_DATASET=$DATASET
TB21_ENABLE_KVM_DEVICE=$KVM_DEVICE
TB21_STATIC_RUNTIME_CLOSURE_GATE=$STATIC_GATE
TB21_API_ENV=$API_ENV
EOF

LAUNCH_ARGS="--execute --mode $LAUNCH_MODE --attempts $ATTEMPTS_SPEC --concurrency $CONCURRENCY --model $MODEL --relay-url $RELAY_URL --run-id $RUN_ID"
REMOTE_CMD="cd $LAUNCHER_ROOT && env $(echo "$REMOTE_ENV" | tr '\n' ' ')bash $LAUNCHER_REL $LAUNCH_ARGS"
TMUX_SESSION="tb21_gpt55_repro_${LAUNCH_MODE}_c${CONCURRENCY}"

print_plan() {
  cat <<PLAN
[repro] config              = $CONFIG
[repro] canonical_run_id    = $CANONICAL_RUN_ID
[repro] expected_score      = ${EXPECTED_RESOLVED}/${EXPECTED_TOTAL} = ${EXPECTED_PCT} (corrected; raw 62/89 is do-not-quote)
[repro] new_run_id          = $RUN_ID
[repro] bench               = $BENCH
[repro] model / agent       = $MODEL / $AGENT
[repro] effort              = ${LAUNCH_MODE}/default (no reasoning_effort arg)
[repro] concurrency         = $CONCURRENCY
[repro] attempts            = $N_ATTEMPTS (spec=$ATTEMPTS_SPEC)
[repro] timeout             = multiplier $TIMEOUT_MULTIPLIER / ${TIMEOUT_SEC}s (agent+test)
[repro] dataset             = $DATASET
[repro] image_manifest      = $IMAGE_MANIFEST
[repro] image_map           = $IMAGE_MAP
[repro] runner              = $RUNNER
[repro] relay (canonical)   = $RELAY_CANONICAL
[repro] relay (this run)    = $RELAY_URL     <-- ONLY intended deviation
[repro] api_env             = $API_ENV  (key var $API_KEY_VAR; never read by this script)
[repro] execution_host      = $POD_SSH
[repro] kvm_device          = $KVM_DEVICE   <-- guard: runner default is 1; canonical was OFF
[repro] static_closure_gate = $STATIC_GATE  <-- canonical value

[repro] remote env:
$(echo "$REMOTE_ENV" | sed 's/^/[repro]   /')
[repro] remote command:
[repro]   $REMOTE_CMD

[repro] tmux session (execute mode):
[repro]   tmux new-session -d -s $TMUX_SESSION "ssh -CAXY $POD_SSH bash -lc '<remote command>'"
PLAN
}

if [[ "$MODE_ACTION" == "dry-run" ]]; then
  print_plan
  echo "[repro] dry_run=1 nothing launched"
  exit 0
fi

print_plan
echo "[repro] --- preflight on $POD_SSH ---"

PREFLIGHT=$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$POD_SSH" bash -s <<PF
set -uo pipefail
export NO_PROXY='*' no_proxy='*'
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
set -o noglob

[[ -S /var/run/docker.sock ]] && echo "sock=ok" || echo "sock=missing"
docker info >/dev/null 2>&1 && echo "docker=ok" || echo "docker=fail"
[[ -e /dev/kvm ]] && echo "kvm_node=present" || echo "kvm_node=absent"
[[ -d "$DATASET" ]] && echo "dataset=ok" || echo "dataset=missing"
[[ -f "$IMAGE_MANIFEST" ]] && echo "manifest=ok" || echo "manifest=missing"
[[ -f "$IMAGE_MAP" ]] && echo "image_map=ok" || echo "image_map=missing"
[[ -x "$RUNNER" ]] && echo "runner=ok" || echo "runner=missing_or_not_executable"

RUNNER_ROOT="\$(cd "\$(dirname "$RUNNER")/.." && pwd -P)"
[[ -f "\$RUNNER_ROOT/scripts/build_tb21_full89_closure_matrix.py" ]] \
  && echo "closure_helper=ok" || echo "closure_helper=missing"

set -a; source "$API_ENV" >/dev/null 2>&1 || true; set +a
[[ -n "\${$API_KEY_VAR:-}" ]] && echo "api_key=present" || echo "api_key=missing"

code=\$(curl -sS --noproxy '*' -m 12 -o /dev/null -w '%{http_code}' "${RELAY_URL%/v1}/v1/models" 2>/dev/null || echo 000)
echo "relay_http=\$code"
PF
) || { echo "blocked: preflight ssh failed" >&2; exit 24; }

echo "$PREFLIGHT" | sed 's/^/[preflight] /'

fail=0
check() { echo "$PREFLIGHT" | grep -qx "$1" || { echo "blocked: preflight expected '$1'" >&2; fail=1; }; }
check "sock=ok"; check "docker=ok"; check "dataset=ok"; check "manifest=ok"
check "image_map=ok"; check "runner=ok"; check "api_key=present"

relay_code=$(echo "$PREFLIGHT" | sed -n 's/^relay_http=//p')
case "$relay_code" in
  200|401) ;;
  *) echo "blocked: relay $RELAY_URL returned '$relay_code' (want 200 or 401; 000 = down/unreachable)" >&2; fail=1 ;;
esac

if [[ "$STATIC_GATE" == "1" ]] && echo "$PREFLIGHT" | grep -qx "closure_helper=missing"; then
  cat >&2 <<'BLOCK'
blocked: TB21_STATIC_RUNTIME_CLOSURE_GATE=1 (the canonical value) but
         scripts/build_tb21_full89_closure_matrix.py is missing from the runner's
         REPO_ROOT. Resolve explicitly (config.yaml ->
         conflicts.static_closure_gate_helper_missing) -- never downgrade to 0.
BLOCK
  fail=1
fi

[[ "$fail" == "0" ]] || { echo "[repro] preflight FAILED -- nothing launched" >&2; exit 24; }

if [[ "$MODE_ACTION" == "preflight" ]]; then
  echo "[repro] preflight OK -- preflight_only=1 nothing launched"
  exit 0
fi

echo "[repro] preflight OK -- launching in local tmux session $TMUX_SESSION"
tmux new-session -d -s "$TMUX_SESSION" \
  "ssh -CAXY $POD_SSH bash -lc $(printf '%q' "$REMOTE_CMD")"
echo "[repro] launched run_id=$RUN_ID session=$TMUX_SESSION"
echo "[repro] attach with: tmux attach -t $TMUX_SESSION"
