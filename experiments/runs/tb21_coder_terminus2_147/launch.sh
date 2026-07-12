#!/usr/bin/env bash
# TB2.1 x {Qwen3-Coder-30B-A3B-Instruct | Qwen3-30B-A3B-Instruct-2507} x terminus-2
# (OFFICIAL harness), full 89, c=32, attempts=1, single pass@1. Serving = .147.
#
# Clean rerun of the 2026-07-10 line, retargeted from the dead .140 to live .147,
# with the three "false-blocked" defects addressed (see NOTES at bottom).
# Run this ON the KVM pod (Pod B env-kvm-57740737-bzw56) from a LOCAL tmux + ssh.
#
# Usage:  full_run_147.sh <coder|instruct>
#
# It is read-only wrt the SWE-V batch-1 containers (different images) and never
# starts/stops them; the runtime net gate filters to tb2-offline/* only.
set -euo pipefail

PROFILE="${1:?usage: full_run_147.sh <coder|instruct>}"

# ---- profile -> serving endpoint + model + identity suffix + launcher ----
WT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees
REPO="${TB21_REPO:-$WT/tb21-gpt55-launcher-s55}"          # has launcher + ledger; siblings resolve here
MYWORK="${TB21_MYWORK:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SERVING_HOST=100.100.104.147
case "$PROFILE" in
  coder)
    PORT=30001
    MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
    EXPECT_SUFFIX="Qwen3-Coder-30B-A3B-Instruct"
    LAUNCHER="$REPO/scripts/stage_tb21_official_qwen_launcher.sh"   # original accepts Coder
    RID_TAG="coder"
    ;;
  instruct)
    PORT=30000
    MODEL="Qwen/Qwen3-30B-A3B-Instruct-2507"
    EXPECT_SUFFIX="Qwen3-30B-A3B-Instruct-2507"
    # PATCHED launcher copy (accepts Instruct-2507). Create it first, see NOTES / the .patch.
    LAUNCHER="$REPO/scripts/stage_tb21_official_qwen_launcher_terminus2.sh"
    RID_TAG="inst2507"
    ;;
  *) echo "profile must be coder|instruct: $PROFILE" >&2; exit 2 ;;
esac
BASE_URL="http://$SERVING_HOST:$PORT/v1"

[[ -x "$LAUNCHER" ]] || { echo "blocked: launcher missing/not-exec: $LAUNCHER" >&2
  [[ "$PROFILE" == instruct ]] && echo "  create it: cp \"$REPO/scripts/stage_tb21_official_qwen_launcher.sh\" \"$LAUNCHER\" && patch \"$LAUNCHER\" < \"$MYWORK/stage_launcher_accept_instruct.patch\"" >&2
  exit 24; }

# ---- run_id: lowercase assertion + negative test (pit #3: uppercase Z forks run_root) ----
RUN_ID="tb21_${RID_TAG}_t2_c32_$(date -u +%m%d%H%M%S)"
printf '%s' "$RUN_ID" | grep -Eq '^[a-z0-9_-]+$' || { echo "bad run_id: $RUN_ID" >&2; exit 2; }
printf '%s' "TB21_20260712T00Z" | grep -Eq '^[a-z0-9_-]+$' && { echo "ASSERTION_BROKEN: uppercase accepted" >&2; exit 2; }
DERIVED_TAG="${RUN_ID}_attempt1_medium_c32"
printf '%s' "$DERIVED_TAG" | grep -Eq '^[a-z0-9_-]+$' || { echo "bad derived tag: $DERIVED_TAG" >&2; exit 2; }
echo "NEG_TEST_OK run_id=$RUN_ID derived_tag=$DERIVED_TAG profile=$PROFILE base=$BASE_URL model=$MODEL"

cd "$REPO"

# ---- env: no proxy to serving; placeholder key (server reports api_key=null -> no auth) ----
export OPENAI_API_KEY="${OPENAI_API_KEY:-tb-terminus2-placeholder}"
export API_KEY="${API_KEY:-tb-terminus2-placeholder}"
export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
export NO_PROXY="$SERVING_HOST,127.0.0.1,localhost,::1,10.0.0.0/8,100.96.0.0/12,100.100.0.0/16,.pjlab.org.cn"
export no_proxy="$NO_PROXY"
export DOCKER_HOST=unix:///var/run/docker.sock
export TB21_ALLOW_PRIVILEGED_DOCKER=1

# ---- FIX 1: canonical used the plain r7 dataset (no /dev/kvm injection). The r3 runner defaults
#            TB21_ENABLE_KVM_DEVICE=1 (derives a kvm dataset copy); restore canonical = 0.
export TB21_ENABLE_KVM_DEVICE=0
# ---- FIX 2: skip the runtime-closure repair (empty-but-SET). Static closure gate already proves
#            closed=89/open=0 on r7, and `repair --execute` MUTATES the frozen shared dataset.
export TB2_RUNTIME_CLOSURE_REPAIR=""

# ---- serving identity BEFORE (read-only /get_model_info + /get_server_info; NOT inference) ----
python3 "$MYWORK/identity_capture_147.py" before "$MYWORK/serving_run_${RUN_ID}" "http://$SERVING_HOST:$PORT" "$EXPECT_SUFFIX"

# ---- disk watch: stop if / free% < 10 (bytes or inodes) ----
( while true; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    df -h  / | awk -v ts="$ts" 'NR==2{print ts,"df_h",$0}'
    df -ih / | awk -v ts="$ts" 'NR==2{print ts,"df_ih",$0}'
    python3 - <<'PYSTOP'
import shutil, os
s = shutil.disk_usage('/'); bfp = s.free/s.total*100
st = os.statvfs('/'); ifp = (st.f_ffree/st.f_files*100) if st.f_files else 100
if bfp < 10 or ifp < 10:
    print("STOP_LOW_SPACE bytes_free_pct=%.3f inode_free_pct=%.3f" % (bfp, ifp)); raise SystemExit(24)
PYSTOP
    sleep 600
  done ) > "$MYWORK/disk_watch_${RUN_ID}.log" 2>&1 &
watch_pid=$!

# ---- NEW: runtime network-isolation proof. Samples LIVE tb2-offline/* containers every 30s and
#            asserts NetworkMode==none + zero attached networks. Closes the 07-10 gap (its docker
#            state was captured post-teardown = 0 containers, so isolation was only proven statically).
( bash "$MYWORK/assert_net_isolation.sh" runtime "$DOCKER_HOST" "$MYWORK/net_isolation_runtime_${RUN_ID}.jsonl" 999999 30
) > "$MYWORK/net_isolation_watch_${RUN_ID}.log" 2>&1 &
net_pid=$!

# ---- post-start assertion: run.env.summary must show the r7 dataset (not a kvm-derived copy) + 89 ids
EXPECT_DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703
OUT_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda
( RD="$OUT_ROOT/$RUN_ID/medium_c32/attempt_1/tb21_batched_terminus-2_${DERIVED_TAG}/batch_01_of_01/run.env.summary"
  for _ in $(seq 1 90); do
    if [[ -f "$RD" ]]; then
      got=$(grep -m1 '^tb_dataset_path=' "$RD" | cut -d= -f2-)
      ntasks=$(grep -m1 '^tb_task_ids=' "$RD" | tr ' ' '\n' | grep -c .)
      printf '[assert] tb_dataset_path=%s\n[assert] tb_task_ids_count=%s\n' "$got" "$ntasks"
      [[ "$got" != "$EXPECT_DS" ]] && printf '[assert] DATASET_MISMATCH expected=%s\n' "$EXPECT_DS"
      [[ "$ntasks" != "89" ]] && printf '[assert] TASK_COUNT_MISMATCH expected=89 got=%s\n' "$ntasks"
      break
    fi
    sleep 10
  done ) > "$MYWORK/dataset_assert_${RUN_ID}.log" 2>&1 &

set +e
bash "$LAUNCHER" \
  --execute \
  --mode medium \
  --attempts all \
  --concurrency 32 \
  --model "$MODEL" \
  --relay-url "$BASE_URL" \
  --timeout-sec 7200 \
  --timeout-multiplier 1.0 \
  --run-id "$RUN_ID"
runner_rc=$?
set -e

kill "$watch_pid" "$net_pid" 2>/dev/null || true
wait "$watch_pid" 2>/dev/null || true
wait "$net_pid"   2>/dev/null || true

python3 "$MYWORK/identity_capture_147.py" after "$MYWORK/serving_run_${RUN_ID}" "http://$SERVING_HOST:$PORT" "$EXPECT_SUFFIX" || echo "[identity_after] capture_rc=$?"
echo "$runner_rc" > "$MYWORK/full_${RUN_ID}.rc"
echo "$RUN_ID"    > "$MYWORK/full_${RUN_ID}.run_id"
echo done         > "$MYWORK/full_${RUN_ID}.done"
printf '[full] end profile=%s run_id=%s rc=%s\n' "$PROFILE" "$RUN_ID" "$runner_rc"
exit "$runner_rc"

# ============================== NOTES: the three "blocked" defects ==============================
# The 07-10 Coder run FINALIZED with a valid 12/89 score but its strict gate self-reported
# status=blocked. That "blocked" was NOT contamination. Root causes, in priority order:
#
#  (1) infra_fail=89  <- FALSE. tb21_strict_batch_summary.py sets infra_fail when the BATCH-level
#      tb_rc != 0. The 07-10 process got SIGTERM (tb_rc=143) during docker cleanup AFTER results.json
#      was fully written, so all 89 rows inherited infra_fail. FIX: run to natural completion and
#      exit 0. Do not SIGTERM/^C the tb process during teardown. (If teardown legitimately hangs,
#      raise TB_DOCKER_COMPOSE_DOWN_TIMEOUT_SEC rather than killing.)
#
#  (2) external_network_marker (~10-12) <- EXPECTED, NOT contamination. All 89 r7 composes pin
#      network_mode: none on the single client service; terminus-2 runs on the HOST and reaches
#      serving from the host, so the container has no network. The markers are the model's FAILED
#      offline attempts (github.com / /simple/ / "Could not resolve host") counted by a substring
#      scan. gpt-5.5 canonical (the promoted 63/89) carries markers too. The runtime net gate above
#      turns this from "trust the compose" into a positive per-container proof.
#
#  (3) status=blocked itself <- INHERENT. `ready` requires clean_pass==total, i.e. an oracle 89/89.
#      EVERY real model run is "blocked" by this gate. Promotion applies the v4 rules (split infra_fail
#      into real-infra vs task-timeout; split LLM failures into infra-class 5xx/429 vs content-class
#      400), compared against the canonical baseline -- exactly how gpt-5.5 63/89 was promoted.
