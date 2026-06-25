# 2026-06-25 Harbor Bench Driver

## Goal

Make this repository a one-command control plane for offline worker execution of the listed agentic benchmarks, using the project P0 OCI registry plus shared-tar fallback. The near-term implementation target is a suite-level image preflight-only mode that warms/checks Docker images before benchmark adapters run.

## Canonical Remote Paths

- Shared repo root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Active implementation worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/bench-image-preflight-only`
- Active branch: `feat/image-preflight-only`
- Worker endpoint: `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`
- Worker Docker socket: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`
- P0 registry: `https://100.97.118.137:8555`

Do not put durable code, reports, or run artifacts on the local Mac. The Mac is only the cmux/SSH control plane.

## Red Lines

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before acting in this workspace.
- Run code inspection, edits, tests, and benchmark commands on remote hosts through SSH, with durable files under the shared root.
- Do not edit the same worktree from multiple agents unless the write set is explicitly assigned.
- Do not print or persist secrets. Use env vars or pre-existing auth helpers.
- Do not use stale worker aliases. Use only `worker-j9jjd` for current offline-worker probes.
- Do not run public-internet downloads from the worker.
- Do not `/clear` active cmux agents.
- Bug-hunt output must be issue-driven: no vague findings without repro and dedup status.

## Current Main Implementation Contract

Add `scripts/agentic_bench_suite.py --image-preflight-only`:

- Build the suite plan but run only per-bench `image_preflight.commands`.
- Never run benchmark adapter commands in this mode.
- Required preflight failures are fatal.
- Optional preflights are skipped by default.
- `--include-optional-image-preflight` audits optional preflights.
- `--fail-on-optional-image-preflight` makes optional failures fatal when auditing.
- Write controller artifacts under `--output-dir` or the computed controller dir:
  - `run_manifest.json`
  - `image_preflight_summary.json`
  - logs under `logs/<bench>.image_preflight.log`
- Preserve existing `--execute` behavior: required image preflight still blocks adapter execution.

## Acceptance Commands

Run from the active shared worktree on `swe_dev` unless stated otherwise:

```bash
python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_image_preflight_only_runs_required_preflight_without_adapter scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_image_preflight_only_skips_optional_by_default_and_can_audit_nonfatal
python3 -m unittest scripts.test_agentic_bench_images scripts.test_agentic_bench_suite scripts.test_offline_images_manifest
python3 -m py_compile scripts/agentic_bench_images.py scripts/agentic_bench_suite.py scripts/check_offline_images_manifest.py scripts/test_agentic_bench_images.py scripts/test_agentic_bench_suite.py scripts/test_offline_images_manifest.py
git diff --check
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --image-preflight-only --only tau2_paper_core --output-dir /tmp/no_image_preflight_check
```

Worker smoke runs through the worker SSH endpoint and rootless Docker:

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --image-preflight-only --only repozero_py2js_smoke --model-profile dev_proxy_gpt54mini_8130 --max-concurrency 1 --output-dir /tmp/agentic_repozero_preflight_only_<stamp>
```

## Bug-Hunt Issue Protocol

Each hunt agent keeps a lane report under `_coordination/20260625_harbor_bench/lanes/<lane>.md`. A finding can be escalated only when it has this exact block:

```text
ISSUE-READY: <short title>
severity: HIGH|MEDIUM|LOW
dedup: new|comment-on-#N|duplicate-of-#N
location: <file:line or manifest path>
static_repro: <command or deterministic inspection>
impact: <why one-command offline/full bench run breaks>
fix: <concrete fix or mitigation>
evidence: <short observed output or artifact path>
```

Orchestrator files GitHub issues only after dedup against open issues. If it enriches an existing issue, post a comment instead of opening a duplicate. Fixes follow implement -> cross-family review -> PASS -> merge/comment-close.

## Current Continuous Bug-Hunt Pair

- Only two agents run continuous systematic bug hunt.
- surface:50 `hunt-runtime-images`: Docker/image/registry/offline-worker readiness across SWE-bench, RepoZero, Terminal-Bench 2.1, DeepSWE, and related manifests.
- surface:54 `hunt-runner-results`: suite runner, result parser, benchmark-status separation, trace/harness contracts, and score aggregation.
- Alignment cadence: each agent first hunts independently, then reviews the other agent's ledger and writes `CONFIRM`, `REFUTE`, or `DUPLICATE` notes. The orchestrator files issues only after this cross-check.
- Loop rule: when a lane dries up, the agent switches to the next uncovered benchmark category inside its assigned domain rather than stopping.
- surface:51 and surface:55 are not bug-hunt lanes. Keep them idle/reserved for later implementation review or targeted smoke only.

## Main Orchestrator Next Steps

1. Dispatch only surface:50 and surface:54 as the continuous bug-hunt pair.
2. Implement `--image-preflight-only` in the shared worktree using TDD.
3. Run the acceptance commands above on `swe_dev`.
4. Run one worker RepoZero preflight-only smoke.
5. Cross-align the two hunt ledgers, then dedup and file/comment GitHub issues for confirmed ISSUE-READY findings.
6. Merge/push the implementation, then sync the main shared checkout.
7. Schedule a wakeup loop around this handoff and keep the two hunt agents busy.
