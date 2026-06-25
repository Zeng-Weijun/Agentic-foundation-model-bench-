# runner-concurrency-relay round25 audit

Date: 2026-06-26
Lane: runner-concurrency-relay
Scope: read-only audit for future worker smoke via the 8.130 relay and SGLang-compatible profiles.
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`

## Red lines observed

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first.
- No code or manifest edits.
- No real model calls.
- No `docker save`, `docker load`, `docker pull`, `docker run`, or `docker build`.
- Only this report was written by this lane.
- `/data/nips/shared_bench/api_config.env` was inspected only through a sanitizer that prints variable names and endpoint shapes, never secret values.

## Files audited

- `scripts/agentic_bench_suite.py`
- `scripts/run_suite_from_yaml.sh`
- `manifests/suite.example.yaml`
- `manifests/models.example.yaml`
- `/data/nips/shared_bench/api_config.env` variable names and endpoint shapes only

## Command ledger

| Command | Exit | Evidence captured |
| --- | ---: | --- |
| `sed -n '1,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Active worker is `worker-j9jjd`; worker has 60 CPU, offline policy, rootless Docker at `unix:///tmp/rl/run/docker.sock`; first-time image pulls should be capped around 2-4. |
| `ssh dev 'cd <worktree> && nl -ba scripts/agentic_bench_suite.py | sed -n "300,610p"'` | 0 | Model/env sourcing and image preflight concurrency code. |
| `ssh dev 'cd <worktree> && nl -ba scripts/agentic_bench_suite.py | sed -n "610,735p"'` | 0 | Image preflight command construction. |
| `ssh dev 'cd <worktree> && nl -ba scripts/agentic_bench_suite.py | sed -n "740,1435p"'` | 0 | Plan builder, execution executor, CLI arguments. |
| `ssh dev 'cd <worktree> && grep -RIn "proxy_concurrency_ceiling\|suite_concurrency\|image_preflight_concurrency\|ThreadPoolExecutor\|max_concurrency\|concurrency" scripts/agentic_bench_suite.py scripts/run_suite_from_yaml.sh manifests/suite.example.yaml manifests/models.example.yaml'` | 0 | `proxy_concurrency_ceiling` appears only in the YAML, not in runner code. |
| `ssh dev 'cd <worktree> && nl -ba manifests/suite.example.yaml | sed -n "1,360p"'` | 0 | Suite defaults: model concurrency 40, proxy ceiling 50, image preflight 4, 8.130 relay profiles, SGLang future profile. |
| `ssh dev 'cd <worktree> && nl -ba manifests/models.example.yaml | sed -n "1,220p"'` | 0 | SGLang example still names stale `worker_rkn9p`; relay model profile exists but has empty base URL in this file. |
| `ssh dev 'cd <worktree> && nl -ba scripts/run_suite_from_yaml.sh'` | 0 | Wrapper only resolves suite path and execs `agentic_bench_suite.py`. |
| Sanitized Python parser over `/data/nips/shared_bench/api_config.env` | 0 | `OPENAI_BASE_URL` and `REPO2ENV_OPENAI_BASE_URL` are HTTP endpoints on 8.130 with a one-segment path; API keys and related key IDs were redacted. |
| `ssh dev 'cd <worktree> && python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only repozero_py2js_smoke --model-profile gpt54mini_8130 --json | python3 -c <extract fields>'` | 0 | Default dry-run gives `suite_concurrency=40`, `image_preflight_concurrency=4`, run concurrency 1, endpoint `http://8.130.49.170/v1`, and required RepoZero image preflight. |
| `ssh dev 'cd <worktree> && python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only repozero_py2js_smoke --model-profile gpt54mini_8130 --max-concurrency 80 --json | python3 -c <extract fields>'` | 0 | Dry-run accepts `suite_concurrency=80`; `proxy_concurrency_ceiling` is absent from the plan. |
| `ssh dev 'cd <worktree> && python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only swebench_verified_qwen_code_smoke --model-profile qwen3_coder_30b_a3b_sglang_future --json | python3 -c <extract fields>'` | 0 | SGLang profile exports endpoint through `${SGLANG_OPENAI_BASE_URL}` and key through `${SGLANG_OPENAI_API_KEY}`. |
| `ssh dev 'cd <worktree> && git status --short'` | 0 | Pre-existing dirty files observed outside this lane; not modified by this lane. |

## Current runner support

### Suite/model concurrency

- `manifests/suite.example.yaml:10` sets `suite.concurrency: 40`.
- `scripts/agentic_bench_suite.py:775` maps that value, or CLI `--max-concurrency`, into `suite_concurrency`.
- `scripts/agentic_bench_suite.py:923` emits `suite_concurrency` into the plan.
- `scripts/agentic_bench_suite.py:1328-1329` runs benchmark commands with `ThreadPoolExecutor(max_workers=suite_concurrency)`.
- `scripts/agentic_bench_suite.py:1355` exposes `--max-concurrency` as the command-line override.
- Dry-run evidence: RepoZero with `gpt54mini_8130` produced `suite_concurrency=40` by default.

Interpretation: current runner can schedule up to 40-50 model-adapter processes if the operator sets `suite.concurrency` or `--max-concurrency` in that range. This is process-level concurrency, not a true per-model-call semaphore.

### Image warmup concurrency

- `manifests/suite.example.yaml:53-60` configures image preflight with `max_concurrency: 4`, `load_fallback: true`, `run_smoke: true`, and no global pull flag.
- `scripts/agentic_bench_suite.py:572-578` computes image preflight concurrency from `image_preflight.max_concurrency`, `transport_concurrency`, or `concurrency`, defaulting to `min(suite_concurrency, 4)`.
- `scripts/agentic_bench_suite.py:1143-1158` runs image preflights in a separate `ThreadPoolExecutor(max_workers=image_preflight_concurrency)`.
- `scripts/agentic_bench_suite.py:1156-1168` caches identical preflight commands so duplicate manifest checks share one subprocess result.
- Dry-run evidence: RepoZero default plan produced `image_preflight_concurrency=4`.

Interpretation: the runner already supports the requested image warmup range at the high end. The current example is fixed at 4. There is no CLI-only way to lower it to 2 without using a different suite YAML or adding a new CLI flag.

### Relay model/env support

- `manifests/suite.example.yaml:63-73` defines `gpt54mini_8130` with model `gpt-5.4-mini`, relay endpoint `http://8.130.49.170/v1`, and `api_key_env: OPENAI_API_KEY`.
- `manifests/suite.example.yaml:88-98` defines `gpt54_8130` with model `gpt-5.4`, the same relay endpoint, and `api_key_env: OPENAI_API_KEY`.
- `scripts/agentic_bench_suite.py:401-427` exports `MODEL_NAME`, `OPENAI_MODEL`, `LITELLM_MODEL`, `OPENAI_BASE_URL`, `BASE_URL`, and `OPENAI_API_KEY` from the selected profile.
- `scripts/agentic_bench_suite.py:512-535` sources configured env files before exporting runner env.
- `manifests/suite.example.yaml:13-15` sources `~/.bashrc` and `/data/nips/shared_bench/api_config.env` on the execution shell.
- Sanitized `/data/nips/shared_bench/api_config.env` check found `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `REPO2ENV_OPENAI_BASE_URL`, `REPO2ENV_OPENAI_API_KEY`, `PRIMARY_MODEL`, `EVAL_MODEL`, and other model selector variables. Secret values were not printed.

Interpretation: the suite profile already supports the 8.130 relay for `gpt-5.4-mini` and `gpt-5.4` without embedding tokens in YAML.

### SGLang support

- `manifests/suite.example.yaml:100-110` defines `qwen3_coder_30b_a3b_sglang_future` with `provider: sglang`, `base_url_env: SGLANG_OPENAI_BASE_URL`, and `api_key_env: SGLANG_OPENAI_API_KEY`.
- `scripts/agentic_bench_suite.py:363-398` reports required env variables for profiles with `base_url_env` and `api_key_env`.
- Dry-run evidence: SGLang profile produced endpoint `${SGLANG_OPENAI_BASE_URL}`, required env `['SGLANG_OPENAI_API_KEY', 'SGLANG_OPENAI_BASE_URL']`, and exports `OPENAI_BASE_URL`, `BASE_URL`, and `OPENAI_API_KEY` from those env vars.

Interpretation: the runner supports an OpenAI-compatible SGLang endpoint shape. Capacity limits must be set per SGLang server; the runner does not infer them.

### Wrapper support

- `scripts/run_suite_from_yaml.sh:1-16` is a thin wrapper: it picks a suite YAML and execs `scripts/agentic_bench_suite.py` with all remaining arguments.
- It has no independent concurrency, env, or model logic. This is good for predictability; all policy lives in YAML plus `agentic_bench_suite.py`.

## Gaps

1. `proxy_concurrency_ceiling` is declared but not enforced. The YAML says ceiling 50, but the runner accepts `--max-concurrency 80` and emits `suite_concurrency=80` with no ceiling field in the plan.
2. There is no dedicated model-call semaphore. `suite_concurrency` limits concurrent adapter subprocesses, while adapter-specific values such as `MAX_CONCURRENCY`, `REPOZERO_WORKERS`, `TB_N_CONCURRENT`, or `QWEN_NATIVE_MAX_WORKERS` limit behavior inside each adapter. Total model-call concurrency can exceed the intended 40-50 if adapter internals are raised above 1.
3. `bench.concurrency` is recorded into each run manifest at `scripts/agentic_bench_suite.py:890`, but `_execute_plan` does not use it for scheduling. The actual executor uses only plan-level `suite_concurrency`.
4. Image preflight has a YAML cap but no CLI cap. Current example gives 4, which fits the boundary, but a 2-wide warmup requires a separate suite YAML or a new CLI option.
5. Required image preflight runs inside `_run_one` before adapter execution at `scripts/agentic_bench_suite.py:988-1009`. If an operator first runs `--image-preflight-only` and then `--execute`, required preflight checks may run twice unless a later policy or cache makes that explicit.
6. `manifests/models.example.yaml:8` still names `worker_rkn9p`, which WORKFLOW now treats as stale/closed. The suite-local SGLang future profile is safer because it uses `SGLANG_OPENAI_BASE_URL` instead of a baked stale host.
7. `manifests/suite.example.yaml:27-29` records local-to-worker SSH as OK and dev-to-worker SSH as blocked by public key. If `--execute` is launched on `dev`, the runner's `ssh_worker` command will also originate from `dev`. Future real smoke should be launched only from a control plane that can SSH to `worker-j9jjd`, or the dispatch path must be fixed before execution.

## Recommended boundaries

- Relay model call boundary: start at 40 concurrent adapter processes for `gpt54mini_8130` or `gpt54_8130`. Do not exceed 50 until `proxy_concurrency_ceiling` is enforced in code.
- Adapter internal boundary: keep per-bench internal model concurrency at 1 for worker smoke unless the run is intentionally testing a single adapter. If an adapter uses internal concurrency N, set `suite_concurrency <= floor(50 / N)`.
- Image warmup boundary: keep `image_preflight.max_concurrency` in the 2-4 range. Current suite example is 4. Use 2 only via a temporary copied suite YAML or a future `--image-preflight-concurrency` option.
- Worker CPU 60 boundary: `suite_concurrency=40` with adapter internals at 1 leaves CPU headroom for SSH, Docker checks, verifiers, and filesystem overhead. For Docker-heavy or verifier-heavy benches, prefer 20-30 until CPU and I/O behavior is measured.
- SGLang boundary: use the same runner profile mechanism, but set concurrency from the actual SGLang server capacity. Do not assume the 8.130 relay ceiling applies to a local SGLang endpoint.

## Recommended YAML policy for future smoke

This is a policy target, not an edit made by this lane:

```yaml
suite:
  concurrency: 40
  proxy_concurrency_ceiling: 50

image_preflight:
  max_concurrency: 4
  load_fallback: true
  run_smoke: true
  # Keep pull disabled unless every referenced image is an internal P0 Harbor digest.
  # pull: true

model_profiles:
  - id: gpt54mini_8130
    model_name: gpt-5.4-mini
    litellm_model: openai/gpt-5.4-mini
    provider: openai_compatible_relay
    base_url: http://8.130.49.170/v1
    api_key_env: OPENAI_API_KEY
  - id: gpt54_8130
    model_name: gpt-5.4
    litellm_model: openai/gpt-5.4
    provider: openai_compatible_relay
    base_url: http://8.130.49.170/v1
    api_key_env: OPENAI_API_KEY
  - id: qwen3_coder_30b_a3b_sglang_future
    provider: sglang
    base_url_env: SGLANG_OPENAI_BASE_URL
    api_key_env: SGLANG_OPENAI_API_KEY
    api_key_policy: empty_allowed
```

## Recommended commands for future controlled smoke

These commands are recommendations for a later execution lane. They were not run in this audit.

Dry-run plan first:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --dry-run \
  --only repozero_py2js_smoke \
  --model-profile gpt54mini_8130 \
  --max-concurrency 40 \
  --emit-plan /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/relay_smoke_round25/plan.json
```

Image warmup only, with the existing 4-wide image cap:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --image-preflight-only \
  --only repozero_py2js_smoke \
  --model-profile gpt54mini_8130 \
  --max-concurrency 40 \
  --output-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/relay_smoke_round25/controller
```

Relay execute smoke after image readiness and worker dispatch are verified:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only repozero_py2js_smoke \
  --model-profile gpt54mini_8130 \
  --max-concurrency 40 \
  --output-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/relay_smoke_round25/controller
```

Same smoke against `gpt-5.4` relay profile:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only repozero_py2js_smoke \
  --model-profile gpt54_8130 \
  --max-concurrency 40 \
  --output-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/relay_smoke_round25_gpt54/controller
```

SGLang dry-run shape check:

```bash
export SGLANG_OPENAI_BASE_URL=http://<sglang-host>:<port>/v1
set SGLANG_OPENAI_API_KEY to EMPTY placeholder
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --dry-run \
  --only swebench_verified_qwen_code_smoke \
  --model-profile qwen3_coder_30b_a3b_sglang_future \
  --max-concurrency <sglang-safe-concurrency>
```

## Suggested runner gate

Before any real smoke execution, the runner should fail closed unless all of these are true:

- Planned `suite_concurrency` is between 1 and `suite.proxy_concurrency_ceiling`.
- Planned relay profile is one of the approved 8.130 profiles or an explicitly approved SGLang env profile.
- Required env variables are present, but secret values are never printed.
- Planned `image_preflight_concurrency` is between 2 and 4.
- Worker dispatch path is confirmed from the actual launching host.
- If image pull is enabled, every image ref is an internal P0 Harbor digest, not a public registry tag.
- Adapter internal concurrency variables are consistent with the global model-call cap.

## Risks

- The active worktree is dirty before this lane's report write. Observed modified files include `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`, `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`, `scripts/agentic_bench_images.py`, `scripts/stage_cache_images_from_plan.sh`, and `scripts/test_agentic_bench_images.py`. This lane did not modify or revert them.
- Running `--execute` from `dev` may fail to reach `worker-j9jjd` because the manifest itself says dev-to-worker SSH is blocked.
- The current example disables `pull` by omission. Enabling pull later is safe only if manifests point at the internal P0 Harbor digest refs.
- With no model semaphore, raising adapter internals above 1 can silently exceed the intended relay cap.
- Running image preflight separately and then executing may repeat required image checks.

## ISSUE-READY

### `suite.proxy_concurrency_ceiling` is ignored by the runner

- Files/lines:
  - `manifests/suite.example.yaml:10` sets `concurrency: 40`.
  - `manifests/suite.example.yaml:11` sets `proxy_concurrency_ceiling: 50`.
  - `scripts/agentic_bench_suite.py:775` computes `suite_concurrency = int(max_concurrency or suite.get("concurrency", 1))`.
  - `scripts/agentic_bench_suite.py:923` emits `suite_concurrency` but no proxy ceiling.
  - `scripts/agentic_bench_suite.py:1328-1329` uses `suite_concurrency` directly as `ThreadPoolExecutor(max_workers=...)`.
- Repro, dry-run only:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml \
  --dry-run \
  --only repozero_py2js_smoke \
  --model-profile gpt54mini_8130 \
  --max-concurrency 80 \
  --json | python3 -c 'import json,sys; p=json.load(sys.stdin); print(p.get("suite_concurrency")); print(p.get("proxy_concurrency_ceiling"))'
```

Observed result: `suite_concurrency=80`; `proxy_concurrency_ceiling=None` in the emitted plan.

- Impact: an operator can accidentally schedule more than the intended 40-50 concurrent relay model calls. This can overload the 8.130 relay or make worker smoke failures look like benchmark instability instead of runner policy failure.
- Fix: parse `suite.proxy_concurrency_ceiling`, emit it into the plan, and fail closed if requested `suite_concurrency` exceeds it. Prefer adding a distinct `model_concurrency` or provider semaphore later, because process concurrency and true model-call concurrency are not always the same.
