#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

NIPS_ROOT="${NIPS_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026}"
HARBOR_ROOT="${HARBOR_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor}"
TAU3_DATASET_DIR="${TAU3_DATASET_DIR:-$HARBOR_ROOT/datasets/tau3-bench}"
HARBOR_BIN="${HARBOR_BIN:-$NIPS_ROOT/bench/.official_mini_swe_agent/pier-venv/bin/harbor}"
TAU3_AGENT="${TAU3_AGENT:-oracle}"
TAU3_INCLUDE_TASK_NAME="${TAU3_INCLUDE_TASK_NAME:-tau3-airline-0}"
TAU3_EXPECTED_TASK_COUNT="${TAU3_EXPECTED_TASK_COUNT:-375}"
TAU3_N_CONCURRENT="${TAU3_N_CONCURRENT:-${MAX_CONCURRENCY:-1}}"
TAU3_N_ATTEMPTS="${TAU3_N_ATTEMPTS:-1}"
TAU3_MAX_RETRIES="${TAU3_MAX_RETRIES:-0}"
TAU3_RUN_HARBOR="${TAU3_RUN_HARBOR:-1}"
TAU3_USE_PREBUILT_IMAGES="${TAU3_USE_PREBUILT_IMAGES:-1}"
TAU3_PREBUILT_MAIN_IMAGE="${TAU3_PREBUILT_MAIN_IMAGE:-tau3-smoke-main:20260626r2}"
TAU3_PREBUILT_RUNTIME_IMAGE="${TAU3_PREBUILT_RUNTIME_IMAGE:-tau3-smoke-runtime:20260626r2}"
TAU3_PATCH_PREBUILT_DOCKER_IMAGE="${TAU3_PATCH_PREBUILT_DOCKER_IMAGE:-1}"
TAU3_NL_ASSERTIONS_MODEL="${TAU3_NL_ASSERTIONS_MODEL:-unused-no-model}"
TAU3_USER_MODEL="${TAU3_USER_MODEL:-unused-no-model}"
TAU3_USER_REASONING_EFFORT="${TAU3_USER_REASONING_EFFORT:-low}"
TAU3_DUMMY_OPENAI_API_KEY="${TAU3_DUMMY_OPENAI_API_KEY:-EMPTY}"
TAU3_DUMMY_OPENAI_BASE_URL="${TAU3_DUMMY_OPENAI_BASE_URL:-http://127.0.0.1:9/v1}"
TAU3_USE_LOCAL_COMPOSE_SHIM="${TAU3_USE_LOCAL_COMPOSE_SHIM:-1}"
TAU3_REAL_DOCKER="${TAU3_REAL_DOCKER:-/usr/bin/docker}"
TAU3_COMPOSE_SHIM_SCRIPT="${TAU3_COMPOSE_SHIM_SCRIPT:-$SCRIPT_DIR/scripts/harbor_compose_shim.py}"
LITELLM_LOCAL_MODEL_COST_MAP="${LITELLM_LOCAL_MODEL_COST_MAP:-true}"

RUN_TAG="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
BENCH_RUN_DIR="${BENCH_RUN_DIR:-$NIPS_ROOT/agentic-foundation-model-bench/runs/tau3_full_canary_$RUN_TAG}"
TAU3_JOBS_DIR="${TAU3_JOBS_DIR:-$BENCH_RUN_DIR/jobs}"

mkdir -p "$BENCH_RUN_DIR" "$TAU3_JOBS_DIR"

fail() {
  echo "[tau3-full-canary] ERROR: $*" >&2
  exit 2
}

require_path() {
  local path="$1"
  local label="$2"
  [ -e "$path" ] || fail "$label missing: $path"
}

require_image() {
  local ref="$1"
  "$TAU3_REAL_DOCKER" image inspect "$ref" >/dev/null 2>&1 || fail "required local Docker image missing: $ref"
}

if [ "$TAU3_AGENT" != "oracle" ]; then
  fail "TAU3_AGENT=$TAU3_AGENT is not allowed for no-model canary; use oracle"
fi

require_path "$HARBOR_ROOT" HARBOR_ROOT
require_path "$TAU3_DATASET_DIR" TAU3_DATASET_DIR
require_path "$HARBOR_BIN" HARBOR_BIN
[ -x "$HARBOR_BIN" ] || fail "HARBOR_BIN is not executable: $HARBOR_BIN"
HARBOR_PYTHON="${HARBOR_PYTHON:-$(dirname "$HARBOR_BIN")/python}"
[ -x "$HARBOR_PYTHON" ] || HARBOR_PYTHON=python3
require_path "$TAU3_REAL_DOCKER" TAU3_REAL_DOCKER
[ -x "$TAU3_REAL_DOCKER" ] || fail "TAU3_REAL_DOCKER is not executable: $TAU3_REAL_DOCKER"
if [ "$TAU3_USE_LOCAL_COMPOSE_SHIM" = "1" ]; then
  require_path "$TAU3_COMPOSE_SHIM_SCRIPT" TAU3_COMPOSE_SHIM_SCRIPT
fi

mapfile -t task_dirs < <(find "$TAU3_DATASET_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
task_count="${#task_dirs[@]}"
if [ "$task_count" -le 0 ]; then
  fail "no task directories under TAU3_DATASET_DIR=$TAU3_DATASET_DIR"
fi
if [ "$TAU3_EXPECTED_TASK_COUNT" != "0" ] && [ "$task_count" != "$TAU3_EXPECTED_TASK_COUNT" ]; then
  fail "expected $TAU3_EXPECTED_TASK_COUNT tau3 tasks, found $task_count in $TAU3_DATASET_DIR"
fi

if [ -n "$TAU3_INCLUDE_TASK_NAME" ]; then
  found=0
  for task_name in "${task_dirs[@]}"; do
    if [ "$task_name" = "$TAU3_INCLUDE_TASK_NAME" ]; then
      found=1
      break
    fi
  done
  [ "$found" -eq 1 ] || fail "TAU3_INCLUDE_TASK_NAME=$TAU3_INCLUDE_TASK_NAME not found in $TAU3_DATASET_DIR"
fi

if [ "$TAU3_USE_PREBUILT_IMAGES" = "1" ]; then
  require_image "$TAU3_PREBUILT_MAIN_IMAGE"
  require_image "$TAU3_PREBUILT_RUNTIME_IMAGE"
fi

printf '%s\n' "${task_dirs[@]}" > "$BENCH_RUN_DIR/tasks.list"

TAU3_HARBOR_PATH="$PATH"
TAU3_COMPOSE_SHIM_BIN_DIR=""
TAU3_COMPOSE_SHIM_STATE_DIR=""
TAU3_COMPOSE_SHIM_LOG=""
if [ "$TAU3_USE_LOCAL_COMPOSE_SHIM" = "1" ]; then
  TAU3_COMPOSE_SHIM_BIN_DIR="$BENCH_RUN_DIR/bin"
  TAU3_COMPOSE_SHIM_STATE_DIR="$BENCH_RUN_DIR/compose_shim_state"
  TAU3_COMPOSE_SHIM_LOG="$BENCH_RUN_DIR/compose_shim.log"
  mkdir -p "$TAU3_COMPOSE_SHIM_BIN_DIR" "$TAU3_COMPOSE_SHIM_STATE_DIR"
  cat > "$TAU3_COMPOSE_SHIM_BIN_DIR/docker" <<EOF
#!/usr/bin/env bash
exec "$HARBOR_PYTHON" "$TAU3_COMPOSE_SHIM_SCRIPT" "\$@"
EOF
  chmod +x "$TAU3_COMPOSE_SHIM_BIN_DIR/docker"
  TAU3_HARBOR_PATH="$TAU3_COMPOSE_SHIM_BIN_DIR:$PATH"
fi

TAU3_HARBOR_DATASET_DIR="$TAU3_DATASET_DIR"
if [ "$TAU3_USE_PREBUILT_IMAGES" = "1" ] && [ "$TAU3_PATCH_PREBUILT_DOCKER_IMAGE" = "1" ]; then
  [ -n "$TAU3_INCLUDE_TASK_NAME" ] || fail "TAU3_PATCH_PREBUILT_DOCKER_IMAGE=1 requires TAU3_INCLUDE_TASK_NAME"
  TAU3_HARBOR_DATASET_DIR="$BENCH_RUN_DIR/harbor_dataset"
  case "$TAU3_HARBOR_DATASET_DIR" in
    "$BENCH_RUN_DIR"/*) rm -rf "$TAU3_HARBOR_DATASET_DIR" ;;
    *) fail "refusing to remove non-run-dir path: $TAU3_HARBOR_DATASET_DIR" ;;
  esac
  mkdir -p "$TAU3_HARBOR_DATASET_DIR"
  cp -a "$TAU3_DATASET_DIR/$TAU3_INCLUDE_TASK_NAME" "$TAU3_HARBOR_DATASET_DIR/"
  python3 - "$TAU3_HARBOR_DATASET_DIR/$TAU3_INCLUDE_TASK_NAME/task.toml" "$TAU3_PREBUILT_MAIN_IMAGE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
image = sys.argv[2]
text = path.read_text()
marker = "[environment]\n"
if marker not in text:
    raise SystemExit(f"missing [environment] section in {path}")
start = text.index(marker) + len(marker)
next_section = text.find("\n[", start)
section = text[start:] if next_section == -1 else text[start:next_section]
line = f"docker_image = {json.dumps(image)}\n"
if "docker_image" not in section:
    text = text.replace(marker, marker + line, 1)
else:
    lines = text.splitlines()
    in_env = False
    for idx, current in enumerate(lines):
        if current == "[environment]":
            in_env = True
            continue
        if in_env and current.startswith("["):
            break
        if in_env and current.strip().startswith("docker_image"):
            lines[idx] = line.rstrip("\n")
            text = "\n".join(lines) + "\n"
            break
path.write_text(text)
PY
fi

overlay_args=()
overlay_path=""
if [ "$TAU3_USE_PREBUILT_IMAGES" = "1" ]; then
  overlay_path="$BENCH_RUN_DIR/tau3_prebuilt_images.compose.yaml"
  cat > "$overlay_path" <<EOF
services:
  main:
    image: $TAU3_PREBUILT_MAIN_IMAGE
    pull_policy: never
    build: null
    environment:
      LITELLM_LOCAL_MODEL_COST_MAP: "$LITELLM_LOCAL_MODEL_COST_MAP"
  tau3-runtime:
    image: $TAU3_PREBUILT_RUNTIME_IMAGE
    pull_policy: never
    build: null
    environment:
      LITELLM_LOCAL_MODEL_COST_MAP: "$LITELLM_LOCAL_MODEL_COST_MAP"
EOF
  overlay_args=(--extra-docker-compose "$overlay_path")
fi

cat > "$BENCH_RUN_DIR/run.env.summary" <<EOF
schema_version=tau3_full_canary.v1
run_dir=$BENCH_RUN_DIR
harbor_root=$HARBOR_ROOT
harbor_bin=$HARBOR_BIN
dataset_dir=$TAU3_DATASET_DIR
harbor_dataset_dir=$TAU3_HARBOR_DATASET_DIR
dataset_task_count=$task_count
expected_task_count=$TAU3_EXPECTED_TASK_COUNT
include_task_name=$TAU3_INCLUDE_TASK_NAME
agent=$TAU3_AGENT
n_concurrent=$TAU3_N_CONCURRENT
n_attempts=$TAU3_N_ATTEMPTS
max_retries=$TAU3_MAX_RETRIES
no_model=true
tau2_nl_assertions_model=$TAU3_NL_ASSERTIONS_MODEL
tau2_user_model=$TAU3_USER_MODEL
tau2_user_reasoning_effort=$TAU3_USER_REASONING_EFFORT
dummy_openai_base_url=$TAU3_DUMMY_OPENAI_BASE_URL
litellm_local_model_cost_map=$LITELLM_LOCAL_MODEL_COST_MAP
use_local_compose_shim=$TAU3_USE_LOCAL_COMPOSE_SHIM
real_docker=$TAU3_REAL_DOCKER
compose_shim_script=$TAU3_COMPOSE_SHIM_SCRIPT
compose_shim_bin_dir=$TAU3_COMPOSE_SHIM_BIN_DIR
compose_shim_state_dir=$TAU3_COMPOSE_SHIM_STATE_DIR
compose_shim_log=$TAU3_COMPOSE_SHIM_LOG
use_prebuilt_images=$TAU3_USE_PREBUILT_IMAGES
patch_prebuilt_docker_image=$TAU3_PATCH_PREBUILT_DOCKER_IMAGE
prebuilt_main_image=$TAU3_PREBUILT_MAIN_IMAGE
prebuilt_runtime_image=$TAU3_PREBUILT_RUNTIME_IMAGE
overlay_path=$overlay_path
EOF

harbor_cmd=(
  "$HARBOR_BIN" run
  -p "$TAU3_HARBOR_DATASET_DIR"
  -o "$TAU3_JOBS_DIR"
  -a oracle
  -k "$TAU3_N_ATTEMPTS"
  -n "$TAU3_N_CONCURRENT"
  -r "$TAU3_MAX_RETRIES"
  --no-force-build
  --yes
)

if [ -n "$TAU3_INCLUDE_TASK_NAME" ]; then
  harbor_cmd+=(--include-task-name "$TAU3_INCLUDE_TASK_NAME")
fi
if [ "${#overlay_args[@]}" -gt 0 ]; then
  harbor_cmd+=("${overlay_args[@]}")
fi

{
  printf 'cd %q && ' "$HARBOR_ROOT"
  printf 'env -u API_KEY -u ANTHROPIC_API_KEY '
  printf -- '-u SGLANG_OPENAI_API_KEY -u PACKYAPI_KEY -u PACKY_API_KEY -u LITELLM_MODEL -u MODEL_NAME -u OPENAI_MODEL '
  printf 'PATH=%q HARBOR_COMPOSE_SHIM_REAL_DOCKER=%q HARBOR_COMPOSE_SHIM_STATE_DIR=%q HARBOR_COMPOSE_SHIM_LOG=%q ' \
    "$TAU3_HARBOR_PATH" "$TAU3_REAL_DOCKER" "$TAU3_COMPOSE_SHIM_STATE_DIR" "$TAU3_COMPOSE_SHIM_LOG"
  printf 'OPENAI_API_KEY=%q OPENAI_BASE_URL=%q BASE_URL=%q LITELLM_LOCAL_MODEL_COST_MAP=%q ' \
    "$TAU3_DUMMY_OPENAI_API_KEY" "$TAU3_DUMMY_OPENAI_BASE_URL" "$TAU3_DUMMY_OPENAI_BASE_URL" "$LITELLM_LOCAL_MODEL_COST_MAP"
  printf 'TAU2_NL_ASSERTIONS_MODEL=%q TAU2_USER_MODEL=%q TAU2_USER_REASONING_EFFORT=%q ' \
    "$TAU3_NL_ASSERTIONS_MODEL" "$TAU3_USER_MODEL" "$TAU3_USER_REASONING_EFFORT"
  printf '%q ' "${harbor_cmd[@]}"
  printf '\n'
} > "$BENCH_RUN_DIR/command.sh"
chmod +x "$BENCH_RUN_DIR/command.sh"

if [ "${DRY_RUN:-0}" = "1" ] || [ "$TAU3_RUN_HARBOR" = "0" ]; then
  echo "[tau3-full-canary] dry run only"
  echo "[tau3-full-canary] task_count=$task_count include_task=$TAU3_INCLUDE_TASK_NAME"
  echo "[tau3-full-canary] command_file=$BENCH_RUN_DIR/command.sh"
  exit 0
fi

set +e
(
  cd "$HARBOR_ROOT" && \
  env \
    -u API_KEY \
    -u ANTHROPIC_API_KEY \
    -u SGLANG_OPENAI_API_KEY \
    -u PACKYAPI_KEY \
    -u PACKY_API_KEY \
    -u LITELLM_MODEL \
    -u MODEL_NAME \
    -u OPENAI_MODEL \
    PATH="$TAU3_HARBOR_PATH" \
    HARBOR_COMPOSE_SHIM_REAL_DOCKER="$TAU3_REAL_DOCKER" \
    HARBOR_COMPOSE_SHIM_STATE_DIR="$TAU3_COMPOSE_SHIM_STATE_DIR" \
    HARBOR_COMPOSE_SHIM_LOG="$TAU3_COMPOSE_SHIM_LOG" \
    OPENAI_API_KEY="$TAU3_DUMMY_OPENAI_API_KEY" \
    OPENAI_BASE_URL="$TAU3_DUMMY_OPENAI_BASE_URL" \
    BASE_URL="$TAU3_DUMMY_OPENAI_BASE_URL" \
    LITELLM_LOCAL_MODEL_COST_MAP="$LITELLM_LOCAL_MODEL_COST_MAP" \
    TAU2_NL_ASSERTIONS_MODEL="$TAU3_NL_ASSERTIONS_MODEL" \
    TAU2_USER_MODEL="$TAU3_USER_MODEL" \
    TAU2_USER_REASONING_EFFORT="$TAU3_USER_REASONING_EFFORT" \
    "${harbor_cmd[@]}"
) 2>&1 | tee "$BENCH_RUN_DIR/tau3_harbor.log"
harbor_rc="${PIPESTATUS[0]}"
set -e

python3 - "$BENCH_RUN_DIR" "$TAU3_JOBS_DIR" "$harbor_rc" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
jobs_dir = Path(sys.argv[2])
harbor_rc = int(sys.argv[3])
result_paths = sorted(jobs_dir.rglob('verifier/result.json'))
if not result_paths:
    result_paths = sorted(jobs_dir.rglob('result.json'))

results = []
for path in result_paths:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        results.append({'path': str(path), 'status': 'parse_error', 'error': str(exc)})
        continue
    if path.name == 'result.json' and data.get('status') is None and data.get('reward') is None:
        continue
    results.append({
        'path': str(path),
        'status': data.get('status'),
        'reward': data.get('reward'),
        'used_tau2_evaluator': data.get('used_tau2_evaluator'),
    })

passed = sum(1 for item in results if item.get('status') == 'passed')
summary = {
    'schema_version': 'tau3_full_canary.result.v1',
    'harbor_exit_code': harbor_rc,
    'result_count': len(results),
    'passed_count': passed,
    'failed_count': len(results) - passed,
    'passed': harbor_rc == 0 and bool(results) and passed == len(results),
    'results': results,
}
(run_dir / 'tau3_result_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if summary['passed'] else 2)
PY
