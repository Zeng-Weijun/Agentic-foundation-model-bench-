# Next Rootless Registry Pull Debug - 2026-06-25

## Scope

- Lane: report-only rootless registry pull bug hunt.
- Repo: `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Worker endpoint used exactly: `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.
- Registry: `https://100.97.118.137:8555`.
- Docker socket: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.

No restart, delete, pull, load, build, commit, push, or token print was performed in this lane. The checks were read-only: process command lines/env, namespaces, rootlesskit API, cert paths, config files, routes, Docker info/images, and daemon logs.

## Short Finding

The failure is not explained by missing CA files, missing host route, registry downtime, or a different network namespace.

The active rootless Docker daemon is stale relative to the shared guard script:

- Shared checkout script contains `dockerd --config-file=/dev/null`.
- Live `rootlesskit` and `dockerd` command lines do not contain `--config-file=/dev/null`.
- The daemon process has the same network namespace as the shell and its `/proc/<pid>/net/route` includes a direct `100.96.0.0/12` route, but daemon logs still show `dial tcp 100.97.118.137:8555: connect: network is unreachable`.
- Worker shell can `curl --cacert "$CERT" https://100.97.118.137:8555/v2/` with `HTTP/1.1 200 OK`.
- The daemon carries Kubernetes proxy environment (`HTTP_PROXY`, `HTTPS_PROXY`) plus `NO_PROXY=10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn`.

Likely root cause: the currently running daemon was launched before the current rootless guard and remains in a stale rootless/proxy runtime state. It can serve cached image operations, but its registry client cannot route the direct P0 Harbor connection. This should be verified by a controlled daemon restart under the synced command, ideally with proxy variables explicitly removed or with an explicit `NO_PROXY` including `100.97.118.137,100.97.118.137:8555,100.96.0.0/12`.

I cannot prove the restart resolves it in this lane because pull/restart were explicitly out of scope.

## Evidence

### Workflow And Repo Entry

Command:

```bash
sed -n '1,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd
```

Exit code: `0`.

Observed repo cwd:

```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
```

### Baseline Report Read

Command:

```bash
sed -n '1,260p' reports/p0_harbor_worker_guard_20260625.md
```

Exit code: `0`.

Relevant prior baseline:

```text
Worker shell reachability to P0 Harbor: pass
docker pull from P0 Harbor: fail, rc 1, network is unreachable
docker run --rm --network none: pass for cached image
live daemon uses --config-file=/dev/null: fail
```

### Live Process, Namespace, Cert, Config, Route, And Log Check

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
REG=100.97.118.137:8555
REG_HOST=100.97.118.137
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
status=0
printf 'date=%s\n' "$(date -Is)"
printf 'host=%s\n' "$(hostname)"
printf 'docker_host=%s\n' "$DOCKER_HOST"
printf 'reg=%s\n' "$REG"
for t in docker curl ip ss nsenter readlink stat sha256sum openssl; do printf '%s=' "$t"; command -v "$t" || true; done
rootless_pids=$(pgrep -x rootlesskit 2>/dev/null | tr '\n' ' ' || true)
dockerd_pids=$(pgrep -x dockerd 2>/dev/null | tr '\n' ' ' || true)
containerd_pids=$(pgrep -x containerd 2>/dev/null | tr '\n' ' ' || true)
for pid in $rootless_pids $dockerd_pids $containerd_pids; do
  echo "pid=$pid comm=$(cat /proc/$pid/comm 2>/dev/null || true)"
  tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null; echo
done
if ps -eo args | grep -F -- '--config-file=/dev/null' | grep -v grep; then live_config_rc=0; else live_config_rc=1; fi
echo "live_config_file_flag_rc=$live_config_rc"
for pid in self 1 $rootless_pids $dockerd_pids $containerd_pids; do
  test -e /proc/$pid/ns/net || continue
  printf 'pid=%s comm=%s net=%s mnt=%s user=%s\n' "$pid" "$(cat /proc/$pid/comm 2>/dev/null || echo self)" "$(readlink /proc/$pid/ns/net 2>/dev/null)" "$(readlink /proc/$pid/ns/mnt 2>/dev/null)" "$(readlink /proc/$pid/ns/user 2>/dev/null)"
done
curl --silent --show-error --max-time 5 --unix-socket /tmp/rl/run/dockerd-rootless/api.sock http://rootlesskit/v1/info 2>&1
echo "rootlesskit_api_rc=$?"
ls -l /tmp/rl/run/docker.sock 2>&1 || { status=1; true; }
for f in "$CERT" "/etc/docker/certs.d/$REG/ca.crt" "/root/.config/docker/certs.d/$REG/ca.crt" "/tmp/rl/data/certs.d/$REG/ca.crt"; do
  echo "cert_file=$f"
  if test -f "$f"; then
    ls -lh "$f"
    sha256sum "$f"
    openssl x509 -in "$f" -noout -subject -issuer -dates -fingerprint -sha256 2>&1 | sed -n '1,8p'
    if test -f "$CERT" && cmp -s "$CERT" "$f"; then echo matches_source=yes; else echo matches_source=no; fi
  else
    echo missing=yes
    status=1
  fi
done
for f in /etc/docker/daemon.json /root/.config/docker/daemon.json /tmp/rl/data/config/daemon.json /tmp/rl/data/daemon.json /root/.docker/config.json; do
  echo "config_file=$f"
  if test -f "$f"; then
    ls -lh "$f"
    case "$f" in
      */.docker/config.json) python3 - "$f" <<'PY' 2>&1
import json, sys
p=sys.argv[1]
try:
    data=json.load(open(p))
except Exception as exc:
    print('parse_error=' + type(exc).__name__)
else:
    print('keys=' + ','.join(sorted(data.keys())))
    print('auth_hosts=' + ','.join(sorted((data.get('auths') or {}).keys())))
    print('cred_helpers=' + ','.join(sorted((data.get('credHelpers') or {}).keys())))
PY
        ;;
      *) sed -n '1,120p' "$f" ;;
    esac
  else
    echo missing=yes
  fi
done
ip route get "$REG_HOST" 2>&1
echo "route_shell_rc=$?"
timeout 20 curl --cacert "$CERT" -fsS -D - https://$REG/v2/ -o /tmp/p0_v2_shell_body.$$ 2>&1
echo "curl_shell_rc=$?"
if test -s /tmp/p0_v2_shell_body.$$; then echo body=$(cat /tmp/p0_v2_shell_body.$$); fi
rm -f /tmp/p0_v2_shell_body.$$
for pid in $dockerd_pids; do
  echo "dockerd_pid=$pid"
  nsenter -t "$pid" -n ip route get "$REG_HOST" 2>&1
  echo "nsenter_route_rc=$?"
  cat /proc/$pid/net/route 2>/dev/null | sed -n '1,12p'
done
for pid in $rootless_pids $dockerd_pids $containerd_pids; do
  echo "pid=$pid comm=$(cat /proc/$pid/comm 2>/dev/null || true)"
  tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -Ei '^(http|https|no)_proxy=' || echo no_proxy_env_lines
done
env | grep -Ei '^(http|https|no)_proxy=' || echo no_proxy_env_lines
timeout 45 docker info --format 'server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}} cgroup={{.CgroupDriver}}/{{.CgroupVersion}} http_proxy={{.HTTPProxy}} https_proxy={{.HTTPSProxy}} no_proxy={{.NoProxy}}' 2>&1
echo "docker_info_rc=$?"
timeout 45 docker images --digests --format '{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}} {{.Size}}' 100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4 2>&1
echo "docker_images_rc=$?"
tail -n 320 /tmp/rl/dockerd.log 2>/dev/null | grep -E '100\.97\.118\.137|8555|network is unreachable|proxy|Proxy|no_proxy|x509|certificate|Docker daemon|API listen|config-file|daemon\.json|Processing signal|panic|failed' || true
echo "overall_status=$status"
exit "$status"
REMOTE
```

Exit code: `0`.

Key observed output:

```text
date=2026-06-25T23:26:28+08:00
host=zwj2-64rlk-3469265-worker-0
docker_host=unix:///tmp/rl/run/docker.sock
reg=100.97.118.137:8555
rootlesskit_pids=284143
dockerd_pids=284167
containerd_pids=284187
```

Live process command lines:

```text
/tmp/rl/bin/rootlesskit --state-dir=/tmp/rl/run/dockerd-rootless --net=host --copy-up=/etc --copy-up=/run --propagation=rslave dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
dockerd --host=unix:///tmp/rl/run/docker.sock --data-root=/tmp/rl/data --exec-root=/tmp/rl/exec --iptables=false --bridge=none --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh --default-runtime sysbind --storage-driver overlay2
live_config_file_flag_rc=1
```

Namespace comparison:

```text
pid=self net=net:[4026548149] mnt=mnt:[4026548248] user=user:[4026531837]
pid=1 net=net:[4026548149] mnt=mnt:[4026548248] user=user:[4026531837]
pid=284143 rootlesskit net=net:[4026548149] mnt=mnt:[4026548248] user=user:[4026531837]
pid=284167 dockerd net=net:[4026548149] mnt=mnt:[4026547920] user=user:[4026547919]
pid=284187 containerd net=net:[4026548149] mnt=mnt:[4026547920] user=user:[4026547919]
```

Interpretation: `dockerd` is in the same network namespace as the worker shell, but a different mount/user namespace under rootlesskit.

Rootlesskit API:

```text
{"apiVersion":"1.1.1","version":"2.0.2","stateDir":"/tmp/rl/run/dockerd-rootless","childPID":284151}
rootlesskit_api_rc=0
```

Cert paths:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
/etc/docker/certs.d/100.97.118.137:8555/ca.crt
/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt
/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt
```

All four cert files had sha256:

```text
dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
```

All three worker copies reported:

```text
matches_source=yes
```

Docker config files:

```text
/etc/docker/daemon.json:
{
  "insecure-registries": [
    "registry.h.pjlab.org.cn"
  ],
  "data-root": "/mnt/docker_root_swebench_800g"
}

/root/.config/docker/daemon.json: missing
/tmp/rl/data/config/daemon.json: missing
/tmp/rl/data/daemon.json: missing
/root/.docker/config.json: keys=auths; auth_hosts=ghcr.io,registry.h.pjlab.org.cn
```

No auth values were printed.

Shell route and curl:

```text
100.97.118.137 dev eth0 src 100.102.19.118 uid 0
route_shell_rc=0
HTTP/1.1 200 OK
Docker-Distribution-Api-Version: registry/2.0
curl_shell_rc=0
body={}
```

Dockerd namespace route evidence:

```text
nsenter: reassociate to namespace 'ns/net' failed: Operation not permitted
nsenter_route_rc=1
proc_net_route:
Iface Destination Gateway Flags RefCnt Use Metric Mask
eth0 00000000 01136664 0003 0 0 0 00000000
eth0 00006064 00000000 0001 0 0 0 0000F0FF
eth0 00136664 00000000 0001 0 0 0 00FFFFFF
```

Interpretation: `nsenter` was blocked by permissions, but `/proc/<dockerd>/net/route` shows a default route and a direct `100.96.0.0/12` route from the daemon network namespace.

Proxy env propagation:

```text
rootlesskit, dockerd, containerd, and shell all include:
no_proxy=10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn
NO_PROXY=10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn
http_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
https_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
HTTP_PROXY=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
HTTPS_PROXY=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128
```

Docker read-only checks:

```text
server=26.1.3 images=240 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"] cgroup=none/1 http_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128 https_proxy=http://httpproxy-headless.kubebrain.svc.pjlab.local:3128 no_proxy=10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn
docker_info_rc=0
100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4 <none> sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df f6299c4c6dc0 348MB
docker_images_rc=0
```

Recent daemon log:

```text
time="2026-06-25T23:06:06.667055576+08:00" level=warning msg="Error getting v2 registry: Get \"https://100.97.118.137:8555/v2/\": dial tcp 100.97.118.137:8555: connect: network is unreachable"
time="2026-06-25T23:06:06.667091842+08:00" level=info msg="Attempting next endpoint for pull after error: Get \"https://100.97.118.137:8555/v2/\": dial tcp 100.97.118.137:8555: connect: network is unreachable"
time="2026-06-25T23:06:06.667568646+08:00" level=error msg="Handler for POST /v1.45/images/create returned error: Get \"https://100.97.118.137:8555/v2/\": dial tcp 100.97.118.137:8555: connect: network is unreachable"
```

### Restart Helper Shape

Command:

```bash
nl -ba scripts/check_rootless_docker_worker.sh | sed -n '1,150p'
```

Exit code: `0`.

Relevant lines:

```text
66 start_daemon_if_safe() {
67   if [ "$(engine_process_count)" != "0" ]; then
68     echo "restart_refused=active_engine_process"
69     return 10
...
82   nohup /tmp/rl/bin/rootlesskit \
83     --state-dir=/tmp/rl/run/dockerd-rootless \
84     --net=host \
85     --copy-up=/etc \
86     --copy-up=/run \
87     --propagation=rslave \
88     dockerd \
89       --config-file=/dev/null \
90       --host=unix:///tmp/rl/run/docker.sock \
91       --data-root=/tmp/rl/data \
92       --exec-root=/tmp/rl/exec \
93       --iptables=false \
94       --bridge=none \
95       --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh \
96       --default-runtime sysbind \
97       --storage-driver overlay2 \
```

Important limitation: the helper's `--restart-if-down` branch skips restart when `docker info` is healthy. In the current failure mode, `docker info` is healthy but registry pull is broken, so this helper would not restart the stale daemon unless the daemon is first stopped by a separate controlled maintenance action.

### Additional Process Status

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
proxy_host=httpproxy-headless.kubebrain.svc.pjlab.local
getent hosts "$proxy_host" || true
for pid in $(pgrep -x dockerd 2>/dev/null || true); do
  grep -E '^(Name|State|Tgid|Pid|PPid|NSpid|Uid|Gid|Groups|CapInh|CapPrm|CapEff|CapBnd|CapAmb|NoNewPrivs|Seccomp):' /proc/$pid/status 2>/dev/null || true
  grep -E ' /etc | /run | /tmp/rl | /mnt/shared-storage-user ' /proc/$pid/mountinfo 2>/dev/null | sed -n '1,80p' || true
  cat /proc/$pid/net/dev 2>/dev/null | sed -n '1,12p' || true
done
REMOTE
```

Exit code: `0`.

Observed:

```text
100.100.135.62  httpproxy-headless.kubebrain.svc.pjlab.local
dockerd Seccomp: 0
mountinfo selected:
/run tmpfs copy-up present
/etc tmpfs copy-up present
net dev:
lo and eth0 present
```

### Dockerd Root View

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -s' <<'REMOTE'
set -u
REG=100.97.118.137:8555
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
for pid in $(pgrep -x dockerd 2>/dev/null || true); do
  for f in "/proc/$pid/root/etc/docker/daemon.json" "/proc/$pid/root/etc/docker/certs.d/$REG/ca.crt" "/proc/$pid/root/root/.config/docker/certs.d/$REG/ca.crt" "/proc/$pid/root/tmp/rl/data/certs.d/$REG/ca.crt"; do
    echo "root_view_file=$f"
    if test -f "$f"; then
      ls -lh "$f"
      case "$f" in
        *.crt)
          sha256sum "$f"
          if test -f "$CERT" && cmp -s "$CERT" "$f"; then echo matches_source=yes; else echo matches_source=no; fi
          ;;
        *) sed -n '1,120p' "$f" ;;
      esac
    else
      echo missing=yes
    fi
  done
done
REMOTE
```

Exit code: `0`.

Observed:

```text
/proc/284167/root/etc/docker/daemon.json exists and matches host /etc/docker/daemon.json.
/proc/284167/root/etc/docker/certs.d/100.97.118.137:8555/ca.crt matches source.
/proc/284167/root/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt matches source.
/proc/284167/root/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt matches source.
```

Interpretation: rootlesskit `/etc` copy-up is present, but this is not currently a missing-cert-in-daemon-view problem.

## Root Cause Assessment

Evidence rules out these causes:

- P0 Harbor down: worker shell `curl` gets `HTTP/1.1 200 OK`.
- Missing certs: all required cert paths exist and match the source cert, including from dockerd's `/proc/<pid>/root` view.
- Wrong Docker socket: commands used `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, and `/var/run/docker.sock` is not the active path.
- Different network namespace with no route: dockerd has the same net namespace inode as shell and `/proc/<dockerd>/net/route` contains direct routes.
- Missing cached image: cached digest is present, but fresh registry pull still failed in prior guard.

Most likely root cause:

The active rootless daemon is a stale runtime launched before the current guard command. It lacks `--config-file=/dev/null`, carries cluster proxy env, and is in a rootless user/mount namespace with copied-up `/etc` and `/run`. Even though shell and daemon share the same network namespace, the daemon's registry HTTP client is failing direct connection to the P0 registry with `network is unreachable`. The strongest actionable discriminator is a controlled restart under the synced command, then one digest pull verification.

Secondary risk:

The current helper will not restart this state by itself because `docker info` passes. A runner that only calls `scripts/check_rootless_docker_worker.sh --restart-if-down` can still proceed with a pull-broken daemon.

## Exact Controlled-Restart Verification Steps

Run these only in a maintenance window or explicit runner-prewarm step, not inside this report-only lane.

1. Confirm no bench/container work is running:

```bash
export WORKER_SSH=ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
docker ps -a --no-trunc
ps -eo pid,ppid,stat,etime,comm,args | grep -Ei "repozero|terminal|cocoa|vita|tau2|agentic|benchmark" | grep -v grep || true'
```

2. Record current daemon identity and image count:

```bash
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
ps -eo pid,ppid,stat,etime,comm,args | awk '\''BEGIN{IGNORECASE=1} $5 ~ /^(rootlesskit|dockerd|containerd)$/ {print}'\''
docker info --format "server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}}"
docker images --digests --format "{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}} {{.Size}}" 100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4'
```

3. Stop only runtime processes, preserving `/tmp/rl/data`:

```bash
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
pkill -TERM -x dockerd || true
pkill -TERM -x rootlesskit || true
pkill -TERM -x containerd || true
sleep 5
pgrep -a -x dockerd rootlesskit containerd || true
test -d /tmp/rl/data
echo data_root_preserved=/tmp/rl/data'
```

4. Start rootlesskit with the synced guard, preserving Docker data. Prefer no proxy inheritance for the daemon; if proxy must stay, make `NO_PROXY` explicit for the registry host and CIDR.

```bash
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
export PATH=/tmp/rl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export XDG_RUNTIME_DIR=/tmp/rl/run
export HOME=/root
export DOCKERD_ROOTLESS_ROOTLESSKIT_STATE_DIR=/tmp/rl/run/dockerd-rootless
mkdir -p /tmp/rl/run
chmod 700 /tmp/rl/run
rm -rf /tmp/rl/run/dockerd-rootless
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  NO_PROXY=100.97.118.137,100.97.118.137:8555,100.96.0.0/12,10.0.0.0/8,.pjlab.org.cn \
  no_proxy=100.97.118.137,100.97.118.137:8555,100.96.0.0/12,10.0.0.0/8,.pjlab.org.cn \
  nohup /tmp/rl/bin/rootlesskit \
    --state-dir=/tmp/rl/run/dockerd-rootless \
    --net=host \
    --copy-up=/etc \
    --copy-up=/run \
    --propagation=rslave \
    dockerd \
      --config-file=/dev/null \
      --host=unix:///tmp/rl/run/docker.sock \
      --data-root=/tmp/rl/data \
      --exec-root=/tmp/rl/exec \
      --iptables=false \
      --bridge=none \
      --add-runtime sysbind=/tmp/rl/bin/runc-sysbind.sh \
      --default-runtime sysbind \
      --storage-driver overlay2 \
    >>/tmp/rl/dockerd.log 2>&1 &
echo restart_pid=$!
for i in $(seq 1 60); do
  test -S /tmp/rl/run/docker.sock && break
  sleep 1
done
test -S /tmp/rl/run/docker.sock'
```

5. Verify the daemon is the new guarded daemon:

```bash
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
ps -eo pid,ppid,stat,etime,comm,args | awk '\''BEGIN{IGNORECASE=1} $5 ~ /^(rootlesskit|dockerd|containerd)$/ {print}'\''
ps -eo args | grep -F -- "--config-file=/dev/null" | grep -v grep
docker info --format "server={{.ServerVersion}} images={{.Images}} root={{.DockerRootDir}} security={{json .SecurityOptions}} http_proxy={{.HTTPProxy}} https_proxy={{.HTTPSProxy}} no_proxy={{.NoProxy}}"'
```

6. Verify shell and daemon reachability, then perform the single pull smoke:

```bash
ssh -CAXY "$WORKER_SSH" 'set -euo pipefail
REG=100.97.118.137:8555
REF=100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
ip route get 100.97.118.137
curl --cacert "$CERT" -fsS https://$REG/v2/
docker pull "$REF"
docker image inspect "$REF" --format "id={{.Id}} digests={{json .RepoDigests}}"
docker run --rm --network none "$REF" /bin/sh -lc "python --version 2>/dev/null || python3 --version 2>/dev/null || echo shell-ok"'
```

7. Runner gate after verification:

- If step 6 passes, mark `registry_pull_ready=true` for this worker class.
- If shell curl passes but Docker pull still fails, mark `registry_pull_ready=false`, preserve daemon logs, and fall back to checksum-verified tar preload for new images.
- Do not treat cached `docker image inspect` or cached `docker run --network none` as proof that registry distribution works.

