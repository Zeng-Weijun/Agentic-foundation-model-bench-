# CoCoA Python 3.13 Worker Runtime Unblock

Date: 2026-06-25

Scope: CoCoA worker runtime environment only. I did not edit suite launcher or manifest files, did not use `swe-dev` / `swe_dev`, did not install or download packages on the worker, and did not run a model-backed CoCoA benchmark. Checks were bounded to version commands, symlink targets, `uv` state, Python imports, and `parallel_inference.py --help`.

## Root Cause

The CoCoA checkout requires Python 3.13:

```text
pyproject.toml: requires-python = ">=3.13"
.python-version: 3.13
```

The shared CoCoA virtualenv was present but its interpreter symlink was broken on both `dev` and `worker-j9jjd`:

```text
.venv/bin/python -> /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
.venv/pyvenv.cfg: version_info = 3.13.13
```

Before repair, neither host had that uv-managed Python 3.13 path. Both hosts had `uv 0.11.4`, system Python 3.10.12, and uv-managed Python 3.12.13 only.

This explains the full CoCoA block: the legacy adapter chooses `$COCOA_ROOT/.venv/bin/python` first, sees a broken interpreter, and the fallback `uv run python` cannot safely resolve Python 3.13 on the offline worker.

## Existing Worker-Visible Asset

A shared conda environment already exists and is visible from both `dev` and the worker:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/cocoa/bin/python3.13
```

It is Python 3.13.13 and imports the CoCoA runtime dependencies on both hosts:

```text
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
```

It also runs the CoCoA CLI surface without starting a benchmark:

```text
parallel_inference.py --help
```

## Repair Applied

On `worker-j9jjd` only, I created the missing uv Python root as a symlink to the existing shared conda environment:

```bash
ln -s \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/cocoa \
  /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu
```

This is a worker-local pointer repair. It did not download anything and did not change the shared CoCoA checkout, suite YAML, or launcher code.

Post-repair, the legacy adapter's first-choice interpreter works on the worker:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent/.venv/bin/python --version
Python 3.13.13
```

Interpreter introspection after repair:

```text
executable /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent/.venv/bin/python
prefix /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent/.venv
base_prefix /root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu
site ['/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent/.venv/lib/python3.13/site-packages']
```

The repaired `.venv/bin/python` imports the CoCoA dependencies and runs `parallel_inference.py --help` successfully on `worker-j9jjd`.

## Remaining Scope

The Python 3.13 runtime blocker is removed for `worker-j9jjd`. Two non-Python blockers remain outside this lane:

1. `dev -> worker-j9jjd` SSH still fails with `Permission denied (publickey)`. The suite can still be dispatched by local Mac -> worker for now, but the final `dev` controller topology is not fixed.
2. A full CoCoA smoke will make model calls through `dev_proxy_gpt54mini_8130`, so the dev relay proxy must be running and reachable from the worker before executing it.

I did not create the same symlink on `dev`; `dev` is staging/control, while the runtime block was on the worker. If `dev` must run CoCoA directly later, apply the same symlink there or rebuild the shared `.venv` in a controlled way.

## Reusable Check

Added:

```text
scripts/check_cocoabench_env.sh
```

Run it on the worker with:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 \
  ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'bash -s' < scripts/check_cocoabench_env.sh
```

It performs no installs, downloads, benchmark runs, or model calls. It checks the CoCoA root, `.venv` symlink, uv state, shared conda Python 3.13, CoCoA imports, and `parallel_inference.py --help`.

## Exact One-Task Full Smoke Command

After confirming the dev relay proxy is running, the one-task CoCoA execute smoke should be:

```bash
rm -rf /tmp/agentic_cocoa_worker_smoke
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only cocoabench \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_cocoa_worker_smoke
```

The dry-run plan expands this to the worker with:

```text
COCOA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent
COCOA_TASKS_DIR=cocoabench-example-tasks
COCOA_TASKS=linear-regime-estimation
COCOA_MAX_ITERATIONS=20
COCOA_WORKERS=1
OPENAI_BASE_URL=http://100.96.1.101:18540/v1
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
BENCH_OFFLINE=1
```

Recommended next action: run `scripts/check_cocoabench_env.sh` through SSH immediately before the full smoke, verify the dev proxy listener, then run the exact one-task `--execute` command above from the current repo checkout while the main thread owns integration.
