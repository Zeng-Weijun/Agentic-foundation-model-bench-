# Shared Disk Benchmark Layout Research

Date: 2026-06-25

Research mode: read-only. No files were edited on `swe_dev`; no benchmarks, Docker jobs, or model calls were started.

Note after 2026-06-25 user override: this report preserves observed `swe_dev` paths as historical evidence. Future operations for this project should be orchestrated from `dev`, with separate offline rootless workers as execution nodes.

## Executive Summary

There are two benchmark layouts on the shared storage:

1. Older unified launcher layer:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
```

This contains useful scripts, configs, reports, and DeepSWE artifacts, but it is not the cleanest long-term project layout.

2. Newer projectized benchmark layer:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench
```

This is the better structural model to inherit. It already separates `shared/` runner logic from benchmark/scaffold directories such as `swe-bench-verified/qwen-code`, `swe-bench-verified/mini-swe-agent`, `swe-bench-verified/swe-agent`, and `swe-bench-verified/openhands`.

The new `Agentic-foundation-model-bench-` project should not treat `nips2026/bench` as the final structure source. It should inherit the second-generation layout pattern from `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench`, while keeping GitHub as a lightweight source repo and shared storage as the dataset/runtime/run artifact root.

## Existing Layouts

### Older Unified Launcher Layer

Observed high-level structure:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
├── configs/
│   └── code_models/
├── deep-swe/
├── lib/
├── profiles/
├── reports/
├── runs/
│   └── deepswe/
├── scripts/
├── run_*.sh
└── README.md
```

This directory matches the local launcher repo structure under:

```text
/Users/Zhuanz1/Desktop/ssh_work/paper_reading/bench
```

Local `README.md` says this directory was created to collect several runnable `swe_dev` benchmarks under one entrypoint, with default outputs under:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs
```

Observed limitation:

- Remote `nips2026/bench/runs/code_model_suites` was not present in the bounded inspection.
- Current visible artifacts were mainly under `runs/deepswe`.
- This looks like an early unified launcher and DeepSWE output location rather than the clean current SWE-bench Verified production layout.

### Newer Projectized Benchmark Layer

Observed high-level structure:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench
├── BENCH_LAYOUT.md
├── README.md
├── shared/
│   ├── run_code_model_suite_from_yaml.sh
│   ├── lib/bench_common.sh
│   ├── runners/run_*.sh
│   ├── scripts/
│   ├── profiles/
│   ├── env/
│   └── archive/
├── swe-bench-verified/
│   ├── qwen-code/
│   ├── mini-swe-agent/
│   ├── swe-agent/
│   ├── openhands/
│   ├── awe-agent/
│   ├── harness/
│   ├── image_migration/
│   ├── reports/
│   ├── scaffold_versions.yaml
│   └── swe-agent-runtime/
├── terminalbench2.0/
├── terminalbench2.1/
├── cocoabench/
├── repozero/
├── tau2-bench/
├── vitabench/
├── deepswe/
├── featurebench/
├── swe-prbench/
└── swe-atlas/
```

The key rule in this layout is:

```text
bench/<benchmark>/<scaffold>/
```

Root-level benchmark directories remain visible; shared logic lives under `shared/`; old scripts and old outputs go under `shared/archive/`.

## SWE-bench Verified Current Structure

Current main path:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified
```

Observed scaffold split:

```text
swe-bench-verified/
├── qwen-code/
│   ├── run.sh
│   ├── config.yaml
│   ├── config.qwen3_30b_a3b_instruct_2507.yaml
│   └── runs/
├── mini-swe-agent/
│   ├── run.sh
│   ├── config.yaml
│   ├── agent_config.yaml
│   └── runs/
├── swe-agent/
│   ├── run.sh
│   ├── config.yaml
│   ├── official_swe_agent_qwen_function_calling.yaml
│   ├── official_swe_agent_qwen_thought_action.yaml
│   └── runs/
├── openhands/
│   ├── run.sh
│   ├── config.yaml
│   └── runs/
├── awe-agent/
│   ├── run_scale_swe_agent.sh
│   ├── run_from_yaml.sh
│   ├── configs/
│   ├── scripts/
│   ├── runs/
│   └── README.md
├── harness/
│   ├── rootless_worker_*.sh
│   ├── rootless_worker_*.yaml
│   └── rootless_worker_README.md
├── image_migration/
├── reports/
└── scaffold_versions.yaml
```

The scaffold entrypoints follow a common pattern:

```bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONFIG="$SCRIPT_DIR/config.yaml"
exec "$BENCH_ROOT/shared/run_code_model_suite_from_yaml.sh" "$CONFIG" "$MODE"
```

This is the right pattern to preserve:

- Each scaffold owns a small `run.sh` and `config.yaml`.
- Shared suite execution lives in `shared/run_code_model_suite_from_yaml.sh`.
- Shared benchmark adapters live in `shared/runners/run_*.sh`.
- Shared environment handling lives in `shared/lib/bench_common.sh`.

## Dataset, Harness, Runtime Pointers

SWE-bench Verified dataset and harness paths:

```text
/data/swe/datasets -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/datasets
/data/swe/datasets/SWE-bench_Verified/data/test-00000-of-00001.parquet
/data/swe/SWE-bench -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/repos/SWE-bench
/data/swe/SWE-agent -> /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/agent_scaffolds/SWE-agent-official-main-20260529_225705
```

Shared scaffold/runtime assets:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/agent_scaffolds
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/SWE-bench
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev
```

Scaffold pin file:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/scaffold_versions.yaml
```

Observed pin semantics:

- Qwen Code current used version: `@qwen-code/qwen-code 0.15.6`
- Qwen Code latest checked: `0.16.2`, installed but not smoked in the inspected note
- SWE-agent current executable: `/data/conda_envs/sweagent/bin/sweagent`
- OpenHands current version: `0.54.0` under shared bench runtime
- mini-swe-agent: `v2.3.0` in the older manifest context

## Run Artifact Contract To Preserve

The current second-generation layout records enough material to support later audit. Preserve and strengthen this pattern:

```text
runs/<suite_id>/
  config.snapshot.yaml
  suite.env.summary
  summary.tsv
  summary.printed.tsv
  logs/<bench>.log
  status/<bench>.status
  script_snapshots/
    config.yaml
    entrypoint__run.sh
    run_code_model_suite_from_yaml.sh
    bench__run_<bench>.sh
    lib__bench_common.sh
    SHA256SUMS
  <bench>/
    artifact_manifest.json
    command.sh or command.log
    eval_command.sh
    agent traces / outputs
    result files
```

Observed trace-root conventions:

```text
qwen-code:      swebench_verified_qwen_code/qwen_native_outputs/<run_name>/
mini-swe-agent: swebench_verified_mini_swe_agent/mini_swe_agent_outputs/
swe-agent:      swebench_verified_swe_agent/sweagent_output
openhands:      swebench_verified_openhands/openhands_output
awe-agent:      swebench_verified_awe_agent/...
```

## Reusable Assets

Use these as structural inputs for the new project:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/BENCH_LAYOUT.md
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/README.md
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/run_code_model_suite_from_yaml.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/lib/bench_common.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_qwen_code.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_mini_swe_agent.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_swe_agent.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_openhands.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/*/run.sh
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/*/config.yaml
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/scaffold_versions.yaml
```

Treat these as external runtime dependencies, not GitHub source payload:

```text
/data/swe/datasets/SWE-bench_Verified
/data/swe/SWE-agent
/data/swe/SWE-bench
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/agent_scaffolds
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen
/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct
```

These should be represented through manifests containing paths, versions, smoke status, source commits, and checksums where possible.

## Historical Or Risky Material

Do not treat these as mainline launch paths:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/archive/*
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_*.sh old copies
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs_local_logs
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/SMOKE_RESULTS_20260526.md
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/eval_reports/aci_evolve_*.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/repos/SWE-bench/aci_*.json
```

Special caution:

- `swe-agent/*thought_action*` should remain diagnostic unless revalidated. Prior prompt-setting notes indicated thought-action mode produced syntax/empty-patch style failures.
- OpenHands in the newer `swe-bench-verified/openhands/runs` layout had no completed run in the bounded inspection. Treat it as configured but not equivalently validated.

## Recommended New Shared Root

Recommended new project root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
```

Proposed layout:

```text
agentic-foundation-model-bench/
├── README.md
├── BENCH_LAYOUT.md
├── datasets/
│   ├── swe-bench-verified/
│   │   ├── manifest.yaml
│   │   └── README.md
│   ├── terminal-bench-2.1/
│   ├── deepswe/
│   └── repozero/
├── harnesses/
│   ├── swe-bench/
│   ├── qwen-native-swebench/
│   ├── mini-swe-agent/
│   ├── swe-agent/
│   ├── openhands/
│   └── awe-agent/
├── models/
│   ├── configs/
│   ├── serving/
│   └── pins/
├── configs/
│   ├── suites/
│   ├── swe-bench-verified/
│   └── profiles/
├── scripts/
│   ├── run_from_yaml.sh
│   ├── run_code_model_suite_from_yaml.sh
│   ├── run_swebench_verified_qwen_code.sh
│   ├── run_swebench_verified_mini_swe_agent.sh
│   ├── run_swebench_verified_swe_agent.sh
│   ├── run_swebench_verified_openhands.sh
│   └── serve/
├── runs/
│   ├── swe-bench-verified/
│   ├── terminal-bench-2.1/
│   └── deepswe/
├── traces/
│   ├── swe-bench-verified/
│   └── by-run/
├── reports/
│   ├── landscape/
│   ├── scaffold_prompt_settings/
│   ├── scorecards/
│   └── run_audits/
├── manifests/
│   ├── datasets.yaml
│   ├── harnesses.yaml
│   ├── models.yaml
│   └── runs.schema.json
└── tmp/
```

## Open Questions

- Endpoint health was not checked.
- SWE-bench Verified parquet row count/hash was not checked.
- Docker image cache completeness was not checked.
- OpenHands completed full run in the new layout was not found.
- mini-swe-agent final score summary was not read.
- SWE-agent function-calling full-run status was not verified.
- Remote dirty git status and source commit pins were not audited.
- Directory sizes were intentionally not scanned.
