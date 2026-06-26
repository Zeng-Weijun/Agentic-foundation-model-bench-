# Runtime Images Round38 - TB2 Torch Tensor Preflight

Scope: continuous bug-hunt A, report-only. I inspected the remote worktree at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` through `ssh dev`. I did not edit production code, tests, or manifests, and did not run Docker save/load/pull/run/build or benchmarks/models. This report is the only intended write from this lane.

## PASS - Candidate Identity And Manifest State

Current pushed head is present in the worktree:

- Branch: `feat/image-warmup-policy`.
- Head: `9fc70ac`.
- Active manifest: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`.

The manifest still has the expected five required offline-transport gaps. Static parsing reported:

- `status: materialized_from_swe_dev_cache_84_of_89_offline_transport_ready`.
- `cache_image_count=89`, `offline_transport_ready_count=84`, `remaining_transport_gap_count=5`.
- `fallback_status_counts`: `None=50`, `p0_digest_and_fallback_tar_verified=34`, `missing_shared_tar=5`.
- Missing/no-offline-transport rows: `tb2_mteb_retrieve`, `tb2_multi_source_data_merger`, `tb2_pytorch_model_recovery`, `tb2_torch_pipeline_parallelism`, `tb2_torch_tensor_parallelism`.

`tb2_torch_tensor_parallelism` is a valid one-row candidate, but still unpromoted:

- Manifest lines: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1139-1150`.
- `local_ref`: `tb2-offline/torch-tensor-parallelism:20260425`.
- Expected source image id: `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
- Current manifest transport: `fallback_transport: none`, `fallback_status: missing_shared_tar`, no `image_ref`, no `fallback_tar_sha256`.
- Smoke contract in manifest: `network: none`, command `python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok`.

Inventory match is clean:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json` has `ref=tb2-offline/torch-tensor-parallelism:20260425`, `image_id=7f0d9bce1454`, `size=11GB`.
- `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json` has the same ref and `full_image_id=sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
- Fresh planner output returned `missing_transport=5`, `matched=5`, `unmatched=0`, and generated the expected torch-tensor row with `source_host=swe_dev`, `source_size=11GB`, target fallback tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/torch-tensor-parallelism.tar`, and P0 tag `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism:20260425`.

Static lint is still fail-closed as desired:

- `fallback_tar_verified=84`.
- `fallback_tar_missing=0`.
- `fallback_tar_mismatch=0`.
- `required_without_offline_transport=5`.
- Lint rc was `1`, expected until the five rows are promoted.

## COMMENT-READY - Current Round38 Stage Is Already In Flight

There are existing untracked Round38 torch-tensor artifacts in the shared worktree. I did not create them:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_round38_current.tsv`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_dryrun.tsv`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.started`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.log`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.tsv`.

The dry-run TSV is good: it contains exactly one selected row, `tb2_torch_tensor_parallelism`, with `status=dry_run`, expected source id, source host `swe_dev`, the fallback tar path, and P0 tag.

The real stage appears in flight on `swe_dev`:

- Start marker: `2026-06-26T12:36:12+08:00`.
- `ps` on `swe_dev` at `2026-06-26T12:41:14+0800` showed the stage wrapper, `scripts/stage_cache_images_from_plan.sh`, and `/usr/bin/docker save -o .../torch-tensor-parallelism.tar.tmp.2269766 tb2-offline/torch-tensor-parallelism:20260425` still running for about 5 minutes.
- The stage TSV currently has only the header row.
- No `.rc` or `.ended` artifact exists yet.
- The stage log currently has only the `ROW tb2_torch_tensor_parallelism ...` line.
- No final tar or visible temp tar was found by read-only `stat`/`ls` from `dev` or `swe_dev` at the snapshot time.

Dedup: COMMENT-READY for #6/#8/#12/#13. This is not a new ISSUE-READY bug yet. It is an in-flight large-image source-side save with no completed transport artifact. It becomes a blocker only if the process exits nonzero, leaves only partial artifacts, or remains stuck beyond the orchestrator's timeout.

## PASS - Stage Script Guardrails

The staging script has the right identity and source-host checks for this row:

- `scripts/stage_cache_images_from_plan.sh:140-145` fails when `--source-host-label` does not match the plan's `source_host`.
- `scripts/stage_cache_images_from_plan.sh:148-155` re-inspects the local image and fails `identity_mismatch` if the actual image id does not equal `source_image_id`.
- `scripts/stage_cache_images_from_plan.sh:157-164` writes to a temp tar, renames only after `docker save`, sets mode `0644`, and computes `fallback_tar_sha256`.
- `scripts/stage_cache_images_from_plan.sh:171-174` tags, pushes, and records the digest ref when `--push` is used.

This is sufficient to let the orchestrator stage exactly one row, provided it does not launch a duplicate while the current Round38 stage is running.

## COMMENT-READY - Worker Proof Contract

Worker proof is still mandatory after staging succeeds. The row must not be promoted from source-stage evidence alone.

Relevant checker contract:

- `scripts/agentic_bench_images.py:1008-1016` loads a verified fallback tar when the image is absent and `--load-fallback` is set.
- `scripts/agentic_bench_images.py:1018-1031` marks the image present and runs the manifest smoke command when `--run-smoke` is set.
- `scripts/agentic_bench_images.py:1034-1039` distinguishes `identity_mismatch` from required missing rows.

Prior worker evidence supports the same gate:

- QEMU rows passed fallback-load/run-smoke with `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `errors=0`, `identity_mismatch=0` in `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_20260626.json` and `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_20260626.json`.
- `mteb-retrieve` and `multi-source-data-merger` verified tar identity but failed rootless worker ingest, so they remain quarantined. This is why torch-tensor still needs an actual worker proof and cannot be marked ready from P0/fallback tar presence alone.

Expected worker proof command shape after successful staging, not executed by this lane:

```bash
ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn '
  export DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45
  cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
  PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check \
    --image-manifest _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_worker_check_manifest_20260626.yaml \
    --docker-host unix:///tmp/rl/run/docker.sock \
    --load-fallback \
    --run-smoke \
    --json
'
```

Promotion gate for the active TB2 manifest:

- Stage TSV has one completed row for `tb2_torch_tensor_parallelism` with `status=saved_pushed`, `actual_image_id` equal to `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`, nonempty `fallback_tar_sha256`, and nonempty P0 digest ref.
- Fallback tar exists at the planned path and its SHA matches the stage TSV/one-row manifest.
- Worker one-row check returns `tar_verified=1`, `loaded=1` or `pulled=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, `errors=0`, and `missing=0` under the explicit worker endpoint with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`.
- Prefer fallback-load proof over P0-only proof until #8 re-proves rootless direct registry pulls reliably.

## ISSUE-READY Status

No new ISSUE-READY runtime/image bug is confirmed in this review.

The current risk is operational, not a new code false-green:

- `tb2_torch_tensor_parallelism` is a valid isolated next candidate.
- The static manifest still fails closed with five missing transports.
- The planner matches the candidate to the expected `swe_dev` cache identity.
- A stage is already in flight. Starting a second stage would be unsafe because it would race on the same fallback tar/P0 tag artifacts.
- The active manifest should remain unchanged until the in-flight stage and subsequent worker proof both pass.

## Orchestrator Go/No-Go

Decision: do not start another one-row stage now. A one-row stage for `tb2_torch_tensor_parallelism` is already running on `swe_dev`.

The orchestrator may safely continue by monitoring the existing stage artifacts. If the in-flight stage finishes with a complete `saved_pushed` TSV row, digest ref, and fallback tar SHA, then it may safely run the one-row worker fallback-load/run-smoke proof. If the in-flight stage exits nonzero or remains in `docker save` with no output artifacts beyond the timeout the orchestrator accepts for an 11GB image, keep the row unpromoted and record a source-side staging blocker.

## Command Evidence

- `sed -n '1,430p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- Memory/skill quick pass over `MEMORY.md`, `systematic-debugging`, and `verification-before-completion`: rc 0.
- `ssh dev 'cd ... && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all'`: rc 0; branch `feat/image-warmup-policy`, head `9fc70ac`.
- Manifest parser over `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`: rc 0; confirmed 89 rows, 84 ready, five gaps, and the torch-tensor row details.
- `find _coordination/20260625_harbor_bench/inventory ... '*torch*tensor*' '*round38*'`: rc 0; found Round38 current plan, dry-run, started/log/TSV artifacts.
- Handoff and prior-ledger grep for torch-tensor/84-of-89 context: rc 0.
- Round38 artifact read: rc 0; dry-run row present, real stage TSV header-only, log row-only, no rc/ended.
- `ssh swe_dev 'ps -eo ... | grep -E "stage_cache_images_from_plan|torch-tensor|docker save|docker push"'`: rc 0; active wrapper/script/docker-save processes found.
- Read-only `stat`/`ls` of planned tar and temp tar paths from `dev` and `swe_dev`: rc 0; no final tar or visible temp tar found at snapshot time.
- Source inventory read over `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json` and `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`: rc 0; source ref and full image id match the manifest.
- Static line reads for `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, `scripts/stage_cache_images_from_plan.sh`, and `scripts/agentic_bench_images.py`: rc 0.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py plan-stage-missing-transport ... --json`: rc 0; `missing_transport=5`, `matched=5`, `unmatched=0`, torch-tensor row matched.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --require-offline-transport --verify-fallback-files --json`: rc 1; expected fail-closed with `fallback_tar_verified=84`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=5`.
- Prior worker proof JSON summaries for QEMU/mteb/multi-source: rc 0.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --help`: rc 0; used only to record the worker proof CLI flags.

## Validation

Run after writing this report:

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runtime-images-round38-torch-tensor-preflight.md`: rc 0.
- Trailing whitespace scan on this report: rc 0.
- Bounded secret-like scan on this report: rc 0; `authorization_header=0`, `bearer_value=0`, `sk_value=0`, `api_key_assignment=0`, `private_key=0`.
- Final `git status --short --untracked-files=all`: rc 0; showed this report plus pre-existing/unrelated Round38 staging artifacts and other lane reports (`stage-script-round38-review.md`, `worker-proof-round38-contract.md`). This lane wrote only `_coordination/20260625_harbor_bench/lanes/runtime-images-round38-torch-tensor-preflight.md`.
