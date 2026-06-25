# Worker j9jjd Preflight

Date: 2026-06-25

Scope: lightweight worker/rootless/container/API preflight. No benchmark task was launched, no model generation request was made, no package install, git fetch, image pull, or large data mutation was performed.

## Worker Identity

SSH target:

```text
ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
```

Observed worker:

```text
hostname: zwj2-64rlk-3469265-worker-0
fqdn: zwj2-64rlk-3469265-worker-0.zengweijun.ailab-sciversealign.svc.pjlab.local
uid/gid: 0/0
```

Dispatch status:

- local Mac -> worker SSH: ok
- `dev` -> worker SSH: blocked with `Permission denied (publickey)`

This means the final desired `dev` controller -> worker dispatcher still needs SSH credential or agent-forwarding setup. Until then, local Mac can directly dispatch to the worker, but that is not the final controller topology.

## Filesystems

Shared root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun
```

Status:

- shared root is visible on the worker;
- `/data/nips` resolves to `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026`;
- `/data/tmp` exists and is writable;
- new project root `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench` was not present during preflight.

## Rootless Docker

The default shell does not export Docker rootless variables:

```text
DOCKER_HOST: empty
XDG_RUNTIME_DIR: empty
```

The usable rootless socket is:

```text
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
```

With that socket, `docker info` reports:

```text
SecurityOptions: ["name=seccomp,profile=builtin","name=rootless"]
DockerRootDir: /tmp/rl/data
NCPU: 60
MemTotal: 419430400000
Compose: Docker Compose v2.27.0
```

Podman and standalone `docker-compose` were not present. Use the Docker CLI plus `docker compose`.

## Image Cache

Rootless Docker has a substantial SWE-bench image cache:

```text
unique images: 237
image tags: 371
swebench/* tags: 134
swerex-prebuilt:* tags: 237
approx size: 133.1GB
```

Terminal-Bench, RepoZero, OpenHands, tau/vita, and DeepSWE image coverage was not proven by this preflight. Those image requirements need a per-benchmark image manifest and preload plan.

## Container Micro-Smoke

Command class:

- cached SWE-bench image;
- `--network none`;
- bind mount under `/data/tmp/agentic-foundation-model-bench`;
- host writes a file, container reads it, container writes a file, host reads it, temp dir removed.

Result:

```text
ROOTLESS_BIND_MOUNT_SMOKE=pass
image: swebench/sweb.eval.x86_64.django_1776_django-13810:latest
```

This proves rootless container start and bind-mount read/write for a cached SWE-bench image. It does not yet prove Docker compose, host networking, `host.docker.internal`, per-benchmark images, or benchmark runners.

## Relay/API Probe

No generation request was made. Only `/v1/models` was probed.

Worker -> 8.130 relay:

```text
http://8.130.49.170/v1/models: timeout after 8 seconds
OPENAI_API_KEY: set
```

`dev` -> 8.130 relay:

```text
http://8.130.49.170/v1/models: HTTP 503
OPENAI_API_KEY: set
```

Interpretation: model-calling benchmark smoke is currently blocked. Either the 8.130 relay needs to be healthy/reachable from the selected execution path, or model traffic should be proxied through a reachable `dev`/internal endpoint, or a future SGLang endpoint should be opened and recorded in the suite YAML.

## Manifest Fields To Preserve

```json
{
  "controller_host": "dev",
  "execution_host": "zwj2-64rlk-3469265-worker-0",
  "worker_host": "ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn",
  "worker_id": "worker-j9jjd",
  "ssh_dispatch_path": "local_ok_dev_blocked_publickey",
  "uid": 0,
  "gid": 0,
  "rootless": true,
  "container_engine": "docker",
  "docker_host": "unix:///tmp/rl/run/docker.sock",
  "compose_version": "Docker Compose v2.27.0",
  "tmp_root": "/data/tmp",
  "shared_root": "/mnt/shared-storage-user/mineru2-shared/zengweijun",
  "network_policy": "offline_or_internal_only",
  "public_internet": "github_timeout",
  "relay_8130_from_worker": "timeout",
  "relay_8130_from_dev": "503",
  "rootless_bind_mount_smoke": "pass"
}
```

## Next Smoke Order

1. Fix `dev` -> worker SSH dispatch or explicitly accept local Mac -> worker dispatch for the interim.
2. Create/pull the new shared project root from `dev`.
3. Record per-benchmark required images and preload missing images into the rootless Docker store.
4. Prove `docker compose` with a no-model task.
5. Prove model endpoint reachability from the actual execution path.
6. Run one cheap model task, starting with tau/vita/repozero before SWE-bench/OpenHands/DeepSWE.
