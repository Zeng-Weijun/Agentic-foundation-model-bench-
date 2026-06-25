# P0 Harbor Registry Smoke - 2026-06-25

## Scope

Read-only / low-risk validation of the workspace P0 OCI registry and
`worker-j9jjd` registry consumption path.

Constraints followed:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, including the
  `Project-Owned OCI Registry (P0 Harbor)` section.
- Worked from `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Did not delete, restart, push, commit, or run benchmark workloads.
- Used the current verified smoke image from the workflow and manifest.
- Used the explicit worker endpoint, not the stale local `worker` alias.
- Wrote only this report.

## Registry Endpoint

```text
registry URL: https://100.97.118.137:8555
registry container host: swe_dev2 / zwj3-image
container: swe-dh-shared-registry
backend storage: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/data
cert: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
```

Verified smoke image used:

```text
100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
```

Manifest source:

```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/swe-data-harness/rl/manifests/shared_registry_smoke.envs.jsonl
```

Manifest details:

```text
env_id=repo2env-pallets-click-f6299c4
image_transport=registry
image_status=resolved_digest
needs_network=false
fallback_tar=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/tmp/oci_tar_smoke_20260625T130818Z/click-f6299.tar
fallback_tar_sha256=e23626bb23be8776ab43eebd22415a20b9fff066ddbada7201643f0f2e9f0be3
validated_on=["swe_dev","worker-j9jjd"]
created_at=2026-06-25T22:35:00+08:00
```

## Evidence

### 1. `swe_dev2` Registry Container And `/v2/` Health

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn \
  'REG=100.97.118.137:8555; docker ps --filter name=swe-dh-shared-registry --no-trunc; docker inspect swe-dh-shared-registry --format ...; curl -k -fsS --max-time 10 https://$REG/v2/; curl --cacert /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt -fsS --max-time 10 https://$REG/v2/; stat registry cert/data paths'
```

Exit codes:

```text
ssh wrapper rc=0
docker_ps_registry_rc=0
docker_inspect_registry_rc=0
curl_v2_insecure_rc=0
curl_v2_ca_rc=0
stat_registry_paths_rc=0
```

Observed:

```text
HOST=zwj3-image
DATE=2026-06-25T23:05:38+08:00
container_id=be706ac6b5ec0218613efc42837dc4691cc586ad79761e09927a5670dfbb9a4c
image=registry:2
status=running
running=true
started=2026-06-25T14:28:25.126189031Z
restart=0
ports={"5000/tcp":[{"HostIp":"0.0.0.0","HostPort":"8555"},{"HostIp":"::","HostPort":"8555"}]}
mounts=/certs ro from registry/certs; /var/lib/registry rw from registry/data
```

Both `/v2/` probes returned:

```text
{}
```

The registry cert and storage paths exist:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
size=1891 mode=0644

/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/data
mode=0755 directory
```

Note: SSH printed `The host machine is under maintenance, recommend to restart
the workspace.` before the command output. The registry process and `/v2/` health
were still good in this check; this warning should be tracked as host-level
maintenance context, not a registry failure.

### 2. `dev` Docker Current Health

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=12 dev \
  'docker --version; docker info --format ...; docker version; docker ps --format ...'
```

Exit codes:

```text
ssh wrapper rc=0
docker_cli_version_rc=0
docker_info_rc=0
docker_version_rc=0
docker_ps_rc=0
```

Observed:

```text
HOST=zwj2
DATE=2026-06-25T23:05:38+08:00
docker=/usr/bin/docker
Docker version 26.1.3, build 26.1.3-0ubuntu1~22.04.1
server=26.1.3 containers=0 running=0 images=3 root=/mnt/docker_root_swebench_800g driver=overlay2
docker version: client/server OK, API 1.45
docker ps: no running containers printed
```

Interpretation: `dev` Docker is currently healthy for Docker client/server
operations, but it is not the registry host. Registry ownership remains on
`swe_dev2`.

### 3. `worker-j9jjd` CA, Curl, Pull, And Run

Worker endpoint:

```text
ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
```

Command:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=12 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'REG=100.97.118.137:8555; CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt; REF=100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df; export DOCKER_HOST=unix:///tmp/rl/run/docker.sock; ls/sha256/cmp CA paths; curl registry; docker info; docker ps; docker image inspect; docker pull "$REF"; docker run --rm --network none "$REF" ...'
```

Exit codes:

```text
ssh wrapper rc=0
shared cert ls_rc=0
/etc/docker/certs.d/100.97.118.137:8555/ca.crt ls_rc=0
/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt ls_rc=0
/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt ls_rc=0
cmp /etc copy vs shared cert rc=0
cmp /root/.config copy vs shared cert rc=0
cmp /tmp/rl/data copy vs shared cert rc=0
curl_v2_ca_rc=0
curl_v2_insecure_rc=0
docker_info_rc=0
docker_ps_rc=0
image_inspect_before_rc=0
docker_pull_rc=0
image_inspect_after_rc=0
docker_run_rc=0
```

CA evidence:

```text
shared cert sha256=dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
/etc/docker/certs.d/100.97.118.137:8555/ca.crt sha256=dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt sha256=dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt sha256=dccc577139b302a846faab9d6b1fb1a75fd93216f2f294ad1dce9582f233bd17
```

Both worker curl probes returned:

```text
{}
```

Worker rootless Docker state:

```text
rootlesskit pid=284143
dockerd pid=284167
containerd pid=284187
server=26.1.3 containers=0 running=0 images=240 root=/tmp/rl/data security=["name=seccomp,profile=builtin","name=rootless"]
docker ps -a: empty
```

Image inspect before pull already found the verified digest locally:

```text
id=sha256:f6299c4c6dc0c2b27c5a4872c1f12b417b9351f6a32754e0226d84ce38ad7be7
repo_tags=[]
repo_digests=["100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df"]
size=348174514
```

Pull result:

```text
Pulling from swe-data-harness/repo2env-pallets-click-f6299c4
Digest: sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
Status: Image is up to date for 100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
```

Run smoke:

```text
docker run --rm --network none "$REF" /bin/sh -lc 'python --version 2>/dev/null || python3 --version 2>/dev/null || echo shell-ok'
Python 3.10.12
```

Interpretation: worker registry trust, network path to registry, digest pull,
local cache, and no-network container execution are all usable for the current
verified smoke image.

## Worker Pull Availability

Worker pull by digest is currently available:

```text
worker: zwj2-64rlk-3469265-worker-0
docker_host: unix:///tmp/rl/run/docker.sock
registry: https://100.97.118.137:8555
image_ref: 100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@sha256:739a8078125ff68292ce6886671e7c8fd9b7825c3c8cf7fdccce45d22935d3df
docker_pull_rc=0
docker_run_rc=0
```

No fallback tar was needed in this smoke.

## Blockers

No blocker was observed for the P0 registry `/v2/` health path or the
`worker-j9jjd` digest pull/run path for the current verified smoke image.

Residual risks to keep in runner logic:
- This is a pilot registry, not full Harbor: no auth, self-signed TLS, no
  automatic retention/GC policy.
- The `swe_dev2` SSH session printed a host maintenance warning even though the
  registry container was healthy.
- Worker rootless Docker still uses pod-local `/tmp/rl/data`; workers must keep
  local Docker cache readiness checks and fallback OCI tar handling.
- This smoke did not push a new image and did not validate any image other than
  the workflow's current verified smoke digest.

## Command Ledger

| Command | Exit code | Notes |
|---|---:|---|
| Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then `cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd` | 0 | Required preflight. |
| Read `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/swe-data-harness/rl/manifests/shared_registry_smoke.envs.jsonl` | 0 | Confirmed current smoke digest and fallback tar metadata. |
| `git status --short --branch -- reports/p0_harbor_registry_smoke_20260625.md` | 0 | Target report did not exist before writing. |
| SSH `swe_dev2` explicit endpoint registry container and `/v2/` health check | 0 | `docker_ps_registry_rc=0`, `docker_inspect_registry_rc=0`, `curl_v2_insecure_rc=0`, `curl_v2_ca_rc=0`, `stat_registry_paths_rc=0`. |
| SSH `dev` Docker health check | 0 | `docker_cli_version_rc=0`, `docker_info_rc=0`, `docker_version_rc=0`, `docker_ps_rc=0`. |
| SSH explicit `worker-j9jjd` CA/curl/pull/run smoke | 0 | CA path `ls_rc=0`; all CA `cmp_rc=0`; `curl_v2_ca_rc=0`; `curl_v2_insecure_rc=0`; `docker_info_rc=0`; `docker_ps_rc=0`; `image_inspect_before_rc=0`; `docker_pull_rc=0`; `image_inspect_after_rc=0`; `docker_run_rc=0`. |
