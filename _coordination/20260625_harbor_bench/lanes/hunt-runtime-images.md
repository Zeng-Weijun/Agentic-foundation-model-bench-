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

## Round 4 SWE-bench Verified multi image mapping

Scope held for this loop:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first and followed the Continuous Multi-Agent Bug-Hunt lane contract.
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, head `edae6f2`, branch `feat/image-warmup-policy` clean relative to origin at start.
- Wrote only this runtime/images ledger. No production code/manifests, no commit/push, no benchmark execution, no image push/load/pull.

### Selected smoke image matrix

Selection sources:

- Qwen Code suite row uses `QWEN_NATIVE_SUBSET=smoke_n20` with no `QWEN_NATIVE_INSTANCE_IDS`. `run_qwen_code_swebench.py` reads `/data/nips/aci_evolve/experiments/preregistration/verified_subsets_seed42_v1.json` and applies `limit`. On `swe_dev`, `smoke_n20` begins `astropy__astropy-7671 django__django-11087 ...`; on `swe_dev2`, the same absolute subset file is absent.
- mini-swe-agent suite row uses `MINI_SWE_SLICE: "0:1"`; the shared scaffold config has smoke `0:2`. The local Verified parquet first rows are `astropy__astropy-12907 astropy__astropy-13033 ...`; the suite row's current first task is therefore `astropy__astropy-12907`.
- SWE-agent config explicitly selects `django__django-10097`.
- OpenHands config explicitly selects `sphinx-doc__sphinx-8595` and requires runtime target `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`, pretagged from `openhands_smoke4_recover:sphinx8595`.
- swe-agent-runtime config explicitly selects `astropy__astropy-14369` and `astropy__astropy-13033`; this round mapped `astropy__astropy-14369` as the one-task smoke representative.
- Harness rootless smoke config selects eight Astropy tasks; this round mapped `astropy__astropy-12907` as the first batch representative.

| scaffold | selected smoke task | `swebench/*` ref | `swe_dev` inspect | worker inspect | `swerex-prebuilt:*` candidates |
| --- | --- | --- | --- | --- | --- |
| qwen-code | `astropy__astropy-7671` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest` | base ID `sha256:03575dfa5837...`, digest `sha256:e00a59320ce1...` | tag exists but ID `sha256:8d93e2be662f...` | 2 candidates; worker tag ID matches `swerex-prebuilt:...-00527122c8e98259` |
| qwen-code | `django__django-11087` | `swebench/sweb.eval.x86_64.django_1776_django-11087:latest` | base ID `sha256:7e7898eb284c...`, digest `sha256:b552856e03fc...` | tag exists but ID `sha256:8459f3393b37...` | 2 candidates; worker tag ID matches `swerex-prebuilt:...-2d8db77938b386db` |
| mini-swe-agent | `astropy__astropy-12907` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest` | base ID `sha256:cce639c4d4c4...`, digest `sha256:f3f63bb87d58...` | tag exists but ID `sha256:3bfd24c0b7c2...` | 3 candidates; worker tag ID matches `swerex-prebuilt:...-896d8eb0c3be14d2` |
| mini-swe-agent | `astropy__astropy-13033` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-13033:latest` | base ID `sha256:bdbc30d363cf...`, digest `sha256:42797a2c686e...` | tag exists but ID `sha256:658a36cc815f...` | 2 candidates; worker tag ID matches `swerex-prebuilt:...-96abc4c7386679ee` |
| swe-agent | `django__django-10097` | `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` | base ID `sha256:cf945d25ceb6...`, digest `sha256:148894532806...` | tag exists but ID `sha256:3e38b9278651...` | 1 candidate; worker tag ID matches `swerex-prebuilt:...-8be1c797d4885b41` |
| openhands | `sphinx-doc__sphinx-8595` | `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8595:latest` | tag exists as ID `sha256:71d1b75dd311...`, no RepoDigest; matches the single `swerex-prebuilt` candidate | missing on worker | 1 candidate on `swe_dev`, missing on worker |
| swe-agent-runtime | `astropy__astropy-14369` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-14369:latest` | base ID `sha256:1a8a749d6b8e...`, digest `sha256:113488bfd3a6...` | tag exists but ID `sha256:6fd8af0267ac...` | 2 candidates; worker tag ID matches `swerex-prebuilt:...-68211511f3b855f7` |
| harness | `astropy__astropy-12907` | same as mini first task | same as mini first task | same as mini first task | same as mini first task |
| openhands runtime | `sphinx-doc__sphinx-8595` runtime | `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98` | missing target tag; source pretag `openhands_smoke4_recover:sphinx8595` exists as ID `sha256:3832f8d74524...` | target and source both missing | no shared tar/P0 digest found |

Shared/P0 state:

- `manifests/images/swebench_verified.yaml` has only two rows: a `django-13810` worker-cache probe and an optional missing OpenHands runtime row. It has no rows for any selected scaffold task above.
- `manifests/suite.example.yaml` marks Qwen Code, mini-swe-agent, SWE-agent, and OpenHands rows `image_policy: optional`; it has no enabled suite row for `swe-agent-runtime` or the rootless harness scaffold.
- Shared image migration manifests under `swe-bench-verified/image_migration/manifests/*` are tag lists only. `find .../image_migration -type f -name '*.tar*'` printed no tar/sha artifacts.
- P0 registry catalog currently returned only `swe-data-harness/repo2env-pallets-click-f6299c4` and `swe-data-harness/terminal-bench-2-1-gcode-to-text`; no SWE-bench or OpenHands runtime repository is present.
- `reports/swe_dev_docker_cache_inventory_20260626.json` records `digest: ""` for cached images even when live `docker image inspect` on `swe_dev` returns `RepoDigests` for official `swebench/*` base refs.

ISSUE-FILED: #11 SWE-bench image preflight can pass wrong worker images because it verifies tag presence but not expected digest or image ID lineage
severity: HIGH
dedup: filed as #11
location: `scripts/agentic_bench_images.py:351-379`, `manifests/images/swebench_verified.yaml:16-24`, worker rootless Docker cache
static_repro: On `swe_dev`, inspect `swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest` and record official base ID `sha256:03575dfa5837...` plus RepoDigest `sha256:e00a59320ce1...`. On worker with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, inspect the same tag; it exists but returns ID `sha256:8d93e2be662f...`, which matches `swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-astropy-1776-astropy-7671-latest-00527122c8e98259`, not the official base image.
impact: A tag-only image preflight can report `present` for `swebench/*` refs while the worker actually holds a different prebuilt environment under the same tag. For SWE-bench Verified multi, this can silently change the execution environment, make OpenHands base-image checks meaningless, and prevent reproducible P0 promotion because the manifest does not say whether the official base image or a specific `swerex-prebuilt` variant is required.
fix: Add expected image identity fields to SWE-bench image rows: `source_repo_digest` for official `swebench/*` base images, `source_image_id` as a fallback identity, and an explicit `swerex_prebuilt_ref` when the scaffold intentionally requires a prebuilt environment. Update `agentic_bench_images.py` to compare inspected `Id`/`RepoDigests` against those fields and return `identity_mismatch` instead of `present` when a tag resolves to the wrong image. Do not mark SWE-bench rows required until each selected scaffold task has a canonical digest/ID and transport path.
evidence: Worker selected inspect returned tag-present IDs `8d93e2be662f` for `astropy-7671`, `8459f3393b37` for `django-11087`, `3bfd24c0b7c2` for `astropy-12907`, `658a36cc815f` for `astropy-13033`, `3e38b9278651` for `django-10097`, and `6fd8af0267ac` for `astropy-14369`. Each matches a `swerex-prebuilt:*` candidate, while `swe_dev` official base inspect returned different IDs and public RepoDigests for the corresponding `swebench/*` refs.

COMMENT-READY for #6: SWE-bench Verified multi still lacks scaffold-specific required image rows for the actual smoke tasks
severity: HIGH
dedup: comment-on-#6
location: `manifests/images/swebench_verified.yaml:1-35`, `manifests/suite.example.yaml:160-252`, shared scaffold configs under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`
static_repro: Read the six scaffold selection sources listed above, then compare selected refs against `manifests/images/swebench_verified.yaml` and live worker inspect.
impact: The current manifest cannot warm or gate the actual smoke images for Qwen Code, mini-swe-agent, SWE-agent, OpenHands, swe-agent-runtime, or the harness. The one cache-probe row targets `django-13810`, which is not any selected smoke task in the current suite/configs. Because suite rows are optional, worker scheduling can proceed with missing or identity-mismatched images.
fix: Replace the generic worker-cache probe with per-scaffold rows keyed by selected task and scaffold role. Each row should include `local_ref`, expected digest/image ID, exact `swerex-prebuilt` variant if required, fallback tar path/sha when available, and `required: true` for enabled smoke rows. Add suite/image rows for `swe-agent-runtime` and `harness` or explicitly mark them out of scope for SWE-bench Verified multi.
evidence: Selected task matrix above maps at least one smoke task per scaffold. `swebench_verified.yaml` contains only `django-13810` and the optional missing OpenHands runtime; no selected task refs appear in it. `suite.example.yaml` uses `image_policy: optional` for Qwen/mini/SWE-agent/OpenHands and has no swe-agent-runtime/harness rows.

COMMENT-READY for #6/#8: OpenHands smoke cannot run on worker from current cache, P0, or fallback artifacts
severity: HIGH
dedup: comment-on-#6; overlaps #8 worker transport readiness
location: `manifests/images/swebench_verified.yaml:29-35`, `swe-bench-verified/openhands/config.yaml:85-132`, P0 registry `https://100.97.118.137:8555`
static_repro: Inspect `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8595:latest`, `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`, and `openhands_smoke4_recover:sphinx8595` on `swe_dev` and worker; list `image_migration` tars and P0 catalog.
impact: OpenHands is the hardest SWE-bench scaffold to reproduce offline. Worker lacks both the selected Sphinx base tag and the OpenHands runtime/pretag images. `swe_dev` has the pretag source but not the target `ghcr.io/all-hands-ai/runtime:...` tag, so the manifest target cannot be inspected or pushed by digest as-is. There is no shared tar/sha and P0 has no OpenHands/SWE-bench repo. A required OpenHands image preflight would fail; an optional one can be skipped and hide the blocker.
fix: Retag the known-good `openhands_smoke4_recover:sphinx8595` source to the exact runtime target on a staging host, inspect ID, then either push to P0 and record digest or save a fallback tar with sha. Also stage the selected Sphinx base/prebuilt image for worker. Make the OpenHands row required only after worker digest pull or fallback load/run smoke succeeds.
evidence: `swe_dev` inspect: runtime target missing; pretag source exists as `sha256:3832f8d74524...`; selected Sphinx tag exists as `sha256:71d1b75dd311...` with no RepoDigest. Worker inspect: selected Sphinx tag missing, runtime target missing, pretag source missing. P0 catalog returned only repo2env and Terminal-Bench `gcode-to-text`. `image_migration` tar search printed no tar/sha artifacts.

COMMENT-READY for #6: Qwen Code smoke task mapping depends on a host-local subset file that is absent from the shared worktree host
severity: MEDIUM
dedup: comment-on-#6
location: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/scripts/run_qwen_code_swebench.py:33`, `run_qwen_code_swebench.py:159-170`, `manifests/suite.example.yaml:170-175`
static_repro: On `swe_dev2`, check `/data/nips/aci_evolve/experiments/preregistration/verified_subsets_seed42_v1.json`; it is absent. On `swe_dev`, read the same file and inspect `sets.smoke_n20.instance_ids[:2]`; it returns `astropy__astropy-7671 django__django-11087`.
impact: The suite row says only `QWEN_NATIVE_SUBSET=smoke_n20`, so a manifest generator running from the shared worktree or `swe_dev2` cannot derive the Qwen smoke image set. Worse, falling back to generic Verified dataset order would choose `astropy__astropy-12907 astropy__astropy-13033`, which are the mini/harness first rows, not Qwen's actual smoke tasks.
fix: Copy the subset JSON into the durable SWE-bench Verified shared tree or encode explicit `QWEN_NATIVE_INSTANCE_IDS` for smoke rows in the suite/image manifest. The image manifest should record the resolved task IDs, not just the subset name.
evidence: `swe_dev2` subset probe printed `exists False`; `swe_dev` subset probe printed `exists True` and `smoke_n20 20 astropy__astropy-7671 django__django-11087 ...`. The Qwen script reads `SUBSET_FILE` at line 33 and slices it at lines 166-170.

COMMENT-READY for #6: Current shared/P0 artifacts are not enough to promote selected SWE-bench images without re-exporting from Docker cache
severity: HIGH
dedup: comment-on-#6
location: `reports/swe_dev_docker_cache_inventory_20260626.json`, `swe-bench-verified/image_migration/manifests/*`, P0 registry catalog
static_repro: Read the cache inventory JSON, inspect selected refs live on `swe_dev`, list `image_migration` tar artifacts, and query `https://100.97.118.137:8555/v2/_catalog?n=100`.
impact: `swe_dev` has the selected images, but the durable artifacts are only tag lists. There are no shared tars/sha files for selected SWE-bench images, no P0 SWE-bench repositories, and the JSON cache inventory loses RepoDigest values even when live Docker inspect has them. This prevents a safe manifest-only promotion plan: selected images must be re-inspected and exported/pushed from Docker cache before required preflight can be enabled.
fix: Regenerate the SWE-bench image inventory with `RepoDigests`, full image IDs, and selected scaffold mapping. For each selected task, either push the exact source image to P0 and record the returned digest after consumer smoke, or save a fallback tar with sha256. Keep `swe_dev` Docker cache as the reconstruction source, but do not treat current shared text manifests as transport-complete.
evidence: P0 catalog returned `repositories=["swe-data-harness/repo2env-pallets-click-f6299c4", "swe-data-harness/terminal-bench-2-1-gcode-to-text"]`. `find <swe-bench-verified>/image_migration -type f -name '*.tar*'` printed no artifacts. Live `swe_dev` inspect for selected official base refs returned RepoDigests, while `reports/swe_dev_docker_cache_inventory_20260626.json` has empty `digest` fields.

### Cross-lane review update

Read `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` after this image-mapping pass.

CONFIRM: runner-results has independent SWE-bench parser findings around missing per-scaffold artifact hints and no parser support. This runtime round is complementary: it maps image/task readiness and does not duplicate parser issue #1.
DUPLICATE note: OpenHands optional missing evidence remains a #6/#8 image-readiness comment, not a new parser issue. Qwen/OpenHands secret-sidecar findings in runner-results are parser-source issues; this runtime round did not inspect or print secrets.

### Round 4 command evidence

- `sed -n '1,520p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && sed -n '760,980p' WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` skill: rc 0.
- Memory quick search for SWE-bench terms: rc 0; no current-runtime evidence used.
- Remote status/HANDOFF/DRIVER read from active worktree: rc 0; head `edae6f2` and branch clean against `origin/feat/image-warmup-policy`.
- Read `reports/swe_dev_docker_cache_inventory_20260626.json` schema and `manifests/images/swebench_verified.yaml`: rc 0.
- Shared tree, suite SWE section, inventory counts, and worker cache prefix counts: rc 0.
- Scaffold config grep/sed for Qwen, mini-swe-agent, SWE-agent, OpenHands, swe-agent-runtime, and harness: rc 0.
- Run-dir artifact listing for Qwen/mini 20260626 smoke dirs: rc 1 because some optional globbed files were absent; the directory listings and `suite.env.summary` evidence printed before exit and were used only as context.
- First selected-map Python probe: rc 1 due shell quoting syntax error; no files changed.
- Qwen `smoke_n20` broad grep was interrupted after it printed the script pointer: rc 255; replaced by bounded script-line and subset-file probes.
- `swe_dev` parquet first-row probe: rc 0; `count=500`, first rows include `astropy__astropy-12907 astropy__astropy-13033`.
- Qwen subset file on `swe_dev2`: rc 0, `exists False`; same file on `swe_dev`: rc 0, `exists True`, `smoke_n20` first IDs printed.
- Selected mapping from cache inventory for all six scaffolds: rc 0.
- Live `docker image inspect` for selected refs on `swe_dev`: rc 0 wrapper; individual missing refs were OpenHands runtime target only.
- Live worker rootless `docker image inspect` for selected refs: rc 0 wrapper; individual missing refs were OpenHands Sphinx base, OpenHands runtime target, and pretag source.
- `image_migration` tar search and selected manifest grep: rc 0 wrapper; no tar artifacts printed; grep reported a stale `latest` symlink warning but selected tag-list rows printed.
- P0 catalog raw probe: rc 0; returned only repo2env and Terminal-Bench `gcode-to-text` repositories.
- Runner-results cross-lane grep: rc 0.

## Next loop target

Next runtime/image subdomain: decide whether to promote one SWE-bench selected image by digest or fallback tar in a future bounded probe. Best candidate is not OpenHands; start with a non-OpenHands selected image after fixing the identity requirement, such as `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` plus its exact `swerex-prebuilt` variant, and verify whether the runner actually requires official base, prebuilt variant, or both.

## Round 5 bounded SWE-agent django-10097 selected-image promotion plan

Scope held for this loop:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first and followed the Continuous Multi-Agent Bug-Hunt lane contract.
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, head `57eb2ce`.
- Wrote only this runtime/images ledger. No production code/manifests, no commit/push, no full eval, no Docker push/load/pull.
- Candidate selected task: non-OpenHands SWE-agent smoke task `django__django-10097`.

COMMENT-READY for #11/#6: `django__django-10097` promotion is not one tag; SWE-agent needs distinct wrapper and official eval-image identities
severity: HIGH
dedup: comment-on-#11 for identity mismatch; comment-on-#6 for missing required SWE image rows/artifacts
location: `swe-bench-verified/swe-agent/config.yaml:85-98`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified.sh:116-160`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/sweagent/lib/python3.11/site-packages/swerex/deployment/docker.py:270-309`, `manifests/images/swebench_verified.yaml:15-35`, worker rootless Docker cache
static_repro: Use the current smoke config to select `django__django-10097`, inspect the runner and `swerex` code, then compare `docker image inspect` for `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` and `swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-django-1776-django-10097-latest-8be1c797d4885b41` on `swe_dev`, `swe_dev2`, and worker rootless Docker.
impact: A promotion or preflight that records only the `swebench/*` tag can pass the worker while using the wrong image. On worker, both the official-looking `swebench/sweb.eval...django-10097:latest` tag and the exact `swerex-prebuilt:...8be1...` tag resolve to the wrapper image ID `sha256:3e38b9278651...`; the official base image ID `sha256:cf945d25ceb6...` is absent. This hides an eval-time blocker and makes future digest promotion non-reproducible.
runner_need: Both roles are needed, but for different phases. The SWE-agent phase declares `deployment.image=docker.io/swebench/sweb.eval.x86_64.django_1776_django-10097:latest`, then `swerex` reuses/runs the exact wrapper `swerex-prebuilt:...8be1...` when it exists; if that wrapper is missing, `swerex` falls back to building it from the official base and fails under `pull=never` when the base is not local. The suite then runs `python -m swebench.harness.run_evaluation` by default, which uses the official `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` eval image identity.
minimal_promotion_plan: Treat `django__django-10097` as a two-artifact image set before enabling required image preflight. Preferred digest path: from `swe_dev`, promote official eval base `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` with source ID `sha256:cf945d25ceb6...` and upstream RepoDigest `sha256:148894532806...` to a P0 digest ref such as `100.97.118.137:8555/swe-data-harness/swebench-django-10097-eval@sha256:<p0_digest>`; separately promote wrapper `swerex-prebuilt:...8be1...` with source ID `sha256:3e38b9278651...` to a P0 digest ref such as `100.97.118.137:8555/swe-data-harness/swerex-django-10097-wrapper@sha256:<p0_digest>`. Consumer verification should pull by digest, tag to the exact local refs required by the runner, inspect `Id` against the source IDs, and run a `--network none` smoke for each image before marking `image_ready`.
fallback_tar_plan: Existing shared fallback evidence covers only the wrapper: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar` contains `swerex-prebuilt:...8be1...`, and `django-1776-django_00.refs` line 1 lists the exact ref. It has no recorded sha256 sidecar, and it does not contain the official `swebench/sweb.eval...django-10097` base tag. A fallback-only plan therefore still needs a sha256 for the wrapper chunk and a newly exported official-base tar/sha from `swe_dev`, or it should use the P0 digest path for the official base.
blocker: Current artifacts are insufficient for required preflight. `swe_dev2` Docker cache has neither image; P0 has no `django-10097` SWE repositories; worker has the wrapper and an alias tag that masquerades as the official base; shared tar evidence has wrapper-only coverage without sha and no official-base tar. The JSON inventory also records `digest: ""` for both refs, so live inspect evidence must be used until the inventory is regenerated with RepoDigests and full IDs.
evidence: `swe_dev` inspect returns two distinct images: official base `swebench/sweb.eval.x86_64.django_1776_django-10097:latest` ID `sha256:cf945d25ceb69a16f1b06ccb38c5772592f6298698ca1a34b794019a4760dba7`, RepoDigest `sha256:148894532806828ddd882c6617387910c1be8d064e2496fbe7ec046a30eff6fb`, size `2811676744`; wrapper `swerex-prebuilt:...8be1...` ID `sha256:3e38b9278651320311a7f805a33f6736b4c09aac22d2ba699afc17f7d0ce0c95`, no RepoDigest, size `3252254988`. Worker rootless inspect returns both tags as the same wrapper ID `sha256:3e38b9278651320311a7f805a33f6736b4c09aac22d2ba699afc17f7d0ce0c95`, no RepoDigests. P0 `/v2/` returns HTTP 200, but catalog contains only `swe-data-harness/repo2env-pallets-click-f6299c4` and `swe-data-harness/terminal-bench-2-1-gcode-to-text`; proposed `swebench-django-10097-base` and `swerex-django-10097-wrapper` probes return HTTP 404.

COMMENT-READY guard change for #11/#6:
severity: HIGH
dedup: comment-on-#11/#6, not a new issue
fix: Add two required manifest rows or one grouped row with two checked identities for `swe_agent/django__django-10097`: `role: swebench_eval_base`, `local_ref: swebench/sweb.eval.x86_64.django_1776_django-10097:latest`, expected source ID/RepoDigest; and `role: swerex_wrapper`, `local_ref: swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-django-1776-django-10097-latest-8be1c797d4885b41`, expected source ID plus P0 digest or fallback tar/sha. Preflight must fail `identity_mismatch` when a `swebench/*` tag resolves to the wrapper ID, and it must not consider worker tag presence alone sufficient.

### Cross-lane note

Read `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` for `django__django-10097`, `swebench/sweb.eval.x86_64.django_1776_django-10097`, `swerex-prebuilt`, and `#11` references. No peer finding in that ledger contradicted this runtime/image finding; this round is a concrete #11/#6 promotion-plan addendum, not a duplicate new issue.

### Round 5 command evidence

- `sed -n '1,520p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && sed -n '760,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` skill instructions before debugging: rc 0.
- Memory quick search for `django__django-10097`, `swerex-prebuilt`, `image-warmup-policy`, `57eb2ce`: rc 0, no relevant memory hit used.
- Active worktree status/HANDOFF/DRIVER read: rc 0; head `57eb2ce`; branch `feat/image-warmup-policy` initially clean against origin for this lane.
- Read `manifests/suite.example.yaml`, SWE-agent shared entrypoint, and config selection for `django__django-10097`: rc 0 for the config/suite reads; one earlier combined SSH read ended rc 255 after printing useful suite/run.sh context, so it was replaced by bounded reads.
- Read `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_swe_agent.sh`: rc 0; it execs `run_swebench_verified.sh`.
- Read `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified.sh`: rc 0; lines 116-160 run SWE-agent then `swebench.harness.run_evaluation` unless `SWEBENCH_SKIP_EVAL=1`.
- Read `swerex/deployment/docker.py` lines 180-330: rc 0; wrapper reuse occurs before official-base fallback build.
- `ssh swe_dev2 docker image inspect official-base swerex-wrapper --format ...`: rc 1; both refs missing from `swe_dev2` Docker cache.
- `ssh swe_dev docker image inspect official-base swerex-wrapper --format ...`: rc 0; official base and wrapper are distinct images with IDs/digest listed above.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect official-base swerex-wrapper --format ...'`: rc 0; both tags resolve to wrapper ID `sha256:3e38b9278651...`.
- P0 read-only probe from `swe_dev2` for `/v2/`, `_catalog?n=200`, and two candidate `django-10097` tag-list URLs: rc 0; HTTP 200 for health/catalog, HTTP 404 for both candidate repos.
- Shared tar/read-only search under `swe/swerex_images`, `agentic-foundation-model-bench`, `swe-data-harness`, and `shared_bench`: rc 0; found wrapper chunk tar(s), no direct official-base tar evidence.
- `_all_refs.txt` grep for `django-10097`/`8be1...`: rc 0; exact wrapper ref present, no official base ref printed.
- `tar -xOf .../django-1776-django_00.tar manifest.json | grep ...`: rc 0; manifest contains exact `swerex-prebuilt:...8be1...` only.
- `find .../swe/swerex_images -maxdepth 3` for `django-1776-django_00` sidecars: rc 0; found `.tar`, `.refs`, `.done`, no sha256 sidecar.
- `grep` in `manifests/images/swebench_verified.yaml`, `reports/swe_dev_docker_cache_inventory_20260626.json`, and this ledger for `django__django-10097`/image refs: rc 0.
- Parsed `reports/swe_dev_docker_cache_inventory_20260626.json` for `django-10097`: rc 0; two refs present but both `digest` fields empty.
- Read SWE-bench harness code pointers on `swe_dev` for namespace/instance-image construction: rc 0; default namespace is `swebench` and `TestSpec.instance_image_key` builds `swebench/sweb.eval...` refs.
- Cross-lane grep of `hunt-runner-results.md` for this exact task/image/#11 terms: rc 0; no contradicting exact finding printed.
- `git status --short --branch && git rev-parse --short HEAD` in worktree: rc 0; showed unrelated changes in `hunt-runner-results.md`, `scripts/test_agentic_bench_images.py`, and `scripts/__pycache__/`; this lane did not touch them.

## Next loop target

Next runtime/image subdomain: after #11/#6 comments are consumed, check whether any other non-OpenHands selected SWE-bench smoke task already has both a correct official base digest path and an exact wrapper tar/sha. Prefer a task whose worker `swebench/*` tag does not alias to the wrapper, otherwise keep promotion blocked until identity fields are enforced.

## Round 6 Terminal-Bench 2.1 swe_dev cache vs shared fallback audit

Scope held for this loop:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then `_coordination/20260625_harbor_bench/HANDOFF.md`.
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, observed head `a1984bf`.
- Wrote only this runtime/images ledger. No production code, manifests, tests, Docker push/pull/load, benchmark execution, or model execution.
- New evidence source: `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json` vs `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images`.

COMMENT-READY for #6/#8/#11 dedup: TB2.1 full image readiness is still partial; do not treat `manifest.jsonl` or `missing_shard` files as transport-complete source of truth
severity: HIGH
dedup: comment-on-#6 for image warmup manifest coverage and tar fallback gating; comment-on-#8 for worker transport/readiness context; not #11 because this is missing transport/sha coverage, not an identity-lineage mismatch. This confirms and sharpens runtime Round 2 rather than opening a new issue.
location: `manifests/images/terminal_bench_2_1.yaml:11-16`, `manifests/images/terminal_bench_2_1.yaml:18-43`, `manifests/suite.example.yaml:271-296`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json:10152-10158`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json:10280-10286`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json:10440-10446`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl:20-34`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl:86`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/shards/missing_shard_1.txt:9`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/shards/missing_shard_2.txt:7-11`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/shards/missing_shard_2_retry.txt:4-8`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/failures.log:1-4`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/bench_tb21_prebuild_missing_final_20260603_1546.log:1-2`
static_repro: Compare the 89 `tb2-offline/*:20260425` tags in the swe_dev cache inventory with the shared fallback tree. The shared tree has 50 `.tar` files, one `headless-terminal.tar.gz`, zero sha sidecars, 86 `manifest.jsonl` rows, 64 unique manifest tasks, and 14 unique manifest tasks whose declared archive path is absent. The shard files list 35 unique tasks; 20 already have tar fallbacks and 15 still have no tar fallback, while all 35 are present in swe_dev cache.
impact: A full TB2.1 image manifest generated from stale text artifacts can either overstate fallback coverage or understate recovered coverage. If it trusts `manifest.jsonl`, 14 required rows would point at nonexistent tar files. If it trusts `missing_shard_*.txt`, it will mark already-recovered images such as `gcode-to-text` and `fix-git` as missing, while still not producing usable tar coverage for tasks such as `install-windows-3.11`, `mteb-retrieve`, `reshard-c4-data`, and `sam-cell-seg`. Current worker image-smoke preflight is safe only because it is one-task `gcode-to-text`; it is not evidence for full TB2.1 readiness.
fix: Generate the TB2.1 image manifest from a reconciled table, not directly from `manifest.jsonl` or `missing_shard_*.txt`. Use the 89 swe_dev cache refs as the candidate set, join by exact task id against actual tar file existence, compute/record `fallback_tar_sha256` for each present tar, mark no-tar rows explicitly as `missing_transport`, and keep them out of required worker preflight until either a P0 digest plus consumer smoke or a verified fallback tar/sha exists. Treat `missing_shard_*.txt`, `failures.log`, and `bench_tb21_prebuild_missing_final_*.log` as diagnostic inputs only.
evidence: The inventory file contains cache-only refs with no shared tar, for example `tb2-offline/install-windows-3.11:20260425` at lines 10152-10158, `tb2-offline/nginx-request-logging:20260425` at lines 10280-10286, and `tb2-offline/reshard-c4-data:20260425` at lines 10440-10446. The shared tree count command returned `tar=50`, `targz=1`, `sha=0`, `missing_shard=6`. Parsed comparison returned `tb_cached=89`, `tar=50`, `cached_no_tar_count=39`, `manifest_rows=86`, `manifest_unique=64`, `manifest_unique_without_tar=14`, and `duplicate_tasks=22`. Current worker read-only cache list has only five TB2 tags, all in the tar subset: `compile-compcert`, `dna-insert`, `gcode-to-text`, `headless-terminal`, and `llm-inference-batching-scheduler`.

No new ISSUE-READY block filed from this loop:

- The current enabled one-command worker image-smoke row is `terminal_bench_2_1_image_smoke`, and it intentionally selects `TB_TASK_IDS=gcode-to-text` with `TB21_IMAGE_ARCHIVE=.../gcode-to-text.tar`; dry-run shows the preflight command uses `manifests/images/terminal_bench_2_1.yaml` with `--load-fallback --run-smoke --json` and the row has a verified fallback sha in `manifests/images/terminal_bench_2_1.yaml:26-31`.
- The disabled full `terminal_bench_2_1` row has `image_policy: required` but `enabled: false` at `manifests/suite.example.yaml:271-280`, so a current default suite run does not claim full TB2.1 image readiness.
- The false-full-readiness risk is real for the next manifest-generation step, but it is already covered by #6 and previous runtime Round 2; this loop adds concrete file/path/line evidence for the 89-vs-50-vs-missing-shard reconciliation.

Cross-lane check:

- Read `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` for TB2.1 references. It independently confirms the historical #6/#7/#8 image-preflight and selection issues and does not contradict this runtime finding.
- Runner-results focuses on parser/native-result observability. This runtime update is limited to Docker image/fallback readiness and should stay as a #6/#8 comment, not a runner parser issue.

### Round 6 command evidence

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` skill instructions; first cached path probe failed because the listed plugin hash was stale, then `find .../systematic-debugging/SKILL.md | xargs sed` succeeded: rc 0.
- Memory quick search for TB2.1 terms in `MEMORY.md`: rc 0, no hits used.
- Active worktree status and required file/dir existence check: rc 0; branch `feat/image-warmup-policy`, head `a1984bf`; unrelated local changes observed in `scripts/test_agentic_bench_images.py` and `scripts/__pycache__/`.
- Parsed `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`: rc 0; `image_count=1320`, `tb2_offline=89`.
- Listed shared fallback tree and counts: rc 0; `tar=50`, `targz=1`, `sha=0`, `missing_shard=6`.
- Read `manifests/images/terminal_bench_2_1.yaml:1-46` and `manifests/suite.example.yaml:271-296`: rc 0.
- Read shared `manifest.jsonl`, `missing_shard_1.txt`, `missing_shard_2.txt`, `missing_shard_2_retry.txt`, `failures.log`, and `bench_tb21_prebuild_missing_final_20260603_1546.log`: rc 0.
- Set-diff script for swe_dev cache vs shared tar and missing shard files: rc 0; printed `tb_cached 89`, `tar 50`, `missing_unique 35`, `cached_no_tar_count 39`, `missing_with_tar 20`.
- Read suite/image checker code paths in `scripts/agentic_bench_suite.py` and `scripts/agentic_bench_images.py`: rc 0.
- Dry-run `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only terminal_bench_2_1`: rc 0, selected no runs because full row is disabled.
- Dry-run `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only terminal_bench_2_1_image_smoke --model-profile dev_proxy_gpt54mini_8130`: rc 0, printed the worker image preflight command and `TB_TASK_IDS=gcode-to-text`; no Docker action executed.
- Worker read-only cache list via explicit worker-j9jjd endpoint and `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`: command wrapper rc 0; printed five `tb2-offline/*` tags, no push/pull/load/run.
- First manifest-vs-files Python script printed key stats but exited rc 1 due an output-format KeyError after printing; rerun corrected script rc 0 with exact missing archive lines and duplicate task lines.
- Cross-lane grep of `hunt-runtime-images.md` and `hunt-runner-results.md` for TB2.1/#6/#8/#11 terms: rc 0.

## Next loop target

Next runtime/image subdomain: when manifest generation starts, audit the generated TB2.1 rows before any worker preflight. Required checks: exactly one row per selected task id, no row from stale `manifest.jsonl` without an existing tar or P0 digest, `fallback_tar_sha256` present for every tar row, and explicit `missing_transport` rows for the 39 swe_dev-cache-only tasks.
## Round 7 generated manifest audit: TB2.1 cache manifest and SWE django10097 probe

Scope held for this loop:

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then `_coordination/20260625_harbor_bench/HANDOFF.md`.
- Active worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, observed head `9dffbe8`.
- Wrote only this runtime/images ledger. No production code, manifests, tests, Docker push/pull/load, benchmark execution, or model execution.
- Audited generated manifests: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` and `manifests/images/swebench_verified_django10097.yaml`.

No new ISSUE-READY block filed from this loop.

The generated manifests are useful audit/promotion inputs and do not introduce a distinct new runtime bug. They expose the known #6/#8/#11 blockers more concretely: TB2.1 now has exactly one generated row per swe_dev cache task and no stale `manifest.jsonl`-only rows, while SWE django10097 has the right two-artifact identity split and should fail current worker preflight via `identity_mismatch` rather than tag-presence fake pass.

COMMENT-READY for #6/#8: `terminal_bench_2_1_swe_dev_cache.yaml` is complete as a cache inventory, but still not a full offline transport manifest
severity: HIGH
dedup: comment-on-#6 for image warmup/fallback sha gating; comment-on-#8 only for worker readiness context. This is a refinement of Round 6, not a new issue.
location: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1-16`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:17-28`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:465`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:657`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:897`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:989-1084`, `manifests/bench_registry.yaml:51-54`, `manifests/images/README.md:24-29`, `scripts/agentic_bench_images.py:182-210`, `scripts/agentic_bench_images.py:490-498`, `scripts/agentic_bench_images.py:519-521`, `scripts/agentic_bench_images.py:730-734`
static_repro: Parse the generated TB2.1 manifest and compare it to `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`. It has `rows=89`, `cache_tb=89`, `unique_refs=89`, `dups=0`, `missing_from_manifest=0`, and `extra_rows=0`. It therefore fixed the stale-row/duplicate-row shape from the old shared `manifest.jsonl` source. The remaining transport gap is explicit: `with_tar=50`, `with_p0=0`, `no_transport=39`, `req_no_transport=39`, `no_sha=50`, `tar_missing=0`, `required_false=0`, `id_missing=0`, and `repo_digest_missing=89`.
impact: A current worker full preflight against this manifest should fail closed, not fake pass, because all 89 rows are `required: true`, current worker has only five TB2 images, and missing required rows become `status=missing` with rc 1. The manifest is still not an offline reproducibility artifact: 39 required rows have neither P0 digest nor fallback tar, and 50 fallback tar rows are marked `oci_tar_unverified_sha` with no `fallback_tar_sha256`. If run with `--load-fallback`, the checker currently permits `sha256_status in {match, not_configured}`, so it can load unverified tars for those 50 rows; that behavior is the same #6 fallback-sha blocker already tracked.
fix: Keep this manifest as audit-only until every required row has either a digest-pinned internal `image_ref` that has passed worker consumer smoke or a `fallback_tar` plus `fallback_tar_sha256`. For #6, tighten the checker/manifest contract so required fallback loads refuse `sha256_status=not_configured` unless an explicit `allow_unverified_fallback` debug flag is present. For the 39 `fallback_status: missing_shared_tar` rows, keep them required only in an audit manifest; do not wire them into full worker preflight until P0 digest or tar/sha transport exists.
evidence: The manifest header records `status: materialized_from_swe_dev_cache_partial_tar_coverage`, `cache_image_count: 89`, `shared_tar_count: 50`, and blockers `p0_digest_refs_not_published_for_all_tb2_tasks`, `shared_tar_coverage_is_50_of_89_cached_tasks`, and `fallback_tar_sha256_not_recorded_for_generated_rows`. Example no-transport required rows are `install-windows-3.11` at line 465, `nginx-request-logging` at line 657, `reshard-c4-data` at line 897, and `write-compressor` at line 1077. Current worker read-only cache list shows only five TB2 tags: `compile-compcert`, `dna-insert`, `gcode-to-text`, `headless-terminal`, and `llm-inference-batching-scheduler`.

COMMENT-READY for #11/#6: `swebench_verified_django10097.yaml` encodes the intended identity failure, but still needs transport before promotion
severity: HIGH
dedup: comment-on-#11 for correct identity-mismatch behavior; comment-on-#6 for missing P0/fallback transport. This is not a new issue.
location: `manifests/images/swebench_verified_django10097.yaml:12-17`, `manifests/images/swebench_verified_django10097.yaml:18-29`, `manifests/images/swebench_verified_django10097.yaml:31-42`, `manifests/bench_registry.yaml:56-59`, `manifests/images/README.md:26-29`, `scripts/agentic_bench_images.py:474-523`, `scripts/agentic_bench_images.py:730-734`
static_repro: Parse `manifests/images/swebench_verified_django10097.yaml`. It has exactly two required rows: `swebench_django10097_eval_base` with local ref `swebench/sweb.eval.x86_64.django_1776_django-10097:latest`, expected image ID `sha256:cf945d25...`, and source repo digest `sha256:148894...`; and `swebench_django10097_swerex_wrapper` with local ref `swerex-prebuilt:...8be1...`, expected image ID `sha256:3e38b927...`, and wrapper tar path `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar`. Current worker read-only image list shows both the `swebench/*` tag and the `swerex-prebuilt:*` tag resolving to short ID `3e38b9278651`.
impact: This manifest should fail the current worker correctly with `identity_mismatch` for the official eval-base row, rather than fake passing because the tag exists. That closes the #11 fake-green class for this selected task. It is still not a promotion-ready transport manifest: the eval-base row has no `image_ref` and no fallback tar, and the wrapper row has a fallback tar but no `fallback_tar_sha256` or repo digest. A passing swe_dev check only proves source identity; it does not make the active worker reproducible offline.
fix: Keep the django10097 manifest as an identity probe until both artifacts have transport. Required promotion rows need either P0 digest refs plus consumer pull/run-smoke or fallback tar paths with sha256. Specifically, export or push the official eval base separately from the wrapper, add `fallback_tar_sha256` for `django-1776-django_00.tar` if using it, and keep expected image IDs/source repo digests so worker tag aliases continue to fail as identity mismatches.
evidence: Manifest blockers explicitly list `p0_digest_refs_not_published`, `worker_current_swebench_tag_aliases_to_wrapper_identity`, `wrapper_fallback_tar_sha256_not_recorded`, and `official_base_fallback_tar_missing`. `manifests/images/README.md:27` states this manifest is expected to pass on swe_dev and fail with `identity_mismatch` on the current worker until the official base is staged correctly. Worker read-only cache evidence matches that expected failure: `swerex-prebuilt:...8be1...` and `swebench/sweb.eval...django-10097:latest` both show image ID prefix `3e38b9278651`.

Cross-lane check:

- Read `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` for #6/#8/#11 and generated-manifest terms. It confirms the existing #6/#8 preflight and rootless-readiness issues and does not contradict the manifest audit.
- Runner-results remains parser/native-output focused; this round is runtime/image transport and identity evidence only.

### Round 7 command evidence

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` skill instructions: rc 0.
- Memory quick search for `terminal_bench_2_1_swe_dev_cache`, `swebench_verified_django10097`, TB2.1, and django10097 terms: rc 0, no hits used.
- Active worktree/file existence check: rc 0; branch `feat/image-warmup-policy`, observed head `9dffbe8`; generated manifests exist; an unrelated untracked `_coordination/20260625_harbor_bench/inventory/tb2_shared_tars_sha256_20260626.tsv.tmp` was present and not touched.
- First manifest line-number read command had a shell `printf --` option error and exited rc 2 before printing useful manifest content; rerun with `printf "%s\n"` succeeded rc 0.
- Static manifest parser for TB2.1 and SWE django10097: rc 0; printed the row/transport/identity counts quoted above.
- Read manifest examples, no-transport line examples, and SWE django10097 rows with `nl -ba`/`grep`: rc 0.
- Read checker semantics in `scripts/agentic_bench_images.py:182-210`, `474-523`, and `730-737`: rc 0.
- Read `manifests/bench_registry.yaml:42-62` and `manifests/images/README.md:20-32`: rc 0.
- Worker read-only cache list through explicit worker-j9jjd endpoint with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`: rc 0; no Docker inspect/run/pull/load, only `docker image ls`.
- Two attempted `--skip-docker --json` parse commands were malformed because here-doc stdin consumed the pipe; they exited rc 1 and rc 120 with BrokenPipe, no file or Docker mutation. Corrected `python -c` pipe runs for TB and SWE both exited rc 0 and returned all rows as `unchecked`.
- Cross-lane grep over runtime and runner ledgers for generated manifests/#6/#8/#11: rc 0.

## Next loop target

Next runtime/image subdomain: audit the static-lint gap for generated image manifests. A useful next check is whether the repo should add a manifest lint mode that fails audit manifests with required rows lacking both digest and verified fallback sha, while keeping runtime worker preflight responsible for Docker presence/identity/smoke.

### Orchestrator reconciliation after `588006f`

After this Round 7 audit was written, the orchestrator computed and committed `fallback_tar_sha256` for all 50 shared TB2.1 tar rows in `588006f Verify terminal bench fallback shas`. The Round 7 `no_sha=50` observation is therefore superseded for current head. The remaining #6/#8 transport blocker is the 39 required TB2 rows with no P0 digest and no shared fallback tar, plus the need to publish/verify registry digests before worker full preflight.

## Round 8 - Static image-manifest lint gate audit (2026-06-26)

Scope held: runtime/images lane only. No Docker push/pull/load/run, no benchmark/model execution, no production code/manifest/test edits. Read current generated TB2/SWE manifests, current `agentic_bench_images.py` semantics, suite `image_policy` behavior, and runner-results dedup evidence. Existing modified production files in the worktree were treated as unowned read-only state.

COMMENT-READY for #6/#11: static offline-transport lint now exists and fails the generated audit manifests closed; use it as the promotion gate before enabling required worker preflight

dedup: comment-on-#6 for offline transport/P0-or-tar gating. comment-on-#11 only for keeping identity verification in runtime preflight after transport lint passes. Not a new ISSUE-READY bug because the current worktree already has a dedicated `lint --require-offline-transport` mode and it returns nonzero on the current TB2/SWE promotion manifests. Not #8 except that worker daemon/rootless readiness remains a separate runtime check.

location: `scripts/agentic_bench_images.py:318-377`, `scripts/agentic_bench_images.py:749-753`, `scripts/agentic_bench_images.py:799-809`, `scripts/agentic_bench_suite.py:602-700`, `scripts/agentic_bench_suite.py:988-1000`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:499`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:680-1124`, `manifests/images/swebench_verified_django10097.yaml:18-42`, `manifests/bench_registry.yaml:51-59`, `manifests/images/README.md:105-115`, `manifests/suite.example.yaml:271-289`.

static_repro:
- `python3 scripts/agentic_bench_images.py validate --registry manifests/bench_registry.yaml` is structural only: it returned rc 0 with `manifests=9 images=104 required_images=94 missing_manifests=0`, even though generated promotion manifests still lack complete offline transport.
- `python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --require-offline-transport` returned rc 1 with `images=89 required=89 missing_offline_transport=39`. The failing rows are the 39 `fallback_status: missing_shared_tar` TB2 cache rows, for example `tb2_install_windows_3_11` at line 499 and the contiguous missing-shared-tar block from `tb2_mteb_retrieve` through `tb2_write_compressor` at lines 680-1124.
- `python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/swebench_verified_django10097.yaml --require-offline-transport` returned rc 1 with `images=2 required=2 missing_offline_transport=2`: both `swebench_django10097_eval_base` and `swebench_django10097_swerex_wrapper` still lack either a digest-pinned internal registry ref or configured fallback sha.
- `scripts/agentic_bench_suite.py` builds runtime `check` commands from `image_policy` and executes them only when policy is required. That path checks worker Docker cache/pull/load/identity/smoke, not static transport completeness. This is the right separation: lint should block promotion; runtime preflight should verify the selected worker state.

impact: A warm worker can still pass runtime image presence/identity for rows that are not reproducible from P0 digest or verified fallback tar, so promotion should not rely on `validate` or worker cache checks alone. The current static lint closes that class when invoked explicitly, but it is not the same as suite `image_policy: required`. Before wiring generated TB2/SWE audit manifests into a required suite row, the orchestrator/CI must run lint and require zero `missing_offline_transport`.

fix: Add the static gate to the promotion workflow: for every generated manifest that might be marked P0-ready or suite-required, run `python3 scripts/agentic_bench_images.py lint --image-manifest <manifest> --require-offline-transport` and require rc 0. Keep suite worker preflight on `check` so it can still verify local Docker presence, expected image IDs/repo digests, optional pull/load-fallback, and smoke. If this needs to be one command, add a registry-level lint wrapper that iterates selected `bench_registry.yaml` rows and applies the same per-manifest lint contract; do not overload `validate`, because it is currently useful as a structural manifest inventory check.

cross-lane check: grep over `hunt-runner-results.md` for #6/#8/#11/static-lint terms returned rc 0. Runner-results confirms image-preflight failures are currently normalized on the runner side, but it does not contradict this runtime/image conclusion. This loop adds a promotion-gate comment, not a parser/runner issue.

commands/evidence:
- Memory quick search for `static image-manifest lint`, generated manifest names, `fallback_tar_sha256`, and `agentic_bench_images.py`: rc 0, no relevant hits used.
- Remote status/read command in the active worktree: rc 0; branch `feat/image-warmup-policy`, head `25820b4`, with unowned modified `scripts/agentic_bench_images.py`, `scripts/test_agentic_bench_images.py`, and untracked `scripts/__pycache__/`.
- Static manifest parser: rc 0; current generated manifests are 89 TB2 rows and 2 SWE rows; TB2 has 50 fallback sha rows and 39 required rows without digest/sha transport; SWE has 2 required rows without digest/sha transport.
- Source reads for `agentic_bench_images.py`, `agentic_bench_suite.py`, `manifests/bench_registry.yaml`, `manifests/images/README.md`, `manifests/suite.example.yaml`, and tests: rc 0.
- `validate`/`lint` combined command: outer rc 0; inner `VALIDATE_RC=0`, `TB_LINT_RC=1`, `SWE_LINT_RC=1`.
- Cross-lane dedup grep over runtime and runner ledgers: rc 0.

Next runtime/image subdomain: after the promotion workflow consumes this lint gate, re-check whether a registry-level lint wrapper is needed for selected bench-registry policies, then return to concrete P0 digest population for the 39 TB2 missing-shared-tar rows and the two django10097 SWE rows.

## Round 9 - Registry-level static lint gate audit (2026-06-26)

Scope held: runtime/images lane only. No Docker push/pull/load/run, no benchmark/model execution, no production code/manifest/test edits. Read current `bench_registry.yaml`, image CLI semantics, suite image-preflight behavior, and runner-results dedup evidence.

COMMENT-READY for #6/#11: add a registry-selected static lint gate to the promotion workflow; do not rely on `validate`, `list`, or suite `image_policy: required` for transport completeness

dedup: comment-on-#6 for offline image transport gating and generated-manifest promotion readiness. comment-on-#11 for preserving runtime identity checks after transport lint passes. Not a new ISSUE-READY bug because Round 8 already established the core static lint versus runtime preflight split; this loop narrows the registry-level wrapper/promotion command. Not #8 except that worker Docker health remains a later runtime preflight input.

location: `scripts/agentic_bench_images.py:318-377`, `scripts/agentic_bench_images.py:626-669`, `scripts/agentic_bench_images.py:739-753`, `scripts/agentic_bench_images.py:778-809`, `scripts/agentic_bench_suite.py:602-700`, `scripts/agentic_bench_suite.py:1062-1210`, `manifests/bench_registry.yaml:34-79`, `manifests/images/README.md:24-29`, `manifests/suite.example.yaml:271-289`.

static_repro:
- `python3 scripts/agentic_bench_images.py validate --registry manifests/bench_registry.yaml --json` and `python3 scripts/agentic_bench_images.py list --registry manifests/bench_registry.yaml --json` both returned rc 0 and identical `agentic_bench.registry_validation.v1` payloads with `manifests=9`, `images=104`, `required_images=94`, and `missing_manifests=0`. They prove structural reachability only.
- `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only terminal_bench_2_1_image_smoke` returned rc 0; its required `image_preflight.check_argv` is `python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1.yaml --asset-root ... --docker-host unix:///tmp/rl/run/docker.sock --load-fallback --run-smoke --json`, with no `lint` token. Suite required preflight can therefore verify worker runtime state while still skipping the static transport-contract gate.
- A static registry-selection probe over policies starting `required_for_` or `audit_manifest_for_` selected `p0_registry_smoke`, `repozero_py2js`, `terminal_bench_2_1_swe_dev_cache`, and `swebench_verified_django10097_identity_probe`. Per-manifest lint passed the first two and failed TB2 (`missing_offline_transport=39`) plus SWE django10097 (`missing_offline_transport=2`), yielding `STATIC_GATE_RC=1`.

impact: If the orchestrator treats registry `validate`, `list`, or suite `--image-preflight-only` as the promotion gate, a warm worker can still pass runtime `check` for cached images without proving that the manifest is reproducible from a digest-pinned P0 ref or verified fallback tar. The current per-manifest lint prevents that only when explicitly composed over the registry rows selected for promotion/audit.

fix: Keep `validate`/`list` structural and keep suite image preflight as runtime worker verification. Add either a tiny registry-level CLI wrapper or a documented CI/orchestrator gate that runs per-manifest lint over selected registry policies before any manifest is renamed P0-ready or wired into required suite execution. Exact current promotion-gate command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path
import subprocess
import sys
import yaml
registry = Path("manifests/bench_registry.yaml")
config = yaml.safe_load(registry.read_text())
selected_prefixes = ("required_for_", "audit_manifest_for_")
selected = [row for row in config["image_manifests"] if str(row.get("policy", "")).startswith(selected_prefixes)]
failed = []
for row in selected:
    manifest = registry.parent / row["path"]
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/agentic_bench_images.py",
            "lint",
            "--image-manifest",
            str(manifest),
            "--require-offline-transport",
        ],
        check=False,
    )
    if proc.returncode:
        failed.append(row["id"])
if failed:
    print("image manifest promotion gate failed:", ", ".join(failed), file=sys.stderr)
    sys.exit(1)
PY
```

If promoted into the CLI, the equivalent should be a registry-level command such as `python3 scripts/agentic_bench_images.py lint-registry --registry manifests/bench_registry.yaml --policy-prefix required_for_ --policy-prefix audit_manifest_for_ --require-offline-transport`, returning nonzero when any selected manifest has required rows without internal digest refs or fallback sha.

cross-lane check: `hunt-runner-results.md` has no contradictory registry-level lint finding. Its current image-preflight comments focus on runner result normalization and image-preflight failure classification, so this remains a #6/#11 runtime-image promotion-gate comment rather than a runner/parser issue.

commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, then `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` skill instructions: rc 0.
- Memory quick search for registry-level lint, bench-registry lint, `require-offline-transport`, and generated manifest names: rc 0, no relevant hits used.
- Remote status/file inventory: rc 0; branch `feat/image-warmup-policy`, observed head `ccf74ac`, ledger length 593 before append.
- Read current `agentic_bench_images.py`, `agentic_bench_suite.py`, registry/readme/suite excerpts, and grep for lint/preflight symbols: rc 0.
- Registry `validate`/`list` JSON comparison: rc 0; payloads identical and structural-only.
- First static selected-policy probe had a quoting bug in a diagnostic f-string and printed `STATIC_GATE_RC=1`; rerun with `.format()` succeeded as a probe and printed inner `STATIC_GATE_RC=1` with the selected failing manifests.
- Suite dry-run probe for `terminal_bench_2_1_image_smoke`: rc 0; `contains_lint=False` in required preflight `check_argv`.
- Registry policy bucket table: rc 0; selected promotion/audit rows are `p0_registry_smoke`, `repozero_py2js`, `terminal_bench_2_1_swe_dev_cache`, and `swebench_verified_django10097_identity_probe`.
- Cross-lane grep and `_execute_image_preflights()` source read: rc 0.

Next runtime/image subdomain: after registry-selected lint is wired into orchestration, re-check the concrete missing transports: publish/record P0 digests or verified fallback shas for the 39 TB2 rows and the two django10097 SWE rows, then run worker runtime `check` only after the static gate is green.

## Round 10 - Concrete transport population audit (2026-06-26)

Scope held: runtime/images lane only. Worked on `swe_dev` in the active worktree. No production code/manifest/test edits. No Docker push/load/run. Docker/image evidence below comes from saved swe_dev identity inventory plus read-only file/tar/hash inspection. The only write in this loop is this ledger append.

COMMENT-READY for #6/#11: populate the 41 missing transports from known swe_dev sources; no new distinct bug found

dedup: comment-on-#6 for image transport population and lint-registry gating. comment-on-#11 for preserving the django10097 official-base versus wrapper identity split. Not #8 except for later worker pull/readiness validation after transport is populated.

Current lint gate:
- `lint-registry` on the TB2+SWE promotion slice returns rc 1 as expected: `selected_manifests=2`, `required_images=91`, `required_with_fallback_sha=50`, `required_with_digest_ref=0`, `required_without_offline_transport=41`.
- TB2 accounts for 39 missing transports; SWE django10097 accounts for 2 missing transports.

### TB2 39-row transport matrix

All 39 TB2 missing rows are exact swe_dev cache hits and can be exported to verified fallback tar+sha from swe_dev. None currently has a shared tar at the expected `terminalbench2.1/prebuilt-images/20260425/<task>.tar` path, and none has a source repo digest in the identity inventory. P0 digest push is therefore not required to make `lint-registry` pass, but it is preferable for scale and should be kept alongside fallback tar while worker-j9jjd registry pulls remain less reliable than fallback loading.

Counts:
- `missing_rows=39`
- `cache_present=39`
- `identity_match=39`
- `expected_tar_exists=0`
- `with_repo_digests=0`
- approximate Docker virtual size total: `76.01GB`

| category | count | rows | minimum transport to pass lint | preferred scale transport |
|---|---:|---|---|---|
| TB2 small, `<1GB` | 26 | `tb2_nginx_request_logging(269MB)`, `tb2_openssl_selfsigned_cert(229MB)`, `tb2_overfull_hbox(531MB)`, `tb2_password_recovery(396MB)`, `tb2_path_tracing_reverse(453MB)`, `tb2_polyglot_c_py(560MB)`, `tb2_polyglot_rust_c(995MB)`, `tb2_portfolio_optimization(613MB)`, `tb2_protein_assembly(180MB)`, `tb2_pypi_server(321MB)`, `tb2_query_optimize(454MB)`, `tb2_raman_fitting(229MB)`, `tb2_regex_chess(197MB)`, `tb2_regex_log(298MB)`, `tb2_rstan_to_pystan(206MB)`, `tb2_sanitize_git_repo(466MB)`, `tb2_schemelike_metacircular_eval(180MB)`, `tb2_sparql_university(303MB)`, `tb2_sqlite_db_truncate(229MB)`, `tb2_sqlite_with_gcov(311MB)`, `tb2_train_fasttext(874MB)`, `tb2_tune_mjcf(529MB)`, `tb2_video_processing(793MB)`, `tb2_vulnerable_secret(478MB)`, `tb2_winning_avg_corewars(736MB)`, `tb2_write_compressor(996MB)` | `docker save` each exact `tb2-offline/*:20260425` ref to shared tar and record `sha256sum` | optional P0 digest after fallback smoke |
| TB2 medium, `1-3GB` | 9 | `tb2_install_windows_3_11(1.63GB)`, `tb2_mteb_retrieve(2.12GB)`, `tb2_path_tracing(1.1GB)`, `tb2_prove_plus_comm(1.46GB)`, `tb2_pytorch_model_cli(2.6GB)`, `tb2_qemu_alpine_ssh(1.96GB)`, `tb2_qemu_startup(1.96GB)`, `tb2_reshard_c4_data(2.52GB)`, `tb2_sam_cell_seg(1.13GB)` | `docker save` plus sha is sufficient | P0 digest preferred when worker pull path is healthy |
| TB2 large, `>3GB` | 4 | `tb2_multi_source_data_merger(6.2GB)`, `tb2_pytorch_model_recovery(19.2GB)`, `tb2_torch_pipeline_parallelism(11.3GB)`, `tb2_torch_tensor_parallelism(11GB)` | fallback tar+sha still sufficient for lint | P0 digest strongly preferred for repeated multi-worker runs; keep fallback until #8/rootless pull is resolved |

TB2 concrete next commands (not executed in this loop):

```bash
TB_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425
mkdir -p "$TB_ROOT"
while read -r slug ref expected_id; do
  out="$TB_ROOT/${slug}.tar"
  actual_id=$(docker image inspect --format '{{.Id}}' "$ref")
  test "$actual_id" = "$expected_id"
  docker save -o "$out" "$ref"
  sha256sum "$out" > "$out.sha256"
done <<'EOF'
install-windows-3.11 tb2-offline/install-windows-3.11:20260425 sha256:2dad54561527cd64bf8d66c1e3eb555b8e9fbacee320fc578d8654b18c718b4d
mteb-retrieve tb2-offline/mteb-retrieve:20260425 sha256:153b4c97f265aeb902b976c782cb47cefec872f20a31b5a5c1fa1fff644b3672
multi-source-data-merger tb2-offline/multi-source-data-merger:20260425 sha256:a961d25043559f9105b73e875bde5b2cc74b7ba7164bed2ef607fd82181fb8ad
nginx-request-logging tb2-offline/nginx-request-logging:20260425 sha256:e673cf94a1a34da48db6f93a1da618d4cc4aec3d6a4d113d79decd9d1647bab7
openssl-selfsigned-cert tb2-offline/openssl-selfsigned-cert:20260425 sha256:81d7d202b4704906a2e20a240011c44aa1049b49aa07a97a420b9ea1e8208bcb
overfull-hbox tb2-offline/overfull-hbox:20260425 sha256:a58256eef1e42facdb751f33fde0aa1cfd74719a8a420a2ebbf294308d975cbb
password-recovery tb2-offline/password-recovery:20260425 sha256:8a4a2ba55bfa3cf70f52b86ca6b297bfbb6cb3a082283422621e19a2efd2ce2f
path-tracing-reverse tb2-offline/path-tracing-reverse:20260425 sha256:d0aed029cc00c03b921dce59927f0812d8a17e9786e9095d334b8c6f6d889a83
path-tracing tb2-offline/path-tracing:20260425 sha256:49297f6044089e6cf96f9ff85626e3385c3bab32b5544a87a14077dbb4a34b36
polyglot-c-py tb2-offline/polyglot-c-py:20260425 sha256:34f1e78e9e233130df2102ff26672ff6efa598195b02a7e75f5e84809fdc25ec
polyglot-rust-c tb2-offline/polyglot-rust-c:20260425 sha256:a4b68e06827a967edee6ce3ee670bf5c7890987da211b37cb270e23279262d5d
portfolio-optimization tb2-offline/portfolio-optimization:20260425 sha256:1fca885f366e81e4e02a9ebb7336fe5eb212326e4510a507ee9f310d7115262f
protein-assembly tb2-offline/protein-assembly:20260425 sha256:c517a0dd99f0d98d6e95e849e21625f5f6fb7fec903fb15fcdb5f95d7942a757
prove-plus-comm tb2-offline/prove-plus-comm:20260425 sha256:c6b448d30a2cc3b2f45120f49ff26eefda18c4a487c1a386fae5aef312947b32
pypi-server tb2-offline/pypi-server:20260425 sha256:59e8830ad18e1f668d8fb97cd802161fd3e311524ba843d687699132df1f779f
pytorch-model-cli tb2-offline/pytorch-model-cli:20260425 sha256:cb27d97d931461dd0e6b72ce2c5eaf3e2f65e8d418b250a07f06ba6a0ff07ab2
pytorch-model-recovery tb2-offline/pytorch-model-recovery:20260425 sha256:3a67ac23a6097fbd4b6b9b8a78b06f11be5b8076568714c76ab2db5c5e684aa0
qemu-alpine-ssh tb2-offline/qemu-alpine-ssh:20260425 sha256:53987a31bb5e61cfbe1c04d6f860fb4a7a316c6302dac8f168fc92649e40bc1b
qemu-startup tb2-offline/qemu-startup:20260425 sha256:5814c86fde20d025cc06277e708ac9019bb3df9021af4d7421a3d11b45ecc849
query-optimize tb2-offline/query-optimize:20260425 sha256:b7888e243c3263b9e97669e777f8d7ef0196eb5ba964d8f804ca45d32aff19d9
raman-fitting tb2-offline/raman-fitting:20260425 sha256:3ed67c59f865cf947f06a60f64d0e673deef9c17dfc8a0a2c39288661920f432
regex-chess tb2-offline/regex-chess:20260425 sha256:f30f7083851614ac29c8d7c3f653e5e6382fb520e11fcb410765995f0efaf75d
regex-log tb2-offline/regex-log:20260425 sha256:5d9eae30a8a332f29f90f3e1957d872bb6c678e75aac94c0af6fa57c58fd3a77
reshard-c4-data tb2-offline/reshard-c4-data:20260425 sha256:3151b2371e33ed58430f3764533e499f8de126df7f71650e107c85fc263419d6
rstan-to-pystan tb2-offline/rstan-to-pystan:20260425 sha256:83b98640ec929691b076c253bd4bdc2364056793e729f382c1167e9afc8c6b88
sam-cell-seg tb2-offline/sam-cell-seg:20260425 sha256:dbc5dfcc120f219e687090b0dd55f66dca019428d92bf901690eb31761db7152
sanitize-git-repo tb2-offline/sanitize-git-repo:20260425 sha256:6fb3909be2d39ded79f422fc5c8c8669ef02e91680de764630926df74d2bdba1
schemelike-metacircular-eval tb2-offline/schemelike-metacircular-eval:20260425 sha256:5b61010656231f3f13b912c5e4433898efdc926b265e11fe2322813f84816c78
sparql-university tb2-offline/sparql-university:20260425 sha256:b7c23a59ae2253d3e45c8b9d3907bfcd9618242029e0eb6384d98c86f78b513d
sqlite-db-truncate tb2-offline/sqlite-db-truncate:20260425 sha256:62dc8a21604c405fa2a3fc361058993b1dd65b5917df05b9bb3a625605547283
sqlite-with-gcov tb2-offline/sqlite-with-gcov:20260425 sha256:3a0432d8b697baf97d51aca0c1d760eaf8f4583696b3861f8fd8ece48ac25dde
torch-pipeline-parallelism tb2-offline/torch-pipeline-parallelism:20260425 sha256:a014da66007d31e1fb4cc89ed91a0db2f6d99709698b3bfbfc0c12298d663ed0
torch-tensor-parallelism tb2-offline/torch-tensor-parallelism:20260425 sha256:7f0d9bce1454c702e1b7ed3bc8b086d96637cf5091e7d7ebfbfb8e0743436445
train-fasttext tb2-offline/train-fasttext:20260425 sha256:535d3a38744d6c75e60830a5bdf5e3447dbb301af52ca29ddb48e46c7e41f3b2
tune-mjcf tb2-offline/tune-mjcf:20260425 sha256:77711f5e27632be2f05d3f8c8e8a8bb8b6d9f78f956d67d5946a243b9b344475
video-processing tb2-offline/video-processing:20260425 sha256:470f922fb58f033ad22ba766310e58a914e3f45a546433c06d5e543f09f0872e
vulnerable-secret tb2-offline/vulnerable-secret:20260425 sha256:ed187ec82616ca051d93c8dfd84965d42d98ab9d016604cb67c42860b65f0a1b
winning-avg-corewars tb2-offline/winning-avg-corewars:20260425 sha256:3cb6bfd6a3a61962786d02979ce71349759473985e6c7ca294720beae1889cf0
write-compressor tb2-offline/write-compressor:20260425 sha256:868491de68eb60d48c8c1e0cb452ac10a73158c3857e997128d0a83f9b6843b8
EOF
```

For P0 follow-up after fallback artifacts exist, tag/push each source ref by immutable task slug and record the returned internal repo digest. Do not remove fallback tars until worker-j9jjd has reliable internal-registry pull+smoke for the same digest.

### SWE django10097 transport matrix

| row | current source identity | existing transport | minimum to pass lint-registry | preferred scale transport |
|---|---|---|---|---|
| `swebench_django10097_eval_base` | exact swe_dev cache match for `swebench/sweb.eval.x86_64.django_1776_django-10097:latest`; source image id `sha256:cf945d25...`; source repo digest `swebench/...@sha256:148894...`; cache size `2.81GB` | no fallback tar; no internal P0 digest ref | either `docker save` the exact eval-base image to shared tar and record sha, or tag/push it to P0 and record internal digest `image_ref` | P0 digest preferred because official eval base already has source repo digest; keep `source_image_id` and `source_repo_digest` so #11 identity checks remain strict |
| `swebench_django10097_swerex_wrapper` | exact swe_dev cache match for `swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-django-1776-django-10097-latest-8be1c797d4885b41`; source image id `sha256:3e38b927...`; cache size `3.25GB` | existing tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar`, size `7832649216` bytes; no sha sidecar | add `fallback_tar_sha256: 2ba506ed3e6ff4fdbb2ed54612b633ed782b4604a7b94a9d49173b0b2fb73275` | P0 digest optional later; existing tar+sha is enough for lint and fallback, but runtime `check --load-fallback` must still verify `source_image_id` |

SWE concrete next commands (not executed in this loop):

```bash
# Wrapper row: no Docker needed to satisfy static transport lint.
WRAP=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar
sha256sum "$WRAP"
# Record fallback_tar_sha256: 2ba506ed3e6ff4fdbb2ed54612b633ed782b4604a7b94a9d49173b0b2fb73275.
# Keep local_ref/source_image_id unchanged.

# Eval-base fallback route, sufficient for lint-registry.
SWE_OUT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runtime-images/swebench_verified/django10097
mkdir -p "$SWE_OUT"
REF=swebench/sweb.eval.x86_64.django_1776_django-10097:latest
EXPECTED=sha256:cf945d25ceb69a16f1b06ccb38c5772592f6298698ca1a34b794019a4760dba7
actual=$(docker image inspect --format '{{.Id}}' "$REF")
test "$actual" = "$EXPECTED"
docker save -o "$SWE_OUT/sweb.eval.x86_64.django_1776_django-10097.tar" "$REF"
sha256sum "$SWE_OUT/sweb.eval.x86_64.django_1776_django-10097.tar" > "$SWE_OUT/sweb.eval.x86_64.django_1776_django-10097.tar.sha256"

# Eval-base P0 route, preferred for scale once registry consumer smoke is healthy.
REG=100.97.118.137:8555
P0_TAG=$REG/swe-data-harness/swebench-django10097-eval-base:cf945d25
P0_REF=$REG/swe-data-harness/swebench-django10097-eval-base@sha256:<digest-from-push>
docker tag "$REF" "$P0_TAG"
docker push "$P0_TAG"
docker inspect --format='{{index .RepoDigests 0}}' "$P0_TAG"
# Record the returned digest-pinned P0_REF as image_ref; keep source_image_id/source_repo_digest fields.
```

Blockers:
- No TB2 source rows have P0/internal repo digests yet; P0 publication needs a separate push/consumer-smoke phase.
- TB2 fallback export is mechanically possible for all 39 rows, but the large-image subset (`19.2GB`, `11.3GB`, `11GB`, `6.2GB`) will be expensive as shared tars; prefer P0 plus fallback for those.
- SWE eval base has no existing fallback tar; one artifact still must be created or a P0 digest must be published.
- Worker-j9jjd should not rely on P0-only transport until #8 registry pull readiness is fixed or explicitly smoke-proven. Keep fallback tar+sha for every promoted row.

Cross-lane check:
- `hunt-runner-results.md` has no contradictory runtime/image transport finding. Its image-preflight notes remain runner-result classification issues and are compatible with this #6/#11 transport-population plan.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Remote status/head check on `swe_dev`: rc 0; branch `feat/image-warmup-policy`, observed head `a2c3f67`, with `ce2adf2 Add registry image lint gate` in history.
- `lint-registry --help`: rc 0; filters are exact `--policy`/`--manifest-id`, not prefix flags.
- Initial stale `--policy-prefix` lint-registry probe: rc 2; useful only to show the command sketch from Round 9 is superseded by current CLI syntax.
- Correct TB2+SWE lint-registry JSON probe: outer rc 0, inner `LINT_RC=1`, `PY_RC=0`; counts quoted above.
- Inventory-shape read for `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`: rc 0; `images=1320`, `identity_errors=0`.
- TB2 missing-row parser against manifest plus identity inventory: first table print hit a quoting bug and exited rc 1 after already printing core counts; rerun succeeded rc 0 with the 39-row table/counts quoted above.
- SWE django10097 manifest/inventory table: rc 0; both rows are exact cache identity matches; wrapper tar exists and eval-base tar is absent.
- Wrapper tar sidecar/stat/bounded search: rc 0; no sha sidecar found; refs file includes target wrapper ref; tar metadata parse confirms target tag appears once with config `blobs/sha256/3e38b927...`.
- `sha256sum` of wrapper tar: rc 0; digest `2ba506ed3e6ff4fdbb2ed54612b633ed782b4604a7b94a9d49173b0b2fb73275`.
- Over-broad shared-tree find for existing eval-base tar was interrupted after it failed to finish quickly; no conclusion depends on that search because the manifest and bounded wrapper tree already show no configured eval-base fallback.
- TB2 size-bucket command: rc 0.
- Pre-append `git diff --check`/status: rc 0; clean before append.

Next runtime/image subdomain: after these transports are created and manifests updated by the implementation lane, re-run `lint-registry` for the same two policies, then run worker runtime `check` with identity verification and fallback load/smoke on a small representative set before attempting all 91 required rows.

## Round 11 - TB2 first transport batch audit (2026-06-26)

Scope held: runtime/images lane only. Worked on `swe_dev` in the active worktree. No production code/manifest/test edits. No Docker save/push/load/run. Evidence is from static manifests, saved swe_dev cache identity inventory, filesystem metadata, and lint output. The only write in this loop is this ledger append.

COMMENT-READY for #6/#8: first practical TB2 transport batch should be small generic fallback tar+sha exports; do not start with P0-only or large/special-runtime rows

dedup: comment-on-#6 for transport population and warmup gating. comment-on-#8 only for the warning that worker-j9jjd must not rely on P0-only transport until digest pull+smoke is proven. Not #11: SWE django10097 is now lint-clean with fallback sha while preserving identity fields, and this loop is TB2-only. No new ISSUE-READY block.

Current state:
- Current branch includes `bacbde3 Materialize SWE django fallback transport`; observed head was `abac24d`.
- `lint-registry --policy audit_manifest_for_tb2_full_image_warmup --policy required_for_swebench_django10097_promotion_smoke --require-offline-transport` still returns rc 1, but now only because TB2 has 39 missing transports. SWE django10097 is `ok` with `required_with_fallback_sha=2`.
- TB2 remaining gap: `count=39`, `identity_match=39`, `tar_exists=0`, `repo_digests=0`, approximate virtual size total `76.01GB`.
- Shared TB2 fallback tree has enough overall storage headroom (`kataShared` showed `14T` available), but large tars are still expensive to write/hash and should not be first.

### 39-row risk categories

| category | count | rows | first-action guidance |
|---|---:|---|---|
| low-risk generic | 23 | `protein-assembly(180MB)`, `schemelike-metacircular-eval(180MB)`, `regex-chess(197MB)`, `openssl-selfsigned-cert(229MB)`, `sqlite-db-truncate(229MB)`, `regex-log(298MB)`, `sparql-university(303MB)`, `sqlite-with-gcov(311MB)`, `password-recovery(396MB)`, `path-tracing-reverse(453MB)`, `query-optimize(454MB)`, `sanitize-git-repo(466MB)`, `tune-mjcf(529MB)`, `overfull-hbox(531MB)`, `polyglot-c-py(560MB)`, `portfolio-optimization(613MB)`, `winning-avg-corewars(736MB)`, `polyglot-rust-c(995MB)`, `write-compressor(996MB)`, `path-tracing(1.1GB)`, `prove-plus-comm(1.46GB)`, `install-windows-3.11(1.63GB)`, `reshard-c4-data(2.52GB)` | Export fallback tar+sha first. P0 digest optional after fallback smoke. |
| service or secret-sensitive task | 3 | `nginx-request-logging(269MB)`, `pypi-server(321MB)`, `vulnerable-secret(478MB)` | Docker save/tag are fine, but do not use as the first runtime smoke batch. Avoid printing task logs for `vulnerable-secret`. |
| special/domain runtime | 12 | `rstan-to-pystan(206MB)`, `raman-fitting(229MB)`, `video-processing(793MB)`, `train-fasttext(874MB)`, `sam-cell-seg(1.13GB)`, `qemu-alpine-ssh(1.96GB)`, `qemu-startup(1.96GB)`, `mteb-retrieve(2.12GB)`, `pytorch-model-cli(2.6GB)`, `torch-tensor-parallelism(11GB)`, `torch-pipeline-parallelism(11.3GB)`, `pytorch-model-recovery(19.2GB)` | Export later; qemu/torch rows should be smoke-tested separately and not mixed into the first batch. |
| large shared-write risk | 4 | `multi-source-data-merger(6.2GB)`, `torch-tensor-parallelism(11GB)`, `torch-pipeline-parallelism(11.3GB)`, `pytorch-model-recovery(19.2GB)` | Prefer P0 digest for scale, but keep fallback tar until #8 worker registry readiness is stable. Do not include in first export batch. |

### Exact first batch

Recommended first implementation batch: five lowest-risk generic rows, total virtual size about `1.015GB`, no service/secret/qemu/torch/domain-runtime flags.

| order | slug | ref | expected image id | size |
|---:|---|---|---|---:|
| 1 | `protein-assembly` | `tb2-offline/protein-assembly:20260425` | `sha256:c517a0dd99f0991faa3f68ae50943b49a55ca7604abbac6b7d824ed4a71bcd6f` | 180MB |
| 2 | `schemelike-metacircular-eval` | `tb2-offline/schemelike-metacircular-eval:20260425` | `sha256:5b6101065623ccb7c6c1e211e51c2e6bb87444cef56e4de18b22f37d0a3a20ec` | 180MB |
| 3 | `regex-chess` | `tb2-offline/regex-chess:20260425` | `sha256:f30f70838516293594a31f2b7c33b02a3ceb0a75c29bbab922f024531c6a787d` | 197MB |
| 4 | `openssl-selfsigned-cert` | `tb2-offline/openssl-selfsigned-cert:20260425` | `sha256:81d7d202b4706d4c8f726b38c55eedf6cb52c1a8553324cff5b3d56ab379d570` | 229MB |
| 5 | `sqlite-db-truncate` | `tb2-offline/sqlite-db-truncate:20260425` | `sha256:62dc8a21604c99b5c8a00d0f45575072e413625e4265bf6000ecca3bd0206749` | 229MB |

Rationale: this batch is large enough to validate the manifest-update/export loop across multiple rows, but small enough to avoid wasting shared-storage time if command wiring or manifest insertion is wrong. If the implementation lane wants an absolute one-row canary before the five-row batch, use only `protein-assembly` with the same commands.

### Fallback tar+sha commands for first batch

Run on `swe_dev` in an implementation lane, not in this bug-hunt lane:

```bash
set -euo pipefail
TB_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425
mkdir -p "$TB_ROOT"
cat >/tmp/tb2_round11_first_batch.tsv <<'EOF'
protein-assembly tb2-offline/protein-assembly:20260425 sha256:c517a0dd99f0991faa3f68ae50943b49a55ca7604abbac6b7d824ed4a71bcd6f
schemelike-metacircular-eval tb2-offline/schemelike-metacircular-eval:20260425 sha256:5b6101065623ccb7c6c1e211e51c2e6bb87444cef56e4de18b22f37d0a3a20ec
regex-chess tb2-offline/regex-chess:20260425 sha256:f30f70838516293594a31f2b7c33b02a3ceb0a75c29bbab922f024531c6a787d
openssl-selfsigned-cert tb2-offline/openssl-selfsigned-cert:20260425 sha256:81d7d202b4706d4c8f726b38c55eedf6cb52c1a8553324cff5b3d56ab379d570
sqlite-db-truncate tb2-offline/sqlite-db-truncate:20260425 sha256:62dc8a21604c99b5c8a00d0f45575072e413625e4265bf6000ecca3bd0206749
EOF
while read -r slug ref expected_id; do
  out="$TB_ROOT/${slug}.tar"
  tmp="$out.tmp.$$"
  actual_id=$(docker image inspect --format '{{.Id}}' "$ref")
  test "$actual_id" = "$expected_id"
  test ! -e "$out"
  docker save -o "$tmp" "$ref"
  sha256sum "$tmp" > "$tmp.sha256"
  mv "$tmp" "$out"
  mv "$tmp.sha256" "$out.sha256"
done </tmp/tb2_round11_first_batch.tsv
```

After this, update only the five corresponding manifest rows with `fallback_tar` and `fallback_tar_sha256`, keep `source_image_id` unchanged, and run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint-registry \
  --registry manifests/bench_registry.yaml \
  --policy audit_manifest_for_tb2_full_image_warmup \
  --policy required_for_swebench_django10097_promotion_smoke \
  --require-offline-transport
```

Expected after only this batch: `required_without_offline_transport` should drop from `39` to `34`, not to zero.

### P0 digest publication commands for first batch

Use only after fallback artifacts exist and after confirming registry CA/health. Keep fallback tar rows even if P0 digest succeeds because #8/rootless registry pull readiness is still the worker risk.

```bash
set -euo pipefail
REG=100.97.118.137:8555
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
mkdir -p /etc/docker/certs.d/$REG
cp "$CERT" /etc/docker/certs.d/$REG/ca.crt
: >/tmp/tb2_round11_first_batch_p0_digests.tsv
while read -r slug ref expected_id; do
  actual_id=$(docker image inspect --format '{{.Id}}' "$ref")
  test "$actual_id" = "$expected_id"
  tag="$REG/swe-data-harness/tb2-${slug}:20260425"
  docker tag "$ref" "$tag"
  docker push "$tag"
  digest_ref=$(docker inspect --format='{{index .RepoDigests 0}}' "$tag")
  printf '%s\t%s\t%s\n' "$slug" "$tag" "$digest_ref" >>/tmp/tb2_round11_first_batch_p0_digests.tsv
done </tmp/tb2_round11_first_batch.tsv
```

If implementation follows the workflow preference to push from `swe_dev2`, use the fallback tar as the handoff artifact, load/tag/push there, then still keep the original fallback tar+sha in the manifest until worker-j9jjd consumer pull+smoke is proven.

### Rows to defer or isolate

- Defer large writes/pushes: `pytorch-model-recovery(19.2GB)`, `torch-pipeline-parallelism(11.3GB)`, `torch-tensor-parallelism(11GB)`, `multi-source-data-merger(6.2GB)`.
- Isolate qemu runtime smoke: `qemu-alpine-ssh`, `qemu-startup`; Docker save/tag should be metadata-safe, but runtime smoke may exercise virtualization assumptions.
- Isolate torch/runtime-heavy smoke: `pytorch-model-cli`, `pytorch-model-recovery`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`.
- Avoid first runtime smoke/log review on `vulnerable-secret`; export/tag is okay, but do not print benchmark task logs in this lane.
- Service rows `nginx-request-logging` and `pypi-server` should not be in the first runtime smoke batch because task-level execution may bind services or require network-like assumptions even though image export is safe.

Cross-lane check:
- Runner-results has no contradictory transport-population finding. Its TB2 notes remain parser/result-classification follow-ups and are compatible with keeping full TB2 enablement gated behind #6 image transport and #8 worker readiness.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Memory quick search for TB2/lint-registry/django/image-warmup terms: rc 0, no relevant hits used.
- Remote status/head/file check on `swe_dev`: rc 0; observed head `abac24d`, with `bacbde3` in history.
- Post-SWE-fix `lint-registry` JSON probe: outer rc 0, inner `LINT_RC=1`, `PY_RC=0`; SWE manifest is `ok`, TB2 has 39 missing transports.
- First risk categorization script had a quoting error and exited rc 1 before useful table output; rerun succeeded rc 0 and produced the counts/categories/first batch above.
- Manifest line/dedup grep: rc 0; confirms the 39 `fallback_status: missing_shared_tar` rows and existing #6/#8/#11 dedup context.
- Storage metadata command: rc 0; shared filesystem showed `14T` available and current TB2 fallback tree size `40G`.
- SWE django10097 post-fix manifest sanity check: rc 0; both SWE rows now have fallback sha.

Next runtime/image subdomain: after the first five TB2 fallback artifacts are materialized and manifest rows updated by the implementation lane, audit that lint-registry drops from 39 to 34 and then select the next low-risk generic batch before touching service/qemu/torch/large rows.
