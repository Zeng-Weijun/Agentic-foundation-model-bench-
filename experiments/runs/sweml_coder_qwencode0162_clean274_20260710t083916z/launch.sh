#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
WT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swemultilingual-v21-agent51"
RUNS_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs"
PY="/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python"
ADAPTER="$WT/scripts/full274_swemultilingual_qwencode_orchestrator_v21.py"
BASE_RUNNER="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51/scripts/full500_qwencode_orchestrator_v21.py"
DATASET_ROOT="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swebench-multilingual-2025-08-26"
CLEAN_IDS="$WT/manifests/candidates/swemultilingual_clean274_instance_ids_20260710.txt"
EXCLUDED_IDS="$WT/manifests/candidates/swemultilingual_gradle_excluded26_20260710.txt"
P0_MAP="/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swemultilingual_p0_stage_20260706/swemultilingual_p0_map.json"
QWEN_ROOT="${SWEML_QWEN_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/.npm-root-0.16.2}"
QWEN_CODE_VERSION="${SWEML_QWEN_CODE_VERSION:-0.16.2}"
QWEN_NODE_VERSION="${SWEML_QWEN_NODE_VERSION:-v20.20.2}"
QWEN_MOUNT="/opt/qwen-native/.npm-root"
CANARY_INSTANCE_ID="${SWEML_CANARY_INSTANCE_ID:-astral-sh__ruff-15309}"
SERVING_PROFILE="${SWEML_SERVING_PROFILE:-coder}"
case "$SERVING_PROFILE" in
  coder)
    PROFILE_BASE_URL="http://100.100.104.140:30001/v1"
    PROFILE_MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
    PROFILE_MODEL_PATH_SUFFIX="Qwen3-Coder-30B-A3B-Instruct"
    ;;
  instruct2507)
    PROFILE_BASE_URL="http://100.100.104.140:30000/v1"
    PROFILE_MODEL="Qwen/Qwen3-30B-A3B-Instruct-2507"
    PROFILE_MODEL_PATH_SUFFIX="Qwen3-30B-A3B-Instruct-2507"
    ;;
  *) echo "BLOCKED: unknown SWEML_SERVING_PROFILE=$SERVING_PROFILE" >&2; exit 2 ;;
esac
BASE_URL="${SWEML_BASE_URL:-$PROFILE_BASE_URL}"
MODEL="${SWEML_MODEL:-$PROFILE_MODEL}"
MODEL_PATH_SUFFIX="${SWEML_MODEL_PATH_SUFFIX:-$PROFILE_MODEL_PATH_SUFFIX}"
AGENT_DOCKER_NETWORK="${SWEML_AGENT_DOCKER_NETWORK:-bridge}"
CONCURRENCY="${SWEML_CONCURRENCY:-16}"
PREHEAT_CONCURRENCY="${SWEML_PREHEAT_CONCURRENCY:-4}"
DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"

MODE="validate"
RUN_ID="${SWEML_RUN_ID:-sweml_${SERVING_PROFILE}_qwencode_clean274_$(date -u +%Y%m%dt%H%M%Sz)}"
while (($#)); do
  case "$1" in
    --validate-only) MODE="validate"; shift ;;
    --canary-only) MODE="canary"; shift ;;
    --execute) MODE="full"; shift ;;
    --run-id)
      [[ $# -ge 2 ]] || { echo "BLOCKED: --run-id requires a value" >&2; exit 2; }
      RUN_ID="$2"; shift 2 ;;
    --help|-h)
      printf '%s\n' \
        "usage: $0 [--validate-only] [--canary-only|--execute] [--run-id <lowercase-id>]" \
        "default is validation only; canary requires SWEML_ALLOW_CANARY=YES" \
        "full --execute requires SWEML_ALLOW_FULL=YES and SWEML_CANARY_PROOF=<CANARY_PASS.json>"
      exit 0 ;;
    *) echo "BLOCKED: unknown argument: $1" >&2; exit 2 ;;
  esac
done

validate_run_id() {
  local value="$1"
  [[ "$value" =~ ^[a-z0-9_-]+$ ]] || {
    echo "BLOCKED: run_id must match ^[a-z0-9_-]+$: $value" >&2
    return 2
  }
}

assert_sha() {
  local expected="$1" path="$2" got
  [[ -f "$path" ]] || { echo "BLOCKED: missing file: $path" >&2; return 2; }
  got="$(sha256sum "$path" | awk '{print $1}')"
  [[ "$got" == "$expected" ]] || {
    echo "BLOCKED: sha256 mismatch path=$path expected=$expected got=$got" >&2
    return 2
  }
}

validate_static() {
  validate_run_id "$RUN_ID"
  if validate_run_id "Bad_Tag" >/dev/null 2>&1; then
    echo "BLOCKED: uppercase run_id negative test unexpectedly passed" >&2
    return 2
  fi
  [[ "$(wc -l < "$CLEAN_IDS" | tr -d ' ')" == "274" ]] || {
    echo "BLOCKED: clean subset is not 274 lines" >&2; return 2;
  }
  [[ "$(sort -u "$CLEAN_IDS" | wc -l | tr -d ' ')" == "274" ]] || {
    echo "BLOCKED: clean subset contains duplicate instance ids" >&2; return 2;
  }
  [[ "$(wc -l < "$EXCLUDED_IDS" | tr -d ' ')" == "26" ]] || {
    echo "BLOCKED: Gradle exclusion list is not 26 lines" >&2; return 2;
  }
  grep -Fxq "$CANARY_INSTANCE_ID" "$CLEAN_IDS" || {
    echo "BLOCKED: canary instance is not in the clean274 contract: $CANARY_INSTANCE_ID" >&2; return 2;
  }
  [[ "$AGENT_DOCKER_NETWORK" == "bridge" ]] || {
    echo "BLOCKED: actual qwen-code agent containers require SWEML_AGENT_DOCKER_NETWORK=bridge" >&2; return 2;
  }
  assert_sha "28b7f874e48496399077d276f9f2b163a077ddf0a70dc507c148d58da826baa9" \
    "$DATASET_ROOT/data/test-00000-of-00001.parquet"
  assert_sha "4312d17509b431824b79f85bdebe7d477b1fe1f67f0e31d4386ed668cf46c456" "$P0_MAP"
  assert_sha "4027619e50a0d0096df9e9c74584ec75577920cee73564156b05afbfcad2f3d7" "$BASE_RUNNER"
  [[ -x "$QWEN_ROOT/node_modules/.bin/qwen" ]] || {
    echo "BLOCKED: qwen executable missing: $QWEN_ROOT/node_modules/.bin/qwen" >&2; return 2;
  }
  "$PY" - "$QWEN_ROOT/node_modules/@qwen-code/qwen-code/package.json" "$QWEN_CODE_VERSION" <<'PY'
import json, sys
path, expected = sys.argv[1:]
version = json.load(open(path))["version"]
if version != expected:
    raise SystemExit(f"BLOCKED: expected qwen-code {expected}, got {version}")
print(f"qwen_code_package_version={version}")
PY
  local host_node_version host_qwen_version
  host_node_version="$("$QWEN_ROOT/node_modules/node/bin/node" --version)"
  host_qwen_version="$(PATH="$QWEN_ROOT/node_modules/node/bin:$QWEN_ROOT/node_modules/.bin:$PATH" qwen --version)"
  [[ "$host_node_version" == "$QWEN_NODE_VERSION" ]] || {
    echo "BLOCKED: host-side staged node version mismatch expected=$QWEN_NODE_VERSION got=$host_node_version" >&2; return 2;
  }
  [[ "$host_qwen_version" == "$QWEN_CODE_VERSION" ]] || {
    echo "BLOCKED: host-side staged qwen version mismatch expected=$QWEN_CODE_VERSION got=$host_qwen_version" >&2; return 2;
  }
  printf 'qwen_node_host_version=%s\nqwen_code_host_version=%s\n' "$host_node_version" "$host_qwen_version"
}

validate_plan_without_docker_or_model() {
  local tmp rc
  tmp="$(mktemp -d /tmp/sweml_clean274_validate.XXXXXX)"
  trap 'rm -rf "$tmp"' RETURN
  set +e
  OPENAI_API_KEY=EMPTY \
  SWEML_DATASET_ROOT="$DATASET_ROOT" \
  SWEML_QWENCODE_BASE_RUNNER="$BASE_RUNNER" \
  SWEV_P0_MAP="$P0_MAP" \
  SWEV_INSTANCES_FILE="$CLEAN_IDS" \
  SWEV_QWEN_ROOT="$QWEN_ROOT" \
  "$PY" "$ADAPTER" \
    --run-root "$tmp/run" \
    --p0-map "$P0_MAP" \
    --instances-file "$CLEAN_IDS" \
    --base-url "$BASE_URL" \
    --model "$MODEL" \
    --reasoning-effort "" \
    --max-output-tokens 65536 \
    --context-limit 262144 \
    --litellm-provider openai \
    --agent-scaffold qwencode \
    --qwen-code-version "$QWEN_CODE_VERSION" \
    --concurrency "$CONCURRENCY" \
    --include-deferred \
    --keep-images \
    --dry-run \
    --fake-no-key >"$tmp/validate.log" 2>&1
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    tail -80 "$tmp/validate.log" >&2
    return "$rc"
  fi
  "$PY" - "$tmp/run/dry_run_plan.json" "$tmp/run/clean274_dry_run_contract.json" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1]))
contract = json.load(open(sys.argv[2]))
assert plan["instance_count"] == 274, plan["instance_count"]
assert len(set(plan["instances"])) == 274
assert contract["status"] == "verified", contract
print("dry_run_instance_count=274")
print("dry_run_unique_instance_ids=274")
print("dry_run_contract=verified")
PY
  rm -rf "$tmp"
  trap - RETURN
}

validate_canary_proof() {
  local proof="${SWEML_CANARY_PROOF:-}"
  [[ -n "$proof" && -f "$proof" ]] || {
    echo "BLOCKED: full execution requires SWEML_CANARY_PROOF=<existing CANARY_PASS.json>" >&2
    return 2
  }
  "$PY" - "$proof" "$BASE_URL" "$MODEL" "$QWEN_ROOT" "$QWEN_CODE_VERSION" "$SERVING_PROFILE" "$AGENT_DOCKER_NETWORK" <<'PY'
import json, sys
path, base_url, model, qwen_root, version, profile, network = sys.argv[1:]
data = json.load(open(path))
required = {
    "status": "pass",
    "base_url": base_url,
    "model": model,
    "qwen_root": qwen_root,
    "qwen_code_version_in_container": version,
    "serving_profile": profile,
    "agent_docker_network": network,
    "results_rows": 1,
    "unique_instance_ids": 1,
}
bad = {key: {"expected": expected, "got": data.get(key)} for key, expected in required.items() if data.get(key) != expected}
if bad:
    raise SystemExit(f"BLOCKED: canary proof mismatch: {bad}")
if data.get("model_path_before") != data.get("model_path_after"):
    raise SystemExit("BLOCKED: canary proof has model identity drift")
if profile == "instruct2507" and int(data.get("tool_result_blocks", 0)) <= 0:
    raise SystemExit("BLOCKED: Instruct-2507 canary proof has no tool_result blocks")
print(f"canary_proof=verified path={path}")
PY
}

canary_local_ref() {
  "$PY" - "$P0_MAP" "$CANARY_INSTANCE_ID" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
row = data.get(sys.argv[2]) or {}
ref = row.get("local_ref")
if not ref:
    raise SystemExit(f"BLOCKED: canary image local_ref missing for {sys.argv[2]}")
print(ref)
PY
}

in_container_qwen_version_gate() {
  mkdir -p "$RUN_ROOT/scaffold"
  local local_ref output rc node_output
  local_ref="$(canary_local_ref)"
  docker image inspect "$local_ref" > "$RUN_ROOT/scaffold/canary_image_inspect.json"
  set +e
  output="$(docker run --rm --network none --pull=never \
    -v "$QWEN_ROOT:$QWEN_MOUNT:ro" \
    -e "PATH=$QWEN_MOUNT/node_modules/node/bin:$QWEN_MOUNT/node_modules/.bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    "$local_ref" bash -lc \
    "export PATH=$QWEN_MOUNT/node_modules/node/bin:$QWEN_MOUNT/node_modules/.bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; qwen --version" \
    2>"$RUN_ROOT/scaffold/qwen_version_in_container.stderr.txt")"
  rc=$?
  set -e
  printf '%s\n' "$output" > "$RUN_ROOT/scaffold/qwen_version_in_container.txt"
  printf '%s\n' "$rc" > "$RUN_ROOT/scaffold/qwen_version_in_container.rc"
  [[ $rc -eq 0 && "$output" == "$QWEN_CODE_VERSION" ]] || {
    echo "BLOCKED: in-container qwen version expected=$QWEN_CODE_VERSION got=$output rc=$rc" >&2
    return 2
  }
  node_output="$(docker run --rm --network none --pull=never \
    -v "$QWEN_ROOT:$QWEN_MOUNT:ro" \
    "$local_ref" "$QWEN_MOUNT/node_modules/node/bin/node" --version)"
  printf '%s\n' "$node_output" > "$RUN_ROOT/scaffold/node_version_in_container.txt"
  [[ "$node_output" == "$QWEN_NODE_VERSION" ]] || {
    echo "BLOCKED: in-container node version expected=$QWEN_NODE_VERSION got=$node_output" >&2
    return 2
  }
  printf 'qwen_code_in_container_version=%s\nqwen_node_in_container_version=%s\n' "$output" "$node_output"
}

in_container_serving_connectivity_gate() {
  mkdir -p "$RUN_ROOT/scaffold"
  local local_ref models_url output rc
  local_ref="$(canary_local_ref)"
  models_url="${BASE_URL%/}/models"
  printf 'docker_network=%s\nmodels_url=%s\n' "$AGENT_DOCKER_NETWORK" "$models_url" \
    > "$RUN_ROOT/scaffold/serving_connectivity_contract.txt"
  set +e
  output="$(docker run --rm --network "$AGENT_DOCKER_NETWORK" --pull=never \
    -e "SWEML_MODELS_URL=$models_url" \
    "$local_ref" bash -lc \
    'command -v curl >/dev/null && code="$(curl --noproxy "*" -sS -o /tmp/sweml_models.json -w "%{http_code}" --connect-timeout 10 --max-time 30 "$SWEML_MODELS_URL")" && printf "%s\n" "$code" && test "$code" = 200' \
    2>"$RUN_ROOT/scaffold/models_http.stderr.txt")"
  rc=$?
  set -e
  printf '%s\n' "$output" > "$RUN_ROOT/scaffold/models_http_status.txt"
  printf '%s\n' "$rc" > "$RUN_ROOT/scaffold/models_http.rc"
  [[ $rc -eq 0 && "$output" == "200" ]] || {
    echo "BLOCKED: in-container serving connectivity expected HTTP 200 got=$output rc=$rc network=$AGENT_DOCKER_NETWORK" >&2
    return 2
  }
  printf 'qwen_agent_container_network=%s\nqwen_agent_container_models_http=%s\n' "$AGENT_DOCKER_NETWORK" "$output"
}

in_container_public_egress_denied_gate() {
  mkdir -p "$RUN_ROOT/scaffold"
  local local_ref label url output rc
  local_ref="$(canary_local_ref)"
  for spec in "pypi_org=https://pypi.org/" "github_com=https://github.com/"; do
    label="${spec%%=*}"
    url="${spec#*=}"
    set +e
    output="$(docker run --rm --network "$AGENT_DOCKER_NETWORK" --pull=never \
      -e "SWEML_PUBLIC_URL=$url" \
      "$local_ref" bash -lc \
      'curl --noproxy "*" -sS -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$SWEML_PUBLIC_URL"' \
      2>"$RUN_ROOT/scaffold/${label}_curl.stderr.txt")"
    rc=$?
    set -e
    printf '%s\n' "$output" > "$RUN_ROOT/scaffold/${label}_curl.stdout.txt"
    printf '%s\n' "$rc" > "$RUN_ROOT/scaffold/${label}_curl.rc"
    printf 'url=%s\ndocker_network=%s\ncurl_rc=%s\nhttp_status=%s\n' \
      "$url" "$AGENT_DOCKER_NETWORK" "$rc" "${output:-<empty>}" \
      > "$RUN_ROOT/scaffold/${label}_egress_contract.txt"
    if [[ $rc -eq 0 ]]; then
      echo "BLOCKED: public egress unexpectedly reachable url=$url http_status=$output" >&2
      return 2
    fi
    printf 'public_egress_denied url=%s curl_rc=%s raw_http_status=%s\n' \
      "$url" "$rc" "${output:-<empty>}"
  done
}

write_canary_proof() {
  "$PY" - "$RUN_ROOT" "$BASE_URL" "$MODEL" "$QWEN_ROOT" "$QWEN_CODE_VERSION" "$CANARY_INSTANCE_ID" "$SERVING_PROFILE" "$AGENT_DOCKER_NETWORK" <<'PY'
import hashlib, json, sys
from pathlib import Path
run_root, base_url, model, qwen_root, version, iid, profile, network = sys.argv[1:]
root = Path(run_root)
results = [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines() if line.strip()]
before = json.load(open(root / "serving_config/get_model_info_before.json"))
after = json.load(open(root / "serving_config/get_model_info_after.json"))
runtime_version = (root / "scaffold/qwen_version_in_container.txt").read_text().strip()
models_http = (root / "scaffold/models_http_status.txt").read_text().strip()
if len(results) != 1 or len({row.get("instance_id") for row in results}) != 1 or results[0].get("instance_id") != iid:
    raise SystemExit("BLOCKED: canary result ledger is not exactly the selected instance")
if runtime_version != version:
    raise SystemExit("BLOCKED: canary runtime version evidence mismatch")
if before.get("model_path") != after.get("model_path"):
    raise SystemExit("BLOCKED: canary before/after model_path mismatch")
if models_http != "200":
    raise SystemExit("BLOCKED: canary container serving connectivity proof is not HTTP 200")
tool_result_blocks = 0
for stream in sorted(root.glob("*/**/agent/qwen_attempt_*.stdout.jsonl")):
    for line in stream.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = ((record.get("message") or {}).get("content") or [])
        if isinstance(content, list):
            tool_result_blocks += sum(isinstance(item, dict) and item.get("type") == "tool_result" for item in content)
if profile == "instruct2507" and tool_result_blocks <= 0:
    raise SystemExit("BLOCKED: Instruct-2507 canary emitted no tool_result blocks")
payload = {
    "status": "pass",
    "run_root": run_root,
    "instance_id": iid,
    "results_rows": 1,
    "unique_instance_ids": 1,
    "resolved": bool(results[0].get("resolved")),
    "base_url": base_url,
    "model": model,
    "model_path_before": before.get("model_path"),
    "model_path_after": after.get("model_path"),
    "qwen_root": qwen_root,
    "qwen_code_version_in_container": runtime_version,
    "serving_profile": profile,
    "agent_docker_network": network,
    "models_http_status_in_container": int(models_http),
    "tool_result_blocks": tool_result_blocks,
    "results_jsonl_sha256": hashlib.sha256((root / "results.jsonl").read_bytes()).hexdigest(),
}
(root / "CANARY_PASS.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(f"canary_pass={root / 'CANARY_PASS.json'}")
PY
}

capture_serving_config() {
  local phase="$1"
  "$PY" - "$phase" "$RUN_ROOT" "$BASE_URL" "$MODEL_PATH_SUFFIX" <<'PY'
import json, os, sys, urllib.request
from pathlib import Path

phase, run_root, base_url, expected_suffix = sys.argv[1:]
root = Path(run_root) / "serving_config"
root.mkdir(parents=True, exist_ok=True)
origin = base_url.removesuffix("/v1").rstrip("/")

def get(path):
    with urllib.request.urlopen(origin + path, timeout=20) as response:
        return json.load(response)

def redact(value, secrets):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in {"api_key", "admin_api_key"}:
                if isinstance(item, str) and item and item != "<REDACTED>":
                    secrets.append(item)
                out[key] = "<REDACTED>"
            else:
                out[key] = redact(item, secrets)
        return out
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    return value

model_info = get("/get_model_info")
model_path = str(model_info.get("model_path", ""))
if not model_path.endswith(expected_suffix):
    raise SystemExit(f"BLOCKED: model_path mismatch phase={phase} path={model_path!r}")
server_info_raw = get("/get_server_info")
secret_values = []
server_info = redact(server_info_raw, secret_values)
server_text = json.dumps(server_info, sort_keys=True)
leaked = sum(1 for secret in secret_values if secret in server_text)
if leaked:
    raise SystemExit(f"BLOCKED: redacted server_info retained {leaked} secret values")
(root / f"get_model_info_{phase}.json").write_text(json.dumps(model_info, indent=2, sort_keys=True) + "\n")
(root / f"get_server_info_{phase}.redacted.json").write_text(json.dumps(server_info, indent=2, sort_keys=True) + "\n")
(root / f"server_info_secret_scan_{phase}.json").write_text(json.dumps({"status": "pass", "redacted_value_count": len(secret_values), "leaked_value_count": leaked}, indent=2, sort_keys=True) + "\n")
if phase == "after":
    before = json.load(open(root / "get_model_info_before.json"))
    if before.get("model_path") != model_info.get("model_path"):
        (Path(run_root) / "INVALID_MODEL_IDENTITY_CHANGE").write_text("before/after model_path mismatch\n")
        raise SystemExit("BLOCKED: before/after model_path mismatch; entire run invalid")
print(f"serving_identity_{phase}=verified")
PY
}

stress_serving_c16() {
  "$PY" - "$RUN_ROOT" "$BASE_URL" "$MODEL" <<'PY'
import concurrent.futures, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

run_root, base_url, model = sys.argv[1:]
url = base_url.rstrip("/") + "/chat/completions"
key = os.environ.get("OPENAI_API_KEY", "EMPTY")
tool = {
    "type": "function",
    "function": {
        "name": "read_repository_file",
        "description": "Read a repository file before editing it.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
}
payload = {
    "model": model,
    "temperature": 0,
    "max_tokens": 64,
    "messages": [{"role": "user", "content": ("Inspect the repository and call the file-reading tool for README.md before proposing a patch. " * 64).strip()}],
    "tools": [tool],
    "tool_choice": "auto",
}
body = json.dumps(payload).encode()

def one(index):
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.load(response)
            message = ((data.get("choices") or [{}])[0].get("message") or {})
            return {"index": index, "status": response.status, "latency_seconds": round(time.monotonic() - started, 3), "tool_calls": len(message.get("tool_calls") or [])}
    except urllib.error.HTTPError as exc:
        return {"index": index, "status": exc.code, "latency_seconds": round(time.monotonic() - started, 3), "error": "HTTPError"}
    except Exception as exc:
        return {"index": index, "status": 0, "latency_seconds": round(time.monotonic() - started, 3), "error": type(exc).__name__}

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    rows = list(pool.map(one, range(16)))
counts = {
    "total": len(rows),
    "http_200": sum(row["status"] == 200 for row in rows),
    "http_429": sum(row["status"] == 429 for row in rows),
    "http_5xx": sum(500 <= row["status"] < 600 for row in rows),
    "timeouts_or_exceptions": sum(row["status"] == 0 for row in rows),
    "tool_calls_present": sum(row.get("tool_calls", 0) > 0 for row in rows),
}
passed = counts["http_200"] == 16 and counts["http_429"] == 0 and counts["http_5xx"] == 0 and counts["timeouts_or_exceptions"] == 0
# Tool-call presence is recorded, but serving capacity is gated on transport health.
out = {"status": "pass" if passed else "fail", "concurrency": 16, "temperature": 0, "counts": counts, "requests": rows}
path = Path(run_root) / "serving_config/stress_c16_summary.json"
path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
if out["status"] != "pass":
    raise SystemExit(f"BLOCKED: serving stress failed: {counts}")
print("serving_stress_c16=16/16_http_200")
PY
}

capture_disk() {
  local stamp="$1"
  mkdir -p "$RUN_ROOT/disk"
  df -h / > "$RUN_ROOT/disk/df_h_${stamp}.txt"
  df -ih / > "$RUN_ROOT/disk/df_ih_${stamp}.txt"
  local bytes_free inode_free
  bytes_free="$(df -P / | awk 'NR==2 {gsub(/%/,"",$5); print 100-$5}')"
  inode_free="$(df -Pi / | awk 'NR==2 {gsub(/%/,"",$5); print 100-$5}')"
  printf '{"bytes_free_pct":%s,"inode_free_pct":%s,"stamp":"%s"}\n' \
    "$bytes_free" "$inode_free" "$stamp" > "$RUN_ROOT/disk/status_${stamp}.json"
  if (( bytes_free < 10 || inode_free < 10 )); then
    printf 'disk watermark crossed at %s: bytes_free_pct=%s inode_free_pct=%s\n' \
      "$stamp" "$bytes_free" "$inode_free" > "$RUN_ROOT/STOP"
    return 2
  fi
}

disk_monitor() {
  while [[ -f "$RUN_ROOT/RUN_ACTIVE" ]]; do
    local stamp
    stamp="$(date -u +%Y%m%dt%H%M%Sz)"
    capture_disk "$stamp" || true
    for _ in $(seq 1 60); do
      [[ -f "$RUN_ROOT/RUN_ACTIVE" ]] || break
      sleep 10
    done
  done
}

finalize_sha256s() {
  "$PY" - "$RUN_ROOT" "$DATASET_ROOT" "$SELECTED_IDS" <<'PY'
import hashlib, sys
from pathlib import Path
run_root, dataset_root, selected_ids = map(Path, sys.argv[1:])
paths = [
    run_root / "results.jsonl",
    run_root / "events.jsonl",
    run_root / "runner_config.json",
    run_root / "score_summary.json",
    run_root / "score_summary_clean274.json",
    run_root / "overlay.yaml",
    run_root / "CANARY_PASS.json",
    selected_ids,
    dataset_root / "data/test-00000-of-00001.parquet",
]
patterns = [
    "serving_config/*.json", "scaffold/*", "disk/*", "instances/*/agent/qwen_attempt_*.stdout.jsonl",
    "instances/*/agent/prediction.patch.diff", "instances/*/eval/*.json",
    "failed/*/agent/qwen_attempt_*.stdout.jsonl", "failed/*/eval/*.json",
]
for pattern in patterns:
    paths.extend(sorted(run_root.glob(pattern)))
seen = set(); lines = []
for path in paths:
    if path in seen or not path.is_file():
        continue
    seen.add(path)
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    try: display = path.relative_to(run_root)
    except ValueError: display = path
    lines.append(f"{h.hexdigest()}  {display}")
(run_root / "SHA256SUMS").write_text("\n".join(lines) + "\n")
PY
}

validate_static
validate_plan_without_docker_or_model
if [[ "$MODE" == "validate" ]]; then
  echo "READY_PLAN_ONLY: clean274 QwenCode launch contract validated; no Docker/model/worker execution occurred"
  exit 0
fi

RUN_ROOT="$RUNS_ROOT/$RUN_ID"
export RUN_ROOT
SELECTED_IDS="$CLEAN_IDS"
EXPECTED_COUNT=274
RUN_MODE_ARG="--execute"

if [[ "$MODE" == "canary" ]]; then
  [[ "${SWEML_ALLOW_CANARY:-}" == "YES" ]] || {
    echo "BLOCKED: canary execution requires SWEML_ALLOW_CANARY=YES" >&2
    exit 2
  }
  SELECTED_IDS="$RUN_ROOT/canary_instance_ids.txt"
  EXPECTED_COUNT=1
  CONCURRENCY=1
  PREHEAT_CONCURRENCY=1
  RUN_MODE_ARG="--canary-only"
else
  [[ "${SWEML_ALLOW_FULL:-}" == "YES" ]] || {
    echo "BLOCKED: full execution requires SWEML_ALLOW_FULL=YES" >&2
    exit 2
  }
  validate_canary_proof
fi

if [[ "${SWEML_SUPERVISOR:-0}" != "1" ]]; then
  mkdir -p "$RUN_ROOT"
  if [[ "$MODE" == "canary" ]]; then
    printf '%s\n' "$CANARY_INSTANCE_ID" > "$SELECTED_IDS"
  fi
  setsid env SWEML_SUPERVISOR=1 SWEML_RUN_ID="$RUN_ID" \
    "$SCRIPT_PATH" "$RUN_MODE_ARG" --run-id "$RUN_ID" > "$RUN_ROOT/launch.log" 2>&1 < /dev/null &
  pid=$!
  printf '%s\n' "$pid" > "$RUN_ROOT/launch.pid"
  printf 'LAUNCHED mode=%s run_root=%s pid=%s\n' "$MODE" "$RUN_ROOT" "$pid"
  exit 0
fi

mkdir -p "$RUN_ROOT/serving_config" "$RUN_ROOT/disk"
if [[ "$MODE" == "canary" ]]; then
  printf '%s\n' "$CANARY_INSTANCE_ID" > "$SELECTED_IDS"
fi
printf '%s\n' "$RUN_ID" > "$RUN_ROOT/RUN_ID"
printf '%q ' "$SCRIPT_PATH" "$RUN_MODE_ARG" --run-id "$RUN_ID" > "$RUN_ROOT/COMMAND.sh"
printf '\n' >> "$RUN_ROOT/COMMAND.sh"
chmod 600 "$RUN_ROOT/COMMAND.sh"
export DOCKER_HOST BASE_URL MODEL
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
monitor_pid=""
supervisor_exit() {
  local rc=$?
  rm -f "$RUN_ROOT/RUN_ACTIVE"
  if [[ -n "$monitor_pid" ]] && kill -0 "$monitor_pid" 2>/dev/null; then
    kill "$monitor_pid" 2>/dev/null || true
    wait "$monitor_pid" 2>/dev/null || true
  fi
  printf '%s\n' "$rc" > "$RUN_ROOT/FINAL_RC"
}
trap supervisor_exit EXIT

docker info >/dev/null
capture_disk "before"
in_container_qwen_version_gate
in_container_serving_connectivity_gate
in_container_public_egress_denied_gate
capture_serving_config "before"
stress_serving_c16
touch "$RUN_ROOT/RUN_ACTIVE"
disk_monitor &
monitor_pid=$!

set +e
SWEML_DATASET_ROOT="$DATASET_ROOT" \
SWEML_EXPECTED_COUNT="$EXPECTED_COUNT" \
SWEML_AGENT_DOCKER_NETWORK="$AGENT_DOCKER_NETWORK" \
SWEML_QWENCODE_BASE_RUNNER="$BASE_RUNNER" \
SWEV_P0_MAP="$P0_MAP" \
SWEV_INSTANCES_FILE="$SELECTED_IDS" \
SWEV_QWEN_ROOT="$QWEN_ROOT" \
SWEV_BASE_URL="$BASE_URL" \
SWEV_MODEL="$MODEL" \
SWEV_REASONING_EFFORT="" \
SWEV_MAX_OUTPUT_TOKENS=65536 \
SWEV_CONTEXT_LIMIT=262144 \
SWEV_LITELLM_PROVIDER=openai \
SWEV_CONCURRENCY="$CONCURRENCY" \
SWEV_PREHEAT_ALL=1 \
SWEV_PREHEAT_CONCURRENCY="$PREHEAT_CONCURRENCY" \
SWEV_KEEP_IMAGES=1 \
"$PY" "$ADAPTER" \
  --run-root "$RUN_ROOT" \
  --p0-map "$P0_MAP" \
  --instances-file "$SELECTED_IDS" \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --reasoning-effort "" \
  --max-output-tokens 65536 \
  --context-limit 262144 \
  --litellm-provider openai \
  --agent-scaffold qwencode \
  --qwen-code-version "$QWEN_CODE_VERSION" \
  --concurrency "$CONCURRENCY" \
  --include-deferred \
  --preheat-all \
  --preheat-concurrency "$PREHEAT_CONCURRENCY" \
  --keep-images
runner_rc=$?
set -e

rm -f "$RUN_ROOT/RUN_ACTIVE"
wait "$monitor_pid" 2>/dev/null || true
capture_disk "after" || runner_rc=3
capture_serving_config "after" || runner_rc=3
if [[ ! -f "$RUN_ROOT/results.jsonl" ]] || [[ "$(wc -l < "$RUN_ROOT/results.jsonl" | tr -d ' ')" != "$EXPECTED_COUNT" ]]; then
  echo "BLOCKED: final results.jsonl denominator is not $EXPECTED_COUNT" >&2
  runner_rc=3
fi
if [[ "$MODE" == "canary" && "$runner_rc" -eq 0 ]]; then
  write_canary_proof || runner_rc=3
fi
finalize_sha256s
printf '%s\n' "$runner_rc" > "$RUN_ROOT/FINAL_RC"
exit "$runner_rc"
