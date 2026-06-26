# tau3-bench Runtime Image Inventory Round 27

Date: 2026-06-26
Lane: tau3-runtime-image-round27
Host used: `ssh dev`
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Branch: `feat/image-warmup-policy`
Scope: read-only inventory plus this report only. No Docker save/load/pull/run/build, no benchmark run, no model call, no commit/push.

## Executive State

tau3-bench is dataset-ready but still offline-image-blocked. The generated full Harbor dataset exists with 375 task directories and the smoke dataset exists with one task, but no tau3/tau2 image tar, digest manifest, or build log was found in the bounded shared image/log roots. The current suite row remains disabled with `adapter_status: pending_offline_image`, and the bench registry status is `dataset_ready_offline_images_pending`.

No new confirmed bug was found. The current blocker matches the manifest and prior inventory: generated task Dockerfiles still perform `apt-get`, `git clone https://github.com/sierra-research/tau2-bench.git`, and `pip install` during Docker build, which is incompatible with offline worker execution.

## Inputs Inspected

- Image manifest: `manifests/images/tau3_bench.yaml`
- Existing report: `reports/tau3_harbor_adapter_inventory_20260626.md`
- Harbor adapter: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench`
- Full dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench`
- Smoke dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke`
- Upstream tau3 source checkout: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench`
- Shared runner: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh`
- Shared artifact roots checked for tau3/tau2 matches: `agentic-foundation-model-bench/images`, `agentic-foundation-model-bench/manifests`, and `agentic-foundation-model-bench/logs`

## Current Evidence

- `manifests/images/tau3_bench.yaml:4` status is `dataset_ready_offline_images_pending`.
- `manifests/images/tau3_bench.yaml:6-16` points to the adapter, full dataset, smoke dataset, shared runner, 375 tasks, and the offline blocker.
- `manifests/images/tau3_bench.yaml:19-35` has two placeholder image entries, both `registry_status: pending_p0_push_or_shared_tar`.
- `reports/tau3_harbor_adapter_inventory_20260626.md:54-62` records the same two blockers: offline images not ready and Harbor root CLI environment not ready for evaluation smoke.
- `manifests/suite.example.yaml:318-330` keeps `tau3_bench` disabled with `adapter_status: pending_offline_image`, `TAU3_MODE=smoke`, `TAU3_LIMIT=1`, and `TAU3_N_CONCURRENT=1`.
- `manifests/bench_registry.yaml:71-74` marks `tau3_bench` as `dataset_ready_offline_images_pending` and `disabled_until_runtime_images_prebuilt`.
- `_coordination/20260625_harbor_bench/readiness_20260626.json` marks tau3 blocked by `suite_entry_disabled`, `adapter_not_wired`, and `image_manifest_not_materialized`.

Dataset and source inventory:

| Path | State |
| --- | --- |
| Full dataset | Exists, `166M`, 375 task dirs |
| Smoke dataset | Exists, `453K`, 1 task dir |
| Adapter | Exists, `1.8M` |
| Upstream tau3 source checkout | Exists, `957M` |

Observed full dataset counts:

| Domain | Count |
| --- | ---: |
| airline | 50 |
| retail | 114 |
| telecom | 114 |
| banking_knowledge | 97 |
| total | 375 |

Generated file counts and content uniqueness:

| Generated file type | Count | Unique content result |
| --- | ---: | --- |
| `*/environment/Dockerfile` | 375 | one hash: `1863ddddaf284b73f96af00b070f5dfe3cb42f7602ac516a3def590f79ccbd8a` |
| `*/environment/runtime-server/Dockerfile` | 375 | one hash: `c90db88f3c20176a3128e6ffccb3888dcf58c7382fd962abfdf7011a8cbcdcd9` |
| `*/environment/docker-compose.yaml` | 375 | one hash: `e1aa85bb70ab83120e8e863036ea6bb41b600a35a0e5d8b65fce6d0b5a05f1c1` |
| `*/environment/runtime-server/server.py` | 375 | one hash: `0278302be8ec1eaa2beb6865b5b63d80ddb6f1057b21b510ea4f674ee32358ec` |
| `*/environment/runtime-server/task_config.json` | 375 | 375 unique configs, one per task |

This means the image work should produce two shared runtime images, not 375 image builds. The per-task `task_config.json` must remain mounted/copied from each generated task directory or be injected by compose at runtime.

## Image Blocker Details

Smoke main runtime Dockerfile:

- Source: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0/environment/Dockerfile`
- `Dockerfile:1` uses `python:3.12-slim`.
- `Dockerfile:5` defines `TAU2_BENCH_REPO=https://github.com/sierra-research/tau2-bench.git`.
- `Dockerfile:10-14` runs `apt-get`, installs `git`, clones tau2-bench, and runs `pip install --no-cache-dir "${TAU2_BENCH_ROOT}[knowledge]"`.

Smoke MCP sidecar Dockerfile:

- Source: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0/environment/runtime-server/Dockerfile`
- `Dockerfile:1` uses `python:3.12-slim`.
- `Dockerfile:5` defines `TAU2_BENCH_REPO=https://github.com/sierra-research/tau2-bench.git`.
- `Dockerfile:11-16` runs `apt-get`, installs `git`, clones tau2-bench, installs `"${TAU2_BENCH_ROOT}[knowledge]" "fastmcp>=3.0"`, purges git, and removes apt lists.
- `Dockerfile:18-23` copies `server.py` and `task_config.json`, exposes port 8000, and starts `python3 server.py`.

Compose and task contracts:

- `/environment/docker-compose.yaml:7-9` builds `tau3-runtime` from `./runtime-server` instead of referencing an image.
- `/environment/docker-compose.yaml:10-16` passes model/base-url env vars and mounts Harbor agent logs.
- `/task.toml:32-35` exposes the MCP server at `http://tau3-runtime:8000/mcp`.
- `/tests/test.sh:7-14` expects `/opt/tau2-bench` and `/opt/tau2-bench/data`, then runs `/tests/evaluate.py` against `/logs/agent/tau3_runtime_state.json`.
- `/tests/evaluate.py:12-16` also defaults to `/opt/tau2-bench` and model-backed natural-language assertions unless overridden.
- `/environment/runtime-server/server.py:42-65` requires tau2 sources and data under `/opt/tau2-bench`.

Upstream tau3 dependency constraints:

- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench/pyproject.toml:10` requires Python `>=3.12,<3.14`.
- `pyproject.toml:16-36` lists core runtime dependencies including FastAPI, uvicorn, pandas, litellm, requests, numpy, etc.
- `pyproject.toml:58-61` defines the required `knowledge` extra: `rank-bm25` and `openai`.
- The generated sidecar also requires `fastmcp>=3.0`.

## Required Dockerfiles and Images

Required image 1: `tau3-harbor-main-runtime`

- Purpose: Harbor task main container and verifier/oracle runtime.
- Must contain Python 3.12, the local tau2/tau3 source checkout at `/opt/tau2-bench`, tau2 installed with the `knowledge` extra, and data under `/opt/tau2-bench/data`.
- Should replace the generated `environment/Dockerfile` network build with a digest-pinned image reference.
- Current generated Dockerfile can be used only as a behavior reference, not as an offline worker build recipe.

Required image 2: `tau3-harbor-mcp-runtime`

- Purpose: `tau3-runtime` MCP sidecar at `http://tau3-runtime:8000/mcp`.
- Must contain the same tau2/tau3 runtime plus `fastmcp>=3.0`.
- Must support task-specific `server.py` and `task_config.json` injection. Because `task_config.json` is unique for all 375 tasks, the final wiring should either keep a tiny per-task derived build that starts `FROM <digest-pinned-mcp-runtime>` and only `COPY`s local task files, or update compose to mount/copy the task files without network access.
- Current generated compose must change from `build: { context: ./runtime-server }` to a digest-pinned image path or an offline-only derived local context.

No separate database image was found in the generated tau3 task material. Domain state is managed through tau2 source/data inside the runtime images, with per-task config and runtime log state under Harbor paths.

## Build and Staging Plan

Do not run these from the inventory lane. These are the concrete next commands for a future image materialization lane.

### Phase A: prepare immutable build context on internet-enabled `dev`

Use `dev` for source/context verification and optional dependency lock preparation, not Docker-heavy work:

```bash
ssh dev
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy

TAU3_SRC=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench
TAU3_CTX=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/build_contexts/tau3-runtime-20260626
rm -rf "$TAU3_CTX"
mkdir -p "$TAU3_CTX"
rsync -a --delete --exclude .git --exclude .venv --exclude data/simulations "$TAU3_SRC/" "$TAU3_CTX/tau2-bench/"
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0/environment/runtime-server/server.py "$TAU3_CTX/server.py"
sha256sum "$TAU3_CTX/server.py" > "$TAU3_CTX/server.py.sha256"
find "$TAU3_CTX/tau2-bench" -maxdepth 3 -type f | sort > "$TAU3_CTX/source-files.list"
```

If `swe_dev2` cannot reach public package indexes during build, add a wheelhouse step on `dev` before handoff:

```bash
python3.12 -m pip download -d "$TAU3_CTX/wheelhouse" "$TAU3_CTX/tau2-bench[knowledge]" "fastmcp>=3.0"
find "$TAU3_CTX/wheelhouse" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > "$TAU3_CTX/wheelhouse.sha256"
```

### Phase B: build and push on Docker-heavy `swe_dev2`

Per WORKFLOW, use `swe_dev2` for new image prewarm/eval shards and the P0 OCI registry at `100.97.118.137:8555`. Do not run this from `dev` or the offline worker.

```bash
ssh swe_dev2
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/build_contexts/tau3-runtime-20260626

REG=100.97.118.137:8555
NS=agentic-foundation-model-bench
TAG_DATE=20260626

mkdir -p /etc/docker/certs.d/$REG
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt /etc/docker/certs.d/$REG/ca.crt

docker build -f Dockerfile.main -t "$REG/$NS/tau3-harbor-main-runtime:$TAG_DATE" .
docker build -f Dockerfile.mcp -t "$REG/$NS/tau3-harbor-mcp-runtime:$TAG_DATE" .

docker push "$REG/$NS/tau3-harbor-main-runtime:$TAG_DATE"
docker push "$REG/$NS/tau3-harbor-mcp-runtime:$TAG_DATE"

docker inspect --format='{{index .RepoDigests 0}}' "$REG/$NS/tau3-harbor-main-runtime:$TAG_DATE"
docker inspect --format='{{index .RepoDigests 0}}' "$REG/$NS/tau3-harbor-mcp-runtime:$TAG_DATE"
```

If registry push is not available, produce shared fallback tars and checksums from `swe_dev2`:

```bash
OUT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/tau3-bench/20260626
mkdir -p "$OUT"
docker save "$REG/$NS/tau3-harbor-main-runtime:$TAG_DATE" -o "$OUT/tau3-harbor-main-runtime_${TAG_DATE}.tar"
docker save "$REG/$NS/tau3-harbor-mcp-runtime:$TAG_DATE" -o "$OUT/tau3-harbor-mcp-runtime_${TAG_DATE}.tar"
sha256sum "$OUT"/*.tar > "$OUT/SHA256SUMS"
```

### Phase C: future manifest/dataset wiring

After images exist, update only in a separate manifest/code lane:

- `manifests/images/tau3_bench.yaml`: replace placeholders with digest refs and fallback tar/checksum paths.
- Generated dataset template or generated task files: replace network-building Dockerfiles with digest-pinned images.
- `docker-compose.yaml`: replace `tau3-runtime.build.context: ./runtime-server` with an `image:` ref or an offline-only derived build that performs no apt/git/pip network work.
- Keep `task_config.json` per task; do not bake all 375 configs into one immutable image unless Harbor can select the right config at runtime.

## Dockerfile Patch Concept

Main runtime image concept:

```dockerfile
FROM python:3.12-slim
ENV TAU2_BENCH_ROOT=/opt/tau2-bench
ENV TAU2_DATA_DIR=/opt/tau2-bench/data
WORKDIR /app
COPY tau2-bench /opt/tau2-bench
RUN python3 -m pip install --no-cache-dir "/opt/tau2-bench[knowledge]"
```

MCP runtime image concept:

```dockerfile
FROM python:3.12-slim
ENV TAU2_BENCH_ROOT=/opt/tau2-bench
ENV TAU2_DATA_DIR=/opt/tau2-bench/data
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY tau2-bench /opt/tau2-bench
COPY server.py /app/server.py
RUN python3 -m pip install --no-cache-dir "/opt/tau2-bench[knowledge]" "fastmcp>=3.0"
EXPOSE 8000
CMD ["python3", "server.py"]
```

If `swe_dev2` is not allowed public egress during Docker build, replace the `pip install` lines with a wheelhouse install:

```dockerfile
COPY wheelhouse /wheelhouse
RUN python3 -m pip install --no-index --find-links=/wheelhouse "/opt/tau2-bench[knowledge]" "fastmcp>=3.0"
```

## Offline Worker Smoke Plan

Do not run these until images are staged and digest/tar metadata exists.

Worker static smoke, no model call:

```bash
ssh worker
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only tau3_bench --model-profile dev_proxy_gpt54mini_8130
```

Worker image availability smoke, offline Docker only after explicit image preload policy is approved:

```bash
ssh worker
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
REG=100.97.118.137:8555
mkdir -p /root/.config/docker/certs.d/$REG /tmp/rl/data/certs.d/$REG
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt /root/.config/docker/certs.d/$REG/ca.crt
cp /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt /tmp/rl/data/certs.d/$REG/ca.crt
# Then either pull by P0 digest if registry access is allowed on worker, or docker load from the shared fallback tar.
docker image inspect <digest-pinned-main-runtime-ref>
docker image inspect <digest-pinned-mcp-runtime-ref>
```

Worker one-task runtime smoke, no model call preferred:

```bash
ssh worker
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench
TAU3_MODE=smoke TAU3_LIMIT=1 TAU3_RUN_HARBOR=1 TAU3_GENERATE_DATASET=0 TAU3_AGENT_IMPORT_PATH=oracle ./run_tau3_bench.sh
```

If `TAU3_AGENT_IMPORT_PATH=oracle` is not supported by the Harbor CLI path, use `uv run harbor trial start -p <smoke-task-dir> -a oracle` inside the prebuilt Harbor runner environment. Do not use `tau3_llm_agent` for offline smoke unless a model-call lane is explicitly approved.

## Risks and Blockers

1. No staged image artifacts exist yet. Bounded shared checks found zero tau3/tau2 matches under the shared `images`, `manifests`, and `logs` roots.
2. Current generated Dockerfiles are not offline-safe because they use apt, git clone, and pip install at build time.
3. The sidecar image needs a clean contract for per-task `task_config.json`; blindly baking one smoke task config into a shared sidecar image would be wrong for the other 374 tasks.
4. Harbor root CLI environment remains a separate blocker from image staging. Prior report records that `uv run --no-dev harbor --help` tried heavy sync and hit CUDA wheel/mirror problems; a minimal Harbor runner venv or prebuilt Harbor runner image is still needed before full evaluation smoke.
5. Some tau3 verification paths use model-backed user simulation and natural-language assertion evaluation. Offline no-model smoke should prefer oracle/static runtime checks first.

## ISSUE-READY

No new issue. Evidence: the manifest, suite row, registry row, readiness snapshot, generated Dockerfiles, and prior tau3 inventory all consistently record the same pending offline image state. The confirmed blocker is already represented as `pending_offline_image` / `image_manifest_not_materialized`, not a newly discovered contradiction.

## Commands Run

All commands were run from the local control plane through `ssh dev` unless noted. No Docker command, benchmark run, or model call was executed.

| Command | rc | Notes |
| --- | ---: | --- |
| `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required preflight, local control plane. |
| `sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Continued workflow read. |
| `sed -n '621,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Continued workflow read. |
| `rg -n "tau3|tau3-bench|..." /Users/Zhuanz1/.codex/memories/MEMORY.md` | 1 | No relevant memory hit; no memory evidence used. |
| `ssh dev 'cd <worktree> && pwd && git branch --show-current && git log --oneline -1 && git status --short -- <target files>'` | 0 | Confirmed branch `feat/image-warmup-policy`, clean target status. |
| `ssh dev 'cd <worktree> && sed -n "1,260p" manifests/images/tau3_bench.yaml'` | 0 | Read required image manifest. |
| `ssh dev 'cd <worktree> && sed -n "1,360p" reports/tau3_harbor_adapter_inventory_20260626.md'` | 0 | Read required inventory report. |
| `ssh dev 'du/find adapter, dataset, smoke dataset, upstream checkout'` | 0 | Inventory paths and files. |
| `ssh dev 'find upstream checkout key Docker/YAML/README/pyproject files'` | 0 | No upstream Dockerfile found in bounded scan. |
| `ssh dev 'nl -ba generated Dockerfile/runtime Dockerfile/compose/task.toml'` | 0 | Located exact offline blockers. |
| `ssh dev 'nl -ba adapter.py/main.py/run_tau3-bench.yaml'` | 0 | Inspected generator and run config. |
| `ssh dev 'nl -ba runtime server, task_config, test.sh, evaluate.py'` | 0 | Inspected sidecar and verifier contract. |
| `ssh dev 'rg/grep docker,image,runtime,compose,mcp,... over adapter/datasets/source snippets'` | 0 | Confirmed recurring offline build strings. Output was bounded/truncated by `sed`. |
| `ssh dev 'find counts and hash uniqueness for full generated dataset'` | 0 | Initial hash attempt had shell quoting errors for `awk`, then was rerun safely. Counts were valid. |
| `ssh dev 'find/sha256sum/cut/uniq hash uniqueness for generated files'` | 0 | Confirmed one shared main Dockerfile, runtime Dockerfile, compose, and server.py; 375 unique task configs. |
| `ssh dev 'find shared roots for tau3/tau2 image/log/manifest matches'` | 0 | Found no image tar/manifest/log artifacts in bounded shared roots. |
| `ssh dev 'nl -ba run_tau3_bench.sh and list verification artifacts'` | 0 | Inspected runner and existing redaction artifacts. |
| `ssh dev 'nl -ba upstream pyproject and README install section'` | 0 | Confirmed Python and dependency constraints. |
| `ssh dev 'rg tau3 refs in manifests/reports/coordination'` | 0 | Cross-checked prior state and readiness references. |
| `ssh dev 'domain counts, sizes, suite lines, registry lines, readiness excerpt, shared artifact match counts'` | 0 | Final metadata pass. |
| `ssh dev 'test whether target report exists'` | 0 | Target report was missing before this write. |
| `ssh dev 'command -v apply_patch || true'` | 0 | Remote helper absent. |
| `rg -n "P0|registry|Docker|..." /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Confirmed `swe_dev2`, P0 registry, and worker Docker socket guidance. |
| `ssh dev 'cd <worktree> && cat > _coordination/.../tau3-runtime-image-round27.md' <<'EOF'` | 0 | Created this single allowed report. |
