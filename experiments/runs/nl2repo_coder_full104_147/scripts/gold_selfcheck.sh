#!/bin/bash
# Gold self-verification: run driver --mode gold on all tasks that have a gold wheel.
# Proves the offline scoring chain (docker overlay + pip install -e . + pytest with
# the offline wheelhouse) works and build backends resolve. Needs NO serving.
# Detached (setsid). Each gold task self-cleans its image (rmi).
set -u
PA=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA
GOLD=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/nl2repo/gold
DRV=$PA/nl2repo_qwencode_driver.py
TS=$(date -u +%Y%m%dT%H%M%SZ)
RR=$PA/runs/gold_selfcheck_$TS
mkdir -p "$RR/logs"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
CONC=${CONC:-4}
ls -d "$GOLD"/*/ | xargs -n1 basename > "$RR/gold_tasks.txt"
N=$(wc -l < "$RR/gold_tasks.txt")
echo "GOLD_SELFCHECK RR=$RR tasks=$N conc=$CONC"
setsid bash -c "
  xargs -a '$RR/gold_tasks.txt' -P $CONC -I {} bash '$PA/gold_one.sh' {} '$RR' '$DRV'
  echo ALL_GOLD_DONE
" </dev/null >>"$RR/progress.log" 2>&1 &
echo "LAUNCHED pid=$! RR=$RR"
echo "$RR" > "$PA/runs/LATEST_GOLD_SELFCHECK.txt"
echo "monitor: ls $RR/*/summary.json | wc -l (target $N); tail $RR/progress.log"
