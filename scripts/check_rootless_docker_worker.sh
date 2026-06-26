#!/usr/bin/env bash
set -euo pipefail

WORKER_SSH="${WORKER_SSH:-ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn}"
REMOTE_DOCKER_HOST="${REMOTE_DOCKER_HOST:-unix:///tmp/rl/run/docker.sock}"
REMOTE_DOCKER_API_VERSION="${REMOTE_DOCKER_API_VERSION:-1.45}"
HEALTH_SMOKE_IMAGE="${HEALTH_SMOKE_IMAGE:-}"
MODE="${1:-check}"

case "$MODE" in
  check|--check)
    MODE="check"
    ;;
  --restart-if-down)
    MODE="restart-if-down"
    ;;
  -h|--help)
    cat <<'USAGE'
Usage: scripts/check_rootless_docker_worker.sh [--check|--restart-if-down]

Checks rootless Docker health on worker-j9jjd.

Environment:
  WORKER_SSH          SSH target for the worker.
  REMOTE_DOCKER_HOST Rootless Docker socket URI.
  REMOTE_DOCKER_API_VERSION Docker API version for worker CLI calls.
  HEALTH_SMOKE_IMAGE Optional cached image ref to run with --network none.

The default mode is read-only. --restart-if-down starts the daemon only when no
engine processes are present and docker info is not healthy. It does not delete
Docker data, images, or containers.
USAGE
    exit 0
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    exit 2
    ;;
esac

ssh -o BatchMode=yes -o ConnectTimeout=12 "$WORKER_SSH" 'bash -s' -- "$MODE" "$REMOTE_DOCKER_HOST" "$REMOTE_DOCKER_API_VERSION" "$HEALTH_SMOKE_IMAGE" <<'REMOTE'
set -u

mode="$1"
docker_host="$2"
docker_api_version="$3"
health_smoke_image="${4:-}"
export DOCKER_HOST="$docker_host"
export DOCKER_API_VERSION="$docker_api_version"

engine_comm_re='^(dockerd|rootlesskit|containerd|containerd-shim|containerd-shim-runc-v2|runc|docker-proxy|slirp4netns|vpnkit)$'
bench_re='cocoa|terminal-bench|terminal_bench|repozero|vita|tau3|agentic|benchmark'

print_engine_processes() {
  ps -eo pid,ppid,stat,etime,comm,args |
    awk -v re="$engine_comm_re" 'BEGIN{IGNORECASE=1} $5 ~ re {print}'
}

engine_process_count() {
  ps -eo comm |
    awk -v re="$engine_comm_re" 'BEGIN{IGNORECASE=1; n=0} $1 ~ re {n++} END{print n}'
}

print_benchmark_processes() {
  ps -eo pid,ppid,stat,etime,comm,args |
    awk -v re="$bench_re" 'BEGIN{IGNORECASE=1} $0 ~ re && $5 !~ /awk|grep|bash/ {print}'
}

docker_info_ok() {
  timeout 20 docker info >/tmp/rl/check_rootless_docker_info.out 2>/tmp/rl/check_rootless_docker_info.err
}

start_daemon_if_safe() {
  if [ "$(engine_process_count)" != "0" ]; then
    echo "restart_refused=active_engine_process"
    return 10
  fi

  export PATH=/tmp/rl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
  export XDG_RUNTIME_DIR=/tmp/rl/run
  export HOME=/root
  export DOCKERD_ROOTLESS_ROOTLESSKIT_STATE_DIR=/tmp/rl/run/dockerd-rootless
  mkdir -p /tmp/rl/run
  chmod 700 /tmp/rl/run

  # Runtime-only RootlessKit state. Docker data/images live under /tmp/rl/data.
  rm -rf /tmp/rl/run/dockerd-rootless

  nohup /tmp/rl/bin/rootlesskit \
    --state-dir=/tmp/rl/run/dockerd-rootless \
    --net=host \
    --copy-up=/etc \
    --copy-up=/run \
    --propagation=rslave \
    dockerd \
      --config-file=/dev/null \
      --host=unix:///tmp/rl/run/docker.sock \
      --data-root=/tmp/rl/data \
      --exec-root=/tmp/rl/exec \
      --iptables=false \
      --bridge=none \
      --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh \
      --default-runtime sysbind \
      --storage-driver overlay2 \
    >>/tmp/rl/dockerd.log 2>&1 &

  echo "restart_pid=$!"
  for i in $(seq 1 60); do
    if [ -S /tmp/rl/run/docker.sock ]; then
      echo "socket_ready_after=${i}s"
      return 0
    fi
    sleep 1
  done

  echo "restart_socket_ready=false"
  return 11
}

echo "date=$(date -Is)"
echo "host=$(hostname)"
echo "mode=$mode"
echo "docker_host=$DOCKER_HOST"
echo "docker_api_version=$DOCKER_API_VERSION"
echo "health_smoke_image=${health_smoke_image:-}"

echo "--- socket ---"
ls -l /tmp/rl/run/docker.sock 2>&1 || true
stat -c 'socket_mode=%A socket_uid=%u socket_gid=%g socket_type=%F' /tmp/rl/run/docker.sock 2>&1 || true

echo "--- engine processes ---"
print_engine_processes || true

echo "--- benchmark processes ---"
print_benchmark_processes || true

if [ "$mode" = "restart-if-down" ]; then
  if docker_info_ok; then
    echo "restart_skipped=docker_info_ok"
  else
    echo "restart_reason=docker_info_failed"
    start_daemon_if_safe || true
  fi
fi

echo "--- rootlesskit api ---"
curl --silent --show-error --max-time 5 \
  --unix-socket /tmp/rl/run/dockerd-rootless/api.sock \
  http://rootlesskit/v1/info 2>&1 || true
echo

status=0

echo "--- docker info ---"
timeout 30 docker info --format 'server={{.ServerVersion}} containers={{.Containers}} running={{.ContainersRunning}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}} cgroup={{.CgroupDriver}}/{{.CgroupVersion}}' 2>&1
rc=$?
echo "docker_info_rc=$rc"
[ "$rc" -eq 0 ] || status=1

echo "--- docker version ---"
timeout 30 docker version 2>&1
rc=$?
echo "docker_version_rc=$rc"
if [ "$rc" -ne 0 ]; then
  echo "docker_version_diagnostic=known_rootless_version_endpoint_unstable"
fi

echo "--- raw version endpoint ---"
curl --silent --show-error --max-time 5 \
  --unix-socket /tmp/rl/run/docker.sock \
  http://docker/v1.45/version 2>&1
rc=$?
echo "raw_version_rc=$rc"
if [ "$rc" -ne 0 ]; then
  echo "raw_version_diagnostic=known_rootless_version_endpoint_unstable"
fi

echo "--- docker ps ---"
timeout 30 docker ps -a --no-trunc 2>&1
rc=$?
echo "docker_ps_rc=$rc"
[ "$rc" -eq 0 ] || status=1

echo "--- images ---"
timeout 60 docker images -q 2>/dev/null | sort -u | wc -l
timeout 60 docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | sed -n '1,12p'
rc=${PIPESTATUS[0]}
echo "docker_images_rc=$rc"
[ "$rc" -eq 0 ] || status=1

echo "--- docker storage ---"
df -h /tmp /tmp/rl /tmp/rl/data /mnt/shared-storage-user 2>&1 || true
df -i /tmp /tmp/rl /tmp/rl/data /mnt/shared-storage-user 2>&1 || true
timeout 30 docker info --format 'driver={{.Driver}} root={{.DockerRootDir}} containers={{.Containers}} images={{.Images}} driver_status={{json .DriverStatus}}' 2>&1
rc=$?
echo "docker_storage_info_rc=$rc"
timeout 30 docker system df 2>&1
rc=$?
echo "docker_system_df_rc=$rc"
du -sh /tmp/rl/data /tmp/rl/data/overlay2 2>&1 || true

echo "--- cached run smoke ---"
if [ -z "$health_smoke_image" ]; then
  echo "cached_run_smoke_skipped=HEALTH_SMOKE_IMAGE_unset"
else
  echo "cached_run_smoke_image=$health_smoke_image"
  if timeout 20 docker image inspect "$health_smoke_image" >/dev/null 2>&1; then
    timeout 45 docker run --rm --network none "$health_smoke_image" /bin/sh -lc 'python3 --version 2>/dev/null || python --version 2>/dev/null || echo cached-run-ok' 2>&1
    rc=$?
    echo "cached_run_smoke_rc=$rc"
    [ "$rc" -eq 0 ] || status=1
  else
    echo "cached_run_smoke_skipped=image_not_present"
  fi
fi

echo "--- compose ---"
timeout 20 docker compose version 2>&1
rc=$?
echo "compose_version_rc=$rc"
[ "$rc" -eq 0 ] || status=1
timeout 20 docker compose -p rootless_health_probe ps 2>&1
rc=$?
echo "compose_ps_rc=$rc"
[ "$rc" -eq 0 ] || status=1

echo "--- python docker sdk version ---"
if [ -d /tmp/rl/pylibs ]; then
  PYTHONPATH=/tmp/rl/pylibs timeout 20 python3 - <<'PY' 2>&1
import docker
try:
    print(docker.from_env().version())
except Exception as exc:
    print(type(exc).__name__ + ": " + str(exc))
    raise SystemExit(1)
PY
  rc=$?
else
  echo "skipped=/tmp/rl/pylibs missing"
  rc=0
fi
echo "python_docker_version_rc=$rc"
if [ "$rc" -ne 0 ]; then
  echo "python_docker_version_diagnostic=known_rootless_version_endpoint_unstable"
fi

echo "--- non-host rootless network prerequisites ---"
command -v pasta || true
ls -l /dev/net/tun 2>&1 || true

echo "--- recent panic lines ---"
tail -n 120 /tmp/rl/dockerd.log 2>/dev/null |
  grep -E 'panic serving|fillRootlessVersion|Docker daemon|API listen|Processing signal|failed to setup network|could not get XDG_RUNTIME_DIR' || true

exit "$status"
REMOTE
