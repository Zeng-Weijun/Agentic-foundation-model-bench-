# SWE/DeepSWE image map support inventory round27

Date: 2026-06-26
Lane: swe-deepswe-image-map
Scope: support inventory, not bug-hunt. Convert current SWE-bench Verified multi and DeepSWE image/readiness blockers into concrete image-map tasks.
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Branch: `feat/image-warmup-policy`

## Red lines observed

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first.
- Worked through `ssh dev` in the specified worktree.
- No production code, manifest, or test edits.
- No commit or push.
- No token values printed. Only variable names and code references to env key names were observed where needed.
- No Docker mutation: no `docker save`, `docker load`, `docker pull`, `docker run`, or `docker build`.
- No model calls.
- Only this report was written.

## Current manifest/readiness state

### SWE-bench Verified multi

Current repo manifest:

- `manifests/images/swebench_verified.yaml:1-4` declares `bench_id: swebench_verified_multi` and `status: partial_worker_cache_not_full_manifest`.
- `manifests/images/swebench_verified.yaml:10-13` lists blockers:
  - `exact_task_to_image_digest_map_not_frozen`
  - `full_500_verified_image_coverage_not_proven`
  - `openhands_runtime_image_missing`
- `manifests/images/swebench_verified.yaml:16-27` contains only a non-required partial cache probe for one Django task base image plus one SWE-ReX wrapper ref.
- `manifests/images/swebench_verified.yaml:29-35` records the OpenHands runtime target `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98` as `missing_runtime_image` with no fallback.

Suite rows:

- `manifests/suite.example.yaml` has four enabled/wired SWE-bench rows that all point to `manifests/images/swebench_verified.yaml`: qwen-code, mini-swe-agent, swe-agent, and OpenHands.
- Dry-run probe showed all four SWE rows have image preflight `policy=optional`, `required=False`, and `adapter_status=wired_legacy`.
- Existing readiness JSON `_coordination/20260625_harbor_bench/readiness_20260626.json` reports `swebench_verified_multi` as `blocked` with blocker `image_manifest_not_materialized`, entry_count 4, enabled_entry_count 4, wired_entry_count 4, ready_entry_count 0.

### DeepSWE

Current repo manifest:

- `manifests/images/deepswe.yaml:1-4` declares `bench_id: deepswe` and `status: missing_r2e_image_manifest`.
- `manifests/images/deepswe.yaml:8-11` lists blockers:
  - `exact_r2e_gym_or_pier_image_tags_not_enumerated`
  - `no_deepswe_specific_shared_tar_found`
  - `rootless_container_networking_not_proven_for_deepswe`
- `manifests/images/deepswe.yaml:13-19` contains only a non-required placeholder row `deepswe_r2e_images_todo`.

Suite row:

- Dry-run probe showed `deepswe` has image preflight `policy=optional`, `required=False`, manifest `manifests/images/deepswe.yaml`, and `adapter_status=wired_legacy`.
- Existing readiness JSON reports `deepswe` as `blocked` with blocker `image_manifest_not_materialized`, entry_count 1, enabled_entry_count 1, wired_entry_count 1, ready_entry_count 0.

## Existing reports that already cover the blocker class

- `reports/offline_docker_asset_plan_20260625.md:44-49` records partial worker SWE/SWE-ReX cache, zero OpenHands runtime tags, and zero DeepSWE/R2E tags.
- `reports/offline_docker_asset_plan_20260625.md:76-86` says SWE-bench/SWE-ReX needs exact task subset freeze, task-to-image manifest, cache comparison, and shared tar staging for missing images.
- `reports/offline_docker_asset_plan_20260625.md:100-116` says OpenHands needs both SWE-bench base images and runtime image staging; only source archives were found, not runtime image tars.
- `reports/offline_docker_asset_plan_20260625.md:145-154` says DeepSWE needs exact R2E-Gym image enumeration, cache comparison, missing-image staging, and no-model container networking smoke.
- `reports/next_swebench_image_map_plan_20260625.md:37-42` freezes the current smoke selectors and records worker-side gaps.
- `reports/next_swebench_image_map_plan_20260625.md:49-108` records worker rootless cache gaps: Qwen smoke_n20 10/20 present, mini-swe-agent first task present, swe-agent 1/5 present, OpenHands base/pretag/runtime missing.
- `reports/next_swebench_image_map_plan_20260625.md:131-186` already states the row fields needed before flipping SWE image preflight to required.
- `reports/p0_harbor_bench_manifest_inventory_20260625.md:35` and `:43` summarize SWE-bench Verified and DeepSWE as partial/missing image-contract benches.

This lane found no contradiction with those blockers. It refines them into task rows below.

## swe_dev cache evidence

Live `ssh dev -> swe_dev` Docker probing was attempted with the explicit WORKFLOW swe_dev endpoint and failed with `Permission denied (publickey)` (exit 255). The direct alias `swe_dev` was also unavailable from `dev` (`Could not resolve hostname swe_dev`, exit 255). Therefore this report uses the existing repo-owned swe_dev inventory files, which are sufficient for support mapping but should be refreshed by a lane with direct swe_dev access before mutation.

Existing inventory files:

- `reports/swe_dev_docker_cache_inventory_20260626.json`: `schema_version=agentic_bench.docker_cache_inventory.v1`, 1317 images, 500 `swebench/*` refs, 728 `swerex-prebuilt:*` refs, 0 OpenHands, 0 DeepSWE, 0 R2E, 0 Pier refs by this lane's parser.
- `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`: 1320 images, 1320 identity inspections, 0 identity errors, 500 `swebench/*`, 728 `swerex-prebuilt:*`, 0 OpenHands, 0 DeepSWE, 0 R2E, 0 Pier refs.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json`: 591 images, 500 `swebench/*`, but no SWE-ReX refs in that narrower inventory. Do not use this file alone for wrapper coverage.

Selected smoke refs in swe_dev inventory:

- Qwen `smoke_n20`: all 20 base tags are present in the swe_dev identity inventory; each selected task also has at least one matching `swerex-prebuilt:*` wrapper ref.
- mini-swe-agent `MINI_SWE_SLICE=0:1`: `astropy__astropy-12907` base tag is present; three matching SWE-ReX wrapper aliases are present.
- swe-agent default smoke set: all five base tags are present in swe_dev inventory; each has at least one matching SWE-ReX wrapper ref.
- OpenHands smoke task `sphinx-doc__sphinx-8595`: base tag and SWE-ReX wrapper are present in swe_dev inventory.
- OpenHands pretag source `openhands_smoke4_recover:sphinx8595`: missing in swe_dev identity inventory.
- OpenHands runtime target `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`: missing in swe_dev identity inventory.
- DeepSWE/R2E/Pier: 0 matching refs in swe_dev identity inventory.

Representative selected swe_dev identities:

- `swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-21568:latest` -> image id `sha256:cae7e53dbd05e0cfdddc25a475d917003f9fcb03f99d45f3f57660ddd4c0bc9c`, repo digests empty.
- `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8595:latest` -> image id `sha256:71d1b75dd311a7fb6204ef51b7137145b613f0852b8a0964717c67e911ce38f2`, repo digests empty.
- `swerex-prebuilt:docker-io-swebench-sweb-eval-x86-64-sphinx-doc-1776-sphinx-8595-latest-32b267b8eb59088f` -> same image id `sha256:71d1b75dd311a7fb6204ef51b7137145b613f0852b8a0964717c67e911ce38f2`, repo digests empty.

Implication: swe_dev is a strong staging source for the selected SWE base and SWE-ReX wrapper refs, but its local image IDs are not portable P0 registry digests. A promotion lane must produce P0 digest refs and/or fallback tars with sha256.

## Shared asset evidence

- SWE-bench shared tar scan found one tar under the bounded SWE-bench tree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/qwen-code/runs/manual_transfer_astropy_7671_20260613_220547/astropy_7671.image.tar`.
- SWE-ReX chunk storage exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks`: 96 `.tar` files, 0 `.sha256` files found by bounded count. These are repo-family chunk tars, not yet a task-level manifest with checksum rows.
- OpenHands shared source archives exist, including `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen/OpenHands-0.54.0.tar.gz`, but no OpenHands runtime image tar was found in bounded candidate search.
- DeepSWE task tree exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe/tasks`: 113 `task.toml` files and 113 `environment/Dockerfile` files.
- DeepSWE source/project tree exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe`, but bounded image scan found 0 `.tar` and 0 `.sha256` files under that tree.

## DeepSWE R2E/Pier image enumeration

DeepSWE task TOML is the concrete image enumeration source for the current task set. Three sampled tasks showed:

```toml
[environment]
docker_image = "public.ecr.aws/d3j8x8q7/swe-bench-202605:<ext_id>"
allow_internet = false
```

A regex parse over all 113 task TOMLs found:

- `deepswe_tasks=113`
- `unique_images=113`
- repository prefix: `public.ecr.aws/d3j8x8q7/swe-bench-202605` for all 113
- `present_in_swe_dev_inventory=0`
- `missing_in_swe_dev_inventory=113`

First sampled refs:

| task_id | ext_id | docker_image | swe_dev inventory |
| --- | --- | --- | --- |
| `abs-module-cache-flags` | `kh75679ajj3b8dtd7se3h7z0a1833y6r` | `public.ecr.aws/d3j8x8q7/swe-bench-202605:kh75679ajj3b8dtd7se3h7z0a1833y6r` | missing |
| `abs-stepped-slices` | `kh7d5m4ed35zfp7gyhx7wdahed82yw72` | `public.ecr.aws/d3j8x8q7/swe-bench-202605:kh7d5m4ed35zfp7gyhx7wdahed82yw72` | missing |
| `actionlint-action-pinning-lint` | `kh79dnvkvq8j9bs22ededmsc79823akj` | `public.ecr.aws/d3j8x8q7/swe-bench-202605:kh79dnvkvq8j9bs22ededmsc79823akj` | missing |
| `adaptix-name-mapping-aliases` | `kh73dq4n55jdxasppe6jjmth4183d47n` | `public.ecr.aws/d3j8x8q7/swe-bench-202605:kh73dq4n55jdxasppe6jjmth4183d47n` | missing |
| `aiomonitor-task-snapshots-diff` | `kh75rc2q0zhmsqwk7wewfwwtrx830v2n` | `public.ecr.aws/d3j8x8q7/swe-bench-202605:kh75rc2q0zhmsqwk7wewfwwtrx830v2n` | missing |

Runner shape:

- `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh:3-4` describes native R2E editing over R2E-Gym/SWE-Bench-Verified docker gyms with a local Docker backend.
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh:15` defaults `DEEPSWE_BACKEND=docker`.
- `/data/nips/bench/run_deepswe.sh:8-33` is a Pier-oriented runner path with `PIER_BIN`, `DEEPSWE_ENVIRONMENT=docker`, and `DEEPSWE_RELAY_CONTAINER_HOST=host.docker.internal`.
- `/data/nips/bench/run_deepswe.sh:147-172` writes `pier.env` and passes it to Pier via `--env-file`; this file is secret-bearing and must not be copied into normalized reports.
- `/data/nips/bench/run_deepswe.sh:245-289` expects Pier to emit `result.json` and then writes artifact metadata.

Implication: the image map must cover the 113 task `public.ecr.aws/...` images first. Separately, the runner owner must choose the active wrapper path: shared R2E-Gym runner vs legacy Pier runner. The Pier path adds a networking requirement around `host.docker.internal` and a secret-bearing env sidecar; that is readiness work, not an image tar by itself.

## Image-map tasks

### SWE-BASE-01: freeze selected SWE eval base rows

Create a generated task-to-image map for the currently selected smoke rows before any required preflight flip.

Required rows:

- Qwen Code `smoke_n20`: 20 rows using the exact task IDs listed in `reports/next_swebench_image_map_plan_20260625.md:56-77`.
- mini-swe-agent: 1 row for `astropy__astropy-12907`.
- swe-agent default smoke: 5 rows for `astropy__astropy-12907`, `matplotlib__matplotlib-20488`, `sympy__sympy-12096`, `scikit-learn__scikit-learn-10844`, `sphinx-doc__sphinx-10435`.
- OpenHands smoke: 1 row for `sphinx-doc__sphinx-8595`, but only after the suite row is frozen to that ID rather than only `OPENHANDS_EVAL_LIMIT=1`.

Per row fields:

- `task_id`
- `scaffold`: `qwen-code`, `mini-swe-agent`, `swe-agent`, or `openhands`
- `role: swebench_eval_base`
- exact `local_ref`, for example `swebench/sweb.eval.x86_64.<owner>_1776_<repo>-<issue>:latest`
- source host cache evidence: `swe_dev` inventory file, image id, repo digests if any
- worker cache evidence if available from prior worker inventory
- `image_ref` P0 digest once published, or `fallback_tar` plus `fallback_tar_sha256`
- `needs_network: false`

Current support status:

- swe_dev has all selected base refs for the current smoke set.
- worker-side prior report says several selected refs are missing, so promotion/staging is still needed for worker readiness.
- repo digests are empty in swe_dev identity inventory, so local image IDs alone are insufficient for portable P0 rows.

### SWE-SWEREX-01: map SWE-ReX wrapper aliases per selected task

The selected tasks have matching `swerex-prebuilt:*` aliases in swe_dev identity inventory. The task is to turn that into a durable wrapper manifest.

Required work:

- For each selected task, record all observed `swerex-prebuilt:*` aliases and the matching image ID.
- Decide which wrapper alias each scaffold actually requires. Do not include all aliases as required unless the runner can consume any of them deterministically.
- Map each required wrapper alias to either a P0 digest or a fallback tar plus sha256.
- Use `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks` as a candidate source only after an index maps wrapper refs to chunk tars and sha256 files are created.

Current support status:

- 96 SWE-ReX chunk tars exist.
- No `.sha256` files were found for those chunks by the bounded count.
- `swebench_verified_django10097.yaml` demonstrates the desired shape for a wrapper row: `role: swerex_wrapper`, local ref, source image id, fallback tar, and fallback sha256.

### SWE-OH-01: stage OpenHands runtime image

Current blocker:

- `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98` is missing from swe_dev identity inventory, worker evidence, and shared runtime tar search.
- `openhands_smoke4_recover:sphinx8595` pretag source is also missing from swe_dev identity inventory.

Required work:

- On an approved internet-enabled or already-warm builder, obtain or build the exact OpenHands runtime image for 0.54.0.
- Save/push it to P0 Harbor by digest and/or write a fallback tar plus sha256 under the shared image root.
- Add one `role: openhands_runtime` row with exact source ref, P0 digest, fallback tar sha, and no-network smoke command.
- Keep OpenHands runtime build/pull off the worker.

### SWE-OH-02: freeze OpenHands selected task ID

Current suite row has `OPENHANDS_EVAL_LIMIT=1`; existing report maps the shared OpenHands config to `sphinx-doc__sphinx-8595`.

Required work:

- Make the image map depend on `OPENHANDS_SELECTED_IDS=sphinx-doc__sphinx-8595` or otherwise record the exact one-task selection in the suite/report before making image preflight required.
- Add a base image row for `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8595:latest` and, if required by runtime wiring, the matching SWE-ReX wrapper alias.

### DEEPSWE-R2E-01: generate DeepSWE task image manifest from task TOMLs

Current blocker:

- `manifests/images/deepswe.yaml` has only a placeholder row.
- The concrete task source contains 113 unique image refs, all under `public.ecr.aws/d3j8x8q7/swe-bench-202605:<ext_id>`.
- None of those 113 refs are present in swe_dev identity inventory.

Required work:

- Generate a manifest section with one row per `task.toml`:
  - `task_id`
  - `ext_id`
  - `role: deepswe_r2e_task_runtime`
  - `source_image_ref: public.ecr.aws/d3j8x8q7/swe-bench-202605:<ext_id>`
  - source TOML path
  - `allow_internet: false`
  - CPU/memory/storage hints from TOML
- Split the first smoke subset from the full 113 if the immediate goal is only smoke.
- Compare the generated refs against a refreshed cache inventory from the actual staging host.

### DEEPSWE-R2E-02: stage DeepSWE public ECR images to P0/offline transport

Required work:

- Use an internet-enabled staging host, not the worker, to pull/inspect each required `public.ecr.aws/d3j8x8q7/swe-bench-202605:<ext_id>` image.
- Publish each to P0 Harbor by immutable digest and/or save fallback tar plus sha256.
- Add `image_ref` and `fallback_tar_sha256` to generated rows only after the digest/tar exists.
- Do not rely on generic SWE-bench/SWE-ReX cache; current DeepSWE refs are not in swe_dev inventory.

### DEEPSWE-PIER-01: choose runner wrapper path and record networking prerequisites

Required work:

- Decide whether future runs use the shared R2E-Gym runner or the legacy Pier runner at `/data/nips/bench/run_deepswe.sh`.
- If using Pier, record `PIER_BIN`/venv readiness and `DEEPSWE_RELAY_CONTAINER_HOST=host.docker.internal` expectations as runner readiness fields, not image rows.
- Verify a no-model/no-secret container networking probe after images are staged. Do not copy `pier.env`; only record its path/presence and redaction policy.

## Recommended next execution order

1. Refresh direct cache inventory from the actual staging host that can access Docker. For swe_dev, current `ssh dev -> swe_dev` failed with publickey, so use a lane that has direct swe_dev access or use an approved alternative staging host.
2. Generate `swebench_verified` task-to-image rows from the frozen current smoke selectors.
3. Promote selected SWE base images from swe_dev cache to P0 digest and/or fallback tar+sha, prioritizing worker-missing selected rows.
4. Map SWE-ReX wrappers to chunk tar/digest rows and create sha256 metadata.
5. Build/stage the exact OpenHands runtime image and freeze `OPENHANDS_SELECTED_IDS` before making OpenHands preflight required.
6. Generate DeepSWE 113-row R2E image list from task TOMLs; pick a small smoke subset if full 113 staging is too large for first pass.
7. Stage DeepSWE task images from public ECR via an internet-enabled host to P0/fallback tar; then run only no-model/no-token rootless/networking checks.

## No-new-issue evidence

No new ISSUE-READY bug was found in this support inventory lane.

Dedup/no-new-issue rationale:

- SWE-bench blockers observed here are already recorded in `manifests/images/swebench_verified.yaml`, `reports/next_swebench_image_map_plan_20260625.md`, and `readiness_20260626.json` as missing/materialized image map work, not a newly discovered code defect.
- DeepSWE blockers observed here are already recorded in `manifests/images/deepswe.yaml`, `reports/offline_docker_asset_plan_20260625.md`, and `readiness_20260626.json` as missing R2E/Pier image enumeration and no transport evidence.
- The `ssh dev -> swe_dev` publickey failure is an access-path limitation for this lane, not a runner bug. Existing swe_dev inventory files provide enough support evidence for this report, but mutation/staging lanes should refresh from a host with direct Docker access.

## Command ledger

| Command/probe | Exit | Notes |
| --- | ---: | --- |
| `sed -n '1,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Read required workflow first. |
| `grep -n "agentic-foundation-model-bench\|image-warmup-policy\|DeepSWE\|SWE-bench Verified\|swebench" /Users/Zhuanz1/.codex/memories/MEMORY.md | head -80` | 0 | No lane-specific reusable evidence used. |
| `ssh dev 'cd <worktree>; hostname; pwd; git branch --show-current; git rev-parse --short HEAD; git status --short; test target report'` | 0 | Confirmed branch `feat/image-warmup-policy`, HEAD `ea24680`, target report absent at start. |
| Skill file reads for using-superpowers and verification-before-completion | 0 | Process instructions read. |
| Initial broad manifest/report list command with `printf "-- ..."` | 2 | Shell `printf` option parsing issue; superseded by corrected list command. |
| Corrected `find manifests`, `_coordination`, and `reports` list | 0 | Located relevant manifests, reports, readiness and inventory files. |
| Focused `rg` over manifests/reports/lanes for SWE/OpenHands/DeepSWE terms | 0 | Output was large but identified relevant reports and manifests. |
| `nl -ba manifests/images/swebench_verified.yaml`, `deepswe.yaml`, `swebench_verified_django10097.yaml` | 0 | Read manifest blocker rows and example materialized SWE rows. |
| `nl -ba reports/offline_docker_asset_plan_20260625.md` and `reports/next_swebench_image_map_plan_20260625.md` focused ranges | 0 | Read existing blocker and worker cache evidence. |
| `nl -ba reports/p0_harbor_bench_manifest_inventory_20260625.md` focused range | 0 | Read P0 inventory status. |
| JSON summary over swe_dev inventory files | 0 | Existing swe_dev inventories count 500 SWE base refs, 728 SWE-ReX refs, no OpenHands/DeepSWE/R2E/Pier refs. |
| `ssh dev -> swe_dev` alias live Docker probe | 255 | Alias not resolvable from `dev`. |
| `ssh dev -> explicit swe_dev endpoint` live Docker probe | 255 | Publickey denied. Existing inventory used instead. |
| Python selected-task matching against `_coordination/.../swe_dev_docker_cache_identities_20260626.json` | 0 | Selected SWE base and wrapper refs present in swe_dev inventory; OpenHands runtime/presize source missing. |
| Bounded shared asset find for SWE tars, SWE-ReX chunks, OpenHands candidates | 0 | Found one SWE base tar, 96 SWE-ReX chunk tars, OpenHands source archives but no runtime image tar. |
| DeepSWE dir and bounded image/tar candidate find | 0 | Found DeepSWE source and 113 task tree; no DeepSWE tar/sha transport. |
| Runner grep for DeepSWE/SWE/OpenHands image/runtime terms | 0 | Read R2E/Pier/OpenHands runner image and env behavior. |
| DeepSWE count probe | 0 | Output: SWE tar count 1, SWE-ReX chunk tar count 96, DeepSWE tasks 113, DeepSWE Dockerfiles 113, DeepSWE tar/sha 0. The recursive probe was stopped after useful output. |
| Python TOML parse with `tomllib` | 1 | Remote Python lacked `tomllib`; superseded by regex parser. |
| Regex parser over 113 DeepSWE task TOMLs | 0 | Found 113 unique public ECR image refs, 0 present in swe_dev inventory. |
| Read readiness JSON summary | 0 | SWE-bench Verified multi and DeepSWE both blocked by `image_manifest_not_materialized`. |
| Dry-run suite extraction for four SWE rows plus DeepSWE | 0 | All relevant image preflights are optional today; no adapters executed. |
