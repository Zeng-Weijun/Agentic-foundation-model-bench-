#!/bin/bash
# One NL2Repo task, native qwen-code Path A: load -> agent -> score -> rmi.
# Called by full104_launch.sh via xargs. Never touches non-nl2repo containers.
set -u
PA=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA
DRV=$PA/nl2repo_qwencode_driver.py
task="$1"; RR="$2"; TURNS="${3:-40}"; ROLLOUT="${4:-2400}"; CMDTO="${5:-1800}"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
python3 "$DRV" --task "$task" --mode agent --run-root "$RR" \
  --max-session-turns "$TURNS" --rollout-timeout "$ROLLOUT" --cmd-timeout "$CMDTO" \
  > "$RR/logs/${task}.log" 2>&1
echo "done ${task} rc=$?"
