#!/usr/bin/env bash
# Network-isolation gate for the TB2.1 x terminus-2 clean rerun.
#
# WHY: the 2026-07-10 "external_network_marker" was NOT contamination. All 89 r7
# task composes already pin `network_mode: none` on the single `client` service,
# and the terminus-2 agent runs on the HOST (reaching serving from the host and
# injecting commands via docker exec) -- so the task container needs, and has,
# no network at all. The markers (github.com / /simple/ / "Could not resolve host")
# are the model's FAILED offline attempts, counted by a substring scan in
# tb21_strict_batch_summary.py:network_markers(). This gate proves isolation two ways.
#
# MODES:
#   static  <dataset_dir>
#       Fail-closed preflight: every task compose must be single-service `client`
#       with `network_mode: none`, and must NOT declare a top-level `networks:` block.
#   runtime <docker_host> <out_jsonl> [duration_sec] [interval_sec]
#       Positive runtime proof: while the run is live, for every LIVE tb2-offline/*
#       task container assert HostConfig.NetworkMode==none AND NetworkSettings.Networks=={}.
#       Read-only (docker inspect); never touches/stops a container; filters to
#       tb2-offline/* images so it can NEVER observe or disturb the SWE-V batch-1
#       containers (different images) that may share the pod.
set -uo pipefail

mode="${1:-}"; shift || true

fail=0

if [[ "$mode" == "static" ]]; then
  DS="${1:?usage: assert_net_isolation.sh static <dataset_dir>}"
  n_ok=0; n_task=0
  for f in "$DS"/*/docker-compose.yaml; do
    [[ -e "$f" ]] || continue
    n_task=$((n_task+1))
    t="$(basename "$(dirname "$f")")"
    out="$(python3 - "$f" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
svcs = d.get("services") or {}
errs = []
if "networks" in d:
    errs.append("has_top_level_networks")
for name, s in svcs.items():
    s = s or {}
    nm = s.get("network_mode")
    if nm != "none":
        errs.append(f"service[{name}].network_mode={nm!r}!=none")
print("OK" if not errs else "BAD:" + ";".join(errs))
PY
)"
    if [[ "$out" == OK ]]; then n_ok=$((n_ok+1)); else echo "STATIC_FAIL task=$t $out"; fail=1; fi
  done
  echo "static_net_gate tasks=$n_task network_mode_none_ok=$n_ok"
  if [[ "$n_task" -ne 89 ]]; then echo "STATIC_FAIL dataset task count=$n_task expected=89"; fail=1; fi
  [[ "$fail" == 0 ]] && echo "STATIC_NET_ISOLATION_OK" || echo "STATIC_NET_ISOLATION_FAIL"
  exit "$fail"
fi

if [[ "$mode" == "runtime" ]]; then
  DH="${1:?usage: assert_net_isolation.sh runtime <docker_host> <out_jsonl> [dur] [interval]}"
  OUT="${2:?out_jsonl required}"; DUR="${3:-0}"; INT="${4:-30}"
  export DOCKER_HOST="$DH"
  : > "$OUT"
  start=$(date +%s)
  echo "runtime_net_gate docker_host=$DH out=$OUT dur=$DUR interval=$INT (READ-ONLY, tb2-offline/* only)"
  while :; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    # only TB task containers (image tb2-offline/*); NEVER matches SWE-V batch-1 images
    ids=$(docker ps --filter "ancestor=" --format '{{.ID}} {{.Image}}' 2>/dev/null | awk '$2 ~ /^tb2-offline\// {print $1}')
    for id in $ids; do
      row=$(docker inspect --format '{"cid":"{{.Id}}","name":"{{.Name}}","image":"{{.Config.Image}}","network_mode":"{{.HostConfig.NetworkMode}}","networks":"{{json .NetworkSettings.Networks}}"}' "$id" 2>/dev/null)
      [[ -z "$row" ]] && continue
      nm=$(printf '%s' "$row" | python3 -c 'import json,sys;print(json.load(sys.stdin)["network_mode"])' 2>/dev/null)
      nets=$(printf '%s' "$row" | python3 -c 'import json,sys;d=json.load(sys.stdin);n=json.loads(d["networks"]) if d["networks"] not in (None,"null") else {};print(len(n or {}))' 2>/dev/null)
      verdict="ISOLATED"; { [[ "$nm" != "none" ]] || [[ "$nets" != "0" ]]; } && { verdict="LEAK"; fail=1; }
      printf '{"ts":"%s","verdict":"%s","network_mode":"%s","attached_networks":%s,"detail":%s}\n' \
        "$ts" "$verdict" "$nm" "${nets:-null}" "$row" >> "$OUT"
      [[ "$verdict" == LEAK ]] && echo "RUNTIME_LEAK ts=$ts nm=$nm nets=$nets id=$id"
    done
    [[ "$DUR" != 0 && $(( $(date +%s) - start )) -ge "$DUR" ]] && break
    [[ "$DUR" == 0 ]] && break   # single-shot when no duration given
    sleep "$INT"
  done
  observed=$(wc -l < "$OUT" 2>/dev/null || echo 0)
  echo "runtime_net_gate observations=$observed leaks=$([[ $fail == 0 ]] && echo 0 || echo '>0')"
  [[ "$fail" == 0 ]] && echo "RUNTIME_NET_ISOLATION_OK" || echo "RUNTIME_NET_ISOLATION_FAIL"
  exit "$fail"
fi

echo "usage: $0 static <dataset_dir> | runtime <docker_host> <out_jsonl> [dur] [interval]" >&2
exit 2
