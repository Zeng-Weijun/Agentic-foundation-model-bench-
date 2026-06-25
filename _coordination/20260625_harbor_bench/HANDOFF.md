# Harbor Bench Handoff

Updated: 2026-06-26 post-batch9 Asia/Shanghai

## Objective

Build the Harbor/P0-registry-backed bench runner path so a future worker can run all listed agentic benchmarks from one shell/YAML command, with offline image warmup/checks separated from actual benchmark adapter execution.

## Current Repo State

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch: `feat/image-warmup-policy`
- Latest implementation commit: `c55bfab Materialize TB2 medium transport batch 9`; this handoff update follows as a coordination-only commit.
- Original base commit for this workstream: `c42f23c Record runtime image hunt issues`
- Driver doc: `_coordination/20260625_harbor_bench/DRIVER.md`
- Remote worker: `worker-j9jjd`
- Worker Docker socket: `unix:///tmp/rl/run/docker.sock`

## Agent Surface Map

- Orchestrator: `surface:49`
- Continuous hunt A: `surface:50` -> `hunt-runtime-images`
- Continuous hunt B: `surface:54` -> `hunt-runner-results`
- Reserved, not bug hunt: `surface:51`
- Reserved, not bug hunt: `surface:55`

## In Flight

- Main implementation: image preflight warmup policy in `scripts/agentic_bench_suite.py` and `scripts/agentic_bench_images.py` plus tests/docs.
- tau3-bench: full 375-task Harbor dataset generated; shared runner dry-run/redaction verified; worker execution remains disabled pending offline images and Harbor CLI env.
- Image inventory: `swe_dev` has substantially more SWE-bench/TB2.1 Docker images than worker; shared TB2.1 tars are partial, so worker full runs need staging from `swe_dev` cache. Current inventory artifacts: `_coordination/20260625_harbor_bench/inventory/swe_dev_data_inventory_20260626.md`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`, and identity-enriched `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`.
- Terminal-Bench 2.1: `terminal_bench_2_1_image_smoke` is enabled for image preflight using `gcode-to-text`; worker rootless check passes via cached/verified fallback image, while full TB execution remains pending adapter/runtime result wiring.
- Bug-hunt pair: only surface:50 and surface:54 produce `_coordination/20260625_harbor_bench/lanes/*.md`; each must cross-check the other's ledger before the orchestrator files issues.
- Current Round 19 completed: surface:50 audited the remaining 14 TB2 rows and recommended batch9A as `portfolio-optimization`, `sam-cell-seg`, `train-fasttext`, and `video-processing`; surface:54 produced #12/#13 fixture-ready guidance for batch8 image-check provenance. Batch9A is now materialized. Next dispatch should audit the remaining 10 TB2 `missing_shared_tar` rows: `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `pytorch-model-cli`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `reshard-c4-data`, `torch-pipeline-parallelism`, and `torch-tensor-parallelism`. Both hunt lanes stay ledger-only unless explicitly promoted by the orchestrator.
- GitHub issue filing: runner-results lane filed/deduped through REST API:
  - #1 Separate adapter execution status from benchmark result status.
  - #2 Make suite run output directories invocation-unique.
  - #3 Persist execute summary results in manifest order.
- Issue #3 is fixed in commit `933544e` by sorting persisted `_execute_plan` summary results back to manifest order, commented, and closed.
- Issue #1 has partial foundation in commit `b4d3a0c`: `_execute_plan()` now writes normalized `agentic_bench.result.v1` artifacts and summary fields for execution/benchmark status separation, with first parser coverage for RepoZero Py2JS. #1 remains open for VitaBench/CoCoA/SWE-bench/Terminal-Bench/DeepSWE/tau3 parser coverage.
- Issue #2 remains open follow-up implementation item.
- Runtime-images lane filed #4 through #8:
  - #4 Make image preflight project_root follow the active suite/worktree.
  - #5 Make optional image audit failures fatal when requested.
  - #6 Support pull/load-fallback/run-smoke in suite image preflight warmup.
  - #7 Make image-preflight-only fail on explicitly selected empty plans.
  - #8 Split rootless Docker health between info, version, SDK, and compose readiness.
- Current branch fixes #4/#5/#6/#7 pending commit/push/issue close; #8 remains open.
- Issue #9 tracks VitaBench parser redaction for native Authorization headers; filed from runner-results lane evidence without printing any secret values.
- Runtime-images lane comments posted: #6 image warmup cap/dedupe comment and #8 worker rootless P0 pull-vs-fallback evidence comment.
- Image preflight follow-up: suite plan now carries a separate max concurrency cap and dedupes identical preflight commands so image pull/load does not inherit or stampede at suite concurrency 40.
- Issue #10 tracks parser source allowlists for secret-bearing adapter sidecars; runner-results lane comments posted to #1/#2/#9 for pointer contract, invocation-unique run dirs, and Vita config redaction.
- Issue #11 tracks SWE-bench image identity/lineage checks; implemented in `f2925bf`, with image manifest fields for expected/source image IDs and repo digests plus `identity_mismatch` failure status. Runtime-images lane Round 5 posted additional django-10097 two-artifact promotion evidence to #11/#6.
- Issue #12 tracks normalized result provenance. Runner-results Round 9 produced the safe `source.native_artifacts[]` role/status map for RepoZero, tau3, SWE-bench, Terminal-Bench 2.1, and DeepSWE.
- Issue #13 tracks raw image-preflight checker stdout/stderr being written into controller `.image_preflight.log` before parser/result redaction; filed from Round18 runner-results evidence.
- Registry-selected static transport gate now exists as `python3 scripts/agentic_bench_images.py lint-registry`. It lints selected `bench_registry.yaml` rows by repeated/comma-separated `--policy` or `--manifest-id`, returning nonzero if required rows lack internal digest refs or fallback tar checksums. `--verify-fallback-files` additionally verifies configured fallback tar presence and sha256 without Docker.
- Issue comments posted after `ce2adf2`: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4802817585`, #11 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/11#issuecomment-4802817769`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4802817962`, #10 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/10#issuecomment-4802818184`.
- SWE django fallback follow-up comments posted after `bacbde3`: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4802915881`, #11 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/11#issuecomment-4802916080`.
- Verify-fallback/protein-assembly comments posted after `12fe709`: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803028702`, #11 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/11#issuecomment-4803028892`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4803029063`.

## Red Lines

- Concrete code execution on remote shared paths, not Mac-local paths.
- Durable artifacts under `/mnt/shared-storage-user/mineru2-shared/zengweijun`.
- Do not use stale worker aliases.
- Do not print tokens.
- Do not let multiple agents write production files in the same worktree.
- No `/clear` on active agents.

## Next Wakeup Prompt

Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then this handoff. Run `cmux surface-health` and read surfaces 50 and 54 by content as the only continuous bug-hunt pair; read 51/55 only if they were explicitly assigned implementation review or smoke. Collect new `ISSUE-READY` blocks from `_coordination/20260625_harbor_bench/lanes/*.md`, cross-check the two ledgers, dedup against GitHub/open reports, file issue/comment if confirmed, and keep the two hunt agents busy. Continue main implementation from the active shared worktree. Next main step: publish or record transport for the remaining 10 TB2 cache rows via P0 digest refs plus verified fallback tar sha. Keep QEMU, torch/pytorch, largest data rows, and medium generic/data rows separated. SWE django10097 fallback transport is verified and worker-smoked, but P0 digest publication remains preferred for scale when worker rootless Docker can reach the registry. Run worker runtime `check`/smoke via explicit worker-j9jjd endpoint. Suite/model benchmark concurrency can be 40-50 on the 60-CPU worker when images are warm; image transport load/pull concurrency stays capped separately at 2-4.

## Acceptance Snapshot

- Warmup-policy red tests added and observed failing for missing checker flags, optional fatality, suite-relative project roots, and empty selected plans.
- Target tests pass: done; 5 focused tests pass.
- Full unittest/py_compile/diff-check: done; 22 unittest pass, py_compile rc 0, `git diff --check` rc 0.
- Dry-run with `manifests/suite.example.yaml --only repozero_py2js_smoke` resolves `project_root` to the active worktree and forwards `--load-fallback --run-smoke`.
- Old customer-service suite entry removed per user direction; current no-adapter smoke examples use RepoZero/tau3 paths.
- Worker RepoZero image-preflight-only smoke: done through local control-plane SSH to worker with a temporary local-execution suite; output `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/verification/repozero_warmup_policy_20260626_001953`; summary status 0, required preflight pass, RepoZero image present, fallback tar sha256 match, container smoke passed.
- Worker DeepSWE optional image audit: `--fail-on-optional-missing` returns rc 1 with `optional_missing: 1`, closing the prior optional-image fake-green path.
- Direct `swe_dev -> worker` remains blocked by publickey; local Mac -> worker works.
- Local `worker` SSH alias was observed pointing at stale `worker-pshjt`; use the explicit `worker-j9jjd` endpoint from `WORKFLOW.md` until aliases are corrected.
- `swe_dev` `/data/swe/SWE-bench` and `/data/tmp/tb2-prebuild-save` are empty; the useful state is Docker local cache plus shared bench trees. swe_dev cache counts: 500 `swebench/sweb.eval...`, 728 `swerex-prebuilt`, 89 `tb2-offline`, 3 `sweb.*` helper images. Shared Terminal-Bench 2.1 has 50 `.tar` fallbacks plus 1 `.tar.gz`, so TB2 full image readiness is still partial relative to swe_dev cache.
- Generated image manifests now include `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` (89 TB2 rows from swe_dev cache, 79 with verified fallback/P0 transport; 10 still marked `missing_shared_tar`) and `manifests/images/swebench_verified_django10097.yaml` (official eval base + swerex wrapper identity probe). SWE django10097 now has verified fallback tar sha for both rows; worker-j9jjd `--load-fallback --run-smoke` loaded the official eval base over the prior wrapper alias mismatch and ended with `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, `identity_mismatch=0`.
- Static image manifest lint is available via `python3 scripts/agentic_bench_images.py lint --require-offline-transport`; current TB2 generated cache status is 79 configured fallback tars verified by `check --skip-docker`, with 10 rows still marked `fallback_status: missing_shared_tar` by manifest audit.
- Registry-selected lint validation after batch9: `validate` rc 0 with `manifests=9/images=104/required_images=94`; full `lint-registry --verify-fallback-files` reports `fallback_tar_verified=79`, `fallback_tar_missing=1`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=0`. The remaining missing file is the pre-existing RepoZero relative tar path, not a TB2 batch8 artifact.
- Latest full verification after batch9: `python3 -m unittest scripts.test_agentic_bench_images scripts.test_agentic_bench_suite scripts.test_offline_images_manifest` passed 36 tests; `validate`, `git diff --check`, TB2 static fallback check, registry fallback lint, worker fallback smoke, and bounded secret scan passed. Full registry fallback lint currently reports `fallback_tar_verified=83`, `fallback_tar_missing=1` for the existing RepoZero relative tar path, `fallback_tar_mismatch=0`, and `required_without_offline_transport=0`.
- Merge/push/sync shared main checkout: pending for current branch; latest pushed main is `c42f23c` before this warmup-policy commit.

## 2026-06-26 SWE django10097 fallback evidence

- Official eval base fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/swebench/django10097/swebench_django10097_eval_base.tar` (`sha256:b1581243bc031c9dfb246095c039814f5f349c703bb3d67aecde11c239fb8616`).
- Wrapper fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar` (`sha256:2ba506ed3e6ff4fdbb2ed54612b633ed782b4604a7b94a9d49173b0b2fb73275`).
- Tracked sha evidence: `_coordination/20260625_harbor_bench/inventory/swebench_django10097_fallback_sha256_20260626.tsv`.
- Worker command: `agentic_bench_images.py check --image-manifest manifests/images/swebench_verified_django10097.yaml --load-fallback --run-smoke --json` via explicit worker-j9jjd endpoint and `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`; result `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, `identity_mismatch=0`.

## 2026-06-26 TB2 protein-assembly P0/fallback evidence

- Source image: `tb2-offline/protein-assembly:20260425`, source image id `sha256:c517a0dd99f0991faa3f68ae50943b49a55ca7604abbac6b7d824ed4a71bcd6f`.
- P0 digest ref: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-protein-assembly@sha256:1144842bb39d1bf67d8925879202101caf6250a8a7a83fcf1e582496991004e9`.
- Fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/protein-assembly.tar`, sha256 `97176112820eb4c1b079878de2cad0aeefa1fd4661da51a42431ac7ce80fa5c1`.
- Worker-j9jjd direct P0 consumer smoke passed: `docker pull <digest-ref>` and `docker run --rm --network none <digest-ref> /bin/sh -lc 'echo tb2-protein-assembly-smoke-ok'`.
- TB2 generated manifest static gate now reports 24 missing offline transports; `check --skip-docker` reports `tar_verified=65`, `tar_mismatch=0`, `tar_missing=0`. `lint-registry --verify-fallback-files` over TB2+SWE reports `fallback_tar_verified=67`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=24`.
- Tracked evidence: `_coordination/20260625_harbor_bench/inventory/tb2_p0_protein_assembly_20260626.tsv`.

## 2026-06-26 verify-fallback-files evidence

- Added `--verify-fallback-files` to `agentic_bench_images.py lint` and `lint-registry`; it verifies configured fallback tar paths and sha256 values during static promotion lint.
- Regression tests cover direct manifest lint and registry CLI behavior when a row has a sha field but the tar is absent.
- Initial TB2+SWE promotion gate with `--verify-fallback-files` returned `fallback_tar_verified=53`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=38`; latest batch9 evidence below updates TB2-only check to `tar_verified=79` and leaves 10 TB2 rows marked `missing_shared_tar`.

## 2026-06-26 TB2 low-risk batch2 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for four more low-risk Terminal-Bench 2.1 rows: `schemelike-metacircular-eval`, `regex-chess`, `openssl-selfsigned-cert`, and `sqlite-db-truncate`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch2_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_check_20260626.json`; result counts `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `identity_mismatch=0`, `errors=0`.
- Worker direct P0 digest pull is still not a reliable readiness path for this rootless daemon: host `curl -k https://100.97.118.137:8555/v2/` succeeds and host route exists, but `docker pull` from `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` fails with `connect: network is unreachable`. Evidence: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_p0_pull_20260626.txt`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` after batch2 returned `fallback_tar_verified=57`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=34`.
- Issue comments posted after batch2: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803185564`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4803185784`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4803185981`.


## 2026-06-26 TB2 low-risk batch3 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for five more Terminal-Bench 2.1 rows: `rstan-to-pystan`, `raman-fitting`, `regex-log`, `sparql-university`, and `sqlite-with-gcov`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch3_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch3_worker_check_20260626.json`; result counts `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` now returns `fallback_tar_verified=62`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=29`; TB2-only `check --skip-docker` reports `tar_verified=60`, `tar_missing=0`, `tar_mismatch=0`.
- Issue comment posted after batch3: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803259395`.


## 2026-06-26 TB2 low-risk batch4 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for five more Terminal-Bench 2.1 rows: `password-recovery`, `path-tracing-reverse`, `query-optimize`, `sanitize-git-repo`, and `tune-mjcf`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch4_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch4_worker_check_20260626.json`; result counts `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` now returns `fallback_tar_verified=67`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=24`; TB2-only `check --skip-docker` reports `tar_verified=65`, `tar_missing=0`, `tar_mismatch=0`.
- Issue comment posted after batch4: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803343143`.


## 2026-06-26 TB2 low-risk batch5 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for five more Terminal-Bench 2.1 rows: `overfull-hbox`, `polyglot-c-py`, `polyglot-rust-c`, `winning-avg-corewars`, and `write-compressor`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch5_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch5_worker_check_20260626.json`; result counts `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` now returns `fallback_tar_verified=72`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=19`; TB2-only `check --skip-docker` reports `tar_verified=70`, `tar_missing=0`, `tar_mismatch=0`.
- Issue comment posted after batch5: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803463761`.
- P0 digest refs are recorded for these rows, but worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.


## 2026-06-26 TB2 service batch6 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for two service-isolated Terminal-Bench 2.1 rows: `nginx-request-logging` and `pypi-server`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_service_batch6_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_service_batch6_worker_check_20260626.json`; result counts `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` now returns `fallback_tar_verified=74`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=17`; TB2-only verified lint reports `fallback_tar_verified=72`, `required_without_offline_transport=17`.
- Issue comment posted after batch6: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803556773`.
- These rows are image-transport ready only. The `--network none` smoke is not a claim that the actual TB2 service behavior has been executed; real service behavior remains adapter/verifier scope. P0 digest refs are recorded, but worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.


## 2026-06-26 TB2 secret batch7 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for the secret/log-sensitive Terminal-Bench 2.1 row: `vulnerable-secret`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_secret_batch7_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`; result counts `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- Real TB2+SWE promotion gate with `--verify-fallback-files` now returns `fallback_tar_verified=75`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=16`; TB2-only verified lint reports `fallback_tar_verified=73`, `required_without_offline_transport=16`.
- Issue comment posted after batch7: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803651083`.
- This row is image-transport ready only. The `--network none` smoke is a generic image smoke that does not read task logs or verifier artifacts; real secret-task behavior remains adapter/verifier scope. P0 digest refs are recorded, but worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.

## 2026-06-26 TB2 medium batch8 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for two Terminal-Bench 2.1 medium-generic rows: `path-tracing` and `prove-plus-comm`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_medium_batch8_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch8_worker_check_20260626.json`; result counts `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- P0 digest refs recorded: `path-tracing@sha256:07659e59709c19d41fc10f2e824f2645736a3751733b72837733f088ab9724ba` and `prove-plus-comm@sha256:70b7a8e1e4ad02ac01dc434585c6167b936078680c0c6ae64084be096efc6748`.
- TB2-only static check now reports `tar_verified=75`, `tar_missing=0`, `tar_mismatch=0`; 14 generated TB2 cache rows still have `fallback_status: missing_shared_tar`.
- Full registry fallback lint with `--verify-fallback-files` reports `fallback_tar_verified=79`, `fallback_tar_missing=1` for the pre-existing RepoZero relative tar path, `fallback_tar_mismatch=0`, and `required_without_offline_transport=0`.
- GitHub issue #13 was filed from the runner-results Round18 bug-hunt: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13
- Issue comments posted after batch8: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803855715`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4803855848`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4803856045`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4803856254`.
- These rows are image-transport ready only. The `--network none` smoke is a generic image smoke that does not execute Terminal-Bench tasks or claim task success; worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.

## 2026-06-26 TB2 medium batch9 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for four Terminal-Bench 2.1 medium/data-ML rows: `portfolio-optimization`, `sam-cell-seg`, `train-fasttext`, and `video-processing`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_medium_batch9_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch9_worker_check_20260626.json`; result counts `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- P0 digest refs recorded: `portfolio-optimization@sha256:e49c81136737cfcddd8c31b2b6525cd0a42688a91808a1d425a7e103803e76c0`, `sam-cell-seg@sha256:9a84f14ac1bb630fc1d8d1eb0276e4c03432f4bb6735abd9789a369bafbbbab8`, `train-fasttext@sha256:0611d34b94140683d27a859e29e5567080d24d91646137531dae02e14cc4fbd9`, and `video-processing@sha256:dd6c7305b82e6cd9f99a2c862401b5648cd650abd414769bd51251fbf2c589e3`.
- TB2-only static check now reports `tar_verified=79`, `tar_missing=0`, `tar_mismatch=0`; 10 generated TB2 cache rows still have `fallback_status: missing_shared_tar`.
- Full registry fallback lint with `--verify-fallback-files` reports `fallback_tar_verified=83`, `fallback_tar_missing=1` for the pre-existing RepoZero relative tar path, `fallback_tar_mismatch=0`, and `required_without_offline_transport=0`.
- These rows are image-transport ready only. The `--network none` smoke is a generic image smoke that does not execute Terminal-Bench tasks or claim task success; worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.
