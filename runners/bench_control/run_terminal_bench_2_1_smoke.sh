#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/run_terminal_bench_2_1_smoke.sh [--dry-run|--execute] [--load-image]

Runs, or prints, a one-task Terminal-Bench 2.1 smoke against the shared
Terminal-Bench runner. Defaults to --dry-run.

Options:
  --dry-run          Print preflight state and the exact environment/runner.
  --execute          Run the smoke. Refuses to run unless rootless Docker,
                     the tb CLI, the task YAML, and the task image are ready.
  --load-image       With --execute, load the selected image tar if the tag is
                     missing. This loads only the one selected task image.
  --task-id TASK     Terminal-Bench task id. Default: fix-git.
  --run-root DIR     Shared result root for wrapper runs.
  --run-tag TAG      Stable run tag. Default: UTC timestamp.
  -h, --help         Show this help.

Environment overrides:
  DOCKER_HOST, DOCKER_API_VERSION, TB21_REAL_DOCKER, TB21_DOCKER_SHIM_DIR,
  TB2_DOCKER_NETWORK_MODE, OPENAI_BASE_URL, BASE_URL, OPENAI_API_KEY,
  MODEL_SLUG, RUN_TAG, TB_AGENT, TB_BIN, TB_ROOT,
  TB_GLOBAL_AGENT_TIMEOUT_SEC, TB_GLOBAL_TEST_TIMEOUT_SEC, BENCH_RUN_DIR.
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 2
}

have_path() {
  [[ -e "$1" ]]
}

shell_quote() {
  printf '%q' "$1"
}

print_export() {
  local name="$1"
  local value="$2"
  printf 'export %s=' "$name"
  shell_quote "$value"
  printf '\n'
}

safe_compose_value() {
  local value="$1"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9_-]+/-/g; s/^-+//; s/-+$//')"
  printf '%s' "${value:-run}"
}

tb_cli_health_check() {
  local err_file="$1"
  [[ -x "$tb_bin" ]] || return 127
  "$tb_bin" run --help >/dev/null 2>"$err_file"
}

tb_cli_error_excerpt() {
  local err_file="$1"
  if [[ -s "$err_file" ]]; then
    sed -n '1,3p' "$err_file" | tr '
' ' ' | sed -E 's/[[:space:]]+/ /g; s/[[:space:]]+$//'
  fi
}

verify_image_archive_sha() {
  if [[ -z "$image_archive_sha256" ]]; then
    if [[ "$allow_unverified_load" == "1" ]]; then
      echo "WARNING: loading image archive without TB21_IMAGE_ARCHIVE_SHA256: $image_archive" >&2
      return 0
    fi
    die "refusing to load unverified image archive: $image_archive. Set TB21_IMAGE_ARCHIVE_SHA256 or TB21_ALLOW_UNVERIFIED_LOAD=1."
  fi

  command -v sha256sum >/dev/null 2>&1 || die "sha256sum is required to verify $image_archive"
  actual_sha256="$(sha256sum "$image_archive" | awk '{print $1}')"
  [[ "$actual_sha256" == "$image_archive_sha256" ]] \
    || die "image archive sha256 mismatch for $image_archive: expected $image_archive_sha256 got $actual_sha256"
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

dry_run=1
load_image=0
task_id="${TB_TASK_IDS:-fix-git}"
raw_run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
run_tag="$raw_run_tag"

shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
bench_root="${BENCH_ROOT:-$shared_root/swe/bench}"
fallback_bench_root="$shared_root/swe/bench"
if [[ ! -x "$bench_root/shared/runners/run_terminal_bench_2_1.sh" && -x "$fallback_bench_root/shared/runners/run_terminal_bench_2_1.sh" ]]; then
  bench_root="$fallback_bench_root"
fi
run_root="${BENCH_OUTPUT_ROOT:-$nips_root/agentic-foundation-model-bench/runs/terminal_bench_2_1_smoke}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --execute)
      dry_run=0
      shift
      ;;
    --load-image)
      load_image=1
      shift
      ;;
    --task-id)
      [[ $# -ge 2 ]] || die "--task-id requires a value"
      task_id="$2"
      shift 2
      ;;
    --run-root)
      [[ $# -ge 2 ]] || die "--run-root requires a value"
      run_root="$2"
      shift 2
      ;;
    --run-tag)
      [[ $# -ge 2 ]] || die "--run-tag requires a value"
      run_tag="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

raw_run_tag="$run_tag"
run_tag="$(safe_compose_value "$raw_run_tag")"

docker_host="${DOCKER_HOST:-unix:///tmp/rl/run/docker.sock}"
docker_api_version="${DOCKER_API_VERSION:-1.45}"
real_docker="${TB21_REAL_DOCKER:-$(command -v docker || true)}"
docker_shim_dir="${TB21_DOCKER_SHIM_DIR:-$script_dir/docker_shims}"
docker_network_mode="${TB2_DOCKER_NETWORK_MODE:-none}"
path_value="$docker_shim_dir${PATH:+:$PATH}"
dev_proxy_base_url="${OPENAI_BASE_URL:-${BASE_URL:-http://100.96.1.101:18540/v1}}"
model_name="${MODEL_NAME:-gpt-5.4-mini}"
model_slug="${MODEL_SLUG:-$(safe_compose_value "$model_name")}"
litellm_model="${LITELLM_MODEL:-openai/gpt-5.4-mini}"
tb_agent="${TB_AGENT:-terminus-2}"
tb_extra_args="${TB_EXTRA_ARGS:-}"
case " $tb_extra_args " in
  *" --rebuild "*|*" --no-rebuild "*)
    ;;
  *)
    tb_extra_args="${tb_extra_args:+$tb_extra_args }--no-rebuild"
    ;;
esac
legacy_profile="${BENCH_MODEL_PROFILE:-gpt54mini_8130}"
profile_id="${BENCH_PROFILE_ID:-dev_proxy_gpt54mini_8130}"
sitecustomize_dir="${TB21_PYTHON_SITE_DIR:-$script_dir/python_sitecustomize}"
case "${PYTHONPATH:-}" in
  "$sitecustomize_dir"|"$sitecustomize_dir":*)
    python_path_value="${PYTHONPATH:-}"
    ;;
  *)
    python_path_value="$sitecustomize_dir${PYTHONPATH:+:$PYTHONPATH}"
    ;;
esac

runner="${TB21_RUNNER:-$bench_root/shared/runners/run_terminal_bench_2_1.sh}"
tb_root="${TB_ROOT:-$nips_root/shared_bench/terminal-bench}"
tb_bin="${TB_BIN:-$tb_root/.venv/bin/tb}"
tb_source_path="${TB_2_1_SOURCE_PATH:-$nips_root/shared_bench/terminal-bench-2.1/tasks}"
tb_dataset_path="${TB_DATASET_PATH:-$nips_root/shared_bench/terminal-bench-2.1-yaml}"
task_yaml="$tb_dataset_path/$task_id/task.yaml"
image_dir="${TB21_IMAGE_DIR:-$bench_root/terminalbench2.1/prebuilt-images/20260425}"
image_archive="${TB21_IMAGE_ARCHIVE:-$image_dir/$task_id.tar}"
image_archive_sha256="${TB21_IMAGE_ARCHIVE_SHA256:-}"
allow_unverified_load="${TB21_ALLOW_UNVERIFIED_LOAD:-0}"
image_tag="${TB21_IMAGE_TAG:-tb2-offline/$task_id:20260425}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/${task_id}_${run_tag}}"
cleanup_marker="$bench_run_dir/tb2_compose_shim_cleanup_failed.log"

agent_timeout="${TB_GLOBAL_AGENT_TIMEOUT_SEC:-600}"
test_timeout="${TB_GLOBAL_TEST_TIMEOUT_SEC:-300}"
no_proxy_value="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost,100.96.1.101,100.96.0.0/12,.pjlab.org.cn}}"
case ",$no_proxy_value," in
  *,100.96.1.101,*) ;;
  *) no_proxy_value="$no_proxy_value,100.96.1.101" ;;
esac

echo "Terminal-Bench 2.1 smoke wrapper"
echo "mode=$([[ "$dry_run" == 1 ]] && echo dry-run || echo execute)"
echo "task=$task_id"
echo "image=$image_tag"
echo "image_archive=$image_archive"
echo "image_archive_sha256=${image_archive_sha256:-<unset>} allow_unverified_load=$allow_unverified_load"
echo "runner=$runner"
echo "tb_bin=$tb_bin"
echo "run_dir=$bench_run_dir"
echo "docker_host=$docker_host"
echo "docker_api_version=$docker_api_version"
echo "docker_shim_dir=$docker_shim_dir"
echo "docker_network_mode=$docker_network_mode"
echo "model_slug=$model_slug run_tag=$run_tag"
echo "tb_agent=$tb_agent"
echo "tb_extra_args=$tb_extra_args"
echo "profile=$profile_id legacy_bench_model_profile=$legacy_profile"
echo

if [[ "$dry_run" == 1 ]]; then
  echo "Preflight observations:"
  mkdir -p "$bench_run_dir"
  for path in "$runner" "$task_yaml" "$image_archive"; do
    if have_path "$path"; then
      echo "  ok: $path"
    else
      echo "  missing: $path"
    fi
  done
  tb_help_err="$bench_run_dir/tb_cli_help.err"
  if tb_cli_health_check "$tb_help_err"; then
    echo "  ok: $tb_bin"
  else
    tb_help_rc="$?"
    echo "  broken: $tb_bin (tb run --help rc=$tb_help_rc)"
    excerpt="$(tb_cli_error_excerpt "$tb_help_err")"
    if [[ -n "$excerpt" ]]; then
      echo "    $excerpt"
    fi
  fi
  if [[ -n "$real_docker" && -x "$real_docker" ]]; then
    if DOCKER_HOST="$docker_host" "$real_docker" image inspect "$image_tag" >/dev/null 2>&1; then
      echo "  ok: docker image tag is loaded"
    else
      echo "  missing: docker image tag is not loaded"
    fi
  else
    echo "  missing: docker CLI not found on this host"
  fi
  echo
  echo "Dry-run command:"
else
  [[ -x "$runner" ]] || die "missing executable shared runner: $runner"
  [[ -x "$tb_bin" ]] || die "missing executable tb CLI: $tb_bin"
  [[ -f "$task_yaml" ]] || die "missing task YAML: $task_yaml"
  [[ -f "$image_archive" ]] || die "missing image archive: $image_archive"
  [[ -n "$real_docker" && -x "$real_docker" ]] || die "docker CLI not found"

  docker_security="$(DOCKER_HOST="$docker_host" "$real_docker" info --format '{{json .SecurityOptions}}' 2>/dev/null || true)"
  [[ "$docker_security" == *rootless* ]] || die "Docker at $docker_host is not reporting rootless security options"

  mkdir -p "$bench_run_dir"
  tb_help_err="$bench_run_dir/tb_cli_help.err"
  if ! tb_cli_health_check "$tb_help_err"; then
    excerpt="$(tb_cli_error_excerpt "$tb_help_err")"
    die "tb CLI health check failed for $tb_bin${excerpt:+: $excerpt}. Repair the venv or override TB_BIN."
  fi

  if ! DOCKER_HOST="$docker_host" "$real_docker" image inspect "$image_tag" >/dev/null 2>&1; then
    if [[ "$load_image" == 1 ]]; then
      verify_image_archive_sha
      DOCKER_HOST="$docker_host" "$real_docker" load -i "$image_archive"
    else
      die "missing Docker image tag $image_tag. Load it first with: DOCKER_HOST=$docker_host docker load -i $image_archive"
    fi
  fi

  DOCKER_HOST="$docker_host" "$real_docker" image inspect "$image_tag" >/dev/null 2>&1 \
    || die "Docker image tag still missing after load attempt: $image_tag"

  rm -f "$cleanup_marker"
  {
    echo "task_id=$task_id"
    echo "image_tag=$image_tag"
    echo "image_archive=$image_archive"
    echo "image_archive_sha256=$image_archive_sha256"
    echo "allow_unverified_load=$allow_unverified_load"
    echo "runner=$runner"
    echo "tb_bin=$tb_bin"
    echo "docker_host=$docker_host"
    echo "docker_api_version=$docker_api_version"
    echo "real_docker=$real_docker"
    echo "docker_shim_dir=$docker_shim_dir"
    echo "docker_network_mode=$docker_network_mode"
    echo "model_slug=$model_slug"
    echo "run_tag=$run_tag"
    echo "openai_base_url=$dev_proxy_base_url"
    echo "tb_agent=$tb_agent"
    echo "tb_extra_args=$tb_extra_args"
    echo "bench_model_profile=$legacy_profile"
    echo "profile_id=$profile_id"
    echo "created_at=$(date -Is)"
  } > "$bench_run_dir/smoke_wrapper.env"
fi

print_export BENCH_OFFLINE "1"
print_export DOCKER_HOST "$docker_host"
print_export DOCKER_API_VERSION "$docker_api_version"
print_export DOCKER_PY_API_VERSION "$docker_api_version"
print_export TB21_REAL_DOCKER "$real_docker"
print_export TB21_DOCKER_SHIM_DIR "$docker_shim_dir"
print_export TB2_DOCKER_NETWORK_MODE "$docker_network_mode"
print_export TB21_IMAGE_ARCHIVE_SHA256 "$image_archive_sha256"
print_export TB21_ALLOW_UNVERIFIED_LOAD "$allow_unverified_load"
print_export PATH "$path_value"
print_export BENCH_PROFILE_ID "$profile_id"
print_export BENCH_MODEL_PROFILE "$legacy_profile"
print_export RUN_TAG "$run_tag"
print_export MODEL_NAME "$model_name"
print_export MODEL_SLUG "$model_slug"
print_export LITELLM_MODEL "$litellm_model"
print_export TB_AGENT "$tb_agent"
print_export TB_EXTRA_ARGS "$tb_extra_args"
print_export OPENAI_BASE_URL "$dev_proxy_base_url"
print_export BASE_URL "$dev_proxy_base_url"
print_export NO_PROXY "$no_proxy_value"
print_export no_proxy "$no_proxy_value"
print_export PYTHONPATH "$python_path_value"
print_export BENCH_ROOT "$bench_root"
print_export BENCH_OUTPUT_ROOT "$run_root"
print_export BENCH_RUN_DIR "$bench_run_dir"
print_export TB_ROOT "$tb_root"
print_export TB_BIN "$tb_bin"
print_export TB_2_1_SOURCE_PATH "$tb_source_path"
print_export TB_DATASET_PATH "$tb_dataset_path"
print_export TB2_USE_PREBUILT_IMAGES "1"
print_export TB_TASK_IDS "$task_id"
print_export NUM_TASKS "1"
print_export MAX_CONCURRENCY "1"
print_export TB_N_CONCURRENT "1"
print_export TB_GLOBAL_AGENT_TIMEOUT_SEC "$agent_timeout"
print_export TB_GLOBAL_TEST_TIMEOUT_SEC "$test_timeout"
print_export TB_GLOBAL_TIMEOUT_MULTIPLIER "1.0"
printf '%q\n' "$runner"

if [[ "$dry_run" == 1 ]]; then
  exit 0
fi

export BENCH_OFFLINE=1
export DOCKER_HOST="$docker_host"
export DOCKER_API_VERSION="$docker_api_version"
export DOCKER_PY_API_VERSION="$docker_api_version"
export TB21_REAL_DOCKER="$real_docker"
export TB21_DOCKER_SHIM_DIR="$docker_shim_dir"
export TB2_DOCKER_NETWORK_MODE="$docker_network_mode"
export TB21_IMAGE_ARCHIVE_SHA256="$image_archive_sha256"
export TB21_ALLOW_UNVERIFIED_LOAD="$allow_unverified_load"
export PATH="$path_value"
export BENCH_PROFILE_ID="$profile_id"
export BENCH_MODEL_PROFILE="$legacy_profile"
export RUN_TAG="$run_tag"
export MODEL_NAME="$model_name"
export MODEL_SLUG="$model_slug"
export LITELLM_MODEL="$litellm_model"
export TB_AGENT="$tb_agent"
export TB_EXTRA_ARGS="$tb_extra_args"
export OPENAI_BASE_URL="$dev_proxy_base_url"
export BASE_URL="$dev_proxy_base_url"
export NO_PROXY="$no_proxy_value"
export no_proxy="$no_proxy_value"
export PYTHONPATH="$python_path_value"
export BENCH_ROOT="$bench_root"
export BENCH_OUTPUT_ROOT="$run_root"
export BENCH_RUN_DIR="$bench_run_dir"
export TB_ROOT="$tb_root"
export TB_BIN="$tb_bin"
export TB_2_1_SOURCE_PATH="$tb_source_path"
export TB_DATASET_PATH="$tb_dataset_path"
export TB2_USE_PREBUILT_IMAGES=1
export TB_TASK_IDS="$task_id"
export NUM_TASKS=1
export MAX_CONCURRENCY=1
export TB_N_CONCURRENT=1
export TB_GLOBAL_AGENT_TIMEOUT_SEC="$agent_timeout"
export TB_GLOBAL_TEST_TIMEOUT_SEC="$test_timeout"
export TB_GLOBAL_TIMEOUT_MULTIPLIER=1.0

set +e
"$runner"
runner_rc="$?"
set -e

if [[ -s "$cleanup_marker" ]]; then
  echo "ERROR: TB2 docker compose shim cleanup failed; see $cleanup_marker" >&2
  sed -n '1,120p' "$cleanup_marker" >&2 || true
  exit 1
fi

exit "$runner_rc"
