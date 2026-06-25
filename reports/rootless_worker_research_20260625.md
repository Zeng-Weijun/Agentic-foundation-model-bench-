# Rootless Worker Research

Date: 2026-06-25

Research mode: read-only. No benchmark, Docker, Podman, rootless worker, or model-serving job was started.

2026-06-25 user override: operate from `dev`, not `swe_dev`. A rootless worker may be opened later as a separate SSH target and may have no public internet access. Treat `dev` as the controller/staging host and the worker as an offline execution node unless explicitly proven otherwise.

## Executive Summary

Existing `run_*.sh` scripts are benchmark adapters, not a rootless worker architecture. Future testing should run a controller on `dev` and dispatch to dedicated offline rootless worker nodes that wrap the existing runners.

Historical evidence from the earlier read-only `swe_dev` inspection:

- `swe_dev` SSH currently lands as `root` (`uid=0`).
- `XDG_RUNTIME_DIR` was empty in the inspected shell.
- Existing DeepSWE artifacts came from ordinary Docker/Pier/compose-style execution.
- Rootless Docker/Podman availability has not been established on the future worker.

Therefore the correct next step is not to launch full benchmarks. The correct next step is to define and test a rootless worker contract with controlled no-model and one-task smoke checks.

## Recommended Architecture

### Control Plane

Local Mac remains the user control plane, but long-running benchmark orchestration should enter `dev` first:

```text
local Mac
  └── tmux session
        └── ssh dev
              └── controller script
                    └── ssh/offline dispatch to rootless worker(s)
```

Rules:

- Long jobs should start inside a local `tmux` session, then SSH into `dev`.
- Do not run long jobs in a plain foreground SSH session.
- Do not perform ad-hoc resource allocation.
- Shared paths must resolve under:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun
```

### Controller Layer

The controller should be responsible for:

- creating `run_manifest.json`
- creating job queue entries
- assigning jobs to workers
- staging datasets, harnesses, images, wheelhouses, and config snapshots for offline workers
- recording status transitions
- writing `controller.log`
- never calling the Docker socket directly
- never writing API keys to command manifests
- never requiring the offline worker to perform public internet downloads, git fetches, or image pulls

The current local sync script points at:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
```

For the new project, use a cleaner root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
```

### Worker Layer

Each worker should be a non-root process on a concrete `worker_host` with a controlled rootless container endpoint:

```text
DOCKER_HOST=unix:///run/user/<uid>/docker.sock
```

or a Podman-compatible socket.

Worker-owned state:

```text
controller_host: dev
execution_host / worker_host
worker_id
uid/gid
rootless container socket
max_parallel_jobs
tmp root: <worker_tmp_root>/<worker_id>
artifact root: /mnt/.../agentic-foundation-model-bench/runs/<bench>/<run_id>
network_policy: offline_or_internal_only
```

Worker-injected environment:

```text
BENCH_RUN_DIR
RUN_TAG
TMPDIR
DOCKER_HOST
COMPOSE_PROJECT_NAME
NO_PROXY
BENCH_OFFLINE=1 when public internet is unavailable
OPENAI_BASE_URL or internal model endpoint if reachable from the worker
OPENAI_API_KEY present as env only
```

Offline worker rule: the worker must not build by downloading dependencies, pull public container images, fetch GitHub repositories, or install packages from the internet. If a task needs images or wheels, preload them from `dev` through shared storage, `docker save/load`, `podman load`, or an explicitly approved internal registry/cache.

### Runner Layer

Existing scripts remain useful as adapters:

```text
run_swebench_verified.sh
run_swebench_verified_qwen_code.sh
run_swebench_verified_mini_swe_agent.sh
run_swebench_verified_openhands.sh
run_terminal_bench.sh
run_deepswe.sh
run_repozero_py2js.sh
```

But they should be invoked only by the worker wrapper so that each run receives:

- isolated run directory
- controlled environment
- unique compose project name
- standardized manifests
- standardized logs
- rootless container socket
- cleanup policy

## Benchmark-Specific Rootless Risks

### SWE-bench Verified

Known requirements:

- SWE-agent wrapper depends on:

```text
/data/swe/SWE-agent
/data/conda_envs/swebench/bin/python
sweagent
```

- OpenHands uses Docker runtime and the wrapper rewrites `config.toml` temporarily.
- mini-swe-agent uses Docker environment class.
- Qwen native wrapper supports build workers and verifier timeouts, but its inner Docker behavior still needs inspection.

Risks:

- Rootless image store may not contain the existing SWE-bench images; offline workers cannot pull them on demand.
- Rootless bind-mount uid/gid behavior may change file ownership in working trees.
- OpenHands shared `config.toml` mutation is not worker-safe. It must be copied per run or rewritten to use a per-run config file.
- Qwen native runner must be checked for rootful Docker assumptions.

### Terminal-Bench 2.0 / 2.1

Known requirements:

- Wrapper calls `tb run`.
- 2.0 conversion creates `docker-compose.yaml`.
- Offline images may be named like:

```text
tb2-offline/<task>:20260425
```

Risks:

- Some tasks may require privileged operations, host networking, systemd, QEMU, cgroup features, or other capabilities not available under rootless containers.
- Compose project names must be unique per worker/task.
- Prebuilt rootful images are not automatically visible to rootless engine stores.
- Per-task rootless compatibility tags are needed before running larger subsets.

### DeepSWE

Known requirements:

- Pier environment defaults to Docker.
- Script starts a host API relay and exposes it to containers through `host.docker.internal:<port>`.
- Existing historical artifacts show:

```text
deepswe_agent=mini-swe-agent
deepswe_container_openai_base_url=http://host.docker.internal:<port>/v1
```

Risks:

- `host.docker.internal` may not resolve under the chosen rootless engine.
- Egress proxy and host relay behavior must be tested in a rootless container.
- DeepSWE is expensive and long-horizon; failed historical runs included timeout, gateway, context, and max-output issues. These must be classified as infra/model/agent separately.
- Cleanup with `--delete` must not remove useful traces before artifact collection.

### RepoZero

Known requirements:

- Wrapper may pass:

```text
--docker-image ghcr.io/jessezzzzz/repoarena-new:latest
```

Risks:

- Image pull/cache under rootless engine. Offline workers need preloaded images or shared tarballs.
- Cross-language test sandbox behavior.
- Native outputs currently live under RepoZero-specific output paths, not always under `BENCH_RUN_DIR`; a manifest back-reference is required.

### MCP / tau3 / Tool Benchmarks

Known requirements:

- tau3/MCP/Toolathlon-style runs often require service state, DB snapshots, MCP server reset, and tool exposure manifests.

Risks:

- Server reset must be deterministic.
- Per-task exposed tools and distractors must be logged.
- Backend DB before/after state must be captured for tau-style grading.
- LLM judge outputs must be archived with prompt, rubric, claims, and model.
- Local runner standardization for MCP/tau3/tool benchmarks is not yet present in the inspected `bench` directory.

## Manifest Contract

### `run_manifest.json`

Required fields:

```json
{
  "schema_version": "agentic_bench.run_manifest.v1",
  "run_id": "",
  "suite_id": "",
  "bench": "",
  "mode": "",
  "controller_host": "dev",
  "remote_host": "dev",
  "execution_host": "",
  "worker_host": "",
  "worker_network": "offline_or_internal_only",
  "remote_hostname": "",
  "cwd": "",
  "script_path": "",
  "script_sha256": "",
  "git_status_or_rsync_snapshot": "",
  "created_at": "",
  "started_at": "",
  "ended_at": "",
  "exit_code": null,
  "status": "",
  "model": {
    "name": "",
    "endpoint": "",
    "api_key_set": false
  }
}
```

### `worker_manifest.json`

Required fields:

```json
{
  "schema_version": "agentic_bench.worker_manifest.v1",
  "controller_host": "dev",
  "execution_host": "",
  "worker_host": "",
  "worker_id": "",
  "uid": null,
  "gid": null,
  "rootless": null,
  "container_engine": "",
  "docker_host": "",
  "compose_version": "",
  "storage_root": "",
  "tmp_root": "",
  "network_policy": "offline_or_internal_only",
  "max_parallel_jobs": null,
  "ports_used": [],
  "no_proxy": "",
  "resource_limits": {},
  "cleanup_policy": ""
}
```

### `trace_manifest.yaml`

Extend the existing template in `reports/trace_manifest_template.yaml` with:

```yaml
worker:
  controller_host: "dev"
  execution_host: ""
  worker_host: ""
  worker_id: ""
  rootless: null
  container_engine: ""
  docker_host: ""
  tmp_root: ""
  network_policy: "offline_or_internal_only"

container:
  image: ""
  compose_files: []
  project_name: ""
  network_policy: ""
  mounts: []

verifier:
  exit_code: null
  timeout_s: null
  stdout_path: ""
  stderr_path: ""
  log_path: ""

failure:
  infra_error: null
  failure_category: ""
  retry_of: ""
```

## Required Logs

Each run should retain:

```text
controller.log
worker.log
runner.log
command.sh
run.env.summary
container_manifest.json
container_build.log
container_run.log
verifier.log
model_relay.log
openai_relay_probe.json
summary.json
artifact_manifest.json
trace_manifest.yaml
```

Rules:

- `command.sh` must be reproducible but must not contain API keys.
- `summary.json` should normalize cross-benchmark fields:
  - pass / resolved / reward / score
  - cost
  - input/output/cache tokens
  - runtime
  - timeouts
  - infra error flag
  - failure category

## Minimal Smoke Sequence

Do not start with a full benchmark. Use this order.

### Phase 0: `dev` Control-Host Read-only Preflight

Check from `dev`:

```text
hostname
id
readlink -f /data/nips
ls -ld /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026
ls -ld /data/tmp
find <project_root> -maxdepth 2 -name 'run_*.sh'
```

Goal:

- confirm `dev` host identity
- confirm shared path
- confirm tmp path
- confirm runner presence

### Phase 1: Offline Worker SSH and Rootless Engine Preflight

Only after the worker is opened and explicit permission is given to run rootless checks on that worker:

```bash
hostname
id
echo "$XDG_RUNTIME_DIR"
echo "$DOCKER_HOST"
docker context ls
docker info --format '{{json .SecurityOptions}}'
docker compose version
```

Then run a tiny bind-mount read/write/delete test in an isolated tmp directory.

Goal:

- prove rootless engine exists
- prove bind mounts work
- prove cleanup works
- prove the engine is not rootful by accident
- confirm whether shared storage is mounted on the worker
- confirm the worker has no public internet dependency for the smoke

### Phase 2: No-Model Container Smoke

Prefer prepare/verifier-only modes:

- Qwen native SWE-bench: `QWEN_NATIVE_PREPARE_ONLY=1` if supported by the target runner
- CoCoA: `COCOA_PREPARE_ONLY=1`
- Terminal-Bench: generate YAML/compose without running a long task
- repo2env diagnostic smoke if relevant

Goal:

- prove dataset/harness/container preparation without spending model tokens.

### Phase 3: API Smoke

Check only `/v1/models` and endpoint reachability from the intended execution path. Do not run task generation.

Goal:

- prove container-to-host and host-to-serving endpoint path.

### Phase 4: One-Task Smoke

Suggested order:

1. tau3 one task after Harbor dataset/image staging
2. RepoZero one tiny case
3. Terminal-Bench one task
4. SWE-bench one known instance
5. DeepSWE one task

DeepSWE should be last because it stresses Docker compose, host relay, long-horizon agent behavior, token budget, and timeout handling at the same time.

### Phase 5: Two-Worker Smoke

After a one-worker run has complete manifests:

- run two workers
- ensure compose project names do not collide
- ensure run directories do not collide
- ensure OpenHands or other shared checkout configs are not overwritten

## Open Questions

- What is the new offline worker SSH alias, user, UID/GID, and hostname?
- Does the worker have usable rootless Docker or Podman, and what is `DOCKER_HOST`?
- Is `/mnt/shared-storage-user/mineru2-shared/zengweijun` mounted on the worker?
- What worker tmp root should be used if `/data/tmp` is unavailable?
- Is the rootless image store prewarmed with SWE-bench and Terminal-Bench images, or do we need `docker save/load` / `podman load` tarballs staged from `dev`?
- Does `host.docker.internal` work from rootless containers on the worker?
- Can the offline worker reach the internal model endpoint, or must model traffic proxy through `dev`?
- Can OpenHands be forced to use a per-run config without mutating a shared checkout?
- Which Terminal-Bench 2.0/2.1 tasks require capabilities incompatible with rootless containers?
- Does the Qwen native SWE-bench runner call Docker directly, and can it honor `DOCKER_HOST`?
- Where is the current CoCoA checkout? The default inspected path was missing.
- How should infra failures be separated from model failures in DeepSWE and Terminal-Bench?
- What runner should own MCP-Atlas/tau3/tool benchmark server reset and state snapshot?
