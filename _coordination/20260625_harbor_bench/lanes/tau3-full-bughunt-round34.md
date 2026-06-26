# tau3 full adapter/readiness bug-hunt Round34

Date: 2026-06-26
Lane: tau3 full adapter/readiness
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Branch/head checked: `feat/image-warmup-policy` at `008d466 Align active bench taxonomy`
Scope: static/read-only probes plus report write only. No model calls. No Docker build/run/pull/load/save.
Report path: `_coordination/20260625_harbor_bench/lanes/tau3-full-bughunt-round34.md`

## Executive summary

The current suite correctly keeps the oracle-direct helper from satisfying the full `tau3-bench` readiness target: `--readiness --target-benches tau3-bench` exits nonzero and reports the full target blocked by disabled/pending adapter state. That is good and should stay.

However, the remaining full-run blockers are still real. The full `tau3_bench` row is configured as `TAU3_MODE=smoke` and `TAU3_LIMIT=1`, its image preflight is optional, the generated full dataset still asks Harbor/Docker to build public-source Dockerfiles instead of binding the r2 images, and the shared wrapper runs one `tau2_trial_index` even though the adapter parity config uses three. A maintainer could flip `enabled` and `adapter_status` and get a green full readiness report for a one-task smoke with optional image checks.

## Current evidence

- Current full readiness is blocked as expected: `scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --json --target-benches tau3-bench` returned `rc=1` with blockers `no_enabled_suite_entry`, `suite_entry_disabled`, and `adapter_not_wired`.
- The helper row is ready but excluded from full aggregation: readiness JSON had `ready_entry_count=1`, `aggregation_ready_entry_count=0`, and `entries.tau3_bench_oracle_direct_smoke.readiness_role=image_smoke`.
- A safe in-memory mutation that only flips `tau3_bench.enabled=True` and `tau3_bench.adapter_status=wired_legacy` makes readiness green while preserving `TAU3_MODE=smoke`, `TAU3_LIMIT=1`, and `image_preflight.required=false`.
- Full dataset material exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets/tau3-bench` with 375 task directories, 375 `task.toml`, and 375 `task_config.json` files.
- The generated full dataset still has 375 compose files with `build:`, 0 `docker_image:` entries, 375 runtime build contexts, 750 tau2 repo/GitHub build references, and 0 `pull_policy: never` entries.

## ISSUE-READY: full tau3 row can become ready while still running one-task smoke

file:line:
- `manifests/suite.example.yaml:306` defines the full target id `tau3_bench`.
- `manifests/suite.example.yaml:315` sets `TAU3_MODE: smoke`.
- `manifests/suite.example.yaml:316` sets `TAU3_LIMIT: 1`.
- `manifests/suite.example.yaml:320` currently keeps the row disabled.
- `scripts/agentic_bench_suite.py:944` starts `build_readiness_report` aggregation.
- `scripts/agentic_bench_suite.py:962` records blockers from `bench.enabled` / `adapter_status` but does not validate tau3 full-mode task count.
- `scripts/agentic_bench_suite.py:976` marks the entry ready when the generic blockers are absent.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && python3 - <<"PY"
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location("suite", "scripts/agentic_bench_suite.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
suite = mod.load_suite(Path("manifests/suite.example.yaml"))
for bench in suite.benchmarks:
    if bench.id == "tau3_bench":
        bench.enabled = True
        bench.adapter_status = "wired_legacy"
        target = bench
report = mod.build_readiness_report(suite, target_benches={"tau3-bench"})
plan = mod.build_run_plan(suite, bench_ids={"tau3_bench"})
print(json.dumps({
  "params": target.params,
  "image_preflight_required": plan.runs[0].image_preflight.required,
  "target_status": report["targets"][0]["status"],
  "target_blockers": report["targets"][0]["blockers"],
  "aggregation_ready_entry_count": report["targets"][0]["aggregation_ready_entry_count"],
}, indent=2, sort_keys=True))
PY'
```

Observed output included:

```json
{
  "aggregation_ready_entry_count": 1,
  "image_preflight_required": false,
  "params": {
    "MAX_CONCURRENCY": 1,
    "TAU3_LIMIT": 1,
    "TAU3_MODE": "smoke",
    "TAU3_N_CONCURRENT": 1
  },
  "target_blockers": [],
  "target_status": "ready"
}
```

impact:
A future wiring change can make `tau3-bench` appear fully ready for one-command worker execution while it is still configured for a one-task smoke. This would let the readiness report claim full target readiness without proving the 375-task dataset, full dataset path, or full result semantics.

fix:
Split the row semantics explicitly. Keep `tau3_bench_oracle_direct_smoke` as `readiness_role: image_smoke`; change the full `tau3_bench` row to `TAU3_MODE=full`, remove `TAU3_LIMIT` or set an explicit expected count of 375, set `TAU3_GENERATE_DATASET=0`, and set `TAU3_DATASET_DIR` to the frozen full dataset path. Add a tau3-specific readiness check that fails if the full row has `TAU3_MODE=smoke`, `TAU3_LIMIT=1`, or no verified 375-task manifest.

dedup:
Related to the existing helper-not-fake-green coverage, but this is not the same issue: the helper is excluded correctly today. The new failure mode is the full row itself becoming green with smoke parameters after only flipping `enabled` and `adapter_status`.

## ISSUE-READY: full tau3 image preflight is optional despite required r2 images

file:line:
- `manifests/suite.example.yaml:311` points the full target at `manifests/images/tau3_bench.yaml`.
- `manifests/suite.example.yaml:312` sets `image_policy: optional`.
- `manifests/images/tau3_bench.yaml:38` marks the main image as `required: true`.
- `manifests/images/tau3_bench.yaml:53` marks the runtime image as `required: true`.
- `scripts/agentic_bench_suite.py:632` starts `_image_preflight_for_bench`.
- `scripts/agentic_bench_suite.py:646` computes `required = policy not in {"optional", "none", "disabled", "skip"}`.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && python3 - <<"PY"
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location("suite", "scripts/agentic_bench_suite.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
suite = mod.load_suite(Path("manifests/suite.example.yaml"))
for bench in suite.benchmarks:
    if bench.id == "tau3_bench":
        bench.enabled = True
        bench.adapter_status = "wired_legacy"
plan = mod.build_run_plan(suite, bench_ids={"tau3_bench"})
preflight = plan.runs[0].image_preflight
print(json.dumps({"policy": preflight.policy, "required": preflight.required, "manifest": preflight.manifest}, indent=2))
PY'
```

Observed output:

```json
{
  "policy": "optional",
  "required": false,
  "manifest": "manifests/images/tau3_bench.yaml"
}
```

impact:
The full target can proceed without fatal image verification even though the image manifest declares both tau3 r2 images required. Missing, stale, or mismatched local tags would surface later as adapter or Harbor failures instead of a clear readiness/preflight blocker.

fix:
Set the full `tau3_bench` row to `image_policy: required` once it is intended to be executable. Add a regression that an enabled full tau3 row produces `image_preflight.required=true` and that the readiness report remains blocked if required images are unavailable or only the oracle-direct helper has passed.

dedup:
Related to image identity hardening work, but this is specific to the full tau3 suite row and should not be considered covered by the oracle-direct helper's `image_policy: required` setting.

## COMMENT-READY: generated full dataset still builds public-source Dockerfiles instead of using r2 images

file:line:
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/task-template/task.toml:18` starts the verifier environment without a prebuilt `docker_image` binding.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/task-template/environment/docker-compose.yaml:7` defines `tau3-runtime` with `build:`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/task-template/environment/Dockerfile:5` starts a public-source build path with apt/git/pip setup.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/task-template/environment/runtime-server/Dockerfile:5` does the same for the runtime sidecar.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets/tau3-bench/tau3-airline-0/environment/docker-compose.yaml:7` shows the generated full dataset inherited the runtime build context.
- `manifests/images/tau3_bench.yaml:41` and `manifests/images/tau3_bench.yaml:56` contain the r2 digest refs that the generated dataset does not consume.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && FULL=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets/tau3-bench && printf "task_dirs=" && find "$FULL" -mindepth 1 -maxdepth 1 -type d | wc -l && printf "compose_build=" && grep -R "^[[:space:]]*build:" "$FULL"/*/environment/docker-compose.yaml | wc -l && printf "docker_image=" && grep -R "docker_image" "$FULL" | wc -l && printf "tau2_repo_args=" && grep -R "ARG TAU2_REPO_URL\|git clone --depth 1" "$FULL"/*/environment/Dockerfile "$FULL"/*/environment/runtime-server/Dockerfile | wc -l && printf "pull_policy_never=" && grep -R "pull_policy: never" "$FULL" | wc -l'
```

Observed counts:

```text
task_dirs=375
compose_build=375
docker_image=0
tau2_repo_args=750
pull_policy_never=0
```

impact:
The full dataset is image-ready only at the external manifest layer. The actual Harbor task material still asks Docker/compose to build the main and runtime images from public sources. On the offline/rootless worker path, that can reintroduce public apt/GitHub/pip egress and rootless compose build/network failures instead of consuming the staged r2 images.

fix:
Patch the tau3 adapter template/generator to accept pinned main/runtime image refs from `manifests/images/tau3_bench.yaml`, emit a generated dataset that uses those images, and avoid build contexts for offline worker runs. Then regenerate/freeze the full dataset and add a smoke that checks `build:` count is 0, prebuilt image refs are present, and no public-source build fallback remains in the generated full dataset.

dedup:
This should likely be filed as a comment on the existing rootless/offline compose blocker if that issue already tracks tau3 Harbor full execution. The additional evidence here is the full-dataset aggregate proving the r2 images are not yet wired into the generated task material.

## ISSUE-READY: shared full wrapper does not encode the three-trial tau3 parity contract

file:line:
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:15` defaults `TAU3_N_ATTEMPTS=1`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:16` defaults `TAU3_N_RETRIES=0`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:180` starts the `tau3_llm_agent` Harbor command.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:192` passes only `--ak tau2_trial_index=0`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/run_tau3-bench.yaml:12` starts the first `tau3_llm_agent` entry.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/run_tau3-bench.yaml:18` starts the second `tau3_llm_agent` entry.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/run_tau3-bench.yaml:24` starts the third `tau3_llm_agent` entry.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/README.md:131` documents the parity config with three trial indices.

static repro/command:

```bash
ssh dev 'grep -n "TAU3_N_ATTEMPTS\|tau2_trial_index\|name: tau3_llm_agent" /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/run_tau3-bench.yaml /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/README.md'
```

Observed evidence:

```text
/mnt/.../bench/run_tau3_bench.sh:15:TAU3_N_ATTEMPTS="${TAU3_N_ATTEMPTS:-1}"
/mnt/.../bench/run_tau3_bench.sh:192:    --ak tau2_trial_index=0 \
/mnt/.../harbor/adapters/tau3-bench/run_tau3-bench.yaml:12:    name: tau3_llm_agent
/mnt/.../harbor/adapters/tau3-bench/run_tau3-bench.yaml:18:    name: tau3_llm_agent
/mnt/.../harbor/adapters/tau3-bench/run_tau3-bench.yaml:24:    name: tau3_llm_agent
/mnt/.../harbor/adapters/tau3-bench/README.md:131:run config intentionally lists tau3_llm_agent three times with tau2_trial_index 0, 1, 2
```

impact:
A full one-command run through the shared wrapper can execute only one tau3 trial index even after the dataset/image/rootless blockers are fixed. That would not match the adapter's documented parity path or pass^k/average reward semantics, so readiness could be claimed for a partial metric.

fix:
Add an explicit full-mode metric contract. Either call the adapter's `run_tau3-bench.yaml` parity config directly or teach `run_tau3_bench.sh` to loop/aggregate `tau2_trial_index=0,1,2` for full mode. The output summary should record trial count, trial indices, per-trial artifacts, and aggregate metric fields so the suite parser can distinguish smoke, oracle-direct, and full parity runs.

dedup:
New full-readiness semantic gap. Related to the missing suite parser comments below, but parser support alone would not fix the one-trial runner behavior.

## COMMENT-READY: full dataset freeze/checksum contract is still missing

file:line:
- `manifests/images/tau3_bench.yaml:9` records `full_dataset_path`.
- `manifests/images/tau3_bench.yaml:13` records `full_task_count: 375`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:25` defaults `TAU3_GENERATE_DATASET=1`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:54` regenerates the dataset if generation is enabled.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/adapters/tau3-bench/main.py:31` exposes `--overwrite`.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && find . /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets -maxdepth 5 \( -iname "*tau3*freeze*" -o -iname "*tau3*manifest*" -o -iname "*tau3*sha256*" \) -print'
```

Observed output: no matching freeze/checksum/task-manifest file in the searched repo, bench, or generated dataset roots.

impact:
The manifest records counts and paths, but not a frozen task-id list, per-task checksums, adapter source commit, tau2 source commit, or generated-template version. A full run can therefore drift by regeneration or template changes without a direct way to prove that the exact 375-task corpus was used.

fix:
Publish a frozen tau3 full dataset manifest containing sorted task ids, domain counts, per-task `task.toml` / `task_config.json` hashes, adapter commit, tau2 source commit, and template version. Set the full suite row to `TAU3_GENERATE_DATASET=0` and the canonical `TAU3_DATASET_DIR`; readiness should require the freeze manifest before full status can become ready.

dedup:
Likely a new readiness hardening comment rather than a separate blocker issue if the owner already tracks full dataset freezing elsewhere. I did not find a dedicated freeze artifact in the bounded paths above.

## COMMENT-READY: rootless Harbor/compose path remains unproven; oracle-direct smoke bypasses it

file:line:
- `manifests/images/tau3_oracle_direct_smoke.yaml:12` states that the direct helper executes only the main task image and does not use the tau3 runtime sidecar image.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets/tau3-bench/tau3-airline-0/environment/docker-compose.yaml:7` still defines the `tau3-runtime` sidecar for full generated tasks.
- `_coordination/20260625_harbor_bench/HANDOFF.md:398` records the worker rootless compose failure creating the default network with `operation not permitted`.
- `_coordination/20260625_harbor_bench/lanes/tau3-adapter-round30.md:76` records the same compose/default-network blocker and Docker `/v1.45/version` EOF caveat.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && grep -n "does not use tau3 runtime sidecar\|operation not permitted\|/v1.45/version\|default network" manifests/images/tau3_oracle_direct_smoke.yaml _coordination/20260625_harbor_bench/HANDOFF.md _coordination/20260625_harbor_bench/lanes/tau3-adapter-round30.md && grep -n "tau3-runtime\|build:" /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe/bench/swe-atlas/harbor/datasets/tau3-bench/tau3-airline-0/environment/docker-compose.yaml'
```

impact:
The passing oracle-direct image smoke proves the main image can run one task under `docker run --network none`; it does not prove Harbor's full task lifecycle, compose sidecar startup, MCP/API path, or server reset behavior under the rootless worker constraints.

fix:
Before full readiness, require a no-public-network Harbor smoke on the worker rootless Docker path that uses the generated task material and prebuilt main/runtime images. The smoke should prove sidecar startup, reset/snapshot behavior, API access, and summary artifact parsing without requiring public egress or privileged networking.

dedup:
COMMENT-READY for the existing rootless Harbor/compose issue. This is not a new issue if that blocker is already tracked; it is the Round34 confirmation that the helper smoke still cannot retire the full Harbor blocker.

## COMMENT-READY: suite result parser still cannot normalize tau3 summaries

file:line:
- `scripts/agentic_bench_suite.py:1584` starts `_benchmark_result_for_run`.
- `scripts/agentic_bench_suite.py:1588` only has a RepoZero native parser path.
- `scripts/agentic_bench_suite.py:1606` returns `parser_status=no_parser` for successful non-RepoZero adapters.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:286` writes `tau3_result_summary.json` with pass/fail/error counts.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && sed -n "1584,1611p" scripts/agentic_bench_suite.py && sed -n "286,310p" /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh'
```

impact:
Even after a full tau3 run succeeds and writes the wrapper summary, the suite-level native result layer will classify it as `status=unknown`, `parser_status=no_parser`, and `failure_category=native_artifact_missing`. That prevents one-command worker runs from producing first-class pass/fail tau3 results.

fix:
Add a tau3 native parser for `tau3_result_summary.json` and fixtures for passed, failed, and infra-error summaries. The parser should expose mode, task count, trial count, pass/fail/error counts, aggregate reward if present, artifact path, and a clear failure category.

dedup:
COMMENT-READY for existing result-parser issues, previously noted as #1/#12 in Round31. No new issue needed if those remain open.

## COMMENT-READY: bench registry status is stale relative to r2 image manifest

file:line:
- `manifests/bench_registry.yaml:71` starts the `tau3_bench` registry row.
- `manifests/bench_registry.yaml:73` still says `status: dataset_ready_offline_images_pending`.
- `manifests/bench_registry.yaml:74` still says `policy: disabled_until_runtime_images_prebuilt`.
- `manifests/images/tau3_bench.yaml:4` says `status: smoke_images_ready_worker_rootless`.

static repro/command:

```bash
ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && sed -n "71,74p" manifests/bench_registry.yaml && sed -n "1,8p" manifests/images/tau3_bench.yaml'
```

impact:
The top-level registry still communicates that offline tau3 runtime images are pending, while the image manifest says smoke images are ready on the worker rootless path. That can send coordination lanes toward image materialization instead of the remaining full-adapter/rootless/readiness blockers.

fix:
Update the registry wording when production files are in scope, for example `status: smoke_images_ready_full_adapter_pending` and `policy: disabled_until_full_adapter_rootless_smoke_and_parser_ready`.

dedup:
COMMENT-READY taxonomy/status cleanup. It is not the root cause of full execution failure.

## Non-findings / cleared checks

- The current readiness aggregation does not let `tau3_bench_oracle_direct_smoke` fake-green the full target. This is covered by the explicit `readiness_role: image_smoke` row and current readiness output.
- The current suite worker env propagates the rootless Docker API caveat: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45` are present in the in-memory run plan for tau3.
- I did not run Docker, Harbor, model calls, or benchmarks. All findings above are static/read-only or in-memory suite-plan/readiness probes.

## Commands run

| Command | rc | Notes |
| --- | ---: | --- |
| `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required local workflow preflight. |
| `sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required local workflow preflight. |
| `sed -n '621,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required local workflow preflight. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && git branch --show-current && git rev-parse --short HEAD && git status --short'` | 0 | Confirmed branch `feat/image-warmup-policy`, head `008d466`, clean status before report write. |
| `ssh dev 'cd ... && sed -n "306,340p" manifests/suite.example.yaml && sed -n "1,80p" manifests/images/tau3_bench.yaml && sed -n "1,60p" manifests/images/tau3_oracle_direct_smoke.yaml'` | 0 | Inspected suite tau3 rows and image manifests. |
| `ssh dev 'cd ... && sed -n "930,990p" scripts/agentic_bench_suite.py && sed -n "632,739p" scripts/agentic_bench_suite.py'` | 0 | Inspected readiness aggregation and image preflight. |
| `ssh dev 'cd ... && python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --json --target-benches tau3-bench > /tmp/tau3_readiness_round34.json; ...'` | 0 wrapper, 1 captured readiness rc | Current readiness is blocked for full tau3 and helper is not aggregated as full. |
| `ssh dev 'cd ... && python3 - <<PY ... build_run_plan/build_readiness_report in-memory mutation ... PY'` | 0 | Demonstrated full row can become ready with smoke params and optional image preflight if only enabled/wired. |
| `ssh dev 'sed -n "1,330p" /mnt/.../bench/run_tau3_bench.sh'` | 0 | Inspected shared tau3 wrapper. |
| `ssh dev 'sed -n "1,220p" /mnt/.../harbor/adapters/tau3-bench/README.md && sed -n "1,80p" .../run_tau3-bench.yaml'` | 0 | Inspected adapter parity contract. |
| `ssh dev 'sed -n "1,220p" /mnt/.../harbor/adapters/tau3-bench/main.py && sed -n "1,220p" .../adapter.py'` | 0 | Inspected generator/adapter source behavior. |
| `ssh dev 'sed -n "1,120p" /mnt/.../harbor/adapters/tau3-bench/task-template/task.toml && sed -n "1,80p" .../task-template/environment/docker-compose.yaml && ...'` | 0 | Inspected template Docker/build/env material. |
| `ssh dev 'FULL=/mnt/.../harbor/datasets/tau3-bench && find "$FULL" ... && grep -R ...'` | 0 | Counted full generated dataset files and image/build patterns. |
| `ssh dev 'cd ... && find . /mnt/.../bench /mnt/.../harbor/datasets -maxdepth 5 \( -iname "*tau3*freeze*" -o ... \) -print'` | 0 | No full freeze/checksum/task manifest found in bounded paths. |
| `ssh dev 'cd ... && grep -n "tau3" manifests/bench_registry.yaml && sed -n "3277,3390p" _coordination/.../hunt-runner-results.md && ...'` | 0 | Checked prior dedup/status evidence. |

## Final repair gates before full one-command worker readiness

1. Full row must be full-sized: `TAU3_MODE=full`, no one-task smoke limit, frozen dataset path, and dataset generation disabled.
2. Full row image preflight must be required and must validate the main/runtime r2 refs actually used by generated tasks.
3. Generated full dataset must consume prebuilt images and avoid public build contexts under the offline worker path.
4. Worker rootless Harbor/compose smoke must pass with runtime sidecar/API/reset behavior, not only oracle-direct `docker run`.
5. Wrapper/adapter must encode the three-trial tau3 parity contract or document a different accepted full metric.
6. Suite result parsing must normalize `tau3_result_summary.json` into pass/fail/status fields.
7. A freeze manifest must lock the 375-task corpus and hashes before full readiness can be stable.
