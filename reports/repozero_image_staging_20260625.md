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

## Executive Result

`dev` has an approved Docker-based staging path in principle: Docker 26.1.3 is installed, the Docker daemon is reachable, and the shared target root exists.

Staging is not feasible in the current `dev` state because GHCR denies access to the exact tag:

```text
ghcr.io/jessezzzzz/repoarena-new:latest
Head "https://ghcr.io/v2/jessezzzzz/repoarena-new/manifests/latest": denied: denied
```

The worker still does not have the image in rootless Docker, and the shared RepoZero target directory is empty. No tar was staged in this lane.

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

The manifest intentionally uses the tag `ghcr.io/jessezzzzz/repoarena-new:latest`, not a digest, because the registry manifest could not be read with current `dev` credentials.

## Evidence

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

### `dev` image and registry check

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

Interpretation: storage is adequate for a normal image tar, but the exact GHCR tag is neither cached locally nor readable with current credentials.

### GHCR auth and pull probe on `dev`

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

Interpretation: GHCR is reachable from `dev`; the blocker is authorization for this package/tag, not basic network or Docker-daemon availability.

### Shared tar search

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

Interpretation: no matching shared RepoZero image tar/checksum is currently available in the checked roots.

### Worker rootless check

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

Interpretation: the worker remains blocked until a tar is staged and loaded through the rootless Docker socket.

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
- `dev` GHCR access for the exact tag: blocked by authorization.
- Shared tar/checksum: absent.
- Worker rootless image: absent.
- RepoZero benchmark: not run.
- Next required action: provide GHCR credentials authorized for `ghcr.io/jessezzzzz/repoarena-new:latest`, or stage the tar from another internet-enabled host and place it at the fixed target paths above.
