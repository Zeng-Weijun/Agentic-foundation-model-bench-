#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib/bench_common.sh"
bench_init deepswe

DEEPSWE_ROOT="${DEEPSWE_ROOT:-$NIPS_ROOT/bench/deep-swe}"
DEEPSWE_PIER_VENV="${DEEPSWE_PIER_VENV:-/data/tmp/deepswe-pier-venv}"
DEEPSWE_UV_CACHE_DIR="${DEEPSWE_UV_CACHE_DIR:-/data/tmp/deepswe_uv_cache}"
DEEPSWE_PYTHON="${DEEPSWE_PYTHON:-/root/.local/bin/python3.12}"
DEEPSWE_PYPI_INDEX_URL="${DEEPSWE_PYPI_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIER_BIN="${PIER_BIN:-$(command -v pier || true)}"
if [[ -z "$PIER_BIN" && -x "$DEEPSWE_PIER_VENV/bin/pier" ]]; then
  PIER_BIN="$DEEPSWE_PIER_VENV/bin/pier"
fi
DEEPSWE_AGENT="${DEEPSWE_AGENT:-mini-swe-agent}"
DEEPSWE_MODEL="${DEEPSWE_MODEL:-$LITELLM_MODEL}"
DEEPSWE_MODEL_CLASS="${DEEPSWE_MODEL_CLASS:-litellm_response}"
DEEPSWE_REASONING_EFFORT="${DEEPSWE_REASONING_EFFORT:-$OPENAI_REASONING_EFFORT}"
DEEPSWE_COST_LIMIT="${DEEPSWE_COST_LIMIT:-0}"
DEEPSWE_MODE="${DEEPSWE_MODE:-smoke}"
DEEPSWE_N_TASKS="${DEEPSWE_N_TASKS:-$NUM_TASKS}"
DEEPSWE_SAMPLE_SEED="${DEEPSWE_SAMPLE_SEED:-0}"
DEEPSWE_N_CONCURRENT="${DEEPSWE_N_CONCURRENT:-$MAX_CONCURRENCY}"
DEEPSWE_N_ATTEMPTS="${DEEPSWE_N_ATTEMPTS:-$NUM_TRIALS}"
DEEPSWE_JOBS_DIR="${DEEPSWE_JOBS_DIR:-$BENCH_RUN_DIR/pier_jobs}"
DEEPSWE_JOB_NAME="${DEEPSWE_JOB_NAME:-deepswe_${MODEL_SLUG}_${RUN_TAG}}"
DEEPSWE_ENVIRONMENT="${DEEPSWE_ENVIRONMENT:-docker}"
DEEPSWE_HOST_API_RELAY="${DEEPSWE_HOST_API_RELAY:-auto}"
DEEPSWE_RELAY_LISTEN_HOST="${DEEPSWE_RELAY_LISTEN_HOST:-0.0.0.0}"
DEEPSWE_RELAY_CONTAINER_HOST="${DEEPSWE_RELAY_CONTAINER_HOST:-host.docker.internal}"
DEEPSWE_RELAY_UPSTREAM_PROXY="${DEEPSWE_RELAY_UPSTREAM_PROXY:-${HTTP_PROXY:-${http_proxy:-}}}"
DEEPSWE_SET_MSWEA_API_KEY="${DEEPSWE_SET_MSWEA_API_KEY:-0}"

mkdir -p "$BENCH_RUN_DIR" "$DEEPSWE_JOBS_DIR" "$(dirname "$DEEPSWE_ROOT")"

if [[ -z "$PIER_BIN" || ! -x "$PIER_BIN" || "${DEEPSWE_FORCE_INSTALL:-0}" == "1" ]]; then
  bench_require_exe "$(command -v uv || true)" "uv"
  bench_require_exe "$DEEPSWE_PYTHON" "Python 3.12 for Pier"
  bench_run uv --no-config venv --python "$DEEPSWE_PYTHON" "$DEEPSWE_PIER_VENV"
  mkdir -p "$DEEPSWE_UV_CACHE_DIR"
  bench_run env UV_CACHE_DIR="$DEEPSWE_UV_CACHE_DIR" uv --no-config pip install \
    --python "$DEEPSWE_PIER_VENV/bin/python" \
    --default-index "$DEEPSWE_PYPI_INDEX_URL" \
    --link-mode copy \
    datacurve-pier
  PIER_BIN="$DEEPSWE_PIER_VENV/bin/pier"
fi
bench_require_exe "$PIER_BIN" "pier"
if [[ -f "$BENCH_SCRIPT_DIR/scripts/patch_pier_egress_proxy_apt_mirror.py" ]]; then
  pier_python="$(dirname "$PIER_BIN")/python"
  if [[ -x "$pier_python" ]]; then
    "$pier_python" "$BENCH_SCRIPT_DIR/scripts/patch_pier_egress_proxy_apt_mirror.py" \
      | tee -a "$BENCH_RUN_DIR/run.env.summary"
  fi
fi

if [[ ! -d "$DEEPSWE_ROOT/.git" ]]; then
  bench_run git clone https://github.com/datacurve-ai/deep-swe "$DEEPSWE_ROOT"
else
  bench_require_path "$DEEPSWE_ROOT/tasks" "DeepSWE tasks"
fi

DEEPSWE_COMMIT="$(git -C "$DEEPSWE_ROOT" rev-parse HEAD)"
DEEPSWE_TASK_COUNT="$(find "$DEEPSWE_ROOT/tasks" -mindepth 2 -maxdepth 2 -name task.toml | wc -l | tr -d ' ')"

DEEPSWE_UPSTREAM_OPENAI_BASE_URL="${DEEPSWE_UPSTREAM_OPENAI_BASE_URL:-$OPENAI_BASE_URL}"
DEEPSWE_CONTAINER_OPENAI_BASE_URL="$OPENAI_BASE_URL"
deepswe_relay_pid=""

deepswe_cleanup() {
  if [[ -n "$deepswe_relay_pid" ]]; then
    kill "$deepswe_relay_pid" >/dev/null 2>&1 || true
    wait "$deepswe_relay_pid" >/dev/null 2>&1 || true
  fi
}
trap deepswe_cleanup EXIT

deepswe_should_relay=0
case "$DEEPSWE_HOST_API_RELAY" in
  1|true|yes) deepswe_should_relay=1 ;;
  0|false|no) deepswe_should_relay=0 ;;
  auto)
    if [[ "$DEEPSWE_ENVIRONMENT" == "docker" && "$DEEPSWE_UPSTREAM_OPENAI_BASE_URL" == http://* ]]; then
      deepswe_should_relay=1
    fi
    ;;
  *)
    echo "Invalid DEEPSWE_HOST_API_RELAY=$DEEPSWE_HOST_API_RELAY" >&2
    exit 2
    ;;
esac

if [[ "$deepswe_should_relay" == "1" ]]; then
  bench_require_exe "$(command -v python3 || true)" "python3"
  bench_require_path "$BENCH_SCRIPT_DIR/scripts/openai_http_relay.py" "OpenAI HTTP relay"
  if [[ -z "${DEEPSWE_RELAY_PORT:-}" ]]; then
    DEEPSWE_RELAY_PORT="$(
      python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("", 0))
print(sock.getsockname()[1])
sock.close()
PY
    )"
  fi
  relay_cmd=(
    "$BENCH_SCRIPT_DIR/scripts/openai_http_relay.py"
    --listen-host "$DEEPSWE_RELAY_LISTEN_HOST" \
    --listen-port "$DEEPSWE_RELAY_PORT" \
    --target-base-url "$DEEPSWE_UPSTREAM_OPENAI_BASE_URL"
  )
  if [[ -n "$DEEPSWE_RELAY_UPSTREAM_PROXY" ]]; then
    relay_cmd+=(--upstream-http-proxy "$DEEPSWE_RELAY_UPSTREAM_PROXY")
  fi
  "${relay_cmd[@]}" > "$BENCH_RUN_DIR/openai_relay.log" 2>&1 &
  deepswe_relay_pid="$!"

  relay_probe_url="http://127.0.0.1:${DEEPSWE_RELAY_PORT}/v1/models"
  for _ in {1..30}; do
    if curl -m 3 -fsS -H "Authorization: Bearer $OPENAI_API_KEY" "$relay_probe_url" \
      > "$BENCH_RUN_DIR/openai_relay_probe.json"; then
      break
    fi
    sleep 1
  done
  if [[ ! -s "$BENCH_RUN_DIR/openai_relay_probe.json" ]]; then
    echo "OpenAI relay did not pass /v1/models probe; see $BENCH_RUN_DIR/openai_relay.log" >&2
    exit 2
  fi
  DEEPSWE_CONTAINER_OPENAI_BASE_URL="$(
    python3 - "$DEEPSWE_UPSTREAM_OPENAI_BASE_URL" "$DEEPSWE_RELAY_CONTAINER_HOST" "$DEEPSWE_RELAY_PORT" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit

upstream = urlsplit(sys.argv[1])
host = sys.argv[2]
port = sys.argv[3]
path = upstream.path.rstrip("/") or ""
print(urlunsplit(("http", f"{host}:{port}", path, "", "")))
PY
  )"
fi

pier_env="$BENCH_RUN_DIR/pier.env"
umask 077
{
  printf 'OPENAI_API_KEY=%q\n' "$OPENAI_API_KEY"
  printf 'OPENAI_BASE_URL=%q\n' "$DEEPSWE_CONTAINER_OPENAI_BASE_URL"
  printf 'OPENAI_API_BASE=%q\n' "$DEEPSWE_CONTAINER_OPENAI_BASE_URL"
  if [[ "$DEEPSWE_SET_MSWEA_API_KEY" == "1" ]]; then
    printf 'MSWEA_API_KEY=%q\n' "$OPENAI_API_KEY"
  fi
  printf 'MSWEA_COST_TRACKING=%q\n' "${MSWEA_COST_TRACKING:-ignore_errors}"
  printf 'LITELLM_LOCAL_MODEL_COST_MAP=%q\n' "true"
} > "$pier_env"
chmod 600 "$pier_env"

cmd=(
  "$PIER_BIN" run
  --path "$DEEPSWE_ROOT/tasks"
  --agent "$DEEPSWE_AGENT"
  --model "$DEEPSWE_MODEL"
  --env "$DEEPSWE_ENVIRONMENT"
  --jobs-dir "$DEEPSWE_JOBS_DIR"
  --job-name "$DEEPSWE_JOB_NAME"
  --n-concurrent "$DEEPSWE_N_CONCURRENT"
  --n-attempts "$DEEPSWE_N_ATTEMPTS"
  --sample-seed "$DEEPSWE_SAMPLE_SEED"
  --env-file "$pier_env"
  --yes
)

case "$DEEPSWE_AGENT" in
  mini-swe-agent)
    cmd+=(
      --agent-kwarg "model_class=$DEEPSWE_MODEL_CLASS"
      --agent-kwarg "reasoning_effort=$DEEPSWE_REASONING_EFFORT"
      --agent-kwarg "cost_limit=$DEEPSWE_COST_LIMIT"
    )
    ;;
  codex)
    cmd+=(--agent-kwarg "reasoning_effort=$DEEPSWE_REASONING_EFFORT")
    ;;
esac

if [[ "$DEEPSWE_MODE" != "full" ]]; then
  cmd+=(--n-tasks "$DEEPSWE_N_TASKS")
fi
if [[ -n "${DEEPSWE_TASK_NAME:-}" ]]; then
  cmd+=(--include-task-name "$DEEPSWE_TASK_NAME")
fi
if [[ -n "${DEEPSWE_EXCLUDE_TASK_NAME:-}" ]]; then
  cmd+=(--exclude-task-name "$DEEPSWE_EXCLUDE_TASK_NAME")
fi
if [[ -n "${DEEPSWE_TIMEOUT_MULTIPLIER:-}" ]]; then
  cmd+=(--timeout-multiplier "$DEEPSWE_TIMEOUT_MULTIPLIER")
fi
if [[ -n "${DEEPSWE_AGENT_TIMEOUT_MULTIPLIER:-}" ]]; then
  cmd+=(--agent-timeout-multiplier "$DEEPSWE_AGENT_TIMEOUT_MULTIPLIER")
fi
if [[ -n "${DEEPSWE_VERIFIER_TIMEOUT_MULTIPLIER:-}" ]]; then
  cmd+=(--verifier-timeout-multiplier "$DEEPSWE_VERIFIER_TIMEOUT_MULTIPLIER")
fi
if [[ "${DEEPSWE_DELETE:-1}" == "0" ]]; then
  cmd+=(--no-delete)
else
  cmd+=(--delete)
fi
if [[ -n "${DEEPSWE_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $DEEPSWE_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

{
  printf 'deepswe_root=%s\n' "$DEEPSWE_ROOT"
  printf 'deepswe_commit=%s\n' "$DEEPSWE_COMMIT"
  printf 'deepswe_task_count=%s\n' "$DEEPSWE_TASK_COUNT"
  printf 'pier_bin=%s\n' "$PIER_BIN"
  printf 'deepswe_agent=%s\n' "$DEEPSWE_AGENT"
  printf 'deepswe_model=%s\n' "$DEEPSWE_MODEL"
  printf 'deepswe_model_class=%s\n' "$DEEPSWE_MODEL_CLASS"
  printf 'deepswe_mode=%s\n' "$DEEPSWE_MODE"
  printf 'deepswe_n_tasks=%s\n' "$DEEPSWE_N_TASKS"
  printf 'deepswe_n_concurrent=%s\n' "$DEEPSWE_N_CONCURRENT"
  printf 'deepswe_jobs_dir=%s\n' "$DEEPSWE_JOBS_DIR"
  printf 'deepswe_job_name=%s\n' "$DEEPSWE_JOB_NAME"
  printf 'deepswe_host_api_relay=%s\n' "$DEEPSWE_HOST_API_RELAY"
  printf 'deepswe_upstream_openai_base_url=%s\n' "$DEEPSWE_UPSTREAM_OPENAI_BASE_URL"
  printf 'deepswe_container_openai_base_url=%s\n' "$DEEPSWE_CONTAINER_OPENAI_BASE_URL"
  printf 'deepswe_relay_upstream_proxy_set=%s\n' "$([[ -n "$DEEPSWE_RELAY_UPSTREAM_PROXY" ]] && echo yes || echo no)"
  printf 'deepswe_set_mswea_api_key=%s\n' "$DEEPSWE_SET_MSWEA_API_KEY"
  if [[ -n "$deepswe_relay_pid" ]]; then
    printf 'deepswe_relay_pid=%s\n' "$deepswe_relay_pid"
    printf 'deepswe_relay_log=%s\n' "$BENCH_RUN_DIR/openai_relay.log"
  fi
} | tee -a "$BENCH_RUN_DIR/run.env.summary"

printf '%q ' "${cmd[@]/$pier_env/\$BENCH_RUN_DIR\/pier.env}" | tee "$BENCH_RUN_DIR/command.sh"
printf '\n' | tee -a "$BENCH_RUN_DIR/command.sh"

"${cmd[@]}" 2>&1 | tee "$BENCH_RUN_DIR/pier.log"

job_dir="$DEEPSWE_JOBS_DIR/$DEEPSWE_JOB_NAME"
bench_require_path "$job_dir/result.json" "Pier result.json"
ln -sfn "$job_dir" "$BENCH_RUN_DIR/pier_job"

python - "$BENCH_RUN_DIR" "$DEEPSWE_ROOT" "$job_dir" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
deep_swe_root = Path(sys.argv[2])
job_dir = Path(sys.argv[3])
result_path = job_dir / "result.json"
summary = {}
if result_path.exists():
    data = json.loads(result_path.read_text())
    stats = data.get("stats") or {}
    summary = {
        "n_total_trials": data.get("n_total_trials"),
        "n_trial_results": len(data.get("trial_results") or []),
        "stats": stats,
    }

manifest = {
    "benchmark": "deepswe",
    "dataset_root": str(deep_swe_root),
    "dataset_tasks": str(deep_swe_root / "tasks"),
    "pier_job_dir": str(job_dir),
    "pier_job_symlink": str(run_dir / "pier_job"),
    "result_json": str(result_path),
    "pier_log": str(run_dir / "pier.log"),
    "command": str(run_dir / "command.sh"),
    "env_summary": str(run_dir / "run.env.summary"),
    "summary": summary,
}
(run_dir / "artifact_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY

bench_finish "$job_dir/result.json"
