# Terminal-Bench 2.1 Smoke Plan

Date: 2026-06-25

Scope: advance Terminal-Bench 2.1 toward a one-task executable smoke on the offline rootless worker without touching the suite launcher, suite manifest, README files, or other main-thread-owned files.

## Current verified paths

Inspected on `dev` and `worker-j9jjd`, not `swe_dev`.

| Item | Verified path / value | Status |
|---|---|---|
| Terminal-Bench 2.1 projectized root | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1` | Exists |
| Shared runner | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh` | Exists and executable |
| Terminal-Bench CLI root | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench` | Exists |
| Source task checkout | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks` | 89 source task directories |
| Generated YAML dataset | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml` | 89 `task.yaml` files |
| Prebuilt image manifest | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl` | 86 rows, 64 unique tasks |
| Prebuilt image tars | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/*.tar` | 50 tar files currently present |
| Worker rootless Docker endpoint | `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` on `worker-j9jjd` | Docker 26.1.3, security options include `rootless` |
| Worker Terminal-Bench image tags | `tb2-offline/*` in rootless Docker | 0 tags loaded |

The manifest has duplicate rows for some tasks and 14 rows whose archive path is not present. `failures.log` names build failures for `custom-memory-heap-crash`, `reshard-c4-data`, and `install-windows-3.11`.

## Smallest practical smoke target

Use `fix-git` as the first model smoke task:

- task YAML: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml/fix-git/task.yaml`
- source task: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks/fix-git`
- image tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar`
- image tag: `tb2-offline/fix-git:20260425`
- task metadata: `difficulty: easy`, `category: software-engineering`, `parser_name: pytest`, `expert_time_estimate_min: 5`, `max_agent_timeout_sec: 900.0`, `max_test_timeout_sec: 900.0`

Reasoning: `fix-git` is the easiest located task with an existing prebuilt archive and a simple Python slim base plus `git`. It is less image-size-minimal than `gcode-to-text`, but it is the lowest-risk one-task agent smoke among the inspected candidates.

## Wrapper added

Added `scripts/run_terminal_bench_2_1_smoke.sh`.

Default behavior is dry-run only:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --dry-run
```

Executable path, after staging this repo checkout on the worker:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --execute
```

Optional one-image preload path:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --execute --load-image
```

The wrapper selects exactly one task by default, writes results under:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_smoke
```

It sets:

```text
BENCH_OFFLINE=1
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
BENCH_PROFILE_ID=dev_proxy_gpt54mini_8130
BENCH_MODEL_PROFILE=gpt54mini_8130
OPENAI_BASE_URL=http://100.96.1.101:18540/v1
BASE_URL=http://100.96.1.101:18540/v1
TB2_USE_PREBUILT_IMAGES=1
TB_TASK_IDS=fix-git
NUM_TASKS=1
MAX_CONCURRENCY=1
TB_N_CONCURRENT=1
```

It fails closed on `--execute` unless:

- rootless Docker is reachable at `unix:///tmp/rl/run/docker.sock`;
- the shared runner exists and is executable;
- the task YAML exists;
- the one selected image archive exists;
- the `tb` CLI works;
- the exact selected Docker image tag is already loaded, or `--load-image` is explicitly supplied.

## Current blockers to a live one-task smoke

1. The worker rootless Docker store has no Terminal-Bench image tags loaded:

```text
tb_tags=0
```

The next command to satisfy this for the selected task is:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker load -i /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar &&
   DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/fix-git:20260425 >/dev/null'
```

2. The shared Terminal-Bench virtualenv is not executable on `worker-j9jjd` because its Python 3.13 symlink targets a missing worker-local uv interpreter:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/tb:
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/python3:
bad interpreter: No such file or directory
```

The venv symlink points to:

```text
/root/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13
```

but the worker only has `/bin/python3` as Python 3.10.12 for the bounded check, and importing Terminal-Bench with system Python fails on dependency versions. The concrete unblocker is to stage a worker-usable Python 3.13/Terminal-Bench environment without public downloads on the worker, then set `TB_BIN` to that `tb` executable or repair the shared `.venv`.

## Exact one-task command after blockers are fixed

Run on `worker-j9jjd` from a checkout containing this script:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --execute
```

If the image is not loaded yet but the tar is present:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --execute --load-image
```

The underlying shared runner invocation is equivalent to:

```bash
export BENCH_OFFLINE=1
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export BENCH_PROFILE_ID=dev_proxy_gpt54mini_8130
export BENCH_MODEL_PROFILE=gpt54mini_8130
export MODEL_NAME=gpt-5.4-mini
export LITELLM_MODEL=openai/gpt-5.4-mini
export OPENAI_BASE_URL=http://100.96.1.101:18540/v1
export BASE_URL=http://100.96.1.101:18540/v1
export BENCH_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench
export BENCH_OUTPUT_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_smoke
export TB_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench
export TB_BIN=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/.venv/bin/tb
export TB_2_1_SOURCE_PATH=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks
export TB_DATASET_PATH=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml
export TB2_USE_PREBUILT_IMAGES=1
export TB_TASK_IDS=fix-git
export NUM_TASKS=1
export MAX_CONCURRENCY=1
export TB_N_CONCURRENT=1
export TB_GLOBAL_AGENT_TIMEOUT_SEC=600
export TB_GLOBAL_TEST_TIMEOUT_SEC=300
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh
```

## Commands inspected or run

```bash
sed -n '1,240p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
git status --short
git branch --show-current
git log --oneline -5
find . -maxdepth 3 -type f | sort | sed -n '1,220p'
grep -R "terminal\|Terminal\|dev_proxy\|BENCH_MODEL_PROFILE\|AGENTIC\|RESULT" -n scripts manifests reports
sed -n '1,140p' scripts/README.md
sed -n '1,130p' manifests/suite.example.yaml
sed -n '230,270p' manifests/suite.example.yaml
sed -n '1,130p' reports/pending_adapter_inventory_20260625.md
sed -n '60,110p' reports/offline_docker_asset_plan_20260625.md
ssh -G worker
ssh -G dev
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<shared path existence, task count, manifest count, tar count, failures.log check>'
ssh -o BatchMode=yes -o ConnectTimeout=20 'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' '<rootless docker info, tb image tag count, shared path check>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'sed -n "1,260p" /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_terminal_bench_2_1.sh'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<manifest head and tar size sort>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<candidate task YAML and source file inspection>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'sed -n "1,260p" /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/lib/bench_common.sh'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<manifest duplicate/missing archive analysis>'
ssh -o BatchMode=yes -o ConnectTimeout=20 'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' '<tb executable, venv, Python, and import probe>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<dev tb shebang and entrypoint inspection>'
```

No full benchmark and no live one-task model smoke was launched.
