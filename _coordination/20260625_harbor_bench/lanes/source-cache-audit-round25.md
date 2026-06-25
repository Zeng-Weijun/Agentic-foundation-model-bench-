# Source Cache Audit Round 25

Date: 2026-06-26
Lane: `source-cache-audit`
Host checked: `swe_dev` via direct endpoint from `WORKFLOW.md`
Remote worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`

## Scope And Guardrails

This was a read-only cache and manifest audit. I did not run Docker save, load,
pull, run, or build. I did not run benchmarks or model calls. The only write was
this report.

The target worktree already had an unrelated modified file:

```text
 M _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md
```

I did not touch that file.

## Executive Summary

`swe_dev` is the current source-of-truth cache for SWE-bench Verified and
Terminal-Bench 2.1 images. Its local Docker root is `/data/docker` and contains:

```text
DockerRootDir=/data/docker
Docker Images reported by docker info=1597
docker image refs listed=1964
tb2-offline refs=89
swebench/sweb.eval refs=500
swerex-prebuilt refs=728
ghcr.io/all-hands-ai/runtime refs=0
openhands-like refs=1: openhands_smoke4_recover:sphinx8595
```

Shared storage is no longer empty, but it is still incomplete:

```text
Terminal-Bench 2.1 shared coverage:
  old prebuilt 20260425 tars: 50 task tars
  new agentic image-root tars: 34 task tars
  combined unique task tar coverage: 84 of 89
  remaining missing shared tars: 5

SWE-bench Verified shared coverage:
  swebench eval tar under agentic image root: 1 task, django10097
  SWE-ReX chunk/shared tars: 97
  swe_dev Docker cache: 500 swebench eval refs + 728 swerex-prebuilt refs

OpenHands runtime:
  formal runtime tag ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98 absent from swe_dev Docker refs
  shared images/openhands directory absent
  only local OpenHands-like ref found: openhands_smoke4_recover:sphinx8595
```

The immediate Terminal-Bench 2.1 shared gap should be filled from the five
`swe_dev` local Docker refs below, in a future lane that is allowed to save or
push images:

```text
tb2-offline/pytorch-model-recovery:20260425
tb2-offline/qemu-alpine-ssh:20260425
tb2-offline/qemu-startup:20260425
tb2-offline/torch-pipeline-parallelism:20260425
tb2-offline/torch-tensor-parallelism:20260425
```

## Actual Source Paths Found

### `/data/swe`

Important local or symlinked sources:

```text
/data/swe/docker_prebuilt
  du: 3.2G
  actual tar: /data/swe/docker_prebuilt/astropy__astropy-12907__swerex_bundle_v2_20260425.tar
  size: 3415601152 bytes
  mtime: 2026-04-25 20:44:59 +0800
  note: sha256 was not computed in this lane; the read was interrupted after it ran too long.

/data/swe/full500_local
  du: 24M
  relevant files:
    /data/swe/full500_local/verified_full.json
    /data/swe/full500_local/gold.hsgold.json
    /data/swe/full500_local/gold.hsgold3.json
    /data/swe/full500_local/gpt-5.4-mini.full500_s{0..4}.json
    /data/swe/full500_local/preds_shard{0..5}.json
    /data/swe/full500_local/preds_smoke.json

/data/swe/tbench-runs
  du: 2.0G
  relevant files:
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/config.json
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/job.log
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/result.json
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/fix-git__SW7FHoM/result.json
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/fix-git__SW7FHoM/trial.log
    /data/swe/tbench-runs/qwen35_9b_20260509_123331/2026-05-09__12-33-32/fix-git__SW7FHoM/agent/trajectory.json
```

Symlinked `/data/swe` entries resolve to shared storage:

```text
/data/swe/SWE-bench -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/repos/SWE-bench
/data/swe/SWE-agent -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/agent_scaffolds/SWE-agent-official-main-20260529_225705
/data/swe/datasets -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/datasets
/data/swe/runs -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/runs
/data/swe/logs -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/logs
```

### `/data/tmp`

Important actual paths:

```text
/data/tmp/tb2-batch10-mteb-run
  du: 2.1G
  files:
    /data/tmp/tb2-batch10-mteb-run/mteb-retrieve.tar
    /data/tmp/tb2-batch10-mteb-run/run.log
    /data/tmp/tb2-batch10-mteb-run/push.log
  tar size: 2159561728 bytes
  tar mtime: 2026-06-26 04:58:53 +0800
  run.log source_id: sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a
  run.log tar sha: f80be41fc1360f33926c4ceaf572eff8963455f7bf44d3544454d4c6fb3eda2d
  run.log registry digest: 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-mteb-retrieve@sha256:088c20baec521e159982c27bcdb8a48dda67a15729043a92a86ef27a6472c0a8
  run.log intended shared tar: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/mteb-retrieve.tar

/data/tmp/swe-agent-runtime-swebench
  du: 304M
  relevant as repo-cache scratch; no tar/log/manifest files found in the bounded maxdepth-4 file sample.

/data/tmp/swedh_m02d_rollouts
  du: 2.5G
  relevant as SWE-bench Verified rollout scratch. It has many per-instance work/repo directories, but no direct image tar path in the bounded sample.

/data/tmp/deepswe_uv_cache
  du: 815M
  not a primary SWE-bench Verified or Terminal-Bench 2.1 image source.

/data/tmp/repo2env-nightly-trusted-check-v3
  du: 1.1M
  contains repo2env image provenance examples, not a primary SWE-bench Verified or TB2.1 source.
```

A broad `/data/tmp` scan was too noisy and was interrupted after bounded output;
this report uses the targeted paths above.

### `/data/docker`

Docker metadata and cache shape:

```text
/data/docker/image/overlay2/repositories.json
  exists, size=397297 bytes, mtime=2026-06-26 05:54:26 +0800

/data/docker/image/overlay2/imagedb/content/sha256
  exists, imagedb sha256 files=1597

/data/docker/overlay2
  exists, top-level overlay2 dirs=10422

/data/docker/buildkit
  exists, bounded depth-2 file count=8

/data/docker/containers
  exists, container dirs=54
```

No layer traversal was performed beyond bounded metadata counts.

## Docker Image Cache Counts And Representative Refs

All Docker commands in this lane were read-only: `docker info` and
`docker images --format`. No `save/load/pull/run/build` was executed.

Counts:

```text
docker info Images=1597
docker images refs=1964
tb2_offline_refs=89
swebench_sweb_eval_refs=500
swerex_prebuilt_refs=728
openhands_runtime_refs=0
openhands_any_refs=1
```

Representative `tb2-offline` refs:

```text
tb2-offline/fix-git:20260425 e76e9a24f595 339MB
tb2-offline/gcode-to-text:20260425 8fba1dce95b8 182MB
tb2-offline/mteb-retrieve:20260425 153b4c97f265 2.12GB
tb2-offline/multi-source-data-merger:20260425 a961d2504355 6.2GB
tb2-offline/pytorch-model-recovery:20260425 3a67ac23a609 19.2GB
tb2-offline/qemu-alpine-ssh:20260425 53987a31bb5e 1.96GB
tb2-offline/qemu-startup:20260425 5814c86fde20 1.96GB
tb2-offline/torch-pipeline-parallelism:20260425 a014da66007d 11.3GB
tb2-offline/torch-tensor-parallelism:20260425 7f0d9bce1454 11GB
```

Representative `swebench/sweb.eval` refs:

```text
swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest cce639c4d4c4 2.69GB
swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest 03575dfa5837 2.67GB
swebench/sweb.eval.x86_64.django_1776_django-10097:latest cf945d25ceb6 2.81GB
swebench/sweb.eval.x86_64.django_1776_django-11087:latest 7e7898eb2842 2.67GB
swebench/sweb.eval.x86_64.django_1776_django-11740:latest 7dd791f0af58 2.68GB
```

Representative `swerex-prebuilt` refs:

```text
swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-astropy-1776-astropy-12907-latest-896d8eb0c3be14d2 3bfd24c0b7c2 3.22GB
swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-astropy-1776-astropy-7671-latest-00527122c8e98259 8d93e2be662f 3.16GB
swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-django-1776-django-10097-latest-8be1c797d4885b41 3e38b9278651 3.25GB
```

OpenHands:

```text
formal runtime refs matching ghcr.io/all-hands-ai/runtime: 0
openhands-like refs: openhands_smoke4_recover:sphinx8595 3832f8d74524 5.69GB
```

## Shared Manifest And Image State

Relevant repo manifests currently exist:

```text
manifests/images/terminal_bench_2_1.yaml
manifests/images/terminal_bench_2_1_swe_dev_cache.yaml
manifests/images/swebench_verified.yaml
manifests/images/swebench_verified_django10097.yaml
manifests/bench_registry.yaml
manifests/offline_images.tb21_fix_git.yaml
```

Current shared image root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images
```

Observed shared files include:

```text
RepoZero:
  images/repozero/repoarena-new_latest.tar
  images/repozero/repoarena-new_latest.tar.sha256
  images/repozero/repoarena-new_latest.docker-inspect.json
  images/repozero/repoarena-new_latest.manifest.json

SWE-bench django10097 identity probe:
  images/swebench/django10097/swebench_django10097_eval_base.tar
  images/swebench/django10097/sha256sums.txt

Terminal-Bench 2.1 missing batches:
  images/terminalbench2.1/20260425_missing_batch1/*.tar
  images/terminalbench2.1/20260425_missing_batch1/*.tar.sha256 for many but not all rows
  images/terminalbench2.1/20260425_missing_batch2/install-windows-3.11.tar
```

Shared directories still absent:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/swebench_verified
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/openhands
```

Additional SWE-ReX shared source:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images
  shared_swerex_tar_count=97
  examples:
    /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar
    /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/astropy-1776-astropy_03.tar
    /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/sympy-1776-sympy_00.tar
```

## Shared-Incomplete Remediation Map

### Terminal-Bench 2.1

Comparison against `swe_dev` local Docker cache:

```text
swe_dev tb2 Docker tasks: 89
old shared 20260425 tar tasks: 50
new agentic image-root tar tasks: 34
combined shared tar tasks: 84
remaining missing shared tar tasks: 5
```

Remaining five tasks should be supplemented from these local cache refs on
`swe_dev` in a future save/push lane:

```text
pytorch-model-recovery -> tb2-offline/pytorch-model-recovery:20260425, image id prefix 3a67ac23a609, size 19.2GB
qemu-alpine-ssh -> tb2-offline/qemu-alpine-ssh:20260425, image id prefix 53987a31bb5e, size 1.96GB
qemu-startup -> tb2-offline/qemu-startup:20260425, image id prefix 5814c86fde20, size 1.96GB
torch-pipeline-parallelism -> tb2-offline/torch-pipeline-parallelism:20260425, image id prefix a014da66007d, size 11.3GB
torch-tensor-parallelism -> tb2-offline/torch-tensor-parallelism:20260425, image id prefix 7f0d9bce1454, size 11GB
```

Risk: these are among the largest remaining images, especially the PyTorch and
model-recovery tasks. The future lane should stage them deliberately and record
sha256 and P0 digest. This audit did not save or hash those images.

### SWE-bench Verified

Shared state is still partial compared with `swe_dev`:

```text
swe_dev Docker cache:
  500 swebench/sweb.eval refs
  728 swerex-prebuilt refs

shared agentic images:
  1 swebench eval base tar: django10097
  97 SWE-ReX chunk/shared tars under /mnt/shared-storage-user/.../swe/swerex_images
```

Supplement source should be `swe_dev:/data/docker`, not the current shared
manifest alone. The next allowed staging lane should:

1. Freeze the exact Verified task/image map per scaffold.
2. Start with the existing `swebench_verified_django10097.yaml` identity probe.
3. Use `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/*.tar`
   where the needed SWE-ReX wrapper is already chunked.
4. Export or push missing `swebench/sweb.eval.*` refs from `swe_dev` Docker cache.
5. Treat Docker image IDs as local identities only; publish P0 registry digests
   or tar sha256s before declaring multi-worker reproducibility.

### OpenHands Runtime

Current formal OpenHands runtime coverage is missing:

```text
required runtime in manifest:
  ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98
swe_dev matching runtime refs:
  0
shared images/openhands:
  absent
only openhands-like local ref:
  openhands_smoke4_recover:sphinx8595
```

Do not mark OpenHands image-ready based on the pretag alone. A future lane needs
to prove whether `openhands_smoke4_recover:sphinx8595` is a recoverable source
for the expected runtime tag, or build/pull/push the official runtime in an
allowed environment.

## ISSUE-READY

### Stale Terminal-Bench 2.1 cache manifest undercounts current shared tar coverage

- file: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:10`
- file: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:12`
- file: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:15`
- file: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:16`

The manifest still says:

```text
shared_tar_root: /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425
shared_tar_count: 50
shared_tar_coverage_is_50_of_89_cached_tasks
missing_transport_for_39_cache_only_tasks
```

Repro, read-only:

```bash
BASE=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1
docker images --format '{{.Repository}}:{{.Tag}}' |
  awk '$1 ~ /^tb2-offline\// {sub(/^tb2-offline\//,"",$1); sub(/:20260425$/,"",$1); print $1}' |
  sort > /tmp/tb2-docker.txt
find /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425 "$BASE" \
  -type f -name '*.tar' -printf '%f\n' 2>/dev/null |
  sed 's/\.tar$//' | sort -u > /tmp/tb2-shared.txt
wc -l /tmp/tb2-docker.txt /tmp/tb2-shared.txt
comm -23 /tmp/tb2-docker.txt /tmp/tb2-shared.txt
```

Observed:

```text
docker_tb2_task_count=89
all_shared_tb2_tar_task_count=84
docker_tasks_still_missing_any_shared_tar=5
pytorch-model-recovery
qemu-alpine-ssh
qemu-startup
torch-pipeline-parallelism
torch-tensor-parallelism
```

Impact: any image-warmup planner using this manifest will think 39 TB2 tasks
still need transport even though 34 have already been materialized under
`images/terminalbench2.1/20260425_missing_batch1` plus
`20260425_missing_batch2`. That can cause duplicate save/push work, incorrect
risk accounting, and stale blocker reporting.

Fix: regenerate `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` from
both shared roots:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1
```

Update the top-level evidence to `combined_shared_tar_count: 84`, replace the
39-task blocker with a five-task blocker, and add fallback tar paths for the
new `missing_batch1` and `missing_batch2` artifacts.

## Risks

- `/data` on `swe_dev` is 89% used: `1.0T` total, `907G` used, `117G` free.
  Future large `docker save` work must stage deliberately and clean temporary
  files after checksums are recorded.
- The largest remaining TB2 images are 11-19GB by Docker display size. Saving
  them may consume substantial `/data/tmp` and shared-storage bandwidth.
- `fix-git` remains known-bad for worker rootless Docker from prior reports.
  Even though `swe_dev` has `tb2-offline/fix-git:20260425`, its old shared tar
  should not be treated as worker-safe until rebuilt/resaved and load-tested.
- Local Docker image IDs are not portable registry digests. They are useful for
  source identity, but P0 registry digests or tar sha256s are required for a
  durable runner manifest.
- OpenHands runtime is not covered by `swe_dev` formal runtime refs or shared
  tars. The `openhands_smoke4_recover:sphinx8595` image may be useful evidence,
  but it is not the manifest-required runtime tag.
- One attempted sha256 read of a 3.4GB tar was interrupted after running too
  long. This does not mean the tar is invalid; it only means this audit did not
  compute its checksum.

## Commands And Exit Codes

All commands used the direct `swe_dev` endpoint:

```text
ssh -CAXY zengweijun+zwj.group-ailab-mineruinfra-mineruinfra-cpu+root.ailab-mineruinfra.ws@h.pjlab.org.cn
```

| Command shape | RC | Notes |
| --- | ---: | --- |
| `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required preflight, local Mac. |
| `sed -n '261,620p' WORKFLOW.md` and `sed -n '621,1040p' WORKFLOW.md` | 0 | Completed workflow read. |
| Remote host/worktree/top-path check with `git status --short`, `df -h /data/swe /data/tmp /data/docker` | 0 | Found target worktree and unrelated modified file. |
| Bounded `/data/swe` relevant dirs/files and top-level `du` | 0 | Found `docker_prebuilt`, `full500_local`, `tbench-runs`. |
| Broad `/data/tmp` relevant scan and `du` | 0 after interrupt | Output was noisy; superseded by targeted scans. |
| `/data/docker` metadata shape/counts with bounded `find` | 0 | No layer traversal beyond metadata counts. |
| `docker info --format ...` and `docker images --format ...` counts/samples | 0 | Read-only; no save/load/pull/run/build. |
| Strict OpenHands/TB2/SWE image count recalculation | 0 | Corrected OpenHands runtime count to 0. |
| Compare `tb2-offline` Docker tasks against old shared 20260425 tars | 0 | 39 Docker tasks missing old shared tars. |
| Targeted `/data/tmp/tb2-batch10-mteb-run` and related dirs | 0 | Found `mteb-retrieve.tar`, logs, digest evidence. |
| Attempted `sha256sum /data/swe/docker_prebuilt/astropy__astropy-12907__swerex_bundle_v2_20260425.tar` | 130 | Interrupted due long read time; no checksum recorded. |
| Re-read tar stats and TB2 batch10 logs without sha256 | 0 | Recorded size, mtime, log sha/digest. |
| List repo manifests and shared image root files | 0 | Found TB2 batch tar materialization and SWE django10097 tar. |
| Read selected manifests including `terminal_bench_2_1_swe_dev_cache.yaml` and `swebench_verified_django10097.yaml` | 0 | Found stale TB2 cache manifest counts. |
| Count current shared TB2 image-root task coverage | 0 | 34 task tars under agentic image root. |
| Compare combined old+new shared TB2 tars against `swe_dev` Docker cache | 0 | 84/89 covered; 5 missing. |
| `nl -ba manifests/images/terminal_bench_2_1_swe_dev_cache.yaml | sed -n '1,32p'` | 0 | Source lines for ISSUE-READY. |
| SWE shared-vs-cache count for eval, SWE-ReX, and shared image roots | 0 | 500 eval refs, 728 SWE-ReX refs, 1 eval tar, 97 SWE-ReX tars. |
| Read existing `reports/swe_terminal_image_inventory_20260626.md` and `reports/next_swebench_image_map_plan_20260625.md` | 0 | Cross-checked existing conclusions. |
