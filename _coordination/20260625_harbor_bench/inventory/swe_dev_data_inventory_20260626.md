# swe_dev /data and shared bench image inventory - 2026-06-26

Scope: bounded inventory for SWE-bench Verified and Terminal-Bench 2.1 assets, after the user noted shared copies may be incomplete and swe_dev local /data may contain the end-to-end image state.

## Host and storage

- Host: `swe_dev` / `zwj`.
- `/data`: 1.0T total, 905G used, 119G available, 89% used at inventory time.
- `/mnt/shared-storage-user`: shared project filesystem; use it for repo artifacts and fallback tar manifests, not as a Docker root.

## Local /data findings

- `/data/swe/SWE-bench`: present but empty (`du -sh` reported `0`).
- `/data/tmp/tb2-prebuild-save`: present but empty (`du -sh` reported `0`).
- `/data/tmp/swe-agent-runtime-swebench`: 304M, contains `repo-cache/astropy_astropy.git`.
- `/data/swe/docker_prebuilt`: 3.2G, contains one astropy swerex bundle tar: `astropy__astropy-12907__swerex_bundle_v2_20260425.tar` plus its `.images.txt`.
- The end-to-end useful state is primarily in swe_dev Docker local cache, not those two empty `/data` directories.

## swe_dev Docker local cache

Inventory JSON: `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`.

Counts from `scripts/agentic_bench_images.py inventory-cache --docker-host unix:///var/run/docker.sock`:

| Group | Count | Meaning |
|---|---:|---|
| `swebench/sweb.eval.x86_64.*:latest` | 500 | SWE-bench Verified eval images locally cached on swe_dev. |
| `swerex-prebuilt:*` | 728 | Swerex-prebuilt tags; includes SWE-bench images and extra/prebuilt aliases. |
| `tb2-offline/*:20260425` | 89 | Terminal-Bench offline images cached on swe_dev. |
| `sweb.*` base/env | 3 | SWE base/env helper images (`sweb.base.py.x86_64`, env/base rows). |
| total matching inventory rows | 1320 | All rows matching the four prefixes above. |

Implication: swe_dev is the authoritative source for current local Docker cache. For offline worker reproducibility, promote these to the P0 registry by digest or save/load fallback tars; do not rely on rebuilding from public internet on worker.

## Shared SWE-bench Verified tree

Path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`.

- Size: 13G.
- Contains active scaffold trees for `awe-agent`, `mini-swe-agent`, `openhands`, `qwen-code`, `swe-agent`, plus `harness` and `image_migration`.
- Rootless worker entrypoints already exist:
  - `harness/rootless_worker_run.sh`
  - `harness/rootless_worker_pipeline.sh`
  - `harness/rootless_worker_full.sh`
  - `harness/rootless_worker_config.yaml`
  - `harness/rootless_worker_full_config.yaml`
  - `harness/rootless_worker_full_smoke_config.yaml`
- Image migration manifests under `image_migration/manifests/20260601_170434` include:
  - `swebench_base_500.txt`: 500 lines.
  - `swerex_prebuilt_all.txt`: 728 lines.
  - `repo2env_all.txt`: 0 lines in the latest timestamped manifest.
  - `openhands_runtime_current.txt`: 0 lines in the latest timestamped manifest.

Implication: SWE-bench Verified has enough scaffold/runner assets and image inventories for the non-OpenHands SWE path. OpenHands runtime images are not complete in the latest migration manifest and should stay marked as a blocker/fallback-only until rebuilt or mapped.

## Shared Terminal-Bench 2.1 tree

Path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1`.

- Size: 54G.
- Contains `prebuilt-images`, `qwen-code`, and `terminus-2` runner trees.
- `prebuilt-images/20260425`: 50 `.tar` files plus one `headless-terminal.tar.gz`.
- `prebuilt-images/20260625-fix-git-rebuild`: no files were returned in the bounded probe.
- `prebuilt-images/shards` contains `missing_shard_1.txt`, `missing_shard_2.txt`, and `missing_shard_2_retry.txt`.
- swe_dev Docker cache contains 89 `tb2-offline/*:20260425` tags, which is larger than the 50 shared tar fallbacks.

Implication: Terminal-Bench 2.1 is partially warm on shared storage and more complete in swe_dev Docker cache. The next promotion step should generate digest/tar manifests from the 89 local cached tags, then explicitly mark which tasks only have Docker-cache presence and no shared fallback tar.

## Worker observation

Endpoint used: `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`.

- Hostname: `zwj2-64rlk-3469265-worker-0`.
- CPU: `nproc` reported 60.
- `/tmp`: 391G total, 139G used, 253G available.
- Docker commands must set `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
- Worker local Docker cache already has at least:
  - P0 registry smoke image `100.97.118.137:8555/swe-data-harness/repo2env-pallets-click-f6299c4@...`.
  - TB2 small subset: `headless-terminal`, `llm-inference-batching-scheduler`, `gcode-to-text`, `dna-insert`, `compile-compcert`.
  - SWE-bench django subset and matching `swerex-prebuilt` tags.


## Identity-enriched inventory update

After adding `--inspect-identities`, a read-only swe_dev run inspected all matching local images and wrote `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`.

- `images`: 1320.
- `identity_inspected`: 1320.
- `identity_errors`: 0.
- rows with `full_image_id`: 1320.
- rows with non-empty `repo_digests`: 179.
- Generated manifests from this inventory:
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`: 89 TB2 cache rows; swe_dev check reported `present=89`, `identity_mismatch=0`.
  - `manifests/images/swebench_verified_django10097.yaml`: 2 SWE rows; swe_dev check reported `present=2`, `identity_mismatch=0`; worker check reported `present=1`, `identity_mismatch=1`, proving the worker eval-base tag currently aliases to the wrapper image.

## Immediate action items

1. For SWE-bench Verified non-OpenHands path, use the 500 swe_dev eval-image rows plus #11 identity checking as the source of truth; promote/publish digest refs before worker full run.
2. Keep OpenHands SWE path blocked from one-click full-run until its runtime image inventory is rebuilt or mapped; latest migration files have `openhands_runtime_current.txt` with 0 rows.
3. For Terminal-Bench 2.1, treat shared 50 tars as fallback subset and swe_dev 89 Docker tags as the fuller cache source; generate an image manifest that records tar coverage per task.
4. Worker concurrency can target suite concurrency 40-50, but image transport warmup must remain capped separately at 2-4 first-time pulls/loads per worker.
