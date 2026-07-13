#!/bin/bash
# Launch the NL2Repo Path A full-104 native qwen-code evaluation, DETACHED (setsid
# so an SSH drop cannot kill it). RUN THIS ON THE KVM POD (docker + serving reach).
#
# Each task (via nl2repo_qwencode_driver.py --mode agent):
#   docker load (sha256-verified tar) -> native qwen-code in a clean /workspace
#   (base image with /workspace wiped + start.md only) talking DIRECT to the
#   serving -> official post_processor scoring (strip pkg/test files, overlay the
#   model source onto a FRESH base image /workspace, `pip install -e .` + pytest
#   --network none with the offline wheelhouse) -> docker rmi (bounds disk).
#
# Only ever manages its OWN nl2repo-pathA-* containers/images. Concurrency N =>
# at most ~N task images resident at once (each task rmi's itself).
#
# Tunables (env): CONC (parallel tasks, default 8), TURNS (40), ROLLOUT (2400s),
#   CMDTO (per test-command timeout, 1800s), TASKS_FILE (override task list).
set -u
PA=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA
MAN=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/nl2repo/nl2repo_transport_manifest.jsonl
TS=$(date -u +%Y%m%dT%H%M%SZ)
RR=$PA/runs/full104_$TS
mkdir -p "$RR/logs"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export OPENAI_API_KEY=EMPTY

CONC=${CONC:-8}; TURNS=${TURNS:-40}; ROLLOUT=${ROLLOUT:-2400}; CMDTO=${CMDTO:-1800}

# 104 task names from the transport manifest (or a caller-supplied subset)
if [ -n "${TASKS_FILE:-}" ] && [ -f "${TASKS_FILE}" ]; then
  cp "$TASKS_FILE" "$RR/tasks.txt"
else
  python3 -c "import json;[print(json.loads(l)['task']) for l in open('$MAN') if l.strip()]" > "$RR/tasks.txt"
fi
N=$(wc -l < "$RR/tasks.txt")
echo "NL2REPO_FULL104 RR=$RR tasks=$N conc=$CONC turns=$TURNS rollout=$ROLLOUT cmdto=$CMDTO"

setsid bash -c "
  xargs -a '$RR/tasks.txt' -P $CONC -I {} bash '$PA/run_one.sh' {} '$RR' $TURNS $ROLLOUT $CMDTO
  python3 '$PA/aggregate.py' --run-root '$RR' > '$RR/AGGREGATE.txt' 2>&1
" </dev/null >"$RR/launch.log" 2>&1 &
echo "LAUNCHED pid=$! RR=$RR"
echo "$RR" > "$PA/runs/LATEST_FULL104_RUN_ROOT.txt"
echo "monitor : tail -f $RR/launch.log   (per-task: ls $RR/logs)"
echo "progress: ls $RR/*/summary.json | wc -l   (target $N)"
echo "result  : cat $RR/AGGREGATE.txt   (written when all tasks finish)"
