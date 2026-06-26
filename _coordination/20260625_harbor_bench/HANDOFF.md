# Harbor Bench Handoff

Updated: 2026-06-26 post-tau3-round30 oracle-direct smoke Asia/Shanghai

## Objective

Build the Harbor/P0-registry-backed bench runner path so a future worker can run all listed agentic benchmarks from one shell/YAML command, with offline image warmup/checks separated from actual benchmark adapter execution.

## Current Repo State

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch: `feat/image-warmup-policy`
- Current readiness-gate work is recorded in the active branch head; immediate pre-readiness head was `d6bafec Record proxy ceiling issue closure`.
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
- tau3-bench: full 375-task Harbor dataset generated; full Harbor/compose path still blocked on worker rootless compose, but a one-task `TAU3_AGENT=oracle_direct` helper now passes on worker-j9jjd via direct `docker run --network none` and is enabled only as an `image_smoke` suite helper. The full tau3 target remains disabled/pending adapter and must not be counted as ready. `tau2` is no longer an active bench target; keep only tau3, while preserving the upstream source checkout path where tau3 generation depends on it.
- Image inventory: `swe_dev` has substantially more SWE-bench/TB2.1 Docker images than worker; shared TB2.1 tars are partial, so worker full runs need staging from `swe_dev` cache. Current inventory artifacts: `_coordination/20260625_harbor_bench/inventory/swe_dev_data_inventory_20260626.md`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`, and identity-enriched `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`.
- Terminal-Bench 2.1: `terminal_bench_2_1_image_smoke` is enabled for image preflight using `gcode-to-text`; worker rootless check passes via cached/verified fallback image, while full TB execution remains pending adapter/runtime result wiring.
- Bug-hunt pair: only surface:50 and surface:54 produce `_coordination/20260625_harbor_bench/lanes/*.md`; each must cross-check the other's ledger before the orchestrator files issues.
- Current Round 21 completed: surface:50 audited the remaining 8 TB2 rows after batch10 and found no new ISSUE-READY bug. `mteb-retrieve` is the only staged-but-quarantined row: fallback tar exists and P0 HEAD returns 200, but worker fallback load failed, so it remains unpromoted. The other seven remaining rows have no fallback tar hit and P0 HEAD 404. Recommended next implementation order is `multi-source-data-merger` solo after storage/daemon-health checks, then the QEMU/service-like rows, then the giant torch/pytorch rows one by one. surface:54 audited batch10 provenance and the mteb failure, also found no new ISSUE-READY bug, and deduped it to #8/#12/#13/#10. Both hunt lanes stay ledger-only unless explicitly promoted by the orchestrator.
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

Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then this handoff. Run `cmux surface-health` and read surfaces 50 and 54 by content as the only continuous bug-hunt pair; read 51/55 only if they were explicitly assigned implementation review or smoke. Collect new `ISSUE-READY` blocks from `_coordination/20260625_harbor_bench/lanes/*.md`, cross-check the two ledgers, dedup against GitHub/open reports, file issue/comment if confirmed, and keep the two hunt agents busy. Continue main implementation from the active shared worktree. Next main step: keep `mteb-retrieve` and `multi-source-data-merger` quarantined and diagnose/retry only after a clean worker rootless daemon/storage-health proof; do not promote either row from tar/P0 staging evidence alone. After rootless storage is proven healthy, retry `multi-source-data-merger` first because its tar/P0 artifacts already exist; otherwise move only to smaller isolated QEMU/service-like rows if their worker ingest passes, and keep giant torch/pytorch rows one by one. Keep QEMU, torch/pytorch, largest data rows, and medium generic/data rows separated. SWE django10097 fallback transport is verified and worker-smoked, but P0 digest publication remains preferred for scale when worker rootless Docker can reach the registry. Run worker runtime `check`/smoke via explicit worker-j9jjd endpoint. Suite/model benchmark concurrency can be 40-50 on the 60-CPU worker when images are warm; image transport load/pull concurrency stays capped separately at 2-4.

## Acceptance Snapshot

- Warmup-policy red tests added and observed failing for missing checker flags, optional fatality, suite-relative project roots, and empty selected plans.
- Target tests pass: done; 5 focused tests pass.
- Full unittest/py_compile/diff-check: done; 22 unittest pass, py_compile rc 0, `git diff --check` rc 0.
- Dry-run with `manifests/suite.example.yaml --only repozero_py2js_smoke` resolves `project_root` to the active worktree and forwards `--load-fallback --run-smoke`.
- Old customer-service/tau2 suite entry removed per user direction; current no-adapter smoke examples and tau-family target use RepoZero/tau3 paths.
- Worker RepoZero image-preflight-only smoke: done through local control-plane SSH to worker with a temporary local-execution suite; output `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/verification/repozero_warmup_policy_20260626_001953`; summary status 0, required preflight pass, RepoZero image present, fallback tar sha256 match, container smoke passed.
- Worker DeepSWE optional image audit: `--fail-on-optional-missing` returns rc 1 with `optional_missing: 1`, closing the prior optional-image fake-green path.
- Direct `swe_dev -> worker` remains blocked by publickey; local Mac -> worker works.
- Local `worker` SSH alias was observed pointing at stale `worker-pshjt`; use the explicit `worker-j9jjd` endpoint from `WORKFLOW.md` until aliases are corrected.
- `swe_dev` `/data/swe/SWE-bench` and `/data/tmp/tb2-prebuild-save` are empty; the useful state is Docker local cache plus shared bench trees. swe_dev cache counts: 500 `swebench/sweb.eval...`, 728 `swerex-prebuilt`, 89 `tb2-offline`, 3 `sweb.*` helper images. Shared Terminal-Bench 2.1 has 50 `.tar` fallbacks plus 1 `.tar.gz`, so TB2 full image readiness is still partial relative to swe_dev cache.
- Generated image manifests now include `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` (89 TB2 rows from swe_dev cache, 81 with verified fallback/P0 transport; 8 still marked `missing_shared_tar`) and `manifests/images/swebench_verified_django10097.yaml` (official eval base + swerex wrapper identity probe). SWE django10097 now has verified fallback tar sha for both rows; worker-j9jjd `--load-fallback --run-smoke` loaded the official eval base over the prior wrapper alias mismatch and ended with `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, `identity_mismatch=0`.
- Static image manifest lint is available via `python3 scripts/agentic_bench_images.py lint --require-offline-transport`; current TB2 generated cache status is 81 configured fallback tars verified by `check --skip-docker`, with 8 rows still marked `fallback_status: missing_shared_tar` by manifest audit.
- Registry-selected lint validation after batch10: `validate` rc 0 with `manifests=9/images=104/required_images=94`; full `lint-registry --verify-fallback-files` over all registered manifests reports `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=8`. The remaining lint issue is the TB2 generated cache manifest's 8 rows still marked `missing_shared_tar`, not missing tar files for promoted rows.
- Latest full verification after batch10: `python3 -m unittest scripts.test_agentic_bench_images scripts.test_agentic_bench_suite scripts.test_offline_images_manifest` passed 36 tests; `validate`, `git diff --check`, TB2 static fallback check, worker fallback smoke, and bounded secret scan passed. Full registry fallback lint currently reports `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=8` because the generated TB2 cache still has 8 unpromoted rows.
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
- Initial TB2+SWE promotion gate with `--verify-fallback-files` returned `fallback_tar_verified=53`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=38`; latest batch10 evidence below updates TB2-only check to `tar_verified=81` and leaves 8 TB2 rows marked `missing_shared_tar`.

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
- Issue comments posted after batch9: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4803993289`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4803993442`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4803993607`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4803993748`.
- These rows are image-transport ready only. The `--network none` smoke is a generic image smoke that does not execute Terminal-Bench tasks or claim task success; worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.

## 2026-06-26 TB2 medium batch10 P0/fallback evidence

- Added P0 digest plus verified fallback tar transport for two Terminal-Bench 2.1 medium/data-ML rows: `reshard-c4-data` and `pytorch-model-cli`.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_medium_batch10_20260626.tsv`.
- Worker fallback-load/run-smoke evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch10_worker_check_20260626.json`; result counts `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- P0 digest refs recorded: `reshard-c4-data@sha256:4ab395e621f6fbd1ecf4433ea20f5ad8a7d3d3be989bb14ef4c049428a7eaa59` and `pytorch-model-cli@sha256:708e27b09487fbfed9176182bbad343ce2c15fba3294dad910a98726851f1aec`.
- `mteb-retrieve` was exported to fallback tar and pushed to P0 (`@sha256:088c20baec521e159982c27bcdb8a48dda67a15729043a92a86ef27a6472c0a8`) but was not promoted in the manifest because worker-j9jjd `docker load` failed twice with `unlinkat /usr/local/lib/python3.10/site-packages/pip-23.0.1.dist-info: input/output error`.
- TB2-only static check now reports `tar_verified=81`, `tar_missing=0`, `tar_mismatch=0`; 8 generated TB2 cache rows still have `fallback_status: missing_shared_tar`.
- Full registry fallback lint with `--verify-fallback-files` reports `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=8`; the 8 remaining gaps are the unpromoted TB2 generated cache rows listed above.
- These rows are image-transport ready only. The `--network none` smoke is a generic image smoke that does not execute Terminal-Bench tasks or claim task success; worker-j9jjd readiness remains fallback-tar based until #8 re-proves direct rootless registry pulls.
- Issue comments posted after batch10: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4804338762`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4804338936`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4804339072`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4804339204`.


## 2026-06-26 Round21 bug-hunt and tau3-only scope

- Commit `e4c98e6` drops `tau2` as an active bench target: the standalone tau2 smoke report was deleted, reports/manifests now point the tau-family work at `tau3-bench`, and the no-active-tau2 regression test remains as a guard. Remaining `tau2-bench` strings are upstream source checkout/URL references used by tau3 generation or historical layout/test guards.
- Round21 runtime-images ledger: `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` now classifies the final 8 TB2 gaps. `mteb-retrieve` is staged but quarantined; `multi-source-data-merger` is the next solo materialization candidate; QEMU/service-like rows and giant torch/pytorch rows stay isolated. No new ISSUE-READY block.
- Round21 runner-results ledger: `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` now records batch10 image-check provenance and the mteb worker-load failure as COMMENT-READY evidence for existing #8/#12/#13/#10, not a new runner/results issue.
- Round21 agents started from head `250f017`; orchestrator advanced the branch to `e4c98e6` during their run for tau2 de-scope. Their ledger head references are therefore start-context evidence, while this handoff records the current branch head.
- Issue comments posted after Round21: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4804434397`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4804434506`, #10 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/10#issuecomment-4804434618`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4804434724`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4804434827`.


## 2026-06-26 TB2 batch11 multi-source quarantine evidence

- Exported and pushed `multi-source-data-merger` from `swe_dev` cache, but did not promote it in the active TB2 manifest because worker-j9jjd could not ingest the image through either fallback tar or P0 digest pull.
- Evidence TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_multisource_batch11_20260626.tsv`.
- Source image: `tb2-offline/multi-source-data-merger:20260425`, source image id `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83`.
- Fallback tar staged at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/multi-source-data-merger.tar`, sha256 `502a8078ee247e5813161e13c03d4e9c69c08da7d685d5a02b0f544f599f1ea7`.
- P0 digest ref staged as `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-multi-source-data-merger@sha256:33d33940e4e6207900e23fb0f4232f8607be2357d4d07062a1b3c4088dc927c2`.
- Worker fallback-load evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_multisource_batch11_worker_fallback_load_failed_20260626.json`; counts `tar_verified=1`, `loaded=0`, `present=0`, `smoke_passed=0`, `missing=1`, with `load_stderr` `unlinkat /openhands/micromamba/pkgs/cache: input/output error`.
- Worker P0 pull evidence JSON: `_coordination/20260625_harbor_bench/inventory/tb2_multisource_batch11_worker_p0_pull_failed_20260626.json`; counts `tar_verified=1`, `pulled=0`, `present=0`, `smoke_passed=0`, `missing=1`, with `pull_stderr` `failed to register layer: unlinkat /openhands/micromamba/pkgs/cache: input/output error`.
- Active generated TB2 manifest remains at the batch10 readiness level: `multi-source-data-merger` is not counted as worker-ready; current TB2 static gate remains `tar_verified=81`, `required_without_offline_transport=8` until a clean worker rootless storage-health proof and successful ingest/smoke.
- Issue comments posted after batch11 quarantine: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4804623796`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4804624024`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4804624178`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4804624308`.


## 2026-06-26 Round22 rootless storage probe and bug-hunt ledgers

- Commit `32e4f89` adds read-only storage diagnostics and optional cached-image `--network none` smoke to `scripts/check_rootless_docker_worker.sh` via `HEALTH_SMOKE_IMAGE`.
- Real worker probe from the local control plane with `HEALTH_SMOKE_IMAGE=tb2-offline/pytorch-model-cli:20260425` returned overall rc 1 because known #8 `/version`/SDK checks still fail, but the new storage/runtime separators reported `docker_storage_info_rc=0`, `docker_system_df_rc=0`, and `cached_run_smoke_rc=0`.
- Commit `19f00f9` records Round22 bug-hunt ledgers for runtime-images and runner-results. Both lanes found no new ISSUE-READY root cause; both dedup batch11 against #6/#8/#12/#13 and keep `mteb-retrieve` plus `multi-source-data-merger` quarantined until worker rootless layer ingest is proven healthy.
- Runtime evidence now separates cached-image run health from new-layer ingest failure: worker can run an existing TB2 image with `--network none`, while batch11 fresh fallback-load and P0-pull both fail during layer registration with `unlinkat ... input/output error`.
- Issue comments posted after Round22: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4804709166`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4804709315`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4804709470`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4804709619`.


## 2026-06-26 remote cache inventory and TB2 missing-transport staging plan

- Added controller-side cache discovery support to `scripts/agentic_bench_images.py`: `inventory-remote-cache`, `match-inventory`, and `plan-stage-missing-transport`.
- Added `scripts/stage_cache_images_from_plan.sh`, a dry-run-first staging helper. It reads the generated TSV and only performs `docker image inspect`/`docker save` when `--execute` is passed; `--push` is separate and was not used in this round.
- Direct `dev -> swe_dev/swe_dev2` SSH by alias failed (`Could not resolve hostname`); direct `dev -> full endpoint` failed with publickey/maintenance messages. The successful source inventory route was local Mac control plane -> full `swe_dev`/`swe_dev2` endpoints, writing shared artifacts.
- Remote cache inventory artifacts:
  - `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json`: `images=591` for prefixes `tb2-offline/`, `swebench/`, `ghcr.io/jessezzzzz/`, and `sweb.eval`.
  - `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev2.docker_cache_inventory.json`: `images=1`, currently only `tb2-offline/gcode-to-text:20260425` for those prefixes.
- Manifest/cache match artifacts:
  - `tb2_swe_dev_cache_match.json`: TB2 generated cache manifest matched `89/89` required rows against source inventories; `required_missing=0`.
  - `swebench_verified_cache_match.json`: current narrow SWE-bench Verified image manifest matched `1/2` optional rows against source inventories.
- TB2 missing offline transport staging plan:
  - Plan TSV: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.tsv`.
  - Plan JSON: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.json`.
  - The plan has 8 rows and all are matched from `swe_dev`: `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `torch-pipeline-parallelism`, and `torch-tensor-parallelism`.
- Dry-run staging on `swe_dev` parsed all 8 rows and wrote `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_dryrun_result.tsv`; no Docker operations were run in dry-run.
- Real staging smoke executed only `install-windows-3.11` on `swe_dev`, with `--execute` and no `--push`. It saved `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/install-windows-3.11.tar`, sha256 `eabcacaa81ada0061dc6b08c825a74287cb83da38c0a4cdf91a802edb5510c54`, permission `0644`, and result TSV `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_install_windows_result.tsv`.
- No active TB2 manifest row was promoted from this new staging evidence. Worker-j9jjd new-layer ingest remains under #8 quarantine; `mteb-retrieve` and `multi-source-data-merger` stay unpromoted until a clean worker ingest proof exists.

- Issue comments posted for remote cache staging workflow: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4804915658`, #8 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4804915768`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4804915896`, #13 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4804916055`.

## 2026-06-26 staging source-host and image-identity guard

- Implemented the Round24 remote-cache staging provenance fix in `scripts/stage_cache_images_from_plan.sh` and `scripts/agentic_bench_images.py`.
- `match_manifest_inventory()` now reports `identity_mismatch` instead of `matched` when a manifest row has expected image identity and an identity-inspected inventory row has the same ref but a different full image ID or repo digest. Real TB2 `swe_dev` inventory still matches `89/89` with `identity_mismatch=0`.
- `stage_cache_images_from_plan.sh --execute` now parses `docker image inspect` before `docker save` and fails before writing a tar if the actual image `Id` differs from the plan `source_image_id`.
- Staging now accepts `--source-host-label`; selected rows fail with `source_host_mismatch` before Docker access when the plan `source_host` differs from the operator-provided label.
- Stage result TSVs now include `source_host`, `source_ref`, `source_cache_image_id`, `source_size`, and `actual_image_id` so saved/dry-run/mismatch rows keep source provenance.
- New dry-run evidence using the guard-aware output schema: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_install_windows_identity_guard_dryrun_result.tsv`.
- The prior `install-windows-3.11` saved tar remains source-staged only and was not re-promoted or re-saved in this guard fix. It still needs worker fallback-load/run-smoke evidence before active manifest promotion.
- Verification after the fix: `python3 -m unittest scripts.test_agentic_bench_suite scripts.test_agentic_bench_images scripts.test_offline_images_manifest` passed 46 tests; `bash -n` for shell helpers passed; `git diff --check` passed; guard dry-run emitted aligned provenance columns.
- Source-cache audit report: `_coordination/20260625_harbor_bench/lanes/source-cache-audit-round25.md`. It confirms `swe_dev:/data/docker` is the main source cache, with `tb2-offline=89`, `swebench/sweb.eval=500`, and `swerex-prebuilt=728`; combined shared/agentic TB2 tar presence is about `84/89`, but only `81` TB2 rows remain active-promotion verified because staged/quarantined tar presence is not enough for worker readiness.
- Runner concurrency report: `_coordination/20260625_harbor_bench/lanes/runner-concurrency-relay-round25.md`. It confirms current suite dry-run default `suite_concurrency=40`, image preflight concurrency `4`, and records a new ISSUE-READY gap that `proxy_concurrency_ceiling` is not enforced when `--max-concurrency` is raised above 50.
- GitHub issue/comment updates after `c3d267b`: new #14 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/14`; #6 comment `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4805019649`; #11 comment `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/11#issuecomment-4805019721`; #12 comment `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4805019803`; #13 comment `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/13#issuecomment-4805019887`.

## 2026-06-26 relay concurrency ceiling enforcement

- Implemented #14 in `scripts/agentic_bench_suite.py`: `suite.proxy_concurrency_ceiling` is now parsed into the plan as `proxy_concurrency_ceiling`, printed in human dry-runs, and enforced against the final `suite_concurrency` after CLI `--max-concurrency` override.
- Real suite example check: default dry-run now emits `suite_concurrency=40`, `proxy_concurrency_ceiling=50`, and `image_preflight_concurrency=4`; `--max-concurrency 50` passes; `--max-concurrency 80` returns rc 2 with `suite_concurrency 80 exceeds suite.proxy_concurrency_ceiling 50`.
- Regression tests added: `test_plan_emits_proxy_concurrency_ceiling` and `test_cli_rejects_max_concurrency_above_proxy_ceiling`.
- Verification: full unit suite passed 48 tests; shell syntax checks and `git diff --check` passed.
- #14 fixed/closed comment: `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/14#issuecomment-4805037855`.


## 2026-06-26 all-bench readiness gate and RepoZero worker proof

- Added suite-level static readiness gate in `scripts/agentic_bench_suite.py`: `--readiness` emits `agentic_bench.readiness_report.v1` and exits nonzero when any selected target is `blocked` or `missing`. It does not call models, Docker, or benchmark adapters.
- Default readiness target set now covers the user-requested bench list: SWE-bench Verified multi, Terminal Bench 2.1, MCP-Atlas, Tool-Decathlon, tau3-bench, programbench, RepoZero, NL2Repo, and DeepSWE. Subsets can be selected with `--target-benches`.
- Tracked readiness artifact: `_coordination/20260625_harbor_bench/readiness_20260626.json`. Current counts are `ready=1`, `blocked=8`, `missing=0`, `total=9`.
- Current ready target: RepoZero. `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --readiness --target-benches RepoZero` returns ready.
- Current blocked targets and dominant blockers:
  - SWE-bench Verified multi: image manifest is still not materialized for full multi-agent coverage.
  - Terminal Bench 2.1: full adapter is disabled/pending and the 89-row cache manifest still has `required_image_transport_missing` for 5 rows.
  - MCP-Atlas, Tool-Decathlon, programbench, NL2Repo: disabled/pending adapters and placeholder image contracts.
  - tau3-bench: offline runtime images and the oracle-direct helper are ready, but the full benchmark remains disabled/pending adapter and rootless/offline hardening; tau2 remains de-scoped.
  - DeepSWE: adapter smoke is wired, but the image manifest is still a placeholder without R2E/Pier runtime enumeration.
- GitHub issue #15 tracks the stale TB2 cache metadata bug and was closed after `c95d420`: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/15; close comment https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/15#issuecomment-4805168157
- Terminal-Bench 2.1 full suite entry now points at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` rather than the old one-task smoke manifest. The cache manifest metadata now records `cache_image_count=89`, `shared_tar_count=84`, `offline_transport_ready_count=84`, and `remaining_transport_gap_count=5`; only the 84 promoted/worker-proven rows are treated as offline-transport ready.
- Worker-j9jjd RepoZero proof: using a temporary local-execution suite on worker with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, RepoZero readiness returned ready and `--image-preflight-only --only repozero_py2js_smoke` passed. Output: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/verification/repozero_readiness_gate_20260626_rerun`; summary `status=0`, counts `pass=1`, `fail=0`, `optional_fail=0`.
- Round26 bug-hunt ledgers:
  - `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`: #14 proxy ceiling enforcement re-review found no new ISSUE-READY bug.
  - `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: source-cache staging guard re-review found no new independent ISSUE-READY bug; ref-only inventory identity uncertainty is deduped to existing staging/provenance issues.
- Verification for this round: full relevant unittest suite passed 52 tests; `python3 -m py_compile` for Python helpers passed; `bash -n` for shell helpers passed; `git diff --check` passed; worker RepoZero image preflight passed.

## 2026-06-26 Round27 readiness fixes and tau3 smoke image proof

- GitHub issues opened from Round27 bug-hunt:
  - #16 `Readiness target aggregation can mark full Terminal-Bench 2.1 ready from image smoke entry`: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/16
  - #17 `Readiness mode bypasses proxy concurrency ceiling validation for --max-concurrency`: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/17
- #16 fixed/closed comment: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/16#issuecomment-4805335913
- #17 fixed/closed comment: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/17#issuecomment-4805338604
- Implemented #16 by adding readiness roles to suite entries. Entries default to `readiness_role: full`; helper entries with ids/adapters ending in `_image_smoke` default to `image_smoke`. Target status aggregation now uses full-role entries, so a helper image-smoke entry can no longer make the full Terminal-Bench 2.1 target ready while the full entry remains blocked.
- Implemented #17 by factoring suite concurrency/proxy-ceiling validation into a shared helper and running it before `--readiness` emits a report. `--readiness --target-benches RepoZero --max-concurrency 51` now returns rc 2 with `suite_concurrency 51 exceeds suite.proxy_concurrency_ceiling 50`.
- Added regression tests for both bugs: readiness rejects over-ceiling concurrency and a ready `terminal_bench_2_1_image_smoke` helper does not satisfy the full `Terminal Bench 2.1` target.
- Materialized tau3 smoke images from the Harbor smoke task source into P0 registry and shared tars:
  - `tau3-smoke-main:20260626r2`, P0 digest `100.97.118.137:8555/swe-data-harness/tau3-smoke-main@sha256:571aa921fc1eda999b9fc124a266900c6b10a4aceba9283e6f9867f9a44788e4`, fallback tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke-main_20260626r2.tar`, sha256 `cfb1207cf33fa152ee99b01b10b7ff229bb2cdcb847a39d0fc47771f891f2b64`.
  - `tau3-smoke-runtime:20260626r2`, P0 digest `100.97.118.137:8555/swe-data-harness/tau3-smoke-runtime@sha256:290a4f09c7ade3a1e7a08dfd3d4c6d0951b4ae519eae12d2fe1ccb99745dc699`, fallback tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_smoke_image_20260626/tau3-smoke-runtime_20260626r2.tar`, sha256 `2503e032377986ffef80b935035e279a52e1a13807a6fa1e7fb65d6033615d85`.
- tau3 r1 images were rejected as worker-ready because the build upgraded pip and worker rootless layer registration failed with `unlinkat /usr/local/lib/python3.12/site-packages/pip-25.0.1.dist-info: input/output error`. r2 removes the pip upgrade layer and successfully pulls/runs on worker-j9jjd.
- Worker-j9jjd proof used `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45` because the current rootless daemon panics on the Docker CLI `/version` endpoint. P0 digest pull and `--network none` smoke passed for both r2 images: `worker-tau3-main-r2-ok` and `worker-tau3-runtime-r2-ok`.
- `manifests/images/tau3_bench.yaml` now has two required image rows, both with P0 digest refs and verified shared fallback tar sha256. Static image check reports `tar_verified=2`, `tar_missing=0`, `tar_mismatch=0`; worker-side old manifest checker reports `present=2`, `missing=0`, `errors=0`.
- `manifests/suite.example.yaml` now marks tau3 as `pending_adapter` rather than `pending_offline_image`. Readiness for tau3 is still blocked, but only by `suite_entry_disabled` / `adapter_not_wired`; the tau3 image manifest itself is ready with `required_images=2`, `required_without_offline_transport=0`.
- Refreshed `_coordination/20260625_harbor_bench/readiness_20260626.json`. Overall counts remain `ready=1`, `blocked=8`, `missing=0`, `total=9`; the tau3 target blocker changed from image transport pending to adapter wiring pending.
- `/data` source-cache note from this round: `swe_dev` local Docker has `tb2-offline/*=89`, Terminal-Bench 2.1 P0-tagged rows visible locally at `33`, SWE eval images around `501`, and `swerex-prebuilt=728`. This confirms Terminal-Bench 2.1 full source images exist on `swe_dev:/data/docker`; the remaining work is safe staging/promotion under the worker rootless ingest constraints.
- Verification after this round: full unit suite passed `54 tests`; Python py_compile passed; shell `bash -n` passed for launcher/image helper scripts; `git diff --check` passed; tau3 `agentic_bench_images.py --skip-docker` verified both r2 fallback tars; worker-j9jjd P0 pull and `--network none` smoke passed for both tau3 r2 images.


## 2026-06-26 Round28 worker image preflight API env fix

- GitHub issue opened from Round28 runner-results bug-hunt:
  - #18 `Image preflight drops worker DOCKER_API_VERSION for rootless worker`: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/18
- #18 fixed in commit `4a12b0a` and closed with comment: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/18#issuecomment-4805425029
- Implemented #18 by adding worker `DOCKER_API_VERSION: "1.45"` to `manifests/suite.example.yaml`, exporting redacted worker env before every generated image-preflight checker command, and recording that env under `image_preflight.environment` and each preflight command entry.
- `scripts/check_rootless_docker_worker.sh` now passes `REMOTE_DOCKER_API_VERSION` into the worker and prints `docker_api_version=$DOCKER_API_VERSION`. The known rootless `/v1.45/version` panic/EOF path is retained as a diagnostic (`known_rootless_version_endpoint_unstable`) but no longer makes health fail when operational checks pass.
- Worker-j9jjd health proof through the local control plane returned rc 0 with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, `docker_info_rc=0`, `docker_ps_rc=0`, `docker_images_rc=0`, `compose_version_rc=0`, and diagnostic-only failures for `docker version`, raw `/v1.45/version`, and Python Docker SDK version negotiation.
- Worker-j9jjd tau3 image-preflight proof returned rc 0 with `present=2`, `tar_verified=2`, `missing=0`, `errors=0` for `manifests/images/tau3_bench.yaml` using `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`.
- Dry-run plan proof for `terminal_bench_2_1_image_smoke` returned one run with `image_preflight.environment.DOCKER_API_VERSION=1.45`, and the rendered command contains both `export DOCKER_API_VERSION=1.45` and `export DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
- Verification after this round: full unit suite passed `57 tests`; Python py_compile passed; shell `bash -n` passed for launcher/image helper scripts; `git diff --check` passed; worker health script returned rc 0; worker tau3 image checker returned rc 0.


## 2026-06-26 TB2 install-windows promotion and digest retag fix

- GitHub issue opened from the install-windows worker proof:
  - #19 `Image checker digest pull leaves required local_ref tag absent`: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/19
- #19 fixed in commit `dacdef9` and closed with comment: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/19#issuecomment-4805492390
- Implemented #19 by teaching `scripts/agentic_bench_images.py check` to tag a successfully pulled internal digest ref to the first configured `local_ref`, then inspect that local ref and record `local_tag_status`, `local_tag_ref`, `local_tag_source_ref`, and count `tagged` in the image-check summary.
- Staged and pushed Terminal-Bench 2.1 `install-windows-3.11` from `swe_dev` using `scripts/stage_cache_images_from_plan.sh --execute --push --only install-windows-3.11`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_install_windows_p0_push_20260626.tsv`.
- P0 digest: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-install-windows-3.11@sha256:5dcb2476f1597ebc81da54ad010e9dddf5cc5bb2670f225c7be36e8b50ec4265`.
- Shared fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/install-windows-3.11.tar`, sha256 `3c34b88a6c7382e86bed72c517567e1bcc8038e07237f61da5bacc1103fc70b6` after the final save/push pass.
- Worker-j9jjd proof used `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45` with one-row manifest `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_install_windows_worker_check_manifest_20260626.yaml`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_install_windows_worker_check_20260626.json`.
- Worker check returned rc 0 with counts `present=1`, `pulled=1`, `tagged=1`, `smoke_passed=1`, `tar_verified=1`, `missing=0`, `errors=0`; `present_ref` is now the local tag `tb2-offline/install-windows-3.11:20260425`.
- Active TB2 cache manifest now records install-windows as `p0_digest_plus_fallback_tar`. TB2 offline transport readiness moved from `81/89` to `82/89`, with `remaining_transport_gap_count=7`.
- Verification after this promotion: full unit suite passed `58 tests`; Python py_compile passed; shell `bash -n` passed for launcher/image helper scripts; `git diff --check` passed; worker local `docker image inspect tb2-offline/install-windows-3.11:20260425` returns image id `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b`.

## 2026-06-26 TB2 mteb-retrieve worker retry quarantine

- Retried the quarantined Terminal-Bench 2.1 `mteb-retrieve` row on worker-j9jjd with a one-row manifest instead of promoting it from source/P0 evidence.
- Retry manifest: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_manifest_20260626.yaml`.
- Worker retry result: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_20260626.json`; rc file `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_20260626.rc`; stderr file `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_20260626.stderr`.
- Host-vs-daemon diagnostics: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_diagnostics_20260626.txt`.
- Static one-row lint with `--require-offline-transport --verify-fallback-files` passed: `required_images=1`, `required_with_digest_ref=1`, `fallback_tar_verified=1`, `required_without_offline_transport=0`.
- P0 digest ref retried: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-mteb-retrieve@sha256:088c20baec521e159982c27bcdb8a48dda67a15729043a92a86ef27a6472c0a8`.
- Fallback tar retried: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/mteb-retrieve.tar`, sha256 `f80be41fc1360f33926c4ceaf572eff8963455f7bf44d3544454d4c6fb3eda2d`.
- Worker check returned rc 1 with counts `tar_verified=1`, `pulled=0`, `loaded=0`, `present=0`, `smoke_passed=0`, `missing=1`, `errors=0`.
- Pull failed inside the rootless Docker daemon with `connect: network is unreachable` to P0, even though worker host `curl -k -I https://100.97.118.137:8555/v2/` returned HTTP 200 and `ip route get 100.97.118.137` succeeded.
- Fallback tar load failed with `unlinkat /usr/local/lib/python3.10/site-packages/pip-23.0.1.dist-info: input/output error`.
- Docker inspect after the retry confirmed neither the P0 digest ref nor `tb2-offline/mteb-retrieve:20260425` is present locally.
- Conclusion at retry time: do not promote `mteb-retrieve`; keep it under #8 rootless Docker network/ingest quarantine. At that point active Terminal-Bench 2.1 remained `82/89` offline-transport ready with `7` remaining gaps; later qemu proofs below supersede the current active count to `84/89` with `5` remaining gaps.
- #8 comment posted with this evidence: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4805539733
- Round29 runner-results bug hunt found no new ISSUE-READY bug after #18/#19 and install-windows promotion; it recommends parsing allowlisted checker JSON into image-preflight summaries as a #12/#13 follow-up, not as a new issue.

## 2026-06-26 TB2 qemu-alpine fallback/P0 worker proof

- Staged and pushed Terminal-Bench 2.1 `qemu-alpine-ssh` from `swe_dev` using `scripts/stage_cache_images_from_plan.sh --execute --push --only qemu-alpine-ssh`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_stage_20260626.tsv`; log artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_stage_20260626.log`; rc artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_stage_20260626.rc`.
- P0 digest: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-qemu-alpine-ssh@sha256:df4efa529fc2ad4d5c312723c14c4fa9b275ba83bee451046d6d966df19aff54`.
- Shared fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/qemu-alpine-ssh.tar`, sha256 `583a166245327f970231ce00cc3f3308a3d0c4466113a2e0a9e70b7b8127d435`.
- Worker-j9jjd proof used explicit endpoint from `WORKFLOW.md`, `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, and `DOCKER_API_VERSION=1.45` with one-row manifest `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_manifest_20260626.yaml`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_20260626.json`; rc artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_20260626.rc`; stderr artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_20260626.stderr`.
- Worker check returned rc 0 with counts `present=1`, `tar_verified=1`, `loaded=1`, `smoke_passed=1`, `pulled=0`, `missing=0`, `errors=0`, and `identity_mismatch=0`; `present_ref` is the local tag `tb2-offline/qemu-alpine-ssh:20260425`. This is a fallback-load proof, not a worker direct-P0 pull proof.
- Active TB2 cache manifest now records `qemu-alpine-ssh` as `p0_digest_plus_fallback_tar`. TB2 offline transport readiness moved from `82/89` to `83/89`, with `remaining_transport_gap_count=6` at this point. The later qemu-startup proof below supersedes the current active count to `84/89` with `5` remaining gaps.
- Rootless worker direct-P0 behavior remains under #8; do not remove fallback tar requirements from promoted TB2 rows until digest-pull consumer smoke is reliable on worker.


## 2026-06-26 TB2 qemu-startup fallback/P0 worker proof

- Staged and pushed Terminal-Bench 2.1 `qemu-startup` from `swe_dev` using `scripts/stage_cache_images_from_plan.sh --execute --push --only qemu-startup`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_stage_20260626.tsv`; log artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_stage_20260626.log`; rc artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_stage_20260626.rc`.
- P0 digest: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-qemu-startup@sha256:87e1d470d7259159dee9961f0ff2d496472fc0a55d56df9abd997c34721d16a3`.
- Shared fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/qemu-startup.tar`, sha256 `9dfff44089db02e89f770f29f0581db2ebf497ae05dc6b4a30f4b7b8e9083883`.
- Worker-j9jjd proof used explicit endpoint from `WORKFLOW.md`, `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, and `DOCKER_API_VERSION=1.45` with one-row manifest `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_manifest_20260626.yaml`. Result artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_20260626.json`; rc artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_20260626.rc`; stderr artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_20260626.stderr`.
- Worker check returned rc 0 with counts `present=1`, `tar_verified=1`, `loaded=1`, `smoke_passed=1`, `pulled=0`, `missing=0`, `errors=0`, and `identity_mismatch=0`; `present_ref` is the local tag `tb2-offline/qemu-startup:20260425`. This is a fallback-load proof, not a worker direct-P0 pull proof.
- Active TB2 cache manifest now records `qemu-startup` as `p0_digest_plus_fallback_tar`. TB2 offline transport readiness moved from `83/89` to `84/89`, with `remaining_transport_gap_count=5`. Remaining transport gaps are `tb2_mteb_retrieve`, `tb2_multi_source_data_merger`, `tb2_pytorch_model_recovery`, `tb2_torch_pipeline_parallelism`, and `tb2_torch_tensor_parallelism`.
- Rootless worker direct-P0 behavior remains under #8; do not remove fallback tar requirements from promoted TB2 rows until digest-pull consumer smoke is reliable on worker.

## 2026-06-26 tau3 Round29 runner contract and worker blocker

- Added a tau3 adapter evidence report: `_coordination/20260625_harbor_bench/lanes/tau3-adapter-round29.md`.
- Modified the shared runner `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh` outside this git repo. Backup before the change: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29/run_tau3_bench.before_round29.sh`.
- Shared runner current sha256: `469470ffddb2c9753707e80b1194e37680c20477fa72774ee64a85b1f71284a6`; pre-Round29 backup sha256: `db5a9559234c24cde85c0c01582ef6ac9ac5331538422115e8cc249a1689c646`.
- Runner now supports `TAU3_AGENT=oracle`, `HARBOR_BIN`, no-model/no-OpenAI-env dry-run command generation, and post-Harbor `result.json` parsing so Harbor exceptions make the wrapper return nonzero.
- Patched a copied one-task smoke dataset at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round29/dataset/tau3-airline-0`; no full dataset/template mutation was made.
- Worker image inspect passed for both tau3 r2 digest refs and worker runner dry-run passed with direct `harbor run -a oracle --no-force-build` and no model/OpenAI parameters.
- Real worker Harbor oracle smoke did not pass: rootless Docker compose failed creating the default network with `operation not permitted`. After the runner parser fix, the same failure returns wrapper rc 1 and writes `tau3_result_summary.json` with `status=errors`, `n_total_trials=1`, `n_errors=1`, `successful_eval_trials=0`.
- Additional worker probes: `docker network create` is not permitted, `docker run --network host` is not permitted, `docker run --network none` succeeds, and a minimal compose `network_mode: none` probe still hit the known Docker compose `/v1.45/version` EOF instability.
- Oracle mode still triggered a LiteLLM remote model-cost-map warning before local fallback, so Harbor needs an explicit offline/no-public-egress setting before any worker run is called offline clean.
- Conclusion: tau3 remains image-ready and runner-contract-ready for oracle dry-run, but not adapter-smoke-ready. Keep `manifests/suite.example.yaml` tau3 disabled with `adapter_status: pending_adapter` until compose/offline blockers are cleared and a one-task oracle result passes.
- #8 rootless worker comment posted: https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/8#issuecomment-4805622535

## 2026-06-26 tau3 Round30 oracle-direct worker smoke

- Added tau3 adapter evidence report: `_coordination/20260625_harbor_bench/lanes/tau3-adapter-round30.md`.
- Modified the shared runner `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh` outside this git repo again. Current runner sha256 after Round30 direct mode: `4424b70928dda8ca43d613c0a28020e822e05f9b71a53f8acec44a1eeef9c012`.
- Runner now supports `TAU3_AGENT=oracle_direct` for exactly one task. It bypasses Harbor/compose and writes a direct `docker run --rm --network none` command against `tau3-smoke-main:20260626r2`, mounting copied `/solution`, `/tests`, and log/artifact dirs.
- Stable one-task dataset copied to `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/tau3-bench-oracle-direct-smoke`.
- Worker direct oracle proof passed with `direct_rc=0`, verifier `status=passed`, and `reward=1.0`. Artifact: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round30/direct_oracle_run_20260626.txt`.
- Suite-generated command proof passed from the Mac control plane through the explicit worker-j9jjd SSH path. Result summary: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/tau3_bench_oracle_direct_smoke/tau3_result_summary.json`, schema `agentic_bench.tau3_direct_result_summary.v1`, `status=passed`, `verifier_status=passed`, `direct_rc=0`, `reward=1.0`.
- Added enabled helper entry `tau3_bench_oracle_direct_smoke` in `manifests/suite.example.yaml` with `readiness_role: image_smoke`, `adapter_status: wired_legacy`, `TAU3_AGENT=oracle_direct`, `TAU3_GENERATE_DATASET=0`, and `TAU3_DATASET_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/tau3-bench-oracle-direct-smoke`.
- Added regression coverage ensuring the helper is ready but excluded from full tau3 aggregation. Full tau3 still has `aggregation_entry_count=1`, `adapter_status=pending_adapter`, and target status `blocked`.
- Follow-up identity hardening adds `source_image_id` for both tau3 r2 rows in `manifests/images/tau3_bench.yaml`, so image preflight can reject local tag drift before the direct helper executes.
- Follow-up sidecar preflight split fixes #20 by adding `manifests/images/tau3_oracle_direct_smoke.yaml` and pointing `tau3_bench_oracle_direct_smoke` to it, so the direct no-sidecar helper requires only the main task image while full tau3 keeps the two-image manifest.
- Rootless compose remains blocked: a layered `network_mode: none` compose probe and API-version sweep over `1.45`, `1.44`, `1.43`, `1.41`, and unset all failed during compose up at the Docker `/version` EOF path. Artifact: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/artifacts/tau3_adapter_smoke_20260626_round30/compose_api_version_probe_20260626.txt`.
- Offline-clean caveat remains: the direct run uses `--network none` so public egress fails, but tau2/LiteLLM import still attempts the remote model-cost-map fetch before falling back locally. Keep this as an offline-hardening follow-up before calling tau3 fully offline-clean.
- Conclusion: tau3 has one worker-passing oracle-direct smoke helper, not full Harbor adapter readiness. Keep the full tau3 suite entry disabled/pending adapter until Harbor/compose or a proper non-compose adapter path is implemented for all intended tasks.
