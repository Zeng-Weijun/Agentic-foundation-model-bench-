# TB2 Torch Tensor Stage Round38 Attempt

Date: 2026-06-26 Asia/Shanghai
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Head: `9fc70ac Fail closed on unwired adapters and parse tau3 summaries`

## Result

`tb2_torch_tensor_parallelism` is still not promotable. The current five-row plan correctly selected it as the next unquarantined candidate, but source-side materialization failed before any fallback tar, SHA, or P0 digest was produced.

The real stage ran in local tmux session `tb2_torch_tensor_stage_round38` through `ssh swe_dev` and was terminated after `docker save` stayed at zero output for more than eight minutes. The wrapper wrote `rc=143`.

No worker proof was attempted because there is no staged tar or digest to check.

## Evidence Artifacts

- Current five-row plan: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_round38_current.tsv`.
- Dry-run one-row result: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_dryrun.tsv`.
- Real stage start marker: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.started`.
- Real stage log: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.log`.
- Real stage TSV: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.tsv`.
- Real stage rc: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.rc` contains `143`.
- Real stage ended marker: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.ended`.

The stage TSV contains only the header, so it has no `fallback_tar_sha256`, no `p0_digest_ref`, no `actual_image_id`, and no `saved_pushed` row.

## What Was Proven

The current planner is correct:

- `missing_transport=5`, `matched=5`, `unmatched=0`.
- Selected row: `tb2_torch_tensor_parallelism` / `torch-tensor-parallelism`.
- `local_ref=tb2-offline/torch-tensor-parallelism:20260425`.
- `source_host=swe_dev`.
- `source_image_id=sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
- `source_size=11GB`.
- Planned fallback tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/torch-tensor-parallelism.tar`.
- Planned P0 tag: `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism:20260425`.

`swe_dev` had the source image by exact id:

```text
sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97 11026213679 6
```

The project registry was reachable from `swe_dev2` during preflight:

```text
swe-dh-shared-registry Up ... 0.0.0.0:8555->5000/tcp
registry_v2_ok
```

The worker rootless daemon was alive and did not already contain the target tag:

```text
docker_info_ok 26.1.3
inspect_rc=1
Error response from daemon: No such image: tb2-offline/torch-tensor-parallelism:20260425
```

## Source Export Failure

The stage command reached this state and made no progress:

```text
/usr/bin/docker save -o .../torch-tensor-parallelism.tar.tmp.2269766 tb2-offline/torch-tensor-parallelism:20260425
```

At about five and a half minutes:

```text
STAT=Sl
%CPU=0.0
read_bytes=0
write_bytes=0
```

No target tar or visible temp tar existed. File descriptors also did not show the output path opened.

A controlled stream probe to `/data/tmp` confirmed the problem is not the shared tar path alone:

```text
# target image, first 64MB only
timeout=120s
output=/data/tmp/tb2_torch_tensor_first64m.tar
size=0
target_probe_rc=124

# qemu-startup control image, first 64MB only
timeout=60s
output=/data/tmp/tb2_qemu_startup_first64m.tar
size=0
control_probe_rc=124
```

Docker `version` and `image inspect` still worked, but Docker image export/save did not begin streaming. `ctr -n moby images ls` returned only the header and did not expose the Docker tags, so no immediate `ctr images export` bypass was available. `skopeo` and `nerdctl` were not installed on `swe_dev`.

## Promotion Decision

Do not update `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` for this row.

Promotion still requires all of the following, and none are available from this attempt:

- stage TSV row with `status=saved_pushed`;
- exact `actual_image_id` matching the source image id;
- nonempty `fallback_tar_sha256`;
- digest-pinned `p0_digest_ref`;
- existing fallback tar with matching sha256;
- worker-j9jjd fallback-load/run-smoke proof with `tar_verified=1`, `loaded=1` or `pulled=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, and `errors=0`.

## Next Action

Before retrying torch or pytorch rows, fix the source export path or make the stage helper fail boundedly. Recommended next implementation slice: add a `--save-timeout-seconds` guard to `scripts/stage_cache_images_from_plan.sh`, then retry a small already-promoted source image as a control and `tb2_torch_tensor_parallelism` as the target with explicit timeout/progress artifacts.

Do not start `tb2_torch_pipeline_parallelism` until Docker export/save is proven healthy again; it is likely to fail the same way.
