#!/usr/bin/env bash
# TB2.1 x Qwen3-Coder-30B-A3B-Instruct x terminus-2 (OFFICIAL harness), full 89, c=32, attempts=1.
# Pod A only. Direct sglang :30001 (no relay). Read-only wrt Pod B and wrt PIDs 607975/607977.
set -euo pipefail

REPO=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-gpt55-launcher-s55
MYWORK=$REPO/_coordination/20260625_harbor_bench/logs/tb21_coder_terminus2_20260710
BASE_URL=http://100.100.104.140:30001/v1
OUT_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda

# ---- run_id: lowercase assertion + negative test (pit #3: uppercase Z forks run_root vs attempt.done) ----
RUN_ID="tb21_coder_t2_c32_$(date -u +%m%d%H%M%S)"
if ! printf '%s' "$RUN_ID" | grep -Eq '^[a-z0-9_-]+$'; then
  echo "bad run_id (must be ^[a-z0-9_-]+$): $RUN_ID" >&2; exit 2
fi
# negative test: the exact assertion MUST reject an uppercase / trailing-Z tag
if printf '%s' "TB21_20260710T00Z" | grep -Eq '^[a-z0-9_-]+$'; then
  echo "ASSERTION_BROKEN: uppercase tag accepted" >&2; exit 2
fi
# and the derived tb tag (what the stage launcher builds) must also be lowercase
DERIVED_TAG="${RUN_ID}_attempt1_medium_c32"
if ! printf '%s' "$DERIVED_TAG" | grep -Eq '^[a-z0-9_-]+$'; then
  echo "bad derived tag: $DERIVED_TAG" >&2; exit 2
fi
echo "NEG_TEST_OK assertion rejects uppercase/Z tags; run_id=$RUN_ID derived_tag=$DERIVED_TAG"

cd "$REPO"

# ---- env: no proxy to the serving host; placeholder key (server reports api_key=null -> no auth enforced) ----
export OPENAI_API_KEY=tb-terminus2-placeholder
export API_KEY=tb-terminus2-placeholder
export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
export NO_PROXY=100.100.104.140,127.0.0.1,localhost,::1,10.0.0.0/8,100.96.0.0/12,100.103.0.0/16,.pjlab.org.cn
export no_proxy="$NO_PROXY"
export DOCKER_HOST=unix:///var/run/docker.sock
export TB21_ALLOW_PRIVILEGED_DOCKER=1

# ---- FIX 1: match canonical's dataset. The r3 runner (untracked, mtime Jul 7 > canonical Jul 5)
# now defaults TB21_ENABLE_KVM_DEVICE=1, which derives a /dev/kvm-injected dataset copy.
# Canonical's run.env.summary shows tb_dataset_path = the plain r7 dataset, and 85's canary
# gate #7 asserted kvm_device=disabled. Restore that.
export TB21_ENABLE_KVM_DEVICE=0

# ---- FIX 2: the runner sets TB2_RUNTIME_CLOSURE_REPAIR=$REPO_ROOT/scripts/repair_tb21_full89_runtime_closure.py
# only when the var is UNSET ([[ -z ${VAR+x} ]]). Its REPO_ROOT is the r3 worktree, where that
# script does not exist (it is an untracked file living only in the main worktree). The shared
# runner then does `python3 "$TB2_RUNTIME_CLOSURE_REPAIR"` -> exit 2 -> set -e -> whole run dies
# before `tb` is ever invoked. Exporting it as an EMPTY-but-SET string takes the runner's seam
# and makes the shared runner skip the step.
# Skipping is correct, not a downgrade: the static closure gate independently proves
# closed=89 / open=0 on this exact dataset, so the repair is a no-op by construction; and
# `repair --execute` MUTATES the frozen shared r7 dataset (run-tests.sh / docker-compose.yaml /
# bn-fit-modify/solution.sh), which other lanes also consume. TB21_STATIC_RUNTIME_CLOSURE_GATE
# and TB21_STRICT_CLOSURE_GATE both stay 1.
export TB2_RUNTIME_CLOSURE_REPAIR=""

printf '[full] start run_id=%s base=%s concurrency=32 attempts=1 mode=medium\n' "$RUN_ID" "$BASE_URL"
python3 "$MYWORK/identity_capture.py" before "$MYWORK/serving_run"

# ---- disk watch: df -h / and df -ih / every 10 min; stop if either FREE% < 10 ----
(
  while true; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    df -h  / | awk -v ts="$ts" 'NR==2{print ts,"df_h",$0}'
    df -ih / | awk -v ts="$ts" 'NR==2{print ts,"df_ih",$0}'
    python3 - <<'PYSTOP'
import shutil, os
s = shutil.disk_usage('/')
bytes_free_pct = s.free / s.total * 100
st = os.statvfs('/')
inode_free_pct = (st.f_ffree / st.f_files * 100) if st.f_files else 100
if bytes_free_pct < 10 or inode_free_pct < 10:
    print("STOP_LOW_SPACE bytes_free_pct=%.3f inode_free_pct=%.3f" % (bytes_free_pct, inode_free_pct))
    raise SystemExit(24)
PYSTOP
    sleep 600
  done
) > "$MYWORK/disk_watch.log" 2>&1 &
watch_pid=$!

# ---- post-start assertion: the run.env.summary must show the r7 dataset, not a kvm-derived copy
EXPECT_DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703
(
  RD="$OUT_ROOT/$RUN_ID/medium_c32/attempt_1/tb21_batched_terminus-2_${DERIVED_TAG}/batch_01_of_01/run.env.summary"
  for _ in $(seq 1 60); do
    if [[ -f "$RD" ]]; then
      got=$(grep -m1 '^tb_dataset_path=' "$RD" | cut -d= -f2-)
      ntasks=$(grep -m1 '^tb_task_ids=' "$RD" | tr ' ' '\n' | grep -c .)
      printf '[assert] tb_dataset_path=%s\n[assert] tb_task_ids_count=%s\n' "$got" "$ntasks"
      if [[ "$got" != "$EXPECT_DS" ]]; then printf '[assert] DATASET_MISMATCH expected=%s\n' "$EXPECT_DS"; fi
      break
    fi
    sleep 10
  done
) > "$MYWORK/dataset_assert.log" 2>&1 &

set +e
bash scripts/stage_tb21_official_qwen_launcher.sh \
  --execute \
  --mode medium \
  --attempts all \
  --concurrency 32 \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --relay-url "$BASE_URL" \
  --timeout-sec 7200 \
  --timeout-multiplier 1.0 \
  --run-id "$RUN_ID"
runner_rc=$?
set -e

kill "$watch_pid" 2>/dev/null || true
wait "$watch_pid" 2>/dev/null || true

python3 "$MYWORK/identity_capture.py" after "$MYWORK/serving_run" || echo "[identity_after] capture_rc=$?"
echo "$runner_rc" > "$MYWORK/full.rc"
echo "$RUN_ID"   > "$MYWORK/full.run_id"
echo done        > "$MYWORK/full.done"
printf '[full] end run_id=%s rc=%s\n' "$RUN_ID" "$runner_rc"
exit "$runner_rc"
