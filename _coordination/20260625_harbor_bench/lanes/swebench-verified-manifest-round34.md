# SWE-bench Verified offline manifest lane Round34

## Scope

Report-only inventory for SWE-bench Verified offline manifest readiness. No production code, manifest, README, test, Docker state, benchmark, model, commit, or push action was performed. The only intended write is this report.

Authoritative worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` on branch `feat/image-warmup-policy`, observed head `008d466`.

## Full readiness blocker source

Current full SWE-bench Verified readiness is blocked by the repo manifest, not by adapter wiring:

- Suite rows are wired but all four active SWE-bench Verified adapters point at `manifests/images/swebench_verified.yaml` with `image_policy: optional`: `swebench_verified_qwen_code_smoke`, `swebench_verified_mini_swe_agent`, `swebench_verified_swe_agent`, and `swebench_verified_openhands` in `manifests/suite.example.yaml:148-243`.
- `manifests/images/swebench_verified.yaml:4` is still `partial_worker_cache_not_full_manifest`; its own blockers are `exact_task_to_image_digest_map_not_frozen`, `full_500_verified_image_coverage_not_proven`, and `openhands_runtime_image_missing` at `manifests/images/swebench_verified.yaml:10-13`.
- Readiness probe returned rc 1 and reports target `swebench_verified_multi` as `blocked` with blocker `image_manifest_not_materialized`. It counted 4 enabled entries, 0 ready entries, and the shared image manifest counted `images=2`, `optional_placeholders=2`, `required_images=0`, `required_with_offline_transport=0`, `required_without_offline_transport=0`.
- `manifests/bench_registry.yaml:56-64` already distinguishes the materialized `swebench_verified_django10097_identity_probe` from the broader `swebench_verified_multi`, whose policy remains `optional_until_task_image_map_frozen`.

A separate identity probe manifest is much closer to usable smoke readiness:

- `manifests/images/swebench_verified_django10097.yaml:4` is `materialized_from_swe_dev_cache_with_verified_fallback_tars_p0_pending`.
- It has two required rows: `swebench_django10097_eval_base` and `swebench_django10097_swerex_wrapper` at `manifests/images/swebench_verified_django10097.yaml:16-43`.
- Both rows have offline fallback tar paths and SHA256 values. Verified present by size in this round:
  - eval base tar: 2,872,815,104 bytes at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/swebench/django10097/swebench_django10097_eval_base.tar`
  - swerex wrapper tar: 7,832,649,216 bytes at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/django-1776-django_00.tar`

## Asset inventory and adapter mapping

| Asset or evidence | qwen_code | mini_swe_agent | swe_agent | openhands | Status |
| --- | --- | --- | --- | --- | --- |
| Shared SWE-bench Verified tree `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified` | yes | yes | yes | yes | Present, 13G; contains `qwen-code`, `mini-swe-agent`, `swe-agent`, `openhands`, `harness`, and `image_migration`. |
| Shared runner wrappers `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_swebench_verified_*.sh` and `/data/nips/bench/run_swebench_verified_*.sh` | yes | yes | yes | yes | Present. Suite dry-run resolves `/data/nips/bench/run_swebench_verified_mini_swe_agent.sh` and worker rootless Docker env. |
| Migration manifest `swebench_base_500.txt` | candidate | candidate | candidate | base-image candidate only | Present, 500 refs. First rows include `astropy_12907`, `astropy_13033`, `astropy_13236`. |
| Migration manifest `swerex_prebuilt_all.txt` | candidate | candidate | candidate | not enough | Present, 728 wrapper refs. Some tasks have multiple wrapper aliases. |
| Migration manifests `openhands_runtime_current.txt` and `repo2env_all.txt` | no | no | no | blocked | Both are 0 lines in `image_migration/manifests/20260601_170434`; this is the precise OpenHands runtime/offline-transport blocker. |
| Historical identity inventory `_coordination/20260625_harbor_bench/inventory/swe_dev_docker_cache_identities_20260626.json` | strong source inventory | strong source inventory | strong source inventory | no runtime | Present, `images=1320`, `identity_inspected=1320`, `identity_errors=0`. Exact qwen `smoke_n20` base refs are all present in this saved inventory, but this is not current live Docker state. |
| Current live Docker on `ssh dev` | no | no | no | no | Current daemon reported `Images=3` and only `python:3.11-slim`, `alpine:latest`, and `ghcr.io/jessezzzzz/repoarena-new:latest`; no SWE-bench/OpenHands refs are live on this endpoint. |
| Current `/data` paths on `ssh dev` | symlink only | symlink only | symlink only | symlink only | `/data/swe` and `/data/nips` are symlinks to shared storage, but previously reported `/data/swe/docker_prebuilt`, `/data/swe/SWE-bench`, and `/data/tmp/swe-agent-runtime-swebench` were not present on the current `dev` endpoint. Treat older `/data` evidence as historical unless revalidated on the worker that will run. |
| `manifests/images/swebench_verified.yaml` cache match | partial only | not mapped | not mapped | missing | Remote-cache match has 2 manifest rows: django-13810 cache probe matched, OpenHands runtime optional missing. It does not represent qwen smoke_n20, mini, or current swe-agent django10097 smoke. |
| `manifests/images/swebench_verified_django10097.yaml` | not qwen smoke_n20 | not mini default | direct match | no | Good smoke candidate for current swe-agent config because active `swe-agent/config.yaml` smoke filter is `django__django-10097`. |
| Additional tar `/swe-bench-verified/qwen-code/runs/manual_transfer_astropy_7671_20260613_220547/astropy_7671.image.tar` | one qwen smoke task | no | no | no | Present, 2,719,902,720 bytes. Useful fallback candidate for `astropy__astropy-7671` base image only; wrapper and broader qwen rows still need P0/fallback proof. |

Adapter-specific notes:

- qwen_code: suite selector is `QWEN_NATIVE_SUBSET=smoke_n20`. The frozen subset file `/data/nips/aci_evolve/experiments/preregistration/verified_subsets_seed42_v1.json` exists, declares size 20 and hash `d4b59c3eb484fa9e7e2fd31204817f95a2714598c84422235949571b9f8363e6`. A schema-aware check found all 20 expected `swebench/sweb.eval.x86_64.*:latest` base refs in the saved identity inventory. This is enough to generate candidate manifest rows, but not enough to claim current worker readiness because the live `dev` daemon no longer has those images and only one qwen base tar was found.
- mini_swe_agent: suite selector is `MINI_SWE_SUBSET=verified`, `MINI_SWE_SPLIT=test`, `MINI_SWE_SLICE=0:1`, docker environment class. Saved identity inventory has `astropy__astropy-12907` base plus 3 swerex wrapper refs. It needs either P0 digest or fallback tar proof before a required smoke manifest row should be marked ready.
- swe_agent: suite selector is `SWEBENCH_MODE=smoke`; current shared `swe-agent/config.yaml` smoke filter is `django__django-10097`. The existing django10097 identity probe manifest maps this case best and already has required fallback tars, but the active suite row still points to the broader partial manifest.
- openhands: suite only sets `OPENHANDS_EVAL_LIMIT=1`; it does not freeze `OPENHANDS_SELECTED_IDS` or a runtime/pretag tuple. The wrapper has OpenHands base-image and runtime controls, but no OpenHands runtime tar/P0 digest was found and the migration runtime manifest is empty. Keep blocked.

## Minimal commit-ready patch plan

Do not mark `swebench_verified_multi` fully ready yet. Split smoke readiness from full-500 readiness:

1. Add or wire a smoke-only SWE-agent row to `manifests/images/swebench_verified_django10097.yaml` and make that row `image_policy: required` only for `swebench_verified_swe_agent` smoke. This aligns with the current `django__django-10097` smoke selector and existing fallback tars.
2. Keep `swebench_verified_multi` status blocked until exact task image rows cover all intended full entries and OpenHands runtime transport exists.
3. Generate a separate qwen `smoke_n20` manifest draft from the frozen subset and identity inventory. Promote only rows with immutable P0 digest or fallback tar proof to required. The saved identity inventory can seed refs and image IDs; current worker readiness still needs rootless preflight.
4. Generate a mini-swe-agent smoke manifest for the first sliced task only after `astropy__astropy-12907` base and at least one selected wrapper alias have P0 or fallback proof.
5. Leave OpenHands disabled/blocked until both are frozen: selected instance ID(s), and `OPENHANDS_RUNTIME_CONTAINER_IMAGE`/pretag source/target with offline transport.
6. Add readiness wording that django10097 smoke readiness is not full SWE-bench Verified readiness and must not satisfy `readiness_role: full` for `swebench_verified_multi`.

## Minimal worker smoke/preflight commands to run later

Image-only preflight for the existing django10097 probe, no benchmark/model call:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash -lc '\''set -euo pipefail
export BENCH_OFFLINE=1
export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
export DOCKER_API_VERSION=1.45
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy
python3 scripts/agentic_bench_images.py check --image-manifest manifests/images/swebench_verified_django10097.yaml --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench --docker-host unix:///tmp/rl/run/docker.sock --load-fallback --run-smoke --json
'\'''
```

Current suite dry-run for mini-swe-agent, no benchmark/model call, showed the runner still preflights the partial broad manifest:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only swebench_verified_mini_swe_agent --json
```

After a smoke manifest patch, rerun dry-run first and confirm the `image_preflight.manifest` points to the new smoke manifest before any `--execute` adapter smoke. An adapter smoke would be a model call and was intentionally not run in this round.

## Commands and exit codes

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_read_round34 && wc -l /tmp/codex_workflow_read_round34`: rc 0, read 973 lines.
- `ssh dev 'cd <worktree> && pwd && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all && git log --oneline -8'`: rc 0, branch `feat/image-warmup-policy`, head `008d466`, initially clean.
- Shared SWE tree bounded inventory under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`: rc 0, 13G tree, scaffold dirs present, one `astropy_7671` tar found.
- Current live `dev` Docker/read-only inventory: rc 0, Docker root `/mnt/docker_root_swebench_800g`, `Images=3`, no SWE-bench/OpenHands refs in `docker image ls`.
- Migration manifest line checks for `swebench_base_500.txt`, `swerex_prebuilt_all.txt`, `openhands_runtime_current.txt`, `repo2env_all.txt`: rc 0, counts 500, 728, 0, 0.
- Identity and remote-cache JSON parse: rc 0, confirmed historical identity inventory and remote-cache match counts above.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --json`: rc 1, expected because readiness report has 8 blocked targets; SWE-bench Verified blocker is `image_manifest_not_materialized`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only swebench_verified_mini_swe_agent --json`: rc 0, dry-run only; generated worker rootless command and image preflight against `manifests/images/swebench_verified.yaml`.
- Wrapper/selector grep under shared runners and SWE-agent config: rc 0, confirmed qwen `smoke_n20`, mini slice support, OpenHands runtime controls, and current SWE-agent `django__django-10097` smoke selector.

## Blockers

- Current live `dev` Docker cache does not match earlier swe_dev cache artifacts; do not claim worker/full readiness from historical JSON alone.
- Broad `swebench_verified.yaml` has no required offline-transport rows and still contains only a partial cache probe plus OpenHands runtime placeholder.
- OpenHands lacks runtime offline transport and selected-ID freeze.
- qwen `smoke_n20` and mini slice have strong source-inventory coverage but insufficient required-row P0/fallback proof for a current worker-ready manifest.
- Existing django10097 identity manifest is a valid smoke-preflight candidate, but it is not wired to the active suite rows and should not satisfy full SWE-bench Verified readiness.
