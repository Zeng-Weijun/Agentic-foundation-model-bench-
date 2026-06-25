# hunt-runtime-images lane

Agent: surface:50 hunt-runtime-images
Updated: 2026-06-25 Asia/Shanghai
Scope: Docker/image/registry/offline-worker readiness for SWE-bench Verified multi scaffold, RepoZero, Terminal-Bench 2.1, DeepSWE, P0 registry/rootless worker.
Write policy: this lane file only. No production code or manifest changes.
Mutation policy observed this round: no benchmark run, no docker pull, no docker load, no daemon restart, no public worker download. One non-network `docker run --rm --network none` RepoZero image smoke was executed to classify CLI image runtime readiness.

## Round 1 independent findings

ISSUE-READY: image preflight commands run the main checkout instead of the active worktree
severity: HIGH
dedup: new
location: manifests/suite.example.yaml:52
static_repro: From the active worktree, run `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only repozero_py2js_smoke --model-profile dev_proxy_gpt54mini_8130` and inspect `runs[0].image_preflight.command`; it contains `cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`, not `.worktrees/bench-image-preflight-only`.
impact: The image-preflight-only implementation and manifest edits being tested on branch `feat/image-preflight-only` can be bypassed on the worker. A one-command worker preflight may execute stale scripts/manifests from the main checkout and give false confidence or fail for the wrong code version.
fix: Derive image preflight `project_root` from the suite file/worktree by default, or set it explicitly to the active shared worktree for this branch. Add a test that generated worker preflight commands use the same repo root as the suite path unless overridden.
evidence: `nl -ba manifests/suite.example.yaml` shows `image_preflight.project_root` at lines 52-54 points to `/repo`; dry-run output generated an SSH command with `cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`.

ISSUE-READY: optional image audit false-passes missing runtime manifests
severity: HIGH
dedup: new
location: scripts/agentic_bench_images.py:339
static_repro: On worker, run `python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/deepswe.yaml --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench --docker-host unix:///tmp/rl/run/docker.sock --json`; repeat for `manifests/images/swebench_verified.yaml`.
impact: `--include-optional-image-preflight --fail-on-optional-image-preflight` cannot reliably audit optional Docker readiness. DeepSWE has `status: missing_r2e_image_manifest`, no refs, and `required: false`, yet the checker exits 0. SWE-bench has `openhands_runtime_image_missing`, yet the OpenHands runtime row is `optional_missing` and the checker exits 0. Offline worker execution can proceed with missing R2E/OpenHands runtime images unless some other manual report is read.
fix: Make optional audit mode fail when optional image rows are missing, or have `agentic_bench_images.py check` expose `optional_missing` as a nonzero or separately fatal status when requested. Reject image entries with no `local_ref`/`image_ref`/fallback unless the whole bench is disabled or the row is explicitly marked `placeholder: true` and excluded from runnable manifests.
evidence: DeepSWE direct check returned `counts {'missing': 0, 'present': 0, 'unchecked': 1}` with `image deepswe_r2e_images_todo status optional_missing required False local_refs [] image_refs []` and `check_rc=0`. SWE-bench direct check returned `openhands_0_54_runtime status optional_missing required False` and `check_rc=0` despite the missing runtime blocker.

ISSUE-READY: image-preflight-only cannot warm images from P0 registry or fallback tar
severity: HIGH
dedup: new
location: scripts/agentic_bench_suite.py:586
static_repro: From the active worktree, inspect `build_run_plan(... only={"repozero_py2js_smoke"})["runs"][0]["image_preflight"]["commands"][0]["check_argv"]`; it contains only `python3 scripts/agentic_bench_images.py check --image-manifest ... --asset-root ... --docker-host ... --json` and omits `--pull`, `--load-fallback`, and `--run-smoke`.
impact: The DRIVER contract says image-preflight-only should warm/check images before adapters run, with registry digest pull followed by shared-tar fallback. Current suite integration only checks existing local cache. A fresh worker with valid P0 digest/tar metadata will fail required preflight instead of warming the image, and a present but unrunnable image can pass without the manifest smoke command.
fix: Add suite-level and per-bench image preflight policy flags for `pull`, `load_fallback`, and `run_smoke`, defaulting to the safe offline runner contract for required image rows. Keep public registries refused; allow only internal P0 digest refs and verified fallback tars. Include these flags in generated `check_argv` and tests.
evidence: `nl -ba scripts/agentic_bench_suite.py` lines 586-598 construct the checker command and only append `--docker-host` and `--json`. A repro print showed `has_pull False`, `has_load_fallback False`, `has_run_smoke False`.

ISSUE-READY: Terminal-Bench 2.1 required image preflight is unreachable through the suite
severity: MEDIUM
dedup: new
location: manifests/suite.example.yaml:281
static_repro: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only terminal_bench_2_1 --model-profile dev_proxy_gpt54mini_8130` returns `runs_len 0` and rc 0, while direct worker check of `manifests/images/terminal_bench_2_1.yaml` returns rc 1.
impact: The Terminal-Bench 2.1 image manifest has a required `fix-git` row and a known-bad fallback tar, but the suite cannot audit it because the bench row is `enabled: false`. Operators can ask for `--only terminal_bench_2_1` preflight and get a successful empty plan instead of the actionable missing image failure.
fix: For image-preflight-only, either include explicitly selected disabled benches when they have `image_manifest`, add an `enabled_for_image_preflight` field, or add a separate enabled image-only smoke row for Terminal-Bench 2.1. Also make zero selected runs a nonzero status unless `--allow-empty-plan` is explicit.
evidence: Suite lines 281-289 show `terminal_bench_2_1`, `image_policy: required`, `enabled: false`. Direct worker check reported `terminal_bench_2_1_fix_git status missing required True`, fallback sha match, inspect stderr `No such image: tb2-offline/fix-git:20260425`, `check_rc=1`.

ISSUE-READY: rootless restart-if-down skips SDK-unhealthy daemon because it gates restart only on docker info
severity: HIGH
dedup: new
location: scripts/check_rootless_docker_worker.sh:128
static_repro: On worker, `DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker info` returns rc 0, but `docker version` returns rc 1 with EOF and Python Docker SDK version negotiation exits 7. The guard's `restart-if-down` branch skips restart when `docker_info_ok` succeeds.
impact: Docker-SDK or compose-style benchmarks can be scheduled on a daemon that looks healthy to `docker info` and image inspect but fails `/v1.45/version`. This already matches the rootless EOF failure mode that blocks CoCoA-style sandbox startup and can affect Terminal-Bench/compose integrations. The live daemon also lacks the new `--config-file=/dev/null` startup flag, but the guard will not restart it while `docker info` succeeds.
fix: Split health into `info_ready`, `version_endpoint_ready`, `sdk_ready`, and `compose_ready`. In `--restart-if-down`, treat `/version` or SDK failure as down for SDK/compose workloads, but only restart after confirming no active containers/benchmark processes. If restart is not safe, fail closed with `rootless_daemon_sdk_unhealthy` instead of continuing.
evidence: Current worker probe: `docker info` rc 0 with server 26.1.3 and root `/tmp/rl/data`; `docker version` rc 1 with `Get ... /v1.45/version: EOF`; Python Docker SDK printed `DockerException Error while fetching server API version`. Script lines 62-64 define `docker_info_ok`; lines 128-134 skip restart on that predicate; lines 151-204 later mark `docker_version` and SDK failures only after the skip decision.

## Covered non-findings this round

- RepoZero image asset is currently present and runnable by Docker CLI on worker. Direct preflight check returned `present=1 missing=0 tar_verified=1 check_rc=0`, and `docker run --rm --network none ghcr.io/jessezzzzz/repoarena-new:latest /bin/sh -lc "python3 --version || python --version || echo shell-ok"` returned rc 0 with `Python 3.12.3`.
- P0 registry service and worker CA/curl path are currently healthy. On `swe_dev2`, `docker ps --filter name=swe-dh-shared-registry` showed the registry container up and both `curl -k https://100.97.118.137:8555/v2/` and `curl --cacert .../domain.crt` returned rc 0. On worker, CA copies exist under `/etc/docker/certs.d`, `/root/.config/docker/certs.d`, and `/tmp/rl/data/certs.d`; worker `curl --cacert ... https://100.97.118.137:8555/v2/` returned rc 0.
- No worker P0 pull was run in this round. The registry distribution path still needs a controlled pull test after the rootless daemon health policy above is fixed or a no-restart pull window is explicitly assigned.

## Cross-lane review of hunt-runner-results

The requested peer lane file `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` does not exist in the active worktree yet. There are no peer findings to CONFIRM, REFUTE, or mark DUPLICATE in this round.

CONFIRM/REFUTE/DUPLICATE notes:
- NO-PEER-FINDINGS: `hunt-runner-results.md` missing; cross-check pending once surface:54 writes its ledger.

## Commands and exit codes

- `sed -n '1,380p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Remote read of `DRIVER.md` and `HANDOFF.md` from active worktree: rc 0.
- Initial lane listing: rc 0; `lanes/` directory missing.
- Local manifest/script/report inspections through `ssh dev`: rc 0 except two harmless `printf` formatting retries, rc 2, immediately rerun with safe formatting.
- Worker RepoZero default image check: rc 0, `present=1`, `tar_verified=1`.
- Worker RepoZero `docker run --rm --network none` image smoke: rc 0.
- Worker Terminal-Bench 2.1 direct image check: checker rc 1, required image missing.
- Dev Terminal-Bench 2.1 suite dry-run selection: rc 0, `runs_len 0`.
- Worker DeepSWE direct image check: checker rc 0 despite `optional_missing` placeholder.
- Worker SWE-bench direct image check: checker rc 0 despite `openhands_0_54_runtime optional_missing`.
- P0 registry service/curl on `swe_dev2`: rc 0.
- Worker CA/curl/socket/live rootless cmdline probe: rc 0.

## Next loop target

Next uncovered runtime/image subdomain: Terminal-Bench 2.1 image inventory beyond `fix-git`: reconcile the 86 manifest rows, 64 unique tasks, and about 50 shared tars; identify which selected first-smoke tasks have loadable worker images, which rows are duplicates or missing archives, and whether a separate image-only enabled suite row is needed before adapter implementation.
