# CoCoA Worker Prepare Smoke

Date: 2026-06-25

Scope: worker-side CoCoA adapter preflight without model calls. This checked shared checkout paths, task selection, run directory creation, and adapter preparation. It did not run a full CoCoA agent episode.

## Command Shape

The passing prepare-only command was equivalent to:

```bash
COCOA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent \
COCOA_PREPARE_ONLY=1 \
COCOA_TASKS_DIR=cocoabench-example-tasks \
COCOA_TASKS=linear-regime-estimation \
BENCH_RUN_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/manual_cocoa_prepare_20260625/cocoabench \
OPENAI_BASE_URL=http://100.96.1.101:18540/v1 \
DOCKER_HOST=unix:///tmp/rl/run/docker.sock \
/data/nips/bench/run_cocoabench.sh
```

## Result

The adapter completed prepare-only mode:

```text
bench=cocoabench
run_dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/manual_cocoa_prepare_20260625/cocoabench
model=gpt-5.4-mini
base_url=http://100.96.1.101:18540/v1
cocoa_use_encrypted_tasks=0
cocoa_required_task_file=task.yaml
cocoa_effective_tasks_dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/manual_cocoa_prepare_20260625/cocoabench/selected_cocoa_tasks
done: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/manual_cocoa_prepare_20260625/cocoabench/selected_cocoa_tasks
```

Produced artifact:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/manual_cocoa_prepare_20260625/cocoabench/selected_cocoa_tasks/linear-regime-estimation
```

## Fix Applied To Suite Manifest

The legacy adapter default was stale:

```text
COCOA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/cocoa-agent
```

That path is missing on the worker. The real shared checkout is:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent
```

`manifests/suite.example.yaml` now sets `COCOA_ROOT` explicitly for the `cocoabench` suite entry.

## Remaining Full-Smoke Blocker

The full CoCoA agent run is still blocked by the worker Python environment:

```text
.venv/bin/python -> /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
python313_missing
Python 3.10.12
```

The CoCoA checkout expects Python 3.13+. The worker is offline, so the next step is to stage a working Python 3.13/uv environment or an offline wheelhouse/env bundle from `dev`, then run the one-task CoCoA smoke through `dev_proxy_gpt54mini_8130`.
