# tau3-bench Adapter Smoke Plan Round 28

Date: 2026-06-26
Lane: tau3 adapter support
Scope: report-only; no production code, manifest, commit, Docker, benchmark, or model-call changes were made.

## Bottom line

tau3-bench is now image-ready but not adapter-smoke-ready. The r2 main and runtime smoke images are recorded in `manifests/images/tau3_bench.yaml`, have shared tars/checksums, and are marked worker-rootless smoked. The minimal next step is a one-task Harbor oracle smoke against a patched smoke dataset copy, using the r2 prebuilt main image plus the r2 prebuilt `tau3-runtime` sidecar image. That smoke should make no model calls, require no public network, and run only after the worker can inspect the two r2 image digests from local cache or the internal P0 registry.

The current blocker is adapter wiring, not image materialization. The generated smoke task and shared runner still assume model-backed `tau3_llm_agent`, required OpenAI env placeholders, and public-network Docker builds.

## Current evidence

### Image manifest state

`manifests/images/tau3_bench.yaml` records status `smoke_images_ready_worker_rootless` and says the remaining blocker is that the suite adapter is not wired yet. The new r2 image refs are:

| Role | Digest ref | Shared tar | Tar sha256 |
| --- | --- | --- | --- |
| main | `100.97.118.137:8555/swe-data-harness/tau3-smoke-main@sha256:571aa921fc1eda999b9fc124a266900c6b10a4aceba9283e6f9867f9a44788e4` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke-main_20260626r2.tar` | `cfb1207cf33fa152ee99b01b10b7ff229bb2cdcb847a39d0fc47771f891f2b64` |
| runtime | `100.97.118.137:8555/swe-data-harness/tau3-smoke-runtime@sha256:290a4f09c7ade3a1e7a08dfd3d4c6d0951b4ae519eae12d2fe1ccb99745dc699` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke-runtime_20260626r2.tar` | `2503e032377986ffef80b935035e279a52e1a13807a6fa1e7fb65d6033615d85` |

Local artifact files confirm the repo-digest and sha256 sidecar files at:

- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke_20260626r2.repo-digests`
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke_20260626r2.sha256`

Manifest evidence says worker rootless Docker needed `DOCKER_API_VERSION=1.45`, because the worker Docker CLI default `/version` path panics.

### Existing tau3 paths

| Item | Path | State |
| --- | --- | --- |
| Harbor adapter | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench` | Exists per manifest/report evidence. |
| Full dataset | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench` | Exists per manifest/report evidence. |
| Smoke dataset | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke` | Exists; one task inspected. |
| Smoke task | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0` | Current patch target for the first smoke copy. |
| Shared runner | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh` | Exists but currently hard-codes the model agent path. |

### Why current smoke is not yet no-model/offline safe

1. `run_tau3_bench.sh` always builds a Harbor command with `-a tau3_llm_agent`, `--agent-import-path adapters.tau3-bench.tau3_llm_agent:Tau3LLMAgent`, `-m "$MODEL_NAME"`, and OpenAI env forwarding. It also defaults `TAU3_USER_MODEL` and `TAU3_NL_ASSERTIONS_MODEL` from `MODEL_NAME`, so an oracle run cannot be selected cleanly today.
2. The generated smoke `task.toml` requires `OPENAI_API_KEY` and `OPENAI_BASE_URL` in both verifier and environment env maps. Harbor's env resolver treats `${VAR}` without a default as required and exits before the run if it is unset.
3. The smoke task's `environment/Dockerfile` still performs `apt-get`, `git clone https://github.com/sierra-research/tau2-bench.git`, and `pip install`. That is public-network build behavior and must not be on the adapter smoke path.
4. The smoke task's `environment/docker-compose.yaml` still uses `tau3-runtime.build.context: ./runtime-server`, and `environment/runtime-server/Dockerfile` also performs public-network build steps.
5. Harbor supports `[environment].docker_image` and `--no-force-build`; this can select a prebuilt main image, but the task-level compose file is appended afterward and still controls the `tau3-runtime` sidecar. The sidecar therefore needs an explicit prebuilt image stanza too.
6. Harbor has a built-in `oracle` agent, and the smoke task's evaluator skips NL assertions when the oracle solution is present. The smoke `solution/solve.sh` writes the runtime-state log directly, so the first adapter smoke can avoid model/API calls.

## Minimal next adapter smoke

Use a throwaway patched copy of the one-task smoke dataset first. Do not mutate the full dataset or suite rows until this one-task oracle smoke passes.

Recommended copy path:

```bash
SMOKE_SRC=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0
SMOKE_WORK=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28/dataset/tau3-airline-0
mkdir -p "$(dirname "$SMOKE_WORK")"
rsync -a --delete "$SMOKE_SRC/" "$SMOKE_WORK/"
```

### Patch 1: smoke task `task.toml`

Patch file:

`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28/dataset/tau3-airline-0/task.toml`

Make these exact semantic changes in the smoke copy:

```toml
[verifier]
timeout_sec = 300.0
env = { OPENAI_API_KEY = "${OPENAI_API_KEY:-}", OPENAI_BASE_URL = "${OPENAI_BASE_URL:-}", TAU2_NL_ASSERTIONS_MODEL = "${TAU2_NL_ASSERTIONS_MODEL:-unused-no-model}" }

[environment]
build_timeout_sec = 600.0
cpus = 4
memory_mb = 8192
storage_mb = 10240
docker_image = "100.97.118.137:8555/swe-data-harness/tau3-smoke-main@sha256:571aa921fc1eda999b9fc124a266900c6b10a4aceba9283e6f9867f9a44788e4"
env = { OPENAI_API_KEY = "${OPENAI_API_KEY:-}", OPENAI_BASE_URL = "${OPENAI_BASE_URL:-}", TAU2_USER_MODEL = "${TAU2_USER_MODEL:-unused-no-model}", TAU2_USER_REASONING_EFFORT = "${TAU2_USER_REASONING_EFFORT:-low}", TAU2_USER_TEMPERATURE = "${TAU2_USER_TEMPERATURE:-}", TAU2_USER_LLM_ARGS_JSON = "${TAU2_USER_LLM_ARGS_JSON:-}" }
```

Notes:

- Keep `[[environment.mcp_servers]]` unchanged for the first smoke, even though the oracle path does not need to call it. This verifies the sidecar can still start.
- Use `--no-force-build` in the Harbor command. Harbor's prebuilt-image path is bypassed if a caller forces builds while an `environment/Dockerfile` is present.
- Do not add real API values. Empty defaults are intentional for the no-model smoke.

### Patch 2: smoke task `environment/docker-compose.yaml`

Patch file:

`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28/dataset/tau3-airline-0/environment/docker-compose.yaml`

Replace the `tau3-runtime.build` stanza with the prebuilt r2 image:

```yaml
services:
  main:
    depends_on:
      tau3-runtime:
        condition: service_healthy

  tau3-runtime:
    image: 100.97.118.137:8555/swe-data-harness/tau3-smoke-runtime@sha256:290a4f09c7ade3a1e7a08dfd3d4c6d0951b4ae519eae12d2fe1ccb99745dc699
    pull_policy: never
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL:-}
      - TAU2_USER_MODEL=${TAU2_USER_MODEL:-unused-no-model}
      - TAU2_USER_REASONING_EFFORT=${TAU2_USER_REASONING_EFFORT:-low}
    volumes:
      - ${HOST_AGENT_LOGS_PATH}:${ENV_AGENT_LOGS_PATH}
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import socket; s=socket.create_connection(('localhost',8000),timeout=2); s.close()"]
      interval: 2s
      timeout: 5s
      retries: 15
      start_period: 5s
```

The `pull_policy: never` choice keeps the smoke honest: it fails if the runtime image is not locally available instead of silently trying public egress. If the worker team wants to allow internal P0 registry pulls during smoke, change this to `missing` and keep the digest-pinned internal registry ref.

### Patch 3: shared runner support for oracle mode

Patch file after the copied dataset smoke succeeds manually:

`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh`

Required behavior:

- Add `TAU3_AGENT="${TAU3_AGENT:-tau3_llm_agent}"`.
- Do not require `MODEL_NAME` when `TAU3_AGENT=oracle`.
- For `TAU3_AGENT=oracle`, build the Harbor command with `-a oracle`, no `--agent-import-path`, no `-m`, no `--ak`, and no OpenAI env forwarding.
- Always include `--no-force-build` for the smoke path.
- Write `tau3_agent=$TAU3_AGENT` and `tau3_no_model_smoke=1` into `run.env.summary` for oracle mode.
- Preserve existing redacted command behavior for the model-backed `tau3_llm_agent` path.

Minimal command construction shape:

```bash
TAU3_AGENT="${TAU3_AGENT:-tau3_llm_agent}"
TAU3_USER_MODEL="${TAU3_USER_MODEL:-${MODEL_NAME:-unused-no-model}}"
TAU3_NL_ASSERTIONS_MODEL="${TAU3_NL_ASSERTIONS_MODEL:-${MODEL_NAME:-unused-no-model}}"

if [[ "$TAU3_AGENT" == "oracle" ]]; then
  harbor_cmd=(
    uv run --no-default-groups --no-group dev --python "$HARBOR_PYTHON" harbor run
    -p "$TAU3_DATASET_DIR"
    -o "$TAU3_JOBS_DIR"
    -a oracle
    -k "$TAU3_N_ATTEMPTS"
    -n "$TAU3_N_CONCURRENT"
    -r "$TAU3_MAX_RETRIES"
    --no-force-build
    --yes
  )
  redacted_harbor_env=()
else
  # Existing tau3_llm_agent command path, plus --no-force-build for smoke.
  :
fi
```

This runner patch is not needed to perform the first manual Harbor oracle smoke if the direct command below is used, but it is required before suite wiring can treat tau3 as adapter-smoke-ready.

### Patch 4: adapter template after the copied smoke passes

Patch these source-template files only after the copied smoke passes and the desired image-ref parameterization is agreed:

- `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench/src/tau3_bench/task-template/task.toml`
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench/src/tau3_bench/task-template/environment/docker-compose.yaml`

The template patch should make regenerated smoke/full datasets accept prebuilt main/runtime image refs without required API env placeholders. Prefer explicit generator variables such as `TAU3_MAIN_IMAGE_REF` and `TAU3_RUNTIME_IMAGE_REF` rather than hard-coding r2 forever in the template.

### Patch 5: repo manifests after the smoke passes

Patch these repo files only after the smoke produces a real job artifact:

- `manifests/bench_registry.yaml`: update tau3-bench from stale image-pending wording to adapter-smoke-ready evidence.
- `manifests/suite.example.yaml`: update `adapter_status` from `pending_adapter` to `adapter_smoke_ready`; keep `enabled: false` until the result parser and model-backed mode are explicitly approved.
- `manifests/images/tau3_bench.yaml`: add adapter-smoke evidence with job artifact path, worker host, Docker host, and command hash. Do not change the r2 image digests.

## Exact no-model smoke commands

### Dev static preparation only

These commands are safe on `dev`; they copy and patch a one-task smoke dataset but do not run Docker or Harbor:

```bash
ssh dev
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy

SMOKE_SRC=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0
ROUND_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28
SMOKE_WORK=$ROUND_ROOT/dataset/tau3-airline-0
MAIN_REF=100.97.118.137:8555/swe-data-harness/tau3-smoke-main@sha256:571aa921fc1eda999b9fc124a266900c6b10a4aceba9283e6f9867f9a44788e4
RUNTIME_REF=100.97.118.137:8555/swe-data-harness/tau3-smoke-runtime@sha256:290a4f09c7ade3a1e7a08dfd3d4c6d0951b4ae519eae12d2fe1ccb99745dc699

mkdir -p "$ROUND_ROOT/dataset"
rsync -a --delete "$SMOKE_SRC/" "$SMOKE_WORK/"
# Apply Patch 1 and Patch 2 to files under "$SMOKE_WORK".
python3 -m compileall -q "$SMOKE_WORK/tests"
grep -RIn 'OPENAI_API_KEY = "${OPENAI_API_KEY}"\|OPENAI_BASE_URL = "${OPENAI_BASE_URL}"\|build:' "$SMOKE_WORK" && exit 1 || true
```

Expected dev artifacts:

- `$ROUND_ROOT/dataset/tau3-airline-0/task.toml`
- `$ROUND_ROOT/dataset/tau3-airline-0/environment/docker-compose.yaml`
- No `build:` stanza in the patched compose file.
- No required `${OPENAI_API_KEY}` or `${OPENAI_BASE_URL}` placeholder in the patched task config.

### Worker rootless image-cache preflight

Run only when a worker rootless Docker probe is allowed. This performs no pull/load/build:

```bash
ssh worker
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export DOCKER_API_VERSION=1.45
MAIN_REF=100.97.118.137:8555/swe-data-harness/tau3-smoke-main@sha256:571aa921fc1eda999b9fc124a266900c6b10a4aceba9283e6f9867f9a44788e4
RUNTIME_REF=100.97.118.137:8555/swe-data-harness/tau3-smoke-runtime@sha256:290a4f09c7ade3a1e7a08dfd3d4c6d0951b4ae519eae12d2fe1ccb99745dc699

docker image inspect "$MAIN_REF" >/tmp/tau3-main-r2.inspect.json
docker image inspect "$RUNTIME_REF" >/tmp/tau3-runtime-r2.inspect.json
```

Expected state:

- Both `docker image inspect` commands return rc 0.
- If either image inspect fails, do not run Harbor. The next action is an internal-cache fix from the existing r2 tar or P0 registry path, not a public pull.

### Worker Harbor oracle smoke

Run only after the preflight succeeds and a no-sync/offline Harbor CLI environment is confirmed on the worker:

```bash
ssh worker
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export DOCKER_API_VERSION=1.45
export UV_NO_SYNC=1

HARBOR_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor
ROUND_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28
DATASET_DIR=$ROUND_ROOT/dataset
JOBS_DIR=$ROUND_ROOT/jobs
LOG_DIR=$ROUND_ROOT/logs
mkdir -p "$JOBS_DIR" "$LOG_DIR"

cd "$HARBOR_ROOT"
uv run --offline --no-default-groups --no-group dev --python 3.12 harbor run \
  -p "$DATASET_DIR" \
  -o "$JOBS_DIR" \
  -a oracle \
  -k 1 \
  -n 1 \
  -r 0 \
  --no-force-build \
  --yes 2>&1 | tee "$LOG_DIR/tau3_oracle_smoke.log"
```

If `uv run --offline` is not available with the pre-existing Harbor environment, use the locally installed Harbor CLI environment documented by the Harbor owner. Do not let `uv` resolve or download dependencies during this smoke.

Expected smoke artifacts:

- `$ROUND_ROOT/logs/tau3_oracle_smoke.log`
- `$ROUND_ROOT/jobs/**/result.json` or Harbor-equivalent trial result file with reward/status.
- `$ROUND_ROOT/jobs/**/agent/oracle*` or Harbor-equivalent oracle agent log.
- `$ROUND_ROOT/jobs/**/logs/verifier/*` or Harbor-equivalent verifier output.
- A reward of `1.0` for `tau3-airline-0` is expected from the oracle solution path. If the reward is lower, inspect verifier output before changing images.
- No OpenAI key/base URL values should appear in the command log or result artifacts.
- No `docker build`, `docker pull`, or public-network URL should appear in the smoke log.

### Runner-mediated smoke after runner patch

After Patch 3 lands, the suite-facing smoke command should become:

```bash
ssh worker
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export DOCKER_API_VERSION=1.45
export UV_NO_SYNC=1
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench

TAU3_MODE=smoke \
TAU3_GENERATE_DATASET=0 \
TAU3_RUN_HARBOR=1 \
TAU3_AGENT=oracle \
TAU3_DATASET_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28/dataset \
TAU3_JOBS_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round28/jobs \
HARBOR_PYTHON=3.12 \
./run_tau3_bench.sh
```

Expected runner artifacts:

- `$BENCH_RUN_DIR/run.env.summary` includes `tau3_agent=oracle`, `tau3_harbor_run=executed`, `tau3_task_count=1`, and `artifact=<jobs dir>`.
- `$BENCH_RUN_DIR/tasks.list` has exactly one task.
- `$BENCH_RUN_DIR/command.sh` contains `-a oracle` and `--no-force-build`, and does not contain `-m`, `--agent-import-path`, `OPENAI_API_KEY`, or `OPENAI_BASE_URL`.
- `$BENCH_RUN_DIR/tau3_harbor.log` is present and contains no model/API calls.
- The jobs dir contains a successful oracle result for `tau3-airline-0`.

## Blockers to clear before calling tau3 adapter-smoke-ready

1. The smoke task copy must be patched to use the r2 prebuilt main/runtime image refs and to remove required OpenAI env placeholders.
2. The shared runner must support `TAU3_AGENT=oracle` without requiring `MODEL_NAME` or OpenAI env, and must pass `--no-force-build` for this smoke path.
3. Worker rootless image inspect must be confirmed for both r2 digest refs using `DOCKER_API_VERSION=1.45`. If image inspect fails, fix the internal cache/registry state from the existing r2 tar or P0 digest refs before any smoke.
4. The Harbor CLI environment on the worker must be proven offline/no-sync. `uv run --offline` or an already materialized Harbor env is required; dependency resolution during smoke is not acceptable.
5. The first smoke should use the copied one-task dataset only. Full dataset/template/suite/registry patches should wait for a successful one-task oracle job artifact.

## No ISSUE-READY finding

No new confirmed production-code bug is filed from this pass. The evidence shows expected integration blockers: stale tau3 suite/registry status, a model-only runner, generated public-build task files, and missing no-model smoke wiring. These are the next adapter enablement work items, not a separately confirmed defect beyond the known `adapter_not_wired` state.

## Commands run this round

| Command | rc | Notes |
| --- | ---: | --- |
| `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Read required workspace workflow before remote work. |
| `sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Continued workflow read. |
| `sed -n '621,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Completed workflow read. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && pwd && git branch --show-current && git log --oneline -1 && git status --short -- ...'` | 0 | Verified remote worktree, branch `feat/image-warmup-policy`, HEAD `dce3191`, no target-report status. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba manifests/images/tau3_bench.yaml'` | 0 | Inspected r2 tau3 image manifest. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba _coordination/.../tau3-runtime-image-round27.md'` | 0 | Read prior tau3 runtime image lane report. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba reports/tau3_harbor_adapter_inventory_20260626.md'` | 0 | Read adapter inventory report. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && find /mnt/.../artifacts/tau3_smoke_image_20260626 -maxdepth 4 ...'` | 0 | Inspected r2 artifact tree, Dockerfiles, tars, and sidecar files. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../tau3-smoke_20260626r2.repo-digests && nl -ba .../tau3-smoke_20260626r2.sha256'` | 0 | Confirmed r2 digest and checksum sidecar files. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba /mnt/.../nips2026/bench/run_tau3_bench.sh | sed -n "1,130p"'` | 0 | Confirmed runner hard-codes `tau3_llm_agent`, model, and OpenAI env path. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba /mnt/.../swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0/task.toml | sed -n "1,90p"'` | 0 | Confirmed required OpenAI env placeholders and no prebuilt image ref. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba /mnt/.../swe/bench/swe-atlas/harbor/datasets/tau3-bench-smoke/tau3-airline-0/environment/docker-compose.yaml | sed -n "1,80p"'` | 0 | Confirmed sidecar still uses `build.context`. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../environment/Dockerfile && nl -ba .../environment/runtime-server/Dockerfile'` | 0 | Confirmed generated Dockerfiles still do public apt/git/pip build work. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../tests/evaluate.py | sed -n "340,395p"'` | 0 | Confirmed oracle solution path skips NL assertions. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../harbor/src/harbor/agents/factory.py | sed -n ...'` | 0 | Confirmed built-in `oracle` agent mapping. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../harbor/src/harbor/models/task/config.py ... && nl -ba .../harbor/src/harbor/environments/definition.py ...'` | 0 | Confirmed `[environment].docker_image` and prebuilt selection behavior. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && nl -ba .../harbor/src/harbor/utils/env.py ... && nl -ba .../harbor/src/harbor/cli/jobs.py ...'` | 0 | Confirmed required env placeholders cause pre-run failure. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && grep -RIn "force_build\|no-force-build\|force-build" ...'` | 0 | Confirmed Harbor exposes `--force-build/--no-force-build`. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && if [ -e _coordination/.../tau3-adapter-round28.md ]; then ...; else printf TARGET_REPORT_MISSING; fi'` | 0 | Confirmed target report was absent before this write. |
