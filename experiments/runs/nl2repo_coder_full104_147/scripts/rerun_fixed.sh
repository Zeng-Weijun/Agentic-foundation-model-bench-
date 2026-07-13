#!/bin/bash
# Rerun the contaminated tasks (argv-overflow + judging-hang) with the STDIN-FIXED driver.
# Detached (setsid) + hang-watchdog. Each task self-cleans its image (rmi). Writes a fresh
# run dir; merge_aggregate.py combines this (per-task override) with the original full104 run.
set -u
PA=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA
TASKS_FILE="${TASKS_FILE:?set TASKS_FILE}"
TS=$(date -u +%Y%m%dT%H%M%SZ)
RR=$PA/runs/rerun_fixed_$TS
mkdir -p "$RR/logs"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export OPENAI_API_KEY=EMPTY
CONC=${CONC:-6}; TURNS=${TURNS:-40}; ROLLOUT=${ROLLOUT:-1800}; CMDTO=${CMDTO:-1500}
cp "$TASKS_FILE" "$RR/tasks.txt"
N=$(wc -l < "$RR/tasks.txt")
echo "RERUN_FIXED RR=$RR tasks=$N conc=$CONC turns=$TURNS rollout=$ROLLOUT cmdto=$CMDTO"
# hang-watchdog
setsid bash "$PA/rerun_watchdog.sh" "$RR" </dev/null >/dev/null 2>&1 &
WPID=$!
# main rerun
setsid bash -c "
  xargs -a '$RR/tasks.txt' -P $CONC -I {} bash '$PA/run_one.sh' {} '$RR' $TURNS $ROLLOUT $CMDTO
  python3 '$PA/aggregate.py' --run-root '$RR' > '$RR/AGGREGATE.txt' 2>&1
  touch '$RR/DONE'
" </dev/null >"$RR/launch.log" 2>&1 &
echo "LAUNCHED rerun pid=$! watchdog=$WPID RR=$RR"
echo "$RR" > "$PA/runs/LATEST_RERUN_FIXED.txt"
echo "monitor: ls $RR/*/summary.json | wc -l (target $N); tail $RR/watchdog.log"
