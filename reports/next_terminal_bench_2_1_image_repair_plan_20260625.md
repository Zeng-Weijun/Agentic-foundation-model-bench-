# Next Terminal-Bench 2.1 Image Repair Plan

Date: 2026-06-25

Scope: report-only lane for Terminal-Bench 2.1 image repair. I read
`/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before repo work and worked from
`/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
No service restart, Docker build, Docker pull, Docker load, benchmark run,
model call, commit, or push was performed. This report is the only file written
in this lane.

## Executive Decision

Terminal-Bench 2.1 is blocked by two independent gates:

1. `fix-git.tar` is a known-bad archive for worker rootless Docker. It must be
   rebuilt or resaved before it is used as the first 2.1 smoke task.
2. The full 2.1 image set is not manifest-complete. Current bounded checks show
   89 source task dirs, 89 generated YAML tasks, 86 prebuilt manifest rows, 64
   unique manifest tasks, and only 50 present task tars.

The next repair should not be a blind rerun of the current rebuild script. The
latest shared retry log shows `dev` Docker recovered far enough to reach the
task layer, but the build then failed at `apt-get update && apt-get install -y
git` because `deb.debian.org` timed out. Fix the build egress or use an
approved internal Debian mirror/base image first, then rebuild `fix-git` with
the flattened resources strategy already encoded in
`scripts/rebuild_tb21_fix_git_image.sh`.

After `fix-git` is repaired and load-tested, promote Terminal-Bench 2.1 from a
one-task smoke image to a full per-task image manifest. The manifest must keep
known-bad, missing-tar, absent-from-prebuilt-manifest, duplicate-row, load-tested,
and registry/fallback states separate.

## Evidence Snapshot

### Paths

```text
TB 2.1 task source:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks

TB 2.1 generated YAML:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml

Prebuilt image area:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425

Current failed rebuild output dir:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild

Latest retry log:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_2249_retry.log
```

### Current counts

Bounded `ssh dev` checks on 2026-06-25:

```text
source_task_count=89
yaml_task_count=89
manifest_lines=86
unique_manifest_tasks=64
tar_count=50
missing_archive_rows=14
source_tasks_absent_from_manifest=25
duplicate_task_row_groups=22
```

The 50 present tars are the only currently usable fallback archive source for
Terminal-Bench 2.1. One of those 50, `fix-git.tar`, is known bad on worker
rootless Docker.

### `fix-git` load failure

`reports/terminal_bench_2_1_image_load_debug_20260625.md` established:

```text
tar:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
size:
  347601920
sha256:
  6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511
worker load error:
  unlinkat /app/resources/patch_files: input/output error
```

The tar is readable and passes `tar`/Python tarfile iteration. Loading a copy
from `/tmp` reproduced the same error, so this is not a shared-storage read
failure. A different 2.1 tar, `llm-inference-batching-scheduler.tar`, loaded
successfully into the same rootless Docker store. The supported root cause is a
rootless overlay/import incompatibility triggered by `fix-git` creating
`/app/resources/patch_files` in one layer and removing `/app/resources` in a
later layer.

The source Dockerfile explains the bad layer sequence:

```Dockerfile
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

COPY setup.sh ./

COPY resources /app/resources

RUN bash /app/setup.sh && rm -rf /app/resources /app/setup.sh

WORKDIR /app/personal-site
```

### Dev Docker and apt state

Earlier real execution log:

```text
log:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_223806_surface51.log
rc:
  1
failure:
  ERROR: failed to build: failed to receive status: rpc error: code = Unavailable desc = error reading from server: EOF
post-failure:
  docker.service failed after BuildKit/bbolt panic, then restart attempts hit duplicate docker0 bridge state
```

Current read-only health check shows `dev` Docker is back:

```text
host=zwj2
docker=/usr/bin/docker
client=26.1.3 server=26.1.3
docker_info_rc=0
server=26.1.3 images=3 root=/mnt/docker_root_swebench_800g driver=overlay2
buildx_version_rc=0
github.com/docker/buildx v0.30.1
buildx_ls_rc=0
default builder running, BuildKit v0.13.2
```

Latest shared retry log:

```text
log:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_2249_retry.log
rc:
  1
base resolved:
  docker.io/library/python:3.13-slim-bookworm@sha256:fcbd8dfc2605ba7c2eca646846c5e892b2931e41f6227985154a596f26ab8ed7
failed step:
  RUN apt-get update && apt-get install -y git
error:
  Could not connect to debian.map.fastlydns.net:80 (151.101.78.132), connection timed out
  Failed to fetch http://deb.debian.org/debian/dists/bookworm/InRelease
  apt-get ... did not complete successfully: exit code: 100
```

This is the current build blocker. Do not rerun the same build until the Debian
package source is reachable from the build context or replaced with an approved
internal path.

### Worker TB CLI state

`reports/terminal_bench_2_1_smoke_plan_20260625.md` established that the worker
Terminal-Bench CLI is not usable yet:

```text
shared tb bin:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/tb
broken interpreter chain:
  .venv/bin/tb -> .venv/bin/python3 -> /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
worker issue:
  target Python 3.13 path is missing
worker system Python:
  /bin/python3 is Python 3.10.12
```

The smoke wrapper deliberately fails closed when `"$TB_BIN" run --help` fails.
The image work and TB CLI/Python 3.13 work can proceed independently, but no
Terminal-Bench 2.1 model smoke should run until both are fixed.

### Registry and fallback transport state

The P0 OCI registry exists at `https://100.97.118.137:8555`, but current worker
evidence is not enough to make registry pull the primary Terminal-Bench 2.1
distribution path:

```text
worker shell curl to registry:
  pass, HTTP 200
worker rootless docker pull from registry:
  fail, dial tcp 100.97.118.137:8555: connect: network is unreachable
live daemon guard:
  active rootless daemon does not include --config-file=/dev/null
cached docker run --network none:
  pass for an already cached P0 image
```

For Terminal-Bench 2.1, use shared fallback tars first. Add registry digests only
after an image is rebuilt or validated and the worker rootless daemon pull path
is fixed, or after a staging host pushes digest-pinned images and fallback tars
remain available.

## Repair Plan

### Phase 0: freeze repair inputs

Do this before any build:

1. Keep the original `20260425/fix-git.tar` unchanged as the known-bad evidence
   artifact.
2. Preserve the latest retry log and rc file:

   ```text
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_2249_retry.log
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/tb21_fix_git_rebuild_20260625_2249_retry.log.rc
   ```

3. Record the current `python:3.13-slim-bookworm` digest from the retry log:

   ```text
   sha256:fcbd8dfc2605ba7c2eca646846c5e892b2931e41f6227985154a596f26ab8ed7
   ```

4. Record the source `fix-git` inputs:

   ```text
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/Dockerfile
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/setup.sh
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/resources/patch_files/about.md
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git/environment/resources/patch_files/default.html
   ```

### Phase 1: clear the build-host gate

Before rebuilding, run only read-only build-host checks:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -e
docker version --format "client={{.Client.Version}} server={{.Server.Version}}"
docker info --format "server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} driver={{.Driver}}"
docker buildx version
docker buildx ls | sed -n "1,12p"'
```

Do not restart Docker from a bench lane. If `docker info` or `buildx ls` fails,
hand off to an infra lane because the earlier failure mode included a BuildKit
bbolt panic and service restart conflict.

Then clear the apt egress gate in a short, explicit build-network probe owned by
the image lane, not by a benchmark lane. Acceptable fixes, in preference order:

1. Configure the rebuild to use an approved internal Debian mirror for bookworm.
2. Pass the required proxy or network settings into the Docker build, if allowed
   by workspace policy, and log them without secrets.
3. Build or reuse an approved internal base image that already contains Python
   3.13 and `git`, then use that digest as the `fix-git` rebuild base.

The rebuild should fail fast if `apt-get update` cannot reach its configured
package source. Do not consume another long build slot on a known timed-out
`deb.debian.org` path.

### Phase 2: rebuild `fix-git` without persisted resources

The current script concept is correct: generate a temporary Dockerfile that
bind-mounts `setup.sh` and `resources` during the setup `RUN` so
`/app/resources/patch_files` never appears in the final persisted layer graph.

Before the next `--execute`, adjust or override the generated Dockerfile so the
base and apt path are deterministic:

```Dockerfile
# syntax=docker/dockerfile:1.7
FROM python:3.13-slim-bookworm@sha256:fcbd8dfc2605ba7c2eca646846c5e892b2931e41f6227985154a596f26ab8ed7

WORKDIR /app

RUN apt-get update && apt-get install -y git

RUN --mount=type=bind,source=setup.bind.sh,target=/tmp/setup.sh,readonly \
    --mount=type=bind,source=resources,target=/tmp/tb21_resources,readonly \
    bash /tmp/setup.sh

WORKDIR /app/personal-site
```

If the apt fix requires a mirror, add it in the generated Dockerfile as an
explicit `ARG APT_MIRROR` or source-list rewrite rather than editing the
Terminal-Bench upstream task. Keep the upstream task directory unchanged.

Run through local tmux plus `ssh dev` per `WORKFLOW.md`. A future execution
command should look like this, with logs on shared storage:

```bash
cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
tmux new-session -d -s tb21_fixgit_rebuild_r2_$(date +%Y%m%d_%H%M%S) \
  "cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- &&
   ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'bash -s' < scripts/rebuild_tb21_fix_git_image.sh"
```

The remote wrapper should set a shared log path and run:

```bash
source ~/.bashrc >/dev/null 2>&1 || true
export TMPDIR=/data/tmp
export DEST_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild
mkdir -p /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs
bash -s -- --execute > "$LOG" 2>&1
echo "$?" > "$LOG.rc"
```

Expected successful artifacts:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar.sha256
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.docker-inspect.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.layer-scan.txt
```

Required local validation before worker load:

```text
fix-git.tar exists and is non-empty
fix-git.tar.sha256 verifies
fix-git.docker-inspect.json records tb2-offline/fix-git:20260425 or an explicitly approved replacement tag
fix-git.layer-scan.txt contains "no app/resources/patch_files layer entries found"
no layer-scan hit for app/resources/patch_files, app/resources/.wh.patch_files, or app/.wh.resources
```

### Phase 3: worker load-test only the repaired tar

Run this only after Phase 2 succeeds. This lane did not run it.

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -e
   export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
   cd /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild
   sha256sum -c fix-git.tar.sha256
   docker info --format "server={{.ServerVersion}} root={{.DockerRootDir}} security={{json .SecurityOptions}}"
   docker load -i fix-git.tar
   docker image inspect tb2-offline/fix-git:20260425 >/dev/null
   docker run --rm --network none tb2-offline/fix-git:20260425 /bin/sh -lc "git --version && python3 --version"'
```

If the repaired tar still fails with the same path, stop and compare the new
layer scan against the original archive. Only then consider the rootless
containerd alternative mentioned in the load-debug report:

```text
/bin/ctr -a /tmp/rl/exec/containerd/containerd.sock
```

Do not use that path until the Docker `moby` namespace wiring is explicitly
decided, because the benchmark runner expects Docker-visible images.

### Phase 4: repair worker Python 3.13 / TB CLI

This can happen in parallel with image repair but must finish before any real
Terminal-Bench 2.1 smoke.

Required outcome:

```text
TB_BIN points to a worker-usable tb executable
"$TB_BIN" --help exits 0 on worker
"$TB_BIN" run --help exits 0 on worker
the interpreter is Python 3.13, not worker system Python 3.10
no public download is required from the worker
```

Concrete acceptable approaches:

1. Repair the shared `.venv` interpreter target by staging the expected uv
   Python 3.13 path on the worker:

   ```text
   /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
   ```

2. Stage a separate shared Terminal-Bench Python 3.13 venv and run with:

   ```bash
   export TB_BIN=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-py313/.venv/bin/tb
   ```

3. If the venv is rebuilt, verify it against the generated 2.1 YAML path and
   keep all wheel/package sources internal or pre-staged.

Do not run `scripts/run_terminal_bench_2_1_smoke.sh --execute` until both the
repaired image and `TB_BIN` checks pass.

### Phase 5: full Terminal-Bench 2.1 manifest coverage

After the one-image repair, write a real per-task image manifest. It should not
reuse the current 86-row prebuilt `manifest.jsonl` directly because that file
has duplicates and incomplete task coverage.

Required manifest rows:

```text
one row for each of the 89 generated YAML/source tasks
```

Required fields per row:

```yaml
task_id: fix-git
source_task_dir: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git
task_yaml: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml/fix-git/task.yaml
expected_tag: tb2-offline/fix-git:20260425
prebuilt_manifest_rows: 2
prebuilt_archive: /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
fallback_tar: /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild/fix-git.tar
fallback_tar_sha256: <sha256-after-rebuild>
registry_ref: null
registry_digest_status: missing_until_pushed
worker_load_status: pending
failure_class: null
last_verified_at: null
```

Required status classes:

```text
tar_present_not_load_tested
tar_present_load_verified
tar_known_bad_rootless_load
manifest_row_archive_missing
source_task_absent_from_prebuilt_manifest
duplicate_prebuilt_rows_deduped
build_failed_recorded
registry_digest_missing
registry_digest_available
docker_free_not_applicable
```

Current initial classification:

```text
50 tasks: tar present in 20260425 fallback area
1 of those 50: fix-git tar known bad and must be replaced
1 of those 50: llm-inference-batching-scheduler load-verified as control
14 tasks: manifest row exists but archive missing
25 tasks: source/YAML task exists but no prebuilt manifest row
22 task ids: duplicate rows in manifest.jsonl
3 build failures named in failures.log, with reshard-c4-data repeated
```

Manifest rows whose archive is missing:

```text
mteb-retrieve
path-tracing
portfolio-optimization
regex-chess
rstan-to-pystan
schemelike-metacircular-eval
video-processing
multi-source-data-merger
path-tracing-reverse
protein-assembly
sam-cell-seg
train-fasttext
winning-avg-corewars
reshard-c4-data
```

Source/YAML tasks absent from the prebuilt manifest:

```text
install-windows-3.11
nginx-request-logging
openssl-selfsigned-cert
overfull-hbox
password-recovery
polyglot-c-py
polyglot-rust-c
prove-plus-comm
pypi-server
pytorch-model-cli
pytorch-model-recovery
qemu-alpine-ssh
qemu-startup
query-optimize
raman-fitting
regex-log
sanitize-git-repo
sparql-university
sqlite-db-truncate
sqlite-with-gcov
torch-pipeline-parallelism
torch-tensor-parallelism
tune-mjcf
vulnerable-secret
write-compressor
```

Duplicate task row groups in `manifest.jsonl`:

```text
adaptive-rejection-sampler
bn-fit-modify
build-pov-ray
circuit-fibsqrt
compile-compcert
constraints-scheduling
custom-memory-heap-crash
distribution-search
dna-assembly
dna-insert
extract-moves-from-video
feal-differential-cryptanalysis
feal-linear-cryptanalysis
filter-js-from-html
fix-git
fix-ocaml-gc
gcode-to-text
headless-terminal
llm-inference-batching-scheduler
make-mips-interpreter
mcmc-sampling-stan
mteb-leaderboard
```

Build failures recorded in the prebuilt area:

```text
custom-memory-heap-crash
reshard-c4-data
install-windows-3.11
```

The full repair target is therefore 39 missing-image tasks plus the `fix-git`
replacement, not only one archive:

```text
14 manifest tasks with missing archive
+ 25 source tasks absent from prebuilt manifest
+ 1 known-bad present archive
= 40 image actions before all 89 tasks can be image-ready
```

### Phase 6: registry promotion after fallback readiness

Do not make P0 OCI registry the only source of truth for Terminal-Bench 2.1 yet.
For each image row, require:

```text
fallback_tar exists
fallback_tar_sha256 verifies
worker rootless load or cached inspect passes
docker run --rm --network none smoke passes where practical
registry_ref digest is optional until worker pull is proven
```

Once the worker rootless daemon is restarted under the synced guard and
`docker pull` by digest passes, add registry refs with digest-pinned image
coordinates:

```text
100.97.118.137:8555/<project>/<terminal-bench-2.1-task>@sha256:<digest>
```

Keep the fallback tar and checksum in the manifest even after registry digest
promotion. Current worker evidence shows registry shell reachability can pass
while Docker daemon pull fails.

## Acceptance Criteria

`fix-git` is repaired when all are true:

```text
new fix-git.tar exists under a new rebuild directory
new fix-git.tar.sha256 verifies
layer scan proves no app/resources/patch_files persisted/whiteout markers
worker rootless docker load exits 0
docker image inspect tb2-offline/fix-git:20260425 exits 0
docker run --rm --network none tb2-offline/fix-git:20260425 "git --version && python3 --version" exits 0
original 20260425/fix-git.tar remains preserved as known-bad evidence
```

Terminal-Bench 2.1 is image-manifest ready when all are true:

```text
89 source tasks and 89 YAML tasks have manifest rows
every row has one of: load-verified fallback tar, registry digest plus fallback tar, or explicit blocked/build-failed status
all duplicate prebuilt rows are deduped with original row count retained as metadata
all 14 missing-archive rows are either rebuilt or marked blocked with build logs
all 25 source-only rows are either built or marked blocked with build logs
fix-git no longer points at the known-bad 20260425 tar as its runnable fallback
worker TB CLI Python 3.13 is usable
suite runner remains fail-closed until image and TB CLI gates pass
```

## Commands Run In This Lane

All commands below were read-only except creating this report.

```bash
sed -n '1,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_next_tb21_repair_read.txt && cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd
# rc=0

sed -n '1,260p' manifests/images/terminal_bench_2_1.yaml
# rc=0

sed -n '1,220p' manifests/bench_registry.yaml
# rc=0

sed -n '1,220p' manifests/images/pending_benches.yaml
# rc=0

sed -n '1,260p' reports/p0_harbor_bench_manifest_inventory_20260625.md
# rc=0

sed -n '1,280p' reports/terminal_bench_fix_git_rebuild_plan_20260625.md
# rc=0

sed -n '1,320p' scripts/rebuild_tb21_fix_git_image.sh
# rc=0

sed -n '1,280p' reports/all_bench_offline_gap_matrix_20260625.md
# rc=0

sed -n '1,260p' reports/offline_docker_asset_plan_20260625.md
# rc=0

sed -n '1,360p' reports/terminal_bench_2_1_smoke_plan_20260625.md
# rc=0

sed -n '1,340p' reports/terminal_bench_2_1_image_load_debug_20260625.md
# rc=0

sed -n '1,320p' reports/terminal_bench_fix_git_rebuild_execution_20260625.md
# rc=0

ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<bounded TB2.1 counts/source/tar/rebuild-dir check>'
# rc=0

ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<read-only docker version/info/buildx health check>'
# rc=0

ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<shared logs grep for apt/build failure>'
# rc=0

ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<manifest missing archive, duplicate row, absent source task analysis>'
# rc=0

ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<failures.log read>'
# rc=0

test -e reports/next_terminal_bench_2_1_image_repair_plan_20260625.md
# rc=1 before creation
```

## Blockers

1. `fix-git` original tar is not safe to load on worker rootless Docker.
2. The latest rebuild retry is blocked by Debian apt egress from inside the
   Docker build.
3. Worker Terminal-Bench CLI Python 3.13 is broken and must be staged or
   repaired before smoke execution.
4. Worker rootless Docker can run cached images, but its registry pull path is
   not currently proven; use fallback tars until the daemon guard and pull path
   are fixed.
5. Full Terminal-Bench 2.1 image coverage needs 40 image actions: 39 missing
   task images plus the `fix-git` known-bad replacement.
