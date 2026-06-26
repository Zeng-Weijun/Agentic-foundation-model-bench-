# tau3-bench Adapter Round30 Oracle-Direct Worker Smoke

Date: 2026-06-26
Scope: shared runner direct mode, copied one-task dataset, suite helper wiring, and worker-j9jjd smoke evidence. The full tau3 suite target remains disabled/pending adapter.

## Summary

Round29 proved Harbor oracle mode fail-closes correctly but could not run on worker-j9jjd because rootless Docker compose cannot create networks and compose also hits the Docker `/version` EOF path. Round30 isolates the same one-task oracle smoke from Harbor/compose by adding a direct `docker run --network none` mode to the shared runner.

Result: the one-task direct oracle smoke passed on worker-j9jjd with verifier `status=passed` and `reward=1.0`. This is intentionally wired as an enabled `image_smoke` helper, not as full tau3 readiness.

## Paths

- Shared runner: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh`.
- Shared runner sha256 after Round30 direct mode: `4424b70928dda8ca43d613c0a28020e822e05f9b71a53f8acec44a1eeef9c012`.
- Stable one-task dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/tau3-bench-oracle-direct-smoke`.
- Round artifact root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round30`.
- Direct manual oracle proof: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round30/direct_oracle_run_20260626.txt`.
- Suite-generated worker run root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/tau3_bench_oracle_direct_smoke`.
- Suite result summary: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/tau3_bench_oracle_direct_smoke/tau3_result_summary.json`.

## Runner Contract Changes

`run_tau3_bench.sh` now supports `TAU3_AGENT=oracle_direct` for exactly one task.

- It does not call Harbor or Docker compose.
- It writes `command.sh` containing `docker run --rm --network none`.
- It mounts the task's `tests` and `solution` directories read-only.
- It mounts per-run `logs` and `artifacts` directories writable.
- It runs `bash /solution/solve.sh && bash /tests/test.sh` inside `tau3-smoke-main:20260626r2`.
- It writes `tau3_result_summary.json` with schema `agentic_bench.tau3_direct_result_summary.v1`.
- It fail-closes unless `direct_rc=0`, verifier `status=passed`, and reward is `1.0`.

## Dataset Copy

The stable smoke dataset is a copied one-task dataset at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/tau3-bench-oracle-direct-smoke`.

- Task: `tau3-airline-0`.
- `task.toml` uses `docker_image = "tau3-smoke-main:20260626r2"`.
- Required OpenAI env placeholders were changed to empty defaults.
- MCP server config was removed from the copied task.
- `environment/docker-compose.yaml` was reduced to `network_mode: none` during compose probes, but direct mode does not depend on compose.
- Test files compile with `python3 -m compileall -q`.

## Worker Evidence

Worker image inspect confirmed both local tau3 r2 tags exist before execution:

- `tau3-smoke-main:20260626r2` image id `sha256:80c0d9453584d67f4fd89f53f6f47e2503870f7663d3615384f6e23f6dcc0e78`.
- `tau3-smoke-runtime:20260626r2` image id `sha256:b06571be24cf17bb4d04f4f0c76e7209ed112e2bfde48923477d34999581aefb`.

Manual direct oracle run on worker-j9jjd passed:

```text
direct_oracle_rc=0
result_exists True
reward_exists True
status passed
reward 1.0
reward_txt 1.0
```

Suite-generated worker command also passed from the Mac control plane through the explicit worker-j9jjd endpoint. Result summary:

```json
{
  "direct_rc": 0,
  "mode": "oracle_direct",
  "reward": 1.0,
  "schema_version": "agentic_bench.tau3_direct_result_summary.v1",
  "status": "passed",
  "verifier_status": "passed"
}
```

## Remaining Blockers

- Harbor/compose path is still blocked. A layered compose probe with `network_mode: none` failed during container creation at `/v1.45/version` EOF.
- `DOCKER_API_VERSION` sweep over `1.45`, `1.44`, `1.43`, `1.41`, and unset did not fix compose; all failed at Docker `/version` EOF.
- Round29's rootless network blockers still apply: default compose network creation is `operation not permitted`, and `docker run --network host` is not permitted.
- Offline-clean caveat remains. The direct run uses `--network none`, but tau2/LiteLLM import still tries to fetch the remote model-cost map and then falls back locally after DNS failure.

## Suite Wiring

- Added enabled suite helper `tau3_bench_oracle_direct_smoke`.
- Helper uses `readiness_role: image_smoke`, `adapter_status: wired_legacy`, `TAU3_AGENT=oracle_direct`, and the stable one-task dataset path.
- Added regression coverage that the helper is ready but does not satisfy full tau3 readiness.
- Full `tau3_bench` entry remains `enabled: false`, `adapter_status: pending_adapter`, and the target remains `blocked` with `aggregation_entry_count=1`.

## Validation

- Shared runner `bash -n` passed after direct mode changes.
- Focused suite tests for tau3 full readiness and oracle-direct helper passed.
- Suite readiness for `tau3-bench` still returns rc 1 with target status `blocked`.
- Suite dry-run for `tau3_bench_oracle_direct_smoke` resolves `TAU3_AGENT=oracle_direct`, `TAU3_DIRECT_IMAGE=tau3-smoke-main:20260626r2`, and required image preflight.
- Suite-generated command executed successfully on worker and produced `reward=1.0`.
