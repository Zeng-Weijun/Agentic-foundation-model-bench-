# Terminal-Bench 2.1 Gap Support Round28

Date: 2026-06-26
Lane: tb2 gap support
Scope: report-only inventory. No production code, manifest, Docker, benchmark, model-call, commit, push, or GitHub issue mutation was performed by this support lane.

## Bottom line

The active Terminal-Bench 2.1 full image manifest still has 8 rows with `fallback_status: missing_shared_tar`. The next lowest-risk closure candidate is `tb2_install_windows_3_11`: it is the smallest remaining source image at 1.63GB and already has a saved shared tar with sha256 evidence. It still needs P0 digest publication and a single-image worker ingest/smoke proof before promotion into `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`.

Do not use `tb2_multi_source_data_merger` as the next closure probe even though it has a tar and P0 digest evidence: prior worker artifacts record both P0 pull and fallback load failures for that image, so it belongs to the rootless-storage diagnostic lane, not the low-risk closure lane.

## Current manifest baseline

Source: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`

- `cache_image_count: 89`
- `shared_tar_count: 84`
- `offline_transport_ready_count: 81`
- `remaining_transport_gap_count: 8`
- Full TB2 readiness remains blocked by adapter disabled/pending plus the 8 missing offline transports.

## Remaining 8 transport gaps

These are the rows where the active manifest records `fallback_status: missing_shared_tar`.

| Rank | Row | Local ref | Source image id | Source size | Current evidence | Recommendation |
| --- | --- | --- | --- | ---: | --- | --- |
| 1 | `tb2_install_windows_3_11` | `tb2-offline/install-windows-3.11:20260425` | `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b` | 1.63GB | Shared tar saved at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/install-windows-3.11.tar`, sha256 `eabcacaa81ada0061dc6b08c825a74287cb83da38c0a4cdf91a802edb5510c54`; no P0 digest recorded in `tb2_missing_transport_stage_install_windows_result.tsv`. | Next low-risk candidate: publish P0 digest, then run one-image worker proof. |
| 2 | `tb2_mteb_retrieve` | `tb2-offline/mteb-retrieve:20260425` | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2.12GB | Batch1 tar exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/mteb-retrieve.tar`, sha256 `f80be41fc1360f33926c4ceaf572eff8963455f7bf44d3544454d4c6fb3eda2d`; no committed P0 digest evidence found. | Second candidate after install-windows, but verify why it stayed unpromoted. |
| 3 | `tb2_qemu_alpine_ssh` | `tb2-offline/qemu-alpine-ssh:20260425` | `sha256:53987a31bb5efeed33dbc4ef0e0d1dd9a5a3c46ed2978bb3ccef9734c46d7573` | 1.96GB | Stage plan exists, but no confirmed tar/P0 evidence in the active committed inventory. | Stage one QEMU image at a time only after a non-QEMU row proves worker path. |
| 4 | `tb2_qemu_startup` | `tb2-offline/qemu-startup:20260425` | `sha256:5814c86fde20a77a5aa139697de684a25657b71422f797f6fe272bd94e732444` | 1.96GB | Stage plan exists, but no confirmed tar/P0 evidence in the active committed inventory. | Same as QEMU alpine; do not batch both together. |
| 5 | `tb2_multi_source_data_merger` | `tb2-offline/multi-source-data-merger:20260425` | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6.2GB | Batch1 tar exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch1/multi-source-data-merger.tar`, sha256 `502a8078ee247e5813161e13c03d4e9c69c08da7d685d5a02b0f544f599f1ea7`; P0 digest evidence exists in `tb2_p0_multisource_batch11_20260626.tsv`; worker pull/load failed in `tb2_multisource_batch11_worker_*_failed_20260626.json`. | Hold for rootless failure diagnosis; not the next closure candidate. |
| 6 | `tb2_torch_tensor_parallelism` | `tb2-offline/torch-tensor-parallelism:20260425` | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11GB | Stage plan exists, but no confirmed tar/P0 evidence in the active committed inventory. | Defer; large Torch row. |
| 7 | `tb2_torch_pipeline_parallelism` | `tb2-offline/torch-pipeline-parallelism:20260425` | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11.3GB | Stage plan exists, but no confirmed tar/P0 evidence in the active committed inventory. | Defer; large Torch row. |
| 8 | `tb2_pytorch_model_recovery` | `tb2-offline/pytorch-model-recovery:20260425` | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19.2GB | Stage plan exists, but no confirmed tar/P0 evidence in the active committed inventory. | Defer; highest size risk. |

## Worker-safe next command shape

Run this in a separate worker lane; do not batch multiple TB2 gap rows.

1. Health guard first, using the Round28 API-version-aware script:

```bash
scripts/check_rootless_docker_worker.sh --check
```

2. Publish or confirm the P0 digest for `install-windows-3.11` from the existing tar/source image. Record the resulting digest before any manifest edit.

3. On worker-j9jjd, run one-image checker only, with the API version pinned:

```bash
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export DOCKER_API_VERSION=1.45
python3 scripts/agentic_bench_images.py check   --image-manifest /path/to/one-row-install-windows-3.11.yaml   --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench   --docker-host unix:///tmp/rl/run/docker.sock   --pull   --load-fallback   --run-smoke   --json
```

Acceptance criteria before manifest promotion:

- checker status is present/pulled/loaded with `errors=0`;
- tar sha256 remains `eabcacaa81ada0061dc6b08c825a74287cb83da38c0a4cdf91a802edb5510c54` if fallback load is used;
- Docker inspect identity matches `sha256:2dad545615271e1b9d3d5b818cd2083a330159eba7535122b2c5b660ca57f58b`;
- no-network smoke passes;
- no `unlinkat`, `input/output error`, or registry EOF appears.

## Evidence commands

Read-only evidence used for this report:

- Parsed `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` for the 8 `fallback_status: missing_shared_tar` rows.
- Parsed `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json` for source sizes and image ids.
- Read `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_install_windows_result.tsv` for the saved install-windows tar evidence.
- Read `_coordination/20260625_harbor_bench/inventory/tb2_p0_multisource_batch11_20260626.tsv` and `tb2_multisource_batch11_worker_*_failed_20260626.json` for the multi-source hold decision.
- Ran `sha256sum` and `ls -lh` only on the three existing shared tar files listed above; no Docker mutation was performed.
