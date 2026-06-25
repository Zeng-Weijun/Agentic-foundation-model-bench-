# Terminal-Bench 2.1 Fix-Git Rebuild Plan

Date: 2026-06-25

Scope: Lane 3 only. No benchmark/model run was launched. No `swe_dev`/`swe-dev`
host was used. Writes are limited to this report and
`scripts/rebuild_tb21_fix_git_image.sh`.

## Summary

The real `fix-git` source lives under the shared Terminal-Bench 2.1 task
checkout, with the Docker build inputs in the task's `environment/` directory:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/Dockerfile
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/setup.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/resources/patch_files/
```

The source Dockerfile matches the failure hypothesis from
`reports/terminal_bench_2_1_image_load_debug_20260625.md`: it persists
`/app/resources/patch_files` in one layer and removes `/app/resources` in a
later `RUN` layer.

`dev` has a usable Docker/build engine:

```text
host=zwj2
docker=/usr/bin/docker
docker version rc=0, Server Version 26.1.3
docker info rc=0, Driver=overlay2, DockerRootDir=/mnt/docker_root_swebench_800g
docker buildx version rc=0, v0.30.1
podman/buildah/nerdctl unavailable
```

Because the rebuild can pull/use networked sources and may take non-trivial
time, I did not run the actual build in this lane. I added a dry-run-first
script that can be executed on `dev` when the orchestrator wants to spend that
build time.

## Source Evidence

Verified on `dev`:

```text
host=zwj2
source task:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git
generated YAML:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml/fix-git/task.yaml
prebuilt tar:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
prebuilt manifest:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl
shared repo checkout:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
```

Relevant source Dockerfile:

```Dockerfile
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

COPY setup.sh ./

COPY resources /app/resources

RUN bash /app/setup.sh && rm -rf /app/resources /app/setup.sh

WORKDIR /app/personal-site
```

Relevant setup lines:

```text
cp /app/resources/patch_files/about.md ./_includes/about.md
cp /app/resources/patch_files/default.html ./_layouts/default.html
```

Resource files:

```text
2e09260b011012f9f7f491cd02809903449924cf8f825acd369fb8990b04e768  resources/patch_files/about.md
fb3fad17b83338002f5fd6a99ea1ec3a662cea570f9fff9240b8abc1861be655  resources/patch_files/default.html
```

The prebuilt manifest has duplicate rows for the same expected tag and archive:

```text
tb2-offline/fix-git:20260425
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
```

## Rebuild Strategy

The script generates a temporary BuildKit Dockerfile instead of editing the
upstream Terminal-Bench task. The generated Dockerfile bind-mounts `setup.sh`
and `resources/` during the single setup `RUN`, so the final image never
persists `/app/resources/patch_files` as a layer entry and therefore never
removes that path in a later layer.

Generated Dockerfile concept:

```Dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

RUN --mount=type=bind,source=setup.bind.sh,target=/tmp/setup.sh,readonly \
    --mount=type=bind,source=resources,target=/tmp/tb21_resources,readonly \
    bash /tmp/setup.sh

WORKDIR /app/personal-site
```

`setup.bind.sh` is generated from the source `setup.sh` by replacing
`/app/resources` with `/tmp/tb21_resources`.

Expected effect:

- Preserve the source task behavior and final `WORKDIR`.
- Preserve the worker-facing tag `tb2-offline/fix-git:20260425`.
- Avoid the known bad persisted layer sequence:
  `COPY resources /app/resources` followed by `rm -rf /app/resources`.
- Save the rebuilt tar in a separate directory, leaving the original
  `20260425/fix-git.tar` untouched until the rebuilt tar is load-tested.

## Script

Added:

```text
scripts/rebuild_tb21_fix_git_image.sh
```

Default output paths:

```text
tar:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar
sha256:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar.sha256
inspect:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.docker-inspect.json
layer scan:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.layer-scan.txt
tag:
  tb2-offline/fix-git:20260425
```

Dry run on `dev` from a checkout containing the script:

```bash
bash scripts/rebuild_tb21_fix_git_image.sh --dry-run
```

Actual rebuild on `dev`:

```bash
bash scripts/rebuild_tb21_fix_git_image.sh --execute
```

If a fully uncached rebuild is desired:

```bash
bash scripts/rebuild_tb21_fix_git_image.sh --execute --no-cache
```

The script's post-save check scans nested layer tar entries and fails if it
finds `app/resources/patch_files`, `app/resources/.wh.patch_files`, or
`app/.wh.resources`.

## Worker Load Command After Rebuild

Run only after the rebuilt tar and checksum exist:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar &&
   DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/fix-git:20260425 >/dev/null'
```

Expected load success should replace the current failure:

```text
unlinkat /app/resources/patch_files: input/output error
```

If this rebuilt tar still fails with the same path, the hypothesis is wrong or
Docker is preserving the path through another mechanism. The next probe should
compare the rebuilt tar's layer scan with the original tar and inspect the
worker rootless daemon log around the new failed timestamp.

## Commands Run

All commands below exited with rc=0 unless noted.

```bash
cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '621,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '1,260p' reports/cmux_agent_loop_20260625.md
git status --short
ls -la reports scripts
sed -n '1,260p' reports/terminal_bench_2_1_image_load_debug_20260625.md
sed -n '1,240p' reports/offline_image_fix_git_manifest_20260625.md
sed -n '1,240p' reports/terminal_bench_2_1_smoke_plan_20260625.md
sed -n '1,220p' scripts/run_terminal_bench_2_1_smoke.sh
sed -n '221,440p' scripts/run_terminal_bench_2_1_smoke.sh
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<source candidate and initial source tree probe>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<environment/Dockerfile/setup/resources/hash probe>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<docker/build engine probe>'
chmod +x scripts/rebuild_tb21_fix_git_image.sh
bash -n scripts/rebuild_tb21_fix_git_image.sh
scripts/rebuild_tb21_fix_git_image.sh --dry-run
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'bash -s -- --dry-run' < scripts/rebuild_tb21_fix_git_image.sh
git diff --check -- reports/terminal_bench_fix_git_rebuild_plan_20260625.md scripts/rebuild_tb21_fix_git_image.sh
```

Notable non-zero results:

```text
rg Agentic-foundation-model-bench|terminal_bench|Terminal-Bench|fix-git|tb21|TB2.1 /Users/Zhuanz1/.codex/memories/MEMORY.md -> rc=1, no memory hits
test -e reports/terminal_bench_fix_git_rebuild_plan_20260625.md -> rc=1 before creation
test -e scripts/rebuild_tb21_fix_git_image.sh -> rc=1 before creation
command -v podman on dev -> rc=1
podman version on dev -> rc=127
command -v buildah on dev -> rc=1
buildah version on dev -> rc=127
command -v nerdctl on dev -> rc=1
nerdctl version on dev -> rc=127
scripts/rebuild_tb21_fix_git_image.sh --dry-run -> rc=2 before adding explicit --dry-run support; fixed and rerun rc=0
```

## Blockers And Risks

- The actual image rebuild was not run in this lane to avoid launching a
  possibly long networked Docker build from a concurrent cmux agent.
- The rebuilt tar SHA256 is therefore not known yet.
- Rebuild execution on `dev` may need Debian package index access, Docker Hub
  base image access, and GitHub access for
  `https://github.com/TheMikeMerrill/personal-site.git`.
- The original source uses `python:3.13-slim-bookworm` by tag, not digest, so a
  rebuild may not be byte-identical to the old image. It should still preserve
  task behavior because `setup.sh` resets the cloned repo to commit `d7d3e4b`
  before applying the resource files.
- The separate worker Terminal-Bench Python 3.13/.venv blocker remains outside
  this lane. This plan only addresses loading the `fix-git` Docker image.
