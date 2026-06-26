# Runtime/images Round39 bug hunt

Scope: report-only review for Terminal-Bench 2.1 runtime image supply chain toward one-command offline worker execution. I did not edit production code, manifests, tests, or Docker state. No real Docker save/load/pull/run/build command was executed; the only executable repro below used a fake `docker` binary in `/tmp` on `dev`.

Current worktree observation: branch `feat/image-warmup-policy`, head `9f480fe` when inspected. The user-provided pushed-head context (`9fc70ac`) has moved forward.

## Current TB2.1 transport state

PASS / expected blocker remains active.

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml` still has 89 rows and 84 rows with offline transport. The five required rows with neither `image_ref` nor `fallback_tar_sha256` are:
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:686` `tb2_mteb_retrieve`, `fallback_status: missing_shared_tar` at line 694.
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:698` `tb2_multi_source_data_merger`, `fallback_status: missing_shared_tar` at line 706.
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:905` `tb2_pytorch_model_recovery`, `fallback_status: missing_shared_tar` at line 913.
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1127` `tb2_torch_pipeline_parallelism`, `fallback_status: missing_shared_tar` at line 1135.
  - `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1139` `tb2_torch_tensor_parallelism`, `fallback_status: missing_shared_tar` at line 1147.
- Scoped registry lint with fallback-file verification still fails correctly: `missing_offline_transport=5`, `images=89`, rc `1`. This means the current active manifest does not fake-green full TB2.1 readiness.
- `check --skip-docker --json` verified the configured fallback files: `tar_verified=84`, `tar_missing=0`, `tar_mismatch=0`, `errors=0`, rc `0`.

Current staging artifact safety check:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.tsv` has only the header row; its `.rc` is `143`, and the log records `Terminated`. It has no `fallback_tar_sha256`, no `p0_digest_ref`, and no `saved_pushed` row.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_20260626_round39.tsv` also has only the header row; its log is a dry-run skip with rc `0`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_20260626_round39b.tsv` has only the header row and no paired `.rc`/`.ended` file at inspection time. A read-only `ps` probe found no active `stage_cache_images_from_plan`, `docker save`, or `torch-tensor-parallelism` process, so this is a stale incomplete artifact, not promotion evidence.
- Recommendation: continue to require a non-header stage result row plus worker proof before manifest promotion. These current artifacts are not promotable.

## ISSUE-READY: stage TSV can claim `saved_pushed` with an empty P0 digest

severity: P1 supply-chain readiness / false promotion risk.

dedup: Related to #6 because it can corrupt the TB2 transport-population workflow, and related to #12 because normalized provenance should preserve P0/fallback evidence. It is not a duplicate of #8 because no worker rootless ingest is needed to trigger it. It is not the existing identity/source-host guard issue: this is the post-push success criterion for immutable P0 digest capture.

location:

- `scripts/stage_cache_images_from_plan.sh:199-208`
- The push path runs `docker tag`, `docker push`, then captures `p0_digest_ref` with `docker inspect ... || true` at line 207 and unconditionally sets `status="saved_pushed"` at line 208.

minimal repro:

Use a fake Docker executable outside the repo that succeeds for `image inspect`, `save`, `tag`, and `push`, but returns no digest for the post-push `docker inspect --format={{index .RepoDigests 0}}`. Then run the staging script with `--execute --push` on a one-row matched plan. This is non-mutating because `PATH` resolves `docker` to the fake executable in `/tmp`.

Observed repro result:

```text
repro_rc=0
result row status=saved_pushed
fallback_tar_sha256=77d4d51a874ad6c63e0be349049de8fe028c48370acb6cf4f709fcb9d2b6e0ed
p0_digest_ref=<empty>
actual_image_id=sha256:fakeimageid000000000000000000000000000000000000000000000000000000000000
stdout included: stage_cache_images_from_plan: rows=1 staged=1 skipped=0 failed=0
```

impact:

- A source-side staging result can report a row as fully `saved_pushed` even when no immutable P0 digest was captured.
- A downstream manifest patcher or human promotion step could copy a verified fallback sha and treat the P0 route as published, while the digest-pinned worker pull path is not reproducible.
- The active TB2 manifest is currently still safe because the five rows remain missing and registry lint fails. The bug is in the next materialization step: it can produce a misleading stage result before worker proof.

fix:

- After `docker push`, require `p0_digest_ref` to be nonempty and to match the expected registry/repository with `@sha256:`.
- If digest capture fails, write a failure row such as `push_digest_missing`, increment `failed`, keep the fallback tar/sha visible for audit, and exit nonzero.
- Prefer collecting candidate digests with `docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "$p0_tag"` and selecting only refs that start with the expected repository prefix.
- Add a fake-Docker regression test where push succeeds but post-push digest capture is empty; expected rc nonzero and no `saved_pushed` status.

## COMMENT-READY / next safe action

- Do not promote `tb2_torch_tensor_parallelism` from the current Round38/Round39 artifacts. They are header-only or stale incomplete artifacts.
- Before retrying torch/pytorch staging, fix the `saved_pushed` digest guard or have the orchestrator perform an explicit TSV invariant check: every `status=saved_pushed` row must have a nonempty `fallback_tar_sha256`, a nonempty `actual_image_id` matching `source_image_id`, and a `p0_digest_ref` containing `@sha256:` under `100.97.118.137:8555/swe-data-harness/`.
- Keep `tb2_mteb_retrieve` and `tb2_multi_source_data_merger` quarantined under the existing worker/rootless ingest failure path (#8) until a future worker load/pull proof returns `tar_verified=1`, `loaded=1` or `pulled=1`, `present=1`, `smoke_passed=1`, `identity_mismatch=0`, and `errors=0`.

## Commands and rc

- `sed -n '1,430p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`: rc `0`.
- `ssh dev 'cd ...image-warmup-policy && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all'`: rc `0`; branch `feat/image-warmup-policy`, head `9f480fe`.
- `ssh dev 'cd ...image-warmup-policy && PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml --skip-docker --json'`: rc `0`; counts included `tar_verified=84`, `tar_missing=0`, `tar_mismatch=0`, `errors=0`, `unchecked=89`.
- `ssh dev 'cd ...image-warmup-policy && PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint-registry --manifest-id terminal_bench_2_1_swe_dev_cache --require-offline-transport --verify-fallback-files'`: rc `1`; summary `selected_manifests=1`, `images=89`, `missing_offline_transport=5`.
- `ssh dev 'cd ...image-warmup-policy && grep -n "id: tb2_..." manifests/images/terminal_bench_2_1_swe_dev_cache.yaml'`: rc `0`; found the five row line numbers listed above.
- `ssh dev 'cd ...image-warmup-policy && nl -ba scripts/stage_cache_images_from_plan.sh | sed -n "1,230p"'`: rc `0`; confirmed push path at lines 199-208.
- Synthetic fake-Docker repro for `--execute --push` with missing post-push digest: rc `0`; inner script also rc `0`; result row had `status=saved_pushed` and empty `p0_digest_ref`.
- `ssh dev 'cd ...image-warmup-policy && for f in ...tb2_torch_tensor_stage*; do ...; done'`: rc `0`; current torch-tensor stage artifacts have header-only TSVs and no completed `saved_pushed` row.
- `ssh dev 'ps -eo pid,ppid,etime,cmd | grep -E "stage_cache_images_from_plan|docker save|torch-tensor-parallelism" | grep -v grep || true'`: rc `0`; no matching active process.
- Dedup grep across runtime/runner ledgers and handoff for `p0_digest_ref`, `saved_pushed`, `identity_mismatch`, `#6`, `#8`, `#12`, and `#13`: rc `0`; existing worker-proof report requires nonempty digest but the staging script does not enforce it.

## Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runtime-images-round39-bughunt.md`: rc `0`.
- Trailing whitespace scan over `_coordination/20260625_harbor_bench/lanes/runtime-images-round39-bughunt.md`: rc `0`, `trailing_whitespace=0`.
- Bounded secret-like scan over `_coordination/20260625_harbor_bench/lanes/runtime-images-round39-bughunt.md`: rc `0`, `secret_like_hits=0`.
- `git status --short -- _coordination/20260625_harbor_bench/lanes/runtime-images-round39-bughunt.md`: rc `0`, path is untracked (`??`) as expected for this report-only lane.
