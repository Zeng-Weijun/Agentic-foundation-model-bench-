# Runtime Images Round36 - TB2.1 Transport Next Action Review

Scope: report-only runtime/images lane. No production code, manifest, test, Docker pull/load/save/push/run, benchmark, or model execution was performed by this lane. Remote worktree was checked on `dev` at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`, branch `feat/image-warmup-policy`, head `684b479`.

## PASS - Current TB2.1 Static State

The active generated Terminal-Bench 2.1 cache manifest is already past the older 8-row state:

- Manifest: `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`.
- Manifest metadata says `status: materialized_from_swe_dev_cache_84_of_89_offline_transport_ready` at line 4.
- Manifest evidence says `cache_image_count=89`, `shared_tar_count=84`, `offline_transport_ready_count=84`, and `remaining_transport_gap_count=5` at lines 9-14.
- Known blockers include `worker_promoted_offline_transport_is_84_of_89_cached_tasks`, `missing_transport_for_5_cache_tasks`, and `remaining_unpromoted_rows_require_worker_ingest_proof` at lines 15-19.
- Full static fallback verification returned `fallback_tar_verified=84`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, and `required_without_offline_transport=5`; command returned rc 1 as expected because the five required rows still lack offline transport.
- `check --skip-docker --json` returned rc 0 with `tar_verified=84`, `tar_missing=0`, `tar_mismatch=0`, `unchecked=89`, and no Docker identity/error counts.

The five active `missing_shared_tar` rows are:

| Row | Manifest line | Source image id | Source size | Source layers | Current worker cache |
| --- | ---: | --- | ---: | ---: | --- |
| `tb2_mteb_retrieve` | 686 | `sha256:153b4c97f2654e9f04d3908edcf02dd89a4e76081c5985e6bfc901caf936670a` | 2,117,496,845 bytes | 10 | absent |
| `tb2_multi_source_data_merger` | 698 | `sha256:a961d250435509c57119f29bed2fc480ab5e1459af28803d7f00d373e3cf6d83` | 6,203,486,893 bytes | 37 | absent |
| `tb2_pytorch_model_recovery` | 905 | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` | 19,201,784,321 bytes | 13 | absent |
| `tb2_torch_pipeline_parallelism` | 1127 | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | 11,315,069,350 bytes | 6 | absent |
| `tb2_torch_tensor_parallelism` | 1139 | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | 11,026,213,679 bytes | 6 | absent |

The two QEMU rows that were part of the earlier 8-row staging plan are no longer gaps:

- `tb2_qemu_alpine_ssh` is manifest-promoted at line 917 with P0 digest plus fallback tar; worker evidence `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_alpine_worker_check_20260626.json` has `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `errors=0`, and `identity_mismatch=0`.
- `tb2_qemu_startup` is manifest-promoted at line 932 with P0 digest plus fallback tar; worker evidence `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_qemu_startup_worker_check_20260626.json` has `tar_verified=1`, `loaded=1`, `present=1`, `smoke_passed=1`, `errors=0`, and `identity_mismatch=0`.
- Read-only worker inspect with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45` confirmed both QEMU local tags are present by exact source image ID, and the five rows above are absent.

## COMMENT-READY - Stale 8-Row Plan Must Not Drive Bulk Staging

`_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.tsv` is stale for current head `684b479`: it still lists eight rows at lines 2-9, including `install-windows-3.11`, `qemu-alpine-ssh`, and `qemu-startup`, which are already promoted in the active manifest. This is not an ISSUE-READY production bug because the plan is an old evidence artifact and the staging script only acts on the explicit TSV it is given, but it is an operational footgun for the next materialization step.

Dedup: COMMENT-READY for #6 and #12. It is the same transport-population/provenance root: stale staging artifacts must not be interpreted as current manifest readiness.

Concrete fix plan:

- Regenerate a fresh plan from `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` before any new staging, or pass `--only` with one exact current row.
- Do not run the old 8-row TSV without `--only`.
- Prefer writing a new Round36/37 plan artifact so the result carries the current manifest head and five-row count.

Safe dry-run/current-plan command that was executed in this review and returned rc 0:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py plan-stage-missing-transport \
  --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml \
  --inventory _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json \
  --tar-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2 \
  --repository-prefix swe-data-harness \
  --p0-name-prefix terminal-bench-2-1- \
  --json
```

Result: `missing_transport=5`, `matched=5`, `unmatched=0`.

Relevant implementation guardrails already present:

- `scripts/agentic_bench_images.py:819-829` derives staging rows from `missing_offline_transport` in the current manifest lint result.
- `scripts/agentic_bench_images.py:683-689` treats ref matches with conflicting authoritative identity as `identity_mismatch`.
- `scripts/stage_cache_images_from_plan.sh:140-145` fails source-host mismatches.
- `scripts/stage_cache_images_from_plan.sh:148-160` re-inspects the source image ID before `docker save`.
- `scripts/stage_cache_images_from_plan.sh:171-173` records the P0 digest after push.

## COMMENT-READY - Quarantined Rows Stay Quarantined

`mteb-retrieve` and `multi-source-data-merger` have source/P0/fallback evidence from earlier attempts, but they are intentionally not active-manifest ready because worker-j9jjd could not ingest them.

`mteb-retrieve` evidence:

- Retry manifest: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_manifest_20260626.yaml`.
- Retry result: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_20260626.json`.
- Retry rc: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_20260626.rc`.
- Diagnostic artifact: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_mteb_retrieve_worker_retry_diagnostics_20260626.txt`.
- Structured result: `tar_verified=1`, `loaded=0`, `pulled=0`, `present=0`, `missing=1`, `identity_mismatch=0`; fallback load failed during layer registration, and P0 pull failed from inside rootless Docker while host-level registry reachability was separately observed.

`multi-source-data-merger` evidence:

- Staging TSV: `_coordination/20260625_harbor_bench/inventory/tb2_p0_multisource_batch11_20260626.tsv`.
- Worker fallback-load failure: `_coordination/20260625_harbor_bench/inventory/tb2_multisource_batch11_worker_fallback_load_failed_20260626.json`.
- Worker P0-pull failure: `_coordination/20260625_harbor_bench/inventory/tb2_multisource_batch11_worker_p0_pull_failed_20260626.json`.
- Structured fallback result: `tar_verified=1`, `loaded=0`, `present=0`, `missing=1`, `identity_mismatch=0`; fallback load failed during layer registration.
- Structured pull result: `tar_verified=1`, `pulled=0`, `present=0`, `missing=1`, `identity_mismatch=0`; direct P0 pull also failed during layer registration.

Dedup: COMMENT-READY for #8 plus #6/#12/#13. This is not a new ISSUE-READY bug in the current code. The current manifest correctly refuses to promote these rows from source/P0/tar evidence alone, and the static gate still fails required transport for them.

Fix requirement before promotion:

- Keep both rows out of the active manifest until a worker one-row `image_check` returns `tar_verified=1`, `loaded=1` or `pulled=1`, `present=1`, `smoke_passed=1`, `errors=0`, and `identity_mismatch=0` under the explicit worker-j9jjd endpoint with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`.
- Store only allowlisted counts/statuses in runner summaries; keep raw stderr/log bodies pointer-only per #12/#13.

## COMMENT-READY - Next Safe Materialization Candidate

Do not retry `tb2_pytorch_model_recovery` as the next row. It is the largest unpromoted row at 19,201,784,321 bytes, and the prior Round34 attempt did not produce a tar, SHA, or digest:

- Round34 TSV: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.tsv` contains only the header.
- Round34 rc: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.rc` contains `143`.
- Round34 log: `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.log` says the row was aborted after `docker save` made no visible progress.

Recommended next unquarantined row: `tb2_torch_tensor_parallelism`.

Rationale:

- It is still a giant torch row, so it must be isolated, but it is the smallest untried unmaterialized row at 11,026,213,679 bytes and 6 layers.
- It has exact source identity in the current manifest and source inventory: `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
- It has no known prior failed worker-ingest artifact, unlike `mteb-retrieve` and `multi-source-data-merger`.
- `torch-pipeline-parallelism` is the next candidate after it at 11,315,069,350 bytes and 6 layers.
- `pytorch-model-recovery` should remain last unless the source-side save process is wrapped with persistent logging, progress checks, and an explicit timeout.

Recommended next command sequence for the orchestrator or implementation lane, not executed in this review:

```bash
# On swe_dev, in a persistent shell/tmux, first regenerate a current five-row plan.
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py plan-stage-missing-transport \
  --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml \
  --inventory _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json \
  --tar-dir /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2 \
  --repository-prefix swe-data-harness \
  --p0-name-prefix terminal-bench-2-1- \
  --output-tsv _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_round37_current.tsv

# Then stage exactly one unquarantined row.
bash scripts/stage_cache_images_from_plan.sh \
  --plan _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_round37_current.tsv \
  --source-host-label swe_dev \
  --only torch-tensor-parallelism \
  --execute \
  --push \
  --output-tsv _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round37_20260626.tsv
```

Promotion gate after that command:

- Create a one-row manifest for `tb2_torch_tensor_parallelism` with both P0 digest and fallback tar SHA.
- On worker-j9jjd only through the explicit endpoint, run the image checker with `DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45`, prefer fallback-load proof because direct rootless P0 pull remains unreliable under #8.
- Promote the active TB2 manifest only if worker evidence has `tar_verified=1`, `loaded=1` or `pulled=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, and `errors=0`.
- Expected static lint drop after promotion: `required_without_offline_transport` from 5 to 4, `fallback_tar_verified` from 84 to 85, and ready count from 84/89 to 85/89.

## ISSUE-READY Status

No new ISSUE-READY runtime/image bug was confirmed in Round36.

The active code and manifest are currently conservative in the important places:

- Static lint fails because five required rows lack digest-pinned internal refs and verified fallback SHA.
- Worker-ingest failures for mteb/multi-source are not promoted as readiness.
- QEMU rows that now have worker fallback-load/run-smoke proof are promoted and present on worker by exact source image ID.
- The stale 8-row staging plan is a coordination artifact risk, not a current false-green path, as long as the next implementation regenerates a current plan or uses `--only`.

## Command Evidence

All commands were run from the local Mac control plane through `ssh dev`, `ssh swe_dev`, or the explicit worker-j9jjd endpoint. No token, API key, benchmark output, or raw task log was printed.

- `sed -n '1,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc 0.
- `ssh dev 'cd ... && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all'`: rc 0; branch `feat/image-warmup-policy`, head `684b479`; unrelated dirty files existed before this report.
- Manifest parser over `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`: rc 0; `total_rows=89`, `fallback_status_counts={'None': 50, 'missing_shared_tar': 5, 'p0_digest_and_fallback_tar_verified': 34}`, transport split `34 digest+sha`, `50 sha-only`, `5 neither`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --require-offline-transport --verify-fallback-files --json`: rc 1; counts `images=89`, `required_images=89`, `fallback_tar_verified=84`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`, `required_without_offline_transport=5`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --skip-docker --json`: rc 0; counts `tar_verified=84`, `tar_missing=0`, `tar_mismatch=0`, `unchecked=89`, `identity_mismatch=0`, `errors=0`.
- Source cache inventory scan over `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json`, `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_20260626.json`, and `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/swe_dev.docker_cache_inventory.json`: rc 0; all five active gap rows matched `swe_dev` cache.
- `ssh swe_dev 'docker image inspect --format=... <five remaining refs>'`: rc 0; exact sizes and layer counts recorded above.
- Worker read-only `docker image inspect` under `DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45`: rc 0; QEMU refs present, five remaining refs absent.
- Handoff grep for `84/89`, `mteb`, `multi-source`, `qemu`, `rootless`: rc 0; confirmed orchestrator state says the five active gaps are current and mteb/multi-source remain quarantined.
- Current plan dry-run via `plan-stage-missing-transport --json`: rc 0; `missing_transport=5`, `matched=5`, `unmatched=0`.
- Static code line reads for `scripts/agentic_bench_images.py`, `scripts/stage_cache_images_from_plan.sh`, and manifest row line numbers: rc 0.

## Validation

The lane-owned output is this report. Current `git status --short --untracked-files=all` also shows unrelated production/document diffs and `_coordination/20260625_harbor_bench/lanes/runner-results-round36.md` from another lane; this lane did not edit production code or manifests.

- Target path: `_coordination/20260625_harbor_bench/lanes/runtime-images-round36.md`.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runtime-images-round36.md`: rc 0.
- Trailing whitespace scan on the report: rc 0.
- Bounded secret-like scan on the report: rc 0; `authorization_header=0`, `bearer_value=0`, `sk_value=0`, `api_key_assignment=0`, `private_key=0`.