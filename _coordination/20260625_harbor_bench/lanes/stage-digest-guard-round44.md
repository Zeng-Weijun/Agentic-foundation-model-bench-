# Round44 stage cache digest guard

Date: 2026-06-26
Lane: implementation, GitHub #22 digest guard
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/stage-digest-guard-round44`
Branch: `feat/stage-digest-guard-round44`
Base: `origin/feat/image-warmup-policy` at `6e86f1e`

## Scope

Allowed writes used:

- `scripts/stage_cache_images_from_plan.sh`
- `scripts/test_agentic_bench_images.py`
- `_coordination/20260625_harbor_bench/lanes/stage-digest-guard-round44.md`

No Terminal-Bench staging was run. No Docker push/save/load/pull/run/build was
run against the host Docker daemon; Docker interactions were only through the
existing fake-Docker unittest harness with `PATH` pointed at a temporary script.

## Root cause

`stage_cache_images_from_plan.sh` accepted the first non-empty value returned by:

```bash
docker inspect --format='{{index .RepoDigests 0}}' "$p0_tag"
```

That can mark a row `saved_pushed` even when the local tag has a RepoDigest for a
different repository. The required invariant is stricter: a pushed row is valid
only if the selected digest ref matches the pushed P0 repository prefix:

```text
${p0_tag%:*}@sha256:<64 lowercase hex chars>
```

## Test-first reproduction

Added `test_stage_cache_images_script_rejects_wrong_push_repository_digest`.
The fake Docker script returns a successful push plus this wrong repository
digest:

```text
100.97.118.137:8555/swe-data-harness/other-repo@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

for this pushed tag:

```text
100.97.118.137:8555/swe-data-harness/expected-repo:20260425
```

Red command and result:

```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/stage-digest-guard-round44
python3 -m unittest scripts.test_agentic_bench_images.AgenticBenchImagesTest.test_stage_cache_images_script_rejects_wrong_push_repository_digest
# rc=1, expected failure: AssertionError: 0 != 1
```

## Implementation

The script now:

- reads all RepoDigests with `{{range .RepoDigests}}{{println .}}{{end}}`;
- selects only a digest whose prefix is `${p0_tag%:*}@sha256:`;
- requires the digest suffix to be exactly 64 lowercase hex characters;
- preserves `push_digest_missing` when Docker reports no RepoDigests;
- writes `push_digest_mismatch` and exits non-zero when RepoDigests exist but
  none match the pushed P0 repository.

On mismatch, the first observed non-empty RepoDigest is preserved in the output
TSV `p0_digest_ref` column for auditability.

## Verification run so far

```bash
python3 -m unittest scripts.test_agentic_bench_images.AgenticBenchImagesTest.test_stage_cache_images_script_rejects_wrong_push_repository_digest
# rc=0, 1 test OK

python3 -m unittest scripts.test_agentic_bench_images
# rc=0, Ran 26 tests, OK

bash -n scripts/stage_cache_images_from_plan.sh
# rc=0
```

Final pre-commit gates:

```bash
git diff --check -- scripts/stage_cache_images_from_plan.sh scripts/test_agentic_bench_images.py _coordination/20260625_harbor_bench/lanes/stage-digest-guard-round44.md
# rc=0

secret scan over changed files
# matches=0, rc=0
```
