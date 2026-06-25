# CoCoA Worker Smoke - 2026-06-25

## Scope

Run the one-task CoCoA worker smoke through the YAML suite from the local Mac
control plane, dispatching directly to the worker and using the dev proxy.

Restrictions followed:
- No `swe-dev` / `swe_dev` host usage.
- No public-internet install or download on the worker.
- No suite launcher, manifest, README, or benchmark code edits.
- Only the `cocoabench` suite entry was executed.

## Preflight

### Dev proxy listener

Command:
```bash
ssh dev 'hostname; date -Iseconds; ss -ltnp | grep ":18540" || true'
```

Observed:
```text
HOST=zwj2
DATE=2026-06-25T21:21:31+08:00
LISTEN 0 0 0.0.0.0:18540 0.0.0.0:* users:(("python3",pid=2059245,fd=3))
```

### Worker `/v1/models` through dev proxy

Observed from worker:
```text
HOST=zwj2-64rlk-3469265-worker-0
DATE=2026-06-25T21:21:31+08:00
OPENAI_API_KEY_SET=yes
HTTP_CODE=200
models_parse=ok
model_count=9
model_sample=gpt-5.5,gpt-5.4,gpt-5.4-mini,gpt-5.3-codex,gpt-5.3-codex-spark
```

This confirms the worker could reach `http://100.96.1.101:18540/v1` before the
smoke run.

### Worker CoCoA Python environment

`scripts/check_cocoabench_env.sh` was run on the worker before the smoke. It
reported `cocoabench_env=ok`, with:
- `COCOA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent`
- `.venv/bin/python` resolving to `/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/cocoa/bin/python3.13`
- Python `3.13.13`
- CoCoA-required imports and `parallel_inference.py --help` passing.

## Smoke Command

Executed from:
```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-
```

Command:
```bash
rm -rf /tmp/agentic_cocoa_worker_smoke
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only cocoabench \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_cocoa_worker_smoke
```

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
      "ended_at": "2026-06-25T13:21:58Z",
      "exit_code": 0,
      "log_path": "/tmp/agentic_cocoa_worker_smoke/logs/cocoabench.log",
      "started_at": "2026-06-25T13:21:55Z",
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

Important semantic note: the suite launcher marks the benchmark entry as pass
because `run_cocoabench.sh` exited 0 after writing result artifacts. That is
not the same as the CoCoA task succeeding.

## Shared Worker Artifacts

Run directory:
```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/cocoabench
```

Key files:
```text
cocoabench.log
cocoa_config.json
command.sh
run.env.summary
results/linear-regime-estimation.json
results/statistics.txt
work/20260625-212156/tasks/linear-regime-estimation/run.log
work/20260625-212156/tasks/linear-regime-estimation/output/linear-regime-estimation.json
work/20260625-212156/tasks/linear-regime-estimation/output/statistics.txt
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
created_at=2026-06-25T21:21:56+08:00
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
21:21:58 - executor.executor:INFO: Controller initialized: gpt (Model: gpt-5.4-mini)
21:21:58 - executor.executor:INFO: Using UnifiedSandboxClient (browser + file + code + shell)
21:21:58 - executor.inference:INFO: Loaded 1 tasks
21:21:58 - executor.inference:INFO: Processing task 1/1: linear-regime-estimation
21:21:58 - executor.sandbox:INFO: Building and starting container for task 'linear-regime-estimation' using docker-compose
21:21:58 - executor.sandbox:ERROR: Failed to build container with docker-compose: error during connect: Get "http://%!F(MISSING)tmp%!F(MISSING)rl%!F(MISSING)run%!F(MISSING)docker.sock/v1.45/version": EOF: driver not connecting
21:21:58 - executor.inference:ERROR: Task linear-regime-estimation failed with error: Sandbox environment failed to become ready
```

No model call was made: token counts are all zero.

## Bounded Worker Docker Probe

Command shape:
```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock timeout 10s docker version
DOCKER_HOST=unix:///tmp/rl/run/docker.sock timeout 10s docker info --format '{{json .ServerVersion}} {{json .Driver}} {{json .CgroupDriver}}'
```

Observed:
```text
HOST=zwj2-64rlk-3469265-worker-0
DATE=2026-06-25T21:23:52+08:00
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
error during connect: Get "http://%2Ftmp%2Frl%2Frun%2Fdocker.sock/v1.45/version": EOF
docker_version_exit=1
"26.1.3" "overlay2" "none"
```

## Classification

The YAML suite dispatch path, CoCoA Python 3.13 environment, task selection,
dev proxy reachability, and CoCoA runner startup are working.

The one-task smoke is not task-successful end-to-end yet. It fails as an
infrastructure/runtime issue at the sandbox Docker layer:
- CoCoA reaches `parallel_inference.py`.
- The GPT controller initializes with `base_url=http://100.96.1.101:18540/v1`.
- The task is loaded.
- Docker compose fails while probing the rootless Docker socket.
- No model tokens are consumed.

This is not a model quality failure and not a CoCoA Python 3.13 environment
failure.

## Recommended Next Action

Fix or restart the worker rootless Docker runtime behind:
```text
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
```

Then rerun the exact one-task smoke command above. A real end-to-end CoCoA pass
should require both:
- suite `summary.json` status `pass`, and
- CoCoA `results/statistics.txt` showing `Errors: 0` with the task result not
  reporting `status: error`.
