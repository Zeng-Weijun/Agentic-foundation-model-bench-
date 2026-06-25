# RepoZero Worker Load Verification - 2026-06-25

## Scope

- Lane: `surface:55` RepoZero verification.
- Repo: `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Required image: `ghcr.io/jessezzzzz/repoarena-new:latest`.
- Shared asset directory: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero`.
- Worker endpoint used exactly: `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.
- Worker Docker socket: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.

No local `ssh worker` alias was used. No token was printed. No RepoZero benchmark was run. No `docker load` was run because `docker image inspect` already found the image. `scripts/check_rootless_docker_worker.sh --restart-if-down` was not run because `docker info` succeeded on the first worker verification.

## Final Status

| Check | Status | Evidence |
| --- | --- | --- |
| Shared tar | present | `repoarena-new_latest.tar`, `1.2G`, `1242024448` bytes, mode `0600`. |
| Shared checksum | present | `repoarena-new_latest.tar.sha256`, sha256 `06195ec45e6ac02b3c7256f5fcfdacb280612abfc4a820cee5af6d66eb5ea342`. |
| Shared docker inspect metadata | present | `repoarena-new_latest.docker-inspect.json`, image id `sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c`. |
| Shared registry manifest metadata | present | `repoarena-new_latest.manifest.json`, schema `2`, media type `application/vnd.docker.distribution.manifest.v2+json`, layer count `2`. |
| Worker checksum | pass | `repoarena-new_latest.tar: OK`, `sha256sum_rc=0`. |
| Worker Docker daemon | healthy | Docker server `26.1.3`, root `/tmp/rl/data`, security includes `rootless`, `docker_info_rc=0`. |
| Worker image | present | `docker image inspect` rc `0`; `docker image ls` shows `ghcr.io/jessezzzzz/repoarena-new:latest e01d5505ea76 1.2GB`. |

Final RepoZero offline asset state: `present`.

## Commands And Exit Codes

### Workflow preflight and repo entry

Command:

```bash
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Exit code: `0`.

Command:

```bash
cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd && sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Exit code: `0`.

Command:

```bash
sed -n '621,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Exit code: `0`.

### Local helper boundary check

Command:

```bash
if test -f scripts/check_rootless_docker_worker.sh; then
  ls -l scripts/check_rootless_docker_worker.sh
  sed -n '1,260p' scripts/check_rootless_docker_worker.sh
else
  echo 'scripts/check_rootless_docker_worker.sh=MISSING'
fi
```

Exit code: `0`.

Observed:

```text
-rwxr-xr-x@ 1 Zhuanz1 staff 6001 Jun 25 21:50 scripts/check_rootless_docker_worker.sh
WORKER_SSH default: ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
```

The helper was only inspected. It was not run because the worker Docker daemon was healthy.

### Shared asset inspection from `dev`

First attempt:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<asset listing plus inline Python metadata summary>'
```

Exit code: `1`.

Outcome: file listing succeeded, then the inline Python metadata summary failed due shell quoting in the command text. No remote state was changed. The corrected commands below were used for the actual evidence.

Corrected command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'bash -s' <<'REMOTE'
set -euo pipefail
ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
DIR=$ROOT/images/repozero
TAR=$DIR/repoarena-new_latest.tar
SHA=$TAR.sha256
INSPECT=$DIR/repoarena-new_latest.docker-inspect.json
MANIFEST=$DIR/repoarena-new_latest.manifest.json
printf 'host=%s\n' "$(hostname)"
printf 'dir=%s\n' "$DIR"
ls -la "$DIR"
for f in "$TAR" "$SHA" "$INSPECT" "$MANIFEST"; do
  if test -f "$f"; then
    ls -lh "$f"
  else
    echo "MISSING $f"
  fi
done
echo '--- sha file ---'
sed -n '1,5p' "$SHA"
echo '--- dev sha256sum -c ---'
(cd "$DIR" && sha256sum -c repoarena-new_latest.tar.sha256)
REMOTE
```

Exit code: `0`.

Observed:

```text
host=zwj2
dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
repoarena-new_latest.docker-inspect.json 2.5K
repoarena-new_latest.manifest.json 667
repoarena-new_latest.tar 1.2G
repoarena-new_latest.tar.sha256 91
06195ec45e6ac02b3c7256f5fcfdacb280612abfc4a820cee5af6d66eb5ea342  repoarena-new_latest.tar
repoarena-new_latest.tar: OK
```

Metadata summary command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'bash -s' <<'REMOTE'
set -euo pipefail
DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
INSPECT=$DIR/repoarena-new_latest.docker-inspect.json
MANIFEST=$DIR/repoarena-new_latest.manifest.json
python3 - "$INSPECT" "$MANIFEST" <<'PY'
import json, sys
inspect_path, manifest_path = sys.argv[1:3]
inspect_data = json.load(open(inspect_path))
image = inspect_data[0] if isinstance(inspect_data, list) else inspect_data
manifest = json.load(open(manifest_path))
print('inspect_type=' + type(inspect_data).__name__)
print('inspect_id=' + str(image.get('Id')))
print('inspect_repo_tags=' + ','.join(image.get('RepoTags') or []))
print('inspect_repo_digests=' + ','.join(image.get('RepoDigests') or []))
print('inspect_size=' + str(image.get('Size')))
print('inspect_created=' + str(image.get('Created')))
print('manifest_type=' + type(manifest).__name__)
print('manifest_schemaVersion=' + str(manifest.get('schemaVersion') if isinstance(manifest, dict) else None))
print('manifest_mediaType=' + str(manifest.get('mediaType') if isinstance(manifest, dict) else None))
print('manifest_layer_count=' + str(len(manifest.get('layers') or []) if isinstance(manifest, dict) else 0))
PY
REMOTE
```

Exit code: `0`.

Observed:

```text
inspect_type=list
inspect_id=sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c
inspect_repo_tags=ghcr.io/jessezzzzz/repoarena-new:latest
inspect_repo_digests=ghcr.io/jessezzzzz/repoarena-new@sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3
inspect_size=1202432176
inspect_created=2026-05-12T12:09:31.955510342Z
manifest_type=dict
manifest_schemaVersion=2
manifest_mediaType=application/vnd.docker.distribution.manifest.v2+json
manifest_layer_count=2
```

### Worker checksum and image persistence verification

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
DIR=$ROOT/images/repozero
IMAGE=ghcr.io/jessezzzzz/repoarena-new:latest
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
status=0
printf 'host=%s\n' "$(hostname)"
printf 'docker_host=%s\n' "$DOCKER_HOST"
printf 'dir=%s\n' "$DIR"
echo '--- files ---'
ls -la "$DIR" || status=1
for f in repoarena-new_latest.tar repoarena-new_latest.tar.sha256 repoarena-new_latest.docker-inspect.json repoarena-new_latest.manifest.json; do
  if test -f "$DIR/$f"; then
    ls -lh "$DIR/$f"
  else
    echo "MISSING $DIR/$f"
    status=1
  fi
done
echo '--- worker sha256sum -c ---'
(cd "$DIR" && sha256sum -c repoarena-new_latest.tar.sha256)
sha_rc=$?
echo "sha256sum_rc=$sha_rc"
[ "$sha_rc" -eq 0 ] || status=1
echo '--- docker info ---'
timeout 30 docker info --format 'server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}}' 2>&1
docker_info_rc=$?
echo "docker_info_rc=$docker_info_rc"
[ "$docker_info_rc" -eq 0 ] || status=1
echo '--- docker image inspect ---'
timeout 60 docker image inspect "$IMAGE" --format 'id={{.Id}} size={{.Size}} repo_tags={{json .RepoTags}} repo_digests={{json .RepoDigests}} created={{.Created}}' 2>&1
inspect_rc=$?
echo "image_inspect_rc=$inspect_rc"
[ "$inspect_rc" -eq 0 ] || status=1
echo '--- docker image ls exact ---'
timeout 60 docker image ls ghcr.io/jessezzzzz/repoarena-new --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' 2>&1
list_rc=$?
echo "image_list_rc=$list_rc"
[ "$list_rc" -eq 0 ] || status=1
echo "overall_status=$status"
exit "$status"
REMOTE
```

Exit code: `0`.

Observed:

```text
host=zwj2-64rlk-3469265-worker-0
docker_host=unix:///tmp/rl/run/docker.sock
dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero
repoarena-new_latest.docker-inspect.json 2.5K
repoarena-new_latest.manifest.json 667
repoarena-new_latest.tar 1.2G
repoarena-new_latest.tar.sha256 91
repoarena-new_latest.tar: OK
sha256sum_rc=0
server=26.1.3 images=240 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"]
docker_info_rc=0
id=sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c size=1202432176 repo_tags=["ghcr.io/jessezzzzz/repoarena-new:latest"] repo_digests=[] created=2026-05-12T12:09:31.955510342Z
image_inspect_rc=0
ghcr.io/jessezzzzz/repoarena-new:latest e01d5505ea76 1.2GB
image_list_rc=0
overall_status=0
```

Worker `RepoDigests` is empty after local tar load, but the image id and tag match the staged inspect metadata. The staged metadata file records the source digest `ghcr.io/jessezzzzz/repoarena-new@sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3`.

## Actions Not Taken

- Did not run `docker load`: worker `docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest` returned rc `0`.
- Did not run `scripts/check_rootless_docker_worker.sh --restart-if-down`: worker `docker info` returned rc `0`.
- Did not run RepoZero benchmark.
- Did not commit or push.
