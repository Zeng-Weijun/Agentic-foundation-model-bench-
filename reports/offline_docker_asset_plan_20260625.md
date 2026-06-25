# Offline Docker Asset Plan

Date: 2026-06-25

Scope: lightweight read-only inventory for offline Docker/data asset planning. I did not pull images, install packages, run benchmarks, or make model/API calls. The only live checks were SSH reachability, rootless Docker image listing on `worker-j9jjd`, and bounded shared-storage probes for image/cache/tar paths.

## Targets Checked

- Controller host: `dev`
- Worker host: `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`
- Worker hostname: `zwj2-64rlk-3469265-worker-0`
- Rootless Docker endpoint: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`
- Shared root: `/mnt/shared-storage-user/mineru2-shared/zengweijun`
- New shared image root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images`

`dev` is reachable, but `dev -> worker-j9jjd` still fails with `Permission denied (publickey)`. Because the final topology requires `dev` as controller, that SSH path must be fixed before real offline dispatch. The Docker cache inventory below was collected by direct local Mac SSH to the worker, read-only, because the worker already permits that path.

## Worker Rootless Docker Cache

Rootless Docker is up on the worker:

```text
SecurityOptions: ["name=seccomp,profile=builtin","name=rootless"]
DockerRootDir: /tmp/rl/data
NCPU: 60
MemTotal: 419430400000
```

Current cache:

```text
Images: 237
Image tags: 371
Approx image size: 133.1GB
Containers: 0
Local volumes: 0
Build cache: 0
```

Grouped by benchmark keyword:

| Benchmark group | Worker rootless cache | Conclusion |
|---|---:|---|
| SWE-bench / SWErex | 371 tags total: 134 `swebench/*`, 237 `swerex-prebuilt:*` | Substantial partial cache exists. Full 500-task Verified coverage is not proven. |
| Terminal-Bench | 0 matching tags | Worker must load prebuilt `tb2-offline/*:20260425` images before offline runs. |
| OpenHands | 0 matching runtime tags | SWE-bench base images are partly present, but OpenHands 0.54 runtime images are missing. |
| RepoZero / RepoArena | 0 matching tags | `ghcr.io/jessezzzzz/repoarena-new:latest` must be staged and loaded. |
| tau / vita / cocoa | 0 matching tags | No Docker image requirement was found in the bounded runner/config check; Python env/data assets still need staging. |
| DeepSWE | 0 matching DeepSWE/R2E tags | Exact R2E-Gym Docker image manifest and tar source are missing. |

Representative present SWE images:

```text
swebench/sweb.eval.x86_64.django_1776_django-13810:latest
swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest
swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-astropy-1776-astropy-12907-latest-896d8eb0c3be14d2
```

## Shared Storage Image/Tar Assets

Bounded checks from `dev` found these image-related assets. No full-tree `du` was run.

| Path | Finding |
|---|---|
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images` | Exists, currently no image tar files. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/image_migration` | Contains migration scripts, logs, and manifests directories, but no image tar files in the bounded check. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/qwen-code/runs/manual_transfer_astropy_7671_20260613_220547/astropy_7671.image.tar` | One historical SWE-bench image tar, not a complete source set. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.0/offline/first4/images/tb2_offline_first4_20260425.tar` | One Terminal-Bench 2.0 first-four image bundle tar plus sha256. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl` | Present. Maps task archives to `tb2-offline/<task>:20260425` image tags. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/*.tar` | 51 Terminal-Bench 2.1 tar archives found. |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen/OpenHands-0.54.0.tar.gz` | OpenHands source archive exists, but this is not a Docker runtime image tar. |
| `repozero`, `tau2-bench`, `vitabench`, `cocoabench`, `deepswe` benchmark dirs | No image tar files found in bounded checks. |

## Per-Benchmark Gap Plan

### SWE-bench / SWErex

The worker has the only substantial Docker cache discovered in this pass: 134 `swebench/*` tags and 237 `swerex-prebuilt:*` tags. This is enough for known cached-image smoke tasks, but not enough to claim full SWE-bench Verified readiness.

Required next asset work:

1. Freeze the exact SWE-bench task subset for qwen-code, mini-swe-agent, swe-agent, and OpenHands.
2. Generate a task-to-image manifest for every selected instance.
3. Compare that manifest against the 134 observed `swebench/*` tags.
4. Save missing images on an internet-enabled or already-warm staging host, place tars under the shared image root with sha256 files, then load with rootless Docker on the worker.
5. Do not depend on public pulls from the worker.

### Terminal-Bench

Terminal-Bench has the best shared preload source, but none of it is loaded into the worker rootless store yet.

Required next asset work:

1. Decide which Terminal-Bench version and task slice are in scope: 2.0 first-four, 2.1 prebuilt subset, or both.
2. For 2.1, use `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl` as the source manifest.
3. Load the needed archives with rootless Docker on the worker.
4. After loading, verify tags like `tb2-offline/<task>:20260425` exist in `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
5. Only then run a no-model compose/task-generation smoke.

### OpenHands

OpenHands needs both SWE-bench base images and OpenHands runtime images. The config identifies the smoke runtime target:

```text
ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98
```

The worker has zero OpenHands runtime tags. The shared path has OpenHands source archives, not runtime image tars.

Required next asset work:

1. Prebuild the smoke runtime image and any selected full-run per-instance runtime images on a staging host or approved internal builder.
2. Save them to shared image tars with sha256 metadata.
3. Load them into the worker rootless Docker store.
4. Confirm OpenHands config mutation is per-run isolated before parallel execution.
5. Avoid runtime Docker builds on the offline worker unless every build dependency is pre-staged and rootless-compatible.

### RepoZero / RepoArena

The runner defaults to:

```text
ghcr.io/jessezzzzz/repoarena-new:latest
```

The worker has no matching image, and no shared tar was found.

Required next asset work:

1. Save `ghcr.io/jessezzzzz/repoarena-new:latest` from an internet-enabled staging host or approved internal registry.
2. Store the tar plus sha256 under `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/`.
3. Load it into rootless Docker on the worker.
4. Verify the runner does not attempt a pull when `BENCH_OFFLINE=1`.

### tau / vita / cocoa

The bounded runner/config check did not find a required Docker image for tau2, VitaBench, or CoCoA. That does not make these benchmarks offline-ready; it only means the immediate blocker is probably Python environment, dataset, and harness assets rather than Docker images.

Required next asset work:

1. Create an offline wheelhouse/env manifest for the tau2, VitaBench, and CoCoA runner environments.
2. Record dataset and encrypted-task asset paths.
3. Add Docker image rows later if a future adapter introduces containerized tasks.

### DeepSWE

DeepSWE uses an R2E-Gym Docker backend and expects pre-cached gym images. The current worker has no DeepSWE/R2E-specific tags beyond generic SWE-bench/SWErex cache, and no DeepSWE image tar source was found.

Required next asset work:

1. Enumerate exact R2E-Gym/SWE-Bench-Verified Docker image tags from the DeepSWE dataset or R2E-Gym cache metadata.
2. Compare those tags against the worker rootless Docker store.
3. Save missing images to shared tars and load them into the worker.
4. After image preload, run a no-model container networking smoke for the DeepSWE dependency on `host.docker.internal` or replace it with an explicit internal model endpoint route.

## End-to-End Offline Gate

Before any benchmark run on `worker-j9jjd`, require all of the following:

1. `dev -> worker-j9jjd` SSH works in batch mode, or the controller design explicitly records a different approved dispatch path.
2. `manifests/offline_images.example.yaml` is converted from example inventory to a run-specific manifest with exact task/image rows.
3. Every required image has one of:
   - already present in rootless Docker;
   - tar plus sha256 on shared storage;
   - approved internal registry/cache reachable without public internet.
4. The worker rootless store is loaded and verified with `docker image ls` under `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
5. The worker does not perform public image pulls, package installs, git fetches, dataset downloads, or model calls during preflight.
6. A no-model Docker/compose smoke passes per benchmark family before any model-backed run.

The current state is therefore: SWE-bench/SWErex is partially warm on the worker; Terminal-Bench has shared tar assets but is not loaded on the worker; OpenHands, RepoZero, and DeepSWE still need image tar/preload work; tau/vita/cocoa need offline Python/data asset manifests rather than Docker preload rows based on this bounded check.
