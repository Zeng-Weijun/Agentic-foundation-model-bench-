# P0 Harbor Worker Rootless Guard - 2026-06-25

## Scope

- Lane: `surface:55` worker rootless guard.
- Repo: `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Worker endpoint used exactly: `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.
- P0 Harbor / registry endpoint: `100.97.118.137:8555`.
- Smoke image ref: `100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df`.

No `/clear`, commit, push, token print, daemon restart, or data deletion was performed. The only Docker mutation attempted was the requested safe `docker pull`; it failed before changing state. The `docker run` smoke used `--rm --network none` against an already cached digest.

## Final Guard Result

| Guard | Status | Evidence |
| --- | --- | --- |
| Required `DOCKER_HOST` | pass | `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`; default `/var/run/docker.sock` absent; rootless socket present at `/tmp/rl/run/docker.sock`. |
| Registry CA source | pass | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt` exists, sha256 `dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17`. |
| `/etc/docker/certs.d` CA | pass | `/etc/docker/certs.d/100.97.118.137:8555/ca.crt` exists and matches source. |
| `/root/.config/docker/certs.d` CA | pass | `/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt` exists and matches source. |
| `/tmp/rl/data/certs.d` CA | pass | `/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt` exists and matches source. |
| Shared checkout rootless script sync | pass | Local, `dev`, and worker shared checkout script sha256 all equal `44ff505eaf9fd5bfd632d060f8e0cde78983de8509f56f3b581c67df242ccb48`; line 89 contains `--config-file=/dev/null`. |
| Live daemon uses `--config-file=/dev/null` | fail | Active `rootlesskit` / `dockerd` command lines do not include `--config-file=/dev/null`; grep rc `1`. |
| `docker info` | pass | server `26.1.3`, root `/tmp/rl/data`, security includes `rootless`, rc `0`. |
| `docker images` | pass | cached smoke digest present before and after pull attempt, rc `0`. |
| `docker pull` from P0 Harbor | fail | rc `1`: `dial tcp 100.97.118.137:8555: connect: network is unreachable`. |
| Worker shell reachability to P0 Harbor | pass | `curl --cacert "$CERT" https://100.97.118.137:8555/v2/` returned `HTTP/1.1 200 OK`, rc `0`. |
| `docker run --rm --network none` | pass for cached image | returned `Python 3.10.12`, rc `0`. |

Conclusion: worker-j9jjd can run the cached P0 smoke image, but the active rootless Docker daemon is not registry-pull ready. The shared checkout has the intended `--config-file=/dev/null` guard, but the running daemon predates or bypasses it.

## Commands And Exit Codes

### Workflow Preflight

Command:

```bash
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd
```

Exit code: `0`.

Command:

```bash
sed -n '261,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Exit code: `0`.

Command:

```bash
sed -n '761,1100p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Exit code: `0`.

### Local And Shared Script Sync

Command:

```bash
git status --short -- scripts/check_rootless_docker_worker.sh reports/p0_harbor_worker_guard_20260625.md
nl -ba scripts/check_rootless_docker_worker.sh | sed -n '70,105p'
sha256sum scripts/check_rootless_docker_worker.sh
```

Exit code: `0`.

Observed:

```text
89	      --config-file=/dev/null \
44ff505eaf9fd5bfd632d060f8e0cde78983de8509f56f3b581c67df242ccb48  scripts/check_rootless_docker_worker.sh
```

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
SHARED=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
ls -l "$SHARED"
sha256sum "$SHARED"
grep -n -- "--config-file=/dev/null" "$SHARED" || true
nl -ba "$SHARED" | sed -n "82,96p"'
```

Exit code: `0`.

Observed:

```text
host=zwj2
-rwxr-xr-x 1 root root 6033 Jun 25 22:44 /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
44ff505eaf9fd5bfd632d060f8e0cde78983de8509f56f3b581c67df242ccb48  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
89:      --config-file=/dev/null \
```

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'set -euo pipefail
SHARED=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
ls -l "$SHARED"
sha256sum "$SHARED"
grep -n -- "--config-file=/dev/null" "$SHARED" || true'
```

Exit code: `0`.

Observed:

```text
host=zwj2-64rlk-3469265-worker-0
-rwxr-xr-x 1 root root 6033 Jun 25 22:44 /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
44ff505eaf9fd5bfd632d060f8e0cde78983de8509f56f3b581c67df242ccb48  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/check_rootless_docker_worker.sh
89:      --config-file=/dev/null \
```

### Worker Certs, Docker Info, Images, Pull, Run

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
REG=100.97.118.137:8555
NAME=swe-data-harness/repo2env-pallets-click-f6299c4
REF="$REG/$NAME@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df"
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
status=0
printf 'date=%s\n' "$(date -Is)"
printf 'host=%s\n' "$(hostname)"
printf 'reg=%s\n' "$REG"
printf 'ref=%s\n' "$REF"
printf 'docker_host=%s\n' "$DOCKER_HOST"
printf 'default_docker_sock='; if test -S /var/run/docker.sock; then echo present; else echo absent; fi
printf 'rootless_docker_sock='; if test -S /tmp/rl/run/docker.sock; then ls -l /tmp/rl/run/docker.sock; else echo absent; status=1; fi
printf 'openssl='; command -v openssl || true
printf 'docker='; command -v docker || { status=1; true; }
echo '--- cert source ---'
if test -f "$CERT"; then
  ls -lh "$CERT"
  sha256sum "$CERT"
  if command -v openssl >/dev/null 2>&1; then
    openssl x509 -in "$CERT" -noout -subject -issuer -dates -fingerprint -sha256 2>&1
    cert_src_rc=$?
  else
    cert_src_rc=127
  fi
else
  echo "MISSING $CERT"
  cert_src_rc=1
  status=1
fi
echo "cert_source_rc=$cert_src_rc"
[ "$cert_src_rc" -eq 0 ] || status=1
for base in /etc/docker/certs.d /root/.config/docker/certs.d /tmp/rl/data/certs.d; do
  path="$base/$REG/ca.crt"
  echo "--- cert path $path ---"
  if test -f "$path"; then
    ls -lh "$path"
    sha256sum "$path"
    if test -f "$CERT" && cmp -s "$CERT" "$path"; then echo 'matches_source=yes'; else echo 'matches_source=no'; status=1; fi
    if command -v openssl >/dev/null 2>&1; then
      openssl x509 -in "$path" -noout -subject -issuer -dates -fingerprint -sha256 2>&1
      cert_rc=$?
    else
      cert_rc=127
    fi
  else
    echo "MISSING $path"
    cert_rc=1
    status=1
  fi
  echo "cert_path_rc=$cert_rc"
  [ "$cert_rc" -eq 0 ] || status=1
done
echo '--- docker info ---'
timeout 45 docker info --format 'server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}} cgroup={{.CgroupDriver}}/{{.CgroupVersion}}' 2>&1
docker_info_rc=$?
echo "docker_info_rc=$docker_info_rc"
[ "$docker_info_rc" -eq 0 ] || status=1
echo '--- docker images before pull ---'
timeout 60 docker images --digests --format '{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}} {{.Size}}' "$REG/$NAME" 2>&1
docker_images_before_rc=$?
echo "docker_images_before_rc=$docker_images_before_rc"
[ "$docker_images_before_rc" -eq 0 ] || status=1
echo '--- docker pull digest ---'
timeout 300 docker pull "$REF" 2>&1
docker_pull_rc=$?
echo "docker_pull_rc=$docker_pull_rc"
[ "$docker_pull_rc" -eq 0 ] || status=1
echo '--- docker image inspect digest ---'
timeout 60 docker image inspect "$REF" --format 'id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}} size={{.Size}} created={{.Created}}' 2>&1
inspect_rc=$?
echo "docker_inspect_rc=$inspect_rc"
[ "$inspect_rc" -eq 0 ] || status=1
echo '--- docker images after pull ---'
timeout 60 docker images --digests --format '{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}} {{.Size}}' "$REG/$NAME" 2>&1
docker_images_after_rc=$?
echo "docker_images_after_rc=$docker_images_after_rc"
[ "$docker_images_after_rc" -eq 0 ] || status=1
echo '--- docker run network none smoke ---'
timeout 180 docker run --rm --network none "$REF" /bin/sh -lc 'python --version 2>/dev/null || python3 --version 2>/dev/null || echo shell-ok' 2>&1
run_rc=$?
echo "docker_run_rc=$run_rc"
[ "$run_rc" -eq 0 ] || status=1
echo "overall_status=$status"
exit "$status"
REMOTE
```

Exit code: `1`.

Important observed output:

```text
date=2026-06-25T23:06:06+08:00
host=zwj2-64rlk-3469265-worker-0
docker_host=unix:///tmp/rl/run/docker.sock
default_docker_sock=absent
rootless_docker_sock=srw-rw---T 1 root 100112 0 Jun 25 22:31 /tmp/rl/run/docker.sock
openssl=/bin/openssl
docker=/bin/docker
```

Cert source:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
subject=CN = 100.97.118.137
issuer=CN = 100.97.118.137
notBefore=Jun 25 14:28:22 2026 GMT
notAfter=Jun 22 14:28:22 2036 GMT
sha256 Fingerprint=E2:17:1D:D4:C4:30:47:B0:56:54:F7:E4:8F:42:70:1C:85:86:15:74:92:58:B4:6D:A0:FE:6F:5A:5A:7B:53:5C
cert_source_rc=0
```

All three required cert paths:

```text
/etc/docker/certs.d/100.97.118.137:8555/ca.crt
/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt
/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt
```

Each path existed, sha256 was `dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17`, `matches_source=yes`, and `cert_path_rc=0`.

Docker results:

```text
server=26.1.3 images=240 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"] cgroup=none/1
docker_info_rc=0

100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4 <none> sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df f6299c4c6dc0 348MB
docker_images_before_rc=0

Error response from daemon: Get "https://100.97.118.137:8555/v2/": dial tcp 100.97.118.137:8555: connect: network is unreachable
docker_pull_rc=1

id=sha256:f6299c4c6dc0c2b27c5a4872c1f12b417b9351f6a32754e0226d84ce38ad7be7 tags=[] digests=["100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df"] size=348174514 created=2026-06-16T03:42:21.6175305Z
docker_inspect_rc=0

Python 3.10.12
docker_run_rc=0
overall_status=1
```

### Worker Shell Registry Reachability

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
REG=100.97.118.137:8555
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
ip route get 100.97.118.137 || true
timeout 20 curl --cacert "$CERT" -fsS -D - https://$REG/v2/ -o /tmp/p0_registry_v2.out
timeout 20 curl -k -fsS -D - https://$REG/v2/ -o /tmp/p0_registry_v2_insecure.out
rm -f /tmp/p0_registry_v2.out /tmp/p0_registry_v2_insecure.out
REMOTE
```

Exit code: `0`.

Observed:

```text
100.97.118.137 dev eth0 src 100.102.19.118 uid 0
HTTP/1.1 200 OK
Docker-Distribution-Api-Version: registry/2.0
curl_ca_rc=0
HTTP/1.1 200 OK
Docker-Distribution-Api-Version: registry/2.0
curl_insecure_rc=0
overall_status=0
```

Interpretation: the worker shell can reach P0 Harbor with the installed CA; the failed pull is specific to the active rootless Docker daemon path.

### Live Rootless Daemon Guard State

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
ps -eo pid,ppid,stat,etime,comm,args | awk 'BEGIN{IGNORECASE=1} $5 ~ /^(rootlesskit|dockerd|containerd|containerd-shim|runc|slirp4netns)$/ {print}'
if ps -eo args | grep -F -- '--config-file=/dev/null' | grep -v grep; then flag_rc=0; else flag_rc=1; fi
echo "live_config_file_flag_rc=$flag_rc"
for pid in $(pgrep -x dockerd 2>/dev/null || true); do
  echo "dockerd_pid=$pid"
  tr '\0' '\n' < /proc/$pid/environ | grep -E '^(HTTP|HTTPS|NO|http|https|no)_proxy=' || true
done
tail -n 240 /tmp/rl/dockerd.log 2>/dev/null | grep -E '100\.97\.118\.137|8555|network is unreachable|x509|certificate|Docker daemon|API listen|config-file|Processing signal|failed|panic' || true
REMOTE
```

Exit code: `0`.

Observed:

```text
rootlesskit command includes dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
dockerd command includes dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
live_config_file_flag_rc=1
dockerd_pid=284167
no_proxy=10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn
https_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
http_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
Error getting v2 registry: Get "https://100.97.118.137:8555/v2/": dial tcp 100.97.118.137:8555: connect: network is unreachable
```

Interpretation: the shared script is synced with `--config-file=/dev/null`, but the active daemon was not launched from the synced command. It also carries proxy environment. No restart was attempted in this lane.

## Recommended Runner Gate

Before scheduling a Docker-backed bench shard on `worker-j9jjd`, the runner should fail closed unless all required gates below pass:

1. Set `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`; fail if `/var/run/docker.sock` is the only Docker socket or if `/tmp/rl/run/docker.sock` is absent.
2. Verify P0 Harbor CA parity:
   - source: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt`
   - worker copies:
     - `/etc/docker/certs.d/100.97.118.137:8555/ca.crt`
     - `/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt`
     - `/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt`
   - require all three to match source sha256.
3. Verify shared checkout script hash and `--config-file=/dev/null` line before invoking rootless health tooling.
4. Verify the live daemon command line contains `--config-file=/dev/null`. If absent, mark `rootless_daemon_guard_stale` and require a controlled daemon restart outside the bench run. Do not silently continue for uncached images.
5. Run `docker info` and `docker images --digests` for the exact registry repository.
6. Run `docker pull "$image_ref"` by digest. This is the registry distribution gate. Current worker result is `FAIL` with `network is unreachable`.
7. If `docker pull` fails but `docker image inspect "$image_ref"` and the configured `docker run --rm --network none "$image_ref" <smoke command>` pass, mark only `cached_image_ready=true` and `registry_pull_ready=false`. This is acceptable for a cache-confirmation smoke but not for a new-image scheduling path.
8. If pull and cached inspect both fail, use the fallback tar path only after checksum verification, then run the same `--network none` smoke.

Current runner decision for this worker: allow only cached-image smokes for the verified digest; do not rely on P0 Harbor pull for fresh image distribution until the active rootless daemon is restarted under the synced guard and `docker pull` passes.
