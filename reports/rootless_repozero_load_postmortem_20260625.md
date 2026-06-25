# Rootless RepoZero Load Postmortem - worker-j9jjd - 2026-06-25

## Scope

Surface `50` rootless lane follow-up after RepoZero image load on
`worker-j9jjd`.

Constraints followed:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before remote work.
- Worked from `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Used only the explicit worker endpoint:
  `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.
- Did not use the local `worker` SSH alias.
- Did not run benchmarks.
- Did not commit or push.
- Wrote only this report.

## Evidence

### RepoZero load log

Checked:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'stat /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/repozero_worker_load_20260625_2231.log; sed -n "1,120p" ...; tail -n 160 ...'
```

Exit codes:

```text
ssh wrapper rc=0
stat_rc=0
head_rc=0
tail_rc=0
```

Observed log path:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/repozero_worker_load_20260625_2231.log
size: 740 bytes
mtime: 2026-06-25 22:31:07 +0800
```

Key log contents:

```text
started=2026-06-25T22:30:52+08:00
host=zwj2-64rlk-3469265-worker-0
repo_head=570c5f5
repoarena-new_latest.tar: OK
Manifest: manifests/offline_images.repozero.yaml
Asset root: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
Docker host: unix:///tmp/rl/run/docker.sock
Mode: load
Summary: present=0 missing=0 loaded=1 skipped=0 tar_missing=0 errors=0
- repozero_py2js_repoarena_runtime: loaded
  missing_tags: ghcr.io/jessezzzzz/repoarena-new:latest
  loaded_tars: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar

Cannot connect to the Docker daemon at unix:///tmp/rl/run/docker.sock. Is the docker daemon running?
```

Interpretation: the loader reported the RepoZero tar as successfully loaded
(`loaded=1`, `errors=0`) but a later Docker client call in the same log hit a
dead or unavailable daemon/socket.

### Current RepoZero image state

Checked:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest --format ...'
```

Exit codes:

```text
ssh wrapper rc=0
image_inspect_rc=0
image_inspect_detail_rc=0
image_ls_rc=0
```

Observed:

```text
id=sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c
repo_tags=["ghcr.io/jessezzzzz/repoarena-new:latest"]
repo_digests=[]
size=1202432176
created=2026-05-12T12:09:31.955510342Z
```

Exact tag listing:

```text
REPOSITORY                         TAG       DIGEST    IMAGE ID                                                                  CREATED       SIZE
ghcr.io/jessezzzzz/repoarena-new   latest    <none>    sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c   6 weeks ago   1.2GB
```

Interpretation: the RepoZero runtime image exists in the current rootless Docker
store despite the load log ending with a daemon connection failure.

### Current daemon state

Checked daemon/process state and image presence through the explicit endpoint.

Exit codes:

```text
ssh wrapper rc=0
docker_info_rc=0
docker_ps_rc=0
```

Observed:

```text
rootlesskit pid=284143
dockerd pid=284167
containerd pid=284187
process start: Thu Jun 25 22:31:43 2026
socket: /tmp/rl/run/docker.sock
socket mtime: Jun 25 22:31
docker info: server=26.1.3 containers=0 running=0 images=240 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"]
docker ps -a: empty
```

This daemon was started after the RepoZero load log mtime
(`22:31:07 +0800`) and before the follow-up checks. Since the image is visible
now, `/tmp/rl/data` survived at least this daemon process restart.

### Required health script output

Checked:

```bash
WORKER_SSH=ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  ./scripts/check_rootless_docker_worker.sh --restart-if-down
```

Exit codes:

```text
script_rc=1
```

Key output:

```text
mode=restart-if-down
docker_host=unix:///tmp/rl/run/docker.sock
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

Image list sample from the script included:

```text
ghcr.io/jessezzzzz/repoarena-new:latest e01d5505ea76 1.2GB
```

Interpretation: the guard did not restart because `docker info` was already
healthy. It returned non-zero because the known `/version` path and Python Docker
SDK negotiation path are still unhealthy.

### `/tmp/rl/dockerd.log` tail and load-window context

Checked:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'tail -n 220 /tmp/rl/dockerd.log'
```

Exit codes:

```text
ssh wrapper rc=0
dockerd_tail_rc=0
```

Also checked a compact log window:

```bash
grep -En '2026-06-25T22:3[0-7]|2026/06/25 22:3[0-7]|Processing signal|Daemon shutdown complete|API listen|Docker daemon|loading cgroup|shim disconnected|panic serving|fillRootlessVersion|images/load|Loaded image|reference for unknown type' /tmp/rl/dockerd.log
```

Exit code:

```text
grep_log_rc=0
```

Relevant daemon log evidence:

```text
unable to configure the Docker daemon with file /etc/docker/daemon.json: the following directives are specified both as a flag and in the configuration file: data-root: (from flag: /tmp/rl/data, from file: /mnt/docker_root_swebench_800g)
time="2026-06-25T22:31:43+08:00" level=warning msg="[rootlesskit:parent] Running RootlessKit as the root user is unsupported."
time="2026-06-25T22:31:43.648057599+08:00" level=info msg="Starting up"
time="2026-06-25T22:31:44.797446763+08:00" level=info msg="Docker daemon" commit="26.1.3-0ubuntu1~22.04.1" containerd-snapshotter=false storage-driver=overlay2 version=26.1.3
time="2026-06-25T22:31:44.797481117+08:00" level=info msg="Daemon has completed initialization"
time="2026-06-25T22:31:44.815097399+08:00" level=info msg="API listen on /tmp/rl/run/docker.sock"
2026/06/25 22:31:44 http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
2026/06/25 22:32:03 http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
time="2026-06-25T22:32:03.439467980+08:00" level=warning msg="reference for unknown type: " digest="sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df" remote="100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8cf7fdccce45d22935d3df"
time="2026-06-25T22:32:06.838481774+08:00" level=error msg="loading cgroup for 284682" error="cgroups: cgroup deleted"
time="2026-06-25T22:32:06.867181412+08:00" level=info msg="shim disconnected" id=8965d358fc6d8b80247adc7d028de183b4262fb0860fb4b14fa000d2dd0a8e61 namespace=moby
2026/06/25 22:35:40 http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
2026/06/25 22:36:43 http: panic serving @: runtime error: invalid memory address or nil pointer dereference
github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)
```

Interpretation:
- The current log starts with a failed daemon invocation caused by
  `/etc/docker/daemon.json` conflicting with the explicit `--data-root=/tmp/rl/data`.
- The active daemon then started at `22:31:43`.
- The same `fillRootlessVersion` panic remains reproducible whenever clients
  hit `/version`.
- The cgroup/shim messages look like short-lived container cleanup events, not
  persistent running containers; `docker ps -a` is empty.

### Persistence probe

Checked:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker info --format ...; df -hT /tmp/rl /tmp/rl/data /tmp/rl/run; findmnt -T /tmp/rl/data; du -sh /tmp/rl/data'
```

Exit codes:

```text
ssh wrapper rc=0
docker_info_format_rc=0
df_rc=0
findmnt_rc=0
du_rc=0
```

Observed:

```text
root=/tmp/rl/data
driver=overlay2
driver_status=[["Backing Filesystem","tmpfs"],["Supports d_type","true"],["Using metacopy","false"],["Native Overlay Diff","false"],["userxattr","true"]]
images=240

Filesystem Type  Size Used Avail Use% Mounted on
tmpfs      tmpfs 391G 139G 253G  36% /tmp

findmnt: /tmp is tmpfs
du -sh /tmp/rl/data: 134G
```

Interpretation: the image store persists across daemon process restart while
`/tmp/rl/data` remains intact, but the store is on `/tmp` tmpfs, not on the
shared persistent project root.

## Risk

1. **RepoZero image is present now, but not durable across pod/tmpfs loss.**
   The tag `ghcr.io/jessezzzzz/repoarena-new:latest` exists in the current
   rootless Docker store, but that store is `/tmp/rl/data` on tmpfs. It survived
   the daemon restart at `22:31:43`, but it should be treated as pod-local,
   memory-backed state. If the worker pod is replaced, `/tmp` is cleared, or the
   rootless data directory is rebuilt, the image must be reloaded from the shared
   tar.

2. **Daemon process persistence is weak.**
   The load log ended with `Cannot connect to the Docker daemon`, and the active
   daemon was started after that log was written. This confirms the runner cannot
   assume the rootless daemon stays alive across load/check phases.

3. **`docker info` is not a sufficient health gate.**
   `docker info` is currently healthy and caused `--restart-if-down` to skip
   restart, but `docker version`, raw `/v1.45/version`, and Python Docker SDK
   version negotiation still fail. SDK-based benchmark harnesses can fail even
   when image inspect, image listing, compose `ps`, and `docker info` work.

4. **Known `/version` panic remains unresolved.**
   `/tmp/rl/dockerd.log` continues to show
   `github.com/docker/docker/daemon.(*Daemon).fillRootlessVersion(...)` panics.
   This is the same rootless Docker Engine failure mode previously seen in the
   CoCoA lane.

5. **Daemon restart command can fail if it reads host Docker config.**
   The current daemon log contains a failed startup caused by
   `/etc/docker/daemon.json` specifying `data-root=/mnt/docker_root_swebench_800g`
   while the rootless start command also passes `--data-root=/tmp/rl/data`.
   Runner-side daemon start logic must avoid inheriting conflicting daemon
   config. This repo's `scripts/check_rootless_docker_worker.sh` now starts
   `dockerd` with `--config-file=/dev/null` before the explicit rootless flags.

## Runner Guard Changes Needed

1. **Split daemon liveness from SDK readiness.**
   A runner guard should check both:
   - low-level daemon operations: `_ping`, `docker info`, `docker ps`, image
     inspect/list;
   - SDK/compose readiness: `docker version` or raw `/v1.45/version`, and a
     Python Docker SDK `docker.from_env().version()` probe when the harness uses
     the SDK.

2. **Treat `/version` failure as a hard block for SDK-based harnesses.**
   If `docker version` or Python Docker SDK negotiation fails, do not launch
   RepoZero/CoCoA-style runners that depend on Docker SDK version negotiation.
   Classify the failure as `infra_docker_version_endpoint`, not as a missing
   image or benchmark/model failure.

3. **Guard the image by tag immediately before a run.**
   Before RepoZero execution, run:

   ```bash
   DOCKER_HOST=unix:///tmp/rl/run/docker.sock \
     docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest
   ```

   If absent, reload from:

   ```text
   /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar
   ```

   Do not rely on prior successful load logs as durable state.

4. **Record rootless data-root durability in run manifests.**
   Runner artifacts should record:
   - `docker_host=unix:///tmp/rl/run/docker.sock`
   - `docker_root=/tmp/rl/data`
   - `docker_root_fstype=tmpfs`
   - `image_id=sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c`
   - `image_tag=ghcr.io/jessezzzzz/repoarena-new:latest`
   - whether the tag was already present or reloaded in this run.

5. **Make restart behavior explicit and conservative.**
   Restart only when no containers/processes are active and only after recording
   the pre-restart state. A restart may preserve `/tmp/rl/data`, as seen here,
   but it does not prove durable storage. After any restart, rerun image inspect
   and SDK readiness checks before scheduling work.

6. **Avoid daemon config conflicts on startup.**
   Rootless start commands should not accidentally read a host/rootful Docker
   config that conflicts with `--data-root=/tmp/rl/data`. The observed
   `/etc/docker/daemon.json` conflict is handled in this repo's start wrapper by
   passing `--config-file=/dev/null` to `dockerd` before relying on automatic
   recovery.

## Command Ledger

All local commands were run after:

```bash
cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
```

| Command | Exit code | Notes |
|---|---:|---|
| Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` then `cd .../Agentic-foundation-model-bench- && pwd` | 0 | Required preflight. |
| `rg -n "Agentic-foundation-model-bench|rootless|worker-j9jjd|repozero" /Users/Zhuanz1/.codex/memories/MEMORY.md` | 1 | No relevant memory hits. |
| `git status --short --branch -- reports/rootless_repozero_load_postmortem_20260625.md scripts/check_rootless_docker_worker.sh` | 0 | Target report did not exist before writing; guard script was later patched to pass `--config-file=/dev/null`. |
| `ls -l scripts/check_rootless_docker_worker.sh && sed -n '1,240p' ...` | 0 | Confirmed existing health script and `--restart-if-down` behavior. |
| SSH explicit endpoint: stat/head/tail `repozero_worker_load_20260625_2231.log` | 0 | Subcommands: `stat_rc=0`, `head_rc=0`, `tail_rc=0`. |
| SSH explicit endpoint: `tail -n 220 /tmp/rl/dockerd.log` | 0 | `dockerd_tail_rc=0`. |
| SSH explicit endpoint: `docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest` plus quick daemon state | 0 | `image_inspect_rc=0`, `docker_info_rc=0`, `docker_ps_rc=0`. |
| `WORKER_SSH=explicit ./scripts/check_rootless_docker_worker.sh --restart-if-down` | 1 | Expected unhealthy result: restart skipped because `docker_info_ok`; `/version` and SDK checks failed. |
| SSH explicit endpoint: persistence and load-window probe | 0 | Subcommands: `docker_info_format_rc=0`, `df_rc=0`, `findmnt_rc=0`, `du_rc=0`, `grep_log_rc=0`; one image inspect template subcommand failed with `image_inspect_detail_rc=1` because `.Containers` is not a valid key. |
| SSH explicit endpoint: corrected image inspect/detail and exact image ls | 0 | `image_inspect_detail_rc=0`, `image_ls_rc=0`. |
