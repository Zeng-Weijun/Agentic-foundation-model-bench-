#!/bin/bash
# Hang-watchdog for the fixed rerun: force-remove nl2repo-pathA score/agent containers
# that exceed a hard age, so a judging hang (e.g. tqdm pytest deadlock) cannot stall the
# batch or the driver. Exits when RR/DONE appears. Logs each kill.
set -u
RR="$1"
SCORE_MAX=${SCORE_MAX:-1800}   # 30 min hard cap on a scoring container
AGENT_MAX=${AGENT_MAX:-2000}   # ~33 min hard cap on an agent container
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
while [ ! -f "$RR/DONE" ]; do
  now=$(date +%s)
  for c in $(docker ps --format '{{.Names}}' 2>/dev/null | grep '^nl2repo-pathA-'); do
    started=$(docker inspect -f '{{.State.StartedAt}}' "$c" 2>/dev/null) || continue
    st=$(date -d "$started" +%s 2>/dev/null) || continue
    age=$(( now - st ))
    lim=$AGENT_MAX; case "$c" in *score*) lim=$SCORE_MAX;; esac
    if [ "$age" -gt "$lim" ]; then
      docker rm -f "$c" >/dev/null 2>&1 && echo "$(date -u +%H:%M:%SZ) WATCHDOG killed $c age=${age}s lim=${lim}s" >> "$RR/watchdog.log"
    fi
  done
  sleep 45
done
echo "$(date -u +%H:%M:%SZ) watchdog exit (DONE seen)" >> "$RR/watchdog.log"
