# tau3-bench Adapter Round29 Worker Oracle Smoke Attempt

Date: 2026-06-26
Scope: shared runner + copied-dataset smoke evidence. The active suite entry remains disabled/pending; tau3 is not promoted to adapter-smoke-ready.

## Summary

This round moved tau3 beyond image-only readiness but did not clear the worker adapter smoke gate.

- The shared runner `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh` now supports `TAU3_AGENT=oracle` for a no-model smoke path.
- The runner also supports `HARBOR_BIN` so worker can call the already-materialized Harbor venv at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/harbor/.venv/bin/harbor` instead of relying on `uv run`.
- The runner now parses Harbor `result.json` after execution and returns nonzero when Harbor reports exceptions, zero total trials, or zero successful eval trials. This fixed the observed false-success path where Harbor process rc was 0 while job stats had `n_errors=1`.
- A copied one-task dataset was patched under shared artifacts to use prebuilt tau3 r2 images and empty-default OpenAI env placeholders.
- Worker image inspect passed for both tau3 r2 digest images.
- Real worker Harbor oracle smoke still failed before task execution because rootless Docker compose cannot create the default network on worker-j9jjd.

Conclusion: tau3 is image-ready and runner-contract-ready for oracle dry-run, but not adapter-smoke-ready on the worker.

## Paths

- Shared runner: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh`.
- Runner backup before Round29: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29/run_tau3_bench.before_round29.sh`.
- Runner current sha256: `469470ffddb2c9753707e80b1194e37680c20477fa72774ee64a85b1f71284a6`.
- Runner pre-Round29 sha256: `db5a9559234c24cde85c0c01582ef6ac9ac5331538422115e8cc249a1689c646`.
- Copied/patched dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29/dataset/tau3-airline-0`.
- First worker execute artifact root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29`.
- Parse-check execute artifact root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29_parsecheck`.
- Parse-check result summary: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29_parsecheck/runner_execute/tau3_bench/gpt-5.4_parsecheck_execute/tau3_result_summary.json`.
- #8 comment: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4805622535

## Runner Contract Changes

`run_tau3_bench.sh` now has these behavior changes on the shared bench path:

- `TAU3_AGENT=${TAU3_AGENT:-tau3_llm_agent}`.
- `TAU3_AGENT=oracle` builds `harbor run -a oracle -k ... -n ... -r ... --no-force-build --yes`.
- Oracle mode does not include `-m`, `--agent-import-path`, `--ak`, `OPENAI_API_KEY`, or `OPENAI_BASE_URL` in `command.sh`.
- Oracle mode unsets model/API env vars around the Harbor call.
- Default `tau3_llm_agent` mode still emits the original model-backed command and now also includes `--no-force-build`.
- `HARBOR_BIN` overrides the default `uv run ... harbor run` prefix.
- After Harbor execution, the runner writes `tau3_result_summary.json` and returns nonzero when the latest job result reports errors/no trials/no successful eval trials.

## Dataset Copy Changes

Only the copied smoke dataset was patched; the full/generated dataset and adapter templates were not changed.

- `task.toml` now sets empty defaults for `OPENAI_API_KEY` and `OPENAI_BASE_URL` in verifier/environment env maps.
- `task.toml` sets `docker_image` to the tau3 r2 main image digest.
- `environment/docker-compose.yaml` replaces the sidecar build stanza with the tau3 r2 runtime image digest and `pull_policy: never`.
- The patched copy passed `python3 -m compileall -q <dataset>/tests`.
- Grep verification found no required `${OPENAI_API_KEY}`, no required `${OPENAI_BASE_URL}`, and no `build:` stanza in the patched copy.

## Worker Evidence

Worker image cache preflight passed for both r2 digest refs:

- Main image: `sha256:80c0d9453584d67f4fd89f53f6f47e2503870f7663d3615384f6e23f6dcc0e78`.
- Runtime image: `sha256:b06571be24cf17bb4d04f4f0c76e7209ed112e2bfde48923477d34999581aefb`.

Worker runner dry-run with `HARBOR_BIN` passed:

- Artifact root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29/runner_dryrun_harbor_bin`.
- `command.sh` contains direct `harbor run -a oracle --no-force-build`.
- `command.sh` does not contain `uv run`, `--agent-import-path`, ` -m `, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `tau3_llm_agent`.

First real worker oracle smoke before result parsing returned wrapper rc 0 but Harbor stats had an exception:

- Harbor output: `Trials=0`, `Exceptions=1`, `Mean=0.000`.
- Job result: `n_total_trials=1`, `n_errors=1`, `oracle__dataset.n_trials=0`.
- Exception: rootless Docker compose failed to create network with `operation not permitted`.

After adding result parsing, the parse-check smoke returned wrapper rc 1 as intended:

```json
{
  "status": "errors",
  "n_total_trials": 1,
  "n_errors": 1,
  "successful_eval_trials": 0
}
```

## Remaining Blockers

- Worker rootless Docker cannot create compose/default networks: `docker network create tau3-rootless-probe` returns `operation not permitted`.
- `docker run --network host` also fails with a netlink namespace permission error.
- `docker run --network none` succeeds, but Harbor's compose path is not yet proven with a no-network task.
- A minimal compose `network_mode: none` probe hit the known Docker compose `/v1.45/version` EOF instability, so compose itself is still not a clean rootless execution substrate on this worker.
- Even oracle mode emitted a LiteLLM warning attempting to fetch a remote model-cost map from GitHub before falling back locally. The Harbor environment needs an explicit offline/no-public-egress setting before any worker run is called offline-clean.

## Validation

- Shared runner `bash -n` passed after the oracle/HARBOR_BIN/result-parser changes.
- Dev dry-run and worker dry-run both passed for `TAU3_AGENT=oracle`.
- Worker parse-check execute returned rc 1 on the known Harbor exception, proving wrapper false-success is fixed.
- Round artifact bounded secret scan passed.
- No suite readiness promotion was made. `manifests/suite.example.yaml` should keep `tau3_bench` disabled and `adapter_status: pending_adapter` until the rootless compose/offline blocker is cleared and a real one-task oracle result succeeds.
