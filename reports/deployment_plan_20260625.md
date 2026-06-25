# Agentic Foundation Model Bench Deployment Plan

Date: 2026-06-25

This is the integration plan for the new GitHub repository and the future shared-disk deployment orchestrated from `dev`. Rootless workers are separate execution nodes and may be offline.

## Decision Summary

1. GitHub should contain source, docs, manifests, schema, and lightweight runner wrappers.
2. Shared storage should contain datasets, harness checkouts, model/runtime paths, run artifacts, large traces, and benchmark outputs.
3. `dev` is the control/staging host for setup, downloads, manifest creation, queueing, and worker dispatch. Offline workers should only consume pre-staged assets.
4. The new shared-disk project should use a clean root:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
```

5. The deployment should inherit the proven `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench` layout pattern:

```text
benchmark/scaffold/run.sh
benchmark/scaffold/config.yaml
shared/run_code_model_suite_from_yaml.sh
shared/runners/run_<bench>_<scaffold>.sh
runs/<suite_id>/script_snapshots/
runs/<suite_id>/<bench>/artifact_manifest.json
```

6. Do not treat current `run_*.sh` scripts as rootless worker infrastructure. They are runner adapters. Add a worker layer above them.

## GitHub Repository Scope

Repository:

```text
https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-.git
```

Recommended first version:

```text
Agentic-foundation-model-bench-/
├── README.md
├── reports/
│   ├── README.md
│   ├── agentic_bench_landscape_20260625.md
│   ├── agentic_bench_matrix_20260625.csv
│   ├── shared_disk_layout_research_20260625.md
│   ├── rootless_worker_research_20260625.md
│   ├── deployment_plan_20260625.md
│   ├── qwen3_coder_swebench_qwen_code_retry_cases_20260529.md
│   └── trace_manifest_template.yaml
├── manifests/
│   ├── README.md
│   ├── datasets.example.yaml
│   ├── harnesses.example.yaml
│   ├── models.example.yaml
│   └── runs.schema.json
├── scripts/
│   └── README.md
└── traces/
    └── README.md
```

Do not put the full local `bench/` directory into GitHub yet. It contains historical runner scripts and local assumptions that need pruning before they become public/source-of-truth.

## Shared Disk Target Layout

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/
├── README.md
├── BENCH_LAYOUT.md
├── datasets/
├── harnesses/
├── models/
├── configs/
├── scripts/
├── shared/
├── runs/
├── traces/
├── reports/
├── manifests/
└── tmp/
```

### `datasets/`

Manifest-first. Do not copy large datasets until we explicitly freeze them.

Example pointers:

```text
/data/swe/datasets/SWE-bench_Verified
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/datasets
```

### `harnesses/`

Record existing harness/runtime checkouts:

```text
/data/swe/SWE-bench
/data/swe/SWE-agent
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/agent_scaffolds
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen
```

Each harness manifest should include:

- path
- version
- source commit if available
- local patches if any
- smoke status
- known limitations

### `models/`

Record model weights and serving endpoints, not model files.

Example:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct
http://100.103.11.77:8503/v1
```

### `runs/`

All durable outputs go here:

```text
runs/<bench>/<scaffold>/<run_id>/
```

Required:

```text
run_manifest.json
worker_manifest.json
trace_manifest.yaml
artifact_manifest.json
run.env.summary
command.sh
controller.log
worker.log
runner.log
summary.json
```

### `traces/`

Large agent-native traces can remain in native paths if every run has a manifest pointer. For public GitHub, store only trimmed case studies or trace indexes unless the raw trace is small and license-safe.

## Worker Architecture

```text
local Mac control plane
  └── local tmux session
        └── ssh dev
              └── controller creates run manifests, stages assets, and owns the worker queue
                    └── ssh/offline dispatch to rootless worker process
                          └── existing benchmark runner adapter
                                └── Docker/Podman rootless container tasks
```

Worker contract:

- non-root user
- explicit `DOCKER_HOST`
- explicit `controller_host=dev`
- explicit `execution_host` / `worker_host`
- explicit `network_policy`, defaulting to `offline_or_internal_only`
- unique `worker_id`
- unique `COMPOSE_PROJECT_NAME`
- isolated `<worker_tmp_root>/<worker_id>`
- artifact root under shared storage
- no API keys in files
- no shared mutable checkout config
- no public internet downloads, git fetches, dependency installs, or image pulls from the worker

## First Milestones

### M0: GitHub Dossier

Goal:

- Push the report/dossier-only repository.
- No runner claims yet.

Deliverables:

- `reports/agentic_bench_landscape_20260625.md`
- `reports/agentic_bench_matrix_20260625.csv`
- `reports/shared_disk_layout_research_20260625.md`
- `reports/rootless_worker_research_20260625.md`
- `reports/deployment_plan_20260625.md`
- `reports/trace_manifest_template.yaml`

### M1: Shared Disk Skeleton

Goal:

- Create the clean shared root and empty skeleton directories.
- Add manifests with pointers to existing datasets/harnesses/models.
- Run this from `dev`.

No benchmark runs.

### M2: Rootless Preflight

Goal:

- Prove or disprove usable rootless Docker/Podman on the offline worker after the user opens it.
- Record `worker_manifest.json`.
- Record `controller_host=dev`, `worker_host`, `execution_host`, `worker_network=offline_or_internal_only`, and shared-mount availability.

Checks:

- user/uid/gid
- `XDG_RUNTIME_DIR`
- `DOCKER_HOST`
- engine info
- compose version
- bind-mount read/write/delete
- network reachability to internal model endpoint
- absence of public internet dependency during the smoke

### M3: No-Model Smoke

Goal:

- Prepare or verifier-only tasks without model calls.
- Prove dataset/harness/container path.

Candidates:

- Qwen native SWE-bench prepare-only
- Terminal-Bench compose generation
- CoCoA prepare-only if checkout is located
- repo2env diagnostic offline if relevant

### M4: One-Task Smoke

Run one task per benchmark family with strict manifest capture.

Suggested order:

1. tau2 or tau3 minimal task if harness is pinned
2. RepoZero tiny case
3. Terminal-Bench one rootless-compatible task
4. SWE-bench Verified one known instance
5. DeepSWE one task

### M5: Two-Worker Smoke

Goal:

- Prove no collisions in run dirs, compose project names, ports, OpenHands configs, and temp dirs.

### M6: Full Benchmark Campaigns

Only after M0-M5 are complete.

## Immediate Risks

- The previous `swe_dev` root/empty-`XDG_RUNTIME_DIR` observation is historical evidence, not the new target. The new worker's user, UID/GID, `XDG_RUNTIME_DIR`, and rootless engine are unknown.
- Offline workers cannot pull images, fetch repos, install packages, or download datasets at run time; all large assets and dependencies must be staged from `dev`.
- Rootful Docker image caches may not be visible to rootless engines.
- `host.docker.internal` may not work in rootless containers; DeepSWE depends on it for API relay.
- The offline worker may not reach internal model endpoints directly; model traffic may need a `dev`-side relay/proxy if allowed.
- OpenHands wrapper mutates a shared config path; this is unsafe under concurrent workers.
- Terminal-Bench tasks may require capabilities unavailable under rootless containers.
- Qwen native runner internals need inspection for Docker assumptions.
- CoCoA checkout path drifted; default inspected path was missing.
- DeepSWE failure artifacts must separate infra failures from model failures.
- MCP/tau3/tool benchmarks still need server reset and state snapshot contracts.

## Next Actions

1. Push the dossier-only GitHub repository.
2. Add `manifests/*.example.yaml` and `runs.schema.json`.
3. Create the shared-disk skeleton under the clean project root from `dev`.
4. Collect worker facts once the user opens the worker: SSH alias/user, hostname, UID/GID, shared mount, tmp root, rootless engine, `DOCKER_HOST`, `XDG_RUNTIME_DIR`, and model endpoint reachability.
5. Pre-stage required images/dependencies from `dev`; do not rely on worker internet.
6. Run rootless preflight only after explicit permission.
7. Convert one existing SWE-bench Verified scaffold into the new manifest contract before expanding to other benchmarks.
