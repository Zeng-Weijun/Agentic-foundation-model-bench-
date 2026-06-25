# Agentic Foundation Model Bench

This repository is the working dossier and future runner scaffold for evaluating agentic foundation models on software-engineering, terminal, repository-generation, and tool-use benchmarks.

Current focus:

- organize benchmark definitions, task shapes, harnesses, score anchors, and local Qwen/GPT evidence;
- preserve the existing SWE-bench Verified lessons from shared storage;
- use `dev` as the orchestration/control host for shared-disk setup and benchmark staging;
- define an offline rootless worker contract before running larger benchmark campaigns.

Key reports:

- `reports/agentic_bench_landscape_20260625.md` - benchmark landscape and score anchors.
- `reports/agentic_bench_matrix_20260625.csv` - machine-readable benchmark matrix.
- `reports/shared_disk_layout_research_20260625.md` - shared-disk layout research.
- `reports/rootless_worker_research_20260625.md` - rootless worker architecture research.
- `reports/deployment_plan_20260625.md` - GitHub/shared-disk deployment plan.
- `reports/trace_manifest_template.yaml` - per-task trace manifest template.

Current local Qwen score anchor:

- Benchmark: SWE-bench Verified
- Model: `qwen3-coder-30b-a3b-instruct`
- Serving: SGLang on `worker_rkn9p`, `http://100.103.11.77:8503/v1`
- Agent scaffold: Qwen Code `0.15.6`
- Score: `245/500 = 49.0%`
- Source: `reports/qwen3_coder_swebench_qwen_code_retry_cases_20260529.md`

Do not conflate this local 30B-A3B result with public Qwen3-Coder-Next 80A3 technical-report results.

## Planned Shared-Disk Root

Future large artifacts and runnable benchmark state should live under:

```bash
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
```

GitHub should contain source, docs, schemas, manifests, and lightweight runner wrappers. Shared storage should contain datasets, harness checkouts, model/runtime pointers, run artifacts, raw traces, and large outputs.

Operational target: orchestrate from `dev`. Rootless workers can be separate SSH targets and may have no public internet access, so downloads, git fetches, image pulls, dependency preparation, and dataset staging should happen on `dev` or through prebuilt shared caches. Offline workers should consume only pre-staged assets.

## Existing Local Launchers

The rest of this file documents the existing local benchmark launcher directory. These scripts are useful inputs, but they are not yet the final rootless worker architecture.

历史上这个目录是为了把 `swe_dev` 上当前几条能跑的 benchmark 收到一个入口下。每个 benchmark 一个独立 `run_*.sh`，都通过同一套环境变量切模型。后续不要把这段当作新部署目标；新的编排入口应从 `dev` 发起，再调度离线 rootless worker。

目标远端路径建议是：

```bash
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
```

当前这份先落在本地：

```bash
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/bench
```

历史同步脚本原先同步到 `swe_dev`，仅作为旧 launcher 记录：

```bash
./sync_to_swe_dev.sh
```

## 模型配置

复制一份配置：

```bash
cp model.env.example model.env
```

也可以不改 `model.env`，直接用内置 profile：

```bash
BENCH_MODEL_PROFILE=gpt54mini_8130 ./run_tau2.sh
BENCH_MODEL_PROFILE=gpt54_8130 ./run_tau2.sh
BENCH_MODEL_PROFILE=qwen_sglang ./run_tau2.sh
```

8.130 中转模型示例：

```bash
MODEL_NAME=gpt-5.4
LITELLM_MODEL=openai/gpt-5.4
OPENAI_BASE_URL=http://8.130.49.170/v1
OPENAI_REASONING_EFFORT=xhigh
```

SGLang / Qwen OpenAI-compatible endpoint 示例：

```bash
MODEL_NAME=Qwen/Qwen3-Coder-30B-A3B-Instruct
LITELLM_MODEL=openai/Qwen/Qwen3-Coder-30B-A3B-Instruct
OPENAI_BASE_URL=http://gpu-l-lg-cmc-h-h200-0219.host.h.pjlab.org.cn:8000/v1
OPENAI_API_KEY=EMPTY
OPENAI_REASONING_EFFORT=
```

脚本会依次 source：

```bash
~/.bashrc
/data/nips/shared_bench/api_config.env
bench/model.env
bench/.env
```

不会把密钥写入脚本。`BENCH_PASS_API_KEY_IN_ARGS=1` 只有在某些 CLI 不能从环境变量读 key 时才开。

## 单独跑

τ²-Bench smoke：

```bash
NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=1 ./run_tau2.sh
```

VitaBench smoke：

```bash
NUM_TASKS=1 NUM_TRIALS=1 VITA_DOMAIN=delivery ./run_vitabench.sh
```

Terminal-Bench smoke / subset：

```bash
NUM_TASKS=1 TB_AGENT=terminus TB_MODEL="$LITELLM_MODEL" ./run_terminal_bench.sh
```

SWE-bench Verified smoke5：先用 SWE-agent 产 patch，再用 SWE-bench harness eval。

```bash
MAX_CONCURRENCY=2 ./run_swebench_verified.sh
```

repo2env tiny agentic smoke：

```bash
./run_repo2env.sh
```

repo2env diagnostic harness smoke，不测模型，只测 benchmark 链路：

```bash
REPO2ENV_MODE=diagnostic_offline ./run_repo2env.sh
```

CoCoA / CocoBench smoke：

```bash
COCOA_TASKS_DIR=cocoabench-example-tasks COCOA_TASKS=linear-regime-estimation ./run_cocoabench.sh
```

RepoZero Py2JS wrapper：

```bash
REPOZERO_MODE=smoke REPOZERO_CASES="base58/test1.py bencoder/test1.py bech32/test1.py fractions/test1.py" ./run_repozero_py2js.sh
```

RepoZero Py2JS full：

```bash
REPOZERO_MODE=full REPOZERO_WORKERS=4 REPOZERO_CODEX_ATTEMPTS=3 ./run_repozero_py2js.sh
```

注意：RepoZero wrapper 默认使用远端 checkout 里的 `tools_repozero_codex_full.py`，输出到 `RepoZero/Py2JS/output_codex/<run_name>`。如果远端项目实际 runner 名字不同，需要设置 `REPOZERO_RUNNER=/path/to/runner.py`。

## 一键 smoke

默认跑相对轻的 5 条：

```bash
./run_all_smoke.sh
```

指定子集：

```bash
BENCHES="tau2 vitabench terminal_bench" ./run_all_smoke.sh
```

## 并发 smoke suite

用 8.130 的 `gpt-5.4-mini` 跑 2-3 并发 smoke：

```bash
SUITE_CONCURRENCY=3 ./run_gpt54mini_smoke_suite.sh
```

用 Qwen/SGLang endpoint 跑同一套 smoke：

```bash
SUITE_CONCURRENCY=3 ./run_qwen_smoke_suite.sh
```

指定 benchmark 子集：

```bash
SUITE_BENCHES="tau2 vitabench terminal_bench cocoabench" ./run_gpt54mini_smoke_suite.sh
```

默认 suite 会跑：

```bash
tau2 vitabench terminal_bench cocoabench repozero_py2js swebench_verified
```

为了控制额度和时间，suite 里每个 benchmark 都会压到最小 smoke：单任务、单 trial、单 worker；suite 层用 `SUITE_CONCURRENCY` 控制同时启动几个 benchmark。

## 输出

默认输出根目录：

```bash
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs
```

每次运行会生成类似：

```bash
runs/<bench>/<model>_<timestamp>/
  run.env.summary
  command.sh
  *.log
```

各 benchmark 自己的原生结果仍保留在原项目目录，例如：

- τ²: `tau2-bench/data/simulations/<save_to>/results.json`
- VitaBench: `VitaBench/data/simulations/<save_to>`
- SWE-bench: `SWE-agent/trajectories/*__<suffix>/preds.json`
- CoCoA: `runs/.../results`

## 当前确认程度

- `tau2`：`.venv/bin/tau2` 已验证可启动，已有 gpt-5.4 smoke 结果。
- `vitabench`：`.venv/bin/vita` 已验证可启动，已有 gpt-5.4 smoke 结果。
- `terminal_bench`：`.venv/bin/tb --help` 已验证可启动，历史有 89 task full run。
- `swebench_verified`：镜像和历史 eval report 足够；脚本依赖 `/data/swe/SWE-agent` 和 conda env。
- `repo2env`：保留独立脚本，但不再放进默认 smoke 或 A+B+CoCoA full suite。
- `cocoabench`：有历史完整 run；脚本走 CocoaAgent 的 `parallel_inference.py`。
- `repozero_py2js`：远端 runner 已核准为 `repozero_eval/RepoZero/tools_repozero_codex_full.py`，历史 smoke 4/4 通过。
## A+B+CoCoA full suite

The selected full suite is configured in:

```bash
bench/configs/gpt54mini_ab_cocoa_full.yaml
```

Historical command from the old shared bench directory; do not treat this as the new deployment target:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
./run_gpt54mini_ab_cocoa_full_suite.sh
```

Equivalent generic entry:

```bash
./run_suite_from_yaml.sh configs/gpt54mini_ab_cocoa_full.yaml
```

The YAML controls the model profile, suite concurrency, per-benchmark worker
budgets, and the selected benchmark list. The current selection is:

```text
tau2_paper_core
vitabench_full
swebench_verified
terminal_bench_2_0
repozero_py2js
cocoabench
```

`terminal_bench_2_0` converts the raw Terminal-Bench 2.0 task layout under
`shared_bench/terminal-bench-2.0` into the local CLI-compatible directory
`shared_bench/terminal-bench-2.0-yaml`, so this entry runs the 89 raw 2.0 tasks
rather than the 241-task `original-tasks` directory. The converter defaults to
local prebuilt images named `tb2-offline/<task>:20260425`; for offline rootless
workers these images must be preloaded from `dev` or shared storage before a
task starts. Set `TB2_USE_PREBUILT_IMAGES=0` only on an internet/build-capable
host. `tau2_paper_core` runs
only airline, retail, and telecom `base` with 4 trials. `cocoabench` points to
`cocoabench-head`; the wrapper auto-enables encrypted-task loading and filters to
the 148 `task.yaml.enc` tasks supported by the current `parallel_inference.py`
runner. The remaining 27 head tasks use the separate
`instruction.md.enc`/`evaluation.md.enc`/`metadata.json.enc` SCALE-style layout
and are skipped unless that runner is extended.
