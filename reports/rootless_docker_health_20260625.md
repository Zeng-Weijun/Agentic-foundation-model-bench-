# Rootless Docker Health - worker-j9jjd - 2026-06-25

## Scope

Lane 1 diagnosis for the rootless Docker daemon/socket on `worker-j9jjd`.

Restrictions followed:
- Used the exact worker endpoint from `WORKFLOW.md`, not `swe_dev` / `swe-dev`.
- Did not run model benchmarks.
- Did not pull images, install packages, delete Docker data/images, or run public-internet actions on the worker.
- Wrote only this report and `scripts/check_rootless_docker_worker.sh`.

Worker:

```text
ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
hostname: zwj2-64rlk-3469265-worker-0
DOCKER_HOST: unix:///tmp/rl/run/docker.sock
```

Note: the local SSH alias `worker` resolved to a stale closed pod
`worker-pshjt` and failed with public-key denial, so all real checks below used
the explicit `worker-j9jjd` endpoint.

## Executive Summary

The original CoCoA EOF is a Docker daemon `/version` endpoint failure, not a
missing image, socket permission issue, or broad daemon outage.

`docker info`, `_ping`, `/info`, `docker ps`, image listing, `docker compose ps`,
and a cached-image `docker run --rm --network none ... echo` can work. However
`docker version`, raw `GET /v1.45/version`, and Python Docker SDK version
negotiation fail with EOF/empty reply. The daemon log shows the corresponding
server-side panic:

```text
http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
github.com/docker/docker/daemon.(*Daemon).SystemVersion(...)
github.com/docker/docker/api/server/router/system.(*systemRouter).getVersion(...)
```

This matches an upstream Moby rootless `/version` panic class: Moby issue
`#47085` reports `docker version` EOF while `docker run` continues to work, and
Moby PR `#47086` is titled `(*Daemon).fillRootlessVersion: fix nil panic`.

Current state after the safe restart:
- rootless daemon is running again;
- socket exists;
- rootless image store is intact with 238 unique image IDs;
- no active containers;
- no active benchmark processes found;
- `docker info` works;
- `docker version` still fails with EOF and remains the blocker for CoCoA/Python
  Docker SDK paths that negotiate the API version.

## Timeline And Root Cause

### Pre-restart live state

Initial exact-worker probe:

```text
HOST=zwj2-64rlk-3469265-worker-0
DATE=2026-06-25T21:39:33+08:00
DOCKER_HOST=
/bin/docker
Docker version 26.1.3, build 26.1.3-0ubuntu1~22.04.1
Docker Compose version v2.27.0
ls: cannot access '/tmp/rl/run/docker.sock': No such file or directory
```

No `dockerd`, `rootlesskit`, `containerd`, `containerd-shim`, or `runc` process
was active. No active benchmark process was found.

With `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`:

```text
docker info rc=1
docker version rc=1
docker ps rc=1
docker images rc=1
```

The Docker data directory still existed at `/tmp/rl/data`; only the daemon/socket
was absent.

### Log evidence

Prior successful daemon startup used:

```text
dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
```

The daemon repeatedly panicked on the version route before shutdown:

```text
2026/06/25 21:28:25 http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
github.com/docker/docker/daemon.(*Daemon).SystemVersion(...)
github.com/docker/docker/api/server/router/system.(*systemRouter).getVersion(...)
```

The daemon was then stopped gracefully:

```text
time="2026-06-25T21:34:40.182005689+08:00" level=info msg="Processing signal 'terminated'"
time="2026-06-25T21:34:40.187189593+08:00" level=info msg="Daemon shutdown complete"
```

An immediate restart attempt failed because `XDG_RUNTIME_DIR` was not set:

```text
time="2026-06-25T21:34:41+08:00" level=warning msg="[rootlesskit:parent] Running RootlessKit as the root user is unsupported."
could not get XDG_RUNTIME_DIR
[rootlesskit:child ] error: command [dockerd ...] exited: exit status 1
```

### Safe restart performed

Before restart:
- engine process check: empty;
- benchmark process check: empty;
- daemon socket absent;
- no active containers could be present because no daemon/shim/runc process was
  alive.

First restart attempt with `slirp4netns` was non-destructive but failed before
dockerd started:

```text
START_PID=278183
ls: cannot access '/tmp/rl/run/docker.sock': No such file or directory
rootlesskit ... --net=slirp4netns ...
open: No such file or directory
failed to setup network ... ip tuntap add name tap0 mode tap ... exit status 1
```

Evidence for non-host network limitation:

```text
/dev/net/tun: No such file or directory
pasta: executable file not found in $PATH
vpnkit probe: killed after hanging under timeout
rootlesskit --net=host --port-driver=builtin: port driver requires non-host network
```

Second restart attempt used host networking, matching the daemon's
`--bridge=none`/offline usage:

```text
PRE_START_HOSTNET_DATE=2026-06-25T21:43:22+08:00
STARTING_ROOTLESS_DOCKER_NET_HOST
START_PID=278324
SOCKET_READY_AFTER=2s
srw-rw---T 1 root 100112 0 Jun 25 21:43 /tmp/rl/run/docker.sock
```

Runtime command now active:

```text
rootlesskit --state-dir=/tmp/rl/run/dockerd-rootless --net=host --copy-up=/etc --copy-up=/run --propagation=rslave dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
containerd --config /tmp/rl/exec/containerd/containerd.toml
```

## Current Health Snapshot

Snapshot time:

```text
SNAPSHOT_DATE=2026-06-25T21:48:10+08:00
HOST=zwj2-64rlk-3469265-worker-0
```

Socket:

```text
srw-rw---T 1 root 100112 0 Jun 25 21:43 /tmp/rl/run/docker.sock
socket_mode=srw-rw---T socket_uid=0 socket_gid=100112 socket_type=socket
```

RootlessKit API:

```json
{"apiVersion":"1.1.1","version":"2.0.2","stateDir":"/tmp/rl/run/dockerd-rootless","childPID":278332}
```

Docker info:

```text
server=26.1.3 containers=0 running=0 images=238 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"] cgroup=none/1
docker_info_rc=0
```

Docker version:

```text
error during connect: Get "http://%2Ftmp%2Frl%2Frun%2Fdocker.sock/v1.45/version": EOF
docker_version_rc=1
```

Raw version endpoint:

```text
curl: (52) Empty reply from server
raw_version_rc=52
```

Docker ps:

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
docker_ps_rc=0
```

Image cache:

```text
unique image IDs: 238
sample:
tb2-offline/llm-inference-batching-scheduler:20260425 ddd05f6d1dee 180MB
swebench/sweb.eval.x86_64.django_1776_django-13810:latest 79e6f88dc0f5 3.18GB
swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-django-1776-django-13810-latest-31c096b48a1ff064 79e6f88dc0f5 3.18GB
```

Compose:

```text
Docker Compose version v2.27.0
compose_version_rc=0
docker compose -p rootless_health_probe ps
compose_ps_rc=0
```

Python Docker SDK version negotiation:

```text
DockerException: Error while fetching server API version: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
python_docker_version_rc=1
```

Cached-image non-benchmark run smoke:

```text
RUN_SMOKE_DATE=2026-06-25T21:48:24+08:00
rootless-run-ok
docker_run_rc=0
docker_ps_after_run_rc=0
```

No active benchmark processes were found in the final snapshot.

## Interpretation

The daemon/socket is partially healthy:
- Docker rootless daemon is live.
- Socket permissions allow root access from the worker shell.
- Rootless metadata is visible through `/info`.
- Containers can start from cached images with `--network none`.
- Image cache survived restart.

The blocker is specifically the Docker Engine `/version` handler. `docker
version`, raw `/v1.45/version`, and Docker SDK version negotiation all hit that
handler and receive EOF because dockerd panics in `fillRootlessVersion`.

That explains the earlier CoCoA line:

```text
Get "http://.../docker.sock/v1.45/version": EOF: driver not connecting
```

The phrase `driver not connecting` is a downstream wrapper/SDK symptom. The
server-side cause is dockerd closing the HTTP connection after the
`fillRootlessVersion` panic.

## What Was Not Changed

- No Docker data under `/tmp/rl/data` was deleted.
- No images were removed.
- No benchmark was launched.
- No model/API request was made.
- No package install, image pull, or git/network action was run on the worker.

## Blockers And Recommendations

1. `docker version` remains unhealthy after restart.
   - This blocks Docker SDK and any compose/sandbox path that probes
     `/version`.
   - A restart alone does not fix it.

2. The active Docker package is:
   - Docker CLI/Engine `26.1.3-0ubuntu1~22.04.1`
   - RootlessKit `2.0.2`
   - RootlessKit is being run as root inside the pod, which logs as unsupported.

3. Non-host RootlessKit network drivers are not usable in the current pod:
   - `slirp4netns` cannot create `tap0` because `/dev/net/tun` is absent;
   - `pasta` is not installed;
   - `vpnkit` probe hung and was killed.

4. Practical next fixes require one of:
   - use a patched Docker Engine binary/package whose `fillRootlessVersion`
     does not panic;
   - run a properly supported non-root rootless Docker setup with a complete
     RootlessKit network/port driver state;
   - adjust CoCoA/sandbox orchestration to avoid Docker SDK `/version`
     negotiation, if that is feasible for the specific stack.

Until one of those is done, this worker can run simple cached-image Docker
commands, but should not be considered healthy for CoCoA or Python-Docker-SDK
benchmark sandboxes.

## Reusable Check Script

Added:

```text
scripts/check_rootless_docker_worker.sh
```

Default mode is read-only:

```bash
scripts/check_rootless_docker_worker.sh
```

Optional restart mode is guarded and non-destructive:

```bash
scripts/check_rootless_docker_worker.sh --restart-if-down
```

The restart mode only starts the daemon when `docker info` is unhealthy and no
engine processes are present. It does not remove `/tmp/rl/data`, images, or
containers.

## Command Ledger

All commands were run from:

```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
```

| Command class | Exit code | Notes |
|---|---:|---|
| `ssh worker ...` | 255 | Local alias is stale and resolves to `worker-pshjt`; no remote command ran. |
| exact `worker-j9jjd` initial health probe | 0 | Confirmed missing socket and no engine process. |
| prior report/log inspection | 0 | Read-only local/remote evidence collection. |
| first guarded restart attempt | 10 | Guard matched its own search string; no daemon started. |
| second guarded restart attempt | 10 | Guard still matched shell args; no daemon started. |
| `slirp4netns` restart attempt | 0 wrapper / daemon failed | Non-destructive; failed before socket because tap setup failed. |
| host-network rootless restart | 0 | Socket ready after 2s; daemon, containerd active. |
| final health snapshot | 0 wrapper | `docker info rc=0`, `docker version rc=1`, raw `/version rc=52`, Python SDK rc=1. |
| cached-image `docker run --rm --network none ... echo` | 0 | Printed `rootless-run-ok`; `docker ps -a` empty after run. |

## External References

- Moby issue `#47085`: rootless `docker version` EOF while other operations can
  continue.
- Moby PR `#47086`: `(*Daemon).fillRootlessVersion: fix nil panic`.
