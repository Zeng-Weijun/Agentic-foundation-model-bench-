# Stage script Round38 review: torch-tensor-parallelism only

Date: 2026-06-26
Lane: report-only implementation review
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Branch/head checked: `feat/image-warmup-policy` at `9fc70ac Fail closed on unwired adapters and parse tau3 summaries`
Scope: inspect `scripts/stage_cache_images_from_plan.sh` and `scripts/agentic_bench_images.py`; do not run Docker-mutating commands; write this report only.

## Summary

The current scripts are sufficient to stage only `torch-tensor-parallelism`, but the flow must stay narrow:

1. Regenerate or validate a current stage plan from `terminal_bench_2_1_swe_dev_cache.yaml` and the `swe_dev` cache inventory.
2. Run `scripts/stage_cache_images_from_plan.sh` on the source Docker host `swe_dev` with `--only tb2_torch_tensor_parallelism --execute --push`.
3. Use the stage result TSV to create a one-row worker-check manifest under `_coordination/.../inventory/remote_cache_20260626/`.
4. Gate it with static lint and then a worker check using `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` and `DOCKER_API_VERSION=1.45`.

Do not feed the stage result TSV back as a plan: the plan TSV has 11 columns, while the result TSV has 14 columns.

## Current torch row state

The source manifest row is still an audit/cache row, not a worker transport row:

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1139` has id `tb2_torch_tensor_parallelism`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1143` local ref is `tb2-offline/torch-tensor-parallelism:20260425`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1144` source image id is `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1146` / `:1147` still say `fallback_transport: none` and `fallback_status: missing_shared_tar`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:1148` to `:1150` contain the safe no-network smoke command.

The existing stage plan row matches `swe_dev`:

```text
tb2_torch_tensor_parallelism	torch-tensor-parallelism	tb2-offline/torch-tensor-parallelism:20260425	sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97	swe_dev	tb2-offline/torch-tensor-parallelism:20260425	7f0d9bce1454	11GB	/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/torch-tensor-parallelism.tar	100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism:20260425	matched
```

Bounded artifact check found an incomplete prior Round38 attempt:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.started` exists with `2026-06-26T12:36:12+08:00`.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.log` contains only the initial `ROW ...` line.
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_torch_tensor_stage_round38_20260626.tsv` has only the header row.
- The `.rc` artifact is missing.
- The expected tar `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/torch-tensor-parallelism.tar` does not exist.
- `ps` did not show a live `stage_cache_images_from_plan`, `docker save`, `docker push`, or torch-tensor process during this review.

Treat that prior attempt as abandoned. Use a fresh timestamped result/log/rc set for any retry.

## Script behavior that matters

`stage_cache_images_from_plan.sh`:

- `scripts/stage_cache_images_from_plan.sh:6` documents `--plan`, `--execute`, `--push`, `--source-host-label`, `--output-tsv`, and `--only`.
- `scripts/stage_cache_images_from_plan.sh:8` to `:11` state it is dry-run by default and must run on the source Docker host for real staging.
- `scripts/stage_cache_images_from_plan.sh:74` to `:87` allow `--only` to match either id or slug. Use the id `tb2_torch_tensor_parallelism` to be unambiguous.
- `scripts/stage_cache_images_from_plan.sh:99` to `:106` define the result TSV columns, including `fallback_tar_sha256`, `p0_digest_ref`, `actual_image_id`, and `status`.
- `scripts/stage_cache_images_from_plan.sh:140` to `:145` fail closed on source-host mismatch before Docker work.
- `scripts/stage_cache_images_from_plan.sh:148` to `:164` inspect the actual image id before saving the tar and compute the tar sha.
- `scripts/stage_cache_images_from_plan.sh:165` to `:174` tag/push only when `--push` is present and then records the digest ref.

`agentic_bench_images.py`:

- `scripts/agentic_bench_images.py:330` to `:413` implement static manifest lint; with `--require-offline-transport --verify-fallback-files`, the gate requires a digest ref or verified fallback sha and verifies the tar file/hash.
- `scripts/agentic_bench_images.py:428` to `:502` inventory a Docker cache; `--inspect-identities` adds full image IDs when used.
- `scripts/agentic_bench_images.py:693` to `:792` match manifest rows against one or more inventory JSON files.
- `scripts/agentic_bench_images.py:809` to `:873` generate the missing-transport stage plan from required manifest rows whose offline transport is still missing.
- `scripts/agentic_bench_images.py:876` to `:895` write the 11-column stage plan TSV.
- `scripts/agentic_bench_images.py:898` to `:910` builds the no-network smoke command from the manifest row.
- `scripts/agentic_bench_images.py:913` to `:1061` implement worker/cache checks, including inspect, optional internal-registry pull, fallback load, local retag after digest pull, and smoke.
- `scripts/agentic_bench_images.py:1348` to `:1357` define the `check` CLI flags: `--pull`, `--load-fallback`, `--run-smoke`, and `--skip-docker`.
- `scripts/agentic_bench_images.py:1510` to `:1536` return nonzero on errors, tar mismatch, identity mismatch, missing required rows, or missing tar.

## Command recipe

All paths below assume this worktree:

```bash
WT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
ASSET_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
INV_DIR=_coordination/20260625_harbor_bench/inventory/remote_cache_20260626
TAR_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2
ROW_ID=tb2_torch_tensor_parallelism
SLUG=torch-tensor-parallelism
```

### 1. Regenerate and narrow-check the current plan on `dev`

This is non-Docker and safe to run from the controller worktree.

```bash
ssh dev "cd $WT && \
  PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py plan-stage-missing-transport \
    --image-manifest manifests/images/terminal_bench_2_1_swe_dev_cache.yaml \
    --inventory $INV_DIR/swe_dev.docker_cache_inventory.json \
    --tar-dir $TAR_DIR \
    --p0-name-prefix terminal-bench-2-1- \
    --output-tsv $INV_DIR/tb2_missing_transport_stage_round38_current.tsv \
    --json > $INV_DIR/tb2_missing_transport_stage_round38_current.json"
```

Gate the plan to exactly one selected row before staging:

```bash
ssh dev "cd $WT && \
  awk -F '\t' 'NR==1 || \$1==\"tb2_torch_tensor_parallelism\"' \
    $INV_DIR/tb2_missing_transport_stage_round38_current.tsv && \
  test \"\$(awk -F '\t' '\$1==\"tb2_torch_tensor_parallelism\"{n++} END{print n+0}' \
    $INV_DIR/tb2_missing_transport_stage_round38_current.tsv)\" = 1"
```

Expected selected row values:

- `local_ref=tb2-offline/torch-tensor-parallelism:20260425`
- `source_image_id=sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`
- `source_host=swe_dev`
- `source_size=11GB`
- `fallback_tar=$TAR_DIR/torch-tensor-parallelism.tar`
- `p0_tag=100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism:20260425`
- `match_status=matched`

### 2. Dry-run the stage helper against only this row

This is still non-mutating because `--execute` is omitted.

```bash
ssh dev "cd $WT && \
  scripts/stage_cache_images_from_plan.sh \
    --plan $INV_DIR/tb2_missing_transport_stage_round38_current.tsv \
    --only tb2_torch_tensor_parallelism \
    --source-host-label swe_dev \
    --output-tsv $INV_DIR/tb2_torch_tensor_stage_round38_dryrun.tsv"
```

Gate:

```bash
ssh dev "cd $WT && \
  awk -F '\t' '\$1==\"tb2_torch_tensor_parallelism\"{print; ok=(\$14==\"dry_run\")} END{exit ok?0:1}' \
    $INV_DIR/tb2_torch_tensor_stage_round38_dryrun.tsv"
```

### 3. Execute the real stage on `swe_dev` only when writes are approved

This is the mutating step and was not run in this review. It performs `docker image inspect`, `docker save`, `docker tag`, and `docker push`.

Use a persistent shell per `WORKFLOW.md` because this row is about 11GB:

```bash
tmux new -s tb2-torch-tensor-stage-r38
ssh -CAXY zengweijun+zwj.group-ailab-mineruinfra-mineruinfra-cpu+root.ailab-mineruinfra.ws@h.pjlab.org.cn
```

Then on `swe_dev`:

```bash
set -euo pipefail
source ~/.bashrc || true
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy

REG=100.97.118.137:8555
CERT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/swe-data-harness/registry/certs/domain.crt
INV_DIR=_coordination/20260625_harbor_bench/inventory/remote_cache_20260626
PLAN=$INV_DIR/tb2_missing_transport_stage_round38_current.tsv
TS=$(date +%Y%m%d_%H%M%S)
OUT=$INV_DIR/tb2_torch_tensor_stage_round38_${TS}.tsv
LOG=$INV_DIR/tb2_torch_tensor_stage_round38_${TS}.log
RC=$INV_DIR/tb2_torch_tensor_stage_round38_${TS}.rc
STARTED=$INV_DIR/tb2_torch_tensor_stage_round38_${TS}.started

mkdir -p /etc/docker/certs.d/$REG
cp "$CERT" /etc/docker/certs.d/$REG/ca.crt
mkdir -p "$INV_DIR"
date -Iseconds > "$STARTED"

# Optional preflight gates before the mutating save/push:
docker image inspect tb2-offline/torch-tensor-parallelism:20260425 --format '{{.Id}}'
df -h "$TAR_DIR" /data/docker 2>/dev/null || df -h "$TAR_DIR"
curl -k -fsS https://$REG/v2/ >/dev/null

set +e
scripts/stage_cache_images_from_plan.sh \
  --plan "$PLAN" \
  --only tb2_torch_tensor_parallelism \
  --source-host-label swe_dev \
  --execute \
  --push \
  --output-tsv "$OUT" \
  >"$LOG" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$RC"
exit "$rc"
```

Expected stage result gate:

```bash
RESULT=$OUT PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import csv
import os
from pathlib import Path

result = Path(os.environ['RESULT'])
rows = list(csv.DictReader(result.open(), delimiter='\t'))
rows = [row for row in rows if row['id'] == 'tb2_torch_tensor_parallelism']
assert len(rows) == 1, rows
row = rows[0]
assert row['status'] == 'saved_pushed', row
assert row['actual_image_id'] == row['source_image_id'], row
assert row['fallback_tar_sha256'] and len(row['fallback_tar_sha256']) == 64, row
assert '@sha256:' in row['p0_digest_ref'], row
assert Path(row['fallback_tar']).is_file(), row['fallback_tar']
print(row['fallback_tar'])
print(row['fallback_tar_sha256'])
print(row['p0_digest_ref'])
PY
```

### 4. Create the one-row worker-checkable manifest from the stage result

This writes only a coordination artifact, not a production manifest.

```bash
RESULT=$OUT
MANIFEST=$INV_DIR/tb2_torch_tensor_worker_check_manifest_${TS}.yaml
RESULT="$RESULT" MANIFEST="$MANIFEST" PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import csv
import os
from pathlib import Path

result = Path(os.environ['RESULT'])
manifest = Path(os.environ['MANIFEST'])
rows = list(csv.DictReader(result.open(), delimiter='\t'))
rows = [row for row in rows if row['id'] == 'tb2_torch_tensor_parallelism']
assert len(rows) == 1, rows
row = rows[0]
assert row['status'] == 'saved_pushed', row
assert row['actual_image_id'] == row['source_image_id'], row
assert '@sha256:' in row['p0_digest_ref'], row
assert row['fallback_tar_sha256'] and len(row['fallback_tar_sha256']) == 64, row
content = f"""schema_version: agentic_bench.image_manifest.v1
bench_id: tb2_torch_tensor_parallelism_worker_probe
images:
  - id: tb2_torch_tensor_parallelism
    role: terminal_bench_task_runtime
    required: true
    image_transport: p0_digest_plus_fallback_tar
    local_ref: {row['local_ref']}
    image_ref: {row['p0_digest_ref']}
    source_image_id: {row['source_image_id']}
    needs_network: false
    fallback_transport: oci_tar
    fallback_status: staged_p0_digest_and_fallback_tar_pending_worker_proof
    fallback_tar: {row['fallback_tar']}
    fallback_tar_sha256: {row['fallback_tar_sha256']}
    smoke:
      network: none
      command: \"python3 --version 2>/dev/null || python --version 2>/dev/null || echo tb2-smoke-ok\"
"""
manifest.write_text(content, encoding='utf-8')
print(manifest)
PY
```

### 5. Static manifest gate on `dev`

This hashes only the one staged tar and uses no Docker:

```bash
ssh dev "cd $WT && \
  PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_images.py lint \
    --image-manifest $MANIFEST \
    --asset-root $ASSET_ROOT \
    --require-offline-transport \
    --verify-fallback-files \
    --json > $INV_DIR/tb2_torch_tensor_worker_check_manifest_${TS}.lint.json"
```

Expected gate: rc 0 and counts equivalent to `images=1`, `required_images=1`, `required_with_digest_ref=1`, `required_with_fallback_sha=1`, `fallback_tar_verified=1`, `required_without_offline_transport=0`, `fallback_tar_missing=0`, `fallback_tar_mismatch=0`.

### 6. Worker-check command after static lint passes

This is a worker Docker-mutating check and was not run in this review. It should be run only after the manifest exists and static lint is clean.

```bash
WORKER=ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
CHECK_JSON=$INV_DIR/tb2_torch_tensor_worker_check_${TS}.json
CHECK_ERR=$INV_DIR/tb2_torch_tensor_worker_check_${TS}.stderr
CHECK_RC=$INV_DIR/tb2_torch_tensor_worker_check_${TS}.rc

ssh -CAXY "$WORKER" "cd $WT && \
  export DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45 PYTHONDONTWRITEBYTECODE=1 && \
  python3 scripts/agentic_bench_images.py check \
    --image-manifest $MANIFEST \
    --asset-root $ASSET_ROOT \
    --docker-host unix:///tmp/rl/run/docker.sock \
    --pull \
    --load-fallback \
    --run-smoke \
    --json > $CHECK_JSON 2>$CHECK_ERR; \
  rc=\$?; printf '%s\n' \$rc > $CHECK_RC; exit \$rc"
```

Expected worker gate:

```bash
ssh dev "cd $WT && \
  CHECK_JSON=$CHECK_JSON PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
import os
from pathlib import Path
p = Path(os.environ['CHECK_JSON'])
doc = json.loads(p.read_text())
counts = doc['counts']
assert counts['present'] == 1, counts
assert counts['smoke_passed'] == 1, counts
assert counts['errors'] == 0, counts
assert counts['identity_mismatch'] == 0, counts
assert counts['missing'] == 0, counts
assert counts['tar_mismatch'] == 0, counts
# On current worker, fallback load is acceptable because direct P0 pulls are still flaky under #8.
assert counts['pulled'] == 1 or counts['loaded'] == 1, counts
image = doc['images'][0]
assert image['status'] == 'present', image
assert image.get('present_ref') == 'tb2-offline/torch-tensor-parallelism:20260425', image
print(counts)
PY"
```

## Risks

- Large artifact risk: the row is about 11GB. `docker save` writes a large tar under shared storage and `docker push` sends a large layer set to the P0 registry. Check free space before running.
- Existing stale attempt: the current Round38 `.started`/`.log`/header-only `.tsv` has no rc and no tar. Use fresh timestamped artifacts or explicitly quarantine the stale files before rerun.
- Source host must be `swe_dev`: the stage plan source host is `swe_dev`; the script intentionally fails if `--source-host-label` does not match. Do not execute from `dev` or worker.
- Registry pull on worker is not enough: prior evidence shows worker host network may reach P0 while rootless Docker pull can still fail with `network is unreachable`. Keep fallback tar and require `--load-fallback` until #8 is closed.
- Fallback load can also fail: prior `mteb-retrieve` retry had a verified tar and still failed rootless Docker load with an `input/output error`. A passing static lint is necessary but not sufficient.
- The stage script does not update `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`. Production manifest promotion should happen only after the worker one-row check passes, and is out of scope for this report-only lane.
- The result TSV is not a plan TSV. It includes extra columns and should only feed the manifest-generation step, not `stage_cache_images_from_plan.sh --plan`.
- `docker inspect --format='{{index .RepoDigests 0}}'` must return a digest after push. If `p0_digest_ref` is empty, do not create the worker manifest; fix the push/digest capture first.

## Promotion gates

A torch-only promotion can be considered worker-checkable only when all of these are true:

1. Plan row count for `tb2_torch_tensor_parallelism` is exactly 1 and `match_status=matched`.
2. Dry run emits exactly one selected result row with `status=dry_run`.
3. Real stage rc is 0 and result row has `status=saved_pushed`.
4. `actual_image_id` equals `source_image_id` exactly: `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97`.
5. Fallback tar exists at `$TAR_DIR/torch-tensor-parallelism.tar` and its sha matches the result TSV.
6. `p0_digest_ref` is nonempty and uses `@sha256:` under `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-torch-tensor-parallelism`.
7. One-row manifest static lint with `--require-offline-transport --verify-fallback-files` returns rc 0.
8. Worker check returns rc 0 with `present=1`, `smoke_passed=1`, `errors=0`, `identity_mismatch=0`, `missing=0`, and either `pulled=1` or `loaded=1`.
9. If worker uses fallback load rather than pull, record it as fallback-ready, not direct-P0-pull-ready.
10. Only after worker proof should a separate production-manifest patch change the source row from `swe_dev_cache_identity` / `missing_shared_tar` to `p0_digest_plus_fallback_tar`.

## Commands run during this review

| Command | rc | Notes |
| --- | ---: | --- |
| `sed -n ... /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Required workflow preflight; rerun in smaller chunks after initial output truncation. |
| `ssh dev 'cd ... && git branch --show-current && git rev-parse --short HEAD && git status --short'` | 0 | Confirmed branch `feat/image-warmup-policy`, head `9fc70ac`; saw pre-existing untracked Round38 artifacts. |
| `nl -ba scripts/stage_cache_images_from_plan.sh` | 0 | Inspected stage helper behavior and line references. |
| `nl -ba scripts/agentic_bench_images.py` | 0 | Inspected plan, lint, check, and CLI behavior. |
| `grep -RIn 'torch-tensor-parallelism...' manifests scripts _coordination reports` | 0 | Located manifest row, plan row, and previous lane evidence. |
| `nl -ba manifests/images/terminal_bench_2_1_swe_dev_cache.yaml | sed -n '1128,1168p'` | 0 | Confirmed current torch row still lacks P0/fallback transport. |
| `nl -ba scripts/README.md | sed -n '96,150p'` and `nl -ba manifests/images/README.md | sed -n '1,80p'` | 0 | Confirmed documented staging/lint contracts. |
| Read existing one-row worker manifests for install-windows and qemu rows | 0 | Reused established manifest shape. |
| Checked tar path existence for `torch-tensor-parallelism.tar` | 0 | Tar absent; no `.tmp` tar present. |
| Read current Round38 `.started`, `.log`, `.tsv`, and process list | 0 | Found stale/incomplete attempt and no live staging process. |
| Full-manifest `check --skip-docker` probe | interrupted | It began hashing all fallback tars and was intentionally interrupted as too broad for this lane; no Docker action was involved. |
