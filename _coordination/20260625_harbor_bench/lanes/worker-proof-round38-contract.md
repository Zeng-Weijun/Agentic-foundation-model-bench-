# Worker Proof Round38 Contract: tb2_torch_tensor_parallelism

Lane: report-only worker proof contract
Date: 2026-06-26
Remote worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Observed head: `9fc70ac Fail closed on unwired adapters and parse tau3 summaries`
Writable scope used: this report only

## Result

`tb2_torch_tensor_parallelism` is not promotable yet. The exact promotion contract is the QEMU pattern: a stage TSV row with P0 digest plus fallback tar sha, a one-row worker-check manifest, a worker `agentic_bench.image_check.v1` JSON artifact run against `worker-j9jjd` with `allow_pull=false`, `load_fallback=true`, and `run_smoke=true`, plus rc/stderr artifacts. Current torch tensor staging artifacts are incomplete: the Round38 TSV contains only the header and the log contains only the initial `ROW ...` line, so there is no `fallback_tar_sha256`, no `p0_digest_ref`, no `actual_image_id`, and no `saved_pushed` status to feed into worker proof.

No Docker load/pull/run/save/build was run by this lane.

## Commands Run

| command | rc | evidence |
|---|---:|---|
| `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Workflow read first. |
| `ssh dev 'cd <worktree> && hostname && pwd && git branch --show-current && git rev-parse --short HEAD && git log -1 --oneline && git status --short'` | 0 | Host `zwj2`, branch `feat/image-warmup-policy`, head `9fc70ac`; unrelated untracked torch staging artifacts were already present. |
| `grep -RInE 'qemu-startup|qemu_alpine|qemu-alpine|tb2_torch_tensor_parallelism|torch_tensor|tensor_parallel' _coordination reports manifests scripts` | 0 | Located QEMU stage/worker proof artifacts and active TB2 manifest rows. |
| `sed`/`nl` over QEMU worker manifests and `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` | 0 | QEMU rows are promoted at manifest lines 917-943; torch tensor remains `swe_dev_cache_identity` at lines 1139-1150. |
| Python JSON schema extract over QEMU worker checks | 0 | QEMU worker checks expose `schema_version=agentic_bench.image_check.v1`, counts, mode, per-image fallback/inspect/load/smoke fields. |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --require-offline-transport --verify-fallback-files --json` | 1 | Static lint still reports `required_without_offline_transport=5`, `fallback_tar_verified=84`, `required_with_digest_ref=34`, `required_images=89`. |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --skip-docker --json` | 0 | Static check reports `tar_verified=84`, `unchecked=89`; torch tensor has no `image_refs`, no fallback sha, no tar paths. |

## Existing QEMU Proof Shape

Promoted QEMU manifest rows use this active manifest shape:

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:917-931` for `tb2_qemu_alpine_ssh`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:932-946` for `tb2_qemu_startup`.
- Required fields: `id`, `role: terminal_bench_task_runtime`, `required: true`, `image_transport: p0_digest_plus_fallback_tar`, `local_ref`, digest-pinned `image_ref`, exact `source_image_id`, `needs_network: false`, `fallback_transport: oci_tar`, `fallback_status: p0_digest_and_fallback_tar_verified`, `fallback_tar`, 64-hex `fallback_tar_sha256`, and `smoke.network: none` with generic Python/shell smoke command.

The QEMU worker probe manifests used the same one-row fields but with `fallback_status: staged_p0_digest_and_fallback_tar_pending_worker_proof` before the worker check:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_manifest_20260626.yaml`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_manifest_20260626.yaml`.

The QEMU stage TSV row contract is:

```text
id slug local_ref source_image_id source_host source_ref source_cache_image_id source_size fallback_tar fallback_tar_sha256 p0_tag p0_digest_ref actual_image_id status
```

Required successful values from QEMU examples:

- `status=saved_pushed`.
- `p0_digest_ref` is a digest ref under `100.97.118.137:8555/swe-data-harness/...@sha256:<digest>`.
- `fallback_tar_sha256` is non-empty and 64 hex chars.
- `actual_image_id` equals the manifest `source_image_id`.
- Stage rc artifact contains `0`; stage log has no fatal error.

The QEMU worker JSON contract is `scripts/agentic_bench_images.py check` output:

- `scripts/agentic_bench_images.py:913-925` defines `check_image_manifest(...)` with `allow_pull`, `load_fallback`, and `run_smoke` flags.
- `scripts/agentic_bench_images.py:931-945` defines required count keys: `present`, `missing`, `unchecked`, `errors`, `tar_verified`, `tar_missing`, `tar_mismatch`, `loaded`, `pulled`, `tagged`, `smoke_passed`, `optional_missing`, `identity_mismatch`.
- `scripts/agentic_bench_images.py:1008-1030` loads verified fallback tar and runs smoke only when requested.
- `scripts/agentic_bench_images.py:1046-1060` emits `schema_version: agentic_bench.image_check.v1`, `manifest`, `bench_id`, `asset_root`, `docker_host`, `mode`, `counts`, and `images`.
- `scripts/agentic_bench_images.py:1529-1536` returns rc 2 for errors/tar mismatch/identity mismatch, rc 1 for missing/tar missing, and rc 0 only when the manifest is present enough for the requested mode.

Required successful worker proof values, matching QEMU:

| JSON path | Required value for first promotion proof |
|---|---|
| `schema_version` | `agentic_bench.image_check.v1` |
| `bench_id` | one-row probe id, e.g. `tb2_torch_tensor_parallelism_worker_probe` |
| `docker_host` | `unix:///tmp/rl/run/docker.sock` |
| `mode.skip_docker` | `false` |
| `mode.allow_pull` | `false` until worker direct-P0 pull is re-proven under issue #8 |
| `mode.load_fallback` | `true` |
| `mode.run_smoke` | `true` |
| `counts.tar_verified` | `1` |
| `counts.tar_missing` | `0` |
| `counts.tar_mismatch` | `0` |
| `counts.loaded` | `1` for the initial fallback-load proof; a replay may be `0` only if the original loaded proof is retained |
| `counts.pulled` | `0` for fallback proof |
| `counts.present` | `1` |
| `counts.missing` | `0` |
| `counts.smoke_passed` | `1` |
| `counts.identity_mismatch` | `0` |
| `counts.errors` | `0` |
| `images[0].id` | `tb2_torch_tensor_parallelism` |
| `images[0].required` | `true` |
| `images[0].status` | `present` |
| `images[0].fallback.sha256_status` | `match` |
| `images[0].fallback.sha256_actual` | equals `images[0].fallback.sha256` and the manifest `fallback_tar_sha256` |
| `images[0].fallback.missing_paths` | `[]` |
| `images[0].fallback.present_paths` | contains the shared tar path |
| `images[0].inspect_attempts[-1].returncode` | `0` |
| `images[0].inspect_attempts[-1].identity_status` | `match` |
| `images[0].inspect_attempts[-1].actual_image_id` | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` |
| `images[0].load_status` | `loaded` for initial fallback-load proof |
| `images[0].present_ref` | `tb2-offline/torch-tensor-parallelism:20260425` |
| `images[0].smoke_status` | `passed` |
| rc artifact | literal `0` |
| stderr artifact | empty, or only benign non-secret warnings explicitly reviewed |

## Current Torch Tensor State

Active manifest row at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1139-1150` is still a gap:

```yaml
id: tb2_torch_tensor_parallelism
image_transport: swe_dev_cache_identity
local_ref: tb2-offline/torch-tensor-parallelism:20260425
source_image_id: sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97
fallback_transport: none
fallback_status: missing_shared_tar
```

Static `--skip-docker` check confirms the row has:

- `local_refs=['tb2-offline/torch-tensor-parallelism:20260425']`.
- `image_refs=[]`.
- `expected_image_ids=['sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97']`.
- `fallback.sha256_status='not_configured'`.
- `fallback.tar_paths=[]`.

Observed Round38 staging files are not enough for worker proof:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.tsv` has only the header.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.log` has only the initial `ROW tb2_torch_tensor_parallelism ...` line.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.started` exists.
- No worker-check manifest/json/rc/stderr artifact for torch tensor was found in the inspected evidence.

## Required One-Row Manifest Before Worker Proof

After staging succeeds, create a one-row worker proof manifest with the staged digest and tar sha. Do not promote the active manifest until this worker check passes.

```yaml
schema_version: agentic_bench.image_manifest.v1
bench_id: tb2_torch_tensor_parallelism_worker_probe
images:
  - id: tb2_torch_tensor_parallelism
    role: terminal_bench_task_runtime
    required: true
    image_transport: p0_digest_plus_fallback_tar
    local_ref: tb2-offline/torch-tensor-parallelism:20260425
    image_ref: 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism@sha256:<P0_DIGEST_FROM_STAGE_TSV>
    source_image_id: sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97
    needs_network: false
    fallback_transport: oci_tar
    fallback_status: staged_p0_digest_and_fallback_tar_pending_worker_proof
    fallback_tar: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/torch-tensor-parallelism.tar
    fallback_tar_sha256: <FALLBACK_TAR_SHA256_FROM_STAGE_TSV>
    smoke:
      network: none
      command: "python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok"
```

## Reusable Worker Command

This command is for the future proof owner after staging produces a non-empty TSV row with `status=saved_pushed`, `p0_digest_ref`, and `fallback_tar_sha256`. It intentionally uses fallback load and smoke only; it does not pull from P0.

```bash
WORKER_SSH='ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn'
WORKTREE='/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy'
MANIFEST='_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_worker_check_manifest_20260626.yaml'
OUT='_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_worker_check_20260626.json'
ERR='_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_worker_check_20260626.stderr'
RC='_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_worker_check_20260626.rc'

$WORKER_SSH "cd '$WORKTREE' && export DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45 PYTHONDONTWRITEBYTECODE=1 && python3 scripts/agentic_bench_images.py check --image-manifest '$MANIFEST' --docker-host unix:///tmp/rl/run/docker.sock --load-fallback --run-smoke --json > '$OUT.tmp' 2> '$ERR'; rc=\$?; printf '%s\n' \$rc > '$RC'; mv '$OUT.tmp' '$OUT'; exit \$rc"
```

Acceptance for the command output:

- Shell rc is `0` and `$RC` contains `0`.
- `$ERR` is empty or reviewed as benign and secret-free.
- `$OUT` validates against the required JSON fields above.
- The active TB2 manifest may then change this row to `image_transport: p0_digest_plus_fallback_tar`, set the digest `image_ref`, set `fallback_transport: oci_tar`, set `fallback_status: p0_digest_and_fallback_tar_verified`, and add the exact `fallback_tar` plus `fallback_tar_sha256`.

## Notes

- This is a fallback-load/readiness contract, not a direct worker P0 pull proof. Keep `allow_pull=false` and `pulled=0` until the rootless registry pull issue is resolved and independently re-proven.
- Because this row is about 11GB, run it alone. Do not batch with `tb2_torch_pipeline_parallelism` or `tb2_pytorch_model_recovery` in the first worker proof.
- The generic smoke command must remain `--network none`; it is image transport proof only, not a Terminal-Bench task correctness run.
