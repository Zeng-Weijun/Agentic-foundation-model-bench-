# Terminal-Bench 2.1 Image Load Debug

Date: 2026-06-25

Scope: investigate why rootless Docker on `worker-j9jjd` fails to load the Terminal-Bench 2.1 `fix-git` image. No benchmark/model run was launched. `swe_dev` was not used.

## Summary

The failure is specific to the `fix-git` image archive/layer application path, not to all Terminal-Bench 2.1 tars, not to shared-storage reads, and not to a fully broken rootless Docker store.

Evidence:

- `fix-git.tar` is readable and matches the known hash:
  `6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511`.
- `tar -tf` and Python `tarfile` can iterate the archive successfully.
- The layer containing `app/resources/patch_files/` can be streamed out and extracted to `/tmp` successfully.
- Rootless Docker loaded another TB2.1 OCI archive successfully:
  `tb2-offline/llm-inference-batching-scheduler:20260425` from
  `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/llm-inference-batching-scheduler.tar`.
- Loading `fix-git.tar` from a local `/tmp` copy reproduced the same failure:
  `unlinkat /app/resources/patch_files: input/output error`.

Conclusion: this is not a shared filesystem tar-read issue. The best-supported root cause is a rootless Docker overlay2/import bug or incompatibility triggered by the `fix-git` layer sequence around `/app/resources/patch_files`, not corrupt tar bytes. Re-saving or rebuilding this one image into a flatter Docker archive that does not create then remove `/app/resources/patch_files` across layers is the most concrete next action.

## Host and Docker State

Worker:

```text
host=zwj2-64rlk-3469265-worker-0
date=2026-06-25T21:12:23+08:00
```

Docker rootless endpoint:

```text
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
Driver=overlay2
DockerRootDir=/tmp/rl/data
Security=["name=seccomp,profile=builtin","name=rootless"]
```

Storage and inodes were not tight:

```text
Filesystem      Size  Used Avail Use% Mounted on
tmpfs           391G  137G  255G  35% /tmp

Filesystem     Inodes IUsed IFree IUse% Mounted on
tmpfs            252M  4.3M  248M    2% /tmp
```

Rootless Docker had existing SWE images and no Terminal-Bench images before the probe:

```text
docker system df:
Images          237       0         133.1GB   133.1GB (100%)
Containers      0         0         0B        0B
Local Volumes   0         0         0B        0B
Build Cache     0         0         0B        0B

tb_tags=0
```

`docker version --format "{{.Server.Version}}"` returned rc=1 with EOF once. `docker info`, image inspect, and image load APIs continued working. `/tmp/rl/dockerd.log` shows Docker 26.1.3 can panic on `/version` in `fillRootlessVersion`, but this is separate from the `docker load` path observed below.

## Archive Checks

`fix-git.tar`:

```text
path=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
size=347601920
sha256=6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511
tar -tf rc=0
python tarfile iteration rc=0, members=30
```

Smallest present TB2.1 tar used for comparison:

```text
path=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/llm-inference-batching-scheduler.tar
size=185704960
sha256=fd609c5aab2a26bd7403bbc5cb39e52160112b718b826bdc02e477909c400615
```

Both archives are OCI-style Docker-loadable archives with `manifest.json`, `index.json`, `oci-layout`, `repositories`, and `blobs/sha256/*`.

## Layer Evidence

`fix-git.tar` has 11 layers. The reported failing path appears in layer 9:

```text
09 cc77453ad00b17becf953a4ea6ec300658fd249144be5e6586ab34fa9c140efb size=9216 entries=5 marker=patch_files
```

Layer listing:

```text
drwxr-xr-x 0/0               0 2026-06-02 14:33 app/resources/
drwxr-xr-x 0/0               0 2026-06-02 14:33 app/resources/patch_files/
-rw-r--r-- 0/0             332 2026-06-02 14:33 app/resources/patch_files/about.md
-rw-r--r-- 0/0            4875 2026-06-02 14:33 app/resources/patch_files/default.html
```

Manual extraction of that layer to `/tmp` succeeded:

```text
extract_rc=0
/tmp/tb21_layer_probe_fix_git/app/resources/patch_files/about.md
/tmp/tb21_layer_probe_fix_git/app/resources/patch_files/default.html
```

The task Dockerfile explains why this path exists:

```Dockerfile
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y git

COPY setup.sh ./

COPY resources /app/resources

RUN bash /app/setup.sh && rm -rf /app/resources /app/setup.sh

WORKDIR /app/personal-site
```

The setup script uses the resources and then the Dockerfile removes them in a later layer:

```text
cp /app/resources/patch_files/about.md ./_includes/about.md
cp /app/resources/patch_files/default.html ./_layouts/default.html
...
RUN bash /app/setup.sh && rm -rf /app/resources /app/setup.sh
```

That create/use/remove pattern is the strongest path-specific trigger found.

## Load Attempts

### Attempt 1: smallest TB2.1 archive

Command:

```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock \
  docker load -i /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/llm-inference-batching-scheduler.tar
```

Result:

```text
before_inspect_rc=1
load_rc=0
Loaded image: tb2-offline/llm-inference-batching-scheduler:20260425
after_inspect_rc=0
id=sha256:ddd05f6d1deef06eb492f8187d569ba2890a09887e99fb51ee891ae9ebd62471 size=179631681 created=2026-06-02T18:46:02.31168879+08:00
```

This proves that rootless Docker can load at least one TB2.1 OCI archive into the same store.

### Attempt 2: fix-git from local `/tmp` copy

Command:

```bash
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar /tmp/tb21_fix_git_load_probe.tar
sha256sum /tmp/tb21_fix_git_load_probe.tar
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i /tmp/tb21_fix_git_load_probe.tar
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/fix-git:20260425
rm -f /tmp/tb21_fix_git_load_probe.tar
```

Result:

```text
copy_rc=0
6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511  /tmp/tb21_fix_git_load_probe.tar
before_inspect_rc=1
load_start=2026-06-25T21:14:33+08:00
load_rc=1
unlinkat /app/resources/patch_files: input/output error
after_inspect_rc=1
Error response from daemon: No such image: tb2-offline/fix-git:20260425
removed_tmp_copy_rc=0
```

This rules out shared-storage read instability as the cause of this exact failure.

Final image state after probes:

```text
tb2-offline/llm-inference-batching-scheduler:20260425 inspect_rc=0
tb2-offline/fix-git:20260425 inspect_rc=1
tb_tags_after=1
```

## Docker Logs

Rootless Docker is launched as:

```text
rootlesskit --state-dir=/tmp/rl/state --copy-up=/etc --copy-up=/run dockerd \
  --host=unix:///tmp/rl/run/docker.sock \
  --data-root=/tmp/rl/data \
  --exec-root=/tmp/rl/exec \
  --iptables=false \
  --bridge=none \
  --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh \
  --default-runtime sysbind \
  --storage-driver overlay2
```

`journalctl --user -u docker` had no entries. System `journalctl -u docker` showed the unrelated system Docker service, not the rootless `/tmp/rl` daemon.

Accessible rootless log:

```text
/tmp/rl/dockerd.log
```

The failed `fix-git` attempts do not record the `unlinkat` message in the daemon log, but the log records layer cleanup immediately after failures. For the main-thread failed load:

```text
2026-06-25T21:10:31... Layer sha256:32adc85... cleaned up
...
2026-06-25T21:10:31... Layer sha256:b2008ac... cleaned up
```

For the reproduced `/tmp` load:

```text
2026-06-25T21:14:34... Layer sha256:32adc85... cleaned up
2026-06-25T21:14:34... Layer sha256:fb008a... cleaned up
2026-06-25T21:14:34... Layer sha256:3757fa... cleaned up
```

No residual files were left under:

```text
/tmp/rl/data/image/overlay2/layerdb/tmp
/tmp/rl/data/tmp
```

There are historical rootless Docker warnings/errors in the log:

- many `loading cgroup ... cgroups: cgroup deleted` messages;
- a `failed to remove runc container` cleanup warning from `/tmp/rl/bin/runc-sysbind.sh`;
- Docker `/version` endpoint panics in `fillRootlessVersion`.

Those are daemon-health concerns, but they do not explain the `fix-git`-specific import failure by themselves because a different TB2.1 image loaded successfully afterward.

## Classification Against Requirements

| Candidate cause | Finding |
|---|---|
| Specific to `fix-git.tar` | Supported. `fix-git` fails consistently; another TB2.1 tar loads. |
| All TB2.1 tars fail | Ruled out by successful `llm-inference-batching-scheduler` load. |
| Rootless overlay handling of a certain layer/path | Supported. Failure names `/app/resources/patch_files`, and only `fix-git` has the inspected layer with that path. |
| Shared filesystem read issue | Ruled out for this failure. `/tmp` copy has the same hash and fails the same way. |
| Docker state corruption | Not primary. Docker store has enough space/inodes and can load another TB2.1 image, but rootless Docker has health warnings and `/version` panic. |

## Next Action

Do not spend the next step on copying the tar to `/tmp`; that was tested and fails.

Recommended next action:

1. On `dev`, rebuild or re-save only the `fix-git` image so the final imported archive does not include the create/remove `/app/resources/patch_files` sequence across layers. The cleanest Dockerfile-level rebuild is to collapse the `COPY resources`, `RUN setup`, and cleanup into one layer, or use a multi-stage build so `/app/resources` never appears in the final image history.
2. Save the rebuilt image as a new tar with a new tag, for example `tb2-offline/fix-git:20260625-r1`, and write a sha256 next to it.
3. Load just that rebuilt tar on `worker-j9jjd` rootless Docker.
4. If the rebuilt tar still fails, the next controlled alternative is to import through the available rootless containerd socket with `/bin/ctr -a /tmp/rl/exec/containerd/containerd.sock`, but only after deciding how to wire the resulting image into Docker's `moby` namespace. `nerdctl`, `podman`, `buildah`, and `skopeo` are not installed on the worker.

Available alternate tooling check:

```text
ctr=/bin/ctr
docker=/bin/docker
nerdctl=
podman=
buildah=
skopeo=
containerd socket=/tmp/rl/exec/containerd/containerd.sock
```

The practical first fix is therefore a `fix-git` image rebuild/resave on `dev`, not worker storage cleanup.

## Commands and Exit Codes

```bash
# Required workflow and repo state
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '261,520p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '521,747p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
git status --short
git branch --show-current
git log --oneline -5

# Worker Docker/storage
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker version --format '{{.Server.Version}}'  # rc=1, EOF
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker info --format 'Driver={{.Driver}} DockerRootDir={{.DockerRootDir}} Security={{json .SecurityOptions}}'  # rc=0
df -h /tmp/rl/data  # rc=0
df -ih /tmp/rl/data  # rc=0
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker system df  # rc=0

# Archive checks
stat /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar  # rc=0
sha256sum /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar  # rc=0
tar -tf /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar >/dev/null  # rc=0
python3 tarfile iteration over fix-git.tar  # rc=0, members=30

# Layer tracing
python3 inspect manifest.json/index.json/repositories and grep nested blob tar listings  # rc=0
tar -xOf fix-git.tar blobs/sha256/cc774... | tar -tvf -  # rc=0
tar -xOf fix-git.tar blobs/sha256/cc774... | tar -C /tmp/tb21_layer_probe_fix_git -xf - app/resources/patch_files  # rc=0

# Load attempts
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/llm-inference-batching-scheduler.tar  # rc=0
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar /tmp/tb21_fix_git_load_probe.tar  # rc=0
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i /tmp/tb21_fix_git_load_probe.tar  # rc=1, unlinkat /app/resources/patch_files: input/output error
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/llm-inference-batching-scheduler:20260425  # rc=0
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/fix-git:20260425  # rc=1
rm -f /tmp/tb21_fix_git_load_probe.tar  # rc=0

# Logs/tooling
tail -n 240 /tmp/rl/dockerd.log  # rc=0
grep -nE 'fix-git|patch_files|unlinkat|input/output|failed|error|invalid|extract|apply' /tmp/rl/dockerd.log  # rc=0
journalctl --user -u docker --no-pager -n 80  # rc=0, no entries
journalctl -u docker --no-pager -n 80  # rc=0, system Docker logs only
command -v ctr docker nerdctl podman buildah skopeo  # ctr/docker present only
```
