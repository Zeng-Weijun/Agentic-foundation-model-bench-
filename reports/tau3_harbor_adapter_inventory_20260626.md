# tau3-bench Harbor Adapter Inventory - 2026-06-26

## Status

- Active direction: tau3-bench replaces the old customer-service smoke path in the suite.
- Harbor adapter exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench`.
- Shared runner exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh`.
- The suite entry `tau3_bench` now points at `manifests/images/tau3_bench.yaml` and remains disabled until offline runtime images are staged.

## Dataset Evidence

Generated from the local upstream tau3 source checkout:

```text
TAU3_SOURCE_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench
```

Generated datasets:

```text
smoke: /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke
full:  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench
```

Counts observed after generation:

```text
total=375
airline=50
retail=114
telecom=114
banking_knowledge=97
```

Smoke dataset contains `tau3-airline-0` and has the expected Harbor task files:
`task.toml`, `instruction.md`, `environment/Dockerfile`, `environment/docker-compose.yaml`, `environment/runtime-server/Dockerfile`, `tests/test.sh`, and `tests/evaluate.py`.

## Runner Evidence

Dry-run command verified with a synthetic API key and checked for redaction:

```text
DRY_RUN=1 TAU3_RUN_HARBOR=0 TAU3_GENERATE_DATASET=0 ./run_tau3_bench.sh
```

Verification artifact:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/verification/tau3_secret_redaction_20260626_0048
```

The dry-run records a Harbor command with `${OPENAI_API_KEY}` placeholders; it does not write the actual key to stdout or `command.sh`.

## Current Blockers

1. Offline Docker images are not ready.

The generated Harbor task Dockerfiles currently run `apt-get`, `git clone https://github.com/sierra-research/tau2-bench.git`, and `pip install` during Docker build. That cannot work on the offline worker. The required next step is to prebuild the main runtime and `tau3-runtime` MCP sidecar images on `swe_dev`/`swe_dev2`, push digest-pinned refs to the P0 registry or stage verified shared tars, and rewrite or parameterize the generated Dockerfiles/compose files to use those local images.

2. Harbor root CLI environment is not ready enough for evaluation smoke.

`uv run --no-dev harbor --help` attempted to sync heavy packages and hit the internal PyPI mirror on a CUDA wheel. A second attempt with `--no-default-groups --no-group dev --python 3.12` still exceeded the interactive sync window and was interrupted. Dataset generation through the adapter works; full Harbor job execution is pending a minimal Harbor venv or a prebuilt Harbor runner environment.

## Next Steps

- Build tau3 main/runtime base images without public network dependency, using the local upstream tau3 checkout baked into the image.
- Push or tar those images and update `manifests/images/tau3_bench.yaml` with exact local refs, digest refs, fallback tar checksums, and smoke commands.
- Re-enable `tau3_bench` in `manifests/suite.example.yaml` only after image preflight can pass on worker.
- Run `run_tau3_bench.sh` first with oracle or one-task `tau3_llm_agent`, then scale `TAU3_N_CONCURRENT` within the 40-50 relay envelope.
