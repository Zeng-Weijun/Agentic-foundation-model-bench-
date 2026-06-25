# RepoZero Image Staging Report - 2026-06-25

## Scope

- Lane: RepoZero image staging/manifest.
- Required image: `ghcr.io/jessezzzzz/repoarena-new:latest`.
- Target shared asset directory: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero`.
- Worker Docker socket: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
- Hosts used: local Mac control plane, `dev`, and worker `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.
- Hosts not used: `swe_dev`, `swe-dev`, `swe_dev2`.
- Worker public internet: not used.
- RepoZero benchmark: not run.

## Current Result

`dev` now has GHCR access for the exact image after the token follow-up, and the RepoZero Docker image has been staged into the shared offline asset root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar.sha256
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.docker-inspect.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.manifest.json
```

The worker loaded the image from the shared tar. The rootless Docker daemon dropped after the `docker load` step, but the image persisted under `/tmp/rl/data`; after `scripts/check_rootless_docker_worker.sh --restart-if-down`, `docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest` succeeds on worker.

The rootless caveat remains: `docker info`, `docker ps`, `docker images`, and this loader path work, but the Docker `/version` endpoint still fails, so Python Docker SDK version negotiation remains broken.

The original pre-token blocker was:

```text
ghcr.io/jessezzzzz/repoarena-new:latest
Head "https://ghcr.io/v2/jessezzzzz/repoarena-new/manifests/latest": denied: denied
```

That blocker is no longer the current state for this image.

## Fixed Offline Contract

The offline image manifest is fixed in:

```text
manifests/offline_images.repozero.yaml
```

Expected staged files, once an authorized internet-enabled staging host pulls the image:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar.sha256
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.docker-inspect.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.manifest.json
```

The manifest now records both the tag and observed registry/image identifiers:

```text
registry manifest digest: sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3
docker image id:          sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c
```

## Evidence

### GHCR token follow-up and staging on `dev`

The token value is intentionally not recorded here. It is stored on `dev` in a `chmod 600` env file and was used only for `docker login ghcr.io`.

Staging log:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/repozero_stage_20260625_2158.log
```

Observed in the staging log:

```text
started=2026-06-25T22:27:15+08:00
host=zwj2
repo_head=570c5f5
mode:        execute
Digest: sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3
Status: Downloaded newer image for ghcr.io/jessezzzzz/repoarena-new:latest
Staged RepoZero image tar:
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar.sha256
finished=2026-06-25T22:28:47+08:00
```

Shared directory after staging:

```text
repoarena-new_latest.docker-inspect.json  2.5K
repoarena-new_latest.manifest.json        667
repoarena-new_latest.tar                  1.2G
repoarena-new_latest.tar.sha256           91
```

Checksum on `dev`:

```text
repoarena-new_latest.tar: OK
```

Metadata check:

```text
repoarena-new_latest.manifest.json keys: config,layers,mediaType,schemaVersion
repoarena-new_latest.docker-inspect.json Id: sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c
repoarena-new_latest.docker-inspect.json RepoTags: ghcr.io/jessezzzzz/repoarena-new:latest
```

### Worker load and post-load persistence

Worker load log:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/repozero_worker_load_20260625_2231.log
```

Observed in the worker load log:

```text
started=2026-06-25T22:30:52+08:00
host=zwj2-64rlk-3469265-worker-0
repo_head=570c5f5
repoarena-new_latest.tar: OK
Mode: load
Summary: present=0 missing=0 loaded=1 skipped=0 tar_missing=0 errors=0
- repozero_py2js_repoarena_runtime: loaded
Cannot connect to the Docker daemon at unix:///tmp/rl/run/docker.sock. Is the docker daemon running?
```

Interpretation: the loader completed the `docker load`, but the rootless daemon dropped before the trailing `docker image inspect` in the surrounding smoke command.

After running:

```bash
WORKER_SSH='ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  scripts/check_rootless_docker_worker.sh --restart-if-down
```

Observed guard summary:

```text
restart_skipped=docker_info_ok
docker_info_rc=0
docker_version_rc=1
raw_version_rc=52
docker_ps_rc=0
docker_images_rc=0
compose_version_rc=0
compose_ps_rc=0
python_docker_version_rc=1
```

Worker image inspect after guard:

```text
info_ok server=26.1.3 images=240 root=/tmp/rl/data
worker_repozero_present id=sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c size=1202432176 repo_tags=["ghcr.io/jessezzzzz/repoarena-new:latest"]
ghcr.io/jessezzzzz/repoarena-new:latest e01d5505ea76 1.2GB
```

Offline loader check on worker:

```bash
scripts/load_offline_images.sh \
  --manifest manifests/offline_images.repozero.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --check
```

Exit code: `0`.

Observed:

```text
Summary: present=1 missing=0 loaded=0 skipped=1 tar_missing=0 errors=0
- repozero_py2js_repoarena_runtime: present
```

### Tooling on `dev`

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
source ~/.bashrc >/dev/null 2>&1 || true
printf "host=%s\n" "$(hostname)"
for t in docker skopeo podman buildah ctr nerdctl oras crane sha256sum gzip zstd; do
  if command -v "$t" >/dev/null 2>&1; then printf "%s=%s\n" "$t" "$(command -v "$t")"; else printf "%s=MISSING\n" "$t"; fi
done
test -d /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench && echo shared_target_parent=exists
docker version --format "client={{.Client.Version}} server={{.Server.Version}}"
docker info --format "server={{.ServerVersion}} root={{.DockerRootDir}} storage={{.Driver}} cgroup={{.CgroupDriver}}"'
```

Exit code: `0`.

Observed:

```text
host=zwj2
docker=/usr/bin/docker
skopeo=MISSING
podman=MISSING
buildah=MISSING
ctr=/usr/bin/ctr
nerdctl=MISSING
oras=MISSING
crane=MISSING
sha256sum=/usr/bin/sha256sum
gzip=/usr/bin/gzip
zstd=MISSING
shared_target_parent=exists
client=26.1.3 server=26.1.3
server=26.1.3 root=/mnt/docker_root_swebench_800g storage=overlay2 cgroup=cgroupfs
```

Interpretation: Docker is the only practical staging tool currently available on `dev`.

### Pre-token `dev` image and registry check

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
source ~/.bashrc >/dev/null 2>&1 || true
IMAGE=ghcr.io/jessezzzzz/repoarena-new:latest
TARGET_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
mkdir -p "$TARGET_DIR"
ls -la "$TARGET_DIR"
df -h "$TARGET_DIR" /mnt/docker_root_swebench_800g /data/tmp 2>/dev/null || true
if docker image inspect "$IMAGE" >/tmp/repozero.inspect.$$ 2>/tmp/repozero.inspect.err.$$; then
  echo local_present=yes
else
  echo local_present=no
  sed -n "1,20p" /tmp/repozero.inspect.err.$$ || true
fi
rm -f /tmp/repozero.inspect.$$ /tmp/repozero.inspect.err.$$
if timeout 120 docker manifest inspect "$IMAGE" >/tmp/repozero.manifest.$$ 2>/tmp/repozero.manifest.err.$$; then
  echo manifest_access=yes
else
  rc=$?
  echo manifest_access=no rc=$rc
  sed -n "1,80p" /tmp/repozero.manifest.err.$$ || true
fi
rm -f /tmp/repozero.manifest.$$ /tmp/repozero.manifest.err.$$'
```

Exit code: `0`.

Observed:

```text
target_dir exists and is empty
kataShared 50T total, 15T available
/mnt/docker_root_swebench_800g on / has 34G available
/data/tmp has 45G available
local_present=no
Error response from daemon: No such image: ghcr.io/jessezzzzz/repoarena-new:latest
manifest_access=no rc=1
Get "https://ghcr.io/v2/jessezzzzz/repoarena-new/manifests/latest": denied: denied
```

Interpretation at the time of this pre-token probe: storage was adequate for a normal image tar, but the exact GHCR tag was neither cached locally nor readable with the then-current credentials.

### Pre-token GHCR auth and pull probe on `dev`

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
source ~/.bashrc >/dev/null 2>&1 || true
IMAGE=ghcr.io/jessezzzzz/repoarena-new:latest
python3 - <<'"'"'PY'"'"'
import json, pathlib
p = pathlib.Path.home() / ".docker/config.json"
print("docker_config_exists=" + str(p.exists()).lower())
if p.exists():
    data = json.loads(p.read_text())
    auths = data.get("auths") or {}
    helpers = data.get("credHelpers") or {}
    print("auth_hosts=" + ",".join(sorted(auths.keys())))
    print("cred_helper_hosts=" + ",".join(sorted(helpers.keys())))
    print("ghcr_auth_present=" + str(any("ghcr.io" in k for k in auths)).lower())
    print("ghcr_helper_present=" + str(any("ghcr.io" in k for k in helpers)).lower())
PY
timeout 30 curl -fsSIL https://ghcr.io/v2/ 2>&1 | sed -n "1,20p" || true
if timeout 120 docker pull "$IMAGE" >/tmp/repozero.pull.$$ 2>/tmp/repozero.pull.err.$$; then
  echo pull_probe=ok
else
  rc=$?
  echo pull_probe=failed rc=$rc
  sed -n "1,80p" /tmp/repozero.pull.err.$$ || true
fi
rm -f /tmp/repozero.pull.$$ /tmp/repozero.pull.err.$$'
```

Exit code: `0`.

Observed:

```text
docker_config_exists=true
auth_hosts=ghcr.io,registry.h.pjlab.org.cn
cred_helper_hosts=
ghcr_auth_present=true
ghcr_helper_present=false
HTTP/1.1 405 Method Not Allowed
docker-distribution-api-version: registry/2.0
pull_probe=failed rc=1
Error response from daemon: Head "https://ghcr.io/v2/jessezzzzz/repoarena-new/manifests/latest": denied: denied
```

Interpretation at the time of this pre-token probe: GHCR was reachable from `dev`; the blocker was authorization for this package/tag, not basic network or Docker-daemon availability.

### Pre-token shared tar search

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
TARGET_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
find "$TARGET_DIR" \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/repozero \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval \
  -maxdepth 6 -type f \( -iname "*repoarena*.tar" -o -iname "*repoarena*.tar.gz" -o -iname "*repozero*.tar" -o -iname "*repozero*.tar.gz" -o -iname "*.sha256" \) \
  2>/dev/null | sort | sed -n "1,200p"'
```

Exit code: `0`.

Observed: no output.

Interpretation at the time of this pre-token probe: no matching shared RepoZero image tar/checksum was available in the checked roots.

### Pre-token worker rootless check

Command:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
IMAGE=ghcr.io/jessezzzzz/repoarena-new:latest
TARGET_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
printf "host=%s\n" "$(hostname)"
printf "docker_host=%s\n" "$DOCKER_HOST"
test -d "$TARGET_DIR" && echo target_dir=exists || echo target_dir=missing
ls -la "$TARGET_DIR" 2>/dev/null || true
if docker image inspect "$IMAGE" >/dev/null 2>&1; then echo worker_image_present=yes; else echo worker_image_present=no; fi'
```

Exit code: `0`.

Observed:

```text
host=zwj2-64rlk-3469265-worker-0
docker_host=unix:///tmp/rl/run/docker.sock
target_dir=exists
total 1
drwxr-xr-x 2 root root 1024 Jun 25 21:38 .
drwxr-xr-x 3 root root 1024 Jun 25 21:38 ..
worker_image_present=no
```

Interpretation at the time of this pre-token probe: the worker was blocked until a tar was staged and loaded through the rootless Docker socket.

## Staging Commands For An Authorized Host

Use this path on `dev` after fixing GHCR credentials, or on another internet-enabled Linux staging host that can see the shared filesystem:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
docker login ghcr.io
IMAGE_REF='ghcr.io/jessezzzzz/repoarena-new:latest' \
ASSET_ROOT='/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench' \
bash scripts/stage_repozero_image.sh --execute
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
sha256sum -c images/repozero/repoarena-new_latest.tar.sha256
```

Equivalent direct commands:

```bash
IMAGE='ghcr.io/jessezzzzz/repoarena-new:latest'
TARGET_DIR='/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero'
TAR="$TARGET_DIR/repoarena-new_latest.tar"
mkdir -p "$TARGET_DIR"
docker pull "$IMAGE"
docker image inspect "$IMAGE" > "$TARGET_DIR/repoarena-new_latest.docker-inspect.json"
docker manifest inspect "$IMAGE" > "$TARGET_DIR/repoarena-new_latest.manifest.json"
tmp_tar="$TAR.tmp.$$"
docker save -o "$tmp_tar" "$IMAGE"
mv "$tmp_tar" "$TAR"
(cd "$TARGET_DIR" && sha256sum repoarena-new_latest.tar > repoarena-new_latest.tar.sha256)
```

If staging happens on an internet-enabled host without the shared filesystem mounted, write the tar/checksum locally, then copy exactly these files into:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/
```

## Worker Load Commands After Staging

Do not pull from the worker. After the tar exists, run only shared-tar checks/load on the worker:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
sha256sum -c images/repozero/repoarena-new_latest.tar.sha256
docker load -i images/repozero/repoarena-new_latest.tar
docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest >/dev/null
docker image ls ghcr.io/jessezzzzz/repoarena-new'
```

Optional loader check from the repo checkout after the tar exists:

```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock scripts/load_offline_images.sh \
  --manifest manifests/offline_images.repozero.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --check
```

## Decision

- `dev` Docker path: available.
- `dev` GHCR access for the exact tag: available after token follow-up.
- Shared tar/checksum: present and sha256 verified on `dev` and worker.
- Worker rootless image: present after `docker load` and daemon health guard.
- Worker offline loader check: `present=1 missing=0 loaded=0 skipped=1`.
- Remaining Docker blocker: `/version` endpoint still fails, so Python Docker SDK based harnesses remain unsafe until the rootless daemon build/config is fixed or the runner avoids SDK version negotiation.
- RepoZero benchmark: not run.
- Next required action: run a small RepoZero harness smoke against the preloaded image without pulling from worker public internet, and keep a daemon preflight/restart guard before each high-concurrency worker batch.
