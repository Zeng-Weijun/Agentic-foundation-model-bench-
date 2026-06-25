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

## Round 2 Terminal-Bench 2.1 image inventory

Scope: Terminal-Bench 2.1 image inventory only. No production code/manifest edits. No benchmark/model run. No public worker download. No daemon restart. Worker rootless Docker used `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`. This round loaded four small shared tar images and ran non-network shell smokes to classify direct load/inspect/run-smoke readiness.

### Inventory summary

Static inventory from `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl` and source/YAML task trees:

- `manifest_rows=86`
- `unique_manifest_tasks=64`
- `source_task_count=89`
- `yaml_task_count=89`
- `tar_count=50`
- `sha_sidecar_count=0`
- `manifest_tasks_with_present_tar=50`
- `manifest_tasks_missing_tar=14`
- `source_tasks_absent_from_manifest=25`
- `duplicate_task_groups=22`
- `duplicate_extra_rows=22`

Confirmed direct worker load/inspect/run-smoke pass candidates:

| task | tar sha256 | load | inspect | run-smoke |
| --- | --- | --- | --- | --- |
| `llm-inference-batching-scheduler` | `fd609c5aab2a26bd7403bbc5cb39e52160112b718b826bdc02e477909c400615` | already present from prior load | rc 0, image `sha256:ddd05f6d1deef06eb492f8187d569ba2890a09887e99fb51ee891ae9ebd62471` | rc 0, `tb2-smoke-ok` |
| `gcode-to-text` | `d1a85ebdf789dfb2f3b07e321b5824999d1484b3ace4a87880685fd66b3b9231` | rc 0 | rc 0, image `sha256:8fba1dce95b8cf9d7c9c8808445c186a99ffaa4a83dbb122584c1113a13c5371` | rc 0, `tb2-smoke-ok` |
| `compile-compcert` | `65e64bc18b6ec64b5a8e2820b72c22864f1a7c46bc03ec17a9f6e4f37562e2c2` | rc 0 | rc 0, image `sha256:413947be9766744e70f84ea101110834f8e3a5b53a51e61bfd17c82a644559c6` | rc 0, `tb2-smoke-ok` |
| `dna-insert` | `8633a2ab3b72372aa09a5e20ac3b61ffc9943099e979e9760f4beb4f7d19684c` | rc 0 | rc 0, image `sha256:a7b3b181c17858b9f951d770a6664376cdf405b021366af390181a9d45c96477` | rc 0, `tb2-smoke-ok` |
| `headless-terminal` | `512df3d45789c370060e75ed633049260f36094f4dc43dd4958a4f34d833c374` | rc 0 | rc 0, image `sha256:391df61f6e5030070d2c6ad00c3456ca2437557fcffa49f5fb4aa1ec0116d4ff` | rc 0, `tb2-smoke-ok` |

Known bad / not ready:

- `fix-git`: tar exists, sha256 `6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511`, current worker inspect rc 1. Load was not repeated this round because `reports/terminal_bench_2_1_image_load_debug_20260625.md` already reproduces `docker load` rc 1 with `unlinkat /app/resources/patch_files: input/output error`; current manifest still marks `load_status: known_bad_on_worker_rootless`.
- Remaining tar-present tasks: 44 task tars are present but not load-smoked in this bounded round. Do not call them directly ready until load/inspect/run-smoke is sampled or batched under a storage budget.

Manifest tasks with rows but missing tar:

`mteb-retrieve`, `multi-source-data-merger`, `path-tracing`, `path-tracing-reverse`, `portfolio-optimization`, `protein-assembly`, `regex-chess`, `reshard-c4-data`, `rstan-to-pystan`, `sam-cell-seg`, `schemelike-metacircular-eval`, `train-fasttext`, `video-processing`, `winning-avg-corewars`.

Source tasks absent from image manifest entirely:

`install-windows-3.11`, `nginx-request-logging`, `openssl-selfsigned-cert`, `overfull-hbox`, `password-recovery`, `polyglot-c-py`, `polyglot-rust-c`, `prove-plus-comm`, `pypi-server`, `pytorch-model-cli`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `query-optimize`, `raman-fitting`, `regex-log`, `sanitize-git-repo`, `sparql-university`, `sqlite-db-truncate`, `sqlite-with-gcov`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`, `tune-mjcf`, `vulnerable-secret`, `write-compressor`.

Duplicate manifest task groups:

`adaptive-rejection-sampler`, `bn-fit-modify`, `build-pov-ray`, `circuit-fibsqrt`, `compile-compcert`, `constraints-scheduling`, `custom-memory-heap-crash`, `distribution-search`, `dna-assembly`, `dna-insert`, `extract-moves-from-video`, `feal-differential-cryptanalysis`, `feal-linear-cryptanalysis`, `filter-js-from-html`, `fix-git`, `fix-ocaml-gc`, `gcode-to-text`, `headless-terminal`, `llm-inference-batching-scheduler`, `make-mips-interpreter`, `mcmc-sampling-stan`, `mteb-leaderboard`.

COMMENT-READY for #6: Terminal-Bench 2.1 fallback warmup needs inventory completeness and sha gating before full-suite preload
severity: HIGH
dedup: comment-on-#6
location: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl`, `manifests/images/terminal_bench_2_1.yaml:9-26`
static_repro: Run the static inventory script over `manifest.jsonl`, `terminal-bench-2.1/tasks`, `terminal-bench-2.1-yaml`, and `prebuilt-images/20260425/*.tar`.
impact: Even after #6 adds `--pull`, `--load-fallback`, and `--run-smoke`, Terminal-Bench 2.1 cannot be safely warmed as a full 89-task bench from current assets. Only 50 of 89 source tasks have present tars; 14 manifest tasks point to missing archives; 25 source tasks have no manifest row; all 50 present tars lack sidecar sha files or sha fields in `manifest.jsonl`. A batch warmup would either silently skip 39 tasks or load unverifiable tar bytes.
fix: Generate a dedicated TB2.1 image manifest with one canonical row per task, no duplicate rows, `fallback_tar_sha256` for every tar, explicit `missing_tar` rows for the 14 manifest tasks, and explicit `missing_manifest` rows for the 25 source-only tasks. Gate full-suite preload on `present_tar_sha256_count == selected_task_count`; keep unverified tar rows out of required preflight.
evidence: Static inventory returned `manifest_rows=86`, `unique_manifest_tasks=64`, `source_task_count=89`, `tar_count=50`, `sha_sidecar_count=0`, `manifest_tasks_missing_tar=14`, `source_tasks_absent_from_manifest=25`, `duplicate_task_groups=22`. Current `manifests/images/terminal_bench_2_1.yaml` still contains only the known-bad required `fix-git` row.

COMMENT-READY for #7: enable a Terminal-Bench 2.1 image-only suite row, but use a load-smoked task instead of fix-git
severity: MEDIUM
dedup: comment-on-#7
location: `manifests/suite.example.yaml:281-289`, `manifests/images/terminal_bench_2_1.yaml:16-29`
static_repro: On worker rootless Docker, load/inspect/run-smoke selected small tars from `prebuilt-images/20260425` with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
impact: The disabled `terminal_bench_2_1` row still makes `--only terminal_bench_2_1` unreachable, while the only manifest row points to `fix-git`, whose tar is known bad. A useful image-only suite row exists now if it targets a proven image candidate, letting the runner exercise TB2.1 preflight without waiting for CLI/model execution or the `fix-git` rebuild.
fix: Add an enabled image-only/preflight-only TB2.1 row or `enabled_for_image_preflight` path selecting one of the load-smoked images. Recommended first candidate: `tb2-offline/llm-inference-batching-scheduler:20260425` because it was already in the worker cache and passed `docker run --rm --network none`. Other validated candidates from this round are `gcode-to-text`, `compile-compcert`, `dna-insert`, and `headless-terminal`. Keep `fix-git` as `known_bad` until rebuilt/resaved and load-tested.
evidence: Worker test on 2026-06-26 returned load/inspect/run-smoke rc 0 for `gcode-to-text`, `compile-compcert`, `dna-insert`, and `headless-terminal`; `llm-inference-batching-scheduler` inspect and run-smoke rc 0 from prior load. Current `fix-git` inspect rc 1 and load was skipped as known-bad with existing `unlinkat /app/resources/patch_files` evidence.

## Cross-lane review update

Read `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` after Handoff update.

CONFIRM: runner-results confirms runtime issues #4, #5, #6, #7, and #8 with independent static repros. No refutation.
DUPLICATE note: runner-results already marks Terminal-Bench 2.1 disabled-row parser consequence as `duplicate-of-#7` for selection/preflight and `comment-on-#1` for parser consequence. This runtime round therefore records the TB2.1 image-only row recommendation as `comment-on-#7`, not a new issue.

## Round 2 commands and exit codes

- `sed -n '1,380p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read systematic-debugging skill plus remote `HANDOFF.md`, `DRIVER.md`, and current runtime ledger: rc 0.
- Memory quick search for TB2.1 terms: rc 0, no relevant memory hits printed.
- Read TB2.1 reports and shared prebuilt file listings: rc 0.
- Static inventory script over manifest/source/YAML/tars: rc 0.
- Worker rootless current TB tag inventory: rc 0; before this round only `tb2-offline/llm-inference-batching-scheduler:20260425` was present.
- Worker load/inspect/run-smoke batch: rc 0 overall. Per-image results: `llm-inference-batching-scheduler` inspect rc 0 and run-smoke rc 0; `gcode-to-text`, `compile-compcert`, `dna-insert`, and `headless-terminal` each had load rc 0, inspect rc 0, run-smoke rc 0; `fix-git` inspect rc 1 and load skipped as known-bad.
- Read suite row, image manifest row, and peer lane: rc 0.

## Next loop target

Next uncovered runtime/image subdomain: P0 registry distribution for Terminal-Bench-compatible images. Check whether one load-smoked TB2.1 image can be promoted to a digest-pinned P0 registry artifact from a staging host with fallback tar sha, without relying on worker public internet or the SDK-unhealthy `/version` endpoint.

## Round 3 P0 TB2.1 promotion and rootless worker pull gate

Scope held for this loop:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first and used the active worktree `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Wrote only this runtime/images ledger. No production code, manifests, commits, daemon restarts, or public worker downloads.
- Bounded active probe was one Terminal-Bench 2.1 image: `tb2-offline/gcode-to-text:20260425`.

### Evidence summary

Source/cache coverage:

- `swe_dev` Docker cache is a richer source than shared TB2.1 tars and current worker cache: live count returned `tb2_offline=89`, `swebench=500`, `swerex_prebuilt=728`, `openhands_like=1`, `repozero_like=1`.
- Shared TB2.1 prebuilt path has `tar_files=51`, `manifest_rows=86`, `manifest_unique_tasks=64`, and duplicate task rows including `gcode-to-text`; it is not a complete canonical image map.
- Current worker rootless cache has `tb2_offline=5`, `swebench=134`, `swerex_prebuilt=237`, `openhands_like=0`, `repozero_like=1`, `p0_tb_tags=0`; tags overlap, and total Docker image count is `244`.
- Worker has `60` CPUs, `Containers=0`, `Running=0`, no active benchmark processes matched `agentic_bench|terminal-bench|terminalbench|swebench|repozero|openhands|mini-swe|swe-agent`.

P0 registry and one-image promotion:

- Registry on `swe_dev2` was healthy: container `swe-dh-shared-registry Up 3 hours`, `curl -k -fsS https://100.97.118.137:8555/v2/` returned `{}`, Docker root `/data/docker`.
- Before the probe, `swe_dev2` did not have `tb2-offline/gcode-to-text:20260425` locally and did not have the P0 tag locally.
- Shared tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/gcode-to-text.tar` has sha256 `d1a85ebdf789dfb2f3b07e321b5824999d1484b3ace4a87880685fd66b3b9231`.
- `docker load -i` on `swe_dev2` loaded image ID `sha256:8fba1dce95b8cf9d7c9c8808445c186a99ffaa4a83dbb122584c1113a13c5371`.
- Pushed P0 ref `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-gcode-to-text:20260425`; digest returned `sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251`.
- P0 manifest HEAD after push returned `HTTP/1.1 200 OK`, `Content-Type: application/vnd.docker.distribution.manifest.v2+json`, `Docker-Content-Digest: sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251`.

Worker registry vs fallback reproduction:

- Worker CA files exist at `/etc/docker/certs.d/100.97.118.137:8555/ca.crt`, `/root/.config/docker/certs.d/100.97.118.137:8555/ca.crt`, and `/tmp/rl/data/certs.d/100.97.118.137:8555/ca.crt`.
- Worker host-level `curl -k -fsS https://100.97.118.137:8555/v2/` returned `{}`.
- Worker rootless `docker pull 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-gcode-to-text@sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251` failed with `network is unreachable`.
- `/tmp/rl/dockerd.log` recorded the matching daemon-side error: `Get "https://100.97.118.137:8555/v2/": dial tcp 100.97.118.137:8555: connect: network is unreachable`.
- Same worker daemon still has the prior `docker version` EOF symptom: `Client=26.1.3 Server=` followed by `error during connect: Get "http://%2Ftmp%2Frl%2Frun%2Fdocker.sock/v1.45/version": EOF`.
- Fallback tar path is viable for this selected image: worker sha256 matched `d1a85ebdf789dfb2f3b07e321b5824999d1484b3ace4a87880685fd66b3b9231`, local tag inspect returned the same image ID `sha256:8fba1dce95b8cf9d7c9c8808445c186a99ffaa4a83dbb122584c1113a13c5371`, and `docker run --rm --network none tb2-offline/gcode-to-text:20260425 /bin/sh -lc "printf tb21-fallback-smoke-ok"` exited 0.

Concurrency/static runner risk:

- `manifests/suite.example.yaml:10-11` sets `concurrency: 40` and `proxy_concurrency_ceiling: 50`.
- `scripts/agentic_bench_suite.py:1085-1097` uses `suite_concurrency` directly as the image-preflight `ThreadPoolExecutor(max_workers=...)` size.
- `scripts/agentic_bench_images.py:353-371` attempts pull, then fallback load, per manifest entry. There is no per-worker first-pull cap, per-image dedupe lock, or global image-transport semaphore in the static path inspected here.

COMMENT-READY for #8 and #6: worker rootless daemon cannot currently pull P0 by digest even though registry, CA files, and host curl are healthy
severity: HIGH
dedup: comment-on-#8 for rootless daemon readiness; comment-on-#6 for pull/load-fallback warmup behavior
location: `worker-j9jjd` with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`; `manifests/bench_registry.yaml:17`; `scripts/check_rootless_docker_worker.sh`; `scripts/agentic_bench_images.py:353-371`
static_repro: From worker with the rootless socket exported, run `docker pull 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-gcode-to-text@sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251`. Host `curl -k https://100.97.118.137:8555/v2/` succeeds first; the daemon pull fails.
impact: P0 registry promotion works for the selected TB2.1 image, but the active rootless worker cannot consume it by digest. A runner that treats `docker info` or host curl as sufficient readiness will schedule registry transport and fail at image warmup. Under a 40-50 concurrency suite, this can multiply identical rootless pull failures and mask a viable tar fallback.
fix: Treat registry transport readiness as a separate worker state from Docker cache readiness. Guard should require an internal-registry `docker pull` plus `docker run --network none` smoke, or explicitly mark `registry_pull_unavailable` and force verified fallback tar loading. Do not enable required P0 pull for worker-j9jjd until the rootless daemon networking issue is fixed or the suite has deterministic fallback-only mode for that worker class.
evidence: P0 push returned digest `sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251` and registry HEAD returned 200. Worker CA paths all exist and host curl returned `{}`. Worker `docker pull` rc 1 with `network is unreachable`; dockerd log contains the same error. Fallback tar inspect and run-smoke rc 0 for the same image ID.

COMMENT-READY for #6: one TB2.1 image can be promoted to P0, but the manifest row must carry both digest and fallback tar sha until worker digest pulls pass
severity: HIGH
dedup: comment-on-#6
location: P0 ref `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-gcode-to-text@sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251`; shared tar `terminalbench2.1/prebuilt-images/20260425/gcode-to-text.tar`
static_repro: Load the shared tar on `swe_dev2`, tag and push to P0, then pull by digest on worker and fall back to the tar if pull fails.
impact: The registry side is ready for this image, but end-to-end worker readiness is fallback-only today. If the image manifest stores only the registry digest, worker-j9jjd cannot reproduce the selected image. If it stores only the tar, the P0 promotion cannot be validated by manifest digest. Both transports are needed until rootless pull is fixed.
fix: For the first TB2.1 image-only suite row, add a canonical row with `image_ref` equal to the digest above, `local_ref: tb2-offline/gcode-to-text:20260425`, `fallback_tar` equal to the shared tar path, and `fallback_tar_sha256: d1a85ebdf789dfb2f3b07e321b5824999d1484b3ace4a87880685fd66b3b9231`. Keep required preflight gated on fallback smoke for worker-j9jjd until digest pull smoke passes.
evidence: `docker load -i gcode-to-text.tar` on `swe_dev2` rc 0, `docker push` rc 0, registry HEAD rc 0. Worker `docker pull` digest rc 1. Worker fallback sha/inspect/run-smoke command rc 0 and printed `tb21-fallback-smoke-ok`.

COMMENT-READY for #6 and #8: image warmup must cap and dedupe first-time transport before using 40-50 suite concurrency
severity: HIGH
dedup: comment-on-#6; overlaps #8 daemon-readiness risk
location: `manifests/suite.example.yaml:10-11`, `scripts/agentic_bench_suite.py:1075-1097`, `scripts/agentic_bench_images.py:353-371`, `WORKFLOW.md` P0 registry contract
static_repro: Inspect `suite.example.yaml` and `_execute_image_preflights()`: image preflight uses `suite_concurrency` as the executor worker count. Inspect the checker: pull/load are per entry with no cross-run semaphore or image-key lock.
impact: The target 8.130 run shape starts at concurrency 40 and ceiling 50 on a 60-CPU worker. With current code shape, a required preflight suite could launch up to 40 image preflight processes at once. If many rows point to the same missing digest or same fallback tar, the worker can stampede the rootless daemon, P0 registry, and shared filesystem. With current worker digest pull failure, this becomes 40 concurrent failures before fallback. With large SWE/TB images, this can turn image staging into the bottleneck or induce rootless Docker EOF/cgroup churn.
fix: Add an image warmup phase before bench scheduling that groups by canonical image digest or fallback tar sha, runs one transport operation per image per worker, records `image_ready`, and exposes a small first-time pull/load cap independent of model suite concurrency. The cap should follow the workflow guidance of 2-4 first-time pulls per worker. Benchmark execution concurrency 40-50 should start only after selected images are ready.
evidence: Workflow P0 contract says to cap first-time image pulls per worker to 2-4. Current static code uses `max_workers = suite_concurrency`; suite example sets 40/50. Worker evidence shows rootless `docker pull` failed for a single selected digest, while fallback smoke passed serially.

COMMENT-READY for #6/#7: current full TB2.1/SWE image source is cache-first, not manifest-complete
severity: HIGH
dedup: confirms and extends prior runtime Round 2; comment-on-#6/#7
location: `swe_dev` Docker cache; `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425`; `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`
static_repro: Count `swe_dev` Docker repositories by prefix and compare to shared TB2.1 tar/manifest counts plus worker cache counts.
impact: Full Terminal-Bench 2.1 and SWE-bench Verified multi cannot be made required on worker from the current shared manifests alone. `swe_dev` has many end-to-end runtime images, but that cache is not portable evidence until each selected image is exported or pushed with digest/sha and linked in a manifest row. Worker lacks OpenHands-like images in the current cache and only has five TB2.1 task images.
fix: Use `swe_dev` Docker cache as the reconstruction source, but publish selected smoke rows only after each has either a P0 digest plus consumer smoke or a fallback tar with sha plus worker load/run smoke. For SWE-bench Verified multi, freeze selected smoke task IDs per scaffold and map each to exact `swebench/*` and `swerex-prebuilt:*` refs before enabling required image preflight.
evidence: `swe_dev` live image count returned `tb2_offline=89`, `swebench=500`, `swerex_prebuilt=728`; shared TB2.1 has `tar_files=51`, `manifest_rows=86`, `manifest_unique_tasks=64`; worker has only `tb2_offline=5`, `swebench=134`, `swerex_prebuilt=237`, `openhands_like=0`, and no P0 TB tags.

### Round 3 command evidence

- `sed -n '1,520p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- `rg -n "Continuous Multi-Agent Bug-Hunt|Cross-Model Alignment|Bug-Hunt" WORKFLOW.md && sed -n '760,980p' WORKFLOW.md`: rc 0.
- Found and read `superpowers:systematic-debugging` skill: `find .../systematic-debugging/SKILL.md` rc 0; `sed -n '1,520p'` over the skill rc 0.
- Initial explicit `swe_dev2` endpoint typo/probe returned rc 255 `Permission denied (publickey)`; subsequent workflow alias `ssh swe_dev2` was used successfully.
- Read active worktree status, `reports/swe_terminal_image_inventory_20260626.md`, and peer `hunt-runner-results.md`: rc 0.
- `swe_dev` Docker cache count and selected image inspect: rc 0; returned `tb2_offline=89`, `swebench=500`, selected `gcode-to-text` image ID `sha256:8fba1dce95b8...`.
- Worker Docker info/system df/TB2 image inventory/selected inspect: rc 0; returned `Images=244`, `Containers=0`, five TB2.1 task tags, selected image ID `sha256:8fba1dce95b8...`.
- `swe_dev2` registry health and selected local-image check: rc 0; registry healthy, selected image absent before load.
- Worker CA/curl/CPU/container/process check: rc 0; CA paths present, host curl returned `{}`, `nproc=60`, no active containers or benchmark processes.
- Shared TB2.1 gcode tar and manifest row check: rc 0; `gcode-to-text.tar` present, duplicate manifest rows found.
- Code grep with `rg` on `swe_dev2` printed `rg: command not found`; repeated with `grep -RInE` rc 0.
- One-image `swe_dev2` load/tag/push: rc 0; tar sha `d1a85e...`, remote-before 404, push digest `sha256:4453cf8e9ff6...`.
- Worker digest pull: rc 1; failed with `dial tcp 100.97.118.137:8555: connect: network is unreachable`.
- Worker fallback tar sha/inspect/run-smoke: rc 0; printed `tb21-fallback-smoke-ok`.
- Worker rootless process/log/version probe: rc 0 for wrapper command; `docker version` output still showed `/v1.45/version` EOF.
- Worker dockerd PID/proc route read: rc 0; `nsenter` probe was not used as evidence because it is blocked by `Operation not permitted`.
- P0 manifest HEAD after push: rc 0; returned `HTTP/1.1 200 OK` and matching digest header.
- Exact shared TB2.1 and SWE hint count: rc 0; `tar_files=51`, `manifest_rows=86`, `manifest_unique_tasks=64`, shared SWE hint files count `47`.
- `swe_dev` data-path command was interrupted during slow `du -sh /data/docker`: wrapper rc 255 after already printing the live Docker image counts and smaller path sizes; not used for `/data/docker` sizing.
- Static line-reference read for suite concurrency and image warmup code: rc 0.
- Refreshed worker image prefix counts: rc 0; `tb2_offline=5`, `swebench=134`, `swerex_prebuilt=237`, `openhands_like=0`, `repozero_like=1`, `p0_tb_tags=0`.

## Next loop target

Next runtime/image subdomain: build the minimal selected-image manifest proposal for TB2.1 plus SWE-bench Verified multi without editing manifests. For TB2.1, start with `gcode-to-text` because it now has P0 digest evidence and fallback tar smoke evidence. For SWE-bench, select one exact smoke task per scaffold and map each required `swebench/*` plus `swerex-prebuilt:*` image from `swe_dev` cache before any required preflight is enabled.
