# CoCoA Worker Smoke - 2026-06-25

## Scope

Ran the requested one-task CoCoA smoke through the YAML suite from the local Mac
control plane, dispatching directly to `worker-j9jjd` and using the dev proxy.

Restrictions followed:
- Did not use `swe-dev` / `swe_dev`.
- Did not run full CoCoA or any other benchmark entry.
- Did not edit scripts, manifests, README, or benchmark code.
- Only wrote this report file.

## Preflight

### Dev proxy listener

Command:
```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'bash -s' <<'REMOTE'
set -euo pipefail
printf 'HOST=%s\n' "$(hostname)"
date -Iseconds
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true) | grep ':18540' || true
REMOTE
```

Observed:
```text
HOST=zwj2
2026-06-25T21:27:30+08:00
LISTEN 0 0 0.0.0.0:18540 0.0.0.0:* users:(("python3",pid=2059245,fd=3))
```

Dev host address check:
```text
HOST=zwj2
2026-06-25T21:28:06+08:00
100.96.1.101 172.17.0.1
python3 /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/openai_relay_proxy.py --bind 0.0.0.0 --port 18540 --upstream http://8.130.49.170
```

### Worker `/v1/models` through dev proxy

The worker has inherited proxy variables. A first Python `urllib` probe timed
out, but the direct worker-to-dev TCP path and `curl --noproxy '*'` probe both
passed. This is the relevant preflight for the suite command because the suite
sets `NO_PROXY` / `no_proxy` for `100.96.1.101`.

Observed from worker:
```text
HOST=zwj2-64rlk-3469265-worker-0
2026-06-25T21:28:05+08:00
proxy_env=no_proxy=<set> https_proxy=<set> NO_PROXY=<set> HTTPS_PROXY=<set> HTTP_PROXY=<set> http_proxy=<set>
tcp_18540=ok
curl_http_code=200
curl_models_parse=ok
curl_model_count=9
curl_model_sample=gpt-5.5,gpt-5.4,gpt-5.4-mini,gpt-5.3-codex,gpt-5.3-codex-spark
```

### Worker CoCoA Python environment

Before the smoke, I ran:
```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'bash -s' < scripts/check_cocoabench_env.sh
```

Relevant output:
```text
host=zwj2-64rlk-3469265-worker-0
date=2026-06-25T21:28:23+08:00
cocoa_root=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent
realpath=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/cocoa/bin/python3.13
Python 3.13.13
openai ok
numpy ok
yaml ok
requests ok
PIL ok
playwright ok
agent_sandbox ok
websocket ok
anthropic ok
google.genai ok
parallel_inference.py --help passed
cocoabench_env=ok
```

## Smoke Command

Executed from:
```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
```

Requested command:
```bash
rm -rf /tmp/agentic_cocoa_worker_smoke
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only cocoabench \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_cocoa_worker_smoke
```

The command was run under a local Python `subprocess.run(..., timeout=1800)`
wrapper to bound the execution. The command itself completed before the timeout.

Launcher exit code:
```text
0
```

Launcher stdout summary:
```text
suite: dev_worker_smoke_dryrun
mode: smoke
controller_host: dev
dry_run: false
suite_concurrency: 1

- cocoabench [wired_legacy]
  model: dev_proxy_gpt54mini_8130 (gpt-5.4-mini)
  worker_host: ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
  network_policy: offline_or_internal_only
  docker_host: unix:///tmp/rl/run/docker.sock
  command_preview: ... COCOA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent COCOA_TASKS_DIR=cocoabench-example-tasks COCOA_TASKS=linear-regime-estimation COCOA_MAX_ITERATIONS=20 run_cocoabench.sh
  note: worker must consume pre-staged assets; no public internet actions are allowed
cocoabench pass /tmp/agentic_cocoa_worker_smoke/logs/cocoabench.log
```

## Controller Artifacts

Local output directory:
```text
/tmp/agentic_cocoa_worker_smoke
```

Summary:
```json
{
  "results": [
    {
      "bench_id": "cocoabench",
      "ended_at": "2026-06-25T13:28:26Z",
      "exit_code": 0,
      "log_path": "/tmp/agentic_cocoa_worker_smoke/logs/cocoabench.log",
      "started_at": "2026-06-25T13:28:23Z",
      "status": "pass"
    }
  ],
  "status": 0,
  "suite_id": "dev_worker_smoke_dryrun"
}
```

Controller log:
```text
/tmp/agentic_cocoa_worker_smoke/logs/cocoabench.log
```

Controller status file:
```text
/tmp/agentic_cocoa_worker_smoke/status/cocoabench.status
```

Status file contents:
```text
pass
```

Pass/fail semantic note: the suite launcher reports `pass` because the legacy
`run_cocoabench.sh` adapter exited 0 after writing CoCoA result artifacts. That
does not mean the CoCoA task succeeded.

## Shared Worker Artifacts

Run directory:
```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench
```

Files observed:
```text
cocoabench.log
cocoa_config.json
command.sh
results/linear-regime-estimation.json
results/statistics.txt
run.env.summary
work/20260625-212824/tasks/linear-regime-estimation/run.log
```

`run.env.summary`:
```text
bench=cocoabench
run_dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench
model=gpt-5.4-mini
litellm_model=openai/gpt-5.4-mini
base_url=http://100.96.1.101:18540/v1
reasoning_effort=xhigh
num_tasks=1
num_trials=1
max_concurrency=1
created_at=2026-06-25T21:28:24+08:00
cocoa_use_encrypted_tasks=0
cocoa_required_task_file=task.yaml
artifact=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/results
```

`command.sh`:
```bash
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent/.venv/bin/python parallel_inference.py --config /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/cocoa_config.json --tasks-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/selected_cocoa_tasks --output-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/results --work-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench/work --workers 1 --model gpt-5.4-mini
```

## CoCoA Task Result

`results/linear-regime-estimation.json`:
```json
{
  "status": "error",
  "error": "Sandbox environment failed to become ready",
  "task_name": "linear-regime-estimation"
}
```

`results/statistics.txt`:
```text
Total Tasks: 1
Passed: 0
Failed: 0
Errors: 1
Success Rate: 0.00%

Error Tasks:
  - linear-regime-estimation

--- Cost Summary ---
Grand Total Cost: $0.000000
Total Input Tokens: 0
Total Output Tokens: 0
Total Cached Tokens: 0
```

Relevant task log excerpt:
```text
21:28:25 - executor.executor:INFO: Controller initialized: gpt (Model: gpt-5.4-mini)
21:28:25 - executor.executor:INFO: Using UnifiedSandboxClient (browser + file + code + shell)
21:28:25 - executor.inference:INFO: Loaded 1 tasks
21:28:25 - executor.inference:INFO: Processing task 1/1: linear-regime-estimation
21:28:25 - executor.sandbox:INFO: Building and starting container for task 'linear-regime-estimation' using docker-compose
21:28:25 - executor.sandbox:ERROR: Failed to build container with docker-compose: ... error during connect: Get "http://%!F(MISSING)tmp%!F(MISSING)rl%!F(MISSING)run%!F(MISSING)docker.sock/v1.45/version": EOF: driver not connecting
21:28:25 - executor.inference:ERROR: Task linear-regime-estimation failed with error: Sandbox environment failed to become ready
Grand Total Cost: $0.000000
Input: 0  Output: 0  Cached: 0
```

No model call was made.

## Bounded Worker Docker Probe

Command shape:
```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock timeout 10s docker version
DOCKER_HOST=unix:///tmp/rl/run/docker.sock timeout 10s docker info --format '{{json .ServerVersion}} {{json .Driver}} {{json .CgroupDriver}}'
```

Observed:
```text
HOST=zwj2-64rlk-3469265-worker-0
2026-06-25T21:29:06+08:00
DOCKER_HOST=<unset>
srw-rw---T 1 root 100112 0 Jun 18 22:58 /tmp/rl/run/docker.sock
Client:
 Version:           26.1.3
 API version:       1.45
 Go version:        go1.22.2
 Git commit:        26.1.3-0ubuntu1~22.04.1
 Built:             Mon Oct 14 21:24:40 2024
 OS/Arch:           linux/amd64
 Context:           default
docker_version_exit=1
error during connect: Get "http://%2Ftmp%2Frl%2Frun%2Fdocker.sock/v1.45/version": EOF
"26.1.3" "overlay2" "none"
docker_info_exit=0
```

This matches the CoCoA failure boundary: the worker rootless Docker socket is
present but not healthy enough for the `docker-compose` version probe used by
the CoCoA sandbox startup path.

## Classification

The YAML suite dispatch path is executable from local Mac to worker, the CoCoA
Python 3.13 environment is unblocked, the one-task task selection is correct,
and the dev proxy is reachable from the worker.

CoCoA is not yet executable end-to-end at task-success level. The smoke fails as
a worker infrastructure/runtime issue at the sandbox Docker layer:
- CoCoA reaches `parallel_inference.py`.
- The GPT controller initializes with `base_url=http://100.96.1.101:18540/v1`.
- The selected task is exactly `linear-regime-estimation`.
- Sandbox startup fails while probing `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
- The task records `status: error`.
- Token counts are all zero, so this is not a model quality failure.
- The Python 3.13 environment check passes, so this is not the previous Python
  runtime blocker.

End-to-end pass semantics should require both:
- suite `summary.json` status `pass`, and
- CoCoA `results/statistics.txt` showing `Errors: 0` with no task-level
  `status: error`.

Current result: suite adapter executable, task not successful end-to-end.
