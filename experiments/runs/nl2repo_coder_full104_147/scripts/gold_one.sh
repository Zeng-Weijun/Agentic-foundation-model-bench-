#!/bin/bash
# One gold task, --mode gold (no serving). Called by gold_selfcheck.sh via xargs.
set -u
task="$1"; RR="$2"; DRV="$3"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
python3 "$DRV" --task "$task" --mode gold --run-root "$RR" --cmd-timeout 900 \
  > "$RR/logs/${task}.log" 2>&1
echo "gold-done ${task} rc=$?"
