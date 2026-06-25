# Harbor Bench Handoff

Updated: 2026-06-26 00:25 Asia/Shanghai

## Objective

Build the Harbor/P0-registry-backed bench runner path so a future worker can run all listed agentic benchmarks from one shell/YAML command, with offline image warmup/checks separated from actual benchmark adapter execution.

## Current Repo State

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch: `feat/image-warmup-policy`
- Base commit: `c42f23c Record runtime image hunt issues`
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
- Image inventory: `swe_dev` has substantially more SWE-bench/TB2.1 Docker images than worker; shared TB2.1 tars are partial, so worker full runs need staging from `swe_dev` cache.
- Terminal-Bench 2.1: `terminal_bench_2_1_image_smoke` is enabled for image preflight using `gcode-to-text`; worker rootless check passes via cached/verified fallback image, while full TB execution remains pending adapter/runtime result wiring.
- Bug-hunt pair: only surface:50 and surface:54 produce `_coordination/20260625_harbor_bench/lanes/*.md`; each must cross-check the other's ledger before the orchestrator files issues.
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

## Red Lines

- Concrete code execution on remote shared paths, not Mac-local paths.
- Durable artifacts under `/mnt/shared-storage-user/mineru2-shared/zengweijun`.
- Do not use stale worker aliases.
- Do not print tokens.
- Do not let multiple agents write production files in the same worktree.
- No `/clear` on active agents.

## Next Wakeup Prompt

Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then this handoff. Run `cmux surface-health` and read surfaces 50 and 54 by content as the only continuous bug-hunt pair; read 51/55 only if they were explicitly assigned implementation review or smoke. Collect new `ISSUE-READY` blocks from `_coordination/20260625_harbor_bench/lanes/*.md`, cross-check the two ledgers, dedup against GitHub/open reports, file issue/comment if confirmed, and keep the two hunt agents busy. Continue main implementation from the active shared worktree, run acceptance commands on `swe_dev`, then run the worker RepoZero preflight-only smoke.

## Acceptance Snapshot

- Warmup-policy red tests added and observed failing for missing checker flags, optional fatality, suite-relative project roots, and empty selected plans.
- Target tests pass: done; 5 focused tests pass.
- Full unittest/py_compile/diff-check: done; 22 unittest pass, py_compile rc 0, `git diff --check` rc 0.
- Dry-run with `manifests/suite.example.yaml --only repozero_py2js_smoke` resolves `project_root` to the active worktree and forwards `--load-fallback --run-smoke`.
- Old customer-service suite entry removed per user direction; current no-adapter smoke examples use RepoZero/tau3 paths.
- Worker RepoZero image-preflight-only smoke: done through local control-plane SSH to worker with a temporary local-execution suite; output `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/verification/repozero_warmup_policy_20260626_001953`; summary status 0, required preflight pass, RepoZero image present, fallback tar sha256 match, container smoke passed.
- Worker DeepSWE optional image audit: `--fail-on-optional-missing` returns rc 1 with `optional_missing: 1`, closing the prior optional-image fake-green path.
- Direct `swe_dev -> worker` remains blocked by publickey; local Mac -> worker works.
- Merge/push/sync shared main checkout: pending for current branch; latest pushed main is `c42f23c` before this warmup-policy commit.
