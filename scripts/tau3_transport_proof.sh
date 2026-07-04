#!/bin/bash
set -o pipefail
D=docker
MAIN="100.97.118.137:8555/swe-data-harness/tau3-full-main@sha256:3591be51f3901080271eb4a9c1bd9c680fc999ced3c44fc42ccec7d788e81645"
RT="100.97.118.137:8555/swe-data-harness/tau3-full-runtime@sha256:bf0f3ab41886d31db8f7c93f874d63420c1679733dcce1e4c0663c1c11117fa8"
DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench
OUT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/tau3/transport_proof
mkdir -p "$OUT"; LOG="$OUT/proof.log"
# 1 real task per domain (the quarantined -0 dirs are excluded)
TASKS="tau3-airline-0 tau3-retail-0 tau3-telecom-mms-issue-airplane-mode-on-bad-network-preference-bad-wifi-calling-break-apn-mms-setting-break-app-both-permissions-data-mode-off-data-usage-exceeded-unseat-sim-card-user-abroad-roaming-disabled-off-persona-hard tau3-banking_knowledge-task-001"
{
echo "### tau3 DoD-3 transport-proof (re-proof, fixed images) host=$(hostname) $(date -u +%FT%TZ)"
echo "== STEP1: P0 by-digest pull =="
$D pull "$MAIN" 2>&1 | tail -1
$D pull "$RT"   2>&1 | tail -1
echo "== STEP2: internal network (no external egress) =="
$D network rm tau3net >/dev/null 2>&1; $D network create --internal tau3net >/dev/null && echo "net=tau3net(--internal)"
PASS=0; FAIL=0; i=0
for TASK in $TASKS; do
  i=$((i+1)); NAME="rt$i"
  CFG="$DS/$TASK/environment/runtime-server/task_config.json"
  SRC_SHA=$(sha256sum "$CFG" 2>/dev/null | cut -d" " -f1)
  echo "== TASK[$i] ${TASK:0:40}...  (src task_config bytes=$(wc -c < "$CFG" 2>/dev/null) sha=${SRC_SHA:0:12}) =="
  $D rm -f $NAME >/dev/null 2>&1
  $D run -d --name $NAME --network tau3net --network-alias tau3-runtime \
    -e OPENAI_API_KEY=dummy -e OPENAI_BASE_URL=http://127.0.0.1:1 -e TAU2_USER_MODEL=gpt-5.4-mini -e TAU2_USER_REASONING_EFFORT=low \
    -v "$CFG":/app/task_config.json:ro "$RT" >/dev/null 2>&1
  sleep 12
  R="running=$($D inspect --format '{{.State.Running}}' $NAME 2>/dev/null)"
  # 55#2: task_config exists+non-empty AND mounted sha256 == source sha256 (mount-integrity)
  MNT_SHA=$($D exec $NAME sha256sum /app/task_config.json 2>/dev/null | cut -d" " -f1)
  if [ -n "$MNT_SHA" ] && [ "$MNT_SHA" = "$SRC_SHA" ]; then P1="TASKCFG_SHA_MATCH(${MNT_SHA:0:12})"; else P1="TASKCFG_SHA_MISMATCH(mnt=${MNT_SHA:0:12} src=${SRC_SHA:0:12})"; fi
  # sidecar :8000 up (MCP server listening)
  P1b=$($D exec $NAME python3 -c "import socket; socket.create_connection(('localhost',8000),timeout=6); print('SIDECAR_8000_UP')" 2>&1 | tail -1)
  # 55#1: import probe covers the crashed path (tau2->voice->scipy/pyaudio) + fastmcp + domains
  P1c=$($D exec $NAME python3 -c "import tau2, fastmcp, importlib; [importlib.import_module(m) for m in ['tau2.domains.airline','tau2.domains.retail','tau2.domains.telecom']]; print('IMPORT_TAU2_FASTMCP_DOMAINS_OK')" 2>&1 | tail -1)
  # main <-> MCP-sidecar link
  P2=$($D run --rm --network tau3net "$MAIN" python3 -c "import socket; socket.create_connection(('tau3-runtime',8000),timeout=10); print('MAIN_TO_SIDECAR_LINK_OK')" 2>&1 | tail -1)
  # no public net (must fail)
  P3=$($D exec $NAME sh -c "timeout 6 python3 -c \"import urllib.request; urllib.request.urlopen('http://example.com',timeout=5); print('PUBLIC_REACHED_BAD')\" 2>&1 | tail -1 || true")
  [ -z "$(echo "$P3" | grep -i reached)" ] && P3="NO_PUBLIC_NET_CONFIRMED"
  echo "   $R | cfg)$P1 | sidecar)$P1b | import)$P1c | link)$P2 | net)$P3"
  if echo "$P1"|grep -q SHA_MATCH && echo "$P1b"|grep -q SIDECAR_8000_UP && echo "$P1c"|grep -q IMPORT_TAU2_FASTMCP_DOMAINS_OK && echo "$P2"|grep -q LINK_OK && echo "$P3"|grep -q NO_PUBLIC; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "   TASK_FAIL logs: $($D logs $NAME 2>&1 | tail -3 | tr '\n' '|')"; fi
  $D rm -f $NAME >/dev/null 2>&1
done
$D network rm tau3net >/dev/null 2>&1
echo "### TRANSPORT-PROOF RESULT: PASS=$PASS/4 FAIL=$FAIL"
[ "$PASS" = "4" ] && echo "### DoD-3 TRANSPORT-PROOF: PASS (4/4 domains, 55 3-hardening: sha-mount-match + import-probe + no-public-net)" || echo "### DoD-3 TRANSPORT-PROOF: NOT PASS"
} 2>&1 | tee "$LOG"
echo "EVIDENCE=$LOG"
