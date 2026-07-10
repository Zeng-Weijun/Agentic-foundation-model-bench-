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
  DOCKER_HOST, OPENAI_BASE_URL, BASE_URL, OPENAI_API_KEY, TB_BIN, TB_ROOT,
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

dry_run=1
load_image=0
task_id="${TB_TASK_IDS:-fix-git}"
run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"

shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
bench_root="${BENCH_ROOT:-$shared_root/swe/bench}"
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

docker_host="${DOCKER_HOST:-unix:///tmp/rl/run/docker.sock}"
dev_proxy_base_url="${OPENAI_BASE_URL:-${BASE_URL:-http://100.96.1.101:18540/v1}}"
model_name="${MODEL_NAME:-gpt-5.4-mini}"
litellm_model="${LITELLM_MODEL:-openai/gpt-5.4-mini}"
legacy_profile="${BENCH_MODEL_PROFILE:-gpt54mini_8130}"
profile_id="${BENCH_PROFILE_ID:-dev_proxy_gpt54mini_8130}"

runner="${TB21_RUNNER:-$bench_root/shared/runners/run_terminal_bench_2_1.sh}"
tb_root="${TB_ROOT:-$nips_root/shared_bench/terminal-bench}"
tb_bin="${TB_BIN:-$tb_root/.venv/bin/tb}"
tb_source_path="${TB_2_1_SOURCE_PATH:-$nips_root/shared_bench/terminal-bench-2.1/tasks}"
tb_dataset_path="${TB_DATASET_PATH:-$nips_root/shared_bench/terminal-bench-2.1-yaml}"
task_yaml="$tb_dataset_path/$task_id/task.yaml"
image_dir="${TB21_IMAGE_DIR:-$bench_root/terminalbench2.1/prebuilt-images/20260425}"
image_archive="${TB21_IMAGE_ARCHIVE:-$image_dir/$task_id.tar}"
image_tag="${TB21_IMAGE_TAG:-tb2-offline/$task_id:20260425}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/${task_id}_${run_tag}}"

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
echo "runner=$runner"
echo "tb_bin=$tb_bin"
echo "run_dir=$bench_run_dir"
echo "docker_host=$docker_host"
echo "profile=$profile_id legacy_bench_model_profile=$legacy_profile"
echo

if [[ "$dry_run" == 1 ]]; then
  echo "Preflight observations:"
  for path in "$runner" "$tb_bin" "$task_yaml" "$image_archive"; do
    if have_path "$path"; then
      echo "  ok: $path"
    else
      echo "  missing: $path"
    fi
  done
  if command -v docker >/dev/null 2>&1; then
    if DOCKER_HOST="$docker_host" docker image inspect "$image_tag" >/dev/null 2>&1; then
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
  command -v docker >/dev/null 2>&1 || die "docker CLI not found"

  docker_security="$(DOCKER_HOST="$docker_host" docker info --format '{{json .SecurityOptions}}' 2>/dev/null || true)"
  [[ "$docker_security" == *rootless* ]] || die "Docker at $docker_host is not reporting rootless security options"

  if ! "$tb_bin" run --help >/dev/null 2>&1; then
    die "tb CLI failed. On worker-j9jjd the current shared venv has a broken Python 3.13 interpreter path; repair or override TB_BIN."
  fi

  if ! DOCKER_HOST="$docker_host" docker image inspect "$image_tag" >/dev/null 2>&1; then
    if [[ "$load_image" == 1 ]]; then
      DOCKER_HOST="$docker_host" docker load -i "$image_archive"
    else
      die "missing Docker image tag $image_tag. Load it first with: DOCKER_HOST=$docker_host docker load -i $image_archive"
    fi
  fi

  DOCKER_HOST="$docker_host" docker image inspect "$image_tag" >/dev/null 2>&1 \
    || die "Docker image tag still missing after load attempt: $image_tag"

  mkdir -p "$bench_run_dir"
  {
    echo "task_id=$task_id"
    echo "image_tag=$image_tag"
    echo "image_archive=$image_archive"
    echo "runner=$runner"
    echo "tb_bin=$tb_bin"
    echo "docker_host=$docker_host"
    echo "openai_base_url=$dev_proxy_base_url"
    echo "bench_model_profile=$legacy_profile"
    echo "profile_id=$profile_id"
    echo "created_at=$(date -Is)"
  } > "$bench_run_dir/smoke_wrapper.env"
fi

print_export BENCH_OFFLINE "1"
print_export DOCKER_HOST "$docker_host"
print_export BENCH_PROFILE_ID "$profile_id"
print_export BENCH_MODEL_PROFILE "$legacy_profile"
print_export MODEL_NAME "$model_name"
print_export LITELLM_MODEL "$litellm_model"
print_export OPENAI_BASE_URL "$dev_proxy_base_url"
print_export BASE_URL "$dev_proxy_base_url"
print_export NO_PROXY "$no_proxy_value"
print_export no_proxy "$no_proxy_value"
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
export BENCH_PROFILE_ID="$profile_id"
export BENCH_MODEL_PROFILE="$legacy_profile"
export MODEL_NAME="$model_name"
export LITELLM_MODEL="$litellm_model"
export OPENAI_BASE_URL="$dev_proxy_base_url"
export BASE_URL="$dev_proxy_base_url"
export NO_PROXY="$no_proxy_value"
export no_proxy="$no_proxy_value"
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

"$runner"
