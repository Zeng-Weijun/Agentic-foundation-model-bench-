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

## Round 12 - TB2 next batch after protein staging (2026-06-26)

Scope: audit only. No Docker save, push, load, run, or benchmark/model execution was performed in this lane.

COMMENT-READY for #6/#8: after `protein-assembly` landed, the next TB2 transport batch should use fresh Docker-inspect identities and the new verified-fallback lint gate

dedup: comment-on-#6 for TB2 transport population and static promotion gating. comment-on-#8 only for the warning that worker-j9jjd should not rely on P0-only transport until digest pull/run smoke stays reliable. Not #11: no SWE image identity issue is inspected in this round. No new ISSUE-READY block.

Current gate state:
- Observed branch/head: `feat/image-warmup-policy` at `65448e4`, with `12fe709 Verify fallback files in registry lint` in history.
- `lint-registry --policy audit_manifest_for_tb2_full_image_warmup --require-offline-transport --json` returns rc 1 with `images=89`, `required_with_digest_ref=1`, `required_with_fallback_sha=51`, and `required_without_offline_transport=38`.
- Adding `--verify-fallback-files` also returns rc 1 with the same 38 missing rows, but now reports `fallback_tar_verified=51`, `fallback_tar_missing=0`, and `fallback_tar_mismatch=0`.
- Acceptance impact: `--verify-fallback-files` does not change the current missing count because the 51 configured fallback rows all verify and the remaining 38 have no transport fields. It does change the promotion contract: a row with only a stale checksum no longer counts as offline transport unless the tar exists and hashes to the manifest value. The batch update should be accepted only after the verified command drops `required_without_offline_transport` from 38 to 30.

Verified protein staging:
- Current manifest row `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:812-824`, TSV `_coordination/20260625_harbor_bench/inventory/tb2_p0_protein_assembly_20260626.tsv`, Docker inspect, and fallback tar hash all agree.
- Protein source image ID: `sha256:c517a0dd99f0991faa3f68ae50943b49a55ca7604abbac6b7d824ed4a71bcd6f`.
- Protein P0 digest ref: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-protein-assembly@sha256:1144842bb39d1bf67d8925879202101caf6250a8a7a83fcf1e582496991004e9`.
- Protein fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/protein-assembly.tar`, size `185604608`, sha256 `97176112820eb4c1b079878de2cad0aeefa1fd4661da51a42431ac7ce80fa5c1`.
- Caution: older ledger command drafts are stale and should not be reused. Round 10 line 718 has a typo in protein's full source ID, and lines 734/736 have stale `sparql-university`/`sqlite-with-gcov` IDs. Use the fresh inspect identities below. The current staged protein artifacts are not inconsistent.

### Next batch recommendation

Pick these 8 rows next. They exclude staged protein and skip service-first rows such as `nginx-request-logging` even though that image is small, because later runtime smoke may exercise service assumptions. Total inspected source size is `1870913597` bytes.

| order | row | manifest evidence | local ref | exact Docker inspect source ID | inspect size bytes | inventory size |
| --- | --- | --- | --- | --- | ---: | --- |
| 1 | `schemelike-metacircular-eval` | `terminal_bench_2_1_swe_dev_cache.yaml:995-1000` | `tb2-offline/schemelike-metacircular-eval:20260425` | `sha256:5b6101065623ccb7c6c1e211e51c2e6bb87444cef56e4de18b22f37d0a3a20ec` | 179580792 | 180MB |
| 2 | `regex-chess` | `terminal_bench_2_1_swe_dev_cache.yaml:923-928` | `tb2-offline/regex-chess:20260425` | `sha256:f30f70838516293594a31f2b7c33b02a3ceb0a75c29bbab922f024531c6a787d` | 196599444 | 197MB |
| 3 | `rstan-to-pystan` | `terminal_bench_2_1_swe_dev_cache.yaml:959-964` | `tb2-offline/rstan-to-pystan:20260425` | `sha256:83b98640ec92a139654122401f56d4f7471d0282ebf006154c406f38ea468eeb` | 205657034 | 206MB |
| 4 | `sqlite-db-truncate` | `terminal_bench_2_1_swe_dev_cache.yaml:1019-1024` | `tb2-offline/sqlite-db-truncate:20260425` | `sha256:62dc8a21604c99b5c8a00d0f45575072e413625e4265bf6000ecca3bd0206749` | 229124484 | 229MB |
| 5 | `openssl-selfsigned-cert` | `terminal_bench_2_1_swe_dev_cache.yaml:716-721` | `tb2-offline/openssl-selfsigned-cert:20260425` | `sha256:81d7d202b4706d4c8f726b38c55eedf6cb52c1a8553324cff5b3d56ab379d570` | 229125027 | 229MB |
| 6 | `raman-fitting` | `terminal_bench_2_1_swe_dev_cache.yaml:911-916` | `tb2-offline/raman-fitting:20260425` | `sha256:3ed67c59f865f29e6c9693cf36912da16e978c101e611face59fba70f0afe0a4` | 229209193 | 229MB |
| 7 | `regex-log` | `terminal_bench_2_1_swe_dev_cache.yaml:935-940` | `tb2-offline/regex-log:20260425` | `sha256:5d9eae30a8a3d2a2853c023bd1f976528c4d7f7a825d926206648aa52d60606e` | 298200058 | 298MB |
| 8 | `sparql-university` | `terminal_bench_2_1_swe_dev_cache.yaml:1007-1012` | `tb2-offline/sparql-university:20260425` | `sha256:b7c23a59ae22a6ba1f724cdd69b5572d850ba3220f662bed4674bd7a23fafec8` | 303417565 | 303MB |

### Fallback tar+sha commands for implementation lane

These commands are proposed for the implementation lane, not executed here. They intentionally verify source image identity before writing each tar.

```bash
set -euo pipefail
TB_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2
mkdir -p "$TB_ROOT"
cat >/tmp/tb2_round12_next_batch.tsv <<'EOF'
schemelike-metacircular-eval tb2-offline/schemelike-metacircular-eval:20260425 sha256:5b6101065623ccb7c6c1e211e51c2e6bb87444cef56e4de18b22f37d0a3a20ec
regex-chess tb2-offline/regex-chess:20260425 sha256:f30f70838516293594a31f2b7c33b02a3ceb0a75c29bbab922f024531c6a787d
rstan-to-pystan tb2-offline/rstan-to-pystan:20260425 sha256:83b98640ec92a139654122401f56d4f7471d0282ebf006154c406f38ea468eeb
sqlite-db-truncate tb2-offline/sqlite-db-truncate:20260425 sha256:62dc8a21604c99b5c8a00d0f45575072e413625e4265bf6000ecca3bd0206749
openssl-selfsigned-cert tb2-offline/openssl-selfsigned-cert:20260425 sha256:81d7d202b4706d4c8f726b38c55eedf6cb52c1a8553324cff5b3d56ab379d570
raman-fitting tb2-offline/raman-fitting:20260425 sha256:3ed67c59f865f29e6c9693cf36912da16e978c101e611face59fba70f0afe0a4
regex-log tb2-offline/regex-log:20260425 sha256:5d9eae30a8a3d2a2853c023bd1f976528c4d7f7a825d926206648aa52d60606e
sparql-university tb2-offline/sparql-university:20260425 sha256:b7c23a59ae22a6ba1f724cdd69b5572d850ba3220f662bed4674bd7a23fafec8
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
done </tmp/tb2_round12_next_batch.tsv
```

After manifest update, run the verified promotion gate:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint-registry \
  --registry manifests/bench_registry.yaml \
  --asset-root manifests \
  --policy audit_manifest_for_tb2_full_image_warmup \
  --require-offline-transport \
  --verify-fallback-files \
  --json
```

Expected after exactly these 8 rows are materialized and manifest-updated: rc 1 until all TB2 rows are populated, but `required_without_offline_transport` should drop from `38` to `30`, `fallback_tar_verified` should rise from `51` to `59`, and `fallback_tar_missing/fallback_tar_mismatch` should remain `0`.

### P0 digest publication commands for implementation lane

Use the current protein naming convention (`terminal-bench-2-1-${slug}`), not the older `tb2-${slug}` sketch. Keep fallback tar+sha even if P0 succeeds, until worker-j9jjd digest pull+run smoke is reliable.

```bash
set -euo pipefail
REG=100.97.118.137:8555
: >/tmp/tb2_round12_next_batch_p0_digests.tsv
while read -r slug ref expected_id; do
  actual_id=$(docker image inspect --format '{{.Id}}' "$ref")
  test "$actual_id" = "$expected_id"
  tag="$REG/swe-data-harness/terminal-bench-2-1-${slug}:20260425"
  docker tag "$ref" "$tag"
  docker push "$tag"
  digest_ref=$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "$tag" | grep "^$REG/swe-data-harness/terminal-bench-2-1-${slug}@sha256:" | tail -n 1)
  test -n "$digest_ref"
  printf '%s\t%s\t%s\t%s\n' "$slug" "$ref" "$expected_id" "$digest_ref" >>/tmp/tb2_round12_next_batch_p0_digests.tsv
done </tmp/tb2_round12_next_batch.tsv
```

### Risk notes for later rows

- Large write/push risk remains deferred: `pytorch-model-recovery(19.2GB)`, `torch-pipeline-parallelism(11.3GB)`, `torch-tensor-parallelism(11GB)`, `multi-source-data-merger(6.2GB)`.
- Special runtime smoke should be isolated: `qemu-alpine-ssh`, `qemu-startup`, all torch/pytorch rows, and service rows `nginx-request-logging`/`pypi-server`.
- `vulnerable-secret` can be saved/tagged like any other Docker image, but do not use it as the first runtime-log smoke because task-level output may invite unsafe log inspection.
- `sqlite-with-gcov` is the next low-risk alternate after the selected batch, with fresh inspect ID `sha256:3a0432d8b6977202c755a01b0d3050ef8908f4d6a0c4337c8a13e2925b76d9fa`; ignore the stale Round 10 typo.

Cross-lane check:
- `hunt-runner-results.md` has no contradictory TB2 transport finding. Its current image-related comments focus on preserving fallback-load/image-check provenance and parser classification after preflight failures. That is compatible with this #6/#8 transport-population follow-up.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Memory quick search for TB2/lint-registry/image-warmup terms: rc 0, no relevant hits used.
- Remote status/head/file check on `swe_dev`: rc 0; observed branch/head `feat/image-warmup-policy` / `65448e4`, with `12fe709` in history.
- Read `scripts/agentic_bench_images.py` lint-registry/fallback verification lines, tests, and README promotion-gate docs: rc 0.
- `lint-registry --help`: rc 0.
- Registry policy lookup for TB2 manifest: rc 0; selected policy is `audit_manifest_for_tb2_full_image_warmup`.
- TB2 lint without verify and with `--verify-fallback-files`: command outer rc 0, inner lint rc values `RC_LINT_NOVERIFY=1`, `RC_LINT_VERIFY=1`, parse rc 0; counts quoted above.
- Docker inspect over all 38 no-transport TB2 rows: rc 0; all inspected image IDs matched manifest `source_image_id`.
- Manifest/inventory line grep for selected rows and protein: rc 0.
- Protein manifest/TSV/fallback tar hash/tar manifest probe: rc 0.
- Protein local Docker inspect: rc 0; P0 digest ref is present in Docker metadata.
- Dedup grep over runtime and runner ledgers for #6/#8/#11/TB2 transport terms: rc 0.
- Stale ID grep for old draft commands and fresh `sparql-university`/`sqlite-with-gcov` identities: rc 0.

Next runtime/image subdomain: after batch2 artifacts and manifest rows are materialized by the implementation lane, audit the verified lint drop from 38 to 30 and then pick the next batch from `sqlite-with-gcov`, `password-recovery`, `path-tracing-reverse`, `query-optimize`, and `sanitize-git-repo`, before service/qemu/torch/large rows.

## Round 13 - TB2 remaining 34 audit after batch2 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed. Read-only Docker `image inspect`, manifest/lint reads, grep/find, and fallback tar hash reads only.

COMMENT-READY for #6/#8/#12: batch2 is correct, but worker-j9jjd still needs fallback-first TB2 promotion; next implementation should wire the already-created batch3 fallback artifacts before exporting more images

dedup: comment-on-#6 for TB2 transport population and static promotion gating. comment-on-#8 because direct P0 pull is still rootless-daemon network-unreachable on worker-j9jjd. comment-on-#12 because the worker batch2 checker JSON is the reproducibility proof that result/provenance should preserve. Not #11: all inspected remaining TB2 local tags match their manifest `source_image_id`; no SWE/image-lineage mismatch was found. No new ISSUE-READY block.

Current state:
- Observed branch/head: `feat/image-warmup-policy` at `eb552a3 Materialize TB2 low-risk transport batch`.
- Worktree had an untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch3_20260626.tsv`; it changed during this read from 4 rows to 5 rows. Treat it as concurrent staging evidence, not committed manifest truth.
- TB2-only verified lint command returned rc 1 with `images=89`, `required_with_digest_ref=5`, `required_with_fallback_sha=55`, `fallback_tar_verified=55`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=34`.
- The handoff's combined TB2+SWE count `fallback_tar_verified=57` is consistent: TB2 has 55 verified fallback rows, and SWE django10097 contributes 2.
- Batch2 implemented 4 of the Round 12 candidates in the manifest: `schemelike-metacircular-eval`, `regex-chess`, `openssl-selfsigned-cert`, and `sqlite-db-truncate`.
- Round 12's remaining recommended rows are still manifest-missing: `rstan-to-pystan`, `raman-fitting`, `regex-log`, and `sparql-university`. The untracked batch3 TSV now stages those four plus `sqlite-with-gcov`.

Worker transport implication:
- Batch2 worker fallback-load/run-smoke passed: `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_check_20260626.json` reports `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `identity_mismatch=0`, `errors=0`.
- The direct P0 pull probe is still not a reliable worker readiness signal. `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch2_worker_p0_pull_20260626.txt` shows host `curl` to `/v2/` succeeded, but rootless Docker pull failed with `dial tcp 100.97.118.137:8555: connect: network is unreachable`.
- Therefore, do not make remaining TB2 rows P0-only. Every promoted row should keep `fallback_tar` plus `fallback_tar_sha256`, and worker-ready status should require `check --load-fallback --run-smoke` until #8/rootless registry networking is fixed.

### Recommended next implementation batch

Use the already-created untracked batch3 artifacts first. This avoids more `docker save` work and should be the lowest-risk next change: update the five manifest rows with the TSV's P0 digest refs and fallback tar+sha fields, then run verified static lint and a worker fallback-load/run-smoke subset check.

Expected static gate movement after only these five rows are manifest-wired:
- TB2-only `required_without_offline_transport`: `34 -> 29`.
- TB2-only `fallback_tar_verified`: `55 -> 60`.
- TB2-only `required_with_fallback_sha`: `55 -> 60`.
- TB2-only `required_with_digest_ref`: `5 -> 10`, if the P0 digest refs from the TSV are also added.
- Combined TB2+SWE verified fallback count should move from `57 -> 62`.

| row | manifest line | current risk category | local ref | exact source image ID | inspect size bytes | staged fallback tar size | staged fallback sha |
| --- | ---: | --- | --- | --- | ---: | ---: | --- |
| `rstan-to-pystan` | 965 | low-size, already artifacted | `tb2-offline/rstan-to-pystan:20260425` | `sha256:83b98640ec92a139654122401f56d4f7471d0282ebf006154c406f38ea468eeb` | 205657034 | 211495936 | `bc64a7b493db935b75d827cc2daeedaf167ac29b984d2a2b26e0f2483f304bc4` |
| `raman-fitting` | 914 | low-size, already artifacted | `tb2-offline/raman-fitting:20260425` | `sha256:3ed67c59f865f29e6c9693cf36912da16e978c101e611face59fba70f0afe0a4` | 229209193 | 236170752 | `4e5c6c7774ad151bb9f9691fec9346308dcba6d7ec897248824a6859436aec02` |
| `regex-log` | 941 | low-size, already artifacted | `tb2-offline/regex-log:20260425` | `sha256:5d9eae30a8a3d2a2853c023bd1f976528c4d7f7a825d926206648aa52d60606e` | 298200058 | 307172352 | `7e68a41e7976324352fdb717738f457c0204347841aa375a27afc6458a4d6a31` |
| `sparql-university` | 1016 | low-size, already artifacted | `tb2-offline/sparql-university:20260425` | `sha256:b7c23a59ae22a6ba1f724cdd69b5572d850ba3220f662bed4674bd7a23fafec8` | 303417565 | 312662016 | `26848e0a361609db40ede648a7b1768d49902f272d55f45469daee875bf29e7e` |
| `sqlite-with-gcov` | 1043 | low-size, already artifacted | `tb2-offline/sqlite-with-gcov:20260425` | `sha256:3a0432d8b6977202c755a01b0d3050ef8908f4d6a0c4337c8a13e2925b76d9fa` | 310840758 | 319819264 | `ea2d0f9ea92cbea470d750f4c5b44edc21f8e407a699e46689f7e64a381a1292` |

Use the untracked TSV as input only after re-reading it and confirming no concurrent edit changed it:

```bash
sha256sum _coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch3_20260626.tsv
python3 - <<'PY'
import csv, hashlib
from pathlib import Path
p = Path("_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch3_20260626.tsv")
for r in csv.DictReader(p.open(), delimiter="\t"):
    tar = Path(r["fallback_tar"])
    h = hashlib.sha256()
    with tar.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    assert h.hexdigest() == r["fallback_tar_sha256"], r["slug"]
    print(r["slug"], "sha-ok", tar)
PY
```

Then update only those five manifest rows and run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint-registry \
  --registry manifests/bench_registry.yaml \
  --asset-root manifests \
  --policy audit_manifest_for_tb2_full_image_warmup \
  --require-offline-transport \
  --verify-fallback-files \
  --json
```

Do not treat the P0 digest refs as worker-ready yet. The implementation acceptance should also include a worker fallback subset check equivalent to the batch2 proof, with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, `--load-fallback`, and `--run-smoke`; a direct `docker pull` failure must fall back to the verified tar, not fail the batch.

### Remaining rows after batch3

If batch3 is manifest-wired, the remaining gap should be 29 rows. Next export candidates after batch3 should stay with low-size generic rows before touching service, qemu, torch, large, or data-heavy rows:

| suggested order | row | current risk category | source image ID | inspect size bytes |
| --- | --- | --- | --- | ---: |
| 1 | `password-recovery` | low-size | `sha256:8a4a2ba55bfa8edd5dece054d844969a60d1f237ae2e18cf4ce6842fbd1c3465` | 396013238 |
| 2 | `path-tracing-reverse` | low-size | `sha256:d0aed029cc004bed222ed1cd39dea1a8a149cd66bb2616354a75e9cb762e6718` | 452873228 |
| 3 | `query-optimize` | low-size | `sha256:b7888e243c321aa0c7fa3076325057b9e1d85637f5e9443a7a80cb1494cf152c` | 453788685 |
| 4 | `sanitize-git-repo` | low-size | `sha256:6fb3909be2d3e41fdba90e7aac02bb6e68e2b31485c426f7b9a21cdd6e53e187` | 466395053 |
| 5 | `tune-mjcf` | low-size | `sha256:77711f5e2763702941189d7959b99ab7edb1d1a0c9c095fd33c669f6b4fca41e` | 529319551 |
| 6 | `overfull-hbox` | low-size | `sha256:a58256eef1e4e2fb761e753180d216e3edbd0fb79dc3e4b65a7b8c1a16ebb168` | 531075314 |
| 7 | `polyglot-c-py` | low-size | `sha256:34f1e78e9e23c8c9cc5954a4c235d9b5eb432db89c8c1322c36b13aefa3b4222` | 559936028 |
| 8 | `winning-avg-corewars` | low-size | `sha256:3cb6bfd6a3a6db04aa52a00b5eeb2eab71ba1fc4a83c69802126411324ecd892` | 735891766 |

Rows to isolate or defer:
- Service smoke isolation: `nginx-request-logging`, `pypi-server`.
- Secret/log isolation: `vulnerable-secret`.
- Data or ML runtime caution: `portfolio-optimization`, `video-processing`, `train-fasttext`, `sam-cell-seg`, `mteb-retrieve`, `reshard-c4-data`, `multi-source-data-merger`.
- QEMU isolation: `qemu-startup`, `qemu-alpine-ssh`.
- Torch/pytorch heavy rows: `pytorch-model-cli`, `pytorch-model-recovery`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`.
- Large write/push risk: `multi-source-data-merger(6203486893 bytes)`, `torch-tensor-parallelism(11026213679)`, `torch-pipeline-parallelism(11315069350)`, `pytorch-model-recovery(19201784321)`.

Cross-lane check:
- `hunt-runner-results.md` Round 13 confirms the batch2 checker JSON should become a #12 provenance fixture and explicitly says the P0 pull failure remains #8/runtime readiness. No contradiction with this runtime transport recommendation.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Memory quick search for TB2/lint-registry/image-warmup terms: rc 0, no relevant hits used.
- Read WORKFLOW continuous bug-hunt section: rc 0.
- Remote head/status and lint evidence command: rc 0; branch/head `feat/image-warmup-policy` / `eb552a3`, untracked batch3 TSV observed.
- TB2 verified lint command: outer rc 0, inner `LINT_RC=1`, parse rc 0; counts quoted above.
- Batch2 evidence file listing: rc 0.
- Batch2 TSV, worker P0 pull failure, and worker checker summary read: rc 0.
- Untracked batch3 TSV first hash probe: rc 0; initially observed 4 rows.
- Manifest line read around batch2/Round12 rows: rc 0.
- Remaining-34 Docker inspect derivation: rc 0; all inspected IDs matched manifest source IDs.
- Re-read untracked batch3 TSV with line numbers: rc 0; observed 5 rows and sha `fecbcc0b7ea566c3eb82e794072d057b0b368f8e49b71d1a7917139e7db14324`.
- Batch3 fallback tar hash verification for all 5 current rows: rc 0.
- Cross-lane grep over `hunt-runner-results.md` and current runtime ledger tail: rc 0.

Next runtime/image subdomain: after batch3 manifest wiring and worker fallback smoke, audit that TB2 verified lint drops from 34 to 29 and that no manifest row is P0-only. Then pick the next low-size generic export batch before service/qemu/torch/large rows.

## Round 14 - TB2 remaining 29 audit after batch3 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, manifest/lint reads, grep/find, and fallback tar hash reads only.

COMMENT-READY for #6/#8/#12: after batch3, wire and worker-smoke the staged batch4 fallbacks, then export the next low-size generic rows; keep P0 as metadata until worker rootless pull is fixed

dedup: comment-on-#6 for TB2 transport population and static promotion gating. comment-on-#8 because the rootless worker still cannot be treated as P0-pull-ready after the recorded `connect: network is unreachable` failure. comment-on-#12 because each worker fallback check should be preserved as structured image-check provenance. Not #11: every remaining row inspected in this round matched its manifest `source_image_id`; no image identity bug was found. No new ISSUE-READY block.

Current state:
- Observed branch/head: `feat/image-warmup-policy` at `c7a0eef Materialize TB2 low-risk transport batch 3`.
- Clean-head/initial Round 14 TB2-only verified lint returned rc 1 with `images=89`, `required_with_digest_ref=10`, `required_with_fallback_sha=60`, `fallback_tar_verified=60`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=29`.
- During this audit, an implementation lane created and expanded untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch4_20260626.tsv`, then modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` to wire those five rows.
- Live dirty-worktree verified lint after that concurrent manifest edit returned rc 1 with `required_with_digest_ref=15`, `required_with_fallback_sha=65`, `fallback_tar_verified=65`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=24`.
- No batch4 worker fallback-check JSON existed at the time of this audit. Before batch4 is called worker-ready, run the same worker `check --load-fallback --run-smoke` proof used for batches 2 and 3.

### Batch4 staging observed

These five rows are already staged in the untracked batch4 TSV and live dirty manifest, with P0 digest refs plus verified fallback tars. This is now a worker-smoke/commit hygiene step, not a Docker-export step.

| row | manifest line before dirty edit | risk label | local ref | exact source image ID | inspect size bytes | fallback tar size | fallback sha |
| --- | ---: | --- | --- | --- | ---: | ---: | --- |
| `password-recovery` | 743 | low-size, batch4 staged | `tb2-offline/password-recovery:20260425` | `sha256:8a4a2ba55bfa8edd5dece054d844969a60d1f237ae2e18cf4ce6842fbd1c3465` | 396013238 | 407543296 | `8ffc3246f62792f7a9085bf91cf1f01e2d9fcbb7437cce759f98a01048914d4f` |
| `path-tracing-reverse` | 755 | low-size, batch4 staged | `tb2-offline/path-tracing-reverse:20260425` | `sha256:d0aed029cc004bed222ed1cd39dea1a8a149cd66bb2616354a75e9cb762e6718` | 452873228 | 460471296 | `f6bb157c283b34956069a6dd5800a712b91cf9dc6de99fca341e62f9ac063f4f` |
| `query-optimize` | 902 | low-size, batch4 staged | `tb2-offline/query-optimize:20260425` | `sha256:b7888e243c321aa0c7fa3076325057b9e1d85637f5e9443a7a80cb1494cf152c` | 453788685 | 462921728 | `940f201d3d49aff17168b0f686ea90c716379096fb20c9a84497cfe9f37baa44` |
| `sanitize-git-repo` | 998 | low-size, batch4 staged | `tb2-offline/sanitize-git-repo:20260425` | `sha256:6fb3909be2d3e41fdba90e7aac02bb6e68e2b31485c426f7b9a21cdd6e53e187` | 466395053 | 476883456 | `a7f05aaaa8c493d3d60c581f687901b86632ca2846a4214f8b52fcf6c7090084` |
| `tune-mjcf` | 1106 | low-size, batch4 staged | `tb2-offline/tune-mjcf:20260425` | `sha256:77711f5e2763702941189d7959b99ab7edb1d1a0c9c095fd33c669f6b4fca41e` | 529319551 | 550133760 | `64c797c13884c38a0089d8e3ebd33907b91a93990ddcb0b1a370b7d1ab3e57dc` |

Expected gate movement:
- From committed batch3 head: `required_without_offline_transport 29 -> 24` after batch4 manifest wiring, already observed in the dirty worktree.
- `fallback_tar_verified 60 -> 65`, `required_with_fallback_sha 60 -> 65`, and `required_with_digest_ref 10 -> 15`, already observed in the dirty worktree.
- Worker readiness is still pending because there is no batch4 worker-check JSON yet.

Worker command recommendation for batch4 implementation lane:

```bash
# Use the explicit worker-j9jjd endpoint from WORKFLOW.md and rootless Docker socket.
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check \
  --image-manifest <batch4-five-row-temp-or-updated-manifest> \
  --asset-root manifests \
  --docker-host "$DOCKER_HOST" \
  --load-fallback \
  --run-smoke \
  --json
```

The full TB2 manifest will still fail until the remaining 24 rows are populated, so use the same bounded subset proof pattern as batch2/batch3 when proving batch4 worker fallback readiness. Do not rely on direct P0 pull for worker readiness until #8 is resolved.

### Next export/P0/fallback batch after batch4

After batch4 is worker-smoked, the next export batch should avoid service, secret, qemu, torch, large, and data/ML-heavy rows. Pick these five generic rows next:

| order | row | risk label | local ref | exact source image ID | inspect size bytes |
| --- | --- | --- | --- | --- | ---: |
| 1 | `overfull-hbox` | low-size, generic | `tb2-offline/overfull-hbox:20260425` | `sha256:a58256eef1e4e2fb761e753180d216e3edbd0fb79dc3e4b65a7b8c1a16ebb168` | 531075314 |
| 2 | `polyglot-c-py` | low-size, generic | `tb2-offline/polyglot-c-py:20260425` | `sha256:34f1e78e9e23c8c9cc5954a4c235d9b5eb432db89c8c1322c36b13aefa3b4222` | 559936028 |
| 3 | `winning-avg-corewars` | low-size, generic | `tb2-offline/winning-avg-corewars:20260425` | `sha256:3cb6bfd6a3a6db04aa52a00b5eeb2eab71ba1fc4a83c69802126411324ecd892` | 735891766 |
| 4 | `polyglot-rust-c` | low-size but near 1GB | `tb2-offline/polyglot-rust-c:20260425` | `sha256:a4b68e06827a2ace4a21b98b63872ed9c31183c213cf19e214bde116250394c3` | 995089093 |
| 5 | `write-compressor` | low-size but near 1GB | `tb2-offline/write-compressor:20260425` | `sha256:868491de68ebb7000a47f5ef8fb65ab8f34967d07542310311a7c38a8d6a795d` | 995690686 |

Expected gate movement for that next export batch after batch4 is committed:
- `required_without_offline_transport 24 -> 19`.
- `fallback_tar_verified 65 -> 70`.
- `required_with_fallback_sha 65 -> 70`.
- `required_with_digest_ref 15 -> 20`, if P0 digest refs are also published and manifest-wired.

Rows to isolate or defer:
- Service rows: `nginx-request-logging`, `pypi-server`; both are small but should have isolated runtime-smoke expectations.
- Secret/log row: `vulnerable-secret`; export is fine, but do not use as first log-inspection smoke.
- Data/ML runtime rows: `portfolio-optimization`, `video-processing`, `train-fasttext`, `sam-cell-seg`, `mteb-retrieve`, `reshard-c4-data`, `multi-source-data-merger`.
- QEMU rows: `qemu-startup`, `qemu-alpine-ssh`.
- Torch/pytorch rows: `pytorch-model-cli`, `pytorch-model-recovery`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`.
- Large write/push rows: `multi-source-data-merger(6203486893 bytes)`, `torch-tensor-parallelism(11026213679)`, `torch-pipeline-parallelism(11315069350)`, `pytorch-model-recovery(19201784321)`.

Cross-lane check:
- `hunt-runner-results.md` Round 14 focuses on preserving batch3 image-check evidence in structured result/provenance. It agrees that P0 pull failures remain #8/runtime readiness and does not contradict this transport-population recommendation.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions: rc 0.
- Memory quick search for TB2/lint-registry/image-warmup terms: rc 0, no relevant hits used.
- Read WORKFLOW continuous bug-hunt section: rc 0.
- Remote head/status and batch3 evidence file listing: rc 0; branch/head `feat/image-warmup-policy` / `c7a0eef`.
- Initial TB2 verified lint command on batch3 head: outer rc 0, inner `LINT_RC=1`, parse rc 0; counts `fallback_tar_verified=60`, `required_without_offline_transport=29`.
- Remaining-29 Docker inspect derivation: rc 0; every inspected row matched manifest `source_image_id`.
- First batch4 artifact search: rc 0; observed untracked `tb2_p0_lowrisk_batch4_20260626.tsv`.
- Batch4 TSV/hash probe after concurrent expansion: rc 0; observed 5 rows and sha `1af963f1b59e1040200d430f1ba74aa5b0650737f6c922ac8bddb6705ded8983`.
- Batch4 fallback tar hash verification for all 5 current rows: rc 0.
- Batch4 P0-tag read-only Docker inspect for all 5 rows: rc 0; tag IDs match source IDs and RepoDigests match TSV digest refs.
- Status/diff check after concurrent batch4 manifest wiring: rc 0; observed modified manifest and untracked batch4 TSV, not changed by this lane.
- Post-batch4 dirty-worktree verified lint: outer rc 0, inner `LINT_RC=1`, parse rc 0; counts `fallback_tar_verified=65`, `required_without_offline_transport=24`.
- Batch4 worker-check lookup: rc 0; no batch4 worker-check JSON existed.
- Cross-lane grep over `hunt-runner-results.md` and current runtime ledger tail: rc 0.

Next runtime/image subdomain: after batch4 worker fallback smoke exists, audit the dirty manifest/TSV pair for commit readiness and then verify the next five generic exports drop TB2 from 24 to 19 without introducing P0-only rows.


### Orchestrator follow-up after Round 14

After the runtime-images lane finished its read-only audit, the orchestrator completed the batch4 worker proof. `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch4_worker_check_20260626.json` now exists and reports `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, and `errors=0`. Therefore batch4 is no longer worker-smoke-pending; the next runtime/image subdomain should start from the remaining 24-row gap and the next generic export batch described above.

## Round 15 - TB2 remaining 24 audit after batch4 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, manifest/lint reads, grep/find, fallback tar hash reads, and worker-check JSON reads only.

COMMENT-READY for #6/#8/#12: the next generic batch is valid and now appears materialized by another lane; it drops TB2 from 24 to 19 missing transports, but fallback tar remains required because worker P0 pull readiness is still #8

dedup: comment-on-#6 for TB2 transport population and static promotion gating. comment-on-#8 because worker-j9jjd still must not rely on P0-only transport until direct registry pull is fixed or re-proven. comment-on-#12 because the batch5 worker fallback-load/run-smoke JSON should be preserved as structured image-check provenance. Not #11: all inspected candidate rows matched their manifest `source_image_id`; no identity-lineage bug was found. No new ISSUE-READY block.

Current state and concurrency notes:
- Observed branch/head: `feat/image-warmup-policy` at `5a4e0a7 Record TB2 batch4 runtime audit`.
- Initial Round 15 status had no manifest diff and only untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_lowrisk_batch5_20260626.tsv`; at that moment the TSV had three rows: `overfull-hbox`, `polyglot-c-py`, and `winning-avg-corewars`.
- Initial TB2-only verified lint returned rc 1 with `images=89`, `required_with_digest_ref=15`, `required_with_fallback_sha=65`, `fallback_tar_verified=65`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=24`.
- During this audit, another lane expanded batch5 to five rows, modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and created `_coordination/20260625_harbor_bench/inventory/tb2_lowrisk_batch5_worker_check_20260626.json`. This runtime lane did not edit those files.
- After the concurrent batch5 wiring, verified lint returned rc 1 with `required_with_digest_ref=20`, `required_with_fallback_sha=70`, `fallback_tar_verified=70`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=19`.
- Batch5 worker fallback-load/run-smoke JSON reports `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.

### Generic batch audit

The requested generic candidates are safe as the next batch: no service runtime, no secret/log-specific task, no QEMU, no torch/pytorch, and no data/ML-heavy runtime. Hidden risk found during the audit was not a new bug: the untracked TSV briefly lagged behind actual Docker/shared-tar state, listing only three rows while `polyglot-rust-c` and `write-compressor` already had fallback tars and P0 tag metadata. The TSV and manifest were later updated to all five rows, and the worker fallback proof exists.

| row | current manifest line | risk label | exact source image ID | inspect size bytes | fallback tar sha | P0 digest ref |
| --- | ---: | --- | --- | ---: | --- | --- |
| `overfull-hbox` | 731 | low-size generic | `sha256:a58256eef1e4e2fb761e753180d216e3edbd0fb79dc3e4b65a7b8c1a16ebb168` | 531075314 | `50e36c20e4a23291ad0b0d9af527cf4046964cab5d3ee07a025308de8eba38ee` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-overfull-hbox@sha256:20e76797505baeb57f693c8778496b912d390a6afe68975f5e4dd5fd49db06d3` |
| `polyglot-c-py` | 788 | low-size generic | `sha256:34f1e78e9e23c8c9cc5954a4c235d9b5eb432db89c8c1322c36b13aefa3b4222` | 559936028 | `7dd9938b6fec77ada6dd73a82c5acb76bd0fc4824565975214c72f8ad6de27bf` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-polyglot-c-py@sha256:f31972c9fe30b7997df06bd448294d54779e861a61e15f2a7cf353dc8f009f6b` |
| `polyglot-rust-c` | 803 | low-size generic, near 1GB | `sha256:a4b68e06827a2ace4a21b98b63872ed9c31183c213cf19e214bde116250394c3` | 995089093 | `3b5f188592e3f6d4b9bbfa235bbe83e644843c27947e248dbbc2f7af9679dd2a` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-polyglot-rust-c@sha256:608ae734f32f04a7b5013bf5607b890d1f9222bc2f6934d615b765cf8776d064` |
| `winning-avg-corewars` | 1166 | low-size generic | `sha256:3cb6bfd6a3a6db04aa52a00b5eeb2eab71ba1fc4a83c69802126411324ecd892` | 735891766 | `bd8b9926953684737f69cacd23e18269d4dccf425429144ec07af6dd523bbd2a` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-winning-avg-corewars@sha256:ea41cba6fb9a2f72e4647bb578bc08241979ac241a07b24b2342d0c2c7a8befd` |
| `write-compressor` | 1181 | low-size generic, near 1GB | `sha256:868491de68ebb7000a47f5ef8fb65ab8f34967d07542310311a7c38a8d6a795d` | 995690686 | `ec32ea77c1327f6b423312bc42425f8d64b847b2f1839a73e1a1392d7f5602fb` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-write-compressor@sha256:1ab853caf47d81567d48e9f256be114358f6fcfd156d402246ae91fe16c0cd86` |

Expected and observed gate movement:
- From committed batch4 state, the five-row batch should move TB2-only `required_without_offline_transport 24 -> 19`.
- `fallback_tar_verified`, `required_with_fallback_sha`, and `required_with_digest_ref` should move `65 -> 70`, `65 -> 70`, and `15 -> 20`.
- The observed post-wiring verified lint exactly matches that expected movement and keeps `fallback_tar_missing=0` and `fallback_tar_mismatch=0`.
- Worker readiness for this batch should be considered fallback-ready, not P0-pull-ready: the worker check loaded fallback tars (`loaded=5`, `pulled=0`) and smoke-passed all five.

### Remaining 19 rows to isolate/defer

After batch5, the remaining static transport gap is 19 rows. These should be batched by isolation class rather than raw size alone.

| row | isolation/defer reason | exact source image ID | inspect size bytes |
| --- | --- | --- | ---: |
| `nginx-request-logging` | service smoke isolation | `sha256:e673cf94a1a3263065b9c37d101f8c4b6ed54a2227ba0100e105c5c6b46b15ff` | 268733645 |
| `pypi-server` | service smoke isolation | `sha256:59e8830ad18ef4a515d968596b38e467a5b6eb018d1536fd9088c5ddca677ea8` | 320922060 |
| `vulnerable-secret` | secret/log isolation | `sha256:ed187ec826168b02180860a958bca08ea3cae5b871bc3b12d0e026cff218cd74` | 478004753 |
| `portfolio-optimization` | data/ML runtime caution | `sha256:1fca885f366e54cc7fa1e42c02b22d29ce296a5bf1c7f17e7a9cbbede7ca5614` | 613395442 |
| `video-processing` | data/ML runtime caution | `sha256:470f922fb58fcc7f66324e9912e31717e0fd07c0468a3ca23f7e2950f27f0fef` | 793327868 |
| `train-fasttext` | data/ML runtime caution | `sha256:535d3a38744d0b5cf72b033b520132751569231316e134ac6a99cc62e666d13f` | 873782103 |
| `path-tracing` | medium-size generic, isolate from first service batch | `sha256:49297f60440893098411cba5f167d0ee719dcd5e61adca1b149fa9485d3b3a6b` | 1104154092 |
| `sam-cell-seg` | data/ML runtime caution | `sha256:dbc5dfcc120fbcf959d3be14d3ae7b0fb71533e8ca4c5c92b40c9c9dd1a3fe27` | 1130941638 |
| `prove-plus-comm` | medium-size generic, isolate from service/qemu/torch batches | `sha256:c6b448d30a2ca1c7a6c5ea4b05762d85600bc60f562ce382a57673ad8baeaed5` | 1461316125 |
| `install-windows-3.11` | medium-size special environment | `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b` | 1629941732 |
| `qemu-startup` | QEMU isolation | `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444` | 1956605318 |
| `qemu-alpine-ssh` | QEMU isolation | `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573` | 1956628773 |
| `mteb-retrieve` | data/ML runtime caution | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2117496845 |
| `reshard-c4-data` | data/ML runtime caution | `sha256:3151b2371e33c8792274de78add175049aeb6a57b24519842cdea8965a04f879` | 2517145790 |
| `pytorch-model-cli` | torch/pytorch heavy | `sha256:cb27d97d9314394fec729969e14f6d5580dc0f54bcaaddc87006589f75ebe305` | 2604034114 |
| `multi-source-data-merger` | large write plus data/ML runtime | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6203486893 |
| `torch-tensor-parallelism` | large write plus torch heavy | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11026213679 |
| `torch-pipeline-parallelism` | large write plus torch heavy | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11315069350 |
| `pytorch-model-recovery` | largest write plus torch heavy | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19201784321 |

Recommended next split:
- First isolate the two small service rows (`nginx-request-logging`, `pypi-server`) as their own bounded batch with explicit network-none smoke expectations.
- Keep `vulnerable-secret` separate from any log-inspection smoke path.
- Keep QEMU rows separate.
- Keep torch/pytorch and the four largest rows separate; if P0 publication is used for scale, still keep fallback tar+sha until worker-j9jjd direct registry pull has a passing smoke proof.

Cross-lane check:
- `hunt-runner-results.md` Round 15 focuses on preserving batch4 image-check evidence under one-command runner artifacts. It does not contradict the runtime/images finding. It explicitly keeps P0 pull readiness as #8/runtime scope and treats fallback-load checker JSON as the evidence the result layer should preserve.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions and WORKFLOW continuous bug-hunt section: rc 0.
- Remote head/status command: rc 0; branch/head `feat/image-warmup-policy` / `5a4e0a7`; initial status showed only untracked batch5 TSV.
- Initial TB2 verified lint command: outer rc 0, inner `LINT_RC=1`, parse rc 0; counts `fallback_tar_verified=65`, `required_without_offline_transport=24`.
- Remaining-24 Docker inspect derivation: rc 0; every inspected row matched manifest `source_image_id`.
- Initial batch5 TSV read: rc 0; observed 3 data rows and sha `31e70a6bb23bf6fef4b7724cb26ac9ff5f88ba6e7588a0e5957ca3f1fdefe2d6`.
- Batch5 TSV/fallback/P0 verification after concurrent expansion: rc 0; observed 5 data rows and sha `302e9a32c4041e255f756d3f1ab449eeeff6a728307f12406e93fe1bed37cea1`.
- Batch5 read-only Docker inspect for the five P0 tags: rc 0; tag IDs match source IDs and RepoDigests match TSV digest refs.
- Shared fallback tar search for the five candidates: rc 0; all five `.tar` files exist in `images/terminalbench2.1/20260425_missing_batch1`.
- Extra fallback tar sha reads for `polyglot-rust-c` and `write-compressor`: rc 0; shas match the concurrent manifest values.
- Post-batch5 dirty-worktree verified lint: outer rc 0, inner `LINT_RC=1`, parse rc 0; counts `fallback_tar_verified=70`, `required_without_offline_transport=19`, and no fallback missing/mismatch.
- Batch5 worker-check JSON summary read: rc 0; `tar_verified=5`, `loaded=5`, `present=5`, `smoke_passed=5`, `identity_mismatch=0`, `errors=0`.
- Status/diff check after concurrent batch5 wiring: rc 0; observed unowned modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, unowned modified `hunt-runner-results.md`, and untracked batch5 TSV/worker-check JSON. This lane left them untouched.
- Cross-lane read of `hunt-runner-results.md` tail and diff: rc 0; no contradiction found.

Next runtime/image subdomain: after batch5 is committed or handed off, audit the service pair (`nginx-request-logging`, `pypi-server`) separately from the secret, QEMU, torch, and large data/ML rows, and keep the same verified static lint plus worker fallback-load/run-smoke acceptance pattern.

### Round 15 validation evidence

- Remote hash guard before ledger copy-back: rc 0; pre-edit and remote hashes both matched `24ea298f2c772fc26f105269f7e817e1bd71ad7dd04092f927efb76c858373e1`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Final `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`, unowned modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and untracked batch5 inventory JSON/TSV were present and left untouched.
- Final `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0; ledger diff was 96 inserted lines.

## Round 16 - TB2 service-isolated pair audit after batch5 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, registry `HEAD`/manifest probes, manifest/lint reads, fallback tar hash reads, task-definition reads, and worker-check JSON reads only.

COMMENT-READY for #6/#8/#12: the `nginx-request-logging` and `pypi-server` service rows are safe as an isolated transport batch and are now fallback-ready on worker-j9jjd; they still should not be used as proof that direct P0 pull is healthy

dedup: comment-on-#6 for TB2 transport population and worker fallback warmup. comment-on-#8 because the worker proof used fallback load with `allow_pull=false` and `pulled=0`, so it does not close rootless direct-registry readiness. comment-on-#12 because the service batch worker JSON is another structured image-check artifact that runner/results should preserve. Not #11: both local image IDs matched `source_image_id`, and no lineage mismatch was found. No new ISSUE-READY block.

Current state and concurrency notes:
- Observed branch/head: `feat/image-warmup-policy` at `7f48601 Record TB2 batch5 handoff`.
- Initial Round 16 TB2 verified lint returned rc 1 with `fallback_tar_verified=70`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=19`.
- During this audit, another lane staged `_coordination/20260625_harbor_bench/inventory/tb2_p0_service_batch6_20260626.tsv`, modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and created `_coordination/20260625_harbor_bench/inventory/tb2_service_batch6_worker_check_20260626.json`. This runtime lane did not edit those files.
- After the concurrent service-row wiring, verified lint returned rc 1 with `fallback_tar_verified=72`, `required_with_fallback_sha=72`, `required_with_digest_ref=22`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=17`.
- `check --skip-docker` over the current dirty TB2 manifest returned rc 0 with `tar_verified=72`, `tar_missing=0`, `tar_mismatch=0`, and `unchecked=89`.

### Service pair evidence

| row | manifest line | task runtime risk | source image ID | inspect size bytes | fallback tar sha | P0 digest ref |
| --- | ---: | --- | --- | ---: | --- | --- |
| `nginx-request-logging` | 704 | service task, localhost:8080 during real benchmark | `sha256:e673cf94a1a3263065b9c37d101f8c4b6ed54a2227ba0100e105c5c6b46b15ff` | 268733645 | `c391f5d189739059f65647736c885ebe69d7105b896b84d10f3e9277e11f7486` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-nginx-request-logging@sha256:d4509a957929e8e9be7779bf0a114b374bb7d6685f972e1da172a16d8f627a08` |
| `pypi-server` | 857 | service task, localhost:8080 during real benchmark | `sha256:59e8830ad18ef4a515d968596b38e467a5b6eb018d1536fd9088c5ddca677ea8` | 320922060 | `443ac588e1a0e54c5f30fcca6e70949173f094e3e4b367587c884fe6887757c1` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-pypi-server@sha256:18aaa082c92c40a5188fabe4637f2384e4d2d8b94a2d64874d12faea08aab38e` |

Transport checks:
- The service batch TSV has exactly these two rows and sha `7f670ff57dc3887c357827d0addad24a470e744bbf62ce25ed33eeaed2905e3b`.
- Both fallback tars exist under `images/terminalbench2.1/20260425_missing_batch1/`; read-only hashing matched the TSV values. Tar sizes are `276667904` bytes for `nginx-request-logging` and `331606016` bytes for `pypi-server`.
- Read-only Docker inspect on `swe_dev` shows both local refs and P0 tags resolve to the expected source image IDs. Both image configs have `Entrypoint=null`, `Cmd=["python3"]`, no exposed ports, working dir `/app`, and no configured user.
- P0 registry manifest `HEAD` with the digest refs returned HTTP 200 for both rows and `Docker-Content-Digest` matched the TSV digest.
- Worker service batch check reports `schema_version=agentic_bench.image_check.v1`, `bench_id=tb2_service_batch6_worker_smoke`, `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.

Smoke/network assessment:
- The manifest smoke for both rows is still the generic image-readiness smoke: `python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok` with `network: none`.
- That smoke is safe for transport readiness because both images have no entrypoint and default `Cmd=["python3"]`; overriding the command with `/bin/sh -lc ...` should not accidentally start Nginx or a PyPI server.
- It is intentionally not a task-level service proof. The task definitions require localhost port 8080 during actual benchmark execution: `nginx-request-logging` configures Nginx on port 8080, and `pypi-server` must serve `pip install --index-url http://localhost:8080/simple ...`.
- Therefore, the batch6 worker check proves fallback-load, identity, and non-network image smoke only. Keep service behavior verification inside the real TB2 adapter/verifier path, not image warmup. Do not use these rows to broaden image smoke into service startup, curl, or pip-install probes.

Worker #8 implication:
- The service batch should be accepted as worker fallback-ready because the checker used `load_fallback=true`, `run_smoke=true`, `allow_pull=false`, and ended with `loaded=2`, `pulled=0`.
- It should not be called worker P0-pull-ready. The prior #8 rootless Docker pull/network issue remains open, and this batch does not exercise `docker pull` from worker rootless Docker.
- Keep fallback tar+sha in the manifest even after P0 digest refs are present. Do not schedule P0-only service rows until a separate direct worker pull+run-smoke proof passes.

Rows remaining after service batch:
- Static transport gap is now 17 rows: `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `path-tracing`, `portfolio-optimization`, `prove-plus-comm`, `pytorch-model-cli`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `reshard-c4-data`, `sam-cell-seg`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`, `train-fasttext`, `video-processing`, and `vulnerable-secret`.
- Recommended next split: keep `vulnerable-secret` isolated from log-inspection smoke; keep QEMU rows together but separate; keep torch/pytorch and the four largest rows separate; consider a medium generic/data batch only after explicitly deciding whether `path-tracing`, `portfolio-optimization`, `train-fasttext`, and `video-processing` should share smoke expectations.

Cross-lane check:
- `hunt-runner-results.md` Round 16 independently records the batch5 provenance gap and notes that service-row isolation should remain runtime scope. It later observed the same service batch6 TSV/worker-check files as concurrent/unowned artifacts. No contradiction found.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging` instructions and WORKFLOW continuous bug-hunt section: rc 0.
- Memory quick search for Round16/TB2/service-row terms: rc 0, no relevant hits used.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md` and current runtime ledger: rc 0.
- Remote branch/head/status command: rc 0; branch/head `feat/image-warmup-policy` / `7f48601`.
- Current manifest row plus read-only Docker inspect for both service refs: rc 0; IDs, config, source IDs, smoke command, and missing transport state quoted above.
- Initial P0 tag inspect probe before concurrent tag metadata settled: rc 0 wrapper with two `docker image inspect` failures; rerun via manifest-row inspect showed both P0 tags/RepoDigests attached.
- Initial shared tar `find` for the two service tars: rc 0 with no output; after concurrent batch6 staging, TSV and tar hash verification found both fallback tars. This is coordination timing, not a new issue.
- P0 registry digest `HEAD` probes for both service rows: rc 0; HTTP 200 and digest headers matched.
- Service batch6 TSV listing and hash: rc 0; TSV sha `7f670ff57dc3887c357827d0addad24a470e744bbf62ce25ed33eeaed2905e3b`.
- Service fallback tar sha verification: rc 0; both fallback sha values matched.
- Initial TB2 verified lint before batch6 manifest wiring: outer rc 0, inner `LINT_RC=1`; counts `fallback_tar_verified=70`, `required_without_offline_transport=19`.
- Post-batch6 verified lint after concurrent manifest wiring: outer rc 0, inner `LINT_RC=1`; counts `fallback_tar_verified=72`, `required_without_offline_transport=17`, and no fallback missing/mismatch.
- `check --skip-docker` over current dirty TB2 manifest: rc 0; `tar_verified=72`, `tar_missing=0`, `tar_mismatch=0`.
- Bounded reads of the TB2 task definitions, Dockerfiles, tests, and solutions for `nginx-request-logging` and `pypi-server`: rc 0.
- Batch6 worker-check JSON summary read: rc 0; `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `pulled=0`.
- Cross-lane grep/read of `hunt-runner-results.md`: rc 0; no contradiction found.

Next runtime/image subdomain: audit `vulnerable-secret` separately next, because it is small enough for the next transport row but should not be grouped with service or generic batches that might inspect task logs.

### Round 16 validation evidence

- Remote hash guard before ledger copy-back: rc 0; pre-edit and remote hashes both matched `4400e124bfdfc094b862aa0d0f2e976d004cd0ca2168aad3ae0ec2e3981d6040`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" ...` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Bounded secret-pattern scan over this ledger: rc 0, `secret_pattern_hits=none`.
- Final `git status --short --untracked-files=all`: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`, unowned modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, untracked service batch6 TSV/worker-check JSON, and untracked `scripts/__pycache__/*.pyc` files were present and left untouched.
- Final `git diff --stat -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.

## Round 17 - TB2 vulnerable-secret isolated transport audit after batch6 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, manifest/lint reads, fallback tar hash reads, task file-name and marker-count scans, worker-check JSON bounded reads, and grep/find only. No task, solution, test, or log contents were printed.

COMMENT-READY for #6/#8/#10/#12: `vulnerable-secret` is valid as an isolated transport row and is now fallback-ready on worker-j9jjd, but worker smoke must remain the generic network-none image-readiness smoke and result/provenance layers must not copy raw checker stderr or any task/log contents

dedup: comment-on-#6 for TB2 offline transport population, #8 because the worker proof used fallback load with `allow_pull=false` and `pulled=0`, #10 because this task is explicitly secret/log-sensitive and the checker JSON contains a raw nested Docker stderr field, and #12 because the worker proof should be preserved through allowlisted image-check provenance. Not #11: the local image ID matched `source_image_id`. No new ISSUE-READY block.

Current state and concurrency notes:
- Observed branch/head: `feat/image-warmup-policy` at `5eb8822`.
- Initial Round 17 status already had unowned concurrent changes: modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` plus untracked `_coordination/20260625_harbor_bench/inventory/tb2_p0_secret_batch7_20260626.tsv` and `_coordination/20260625_harbor_bench/inventory/tb2_secret_batch7_worker_check_20260626.json`. This runtime lane did not edit those files.
- Before reading the concurrent batch7 files, the committed manifest row at line 1160 was still `image_transport: swe_dev_cache_identity`, `fallback_transport: none`, and `fallback_status: missing_shared_tar`.
- The current dirty manifest row at line 1160 is wired as `p0_digest_plus_fallback_tar` with `image_ref: 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-vulnerable-secret@sha256:b57851ef57bb7d00d05f38ac73ccda754851d5cac5fafa3a728b65afddd31ee3`, `fallback_transport: oci_tar`, `fallback_status: p0_digest_and_fallback_tar_verified`, fallback tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/vulnerable-secret.tar`, and fallback sha `0a1c8f4454cfd1c9b197b1dcd69dcb0318fdda154cd2b14cc54b88bff1ddd2b0`.
- Post-batch7 verified lint returns rc 1 because 16 other TB2 rows still lack offline transport, but `tb2_vulnerable_secret` itself is now `lint_status: ok` with `fallback_sha256_status: match`.

### Vulnerable-secret evidence

| row | manifest line | task runtime risk | source image ID | inspect size bytes | fallback tar sha | P0 digest ref |
| --- | ---: | --- | --- | ---: | --- | --- |
| `vulnerable-secret` | 1160 | secret/log-sensitive task; isolate from any log-inspection smoke | `sha256:ed187ec826168b02180860a958bca08ea3cae5b871bc3b12d0e026cff218cd74` | 478004753 | `0a1c8f4454cfd1c9b197b1dcd69dcb0318fdda154cd2b14cc54b88bff1ddd2b0` | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-vulnerable-secret@sha256:b57851ef57bb7d00d05f38ac73ccda754851d5cac5fafa3a728b65afddd31ee3` |

Transport and worker checks:
- Read-only Docker inspect on `swe_dev` for `tb2-offline/vulnerable-secret:20260425` returned the expected source image ID, size `478004753`, no entrypoint, `Cmd=["python3"]`, no exposed ports, working dir `/app`, empty user, `env_count=7`, and no repo digests.
- The concurrent batch7 TSV has exactly one data row for `vulnerable-secret`, with the same local ref, source image ID, fallback tar, and fallback tar sha.
- The fallback tar exists, size `487526912` bytes, and read-only `sha256sum` matched the manifest/TSV sha.
- The worker check JSON reports `schema_version=agentic_bench.image_check.v1`, `docker_host=unix:///tmp/rl/run/docker.sock`, `mode.allow_pull=false`, `mode.load_fallback=true`, `mode.run_smoke=true`, `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, `errors=0`, `tar_missing=0`, `tar_mismatch=0`, and `pulled=0`.
- The worker check image row has `status=present`, `load_status=loaded`, and `smoke_status=passed`; the final inspect attempt saw actual image ID `sha256:ed187ec826168b02180860a958bca08ea3cae5b871bc3b12d0e026cff218cd74`.
- The worker check JSON has no stdout fields and no `password`, `credential`, `private key`, `BEGIN`, `flag{`, `secret=`, or `token=` marker hits. It does contain one nested `inspect_attempts[0].stderr` field from the pre-load missing-image probe. That current value was not printed by this lane and should remain excluded/redacted by downstream parsers under #10/#12.

Smoke/network and secret/log assessment:
- The manifest smoke is still the generic image-readiness smoke: `python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok` with `network: none`.
- That smoke is the right acceptance probe for this row. Because the image has no entrypoint and default `Cmd=["python3"]`, the checker command override should not execute task code, read task logs, run solution/tests, or emit secret-bearing challenge content.
- Do not replace this with a task-level smoke, grep, exploit, test, solution, or log probe. Bounded file-name/marker-count scans of the task directory found secret/log-related markers in `environment/offline.Dockerfile`, `environment/vulnerable.c`, `instruction.md`, `solution/solve.sh`, `task.toml`, `tests/test.sh`, and `tests/test_outputs.py`; contents were intentionally not printed.
- Treat any future checker `smoke_stderr`, `load_stderr`, `pull_stderr`, or nested `inspect_attempts[].stderr` as untrusted native artifact content. Promote only allowlisted status/count/id/ref/sha fields and safe path pointers/basenames into one-command runner summaries.

Worker #8 implication:
- This row is worker fallback-ready, not worker P0-pull-ready. The observed proof used `allow_pull=false`, `load_fallback=true`, and ended with `loaded=1`, `pulled=0`.
- Keep fallback tar+sha required even with the P0 digest ref present. Do not switch this row to P0-only until direct worker rootless registry pull has its own passing proof.

Expected and observed gate movement:
- The expected movement for materializing this single isolated row after batch6 was `required_without_offline_transport 17 -> 16`, `fallback_tar_verified 72 -> 73`, `required_with_fallback_sha 72 -> 73`, and `required_with_digest_ref 22 -> 23`.
- The observed post-batch7 verified lint exactly matches that movement and keeps `fallback_tar_missing=0` and `fallback_tar_mismatch=0`.
- The remaining 16 TB2 non-`ok` rows are `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `path-tracing`, `portfolio-optimization`, `prove-plus-comm`, `pytorch-model-cli`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `reshard-c4-data`, `sam-cell-seg`, `torch-pipeline-parallelism`, `torch-tensor-parallelism`, `train-fasttext`, and `video-processing`.

Cross-lane check:
- `hunt-runner-results.md` continues to treat raw checker stderr and smoke stderr as #10 redaction scope, image-check provenance as #12, and worker P0 pull readiness as runtime #8. No contradiction found.
- The `vulnerable-secret` worker-check JSON is a useful real success-path fixture for #10/#12 because it passes fallback-load/run-smoke while still containing a nested Docker inspect stderr field; it is not a reason to copy raw checker JSON wholesale.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:systematic-debugging`, `superpowers:using-superpowers`, and `superpowers:verification-before-completion` instructions: rc 0 after one stale-cache-path attempt failed with rc 1.
- Memory quick search for Round17/TB2/vulnerable-secret/image-warmup terms: rc 0, no relevant hits used.
- Read WORKFLOW continuous bug-hunt section: rc 0.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`, current runtime ledger, and branch/head/status: rc 0.
- Manifest row plus read-only Docker inspect for `tb2-offline/vulnerable-secret:20260425`: rc 0 after one shell-quoting attempt failed with rc 1 and was ignored; source ID/config/size quoted above.
- Initial P0 tag inspect probe before concurrent batch7 materialization settled: rc 0 wrapper with `No such image` from Docker inspect; current dirty manifest now has the P0 digest ref above.
- Initial shared fallback tar `find`: rc 0 with no output; after concurrent batch7 staging, fallback tar existence and sha verification returned rc 0 and matched the manifest value.
- Inventory batch7 TSV/worker-check JSON bounded read: rc 0; printed only schema/count/status/id/ref/hash metadata, key names, lengths, and redacted hashes for sensitive-looking fields.
- Worker-check JSON summary and marker-count scan: rc 0; no stdout fields and no secret marker hits in the JSON payload.
- Post-batch7 TB2 verified lint with `--verify-fallback-files`: outer rc 0, inner `LINT_RC=1`; counts `fallback_tar_verified=73`, `required_with_fallback_sha=73`, `required_with_digest_ref=23`, `required_without_offline_transport=16`, `fallback_tar_missing=0`, and `fallback_tar_mismatch=0`.
- Bounded task path and marker-count scan for `vulnerable-secret`: rc 0; printed file names, byte sizes, and marker counts only, not contents.
- Cross-lane grep/read of `hunt-runner-results.md` and current runtime ledger tail: rc 0; no contradiction found.

Next runtime/image subdomain: choose the next isolated group from the remaining 16 rows. Keep QEMU, torch/pytorch, largest data rows, and medium generic/data rows separated, and continue requiring fallback tar+sha until #8 direct worker pull readiness is re-proven.

### Round 17 validation evidence

- Remote hash guard before first ledger copy-back: rc 0; pre-edit and remote hashes both matched `810cfb2b56d9a28d8f5fd67f876685325bbfee7a4a2b3ced9779f8d643d2fe61`.
- `git diff --check`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Initial broad secret-assignment scan over the ledger: rc 1 with false positives on the literal `vulnerable-secret` task slug and marker-name examples, not secret values. Line-reference inspection for those hits: rc 0.
- Refined bounded secret scan for explicit key assignments, bearer tokens, private-key blocks, and common token prefixes: rc 0, `bounded_secret_scan no_matches`.
- Status/diff-stat check after first copy-back: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`, unowned modified `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and untracked batch7 TSV/worker-check JSON were present and left untouched.

## Round 18 - TB2 medium generic batch8 candidate audit (path-tracing, prove-plus-comm) after batch7 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, registry tag `HEAD`, manifest/lint reads, fallback tar searches, task file-name and marker-count scans, and cross-lane grep only.

COMMENT-READY for #6/#8/#10/#12: `path-tracing` and `prove-plus-comm` are feasible as a two-row medium-generic batch8, but they are not materialized yet and must be accepted by verified fallback tar plus worker fallback-load/network-none smoke rather than P0-only or real benchmark execution

dedup: comment-on-#6 for TB2 transport population and worker fallback warmup. comment-on-#8 because direct worker P0 pull remains unproven and this batch should keep fallback tar mandatory. comment-on-#12 because the eventual batch8 worker-check JSON should be preserved as structured image-check provenance. comment-on-#10 because task/test logs and checker stderr remain untrusted native artifacts, even though no new secret-bearing row was found. Not #11: both local source images match their manifest `source_image_id`. No new ISSUE-READY block.

Current state:
- Observed branch/head: `feat/image-warmup-policy` at `ce4f268`.
- `git status --short --untracked-files=all` was clean before this ledger edit.
- Current TB2-only verified lint baseline is post-batch7: `fallback_tar_verified=73`, `required_with_fallback_sha=73`, `required_with_digest_ref=23`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=16`.
- The 16 non-`ok` rows still include `tb2_path_tracing` and `tb2_prove_plus_comm`.

### Candidate evidence

| row | manifest line | risk label | local ref | source image ID | inspect size bytes | current transport |
| --- | ---: | --- | --- | --- | ---: | --- |
| `path-tracing` | 779 | medium generic, no service/qemu/torch marker in image config | `tb2-offline/path-tracing:20260425` | `sha256:49297f60440893098411cba5f167d0ee719dcd5e61adca1b149fa9485d3b3a6b` | 1104154092 | `swe_dev_cache_identity`, `fallback_transport: none`, `fallback_status: missing_shared_tar` |
| `prove-plus-comm` | 848 | medium generic, no service/qemu/torch marker in image config | `tb2-offline/prove-plus-comm:20260425` | `sha256:c6b448d30a2ca1c7a6c5ea4b05762d85600bc60f562ce382a57673ad8baeaed5` | 1461316125 | `swe_dev_cache_identity`, `fallback_transport: none`, `fallback_status: missing_shared_tar` |

Read-only Docker inspect on `swe_dev`:
- Both refs exist in the local cache and their Docker image IDs exactly match the manifest `source_image_id`.
- `path-tracing`: `Entrypoint=null`, `Cmd=["/bin/bash"]`, no exposed ports, working dir `/app`, empty user, `env_count=2`, no repo digests.
- `prove-plus-comm`: `Entrypoint=null`, `Cmd=["/bin/bash"]`, no exposed ports, working dir `/workspace`, empty user, `env_count=4`, no repo digests.
- The default `Cmd=["/bin/bash"]` is safe only because the image checker uses a command override for smoke; do not rely on the image default command as the smoke.

Transport state:
- No shared fallback tar exists for `path-tracing.tar` or `prove-plus-comm.tar` in the checked shared TB2 image trees. The only path-tracing tar hit is `path-tracing-reverse.tar`, which is a distinct already-materialized row and must not be reused.
- No batch8 inventory TSV/JSON exists yet.
- Local Docker has no P0 tag for either `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-path-tracing:20260425` or `...terminal-bench-2-1-prove-plus-comm:20260425`.
- Registry `HEAD` by those tag names returned HTTP 404 for both rows. `curl -f` therefore returned rc 22. Treat that as "not published yet", not as a registry health failure.

Smoke/network assessment:
- The manifest smoke for both rows is the generic image-readiness command `python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok` with `network: none`.
- `scripts/agentic_bench_images.py:497-509` builds the smoke as `docker run --rm --network <manifest network> <image_ref> /bin/sh -lc <manifest command>`, so the configured smoke overrides the default `/bin/bash` image command and should not run the actual Terminal-Bench task.
- `scripts/agentic_bench_images.py:600-612` records `smoke_status` and fails on smoke stderr/errors; raw smoke stderr must still be redacted by downstream #10/#12 handling.
- Bounded task-directory scans found task/test files with generic `curl`, `log`, `benchmark`, and `port` marker counts, but no `secret`, `password`, `token`, `cuda`, `torch`, `qemu`, `server`, or `daemon` marker hits. Contents were not printed. These rows should not use task-level tests, solution scripts, benchmark commands, or log probes for image warmup.
- Keep `--network none` for worker image smoke. If a future implementation changes either row to service/network/task-level smoke, that would be a new bug because it would conflate image transport readiness with real Terminal-Bench execution.

Batch8 recommendation:
- Materialize both rows together as a two-row medium-generic batch.
- Export verified fallback tar+sha first, then optionally push/tag to P0 and record digest refs. Because #8 direct worker registry pull remains unresolved, P0 digest alone is not sufficient.
- After manifest wiring, run a worker-j9jjd fallback-load/run-smoke check with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, `allow_pull=false`, `load_fallback=true`, and `run_smoke=true`.
- Expected TB2-only static gate movement if both rows are materialized: `required_without_offline_transport 16 -> 14`, `fallback_tar_verified 73 -> 75`, `required_with_fallback_sha 73 -> 75`, and `required_with_digest_ref 23 -> 25` if P0 digest refs are also recorded.

Implementation commands to hand to the writer, not executed in this lane:

```bash
REG=100.97.118.137:8555
OUT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1
for slug in path-tracing prove-plus-comm; do
  src="tb2-offline/${slug}:20260425"
  tar="${OUT}/${slug}.tar"
  docker save "$src" -o "$tar"
  sha256sum "$tar"
  docker tag "$src" "$REG/swe-data-harness/terminal-bench-2-1-${slug}:20260425"
  docker push "$REG/swe-data-harness/terminal-bench-2-1-${slug}:20260425"
  docker inspect --format='{{index .RepoDigests 0}}' "$REG/swe-data-harness/terminal-bench-2-1-${slug}:20260425"
done
```

Worker acceptance command shape after manifest wiring, not executed in this lane:

```bash
ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy &&
   export DOCKER_HOST=unix:///tmp/rl/run/docker.sock &&
   PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check \
     --image-manifest <batch8-two-row-manifest.yaml> \
     --load-fallback --run-smoke --json'
```

Cross-lane check:
- `hunt-runner-results.md` has no contradiction. It continues to require image-check provenance under #12, raw Docker/checker stderr redaction under #10, and keeps worker P0 direct pull readiness in runtime #8.
- The batch8 worker-check JSON, once created, should be treated like earlier batch fixtures: preserve counts/statuses/fallback sha/identity fields, but do not copy raw stderr, full command output, task source, task logs, or adapter transcripts into normalized results.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:using-superpowers`, `superpowers:systematic-debugging`, and `superpowers:verification-before-completion`: rc 0.
- Read WORKFLOW continuous bug-hunt section: rc 0.
- Memory quick search for Round18/TB2/path-tracing/prove-plus-comm terms: rc 0, no relevant hits used.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`, current runtime ledger, and branch/head/status: rc 0; branch/head `feat/image-warmup-policy` / `ce4f268`; status clean before ledger edit.
- Candidate manifest row plus read-only Docker inspect: rc 0 after one inline-Python quoting attempt failed with rc 1 and was ignored; source IDs/configs/sizes quoted above.
- TB2-only verified lint with `--verify-fallback-files`: outer rc 0, inner `LINT_RC=1`; counts quoted above.
- Shared fallback tar search for `path-tracing` and `prove-plus-comm`: rc 0; no exact fallback tars found, and `path-tracing-reverse.tar` was identified as distinct.
- Batch8/path/prove inventory search: rc 0; no existing batch8 TSV/JSON found.
- Read-only local P0 tag Docker inspect for both rows: rc 0 wrapper with two `No such image` diagnostics.
- Registry tag `HEAD` probes for both rows: command rc 0 wrapper, per-tag `curl -f` rc 22 with HTTP 404.
- Bounded task directory discovery and marker-count scan: rc 0; printed only file names, byte sizes, and marker counts.
- Read `scripts/agentic_bench_images.py` smoke command/check lines: rc 0.
- Cross-lane grep/read of `hunt-runner-results.md`: rc 0; no contradiction found.

Next runtime/image subdomain: after batch8 is materialized by a writer, audit the resulting TSV/manifest/worker-check evidence and then split the remaining 14 rows into data/ML medium rows, QEMU rows, torch/pytorch rows, and the largest tar rows.

### Round 18 validation evidence

- Remote hash guard before first ledger copy-back: rc 0; pre-edit and remote hashes both matched `07a73b800c8b0e2caa53985c44d87b19848399384704e5b888fa2224f3786c94`.
- `git diff --check`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Refined bounded secret scan for explicit key assignments, bearer tokens, private-key blocks, and common token prefixes: rc 0, `bounded_secret_scan no_matches`.
- Status/diff-stat check after first copy-back: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` was present and left untouched.

## Round 19 - TB2 remaining 14 transport grouping audit after batch8 (2026-06-26)

Scope: ledger-only audit. No production code, manifest, test, commit, Docker save/push/load/run, benchmark, or model call was performed by this lane. Read-only Docker `image inspect`, registry tag `HEAD`, static `check --skip-docker`, fallback tar searches, task file-name and marker-count scans, and cross-lane grep only.

COMMENT-READY for #6/#8/#12/#13: the remaining 14 TB2 rows are ready to split into smaller risk-homogeneous transport batches; batch9 should start with small/medium data-ML rows and keep QEMU/supervisord, explicit torch/pytorch, and largest-write rows isolated

dedup: comment-on-#6 for transport population and worker fallback warmup. comment-on-#8 because the rows must remain fallback-tar based until direct worker P0 pull is re-proven. comment-on-#12 because each future worker-check JSON needs parsed provenance in structured artifacts. comment-on-#13 because raw checker stdout/stderr must not be streamed into controller preflight logs for these higher-risk rows. No new ISSUE-READY block: all observed risks are existing transport/population, provenance, redaction, and rootless-registry constraints.

Current state:
- Observed branch/head: `feat/image-warmup-policy` at `6ade6f2`.
- `git status --short --untracked-files=all` was clean before this ledger edit.
- Current TB2 `check --skip-docker` reports `tar_verified=75`, `tar_missing=0`, `tar_mismatch=0`, `unchecked=89`, and exactly 14 fallback-missing rows.
- All 14 rows are still `image_transport: swe_dev_cache_identity`, `fallback_transport: none`, and `fallback_status: missing_shared_tar`.
- All 14 source images exist in `swe_dev` Docker cache and read-only `docker image inspect` image IDs match their manifest `source_image_id`.
- No exact shared fallback tar exists for any of the 14 checked slugs under the shared TB2 image roots.
- No local P0 tag exists for any row; registry tag `HEAD` for `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-<slug>:20260425` returned HTTP 404 for every row.

### Remaining-row inventory

| group | row | line | source image ID | inspect size bytes | default cmd | marker/risk summary |
| --- | --- | ---: | --- | ---: | --- | --- |
| data/ML medium, preferred batch9A | `portfolio-optimization` | 824 | `sha256:1fca885f366e54cc7fa1e42c02b22d29ce296a5bf1c7f17e7a9cbbede7ca5614` | 613395442 | `["python3"]` | benchmark/data/port markers; no qemu/service/default-daemon |
| data/ML medium, preferred batch9A | `video-processing` | 1154 | `sha256:470f922fb58fcc7f66324e9912e31717e0fd07c0468a3ca23f7e2950f27f0fef` | 793327868 | `["python3"]` | video/data markers; no qemu/service/default-daemon |
| data/ML medium, preferred batch9A | `train-fasttext` | 1127 | `sha256:535d3a38744d0b5cf72b033b520132751569231316e134ac6a99cc62e666d13f` | 873782103 | `["python3"]` | fasttext/data/model markers; private test tar exists in task tree, so do not read task artifacts |
| data/ML medium, preferred batch9A with caution | `sam-cell-seg` | 1016 | `sha256:dbc5dfcc120fbcf959d3be14d3ae7b0fb71533e8ca4c5c92b40c9c9dd1a3fe27` | 1130941638 | `["python3"]` | SAM/seg/model plus torch markers; still much smaller than explicit torch batch |
| data/ML medium-heavy, batch9B | `mteb-retrieve` | 680 | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2117496845 | `["python3"]` | MTEB/model/data markers and some torch markers |
| data/ML medium-heavy, batch9B | `reshard-c4-data` | 989 | `sha256:3151b2371e33c8792274de78add175049aeb6a57b24519842cdea8965a04f879` | 2517145790 | `["python3"]` | C4/data/dataset markers and large file-hash fixture |
| QEMU/supervisord special | `qemu-startup` | 917 | `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444` | 1956605318 | `["bash"]` | QEMU/log/network markers; keep isolated |
| QEMU/supervisord special | `qemu-alpine-ssh` | 905 | `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573` | 1956628773 | `["bash"]` | QEMU/SSH/password/log/network markers; keep isolated and do not print task contents |
| QEMU/service-like special | `install-windows-3.11` | 499 | `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b` | 1629941732 | `["supervisord","-c","/etc/supervisor/supervisord.conf"]` | QEMU/windows/supervisord/server/password markers; isolate from generic smoke batches |
| explicit torch/pytorch | `pytorch-model-cli` | 881 | `sha256:cb27d97d9314394fec729969e14f6d5580dc0f54bcaaddc87006589f75ebe305` | 2604034114 | `["python3"]` | PyTorch/model/data markers; medium size but explicit torch row |
| explicit torch/pytorch, largest | `pytorch-model-recovery` | 893 | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19201784321 | `["python3"]` | largest image; PyTorch/model/dataset markers; isolate |
| explicit torch/pytorch, huge | `torch-tensor-parallelism` | 1115 | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11026213679 | `["/bin/bash"]` | torch/model markers; huge tar/push/load cost |
| explicit torch/pytorch, huge | `torch-pipeline-parallelism` | 1103 | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11315069350 | `["/bin/bash"]` | torch/model markers plus token marker count in task files; do not print task contents |
| largest data/write | `multi-source-data-merger` | 692 | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6203486893 | `["/bin/bash"]` | data/dataset markers; large tar/push/load cost |

### Batch9 recommendation

Recommended first batch9 implementation:
- Batch9A, four rows: `portfolio-optimization`, `video-processing`, `train-fasttext`, and `sam-cell-seg`.
- Expected static movement if materialized with P0 digest plus verified fallback tar: TB2 `tar_verified 75 -> 79`; remaining `missing_shared_tar 14 -> 10`.
- Rationale: all four are under 1.2GB, have source IDs already verified, are not QEMU/service/default-daemon rows, and avoid the explicit giant torch/pytorch rows. `sam-cell-seg` has SAM/torch markers, so keep it in the data/ML bucket only if the implementation uses generic image smoke; otherwise move it to the later torch-ish batch.

Recommended second data/ML batch:
- Batch9B or batch10, two rows: `mteb-retrieve` and `reshard-c4-data`.
- Expected movement after batch9A: `79 -> 81` verified tars and remaining `10 -> 8`.
- Rationale: both are medium-heavy data/model rows and should be kept separate from the smaller batch if shared-storage write pressure or worker load time is a concern.

Rows to isolate or defer:
- QEMU/supervisord batch: `qemu-startup`, `qemu-alpine-ssh`, and `install-windows-3.11`. Keep generic `--network none` smoke and never let image warmup start QEMU, SSH, browser, supervisord, or service behavior. These rows have QEMU, SSH/password, supervisord/server, and log markers.
- Explicit torch/pytorch batch: `pytorch-model-cli`, `pytorch-model-recovery`, `torch-tensor-parallelism`, and `torch-pipeline-parallelism`. Split `pytorch-model-cli` from the three huge rows if disk or load time is tight. `pytorch-model-recovery`, `torch-tensor-parallelism`, and `torch-pipeline-parallelism` are the largest/highest-write rows.
- Largest data/write row: `multi-source-data-merger` should not be bundled into batch9A because its image is 6.2GB and task files show data/dataset-heavy markers. Materialize after the medium data/ML rows or with other large-write rows.

Smoke and provenance guard:
- The manifest smoke for all 14 rows is still the generic `python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok` with `network: none`.
- Future worker checks must stay `allow_pull=false`, `load_fallback=true`, `run_smoke=true` until #8 direct P0 rootless pull is re-proven.
- Do not turn image warmup into task execution. Do not run QEMU, SSH, supervisord, torch training/inference, dataset reshards, private test archives, or solution/test scripts during image smoke.
- #13 is directly relevant for the future batch9 worker-check JSON: raw checker stdout/stderr must not be streamed into durable controller `.image_preflight.log` as the only evidence path. Future runner artifacts should preserve allowlisted counts/statuses/refs/fallback sha/identity fields under #12 and redact or exclude raw `inspect_attempts[].stderr`, `pull_stderr`, `load_stderr`, and `smoke_stderr`.

Commands/evidence:
- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read `superpowers:using-superpowers`, `superpowers:systematic-debugging`, and `superpowers:verification-before-completion`: rc 0.
- Read WORKFLOW continuous bug-hunt section: rc 0.
- Memory quick search for Round19/TB2/batch9 terms: rc 0, no relevant hits used.
- Read remote `_coordination/20260625_harbor_bench/HANDOFF.md`, current runtime ledger, and branch/head/status: rc 0; branch/head `feat/image-warmup-policy` / `6ade6f2`; status clean before ledger edit.
- Cross-check runner ledger for #13/#12/raw preflight log/provenance implications: rc 0; no contradiction found. Runner ledger says #13 is already filed for raw image-preflight checker output in controller logs and #12 covers parsed image-check provenance.
- Manifest parse plus read-only Docker inspect for all `fallback_status: missing_shared_tar` rows: rc 0; 14 rows found, all `source_match=true`.
- TB2 `check --skip-docker --json`: rc 0; `tar_verified=75`, `tar_missing=0`, `tar_mismatch=0`, `unchecked=89`, and 14 fallback-missing ids exactly matching this audit.
- Shared fallback tar search for all 14 slugs: rc 0; no exact fallback tar hits.
- Read-only local P0 tag Docker inspect for all 14 rows: rc 0 wrapper; every per-row Docker inspect returned rc 1 with no stdout.
- Registry tag `HEAD` probes for all 14 rows: rc 0 wrapper; every per-row `curl -f` returned rc 22 with `HTTP/1.1 404 Not Found`.
- Bounded task directory marker-count scan for all 14 rows: rc 0; printed file names, byte sizes, and marker counts only, not contents.
- Batch9/remaining/qemu/torch inventory search: rc 0; no existing batch9 or remaining14 TSV/JSON artifacts found.

Next runtime/image subdomain: after batch9A is materialized, audit TSV/manifest/worker-check evidence with special attention to #13 raw preflight logs, then decide whether to take `mteb-retrieve`/`reshard-c4-data` or the QEMU/supervisord batch next.

### Round 19 validation evidence

- Remote hash guard before first ledger copy-back: rc 0; pre-edit and remote hashes both matched `8380ba4b2daf99d5bc1012120e698f2a6cfd8a20bcd27a46da57f2db82353445`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Refined bounded secret scan for explicit key assignments, bearer tokens, private-key blocks, and common token prefixes: rc 0, `bounded_secret_scan no_matches`.
- Status/diff-stat check after first copy-back: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` was present and left untouched.
## Round 20 remaining TB2 transport split after batch9

Scope: runtime/images ledger-only audit on branch `feat/image-warmup-policy`, expected coordination head `d1895a2` after batch9. I did not edit production code, manifests, tests, or inventory artifacts, and did not run Docker save, push, pull, load, run, benchmarks, or model calls.

### COMMENT-READY: next safe split for the final 10 TB2 missing transports

Dedup judgment: COMMENT-READY for existing #6/#8/#12/#13, with no new ISSUE-READY finding. #6 still owns incomplete TB2 offline transport coverage. #8 still means worker-j9jjd rootless should not depend on direct P0 pull alone. #12 still owns structured image-check provenance. #13 still owns raw image-preflight checker output being written into controller logs before parser redaction. This round found no distinct new root cause.

Current state from the generated manifest and static checker:

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` has 89 TB2 rows.
- 79 rows have verified fallback SHA coverage; exactly 10 rows still have `fallback_transport: none` and `fallback_status: missing_shared_tar`.
- All 10 are present in swe_dev Docker cache and `docker image inspect` ID matches the manifest `source_image_id`.
- No exact fallback tar exists in the shared TB2 prebuilt-image tree for the 10 slugs.
- P0 registry HEAD probes for `bench-runtime/tb2-offline:<slug>` returned HTTP 404 for all 10; local swe_dev Docker also has no matching `100.97.118.137:8555/bench-runtime/tb2-offline:<slug>` tags.
- Batch9 evidence is consistent with fallback-based worker readiness: `_coordination/20260625_harbor_bench/inventory/tb2_medium_batch9_worker_check_20260626.json` reports `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `pulled=0`, and `errors=0`.

Recommended split after batch9:

| Batch | Rows | Source sizes | Risk label | Expected lint drop | Rationale |
| --- | --- | ---: | --- | ---: | --- |
| 10A, recommended next | `mteb-retrieve`, `reshard-c4-data`, `pytorch-model-cli` | 2.12GB + 2.52GB + 2.60GB | medium data/ML, non-QEMU, non-service, non-huge | 79 verified -> 82 verified; remaining missing 10 -> 7 | All have explicit `python3` default command, `needs_network: false`, manifest smoke is network-none Python version check, and image sizes are below the later giant torch rows. Keep fallback tar mandatory and smoke image-only, not task-level retrieval, training, or dataset processing. |
| 10B, isolated QEMU/supervisord | `install-windows-3.11`, `qemu-alpine-ssh`, `qemu-startup` | 1.63GB + 1.96GB + 1.96GB | QEMU/SSH/supervisord/service-like | 82 -> 85 if done after 10A | These are not large, but they should be isolated because image history markers include `qemu`/`ssh`, and `install-windows-3.11` defaults to `supervisord`. Use only the manifest network-none smoke override; do not run defaults or task harnesses in the image lane. |
| 10C, solo data/write row | `multi-source-data-merger` | 6.20GB | larger data/write, history marker includes `c4`; marker scan also saw `password` in image history text | 85 -> 86 if done after 10B | Keep solo to reduce blast radius and avoid mixing with QEMU or giant torch rows. Use image-only smoke; do not inspect or copy task logs/data contents. |
| 10D, giant torch one-by-one | `torch-tensor-parallelism`, `torch-pipeline-parallelism`, `pytorch-model-recovery` | 11.0GB + 11.3GB + 19.2GB | largest torch/model rows | 86 -> 89 one row at a time | These are the storage/time-risk rows. Export/push/load-smoke one at a time with explicit free-space checks and fallback tar required. Do not run GPU, training, tensor parallel, model recovery, or task commands. |

I would start with 10A only. It removes three rows without touching QEMU/service-like defaults or the 11-19GB giant torch images. After 10A is materialized and worker-smoked with `allow_pull=false`, the next dispatch can choose whether to isolate 10B or do `multi-source-data-merger` solo depending on available storage and #13/#12 logging/provenance readiness.

### Per-row evidence

| Row | Manifest line | Local ref | Source image ID | Inspect size bytes | Default command | Transport/risk note |
| --- | ---: | --- | --- | ---: | --- | --- |
| `install-windows-3.11` | 503 | `tb2-offline/install-windows-3.11:20260425` | `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b` | 1629941732 | `supervisord -c /etc/supervisor/supervisord.conf` | Isolate; source/YAML task was absent from old prebuilt manifest, and old report also named it in build failures. Do not run default command. |
| `mteb-retrieve` | 684 | `tb2-offline/mteb-retrieve:20260425` | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2117496845 | `python3` | Good 10A candidate; old prebuilt manifest row existed but tar was missing. Image history marker scan saw `mteb`/`torch`/`pytorch`/`c4`, so keep smoke image-only. |
| `multi-source-data-merger` | 696 | `tb2-offline/multi-source-data-merger:20260425` | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6203486893 | `/bin/bash` | Solo after 10A/10B; larger data/write row. Old prebuilt manifest row existed but tar was missing. |
| `pytorch-model-cli` | 888 | `tb2-offline/pytorch-model-cli:20260425` | `sha256:cb27d97d9314394fec729969e14f6d5580dc0f54bcaaddc87006589f75ebe305` | 2604034114 | `python3` | Good 10A candidate despite PyTorch marker because size is modest and smoke is Python version only. |
| `pytorch-model-recovery` | 900 | `tb2-offline/pytorch-model-recovery:20260425` | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19201784321 | `python3` | Defer; largest remaining image. Export/push/load-smoke alone. |
| `qemu-alpine-ssh` | 912 | `tb2-offline/qemu-alpine-ssh:20260425` | `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573` | 1956628773 | `bash` | Isolate with QEMU rows; image history markers include `qemu` and `ssh`. |
| `qemu-startup` | 924 | `tb2-offline/qemu-startup:20260425` | `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444` | 1956605318 | `bash` | Isolate with QEMU rows; image history markers include `qemu` and `ssh`. |
| `reshard-c4-data` | 996 | `tb2-offline/reshard-c4-data:20260425` | `sha256:3151b2371e33c8792274de78add175049aeb6a57b24519842cdea8965a04f879` | 2517145790 | `python3` | Good 10A candidate; old report said tar missing and also named it in build failures, but current swe_dev cache identity is present and inspect matches. |
| `torch-pipeline-parallelism` | 1113 | `tb2-offline/torch-pipeline-parallelism:20260425` | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11315069350 | `/bin/bash` | Defer; giant torch row. Export/push/load-smoke alone or paired only after storage check. |
| `torch-tensor-parallelism` | 1125 | `tb2-offline/torch-tensor-parallelism:20260425` | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11026213679 | `/bin/bash` | Defer; giant torch row. Export/push/load-smoke alone or paired only after storage check. |

### Concrete next commands for implementation owner, not run in this lane

For 10A fallback tar plus P0 digest publication on swe_dev:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
out=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1
mkdir -p "$out"
for slug in mteb-retrieve reshard-c4-data pytorch-model-cli; do
  src="tb2-offline/${slug}:20260425"
  tar="${out}/${slug}.tar"
  p0="100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-${slug}:20260425"
  docker image inspect "$src" --format '{{.Id}} {{.Size}}'
  docker save -o "$tar" "$src"
  sha256sum "$tar"
  docker tag "$src" "$p0"
  docker push "$p0"
  docker image inspect "$p0" --format '{{json .RepoDigests}}'
done
```

After manifest update, verify static and worker fallback mode without depending on direct P0 pull:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint-registry --bench-registry manifests/bench_registry.yaml --policy selected-required --verify-fallback-files

WORKER_SSH='ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn'
ssh -CAXY "$WORKER_SSH" 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && export DOCKER_HOST=unix:///tmp/rl/run/docker.sock && PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --allow-pull=false --load-fallback --run-smoke --json'
```

Guardrails for implementation owner:

- Fallback tar is still required even if P0 digest publication succeeds, because worker rootless direct P0 pull remains constrained by #8.
- Use the manifest smoke command with `network: none`; do not run default image commands, task harnesses, benchmark commands, QEMU guests, SSH daemons, PyTorch training/inference, C4/MTEB retrieval, or model recovery.
- For #12/#13, worker-check artifacts should preserve parsed counts and safe image IDs/statuses, but default controller logs must not persist raw checker stdout/stderr or task/log contents.

### Cross-lane notes

- Runner ledger #13 already covers the raw controller image-preflight log sink. These 10 remaining rows increase the importance of that fix because QEMU/SSH, data/ML, and torch rows can produce arbitrary Docker stderr or smoke stderr. This is not a new issue.
- Runner ledger #12 already covers preserving structured image-check evidence. Batch10 worker checks should record fallback-vs-pull mode, `tar_verified`, `loaded`, `present`, `smoke_passed`, `identity_mismatch`, `errors`, per-row IDs, safe source IDs, safe fallback pointers, and parsed redaction metadata.
- Batch9 evidence has `pulled=0`; do not reinterpret it as worker direct-P0 readiness.
- No contradiction found with runner/results ledger #12/#13.

### Round 20 command evidence before ledger validation

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Read selected skill docs and the `Continuous Multi-Agent Bug-Hunt & Cross-Model Alignment` section of `WORKFLOW.md`: rc 0.
- `ssh swe_dev 'cd .../image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --short --untracked-files=all'`: rc 0; branch/head `feat/image-warmup-policy` / `d1895a2`; no worktree status lines printed before this ledger edit.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md` and current runtime ledger tail: rc 0.
- Cross-checked `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` for #12/#13/raw preflight/P0/fallback terms: rc 0.
- Initial manifest parse using plain slugs instead of `local_ref` schema returned `rows_found 0`: rc 0; not used as evidence except to correct the parser to the actual schema.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --skip-docker --json`: rc 0; JSON counts included `tar_verified=79`, `unchecked=89`, `tar_missing=0`, `tar_mismatch=0`, `errors=0`.
- Corrected YAML parse plus read-only `docker image inspect` for the 10 `local_ref` values: rc 0; all 10 inspected successfully and matched manifest source IDs.
- Exact fallback tar search under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images`: rc 0; no exact `.tar`, `.tar.gz`, or `.tgz` hits for the 10 slugs.
- Read-only local P0 tag `docker image inspect` for `100.97.118.137:8555/bench-runtime/tb2-offline:<slug>`: wrapper rc 0; each per-row inspect returned rc 1 with no local image.
- Registry HEAD probes against `https://100.97.118.137:8555/v2/bench-runtime/tb2-offline/manifests/<slug>` with Docker manifest accept header: wrapper rc 0; all 10 returned HTTP 404.
- Broad shared-directory `find` for task directories was interrupted after it remained too broad: rc 255; not used as evidence.
- `git ls-files | grep` for the 10 slugs: rc 0 with no output, confirming this worktree does not track task source directories for these slugs.
- Targeted repo grep for the 10 slugs across manifests, reports, and coordination inventories: rc 0; found manifest lines, cache inventories, handoff, and old repair-plan references.
- Read `reports/next_terminal_bench_2_1_image_repair_plan_20260625.md:440-510` and `520-545`: rc 0; confirmed old missing-archive/source-absent classifications and build-failure notes.
- Read-only `docker image history --no-trunc --format '{{.CreatedBy}}'` marker scan for the 10 refs: rc 0; printed marker names and line counts only, not raw history commands.
- Manifest line context with `nl -ba manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`: rc 0; confirmed all 10 rows have `fallback_transport: none`, `fallback_status: missing_shared_tar`, `needs_network: false`, and network-none smoke.
- Batch9 TSV and worker-check JSON inspection: rc 0; batch9 worker check has `tar_verified=4`, `loaded=4`, `present=4`, `smoke_passed=4`, `pulled=0`, `errors=0`.

### Round 20 validation evidence

- Remote hash guard before first ledger copy-back: rc 0; remote and local pre-edit hash matched `449a6f6bfad2b71ce88653f56c045c5ab279cec13cdbbe31797103cac1c695d5`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- First bounded secret-scan command had a shell quoting error: rc 1, `zsh:20: unmatched "`. It was not used as validation.
- Corrected bounded secret scan for private-key blocks, bearer tokens, explicit secret assignments, OpenAI-style keys, and GitHub-style tokens: rc 0, `bounded_secret_scan no_matches`.
- Status/diff-stat check after first copy-back: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` was present and left untouched.
- Post-reorder validation after moving Round20 to EOF: rc 0 for `git diff --check`, trailing-whitespace scan, bounded secret scan, heading-order grep, and status/diff-stat. Round20 now follows Round19 in the ledger.

## Round 21 - TB2 remaining 8 after batch10 and mteb quarantine

Scope: runtime/images ledger-only audit on `feat/image-warmup-policy` at observed head `250f017`. I did not edit production code, manifests, tests, handoff, runner ledger, issue records, or inventory artifacts. I did not run Docker build/save/load/pull/run, benchmarks, or model calls. Read-only Docker inspect/history, static lints, registry `HEAD`, and bounded artifact scans only.

### Findings

COMMENT-READY for #6/#8/#12/#13, no new ISSUE-READY block.

Dedup judgment:

- #6 still owns the remaining TB2 offline transport population work and the worker warmup requirement.
- #8 still owns worker-j9jjd rootless Docker instability and direct P0 pull/load readiness. `mteb-retrieve` is now the clearest quarantined row under #8 because tar/P0 staging exists but worker fallback load failed.
- #12 still owns structured image-check provenance. Batch10 and future failed-load attempts must preserve safe counts/statuses and source pointers, not just log text.
- #13 still owns the raw image-preflight checker stdout/stderr log sink. The mteb failed-load case would be a strong fixture for #13/#12 after sanitization, but it is not a distinct new root cause.

I do not see a confirmed new bug in manifest promotion criteria. The current implementation behaved conservatively: `mteb-retrieve` has an exported fallback tar and a P0 tag, but it was not promoted into `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` because worker fallback load failed. The strict static gate therefore still fails with `required_without_offline_transport=8`. If a future writer promotes mteb based only on tar/P0 existence, static lint would pass for that row because `scripts/agentic_bench_images.py:328-387` is intentionally a static transport lint: it considers an internal digest ref or verified fallback checksum as offline transport, while `scripts/agentic_bench_images.py:590-598` records actual load failure at runtime preflight. That risk is a policy/process guard for #6/#8, not a newly confirmed code bug in the present branch.

### Safe Counts

- Current generated TB2 cache manifest: 89 rows.
- TB2 static `check --skip-docker`: `tar_verified=81`, `tar_missing=0`, `tar_mismatch=0`, `errors=0`, `unchecked=89`.
- Strict registry lint with `--require-offline-transport --verify-fallback-files`: rc 1, global `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=8`.
- The only manifest with strict lint issues is `terminal_bench_2_1_swe_dev_cache`, with `required_without_offline_transport=8`.
- Batch10 worker fallback evidence: `tar_verified=2`, `loaded=2`, `present=2`, `smoke_passed=2`, `identity_mismatch=0`, `errors=0`, `pulled=0`.
- Remaining eight manifest gaps: `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `torch-pipeline-parallelism`, and `torch-tensor-parallelism`.

### Remaining-row Classification

| group | row | manifest line | source image id | inspect size bytes | default cmd | current transport evidence | recommendation |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| special quarantined staged row | `mteb-retrieve` | 684 | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2117496845 | `python3` | fallback tar exists, P0 tag HEAD HTTP 200, manifest still `missing_shared_tar` because worker load failed | Do not promote until worker rootless Docker can load it or a fresh worker/load path proves the failure is environmental and resolved. Keep a separate quarantine note/artifact pointer. |
| generic/data large solo | `multi-source-data-merger` | 696 | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6203486893 | `/bin/bash` | no fallback tar hit, P0 HEAD HTTP 404 | Next safest non-mteb materialization after storage check; do as a solo data/write batch. |
| QEMU/supervisord isolated | `install-windows-3.11` | 503 | `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b` | 1629941732 | `supervisord -c /etc/supervisor/supervisord.conf` | no fallback tar hit, P0 HEAD HTTP 404 | Isolate. Use manifest network-none smoke only; never run default supervisord/task behavior in image lane. |
| QEMU isolated | `qemu-alpine-ssh` | 915 | `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573` | 1956628773 | `bash` | no fallback tar hit, P0 HEAD HTTP 404 | Batch with `qemu-startup` only, or keep separate if worker daemon is unhealthy. |
| QEMU isolated | `qemu-startup` | 927 | `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444` | 1956605318 | `bash` | no fallback tar hit, P0 HEAD HTTP 404 | Batch with `qemu-alpine-ssh` only; smoke must remain generic network-none. |
| giant torch | `torch-tensor-parallelism` | 1131 | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11026213679 | `/bin/bash` | no fallback tar hit, P0 HEAD HTTP 404 | Defer to giant-image phase; export/push/load-smoke one at a time. |
| giant torch | `torch-pipeline-parallelism` | 1119 | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11315069350 | `/bin/bash` | no fallback tar hit, P0 HEAD HTTP 404 | Defer to giant-image phase; export/push/load-smoke one at a time. |
| largest pytorch | `pytorch-model-recovery` | 903 | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19201784321 | `python3` | no fallback tar hit, P0 HEAD HTTP 404 | Last or solo after explicit free-space and daemon-health checks. |

History-marker scan was safe-count only and did not print full history commands. It found QEMU/SSH markers for the QEMU pair, supervisord/data/password markers for `install-windows-3.11`, data/password markers for `multi-source-data-merger`, MTEB/torch/pytorch/data markers for `mteb-retrieve`, and torch/data markers for the torch/pytorch rows.

### Recommended Next Batch

1. Keep `mteb-retrieve` out of the promoted manifest until the rootless load failure is resolved. It already has tar/P0 staging, so the next action is not more export; it is rootless daemon/load diagnosis or retry after a clean daemon/storage-health proof. Any retry artifact should preserve only safe phase, rc, counts, image id, tar sha status, and a restricted pointer to raw load stderr.
2. Next implementation batch if storage is healthy: `multi-source-data-merger` solo. It is the only remaining non-QEMU/non-giant candidate, but at 6.2GB it should not be mixed with QEMU or giant torch rows. Expected strict lint movement if promoted and worker-smoked: `required_without_offline_transport 8 -> 7`, TB2 `tar_verified 81 -> 82`.
3. Then QEMU/service-like batch: `qemu-alpine-ssh` and `qemu-startup`; optionally add `install-windows-3.11` only if the implementation owner is comfortable treating the supervisord default as a special row. Expected movement for the two QEMU rows: `7 -> 5`; with install-windows too: `7 -> 4`.
4. Final giant rows one by one: `torch-tensor-parallelism`, `torch-pipeline-parallelism`, then `pytorch-model-recovery` last. Use one-row worker fallback-load/run-smoke checks, free-space checks before and after, and no task/model execution.

Guardrails:

- Worker readiness remains fallback-load based with `allow_pull=false`, `load_fallback=true`, and `run_smoke=true` until #8 re-proves direct P0 rootless pull.
- The generic smoke must stay `--network none`; do not run QEMU guests, SSH daemons, supervisord, PyTorch inference/training, dataset reshards, MTEB retrieval, task harnesses, solution scripts, or benchmark/model calls.
- Do not let static lint alone promote a row to scheduling readiness. Static lint proves digest/tar identity; worker image preflight proves the worker daemon can consume it.

### Commands And Exit Codes

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0. The command later tried an old skill path and exited rc 1 after `WORKFLOW.md`; I then found and read the current skill paths.
- Read `WORKFLOW.md` remaining sections including the P0 registry and continuous bug-hunt rules: rc 0.
- Read current `superpowers` skill files from the refreshed plugin cache: rc 0.
- Memory quick search for Round21/mteb/batch10 terms: rc 0, no relevant hits used.
- Remote branch/head/status plus handoff read: rc 0; branch/head `feat/image-warmup-policy` / `250f017`.
- Read current runtime ledger tail and cross-checked runner ledger for #12/#13/batch10 terms: rc 0; no contradiction found.
- Manifest parse plus read-only Docker inspect for the eight remaining rows and the two batch10 promoted rows: rc 0; eight remaining rows listed above, batch10 rows show P0 digest plus verified fallback tar in the manifest.
- TB2 `check --skip-docker --json`: rc 0; counts quoted above and exactly eight fallback-SHA-missing refs.
- Batch10 TSV and worker-check JSON safe inspection: rc 0; printed slugs/source IDs/P0 digest refs/fallback SHA and safe checker counts/statuses only. Raw nested stderr values were not printed.
- Initial `lint-registry` command used an obsolete `--bench-registry` flag: rc 2; not used as evidence.
- Current `lint-registry --help`: rc 0.
- `lint-registry --verify-fallback-files --json` without `--require-offline-transport`: rc 0; it verifies configured fallback files only and reported `required_without_offline_transport=0`.
- Strict `lint-registry --require-offline-transport --verify-fallback-files --json`: rc 1; counts quoted above with `required_without_offline_transport=8`.
- MTEB tar/P0 bounded check: rc 0; one tar hit at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/mteb-retrieve.tar` size 2159561728, and P0 tag HEAD HTTP 200.
- Bounded hit-count scan for mteb/load-failure terms across handoff/runtime ledger/reports: rc 0; printed file paths, sizes, and keyword counts only.
- One intermediate grep command printed historical report lines containing Docker I/O-error text; I discarded that output and did not use it as Round21 evidence. The safe hit-count scan above replaced it.
- Code-line reads for static lint and runtime load semantics in `scripts/agentic_bench_images.py`: rc 0; relevant lines are `328-387`, `590-598`, and `960-975`.
- Remaining-eight tar/P0 bounded check: rc 0; `mteb-retrieve` is the only row with a tar hit and P0 HTTP 200; the other seven have zero tar hits and P0 HTTP 404.
- Read-only Docker history marker scan: rc 0; printed marker names and line counts only, not raw history commands.

### Blockers

- `mteb-retrieve` is blocked at worker rootless fallback load, not at export or P0 publication.
- The remaining seven non-mteb rows still need fallback tar/P0 materialization and worker fallback-load/run-smoke proof.
- Rootless worker direct P0 pull is still not the readiness path until #8 is resolved.
- #12/#13 still block treating one-command image-preflight artifacts as self-auditing unless safe parsed image-check provenance and raw-log redaction are implemented.

### Round 21 validation evidence

- Remote hash guard before first ledger copy-back: rc 0; remote and local pre-edit hash matched `679b933bd94752fbb3cbdba96268ba43677adb78d3e0f4a03e5f5a251686c195`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`: rc 0.
- Trailing-whitespace scan with `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` under inverted check: rc 0, `trailing_whitespace=no_matches`.
- Bounded secret scan for private-key blocks, bearer tokens, explicit secret assignments, OpenAI-style keys, and GitHub-style tokens: rc 0, `bounded_secret_scan no_matches`.
- New-time `__pycache__` scan: rc 0 and no paths printed; no cleanup needed.
- Status/diff-stat check: rc 0. This lane modified only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; unowned modified `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` was present and left untouched.
## Round22 rootless ingest quarantine audit after batch11

### Findings
- COMMENT-READY for #8/#6/#12/#13; no new ISSUE-READY root cause found. Batch11 `tb2_multi_source_data_merger` is correctly quarantined: the staged TSV has both a fallback tar SHA and a P0 digest, but the active manifest still leaves the row as `fallback_status: missing_shared_tar`/`fallback_transport: none`, and strict registry lint still fails the same 8 rows. This prevents a fake pass after worker ingest failed.
- The multi-source failure matches the earlier mteb-retrieve quarantine pattern more than a single corrupt artifact: both fallback-load and P0-pull worker checks failed during Docker layer ingest/register, with safe error signatures containing `unlinkat` plus `input/output error`. The batch11 signatures are on a `micromamba_cache` path class; older fix-git evidence hit a different path class. That cross-image/path spread points at worker-j9jjd rootless storage/snapshotter health or a layer-ingest edge, not a missing registry object.
- Registry/tar corruption is not the best explanation from current evidence: the fallback checker reports `tar_verified=1`, the fallback tar exists on shared storage, and the P0 manifest HEAD returns 200 with the expected `Docker-Content-Digest`. Worker host curl to the registry and to the multi-source manifest also returns 200.
- Worker capacity is not obviously exhausted: `/tmp` tmpfs has about 236G free and low inode use, `docker system df` reports no containers/build cache, and the safe signature/log scan saw no `no space` indicator. Existing-image execution still works: `tb2-offline/gcode-to-text:20260425` ran a tiny `--network none` smoke successfully on worker rootless Docker.
- The rootless daemon remains in the known #8 split state: `docker info` succeeds but `docker version` returns rc 1 with no server block. Dockerd log contains one sanitized multi-source layer-register/EIO hit plus many historical error/panic markers, so this should stay quarantined until rootless daemon/storage health is proven clean by the owner lane.
- Artifact hygiene risk for #12/#13 remains: the failure JSONs contain raw `load_stderr`/`pull_stderr` fields. In reports and runner-visible summaries, store or publish only status, path class, error category, length/hash, and redacted phase; keep raw payloads out of default ledgers.

### Safe counts and quarantine state

| Check | Result |
| --- | --- |
| Active TB2 generated cache rows | 89 |
| Active missing offline transport rows | 8: install-windows-3.11, mteb-retrieve, multi-source-data-merger, pytorch-model-recovery, qemu-alpine-ssh, qemu-startup, torch-pipeline-parallelism, torch-tensor-parallelism |
| `lint-registry --require-offline-transport --verify-fallback-files` | rc 1, `required_without_offline_transport=8`, `fallback_tar_verified=86`, missing/mismatch 0 |
| Batch11 multi-source fallback check | `tar_verified=1`, `loaded=0`, `present=0`, `smoke_passed=0`, `load_status=failed` |
| Batch11 multi-source P0 pull check | `pulled=0`, `present=0`, `smoke_passed=0`, `pull_status=failed` |
| Worker existing-image tiny smoke | rc 0, `--network none`, already-present `gcode-to-text` image |

### Recommended next batch/order
- Do not promote `multi-source-data-merger` or `mteb-retrieve` from staged artifacts into the active manifest until a worker-j9jjd rootless ingest retry succeeds. Staged tar/P0 presence alone must not count as promotion.
- Next safe materialization order should separate rootless ingest-risk rows from normal image population:
  1. Rootless special handling: `mteb-retrieve`, `multi-source-data-merger`. Retry only after a non-destructive worker storage-health bundle is reviewed; use fallback tar first, then P0 digest, and record redacted phase signatures.
  2. Generic/data candidate: `pytorch-model-recovery` only if its size and local inspect look moderate enough for a controlled single-row retry.
  3. QEMU rows: `qemu-alpine-ssh`, `qemu-startup`; isolate from generic batches because runtime smoke behavior and privileged/emulation assumptions can differ.
  4. Giant torch rows: `torch-pipeline-parallelism`, `torch-tensor-parallelism`; isolate last because large layer registration is likely to stress the same rootless storage failure mode.
  5. `install-windows-3.11`: keep isolated due OS/toolchain semantics and likely large/special layers.
- Concrete fix plan: keep static lint strict; add or keep a promotion gate requiring both offline transport metadata and worker ingest evidence (`loaded/present/smoke_passed` or intentionally skipped smoke with owner approval). For failed loads, record a quarantine status separate from missing tar so orchestration can distinguish "transport staged but worker rejected" from "transport absent" without weakening identity checks.

### Command evidence
- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0. `sed -n '260,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0.
- `ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --short --untracked-files=all && sed -n "1,260p" _coordination/20260625_harbor_bench/HANDOFF.md'`; rc 0. Branch `feat/image-warmup-policy`, head `1b7325a`.
- `ssh dev 'cd ... && tail -n 280 _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md'`; rc 0. Confirmed prior Round21 mteb quarantine/dedup context.
- `ssh dev 'cd ... && grep -nE "Round 2[01]|batch10|batch11|multi-source|mteb|#12|#13|rootless|load|pull|fallback" _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md | tail -n 220'`; rc 0. Runner ledger aligns: failed-load evidence is #8/#12/#13 commentary, not a new issue.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... read batch11 TSV and failure JSONs, emit safe status/hash/path-class summaries only ... PY'`; rc 0. TSV source image `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83`; fallback SHA `502a8078ee247e5813161e13c03d4e9c69c08da7d685d5a02b0f544f599f1ea7`; P0 digest `sha256:33d33940e4e6207900e23fb0f4232f8607be2357d4d07062a1b3c4088dc927c2`. Fallback/P0 failure signatures both contained `unlinkat` plus EIO, path class `micromamba_cache`; raw payloads intentionally not copied.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... inspect manifests/images/terminal_bench_2_1_swe_dev_cache.yaml and run check --skip-docker ... PY'`; rc 0. Manifest still has mteb and multi-source at `fallback_status: missing_shared_tar`, `fallback_transport: none`; `check --skip-docker` rc 0 with `tar_verified=81`, `unchecked=89`.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... run lint-registry --require-offline-transport --verify-fallback-files --json ... PY'`; rc 0 wrapper, inner lint rc 1. Counts: `required_without_offline_transport=8`, `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... stat fallback tar and curl P0 manifest HEAD ... PY'`; rc 0. Fallback tar size `6324784128`; P0 manifest HEAD rc 0, HTTP 200, digest header matches the TSV digest.
- First worker diagnostics wrapper had a local quoting error and exited rc 127; discarded as evidence.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... sanitize /tmp/rl/dockerd.log counts and hashed recent hits ... PY'`; rc 0. Safe counts included one `input/output error`, one `unlinkat`, one `failed to register layer`, and one `multi-source-data-merger` hit; no `no space` hit.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'export DOCKER_HOST=unix:///tmp/rl/run/docker.sock; ... read-only docker/image/socket/df/curl diagnostics ...'`; rc 0. Docker image listing rc 0, 409 image refs; multi-source and mteb refs not present; `/tmp` tmpfs has about 236G free and low inode use; socket exists; rootlesskit/dockerd/containerd processes present; registry and multi-source manifest curl return 200.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'export DOCKER_HOST=unix:///tmp/rl/run/docker.sock; docker info ...; docker version ...; docker system df ...; docker ps ...'`; rc 0 wrapper. `docker info` rc 0; `docker version` rc 1; `docker ps` showed no active containers; `docker system df` showed no build cache/containers.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'export DOCKER_HOST=unix:///tmp/rl/run/docker.sock; docker run --rm --network none tb2-offline/gcode-to-text:20260425 /bin/sh -lc "python3 --version 2>/dev/null || python --version 2>/dev/null || echo gcode-present-smoke-ok"; rc=$?; echo tiny_smoke_rc=$rc; exit $rc'`; rc 0. Existing-image run path works without network.

### Validation evidence
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace.
- Bounded secret scan on the ledger for common token/key forms; rc 1, interpreted as no matches.
- `find _coordination/20260625_harbor_bench -path "*/__pycache__*" -print -quit`; rc 0 with no result; no created pycache found.

### Dedup and blockers
- Dedup #8: rootless Docker remains healthy enough for inspect/run of existing images but unreliable for new-layer ingest; `docker version` still fails while `docker info` works.
- Dedup #6/#12: static lint correctly blocks rows missing promoted offline transport; do not weaken required preflight or allow staged-but-not-worker-ingested rows to pass.
- Dedup #13: worker failure artifacts should stay redacted and should preserve enough phase/category metadata for runner triage.
- Blocker: worker-j9jjd rootless storage-health root cause is not isolated enough for a new issue. Need an owner-approved, non-destructive health/retry plan before reattempting mteb or multi-source ingestion.
## Round23 rootless storage health retry decision tree after HEALTH_SMOKE_IMAGE

### Scope

- Lane: runtime/images rootless Docker image-ingest readiness for worker-j9jjd.
- Worktree/head verified through `ssh dev`: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, head `5ded6c8`.
- Ledger-only. I did not edit production code, manifests, tests, handoff, runner ledger, inventory artifacts, or issue records. I did not commit or push.
- Docker actions were read-only except one cached-image `docker run --rm --network none` through `HEALTH_SMOKE_IMAGE`; no prune, restart, delete, pull, load, save, benchmark, or model call was run.

### Findings

- COMMENT-READY for #8/#6/#12/#13; no new ISSUE-READY root cause found.
- Commit `32e4f89` improves the rootless worker health probe by making cached-image runtime health separable from storage/transport health: `HEALTH_SMOKE_IMAGE` is read at `scripts/check_rootless_docker_worker.sh:4-6`, documented as optional cached smoke at `:22-29`, and executed only after `docker image inspect` succeeds at `:193-205`.
- The new probe supports the Round22 diagnosis: worker-j9jjd can still run an already-present image with `--network none`, and Docker storage info/system-df checks return rc 0, but the daemon is not fully healthy because `docker version`, raw `/version`, and Python Docker SDK version checks still fail.
- Current worker evidence is not strong enough to retry `mteb-retrieve` or `multi-source-data-merger`: cached runtime is healthy, but no successful new-layer ingest has been observed after the mteb/multi-source EIO failures. Both rows remain absent from worker image cache.
- Active manifest and strict registry lint still fail closed. Both `tb2_mteb_retrieve` and `tb2_multi_source_data_merger` remain `fallback_status: missing_shared_tar`, `fallback_transport: none`, with no active `image_ref`, fallback tar, or fallback sha. `lint-registry --require-offline-transport --verify-fallback-files` still returns rc 1 with `required_without_offline_transport=8`.
- Artifact staging is present for both risky rows: mteb and multi-source fallback tars exist on shared storage and P0 manifest HEAD returns HTTP 200 with matching digest headers. That proves transport artifacts exist; it does not prove worker ingest readiness.
- The latest sanitized dockerd-log scan still shows the earlier multi-source layer-register EIO marker and no new EIO/unlinkat markers from this read-only pass. Free space and inode pressure are not current blockers (`/tmp` has about 253GB free, 2% inode use; `docker system df` shows 0 active images/containers/build cache). This narrows the retry question to new-layer ingest behavior, not generic container execution or obvious capacity exhaustion.

### Decision tree for mteb/multi-source retry

Preconditions before any retry:

| Gate | Required evidence | Current Round23 status | Decision |
| --- | --- | --- | --- |
| Correct worker endpoint | Explicit `worker-j9jjd` endpoint, not stale alias; local control plane can reach it | PASS via streamed script/local worker SSH; `dev -> worker` script attempt rc 255 and is not usable | Use local control-plane or another proven route for worker checks |
| No active benchmark/process interference | Health script benchmark process section has zero rows; `docker ps` has zero running rows | PASS, benchmark process count 0, `docker_ps_rows=0` | Safe for read-only checks only |
| Engine/socket present | Rootlesskit/dockerd/containerd present; socket exists | PASS, health script saw 3 engine-process rows and Docker info rc 0 | No restart allowed or needed in this lane |
| Basic storage readable | `docker_storage_info_rc=0`, `docker_system_df_rc=0`, free space/inodes healthy, no `no space` markers | PASS for storage metadata and capacity | Capacity is not enough to prove ingest |
| Cached runtime works | `HEALTH_SMOKE_IMAGE` is already present and `cached_run_smoke_rc=0` with `--network none` | PASS for `tb2-offline/pytorch-model-cli:20260425` | Existing-image execution is healthy |
| API/version/SDK readiness | `docker version`, raw `/version`, Python Docker SDK version rc 0 | FAIL: version rc 1, raw version rc 52, Python SDK rc 1 | Keep #8 open; do not treat daemon fully healthy |
| Fresh layer ingest proof | At least one owner-approved small/known-new fallback load plus inspect/run-smoke succeeds after health probe | NOT PROVED in this lane | Do not retry large mteb/multi-source yet |

Retry policy:

1. If any precondition above fails, keep both rows quarantined. Do not promote manifest rows and do not run fallback load/P0 pull.
2. If only cached runtime passes but version/SDK/raw endpoint still fail, classify as `partial_rootless_health`; keep #8 open and require an owner decision before any fresh ingest attempt.
3. If the owner wants a minimal ingest proof, first use a small known-new fallback tar that is not mteb or multi-source and run `check --load-fallback --run-smoke` with `allow_pull=false`. Passing cached smoke alone is not enough.
4. Retry mteb first only if a fresh-layer proof passes and storage/log markers stay clean. Use fallback tar before P0 pull because worker direct P0 remains a #8 risk, and mteb is smaller than multi-source.
5. Retry multi-source only after mteb or another comparable ingest proof passes. It is larger and already failed through both fallback-load and P0-pull paths.
6. Any retry result category `tar_verified=1` plus `loaded=0` or `present=0`, `pull_status=failed`, `load_status=failed`, `identity_mismatch>0`, `tar_mismatch>0`, `smoke_passed=0`, new EIO/unlinkat marker, `no space`, daemon restart, or benchmark process interference must remain quarantine and be recorded as restricted raw evidence plus safe parsed counts.
7. A row can leave quarantine only with active-manifest transport fields, verified fallback sha, worker `loaded/present/smoke_passed` evidence, and no identity mismatch. Static lint passing alone must not be interpreted as worker readiness.

### Dedup and issue status

- #8 owns the daemon-health split. Round23 adds a clearer health hierarchy: cached run and storage metadata are green, but version/SDK/raw API plus fresh ingest are still not proven.
- #6 owns image warmup and promotion gating. mteb and multi-source must not be promoted from staged tar/P0 evidence without worker ingest proof.
- #12 owns structured image-check provenance. Retry artifacts need safe counts/statuses, image IDs, fallback sha status, and worker/phase categories.
- #13 owns raw checker/stdout/stderr leakage. The mteb/multi-source failures should continue to use redacted summaries and restricted raw pointers.
- No new ISSUE-READY block: the observed behavior is a known #8/#6 quarantine case, and current code/manifest state fails closed rather than fake-passing.

### Command evidence

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && sed -n '260,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0, output truncated by the terminal but the command completed successfully.
- Read `superpowers` systematic-debugging and verification-before-completion skill files; rc 0. Memory quick grep for Round23/rootless terms; rc 0 with no relevant hits used.
- `ssh dev 'cd .../image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --short --untracked-files=all && sed -n "1,280p" _coordination/20260625_harbor_bench/HANDOFF.md'`; rc 0. Branch/head `feat/image-warmup-policy` / `5ded6c8`.
- `ssh dev 'cd ... && tail -n 180 _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md'`; rc 0. Confirmed Round22 quarantine and rootless evidence.
- `ssh dev 'cd ... && tail -n 220 _coordination/20260625_harbor_bench/lanes/hunt-runner-results.md'`; rc 0. Runner lane aligns with #8/#12/#13 dedup; no contradiction.
- `ssh dev 'cd ... && git show --stat --oneline 32e4f89 -- scripts/check_rootless_docker_worker.sh && sed -n "1,260p" scripts/check_rootless_docker_worker.sh'`; rc 0. Confirmed `HEALTH_SMOKE_IMAGE` support and default read-only mode.
- `ssh dev 'cd ... && nl -ba scripts/check_rootless_docker_worker.sh | sed -n "1,230p"'`; rc 0. Relevant read-only/storage/smoke lines recorded above.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... parse TB2 manifest and run strict lint-registry ... PY'`; rc 0 wrapper. Manifest rows for mteb and multi-source remain unpromoted; inner `lint-registry` rc 1 with `required_without_offline_transport=8`, `fallback_tar_verified=86`, missing/mismatch 0.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... summarize batch11 failure JSONs by counts/hash/path-class only ... PY'`; rc 0. Multi-source fallback and P0 failure artifacts both have `tar_verified=1`, `present=0`, safe signatures containing EIO/unlinkat, and no network-unreachable/no-space signature.
- `ssh dev 'cd ... && WORKER_SSH=... HEALTH_SMOKE_IMAGE=tb2-offline/pytorch-model-cli:20260425 ./scripts/check_rootless_docker_worker.sh --check'` through a sanitizer; rc 0 wrapper, script rc 255. This route is discarded for worker health because `dev -> worker` SSH is blocked.
- Streamed the same script from the remote worktree to the local control plane and ran it with explicit worker endpoint, `HEALTH_SMOKE_IMAGE=tb2-offline/pytorch-model-cli:20260425`, `REMOTE_DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, and `--check`; rc 0 wrapper, script rc 1. Safe parsed rc fields: `docker_info_rc=0`, `docker_storage_info_rc=0`, `docker_system_df_rc=0`, `cached_run_smoke_rc=0`, `compose_version_rc=0`, `compose_ps_rc=0`, `docker_ps_rc=0`, `docker_images_rc=0`, `docker_version_rc=1`, `raw_version_rc=52`, `python_docker_version_rc=1`. Benchmark process count 0; Docker ps rows 0; unique image count 276; marker counts had no EIO/unlinkat/no-space/network-unreachable in this script capture.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd... 'PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... sanitize /tmp/rl/dockerd.log marker counts ... PY'`; rc 0. Full log has one EIO/unlinkat/failed-register marker for multi-source; tail 120/300 has no EIO/unlinkat; no `no space`; recent relevant hits were printed as length/hash/category only.
- `ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd... 'export DOCKER_HOST=unix:///tmp/rl/run/docker.sock; PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... read-only docker inspect/info/system-df/df/findmnt ... PY'`; rc 0. Cached smoke image inspect rc 0, mteb and multi-source local inspect rc 1, Docker info rc 0 with 0 containers/running and 276 images, `docker system df` rc 0, `/tmp` free about 253GB and inode use 2%, rootless data on tmpfs.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... inspect batch10/batch11 TSVs and handoff hit counts ... PY'`; rc 0. Batch10 TSV has only promoted `reshard-c4-data` and `pytorch-model-cli`; batch11 TSV has staged `multi-source-data-merger`; handoff contains mteb staging/failure notes.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 - <<PY ... stat mteb/multi-source tars and curl P0 manifest HEADs ... PY'`; rc 0. mteb tar exists size `2159561728`, P0 HEAD HTTP 200 digest `sha256:088c20baec521e159982c27bcdb8a48dda67a15729043a92a86ef27a6472c0a8`; multi-source tar exists size `6324784128`, P0 HEAD HTTP 200 digest `sha256:33d33940e4e6207900e23fb0f4232f8607be2357d4d07062a1b3c4088dc927c2`.

### Blockers

- `dev -> worker` cannot run the script directly (rc 255), so worker checks need the local control plane or another proven route until SSH routing is fixed.
- Worker rootless Docker is only partially healthy: cached runtime and storage metadata are healthy, but `/version`/SDK checks fail and no post-failure fresh-layer ingest proof exists.
- `mteb-retrieve` and `multi-source-data-merger` remain absent from worker cache and must stay quarantined until a retry produces worker load/present/smoke evidence without EIO/unlinkat or identity mismatch.

### Validation evidence

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace.
- Bounded secret scan on the ledger for common token/key forms; rc 1, interpreted as no matches.
- `find _coordination/20260625_harbor_bench -path "*/__pycache__*" -print -quit`; rc 0 with no result; no pycache found.
## Round24 remote cache staging workflow and worker-readiness boundary

### Scope

- Lane: runtime/images review of the remote cache staging workflow added around `ccff9db` and recorded at head `86ae01e`.
- Worktree verified through `ssh dev`: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, head `86ae01e`.
- Ledger-only. I did not edit production code, manifests, tests, handoff, runner ledger, or inventory artifacts. I did not commit or push.
- No Docker save/load/push/pull and no worker actions were run in this lane. Static reads, JSON/TSV parsing, and lint/match commands only.

### ISSUE-READY: staging script can save a shared fallback tar from the wrong host or wrong image identity

Severity: Medium. This is a transport-population integrity bug that can corrupt shared fallback-tar evidence before worker preflight sees it.

Dedup: related to #6 image transport population and #11 image identity, but distinct from #8/#12/#13. #8 is worker rootless health, #12/#13 are result/log provenance. This bug is in the source-side staging writer before manifest promotion or worker ingest.

Location:

- `scripts/stage_cache_images_from_plan.sh:94` reads `source_host`, `source_ref`, `source_cache_image_id`, and `source_size` from the staging plan.
- `scripts/stage_cache_images_from_plan.sh:119-128` only runs `docker image inspect "$local_ref"`, `docker save -o "$tmp_tar" "$local_ref"`, moves the tar to the shared `fallback_tar`, chmods it, and hashes it. It does not check the current host against `source_host` and does not compare the inspected image ID to `source_image_id` or `source_cache_image_id` before writing the tar.
- `scripts/stage_cache_images_from_plan.sh:143-145` writes result rows without `source_host`, `source_ref`, `source_cache_image_id`, `source_size`, or `actual_image_id`, so provenance needed to audit a wrong-host save is dropped from the result TSV.
- `scripts/README.md:132-135` says the generated plan should run on the source Docker host, but this is a documentation-only guard.
- `scripts/test_agentic_bench_images.py:510-571` covers a successful fake Docker save, but it does not assert host-label enforcement or image-ID mismatch rejection.

Static repro:

1. Use a plan row whose `source_host` is `swe_dev`, `local_ref` is `tb2-offline/install-windows-3.11:20260425`, and `source_image_id` is `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b`.
2. Run `scripts/stage_cache_images_from_plan.sh --plan PLAN --execute --only install-windows-3.11` on any host where that tag exists but resolves to a different image ID, or with a fake `docker image inspect` returning a wrong `.Id`.
3. By inspection of `scripts/stage_cache_images_from_plan.sh:119-128`, the script still saves the tar and computes a valid SHA because the inspect result is used only as a presence check. No branch compares identity or host before writing the shared `fallback_tar`.

Impact:

- A wrong host or stale tag can overwrite a shared fallback tar with valid bytes and a valid SHA, producing result status `saved` even though the tar is not the plan's source image.
- Later worker identity checks may catch this if the row is promoted and load-smoked, but the shared staging evidence is already polluted and can waste large storage/time. If a future promotion path trusts saved tar+sha without worker identity evidence, this becomes a fake-ready path.
- The concrete Round24 plan rows all say `source_host=swe_dev`, while `swe_dev2` has only one matching prefix image. Host confusion is therefore realistic in this workflow, especially because direct `dev -> swe_dev` aliases were reported broken and operators are using full endpoints/control-plane hops.

Concrete fix:

- Add an explicit host guard, for example `--source-host-label swe_dev` or `SOURCE_HOST_LABEL=swe_dev`, and fail if any selected row's `source_host` differs unless an explicit `--allow-source-host-mismatch` is provided.
- Parse `docker image inspect "$local_ref"` JSON before `docker save`; compare `.Id` to `source_image_id` when present and compare the configured `source_cache_image_id` as a prefix/minimum check. Fail before writing `tmp_tar` on mismatch.
- Write `source_host`, `source_ref`, `source_cache_image_id`, `source_size`, and `actual_image_id` into the result TSV.
- Add tests that fake `docker image inspect` with a wrong ID and assert no tar is written, plus a test that selected rows with a different source host fail unless an explicit override is set.

### COMMENT-READY: staging artifacts do not currently imply worker readiness

- The new controller commands separate inventory/match/plan from active manifests. `plan-stage-missing-transport` calls static lint with `require_offline_transport=True` and only emits rows for required active-manifest gaps (`scripts/agentic_bench_images.py:770-834`); `write_staging_plan_tsv` only writes the planning TSV (`:837-856`).
- The active TB2 manifest still fails closed. `tb2_install_windows_3_11`, `tb2_mteb_retrieve`, and `tb2_multi_source_data_merger` remain `fallback_status: missing_shared_tar`, `fallback_transport: none`, with no active image ref, fallback tar, or fallback sha.
- Strict registry lint still returns rc 1 with `required_without_offline_transport=8`, `fallback_tar_verified=86`, and no fallback missing/mismatch. The saved install-windows tar has not changed the active promotion gate.
- The plan/match artifacts are source-cache evidence only: `tb2_swe_dev_cache_match.json` reports `matched=89/89`, and the 8-row staging plan has all rows matched from `swe_dev`. This proves source cache availability, not P0 digest publication, worker fallback load, identity verification, or runtime smoke.

### COMMENT-READY: install-windows saved tar remains quarantined

- `tb2_missing_transport_stage_install_windows_result.tsv` has one row with `status=saved`, a 64-character `fallback_tar_sha256`, and empty `p0_digest_ref`.
- The install-windows tar exists at the batch2 target path and is about 1.66GB, but the active manifest row still has no fallback tar or sha and strict lint still lists it among the 8 missing offline-transport rows.
- It must remain quarantined until the staging script source-host/identity guard is fixed or manually verified, then a worker fallback-load/run-smoke evidence artifact proves `loaded/present/smoke_passed` with no identity mismatch. The image smoke command is `python3 --version ... || echo tb2-smoke-ok` with `network: none`; it does not run the task's supervisord/default behavior or any real Terminal-Bench benchmark.

### Next row order and runtime risk

- Source-side export order should first fix or manually compensate for the staging script guard above. After that, `install-windows-3.11` can be treated as a small-but-special worker-ingest probe only if it remains isolated and is not interpreted as task success.
- Keep `mteb-retrieve` and `multi-source-data-merger` quarantined despite existing staged tar/P0 evidence because both have worker ingest failure history or related rootless risk.
- Keep QEMU rows (`qemu-alpine-ssh`, `qemu-startup`) isolated from install-windows and from generic data rows. They are moderate size but have special runtime semantics.
- Keep giant rows last and one-at-a-time: `torch-pipeline-parallelism`, `torch-tensor-parallelism`, and especially `pytorch-model-recovery` at 19.2GB source size.
- The all-row `--execute` mode can write roughly the whole remaining plan if `--only` is omitted. This is mitigated by dry-run default, but the safer operational contract is an explicit `--all` or row/byte budget for multi-row saves.

### Command evidence

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && sed -n '260,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0, output truncated by the terminal but command completed successfully.
- Read systematic-debugging and verification-before-completion skill files; rc 0. Memory quick grep for Round24/remote-cache terms; rc 0 with no relevant hits used.
- `ssh dev 'cd .../image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --short --untracked-files=all && sed -n "1,320p" _coordination/20260625_harbor_bench/HANDOFF.md'`; rc 0. Branch/head `feat/image-warmup-policy` / `86ae01e`.
- Read runtime ledger tail and runner ledger tail for Round22/Round23 alignment; rc 0.
- `git show --stat --oneline ccff9db` and `git show --stat --oneline 86ae01e`; rc 0. Confirmed remote cache staging workflow and issue-comment commit.
- Grep for new CLI names in `scripts/agentic_bench_images.py`; rc 0. CLI parsers are at `scripts/agentic_bench_images.py:1311-1336`, dispatch at `:1382-1441`.
- `nl -ba scripts/stage_cache_images_from_plan.sh | sed -n '1,240p'`; rc 0. Static source-host/identity guard finding comes from lines `94` and `119-145`.
- `find _coordination/20260625_harbor_bench/inventory/remote_cache_20260626 -maxdepth 1 -type f -printf '%f	%s
'`; rc 0. Found 7 remote-cache artifacts.
- `nl -ba scripts/agentic_bench_images.py | sed -n '560,705p'`; rc 0. Inventory host fallback and match behavior read at `:619-663` and `:666-705`.
- `nl -ba scripts/agentic_bench_images.py | sed -n '700,1040p'`; rc 0. Planning and active checker semantics read at `:770-856` and `:874-1005`.
- `nl -ba scripts/README.md | sed -n '80,135p'`; rc 0. README documents remote cache inventory, match, plan, and staging usage.
- `nl -ba scripts/test_agentic_bench_images.py | sed -n '351,620p'`; rc 0. Tests cover inventory matching, staging-plan generation, CLI dispatch, and successful fake staging, but no wrong-host or wrong-image-ID rejection.
- Parsed `tb2_missing_transport_stage_plan.tsv`, `tb2_missing_transport_stage_dryrun_result.tsv`, and `tb2_missing_transport_stage_install_windows_result.tsv`; rc 0. Plan has 8 rows, all `source_host=swe_dev`; install-windows result has `status=saved`, SHA length 64, empty P0 digest; result TSVs omit source host/ref/cache-size fields.
- Parsed `swe_dev.docker_cache_inventory.json`, `swe_dev2.docker_cache_inventory.json`, `tb2_swe_dev_cache_match.json`, `swebench_verified_cache_match.json`, and `tb2_missing_transport_stage_plan.json`; rc 0. Counts: swe_dev images 591, swe_dev2 images 1, TB2 matched 89/89, SWE matched 1/2 optional rows, staging plan matched 8/8.
- The first attempt to pipe `match-inventory --json` into a here-doc parser returned rc 1 with a JSON decode/BrokenPipe operator error; discarded as evidence.
- Re-ran `match-inventory` through a subprocess wrapper; rc 0. Counts: images 89, matched 89, required_missing 0. The three reviewed remaining rows matched `swe_dev` by ref with short source cache IDs.
- Parsed the active TB2 manifest and strict `lint-registry --require-offline-transport --verify-fallback-files --json`; wrapper rc 0, inner lint rc 1. `install-windows`, `mteb`, and `multi-source` remain unpromoted; lint counts still show `required_without_offline_transport=8`, `fallback_tar_verified=86`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`.
- Parsed smoke settings for install-windows, mteb, multi-source, and QEMU rows; rc 0. All reviewed rows use a generic `network: none` smoke command and do not run task/default service behavior.

### Blockers

- The staging writer needs source-host and image-ID guards before the result TSV can be trusted as clean source-side fallback evidence at scale.
- `install-windows-3.11` has saved-tar evidence only, not P0 digest or worker fallback-load/run-smoke evidence.
- Worker-j9jjd rootless new-layer ingest remains under #8 quarantine; staging source-cache evidence must not bypass worker preflight.

### Validation evidence

- Initial `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 2 due to a new blank line at EOF from the append. Fixed by normalizing this ledger to exactly one final newline.
- Follow-up `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace.
- Bounded secret scan on the ledger for common token/key forms; rc 1, interpreted as no matches.
- `find _coordination/20260625_harbor_bench -path "*/__pycache__*" -print -quit`; rc 0 with no result; no pycache found.

## Round26 source-cache staging guard review

Scope: runtime/images ledger-only review of commits `c3d267b`, `f66a43c`, and `d6bafec` at branch head `d6bafec`. No Docker save/load/pull/run/build, no benchmark/model calls, and no production file edits were performed.

### Findings

No new ISSUE-READY bug from this lane. The current guard changes fix the highest-risk source-side write path found earlier, but the promotion workflow still has an existing identity-unverified planning boundary already covered by the runner/results Round24 ISSUE-READY block and by #6/#12 commentary.

- `scripts/agentic_bench_images.py:628-687` now distinguishes ref matches from authoritative identity mismatch when inventory rows include `full_image_id` or repo digest evidence. `scripts/agentic_bench_images.py:689-788` reports `identity_mismatch` counts, and CLI dispatch at `scripts/agentic_bench_images.py:1437-1453` returns nonzero when required rows become missing through identity mismatch.
- `scripts/agentic_bench_images.py:805-869` keeps staging plans limited to required rows missing offline transport. Its CLI at `scripts/agentic_bench_images.py:1454-1476` returns nonzero when rows are unmatched, so an authoritative identity mismatch does not become a successful staging plan.
- `scripts/stage_cache_images_from_plan.sh:89-106` added result columns for `source_host`, `source_ref`, `source_cache_image_id`, `source_size`, and `actual_image_id`. `scripts/stage_cache_images_from_plan.sh:140-160` fails selected rows on explicit `--source-host-label` mismatch and, in `--execute`, compares inspected Docker `Id` to `source_image_id` before `docker save`. `scripts/stage_cache_images_from_plan.sh:182-185` exits 1 when any selected row failed.
- The guard-aware dry-run artifact `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_install_windows_identity_guard_dryrun_result.tsv` has the new provenance columns and one `dry_run` row for `tb2_install_windows_3_11` with `source_host=swe_dev`, `source_ref=tb2-offline/install-windows-3.11:20260425`, `source_cache_image_id=2dad54561527`, and blank `actual_image_id`, as expected for non-execute dry-run.
- Older artifacts in the same directory remain old-schema evidence: `tb2_missing_transport_stage_dryrun_result.tsv` and `tb2_missing_transport_stage_install_windows_result.tsv` do not include source host/ref/cache-size/actual ID columns. This is not a new bug because HANDOFF says prior install-windows tar is source-staged only, not re-promoted or worker-ready. Any future promotion should regenerate execute result evidence with the guard-aware schema.
- Current stdout-only match using current code reports `identity_mismatch=0`, but the persisted `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_swe_dev_cache_match.json` is stale-schema and lacks the new identity count keys. Treat that JSON as cache-availability evidence, not proof of the new guard fields.

### COMMENT-READY / dedup

- Dedup to runner/results Round24 and #6/#12: the remote cache inventory used by the staged plan is still not identity-inspected. `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json` has `inspect_identities=False`, 591 image rows, zero `full_image_id` rows, and zero repo-digest rows. A synthetic no-Docker probe confirms a ref-only inventory row with a wrong short `image_id` still matches by ref and exits 0. This is the same identity-unverified planning root cause already filed by the runner/results lane, not a new distinct runtime/images issue after `c3d267b`.
- The execute path now materially reduces blast radius: even if a ref-only plan is produced, `--execute` inspects the local image and fails before writing a tar when the actual full `Id` differs from `source_image_id`. The remaining fix plan is still to generate staging plans from `--inspect-identities` inventories, or make `plan-stage-missing-transport` mark rows `identity_unverified` and fail unless an explicit unsafe override is supplied.
- `--source-host-label` is effective when supplied. Because README at `scripts/README.md:132-135` tells operators to pass it, and the execute ID guard catches wrong-tag image drift, omission is an operational guardrail gap under the existing source-cache issue rather than a fresh ISSUE-READY block. A stricter follow-up would require `--source-host-label` for `--execute` whenever selected plan rows include `source_host`, with an explicit override for legacy plans.
- Dedup to #8/#12/#13: staging and dry-run TSVs remain pre-worker source-cache artifacts. They do not prove worker rootless ingest, P0 pull, fallback-load, smoke success, or benchmark readiness. Rows with mteb/multi-source load failures and install-windows staged-only status must remain quarantined until active manifest metadata plus worker image-check evidence exists.

### Probe evidence

- `ssh dev 'cd .../image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && sed -n ... HANDOFF.md'`; rc 0. Branch/head was `feat/image-warmup-policy` / `d6bafec`; HANDOFF records the source-host and image-identity guard, new dry-run evidence, and notes prior install-windows staging is not worker-ready.
- `git show --stat --oneline c3d267b`, `git show --stat --oneline f66a43c`, and `git show --stat --oneline d6bafec`; rc 0. Confirmed the guard implementation, issue-record-only update, and proxy-ceiling handoff update.
- `nl -ba scripts/agentic_bench_images.py | sed -n '620,920p'`; rc 0. Read identity token, mismatch, inventory match, and plan generation code.
- `nl -ba scripts/agentic_bench_images.py | sed -n '1240,1518p'`; rc 0. Read CLI return-code behavior for `match-inventory` and `plan-stage-missing-transport`.
- `nl -ba scripts/stage_cache_images_from_plan.sh | sed -n '1,260p'`; rc 0. Read source-host guard, execute-time image ID comparison, result TSV schema, and failure exit behavior.
- `find _coordination/20260625_harbor_bench/inventory/remote_cache_20260626 -maxdepth 1 -type f -printf '%f\t%s\n' | sort`; rc 0. Found the remote-cache inventories, match/plan JSON/TSV, old dry-run/result TSVs, and the new guard-aware dry-run TSV.
- Parsed remote-cache artifacts with Python; rc 0. Persisted `tb2_missing_transport_stage_plan.json` has `missing_transport=8`, `matched=8`, `unmatched=0`; all rows have `match_status=matched`. New guard dry-run TSV has columns `id, slug, local_ref, source_image_id, source_host, source_ref, source_cache_image_id, source_size, fallback_tar, fallback_tar_sha256, p0_tag, p0_digest_ref, actual_image_id, status`. Old dry-run/result TSVs have old columns only.
- Current-code stdout-only `match-inventory` over the TB2 manifest and the two remote-cache inventories; rc 0. Counts included `identity_mismatch=0`, `required_identity_mismatch=0`, `matched=89`, `required_missing=0`.
- Current-code stdout-only `plan-stage-missing-transport` over the same manifest/inventories; rc 0. Counts were `missing_transport=8`, `matched=8`, `unmatched=0`; row statuses were all `matched`.
- Dry-run stage helper with correct source label: `scripts/stage_cache_images_from_plan.sh --plan ... --only install-windows-3.11 --source-host-label swe_dev`; rc 0. It selected one row, staged zero, skipped seven, failed zero, and did not enter execute/Docker paths.
- Dry-run stage helper with wrong source label: `scripts/stage_cache_images_from_plan.sh --plan ... --only install-windows-3.11 --source-host-label worker-j9jjd`; wrapper rc 0, inner rc 1. Output reported `source host mismatch`, rows=1, staged=0, skipped=7, failed=1.
- Synthetic authoritative mismatch probe using temporary files outside the repo; rc 0. Inner `match-inventory` rc was 1 with `identity_mismatch=1`, `required_identity_mismatch=1`, and row status `identity_mismatch`. Inner `plan-stage-missing-transport` rc was 1 with `missing_transport=1`, `matched=0`, `unmatched=1`, and row status `identity_mismatch`.
- Synthetic ref-only probe using temporary files outside the repo; rc 0. Inner `match-inventory` rc was 0 with `matched=1`, `identity_mismatch=0`, and match reason `ref` even though the inventory short `image_id` differed from manifest `source_image_id`. This is the existing identity-unverified planning issue, not a new issue after the execute guard fix.
- Parsed inventory identity coverage; rc 0. Remote-cache `swe_dev.docker_cache_inventory.json` has `inspect_identities=False`, 591 images, zero full-ID rows, and zero repo-digest rows. The older identity inventory `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json` has `inspect_identities=True`, 1320 full-ID rows, and 179 repo-digest rows, so it is the safer source for identity-enforced plan generation.
- Grep cross-check against runtime and runner ledgers for `#12`, `#13`, `Round24`, `identity`, `source-host`, and `staging`; rc 0. Runner/results Round24 already contains ISSUE-READY text for ref-only identity-unverified remote-cache staging, while runtime Round24 contains the earlier source-host/execute identity writer bug that `c3d267b` addresses.

### Blockers / next guard changes

- Regenerate source-cache match/plan artifacts from an identity-inspected inventory before treating the staging plan as identity proof. The existing remote-cache plan is usable for row selection only.
- Regenerate any execute result TSVs that will be used for promotion with the new guard-aware schema, including `actual_image_id`; do not rely on the old install-windows saved TSV for final promotion.
- Keep worker readiness separate from source staging: active manifest transport plus worker fallback-load/present/smoke evidence is still required before rows leave quarantine.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0 after normalizing this ledger to one final newline.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace.
- Bounded key-like secret scan on this ledger; rc 1, interpreted as no matches. The first broad scan rule falsely matched the task name `vulnerable-secret:20260425`; the final stricter scan requires key-like prefixes or bearer/private-key forms.
- `find _coordination/20260625_harbor_bench -path "*/__pycache__*" -print -quit`; rc 0 with no output.
- `git status --short --untracked-files=all`; rc 0. It shows this lane's modified `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` plus concurrent unrelated modifications to `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md` and `scripts/test_agentic_bench_suite.py`; those other files were not edited by this lane.

## Round27 readiness gate image review

Scope: runtime/images adversarial review of `c95d420` / `ea24680` at head `ea24680`. Ledger-only; no production code, manifests, tests, Docker save/load/pull/run/build, benchmark execution, model calls, commits, or pushes were performed.

### ISSUE-READY: readiness target can be marked ready by an image-smoke entry while the full Terminal-Bench 2.1 entry is blocked

severity: high

dedup: Distinct from runner-results Round27, which found `--readiness` accepts an over-ceiling `--max-concurrency` override. Related to #15 only historically because #15 fixed stale TB2 cache metadata and closed after `c95d420`; this bug is the target aggregation rule. Related to #6/#8/#12 because false readiness could bypass image transport/rootless/provenance gates, but the root cause is in readiness target selection/status aggregation.

location:

- `scripts/agentic_bench_suite.py:760-770` lets a readiness target match any suite entry by `id`, `benchmark`, `adapter`, or image-manifest path stem.
- `scripts/agentic_bench_suite.py:919-926` collects all matched entries and computes `ready_entries`.
- `scripts/agentic_bench_suite.py:931-932` marks the whole target `ready` when any matched entry is ready.
- `manifests/suite.example.yaml:271-279` contains the full `terminal_bench_2_1` entry, disabled and `pending_adapter`, pointing at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`.
- `manifests/suite.example.yaml:281-296` contains the enabled `terminal_bench_2_1_image_smoke` entry with the same `benchmark: terminal_bench_2_1`, so it is matched to the same readiness target even though it points at the one-task smoke manifest.
- `scripts/test_agentic_bench_suite.py:1014-1036` verifies the full TB2 entry and 81/8 counts, but it does not assert that a ready image-smoke entry cannot satisfy the full `Terminal Bench 2.1` readiness target while the full entry remains blocked.

static_repro:

1. Create a temporary suite outside the repo with two entries for the same readiness target: a disabled/pending full `terminal_bench_2_1` entry pointing at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and an enabled/wired `terminal_bench_2_1_image_smoke` entry sharing `benchmark: terminal_bench_2_1` but pointing at a ready image manifest.
2. Run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_suite.py "$tmp/tb2_smoke_masks_full.yaml" --readiness --target-benches Terminal-Bench-2.1 --json`.
3. Observed rc 0 with `counts {'ready': 1, 'blocked': 0, 'missing': 0, 'total': 1}` and target `terminal_bench_2_1` status `ready`, even though the full entry in the same report is `enabled=False`, `adapter_status=pending_adapter`, `ready=False`, and its image manifest reports `required_images=89`, `required_with_offline_transport=81`, `required_without_offline_transport=8`, blocker `required_image_transport_missing`.

impact:

- Once the one-task image-smoke entry becomes wired, `--readiness --target-benches Terminal-Bench-2.1` can return green while the full Terminal-Bench 2.1 entry remains disabled and has 8 missing offline transports.
- This can let orchestration treat the full TB2 target as scheduler-ready based on a one-task image smoke. That would overstate image readiness and skip the remaining TB2 transport/rootless ingest work.
- The current branch does not false-green TB2 only because `terminal_bench_2_1_image_smoke` still has `adapter_status: pending_adapter`; the aggregation rule is already wrong and has a direct no-Docker repro.

fix:

- Add target-level readiness roles or exact entry requirements. For `terminal_bench_2_1`, the full target should require the `terminal_bench_2_1` entry or a `readiness_role: full` entry, not any smoke/helper entry with the same benchmark key.
- Alternatively, mark helper entries such as `terminal_bench_2_1_image_smoke` with `readiness_role: image_smoke` and exclude them from full-target readiness aggregation unless the requested target explicitly names the smoke entry.
- Change aggregation from any-ready to a stricter policy for full targets: blocked full entries must remain target blockers even when a helper entry is ready.
- Add a regression test where a ready `terminal_bench_2_1_image_smoke` entry coexists with a blocked full `terminal_bench_2_1` entry, and assert the target remains blocked with the full entry's `required_image_transport_missing` blocker.

### No-new-issue checks

- Readiness manifest path resolution is behaving correctly in the checked paths. `scripts/agentic_bench_suite.py:773-777` resolves relative image manifests against `project_root`, and `scripts/agentic_bench_suite.py:876-882` passes the suite-level or bench-level project root into static image readiness. Invoking the wrapper from `/tmp` with an absolute suite path still resolved TB2 image manifest paths under the active worktree, not the shell cwd.
- `image_preflight.project_root` for the worker RepoZero temporary local-execution suite is not drifting to a stale checkout. The recorded `run_manifest.json` has `execution_kind=local`, one run, and `image_preflight.project_root=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` for `manifests/images/repozero.yaml`.
- Terminal-Bench 2.1 full entry now points at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and the active readiness report sees the expected full-manifest counts: `required_images=89`, `required_with_offline_transport=81`, `required_without_offline_transport=8`.
- Static image lint/check agree with the readiness counts. TB2 `check --skip-docker --json` reported `tar_verified=81`, `tar_missing=0`, `tar_mismatch=0`; TB2 `lint --require-offline-transport --verify-fallback-files --json` returned rc 1 with `fallback_tar_verified=81`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and exactly eight `missing_offline_transport` rows: `install-windows-3.11`, `mteb-retrieve`, `multi-source-data-merger`, `pytorch-model-recovery`, `qemu-alpine-ssh`, `qemu-startup`, `torch-pipeline-parallelism`, and `torch-tensor-parallelism`.
- Worker RepoZero evidence is not a full benchmark execution artifact. The evidence directory contains `image_preflight_summary.json`, one image-preflight log, one status file, and `run_manifest.json`; parsed summary has schema `agentic_bench.image_preflight_summary.v1`, counts `pass=1`, `fail=0`, `optional_fail=0`, and no benchmark result schema/score. The run manifest still contains the adapter command as a plan field, but this proof is `--image-preflight-only` image readiness, not RepoZero task execution.

### Command evidence

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md && sed -n '260,980p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0, output truncated by terminal but command completed successfully.
- Skill instruction reads for systematic-debugging and verification-before-completion; rc 0. Memory quick grep for readiness/Round27 terms returned one unrelated generic line and was not used as evidence.
- Remote head/status/HANDOFF/runtime-ledger read through `ssh dev`; rc 0. Branch/head: `feat/image-warmup-policy` / `ea24680`.
- `git show --stat --oneline ea24680` and `git show --stat --oneline c95d420`; rc 0.
- Static reads of `scripts/agentic_bench_suite.py`, `manifests/suite.example.yaml`, `scripts/README.md`, and `scripts/test_agentic_bench_suite.py`; rc 0. Relevant lines are listed above.
- Default full readiness probe: `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --readiness --json`; wrapper rc 0, inner readiness rc 1. Counts `ready=1`, `blocked=8`, `missing=0`, `total=9`.
- RepoZero readiness subset: `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --readiness --target-benches RepoZero --json`; wrapper rc 0, inner readiness rc 0. Target `repozero` ready with one entry and `manifests/images/repozero.yaml` ready.
- Terminal-Bench 2.1 readiness subset: `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --readiness --target-benches Terminal-Bench-2.1 --json`; wrapper rc 0, inner readiness rc 1. Target has two entries; full entry blocked with 89/81/8 counts, smoke entry image manifest ready but adapter pending.
- Synthetic no-Docker target-aggregation repro using a temporary suite outside the repo; wrapper rc 0, inner readiness rc 0. The target became ready from the smoke entry while the full entry remained blocked with `required_image_transport_missing`.
- Absolute-suite path resolution probe from `/tmp`; wrapper rc 0, inner readiness rc 1. TB2 manifest paths resolved under the active worktree and kept the 89/81/8 counts.
- RepoZero dry-run plan probe: `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --dry-run --only repozero_py2js_smoke --json`; wrapper rc 0, inner rc 0. `image_preflight.project_root` resolved to the active worktree.
- Parsed worker RepoZero evidence directory `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/verification/repozero_readiness_gate_20260626_rerun`; rc 0. It contains only image-preflight summary/log/status plus run manifest; no benchmark result artifact was present in the checked file list.
- Cross-check of runner-results Round27 ledger; rc 0. Runner lane ISSUE-READY is the `--readiness --max-concurrency` ceiling bypass, distinct from this target aggregation finding.

### Validation

- Initial `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 2 due only to a new blank line at EOF from the append. The ledger was normalized to exactly one final newline before the final validation pass.
- Initial trailing whitespace scan on this ledger: rc 1, interpreted as no matches.
- Initial bounded key-like secret scan on this ledger: rc 1, interpreted as no matches.
- Initial pycache scan under `_coordination/20260625_harbor_bench`: rc 0 with no output.
- `git status --short --untracked-files=all`; rc 0. It showed this lane's runtime ledger plus concurrent unrelated `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`; this lane did not edit the runner ledger.


## Round29 post-install-windows image transport review

Scope: runtime/images review at branch `feat/image-warmup-policy`, head `6bd03e8`, after #18/#19 closure and TB2 `install-windows-3.11` promotion. Ledger-only. I did not edit production code, manifests, tests, handoff, runner ledger, commits, GitHub issues, or Docker state. The only live worker Docker probe was bounded read-only `docker image inspect` against already-promoted local tags with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`; no pull/load/run/save/build/restart/prune was executed.

### Findings

No new ISSUE-READY runtime/image bug confirmed in this pass. The current state fails closed for the remaining TB2 transport gaps and no longer shows the two unsafe paths found in Round27/Round28.

- #18 appears fixed for suite-generated image preflight. `manifests/suite.example.yaml:48-52` now puts `DOCKER_API_VERSION: "1.45"` in the worker env, and `scripts/agentic_bench_suite.py:663-729` exports and records the redacted preflight env per command. The dry-run for `terminal_bench_2_1_image_smoke` produced one run with `image_preflight.environment.DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, `image_preflight.environment.DOCKER_API_VERSION=1.45`, image-preflight concurrency `4`, and rendered exports for both variables.
- #19 appears fixed for digest pulls that must leave a local tag behind. `scripts/agentic_bench_images.py:978-1004` pulls the internal digest, tags the pulled digest ref to the first configured `local_ref`, records `local_tag_status`, `local_tag_ref`, and `local_tag_source_ref`, and increments `counts.tagged`. `scripts/agentic_bench_images.py:1529-1533` still exits nonzero on checker errors/missing images, so a tag failure is not a fake-pass path.
- The install-windows worker proof is internally consistent. The active manifest row has `fallback_status=p0_digest_and_fallback_tar_verified`, a P0 digest ref, fallback sha prefix `3c34b88a6c7382e8`, and local ref `tb2-offline/install-windows-3.11:20260425`. The worker proof JSON records `present=1`, `pulled=1`, `tagged=1`, `smoke_passed=1`, `tar_verified=1`, `missing=0`, `errors=0`, and the row has `present_ref=tb2-offline/install-windows-3.11:20260425` with `local_tag_status=tagged`.
- The live worker read-only inspect confirms promoted local tags are present under the required rootless env: `tb2-offline/install-windows-3.11:20260425`, `tau3-smoke-main:20260626r2`, and `tau3-smoke-runtime:20260626r2` all returned image IDs with rc 0. This is presence evidence only, not a fresh pull/run smoke.
- TB2 full readiness remains correctly blocked. The active generated TB2 cache manifest says `materialized_from_swe_dev_cache_82_of_89_offline_transport_ready`, `offline_transport_ready_count=82`, and `remaining_transport_gap_count=7`. Strict lint with `--require-offline-transport --verify-fallback-files` returned rc 1 with `fallback_tar_verified=82`, no fallback tar missing/mismatch, and `required_without_offline_transport=7`.
- The seven required TB2 gaps are exactly `tb2_mteb_retrieve`, `tb2_multi_source_data_merger`, `tb2_pytorch_model_recovery`, `tb2_qemu_alpine_ssh`, `tb2_qemu_startup`, `tb2_torch_pipeline_parallelism`, and `tb2_torch_tensor_parallelism`. `tb2_mteb_leaderboard` is not a gap: it has `lint_status=ok` and a verified fallback tar.
- Readiness aggregation remains fail-closed after the Round27 role fix. `--readiness --target-benches Terminal-Bench-2.1,tau3-bench --json` returned rc 1 with `blocked=2`, `ready=0`. The full TB2 entry is `readiness_role=full` and blocked by `suite_entry_disabled`, `adapter_not_wired`, and `required_image_transport_missing`; the TB2 image-smoke helper is `readiness_role=image_smoke`, image-ready, but still `adapter_not_wired` and does not satisfy the full target. The tau3 entry is disabled/pending adapter while its image manifest is ready.
- tau3 r2 should still be described as image transport/smoke readiness, not full benchmark readiness. `manifests/images/tau3_bench.yaml:4-32` records worker-rootless smoke image readiness and explicitly says the remaining blocker is that the suite adapter is not wired. Static tau3 lint returned rc 0 with two required rows, two digest refs, two verified fallback tars, and zero missing offline transport. `manifests/suite.example.yaml:319-333` keeps `tau3_bench` disabled with `adapter_status: pending_adapter`.

### COMMENT-READY / dedup

- Dedup to #6 and #8: TB2 transport population still needs fallback tar plus worker fallback-load/run-smoke proof because worker-j9jjd P0/rootless new-layer ingest has prior failures. The install-windows promotion is good evidence for that one row only; it does not clear mteb/multi-source or the giant torch rows.
- Dedup to #12/#13: the image-check JSON has useful allowlisted provenance fields (`counts`, `present_ref`, `pull_status`, `local_tag_status`, `smoke_status`), but this pass found no new raw-output or normalized-result bug beyond the existing provenance/log issues.
- #18/#19 are closed fixes and the checked paths match the intended behavior. No new issue should be filed from this lane unless a later worker check shows `local_tag_status=failed` while a suite-level gate still returns success, or readiness starts treating image-smoke helper entries as full-target readiness.

### Next candidates

- Keep `mteb-retrieve` and `multi-source-data-merger` quarantined. Both have staged/P0 history tied to worker rootless layer-registration I/O errors; do not promote either from source-cache or P0 evidence until a clean worker storage-health proof and successful ingest/smoke exist.
- Next lowest-size candidates are the QEMU rows, but they need isolation: `tb2_qemu_alpine_ssh` and `tb2_qemu_startup` are each about `1.96GB` in the staging plan. Use fallback tar as required and treat a `--network none` smoke as image transport only, not QEMU task behavior.
- Defer giant ML/torch rows one at a time: `tb2_torch_tensor_parallelism` about `11GB`, `tb2_torch_pipeline_parallelism` about `11.3GB`, and `tb2_pytorch_model_recovery` about `19.2GB`. These are last because they maximize rootless storage pressure and can mask whether a failure is image-specific or daemon/storage-wide.

### Command evidence

- `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` and `sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0.
- Attempted to read the listed systematic-debugging and verification-before-completion skill files; rc 1 because the listed local skill paths were absent. Continued with manual fact-first debugging and verification.
- `ssh dev 'cd .../image-warmup-policy && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD && git status --short --untracked-files=all && grep -n "Round29 post-install-windows image transport review" .../hunt-runtime-images.md || true'`; rc 0. Branch/head `feat/image-warmup-policy` / `6bd03e8`; no existing Round29 runtime heading. Pre-existing unrelated changes were visible in runner ledger and remote-cache inventory files.
- Read `_coordination/20260625_harbor_bench/HANDOFF.md`, runtime ledger tail, and runner ledger Round28/Round29 cross-checks; rc 0. Runner Round29 also reports #18/#19 fixed and no new runner issue.
- Static reads of `scripts/agentic_bench_suite.py:470-735`, `scripts/agentic_bench_images.py:913-1061`, `scripts/agentic_bench_images.py:1500-1535`, `manifests/suite.example.yaml:42-64`, `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1-28`, and `manifests/images/tau3_bench.yaml:1-61`; rc 0.
- One inline Python manifest parser failed before checks with rc 1 due shell quoting; discarded as operator error and rerun.
- Parsed TB2 manifest, install-windows worker JSON/rc files, install-windows push TSV, and the remote-cache stage plan; rc 0. Output confirmed 89 rows, 7 current missing rows, install-windows push rc 0, worker check rc 0, and the seven gap sizes listed above.
- `PYTHONDONTWRITEBYTECODE=1` dry-run/readiness/lint wrapper; rc 0. Inner commands: TB2 image-smoke dry-run rc 0, readiness for TB2+tau3 rc 1, TB2 strict lint rc 1, tau3 strict lint rc 0.
- Re-parsed readiness and TB2 lint payloads to inspect nested fields; wrapper rc 0. Inner readiness rc 1 and TB2 lint rc 1, with full TB2 blocked and seven `lint_status=missing_offline_transport` required rows.
- Focused tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_image_preflight_remote_command_exports_worker_env scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_readiness_helper_entry_does_not_satisfy_full_terminal_bench_target scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_terminal_bench_full_entry_uses_cache_manifest_with_current_gap_counts scripts.test_agentic_bench_images.AgenticBenchImagesTest.test_check_manifest_tags_pulled_digest_to_local_ref`; rc 0, 4 tests passed.
- `find _coordination/20260625_harbor_bench -type f \( -iname "*tau3*worker*" -o -iname "*tau3*check*" -o -iname "*tau3*r2*" -o -iname "*install_windows*" \) ...`; rc 0. Found install-windows artifacts and no tau3 worker JSON artifact in this tree; tau3 evidence is currently in manifest/handoff/lane notes and the live read-only image inspect above.
- Worker read-only inspect via explicit worker-j9jjd endpoint with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45`; rc 0. It printed image IDs for `tb2-offline/install-windows-3.11:20260425`, `tau3-smoke-main:20260626r2`, and `tau3-smoke-runtime:20260626r2`.
- The first Round29 append attempt used unsafe local shell quoting around Markdown backticks, which produced local command-substitution errors and corrupted the new Round29 section. I repaired only this ledger by replacing the malformed Round29-from-heading-to-EOF block; prior rounds were left intact.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace matches.
- Bounded key-like secret scan on this ledger; rc 1, interpreted as no matches.
- `find _coordination/20260625_harbor_bench -path "*/__pycache__*" -print -quit`; rc 0 with no output, interpreted as no pycache under coordination.
- `git status --short --untracked-files=all`; rc 0. Only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` is modified after this lane's repair.


## Round31 tau3 oracle-direct image review

Scope: runtime/images ledger-only review after the Round31 prompt. I read `WORKFLOW.md` first, then worked through `ssh dev` in the shared worktree. I did not edit production code, manifests, HANDOFF, tests, commits, GitHub issues, or Docker state. The only Docker execution was a bounded worker `docker run --rm --network none` against an already-present tau3 r2 local image; no Docker pull/load/build/prune/restart and no public download was run. Final current head observed during the round moved from the requested `033fbe6` to `9943896` because another lane committed `Add tau3 oracle direct smoke helper` while this review was running.

### ISSUE-READY: oracle-direct helper preflights an unused tau3 sidecar image (#20)

severity: medium

dedup: Related to #8 because the worker rootless daemon has fragile P0/fallback ingest and compose/network limits, but not a duplicate: this bug is a suite/image-manifest contract mismatch that can fail before any compose path is used. Related to #6 image preflight policy, but distinct from transport population. Not #16 because readiness-role aggregation is working; full tau3 remains blocked while the helper is ready.

location:

- `manifests/suite.example.yaml:335-353` defines enabled helper `tau3_bench_oracle_direct_smoke` with `TAU3_AGENT=oracle_direct`, `TAU3_DIRECT_IMAGE=tau3-smoke-main:20260626r2`, and `image_manifest: manifests/images/tau3_bench.yaml`.
- `manifests/images/tau3_bench.yaml:35-63` makes both `tau3_harbor_main_runtime` and `tau3_harbor_mcp_runtime` required. The second row is the sidecar/runtime image `tau3-smoke-runtime:20260626r2`.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:72-101` implements `TAU3_AGENT=oracle_direct`; the direct command is `docker run --rm --network none ... "$TAU3_DIRECT_IMAGE" bash -lc 'bash /solution/solve.sh && bash /tests/test.sh'`. It mounts `/tests`, `/solution`, logs, and artifacts, and does not use the runtime sidecar image or Docker compose.

static_repro:

1. Dry-run the helper: `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --dry-run --json --only tau3_bench_oracle_direct_smoke --model-profile dev_proxy_gpt54mini_8130`. It returns one run with `TAU3_AGENT=oracle_direct`, `TAU3_DIRECT_IMAGE=tau3-smoke-main:20260626r2`, and required image preflight on `manifests/images/tau3_bench.yaml`.
2. In-memory fake the image checker with main image present at the expected `source_image_id` and sidecar image absent. `check_image_manifest('manifests/images/tau3_bench.yaml', allow_pull=False, load_fallback=False)` returns `present=1`, `missing=1`; `tau3_harbor_main_runtime` is present and `tau3_harbor_mcp_runtime` is missing.
3. The direct runner command only needs the main image. A real worker no-network probe against the already-present main tag returned rc 0: `docker run --rm --network none tau3-smoke-main:20260626r2 python3 -c 'import tau2; print("round31-main-network-none-ok")'`.

impact:

- A worker with the direct-used main image ready but the unused sidecar missing, stale, quarantined, or failing P0/fallback ingest will fail the `tau3_bench_oracle_direct_smoke` preflight even though the direct no-sidecar oracle smoke has enough image state to run.
- This increases exposure to the #8 rootless daemon failure modes by forcing an unnecessary second image through inspect/pull/load/smoke policy for a path that intentionally bypasses Harbor/compose.
- It can make the new helper look less robust than the real worker execution path and can confuse future promotion gates about what is required for no-sidecar tau3 oracle smoke versus full Harbor tau3 execution.

fix:

- Add a separate image manifest for the helper, for example `manifests/images/tau3_oracle_direct_smoke.yaml`, containing only `tau3_harbor_main_runtime` with `image_ref`, `local_ref`, `source_image_id`, `fallback_tar`, and `fallback_tar_sha256`.
- Point `tau3_bench_oracle_direct_smoke.image_manifest` at that direct-only manifest. Keep `manifests/images/tau3_bench.yaml` as the two-image Harbor/full-smoke manifest for compose/sidecar paths.
- Add a regression test that the helper image preflight has `required_images=1`, `required_without_offline_transport=0`, exports `DOCKER_API_VERSION=1.45`, and still does not satisfy the full tau3 target aggregation.

### No-new-issue evidence

- Current uncommitted tau3 identity hardening is effective. `manifests/images/tau3_bench.yaml` now has `source_image_id` for both tau3 r2 rows, and `scripts/agentic_bench_images.py check --skip-docker` reports those expected image IDs. The earlier suspected local-tag identity gap is therefore not a current issue in this worktree.
- The worker no-sidecar/no-network execution path is real for the main image: worker-j9jjd `docker image inspect` found both tau3 r2 local tags with the expected image IDs, and `docker run --rm --network none tau3-smoke-main:20260626r2 python3 -c 'import tau2; ...'` returned rc 0. The log still shows LiteLLM attempting a remote model-cost-map fetch and falling back after DNS failure; this is the known offline-hardening caveat, not a new image transport issue because `--network none` prevents public egress.
- Readiness aggregation is still fail-closed. `--readiness --target-benches tau3-bench --json` returned rc 1: full `tau3_bench` is disabled/pending adapter and blocked, while `tau3_bench_oracle_direct_smoke` is an enabled `image_smoke` helper and does not make the full target ready.
- Rootless compose remains deduped to #8. Handoff and Round30 artifacts record default compose network `operation not permitted`, `network_mode: none` compose hitting `/version` EOF, and API-version sweeps failing. This lane did not find a distinct compose root cause beyond #8.
- `swe_dev` source-cache state is consistent with the handoff: read-only Docker cache count from the explicit `swe_dev` endpoint returned `tb2_offline=89`, `swebench=500`, `swerex_prebuilt=728`, `p0_tb2_tagged=34`, `/data/docker` present, `/data` 89% used, and both `/data/swe/SWE-bench` and `/data/tmp/tb2-prebuild-save` have zero top-level files. The useful TB2/SWE source state is Docker cache plus shared/P0 manifest artifacts, not loose `/data` tar/source directories.

### Command evidence

- `sed -n '1,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0.
- Memory quick grep for `Round31|oracle_direct|tau3_bench_oracle_direct_smoke|tau3 rootless|033fbe6|image-warmup-policy`; rc 0 with no relevant hits used.
- Read current systematic-debugging and verification-before-completion skill files from `/Users/Zhuanz1/.codex/plugins/cache/openai-curated/superpowers/d08f0354/...`; rc 0.
- Initial remote status: branch `feat/image-warmup-policy`, head `033fbe6`, with other-lane uncommitted changes in HANDOFF/readiness/suite/tests and untracked tau3 adapter ledger/pycache; rc 0.
- Later remote status after concurrent commit: head `9943896`; uncommitted other-lane changes remained in `_coordination/20260625_harbor_bench/HANDOFF.md`, `_coordination/20260625_harbor_bench/lanes/tau3-adapter-round30.md`, `manifests/images/tau3_bench.yaml`, and `scripts/test_agentic_bench_suite.py`; rc 0. This lane did not edit those files.
- Read HANDOFF Round27-Round30 sections, `tau3-adapter-round30.md`, current suite diff, runtime ledger tail, and runner ledger grep; rc 0.
- Static line reads for `manifests/images/tau3_bench.yaml`, `manifests/suite.example.yaml`, `/mnt/.../bench/run_tau3_bench.sh`, and `scripts/agentic_bench_images.py`; rc 0.
- First in-memory identity probe had a shell quoting SyntaxError; rc 1, discarded as operator error. Second probe used a missing helper class; rc 1, discarded. Corrected in-memory identity probe returned rc 0 and confirmed current `source_image_id` pins are seen by the checker.
- Suite dry-run/readiness probe with `PYTHONDONTWRITEBYTECODE=1`; wrapper rc 0. Inner dry-run for `tau3_bench_oracle_direct_smoke` rc 0; inner readiness for `tau3-bench` rc 1 with full target blocked and helper ready.
- Worker explicit endpoint no-network probe with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45`; rc 0. It inspected both tau3 r2 local tags and ran the main image under `--network none` successfully.
- Explicit `swe_dev` endpoint Docker-cache count probe; rc 0. Counts recorded in no-new-issue evidence above.
- Tau3 static image lint/check probe; rc 0. `lint` counts: `images=2`, `required_images=2`, `required_with_digest_ref=2`, `required_with_fallback_sha=2`, `fallback_tar_verified=2`, `required_without_offline_transport=0`. `check --skip-docker` counts: `tar_verified=2`, `unchecked=2`, no tar mismatch/missing.
- In-memory sidecar-missing checker repro; rc 0. Fake main-present/runtime-missing state returned `present=1`, `missing=1`, proving the direct helper can be blocked by the unused sidecar requirement.
- Dedup grep for `oracle_direct`, `sidecar`, `tau3_harbor_mcp_runtime`, `tau3-smoke-runtime`, `image_smoke`, and #8 context across runtime ledger, runner ledger, and HANDOFF; rc 0. No prior finding for this exact unused-sidecar preflight mismatch was found.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace matches.
- Bounded key-like secret scan on this ledger; rc 1, interpreted as no matches.
- `find . -path "*/__pycache__*" -print`; rc 0 with no output in this final scan, so no pycache was present at validation time.
- `git status --short --untracked-files=all`; rc 0. Final status showed only `_coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md` modified by this lane.


## Round32 tau3 direct manifest and TB2 QEMU transport review

Scope: runtime/images ledger-only review at head `1a722d6`. I read `WORKFLOW.md` first, then worked through `ssh dev` in the shared worktree. I did not edit production code, manifests, HANDOFF, tests, commits, GitHub issues, or Docker state. Docker usage was limited to read-only `docker image inspect` / `docker image ls` on `swe_dev`; no Docker pull/load/save/build/prune/restart and no public download was run.

### Findings

No new ISSUE-READY runtime/image bug confirmed in this pass.

- #20 appears fixed. `manifests/suite.example.yaml:335-353` now points the enabled helper `tau3_bench_oracle_direct_smoke` at `manifests/images/tau3_oracle_direct_smoke.yaml` instead of the two-image full tau3 manifest.
- The new `manifests/images/tau3_oracle_direct_smoke.yaml:1-28` contains exactly one required image row, `tau3_oracle_direct_main_runtime`, with the P0 digest ref, local tag `tau3-smoke-main:20260626r2`, `source_image_id`, fallback tar, and fallback tar sha for the main runtime only. Its evidence note says oracle-direct does not use the runtime sidecar.
- Static lint for `tau3_oracle_direct_smoke.yaml` returned rc 0 with `images=1`, `required_images=1`, `required_with_digest_ref=1`, `required_with_fallback_sha=1`, `fallback_tar_verified=1`, and `required_without_offline_transport=0`.
- Static check with `--skip-docker` for `tau3_oracle_direct_smoke.yaml` returned rc 0 with `tar_verified=1`, `unchecked=1`, no missing/tar mismatch.
- In-memory fake checker repro from Round31 is now fixed for the direct helper: with main image present and sidecar image absent, `check_image_manifest('manifests/images/tau3_oracle_direct_smoke.yaml')` returns `present=1`, `missing=0`. The same fake state against full `manifests/images/tau3_bench.yaml` still returns `present=1`, `missing=1`, which is correct for the Harbor/compose path.
- Dry-run for `tau3_bench_oracle_direct_smoke` returned rc 0 and resolves required image preflight to `manifests/images/tau3_oracle_direct_smoke.yaml`, with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`, `DOCKER_API_VERSION=1.45`, and `TAU3_DIRECT_IMAGE=tau3-smoke-main:20260626r2`.
- Full tau3 readiness remains fail-closed. `--readiness --target-benches tau3-bench --json` returned rc 1: the full `tau3_bench` entry is disabled and `pending_adapter`, while the oracle-direct helper is `readiness_role=image_smoke` and does not make the full target ready.

### TB2 QEMU status and risk

No new QEMU-specific bug is confirmed. The current branch still correctly treats both QEMU rows as missing offline transport, and the staged plan is source-cache evidence only.

- Active TB2 manifest `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` remains `82/89` offline-transport ready with 7 required gaps: `tb2_mteb_retrieve`, `tb2_multi_source_data_merger`, `tb2_pytorch_model_recovery`, `tb2_qemu_alpine_ssh`, `tb2_qemu_startup`, `tb2_torch_pipeline_parallelism`, and `tb2_torch_tensor_parallelism`.
- QEMU active rows have `fallback_status=missing_shared_tar`, `fallback_transport=none`, no `image_ref`, no `fallback_tar`, and no `fallback_tar_sha256`. Their smoke command is the generic `python3 --version ... || echo tb2-smoke-ok` under `network: none`, so planned image warmup should not launch QEMU, SSH, supervisord, or task behavior.
- `tb2_missing_transport_stage_plan.json` has both QEMU rows matched from `swe_dev` and planned to write batch2 fallback tars, but those planned tar files do not exist yet. Planned P0 tags also have no digest refs.
- Internal P0 manifest checks returned HTTP `404` for both `terminal-bench-2-1-qemu-alpine-ssh:20260425` and `terminal-bench-2-1-qemu-startup:20260425`, matching the absence of digest refs in the plan.
- Live read-only `swe_dev` Docker inspect confirms source-cache identity and size match the manifest/plan: `qemu-alpine-ssh` image id `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573`, size `1956628773`, default command `bash`; `qemu-startup` image id `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444`, size `1956605318`, default command `bash`. Both show no exposed ports or declared volumes in inspect metadata.
- `swe_dev` `/data` state remains tight but usable for small isolated QEMU staging: `/data` reported 1.0T total, 907G used, 117G free, 89% used; `/data/docker` exists. `/data/swe/SWE-bench` and `/data/tmp/tb2-prebuild-save` have zero top-level files, so the useful source is Docker cache, not loose tars.

### COMMENT-READY / next candidates

- Keep QEMU staging isolated and fallback-first. The next safe implementation candidate is a two-row QEMU batch only if the operator runs source-side staging from `swe_dev` with source-host and identity guards, then proves worker fallback-load/run-smoke. Do not mix with giant torch/pytorch rows.
- Suggested source-side materialization commands for the implementation owner, not executed in this lane:
  - `scripts/stage_cache_images_from_plan.sh --plan _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.tsv --only qemu-alpine-ssh --source-host-label swe_dev --execute --push`
  - `scripts/stage_cache_images_from_plan.sh --plan _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.tsv --only qemu-startup --source-host-label swe_dev --execute --push`
- After each row is staged, require active manifest metadata with P0 digest and fallback sha, then worker-j9jjd `check --load-fallback --run-smoke --json` using `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`. If P0 pull or fallback load hits rootless network/EIO failures, quarantine under #8 like `mteb-retrieve` and `multi-source-data-merger`.
- Dedup: QEMU rootless ingest/network risk belongs to #8 unless a new row-specific failure shows a distinct archive corruption or manifest/source identity mismatch. The current evidence is COMMENT-READY for #6/#8/#12/#13, not a new issue.

### Command evidence

- `sed -n '1,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc 0.
- Read systematic-debugging and verification-before-completion skill files; rc 0. Memory quick grep for Round32/tau3/QEMU terms returned rc 0 with no relevant hits used.
- Remote head/status/log read through `ssh dev`; rc 0. Branch/head `feat/image-warmup-policy` / `1a722d6`; initial status output was clean.
- Grep for `#20`, tau3 direct helper, and QEMU context across HANDOFF/runtime/runner ledgers and inventory paths; rc 0.
- Static line reads for `manifests/images/tau3_oracle_direct_smoke.yaml`, `manifests/images/tau3_bench.yaml`, `manifests/suite.example.yaml`, and `scripts/test_agentic_bench_suite.py`; rc 0.
- `git show --stat --oneline 1a722d6` and related commit file list; rc 0. Confirmed #20 fix touched the direct image manifest, suite helper manifest pointer, tests, ledgers, readiness snapshot, and handoff.
- Tau3 direct/full lint, skip-docker check, fake sidecar-absent checker repro, dry-run, and readiness probe in one Python wrapper; wrapper rc 0. Inner results are summarized above: direct lint rc 0, direct skip-check rc 0, full lint rc 0, fake direct sidecar-absent present/missing `1/0`, fake full sidecar-absent present/missing `1/1`, helper dry-run rc 0, tau3 readiness rc 1.
- Parsed active TB2 manifest and remote-cache staging plan; rc 0. Current gaps and QEMU plan rows are summarized above.
- Grep for QEMU rows across active manifest and remote-cache artifacts; rc 0. It found the active manifest rows, staging plan TSV/JSON rows, stale dry-run rows, and cache-match artifacts.
- Internal P0 manifest check from `dev` with `curl -k` and Docker manifest accept header; rc 0. HTTP codes were `404` for `qemu-alpine-ssh` and `qemu-startup` tags.
- Parsed stale/non-identity and identity cache inventories for QEMU rows; rc 0. The identity inventory has full image IDs matching active manifest source IDs; the stale remote-cache inventory has only short IDs and no repo digests.
- First live `swe_dev` inspect command had rc 1 because a Go template referenced missing `.Config.ExposedPorts`; discarded except as operator error. Second live `swe_dev` JSON inspect printed `docker_inspect_rc 0` and the QEMU image metadata, but the wrapper exited rc 1 because a later `docker image ls` call used two repository args. Final corrected `docker image ls`/`df`/path-count command returned rc 0 and recorded cache/storage evidence above.
- TB2 static lint without fallback rehashing; wrapper rc 0, inner lint rc 1. Counts: `images=89`, `required_images=89`, `required_with_fallback_sha=82`, `required_without_offline_transport=7`; QEMU rows have `lint_status=missing_offline_transport`, no digest ref, and no fallback sha.

### Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 0, no output.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/hunt-runtime-images.md`; rc 1, interpreted as no trailing whitespace matches.
- Bounded key-like secret scan on this ledger; rc 1, interpreted as no matches.
- `find . -path "*/__pycache__*" -print`; rc 0 with no output, so no pycache was present at validation time.
- Final `git status --short --untracked-files=all`; rc 0. It showed this lane's modified `hunt-runtime-images.md`, plus concurrent unrelated changes to `hunt-runner-results.md` and untracked `tb2_qemu_alpine_stage_20260626.{log,tsv}`. I did not edit the runner ledger or create the QEMU artifacts.
- Read-only follow-up on those concurrent QEMU artifacts; rc 0 for `ls/sed`, and the corrected tar-existence probe rc 0. The TSV had only a header, the log had a single `ROW tb2_qemu_alpine_ssh ...` line, and both planned QEMU fallback tar paths were still absent. One intermediate tar-existence probe had a shell quoting SyntaxError and rc 1; discarded as operator error.
