# TB2.1 Runtime Images Round34

## Scope

- Lane: Terminal-Bench 2.1 runtime/images transport materialization.
- Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`.
- Observed branch/head: `feat/image-warmup-policy` / `008d466`.
- Wrote only this report plus new Round34 inventory evidence files under `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/`.
- Did not edit README, manifests, scripts, reports, tests, HANDOFF, commits, or GitHub issues.
- Did not run benchmarks or model calls. Docker-heavy source checks were on `swe_dev`; no worker public pull was attempted.

## Selected Row

Selected `tb2_pytorch_model_recovery` as the single isolated Round34 row.

Reasoning:

- The prompt suggested evaluating `tb2_pytorch_model_recovery` first.
- `mteb-retrieve` and `multi-source-data-merger` already have worker ingest risk and were kept out of the batch.
- The two torch rows are smaller than `pytorch-model-recovery`, but they were not mixed in after the selected row blocked at source-side `docker save`.

Current remaining manifest gaps before Round34 were still these five rows:

- `tb2_mteb_retrieve`
- `tb2_multi_source_data_merger`
- `tb2_pytorch_model_recovery`
- `tb2_torch_pipeline_parallelism`
- `tb2_torch_tensor_parallelism`

## Source Image Identity

Source row from staging plan:

| field | value |
|---|---|
| id | `tb2_pytorch_model_recovery` |
| slug | `pytorch-model-recovery` |
| local_ref | `tb2-offline/pytorch-model-recovery:20260425` |
| source_image_id | `sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4` |
| source_host | `swe_dev` |
| source_size | `19.2GB` in plan, `19201784321` bytes from live inspect |
| fallback_tar target | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/20260425_missing_batch2/pytorch-model-recovery.tar` |
| p0 tag target | `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-pytorch-model-recovery:20260425` |

Live `swe_dev` inspect returned rc `0`:

```text
id=sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4
size=19201784321
cmd=["python3"]
workdir=/app
exposed_ports=[]
volumes=[]
repo_digests=[]
```

Comparison rows inspected before choosing not to mix batches:

| row | source image id | size | default cmd | risk note |
|---|---|---:|---|---|
| `tb2_torch_tensor_parallelism` | `sha256:7f0d9bce1454a49b3890a9af55bab21405a4586cb7fe56d941447be303bdbf97` | `11026213679` | `["/bin/bash"]` | large torch row, defer after selected row blocked |
| `tb2_torch_pipeline_parallelism` | `sha256:a014da66007ddb4eb52ed23f2cceab716410d4c12475770701f982519543f77a` | `11315069350` | `["/bin/bash"]` | large torch row, defer after selected row blocked |

## Stage Attempt

Attempted source-side materialization from `swe_dev` with one row only:

```bash
./scripts/stage_cache_images_from_plan.sh   --plan _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_missing_transport_stage_plan.tsv   --only pytorch-model-recovery   --source-host-label swe_dev   --execute   --push   --output-tsv _coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.tsv
```

Evidence files:

- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.log`
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.tsv`
- `_coordination/20260625_harbor_bench/inventory/remote_cache_20260626/tb2_pytorch_model_recovery_stage_round34_20260626.rc`

Result: source-side staging did not complete.

Observed state:

- The script printed only the selected `ROW ...` line and then entered `docker save`.
- After about 11 minutes, the remote process was still alive in `docker save` with `0.0` CPU, the log was still only the initial row line, and no final or tmp fallback tar was visible at the target path.
- I terminated only the Round34 staging PIDs to avoid leaving a hung save in the background. No prune, restart, delete, or Docker data mutation was performed beyond stopping this lane's own save attempt.
- I wrote rc `143` to the Round34 rc evidence file and appended `ROUND34_ABORTED_BY_AGENT after docker save made no visible progress; see report.` to the log.

Evidence snapshot after stop:

```text
stage rc file: 143
stage log bytes: 441
stage tsv bytes: 168, header only
fallback tar: absent
P0 manifest HEAD/GET check: HTTP 404 for terminal-bench-2-1-pytorch-model-recovery:20260425
```

The source Docker daemon still answered a bounded `docker image inspect` for `tb2-offline/pytorch-model-recovery:20260425` after the stop, so this is recorded as a row materialization blocker at `docker save`, not as source image disappearance.

## Worker Proof

No worker load/run-smoke proof was attempted for `tb2_pytorch_model_recovery` because the source-side stage did not produce either required transport:

- no fallback tar
- no fallback sha
- no P0 digest ref

Worker command requirements for the eventual proof remain:

```bash
ssh -CAXY ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn   'export DOCKER_HOST=unix:///tmp/rl/run/docker.sock DOCKER_API_VERSION=1.45; ... check --load-fallback --run-smoke ...'
```

Do not claim this row worker-ready until a future run has verified fallback sha, loaded the tar, found the local tag, and passed a `--network none` smoke with `identity_mismatch=0`.

## Quarantine Rows Rechecked

`mteb-retrieve` and `multi-source-data-merger` were not staged in Round34.

Registry probe from `dev` returned:

```text
mteb-retrieve 200
multi-source-data-merger 200
```

Those P0 tags are not enough for manifest promotion because prior worker ingest evidence remains bad:

- `mteb-retrieve`: fallback tar load failed on worker with rootless filesystem I/O error in prior evidence; keep quarantined.
- `multi-source-data-merger`: earlier batch11 worker fallback and P0 ingest failures remain the gating evidence; keep quarantined.

## Manifest Patch Summary

No manifest patch should be applied from Round34.

Reason: `tb2_pytorch_model_recovery` did not get a completed fallback tar, fallback sha, P0 digest ref, or worker fallback-load/run-smoke proof. The active row should remain:

```yaml
image_transport: swe_dev_cache_identity
fallback_transport: none
fallback_status: missing_shared_tar
```

If a future retry succeeds, the manifest patch would need to set the row to `p0_digest_plus_fallback_tar`, add the digest-pinned `image_ref`, add `fallback_transport: oci_tar`, set `fallback_status: p0_digest_and_fallback_tar_verified`, add `fallback_tar`, add `fallback_tar_sha256`, and preserve `source_image_id: sha256:3a67ac23a6090b6c83237d1376ba332c355f54884a3c94db367bdc16b52946a4`.

## Next Recommendation

Do not retry `pytorch-model-recovery` blindly on the same path without first deciding whether the source-side save stall was expected shared-storage latency or a Docker/export issue. A safe next controller decision is one of:

1. Retry `pytorch-model-recovery` under a persistent tmux/job wrapper with a longer timeout and periodic file/process telemetry, because it is a 19.2GB image.
2. Try exactly one smaller torch row, preferably `torch-tensor-parallelism` at about 11.0GB, but only if the controller accepts that this is a new large-image export attempt after the selected row stalled.
3. Keep all five rows blocked until a lower-level Docker save/export health check on `swe_dev` is run against a known medium cached image.

Do not promote `mteb-retrieve` or `multi-source-data-merger` from P0 status alone.

## Commands And Exit Codes

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc `0`.
- Read verification skill file; rc `0`.
- Memory grep for relevant TB2/rootless context; rc `0`.
- Remote preflight on `dev`: `git branch --show-current`, `git rev-parse --short HEAD`, `git status --short --untracked-files=all`, HANDOFF excerpt; rc `0`; branch/head `feat/image-warmup-policy` / `008d466`; no status lines were printed before the HANDOFF excerpt.
- Read `scripts/stage_cache_images_from_plan.sh`; rc `0`.
- Parse active TB2 missing rows from `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`; rc `0`; five rows listed above.
- List remote cache inventory and print `tb2_missing_transport_stage_plan.tsv`; rc `0`.
- First `swe_dev` Docker inspect using Go template with `.Config.ExposedPorts`; rc `1` because the key was absent; discarded as operator error.
- `swe_dev` disk/tar existence check; rc `0`; `/data` had `117G` free, shared storage had `13T` free, selected fallback tar absent.
- P0 manifest probes for candidate rows from `dev`; rc `0`; `pytorch-model-recovery`/torch rows returned `404`, mteb/multi-source returned `200`.
- JSON-based `swe_dev` Docker inspect for selected and torch rows; rc `0`; identities and sizes listed above.
- Stage command for `pytorch-model-recovery`; foreground SSH session interrupted after source-side stall; local session rc `255`; remote stage evidence rc file set to `143` after terminating only the Round34 staging PIDs.
- Side checks while staging: process/log/tar probes rc `0`; process showed `docker save` alive at 0 CPU, no fallback tar visible, log only initial row line.
- Post-stop process/tar/log/TSV/rc verification; rc `0`; no Round34 staging PIDs remained, fallback tar absent, TSV header-only, rc `143`.
- Post-stop P0 probe; rc `0`; HTTP `404` for `pytorch-model-recovery` tag.
- Post-stop bounded `docker image inspect` on `swe_dev`; rc `0`; source image still present.

## Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/tb2-transport-round34.md`; rc `0`, no output.
- Because the report is untracked, `git diff --check --no-index -- /dev/null _coordination/20260625_harbor_bench/lanes/tb2-transport-round34.md` was also run; rc `1` because the files differ, with no whitespace diagnostics printed.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/tb2-transport-round34.md || true`; rc `0`, no output, interpreted as no trailing whitespace.
- Bounded secret-like scan for API keys, access/auth tokens, Authorization/Bearer assignments, or private-key headers; rc `0`, no output.
- `git status --short --untracked-files=all`; rc `0`. It showed this lane's new report and three new Round34 `tb2_pytorch_model_recovery_stage_round34_20260626.*` evidence files, plus concurrent untracked Round34 lane reports from other agents. I did not edit those other lane files.
