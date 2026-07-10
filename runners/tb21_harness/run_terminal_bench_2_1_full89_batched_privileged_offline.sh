#!/usr/bin/env bash
set -euo pipefail

# Additive privileged-Docker variant of the Terminal-Bench 2.1 full89
# batched runner. It keeps the canonical offline/bootstrap behavior but
# never starts, restarts, prunes, or deletes the retired rootless-vfs stack.
# Use only with TB21_ALLOW_PRIVILEGED_DOCKER=1 and DOCKER_HOST=unix:///var/run/docker.sock.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
cd "$REPO_ROOT"

if [[ "${TB21_SOURCE_REMOTE_BASHRC:-1}" == 1 && -f "$HOME/.bashrc" ]]; then
  set +u
  # Remote .bashrc is the workspace authority for proxy/TMP/PATH in non-interactive SSH.
  # Suppress alias chatter; keep exported proxy variables for API preflight and agents.
  source "$HOME/.bashrc" >/dev/null 2>&1 || true
  set -u
fi

export DOCKER_HOST="${DOCKER_HOST:-unix:///var/run/docker.sock}"
export TB21_ALLOW_PRIVILEGED_DOCKER="${TB21_ALLOW_PRIVILEGED_DOCKER:-0}"
export TB21_PRIVILEGED_DOCKER_HOST="${TB21_PRIVILEGED_DOCKER_HOST:-unix:///var/run/docker.sock}"
export TB_DOCKER_SDK_API_VERSION="${TB_DOCKER_SDK_API_VERSION:-1.45}"
export TB_DOCKER_SDK_TIMEOUT_SEC="${TB_DOCKER_SDK_TIMEOUT_SEC:-300}"
export TB21_BASE_SKIP_TEST_COPY_TASK_IDS="${TB_SKIP_TEST_COPY_TASK_IDS:-build-pov-ray}"
export TB_SKIP_TEST_COPY_TASK_IDS="$TB21_BASE_SKIP_TEST_COPY_TASK_IDS"
export TB21_FULL89_IMAGE_MANIFEST="${TB21_FULL89_IMAGE_MANIFEST:-manifests/images/terminal_bench_2_1_full89_p0_closure_r2.yaml}"
export TB21_BATCH_SIZE="${TB21_BATCH_SIZE:-12}"
export TB21_BATCH_DIR="${TB21_BATCH_DIR:-manifests/images/terminal_bench_2_1_full89_batches}"
export TB21_BATCH_PLAN_JSON="${TB21_BATCH_PLAN_JSON:-$TB21_BATCH_DIR/plan.json}"
export TB21_BATCH_RUN="${TB21_BATCH_RUN:-1}"
export TB21_BATCH_START="${TB21_BATCH_START:-1}"
export TB21_BATCH_LIMIT="${TB21_BATCH_LIMIT:-0}"
export TB21_FULL_CONCURRENCY="${TB21_FULL_CONCURRENCY:-12}"
export TB21_PREHEAT_PULL="${TB21_PREHEAT_PULL:-1}"
export TB21_PREHEAT_FORCE_PULL="${TB21_PREHEAT_FORCE_PULL:-0}"
export TB21_PREHEAT_LOAD_FALLBACK="${TB21_PREHEAT_LOAD_FALLBACK:-1}"
export TB21_RESTART_DOCKER_AFTER_BATCH="${TB21_RESTART_DOCKER_AFTER_BATCH:-0}"
export TB21_RUN_CLEANUP_HELPER="${TB21_RUN_CLEANUP_HELPER:-0}"
export TB21_REMOVE_BATCH_IMAGES="${TB21_REMOVE_BATCH_IMAGES:-0}"
export TB21_BIND_PAYLOAD_PREFLIGHT="${TB21_BIND_PAYLOAD_PREFLIGHT:-1}"
export TB21_BIND_PAYLOAD_PREFLIGHT_ONLY="${TB21_BIND_PAYLOAD_PREFLIGHT_ONLY:-0}"
export TB21_ENABLE_KVM_DEVICE="${TB21_ENABLE_KVM_DEVICE:-1}"
export TB21_KVM_DEVICE_PATH="${TB21_KVM_DEVICE_PATH:-/dev/kvm}"
export TB21_KVM_DEVICE_PREFLIGHT_ONLY="${TB21_KVM_DEVICE_PREFLIGHT_ONLY:-0}"
export TB21_KVM_DEVICE_DATASET_ROOT="${TB21_KVM_DEVICE_DATASET_ROOT:-_coordination/20260625_harbor_bench/artifacts/tb21_kvm_device_datasets}"
export TB21_ORACLE_MOUNT_GUARD_REQUIRED="${TB21_ORACLE_MOUNT_GUARD_REQUIRED:-1}"
export TB21_ORACLE_MOUNT_GUARD_CHECK_ONLY="${TB21_ORACLE_MOUNT_GUARD_CHECK_ONLY:-0}"
export TB21_TB_ROOT="${TB21_TB_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench}"
export TB21_ORACLE_PREFER_SOLUTION_YAML="${TB21_ORACLE_PREFER_SOLUTION_YAML:-1}"
export TB_DOCKER_COMPOSE_DOWN_TIMEOUT_SEC="${TB_DOCKER_COMPOSE_DOWN_TIMEOUT_SEC:-120}"
export TB_DOCKER_FORCE_CLEANUP_HELPER="${TB_DOCKER_FORCE_CLEANUP_HELPER:-$REPO_ROOT/scripts/cleanup_tb21_worker.sh}"
TB21_FULL_TAG_RAW="${TB21_FULL_TAG:-$(date -u +%Y%m%dt%H%M%sz)}"
TB21_FULL_TAG="$(printf '%s' "$TB21_FULL_TAG_RAW" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/_/g')"
export TB21_FULL_TAG
export TB21_FULL89_DATASET="${TB21_FULL89_DATASET:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-20260629}"
export TB21_FULL89_IMAGE_MAP="${TB21_FULL89_IMAGE_MAP:-manifests/images/tb21_prebuilt_image_map_full89_closure_r2.json}"
export TB2_OFFLINE_TEST_BOOTSTRAP=1
export TB2_SKIP_DATASET_REBUILD="${TB2_SKIP_DATASET_REBUILD:-1}"
if [[ -z "${TB2_RUNTIME_CLOSURE_REPAIR+x}" ]]; then
  export TB2_RUNTIME_CLOSURE_REPAIR="$REPO_ROOT/scripts/repair_tb21_full89_runtime_closure.py"
fi

case "$TB21_BATCH_SIZE" in ''|*[!0-9]*) echo "TB21_BATCH_SIZE must be a positive integer" >&2; exit 2 ;; esac
case "$TB21_FULL_CONCURRENCY" in ''|*[!0-9]*) echo "TB21_FULL_CONCURRENCY must be a positive integer" >&2; exit 2 ;; esac
case "$TB21_BATCH_START" in ''|*[!0-9]*) echo "TB21_BATCH_START must be a positive integer" >&2; exit 2 ;; esac
case "$TB21_BATCH_LIMIT" in ''|*[!0-9]*) echo "TB21_BATCH_LIMIT must be a non-negative integer" >&2; exit 2 ;; esac
if [[ "$TB21_BATCH_START" -lt 1 ]]; then echo "TB21_BATCH_START must be a positive integer" >&2; exit 2; fi

check_oracle_mount_guard_for_concurrency() {
  local agent="${TB_AGENT:-terminus-2}"
  if [[ "$agent" != "oracle" ]]; then
    echo "[tb21-batched-privileged] oracle_mount_guard=skipped agent=$agent"
    return 0
  fi
  if [[ "$TB21_FULL_CONCURRENCY" -le 1 ]]; then
    echo "[tb21-batched-privileged] oracle_mount_guard=skipped concurrency=$TB21_FULL_CONCURRENCY"
    return 0
  fi
  if [[ "$TB21_ORACLE_MOUNT_GUARD_REQUIRED" != "1" ]]; then
    echo "[tb21-batched-privileged] oracle_mount_guard=disabled concurrency=$TB21_FULL_CONCURRENCY" >&2
    return 0
  fi
  local oracle_agent_path="$TB21_TB_ROOT/terminal_bench/agents/oracle_agent.py"
  if [[ ! -f "$oracle_agent_path" ]]; then
    echo "[tb21-batched-privileged] blocked: oracle mount guard missing oracle_agent_path=$oracle_agent_path" >&2
    exit 24
  fi
  if ! grep -q "TB21_ORACLE_SOLUTION_VERIFY" "$oracle_agent_path"; then
    echo "[tb21-batched-privileged] blocked: oracle mount guard missing marker=TB21_ORACLE_SOLUTION_VERIFY oracle_agent_path=$oracle_agent_path" >&2
    echo "[tb21-batched-privileged] refusing oracle concurrency=$TB21_FULL_CONCURRENCY until /oracle/solution.sh is verified before agent execution" >&2
    exit 24
  fi
  echo "[tb21-batched-privileged] oracle_mount_guard=available concurrency=$TB21_FULL_CONCURRENCY oracle_agent_path=$oracle_agent_path"
}

check_oracle_mount_guard_for_concurrency
if [[ "$TB21_ORACLE_MOUNT_GUARD_CHECK_ONLY" == "1" ]]; then
  echo "[tb21-batched-privileged] oracle_mount_guard_check_only=done"
  exit 0
fi

runtime_closure_static_gate() {
  if [[ "${TB21_STATIC_RUNTIME_CLOSURE_GATE:-1}" != "1" ]]; then
    echo "[tb21-runtime-closure] static_gate=skipped TB21_STATIC_RUNTIME_CLOSURE_GATE=${TB21_STATIC_RUNTIME_CLOSURE_GATE:-unset}"
    return 0
  fi
  local report_dir="${TB21_RUNTIME_CLOSURE_REPORT_DIR:-_coordination/20260625_harbor_bench/reports}"
  mkdir -p "$report_dir"
  local matrix="${TB21_RUNTIME_CLOSURE_MATRIX:-$report_dir/tb21_full89_runtime_closure_matrix_${TB21_FULL_TAG}.jsonl}"
  local summary="${TB21_RUNTIME_CLOSURE_SUMMARY:-$report_dir/tb21_full89_runtime_closure_matrix_${TB21_FULL_TAG}.summary.json}"
  local vendor="${TB21_RUNTIME_CLOSURE_VENDOR_COMMANDS:-$report_dir/tb21_full89_runtime_closure_vendor_${TB21_FULL_TAG}.sh}"
  local gate="${TB21_RUNTIME_CLOSURE_GATE_JSON:-$report_dir/tb21_full89_runtime_closure_static_gate_${TB21_FULL_TAG}.json}"
  python3 scripts/build_tb21_full89_closure_matrix.py \
    --dataset-dir "$TB21_FULL89_DATASET" \
    --output "$matrix" \
    --summary-output "$summary" \
    --vendor-commands-output "$vendor"
  local gate_rc=0
  python3 scripts/tb21_runtime_closure_static_gate.py --matrix "$matrix" --output-json "$gate" --expect-closed || gate_rc=$?
  if [[ "$gate_rc" == "0" ]]; then
    echo "[tb21-runtime-closure] static_gate=closed gate=$gate"
    return 0
  fi
  if [[ "$gate_rc" == "24" && "${TB21_ALLOW_OPEN_RUNTIME_CLOSURE:-0}" == "1" ]]; then
    echo "[tb21-runtime-closure] static_gate=open_but_allowed gate=$gate" >&2
    echo "[tb21-runtime-closure] exploratory run only; do not claim offline full readiness from this run." >&2
    return 0
  fi
  echo "[tb21-runtime-closure] blocked: runtime dependency closure is still open; gate=$gate" >&2
  echo "[tb21-runtime-closure] set TB21_ALLOW_OPEN_RUNTIME_CLOSURE=1 only for trace-gathering exploratory runs." >&2
  exit "$gate_rc"
}



prepare_kvm_device_dataset() {
  if [[ "${TB21_ENABLE_KVM_DEVICE:-1}" != "1" ]]; then
    echo "[tb21-batched-privileged] kvm_device=disabled"
    return 0
  fi
  local device_path="${TB21_KVM_DEVICE_PATH:-/dev/kvm}"
  if [[ ! -e "$device_path" ]]; then
    echo "[tb21-batched-privileged] blocked: kvm device missing path=$device_path" >&2
    exit 24
  fi
  local original_dataset="$TB21_FULL89_DATASET"
  local dataset_root="$TB21_KVM_DEVICE_DATASET_ROOT/$TB21_FULL_TAG"
  mkdir -p "$dataset_root"
  dataset_root="$(cd "$dataset_root" && pwd -P)"
  local effective_dataset="$dataset_root/dataset"
  local summary_json="$dataset_root/kvm_device_summary.json"
  python3 - "$original_dataset" "$effective_dataset" "$device_path" "$summary_json" <<'PY_KVM_DEVICE_DATASET'
from __future__ import annotations
import json
import os
import shutil
import sys
from pathlib import Path

import yaml

src = Path(sys.argv[1]).resolve()
dst = Path(sys.argv[2]).resolve()
device = Path(sys.argv[3])
out = Path(sys.argv[4])
if not src.is_dir():
    raise SystemExit(f"source dataset missing: {src}")
if dst == src or src in dst.parents:
    raise SystemExit(f"refusing unsafe effective dataset path: {dst}")
if dst.exists() or dst.is_symlink():
    shutil.rmtree(dst)
shutil.copytree(src, dst, symlinks=True)
payload_src = Path(str(src) + "_payloads")
payload_dst = Path(str(dst) + "_payloads")
if payload_dst.exists() or payload_dst.is_symlink():
    if payload_dst.is_dir() and not payload_dst.is_symlink():
        shutil.rmtree(payload_dst)
    else:
        payload_dst.unlink()
if payload_src.exists():
    payload_dst.symlink_to(payload_src, target_is_directory=True)
rows = []
entry = f"{device}:/dev/kvm"
for task_dir in sorted(p for p in dst.iterdir() if p.is_dir() and not p.name.startswith("_")):
    compose = task_dir / "docker-compose.yaml"
    if not compose.is_file():
        rows.append({"task_id": task_dir.name, "status": "blocked", "reason": "missing_compose"})
        continue
    data = yaml.safe_load(compose.read_text(encoding="utf-8")) or {}
    services = data.setdefault("services", {})
    client = services.setdefault("client", {})
    volumes = client.get("volumes") or []
    if isinstance(volumes, list) and payload_src.exists():
        for volume in volumes:
            if not isinstance(volume, dict):
                continue
            if volume.get("target") == "/tests":
                volume["source"] = str(payload_dst / "_tb21_bind_test_payloads" / task_dir.name)
            elif volume.get("target") == "/oracle":
                volume["source"] = str(payload_dst / "_tb21_bind_oracle_payloads" / task_dir.name)
    devices = client.setdefault("devices", [])
    if not isinstance(devices, list):
        rows.append({"task_id": task_dir.name, "status": "blocked", "reason": "bad_devices_type"})
        continue
    if entry not in devices:
        devices.append(entry)
    compose.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    rows.append({"task_id": task_dir.name, "status": "ok", "device": entry})
summary = {
    "schema_version": "tb21.kvm_device_dataset.v1",
    "source_dataset": str(src),
    "effective_dataset": str(dst),
    "payload_symlink": str(payload_dst) if payload_src.exists() else None,
    "device_path": str(device),
    "container_device": "/dev/kvm",
    "device_entry": entry,
    "counts": {
        "tasks": len(rows),
        "ok": sum(1 for row in rows if row.get("status") == "ok"),
        "blocked": sum(1 for row in rows if row.get("status") != "ok"),
    },
    "rows": rows,
}
out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if summary["counts"]["tasks"] <= 0 or summary["counts"]["blocked"]:
    raise SystemExit(24)
print(json.dumps(summary["counts"], sort_keys=True))
PY_KVM_DEVICE_DATASET
  export TB21_FULL89_ORIGINAL_DATASET="$original_dataset"
  export TB21_FULL89_DATASET="$effective_dataset"
  echo "[tb21-batched-privileged] kvm_device_dataset=$effective_dataset summary=$summary_json device=${device_path}:/dev/kvm"
}

check_bind_payload_preflight() {
  if [[ "${TB21_BIND_PAYLOAD_PREFLIGHT:-1}" != "1" ]]; then
    echo "[tb21-batched-privileged] bind_payload_preflight=skipped"
    return 0
  fi
  local report_dir="${TB21_BIND_PAYLOAD_PREFLIGHT_REPORT_DIR:-${TB21_RUNTIME_CLOSURE_REPORT_DIR:-_coordination/20260625_harbor_bench/reports}}"
  mkdir -p "$report_dir"
  local output_json="${TB21_BIND_PAYLOAD_PREFLIGHT_JSON:-$report_dir/tb21_bind_payload_preflight_${TB21_FULL_TAG}.json}"
  local preflight_rc=0
  python3 - "$TB21_FULL89_DATASET" "$output_json" <<'PY_BIND_PAYLOAD_PREFLIGHT' || preflight_rc=$?
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import yaml

dataset = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])

def first_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]

payload_base = Path(str(dataset) + "_payloads")
test_root_env = os.environ.get("TB21_BIND_TEST_PAYLOAD_ROOT")
oracle_root_env = os.environ.get("TB21_BIND_ORACLE_PAYLOAD_ROOT")
test_root = Path(test_root_env) if test_root_env else first_existing([
    payload_base / "_tb21_bind_test_payloads",
    dataset / "_tb21_bind_test_payloads",
])
oracle_root = Path(oracle_root_env) if oracle_root_env else first_existing([
    payload_base / "_tb21_bind_oracle_payloads",
    dataset / "_tb21_bind_oracle_payloads",
])
rows = []
errors = []
if not dataset.is_dir():
    errors.append({"task_id": "__dataset__", "reason": "dataset_missing", "path": str(dataset)})

task_dirs = sorted(p for p in dataset.iterdir() if p.is_dir() and not p.name.startswith("_")) if dataset.is_dir() else []
for task_dir in task_dirs:
    task = task_dir.name
    task_errors = []
    test_payload = test_root / task
    oracle_payload = oracle_root / task
    required_test_files = ["run-tests.sh", "test_outputs.py", "solution.sh"]
    for name in required_test_files:
        path = test_payload / name
        if not path.is_file() or path.stat().st_size <= 0:
            task_errors.append({"reason": "missing_or_empty_test_payload_file", "path": str(path)})
    oracle_solution = oracle_payload / "solution.sh"
    if oracle_solution.is_symlink():
        task_errors.append({"reason": "oracle_payload_solution_symlink", "path": str(oracle_solution), "target": os.readlink(oracle_solution)})
    elif not oracle_solution.is_file() or oracle_solution.stat().st_size <= 0:
        task_errors.append({"reason": "missing_or_empty_oracle_payload_file", "path": str(oracle_solution)})
    compose = task_dir / "docker-compose.yaml"
    if not compose.is_file() or compose.stat().st_size <= 0:
        task_errors.append({"reason": "missing_or_empty_compose", "path": str(compose)})
    else:
        try:
            data = yaml.safe_load(compose.read_text(encoding="utf-8")) or {}
            client = ((data.get("services") or {}).get("client") or {})
            volumes = client.get("volumes") or []
            targets = {v.get("target"): str(v.get("source")) for v in volumes if isinstance(v, dict)}
            if targets.get("/tests") != str(test_payload):
                task_errors.append({"reason": "bad_tests_bind_mount", "expected": str(test_payload), "actual": targets.get("/tests")})
            if targets.get("/oracle") != str(oracle_payload):
                task_errors.append({"reason": "bad_oracle_bind_mount", "expected": str(oracle_payload), "actual": targets.get("/oracle")})
        except Exception as exc:
            task_errors.append({"reason": "compose_parse_error", "path": str(compose), "error": f"{type(exc).__name__}: {exc}"})
    rows.append({"task_id": task, "status": "ok" if not task_errors else "blocked", "errors": task_errors})
    errors.extend({"task_id": task, **err} for err in task_errors)
summary = {
    "schema_version": "tb21.bind_payload_preflight.v1",
    "dataset": str(dataset),
    "test_payload_root": str(test_root),
    "oracle_payload_root": str(oracle_root),
    "counts": {
        "tasks": len(task_dirs),
        "ok": sum(1 for row in rows if row["status"] == "ok"),
        "blocked": sum(1 for row in rows if row["status"] != "ok"),
        "errors": len(errors),
    },
    "ready": len(task_dirs) > 0 and not errors,
    "rows": rows,
    "errors": errors,
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary["counts"], sort_keys=True))
if not summary["ready"]:
    raise SystemExit(24)
PY_BIND_PAYLOAD_PREFLIGHT
  if [[ "$preflight_rc" == "0" ]]; then
    echo "[tb21-batched-privileged] bind_payload_preflight=ok json=$output_json"
    return 0
  fi
  echo "[tb21-batched-privileged] blocked: bind payload preflight failed rc=$preflight_rc json=$output_json" >&2
  python3 - "$output_json" <<'PY_BIND_PAYLOAD_REPORT' >&2 || true
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if p.exists():
    data = json.loads(p.read_text())
    for err in data.get("errors", [])[:20]:
        print(json.dumps(err, sort_keys=True))
PY_BIND_PAYLOAD_REPORT
  exit "$preflight_rc"
}


check_privileged_docker() {
  local reason="${1:-health}"
  if [[ "$TB21_ALLOW_PRIVILEGED_DOCKER" != "1" ]]; then
    echo "[tb21-batched-privileged] blocked: set TB21_ALLOW_PRIVILEGED_DOCKER=1 to use privileged docker" >&2
    exit 2
  fi
  if [[ "$DOCKER_HOST" != "$TB21_PRIVILEGED_DOCKER_HOST" ]]; then
    echo "[tb21-batched-privileged] blocked: DOCKER_HOST=$DOCKER_HOST expected=$TB21_PRIVILEGED_DOCKER_HOST" >&2
    exit 2
  fi
  local security
  security="$(docker info --format '{{json .SecurityOptions}}')" || {
    echo "[tb21-batched-privileged] docker_info_failed reason=$reason host=$DOCKER_HOST" >&2
    exit 26
  }
  if grep -q rootless <<<"$security"; then
    echo "[tb21-batched-privileged] blocked: docker reports rootless security options under privileged runner security=$security" >&2
    exit 2
  fi
  docker info --format "[tb21-batched-privileged] docker_health reason=${reason} server={{.ServerVersion}} driver={{.Driver}} root={{.DockerRootDir}} images={{.Images}} containers={{.Containers}} running={{.ContainersRunning}} security={{json .SecurityOptions}}"
}

prepare_kvm_device_dataset
if [[ "$TB21_KVM_DEVICE_PREFLIGHT_ONLY" == "1" ]]; then
  echo "[tb21-batched-privileged] kvm_device_preflight_only=done"
  exit 0
fi

check_bind_payload_preflight
if [[ "$TB21_BIND_PAYLOAD_PREFLIGHT_ONLY" == "1" ]]; then
  echo "[tb21-batched-privileged] bind_payload_preflight_only=done"
  exit 0
fi

runtime_closure_static_gate

check_privileged_docker "initial"
python3 scripts/build_tb21_full89_batch_manifests.py   --image-manifest "$TB21_FULL89_IMAGE_MANIFEST"   --output-dir "$TB21_BATCH_DIR"   --batch-size "$TB21_BATCH_SIZE"   --plan-json "$TB21_BATCH_PLAN_JSON"

mkdir -p runs
run_root="${BENCH_OUTPUT_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_full89_batched}/tb21_batched_${TB_AGENT:-terminus-2}_${TB21_FULL_TAG}"
mkdir -p "$run_root"
cp "$TB21_BATCH_PLAN_JSON" "$run_root/plan.json"

total_batch_count=$(python3 - "$TB21_BATCH_PLAN_JSON" <<'PY_BATCH_COUNT'
import json, sys
print(len(json.load(open(sys.argv[1]))["batches"]))
PY_BATCH_COUNT
)
if [[ "$TB21_BATCH_START" -gt "$total_batch_count" ]]; then
  echo "TB21_BATCH_START=$TB21_BATCH_START exceeds total batches $total_batch_count" >&2
  exit 2
fi
batch_end="$total_batch_count"
if [[ "$TB21_BATCH_LIMIT" != 0 ]]; then
  batch_end=$(( TB21_BATCH_START + TB21_BATCH_LIMIT - 1 ))
  if [[ "$batch_end" -gt "$total_batch_count" ]]; then
    batch_end="$total_batch_count"
  fi
fi
batch_count=$(( batch_end - TB21_BATCH_START + 1 ))

echo "[tb21-batched] docker_host=$DOCKER_HOST batch_size=$TB21_BATCH_SIZE batches=$batch_count batch_start=$TB21_BATCH_START batch_end=$batch_end total_batches=$total_batch_count run=$TB21_BATCH_RUN"
docker info --format '{{.ServerVersion}} {{.Driver}} {{.DockerRootDir}} {{json .SecurityOptions}}'
docker_driver="$(docker info --format '{{.Driver}}')"
if [[ "$docker_driver" == vfs ]]; then
  vfs_cap="${TB21_VFS_MAX_CONCURRENCY:-2}"
  if [[ "$TB21_FULL_CONCURRENCY" -gt "$vfs_cap" && "${TB21_ALLOW_VFS_STRESS:-0}" != 1 ]]; then
    echo "[tb21-batched] refusing TB21_FULL_CONCURRENCY=$TB21_FULL_CONCURRENCY on docker_driver=vfs; current worker rootless/vfs cap is $vfs_cap. Set TB21_ALLOW_VFS_STRESS=1 only for stress tests." >&2
    exit 2
  fi
fi

batch_json() {
  local index="$1"
  python3 - "$TB21_BATCH_PLAN_JSON" "$index" <<'PY_BATCH_JSON'
import json, sys
plan=json.load(open(sys.argv[1])); idx=int(sys.argv[2])-1
print(json.dumps(plan["batches"][idx], sort_keys=True))
PY_BATCH_JSON
}

api_preflight() {
  [[ "${TB_API_PREFLIGHT:-1}" == 1 ]] || return 0
  [[ "${TB21_API_PREFLIGHT_DONE:-0}" == 0 ]] || return 0
  python3 - <<'PY_API_PREFLIGHT'
import os, socket, sys
from urllib.parse import urlparse
base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("BASE_URL") or ""
if not base:
    print("[tb21-batched] api_preflight_failed reason=missing_base_url", file=sys.stderr)
    raise SystemExit(2)
parsed = urlparse(base)
if not parsed.scheme or not parsed.hostname:
    print(f"[tb21-batched] api_preflight_failed reason=bad_base_url base={base!r}", file=sys.stderr)
    raise SystemExit(2)
proxy_url = os.environ.get("https_proxy" if parsed.scheme == "https" else "http_proxy") or os.environ.get("HTTPS_PROXY" if parsed.scheme == "https" else "HTTP_PROXY")
proxy_used = False
if proxy_url:
    proxy = urlparse(proxy_url)
    if proxy.hostname:
        host = proxy.hostname
        port = proxy.port or (443 if proxy.scheme == "https" else 80)
        proxy_used = True
        target_label = f"proxy={host}:{port}"
    else:
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        target_label = f"base={host}:{port}"
else:
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    target_label = f"base={host}:{port}"
timeout = float(os.environ.get("TB_API_PREFLIGHT_TIMEOUT_SEC", "10"))
try:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.close()
except Exception as exc:
    print(f"[tb21-batched] api_preflight_failed {target_label} proxy_used={int(proxy_used)} base={base} error={type(exc).__name__}:{str(exc)[:160]}", file=sys.stderr)
    raise SystemExit(2)
print(f"[tb21-batched] api_preflight_ok {target_label} proxy_used={int(proxy_used)} base={base}")
PY_API_PREFLIGHT
  export TB21_API_PREFLIGHT_DONE=1
}

restart_rootless_for_batch() {
  local reason="$1"
  echo "[tb21-batched-privileged] docker_health_only reason=$reason"
  check_privileged_docker "$reason"
}

run_preheat_with_retry() {
  local expected="$1"
  local attempt=1
  while :; do
    if [[ "$attempt" -gt 1 ]]; then
      echo "[tb21-batched] preheat_retry attempt=$attempt batch=$batch_id"
    fi
    preheat_rc=0
    python3 scripts/agentic_bench_images.py "${preheat_args[@]}" > "$preheat_json" 2> "$preheat_err" || preheat_rc=$?
    if [[ "$preheat_rc" == 0 ]] && python3 - "$preheat_json" "$expected" <<'PY_PREHEAT_CHECK'
import json, sys
p=sys.argv[1]; expected=int(sys.argv[2])
data=json.load(open(p)); counts=data.get("counts", {})
print("[tb21-batched] preheat_counts=" + json.dumps(counts, sort_keys=True))
if counts.get("present") != expected or counts.get("missing") != 0 or counts.get("errors") != 0:
    raise SystemExit(f"batch preheat not clean: {counts} expected_present={expected}")
PY_PREHEAT_CHECK
    then
      return 0
    fi
    if [[ "$attempt" -ge "${TB21_PREHEAT_MAX_ATTEMPTS:-2}" ]]; then
      echo "[tb21-batched] preheat_failed_final batch=$batch_id rc=$preheat_rc json=$preheat_json err=$preheat_err" >&2
      return 1
    fi
    echo "[tb21-batched] preheat_attempt_failed batch=$batch_id attempt=$attempt rc=$preheat_rc json=$preheat_json err=$preheat_err" >&2
    restart_rootless_for_batch "preheat_failed_${batch_id}_attempt_${attempt}"
    attempt=$((attempt + 1))
  done
}

remove_batch_images() {
  local manifest="$1"
  if [[ "${TB21_REMOVE_BATCH_IMAGES:-0}" == "1" ]]; then
    echo "[tb21-batched-privileged] refusing image deletion in privileged Pod-A runner manifest=$manifest" >&2
    return 2
  fi
  echo "[tb21-batched-privileged] remove_batch_images=skipped manifest=$manifest"
}

for i in $(seq "$TB21_BATCH_START" "$batch_end"); do
  info="$(batch_json "$i")"
  manifest="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["manifest"])' "$info")"
  image_count="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["image_count"])' "$info")"
  task_ids="$(python3 -c 'import json,sys; print(" ".join(json.loads(sys.argv[1])["task_ids"]))' "$info")"
  batch_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["batch_id"])' "$info")"
  echo "[tb21-batched] batch=$batch_id manifest=$manifest image_count=$image_count tasks=$task_ids"
  preheat_json="$run_root/tb21_full89_batched_${batch_id}_preheat_${TB21_FULL_TAG}.json"
  preheat_err="$run_root/tb21_full89_batched_${batch_id}_preheat_${TB21_FULL_TAG}.err"
  preheat_args=(check --image-manifest "$manifest" --docker-host "$DOCKER_HOST" --retag-local --json)
  preheat_args+=(--pull-attempts "${TB21_PREHEAT_PULL_ATTEMPTS:-${AGENTIC_BENCH_DOCKER_PULL_ATTEMPTS:-1}}")
  if [[ "$TB21_PREHEAT_PULL" == 1 ]]; then
    preheat_args+=(--pull)
  fi
  if [[ "$TB21_PREHEAT_FORCE_PULL" == 1 ]]; then
    preheat_args+=(--force-pull)
  fi
  if [[ "$TB21_PREHEAT_LOAD_FALLBACK" == 1 ]]; then
    preheat_args+=(--load-fallback)
  fi
  if [[ "${TB21_PREHEAT_RUN_SMOKE:-0}" == 1 ]]; then
    preheat_args+=(--run-smoke)
  fi
  if [[ "${TB21_RESTART_DOCKER_EACH_BATCH:-0}" == 1 ]]; then
    restart_rootless_for_batch "before_${batch_id}"
  else
    check_privileged_docker "before_${batch_id}"
  fi
  run_preheat_with_retry "$image_count"
  if [[ "$TB21_BATCH_RUN" == 1 ]]; then
    export TB_TASK_IDS="$task_ids"
    task_ids_csv="${task_ids// /,}"
    if [[ -n "$TB21_BASE_SKIP_TEST_COPY_TASK_IDS" && -n "$task_ids_csv" ]]; then
      export TB_SKIP_TEST_COPY_TASK_IDS="$TB21_BASE_SKIP_TEST_COPY_TASK_IDS,$task_ids_csv"
    else
      export TB_SKIP_TEST_COPY_TASK_IDS="$task_ids_csv"
    fi
    echo "[tb21-batched-privileged] skip_test_copy_task_ids=$TB_SKIP_TEST_COPY_TASK_IDS"
    export TB_DATASET_PATH="$TB21_FULL89_DATASET"
    export TB2_PREBUILT_IMAGE_MAP="$TB21_FULL89_IMAGE_MAP"
    export TB2_USE_PREBUILT_IMAGES=1
    export BENCH_OFFLINE=1
    export TB_AGENT="${TB_AGENT:-terminus-2}"
    export TB_MANIFEST_AGENT="$TB_AGENT"
    export MODEL_NAME="${MODEL_NAME:-gpt-5.4-mini}"
    export LITELLM_MODEL="${LITELLM_MODEL:-openai/gpt-5.4-mini}"
    export TB_MODEL="${TB_MODEL:-$LITELLM_MODEL}"
    export OPENAI_BASE_URL="${OPENAI_BASE_URL:-${BASE_URL:-http://100.96.1.101:18540/v1}}"
    export BASE_URL="$OPENAI_BASE_URL"
    if [[ "$TB_AGENT" != "oracle" ]]; then
      effective_api_key="${OPENAI_API_KEY:-${API_KEY:-}}"
      if [[ -z "$effective_api_key" || "$effective_api_key" == "EMPTY" ]]; then
        echo "[tb21-batched] missing API key for TB_AGENT=$TB_AGENT" >&2
        exit 2
      fi
      export OPENAI_API_KEY="$effective_api_key"
      api_preflight
    fi
    export TB_N_CONCURRENT="$(( TB21_FULL_CONCURRENCY < image_count ? TB21_FULL_CONCURRENCY : image_count ))"
    export MAX_CONCURRENCY="$TB_N_CONCURRENT"
    case " ${TB_EXTRA_ARGS:-} " in
      *" --no-rebuild "*|*" --rebuild "*) ;;
      *) export TB_EXTRA_ARGS="--no-rebuild${TB_EXTRA_ARGS:+ $TB_EXTRA_ARGS}" ;;
    esac
    export RUN_TAG="tb21_full89_batched_${batch_id}_${TB_AGENT}_c${TB_N_CONCURRENT}_${TB21_FULL_TAG}"
    export TB_JOB_NAME="$RUN_TAG"
    export BENCH_RUN_DIR="$run_root/$batch_id"
    if [[ "$TB21_RUN_CLEANUP_HELPER" == "1" ]]; then
      echo "[tb21-batched-privileged] cleanup_helper=enabled batch=$batch_id"
      scripts/cleanup_tb21_worker.sh --execute --docker-host "$DOCKER_HOST" --kill-children || true
    else
      echo "[tb21-batched-privileged] cleanup_helper=skipped batch=$batch_id"
    fi
    tb_runner_rc=0
    "${TB21_RUNNER:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh}" || tb_runner_rc=$?
    batch_strict_json="$BENCH_RUN_DIR/tb21_strict_summary.json"
    batch_strict_rc=0
    if [[ "${TB21_STRICT_CLOSURE_GATE:-1}" == "1" ]]; then
      batch_strict_args=(--run-dir "$BENCH_RUN_DIR" --output-json "$batch_strict_json")
      if [[ "${TB21_EXPECT_CLEAN:-0}" == "1" ]]; then
        batch_strict_args+=(--expect-clean)
      fi
      if [[ "${TB21_ALLOW_ORACLE_SCORE:-0}" == "1" ]]; then
        batch_strict_args+=(--allow-oracle-score)
      fi
      scripts/tb21_closure_gate.sh "${batch_strict_args[@]}" || batch_strict_rc=$?
    fi
    if [[ "$TB21_RUN_CLEANUP_HELPER" == "1" ]]; then
      echo "[tb21-batched-privileged] cleanup_helper=enabled batch=$batch_id"
      scripts/cleanup_tb21_worker.sh --execute --docker-host "$DOCKER_HOST" --kill-children || true
    else
      echo "[tb21-batched-privileged] cleanup_helper=skipped batch=$batch_id"
    fi
    if [[ "$tb_runner_rc" != "0" ]]; then
      echo "[tb21-batched] runner_failed batch=$batch_id rc=$tb_runner_rc" >&2
      exit "$tb_runner_rc"
    fi
    if [[ "$batch_strict_rc" != "0" ]]; then
      echo "[tb21-batched] strict_gate_failed batch=$batch_id rc=$batch_strict_rc summary=$batch_strict_json" >&2
      exit "$batch_strict_rc"
    fi
  fi
  remove_batch_images "$manifest"
  if [[ "$TB21_RESTART_DOCKER_AFTER_BATCH" == 1 ]]; then
    restart_rootless_for_batch "after_${batch_id}"
  fi
  df -h /tmp | tail -1
  echo "[tb21-batched] batch_done=$batch_id"
done

echo "[tb21-batched] done run_root=$run_root"
