# Harbor Bench Handoff

Updated: 2026-06-26 02:27 Asia/Shanghai

## Objective

Build the Harbor/P0-registry-backed bench runner path so a future worker can run all listed agentic benchmarks from one shell/YAML command, with offline image warmup/checks separated from actual benchmark adapter execution.

## Current Repo State

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch: `feat/image-warmup-policy`
- Latest branch commit: current commit `Materialize SWE django fallback transport`
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
- Current Round 10 dispatch: surface:50 audits concrete transport population for the remaining 39 TB2 missing rows and should account for the now-verified SWE django10097 fallback transport; surface:54 writes fixture-ready parser expectations for Terminal-Bench nonzero-with-manifest and DeepSWE failure-before-result. Both are ledger-only and should not edit production code.
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
- Issue #12 tracks normalized result provenance. Runner-results Round 9 produced the safe `source.native_artifacts[]` role/status map for RepoZero, tau3, SWE-bench, Terminal-Bench 2.1, and DeepSWE; no new issue opened.
- Registry-selected static transport gate now exists as `python3 scripts/agentic_bench_images.py lint-registry`. It lints selected `bench_registry.yaml` rows by repeated/comma-separated `--policy` or `--manifest-id`, returning nonzero if required rows lack internal digest refs or fallback tar checksums.
- Issue comments posted after `ce2adf2`: #6 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/6#issuecomment-4802817585`, #11 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/11#issuecomment-4802817769`, #12 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/12#issuecomment-4802817962`, #10 `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-/issues/10#issuecomment-4802818184`.

## Red Lines

- Concrete code execution on remote shared paths, not Mac-local paths.
- Durable artifacts under `/mnt/shared-storage-user/mineru2-shared/zengweijun`.
- Do not use stale worker aliases.
- Do not print tokens.
- Do not let multiple agents write production files in the same worktree.
- No `/clear` on active agents.

## Next Wakeup Prompt

Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then this handoff. Run `cmux surface-health` and read surfaces 50 and 54 by content as the only continuous bug-hunt pair; read 51/55 only if they were explicitly assigned implementation review or smoke. Collect new `ISSUE-READY` blocks from `_coordination/20260625_harbor_bench/lanes/*.md`, cross-check the two ledgers, dedup against GitHub/open reports, file issue/comment if confirmed, and keep the two hunt agents busy. Continue main implementation from the active shared worktree. Next main step: use `lint-registry` as the static promotion gate, then publish or record transport for the remaining 39 TB2 cache rows via P0 digest refs or verified fallback tar sha; SWE django10097 fallback transport is now verified and worker-smoked, but P0 digest publication remains preferred for scale. Run worker runtime `check`/smoke via explicit worker-j9jjd endpoint with suite concurrency 40-50 and image transport concurrency capped separately at 2-4.

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
- Generated image manifests now include `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` (89 TB2 rows from swe_dev cache, 50 with verified fallback tar sha) and `manifests/images/swebench_verified_django10097.yaml` (official eval base + swerex wrapper identity probe). SWE django10097 now has verified fallback tar sha for both rows; worker-j9jjd `--load-fallback --run-smoke` loaded the official eval base over the prior wrapper alias mismatch and ended with `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, `identity_mismatch=0`.
- Static image manifest lint is available via `python3 scripts/agentic_bench_images.py lint --require-offline-transport`; current expected results: RepoZero/P0 smoke pass, SWE django10097 promotion smoke pass, and TB2 generated cache manifest fails closed with 39 required rows missing offline transport.
- Registry-selected lint validation: `validate` rc 0 with `manifests=9/images=104/required_images=94`; `lint-registry` for `required_for_registry_health` + `required_for_repozero_smoke` rc 0 with 0 missing transport; `lint-registry` for `required_for_swebench_django10097_promotion_smoke` rc 0 with 0 missing transport; combined TB2+SWE promotion lint now rc 1 with 39 missing transports, all in TB2.
- Latest full verification for the lint-registry change: `python3 -m unittest scripts.test_agentic_bench_images scripts.test_agentic_bench_suite scripts.test_offline_images_manifest` passed 34 tests; `py_compile` and `git diff --check` passed.
- Merge/push/sync shared main checkout: pending for current branch; latest pushed main is `c42f23c` before this warmup-policy commit.

## 2026-06-26 SWE django10097 fallback evidence

- Official eval base fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/swebench/django10097/swebench_django10097_eval_base.tar` (`sha256:b1581243bc031c9dfb246095c039814f5f349c703bb3d67aecde11c239fb8616`).
- Wrapper fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar` (`sha256:2ba506ed3e6ff4fdbb2ed54612b633ed782b4604a7b94a9d49173b0b2fb73275`).
- Tracked sha evidence: `_coordination/20260625_harbor_bench/inventory/swebench_django10097_fallback_sha256_20260626.tsv`.
- Worker command: `agentic_bench_images.py check --image-manifest manifests/images/swebench_verified_django10097.yaml --load-fallback --run-smoke --json` via explicit worker-j9jjd endpoint and `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`; result `present=2`, `tar_verified=2`, `loaded=1`, `smoke_passed=2`, `identity_mismatch=0`.
