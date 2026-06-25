# Harbor Bench Handoff

Updated: 2026-06-26 post-round21-tau3-only Asia/Shanghai

## Objective

Build the Harbor/P0-registry-backed bench runner path so a future worker can run all listed agentic benchmarks from one shell/YAML command, with offline image warmup/checks separated from actual benchmark adapter execution.

## Current Repo State

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch: `feat/image-warmup-policy`
- Latest implementation/coordination head: `e4c98e6 Drop tau2 as active bench target`; Round21 ledger commits follow as coordination-only updates.
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
- tau3-bench: full 375-task Harbor dataset generated; shared runner dry-run/redaction verified; worker execution remains disabled pending offline images and Harbor CLI env. `tau2` is no longer an active bench target; keep only tau3, while preserving the upstream source checkout path where tau3 generation depends on it.
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
