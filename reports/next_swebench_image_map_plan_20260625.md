# Next SWE-bench Image Map Plan - 2026-06-25

## Scope

Report-only lane. I did not run benchmarks, `docker pull`, `docker load`,
service restarts, or repo code/manifest edits. Worker checks used the explicit
worker endpoint:

`ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`

## Current repo state

- `manifests/suite.example.yaml` has four SWE-bench Verified rows:
  `swebench_verified_qwen_code_smoke`,
  `swebench_verified_mini_swe_agent`,
  `swebench_verified_swe_agent`, and `swebench_verified_openhands`.
- All four rows point at `manifests/images/swebench_verified.yaml`.
- All four rows still use `image_policy: optional`, so current suite preflight
  is advisory rather than required.
- `manifests/images/swebench_verified.yaml` is explicitly partial:
  `status: partial_worker_cache_not_full_manifest`, with blockers
  `exact_task_to_image_digest_map_not_frozen`,
  `full_500_verified_image_coverage_not_proven`, and
  `openhands_runtime_image_missing`.
- `scripts/agentic_bench_suite.py` only treats image preflight as required once
  `image_policy` is changed away from `optional|none|disabled|skip`.
- Worker cached SWE-bench tags have empty `RepoDigests` in `docker image inspect`
  output. The stable local identifiers observed below are Docker image IDs
  (`sha256:...`), not registry digests. P0/Harbor digest rows still need real
  repo digests before they are treated as portable immutable manifest entries.

## Selected smoke tasks

Current selectors are not all equivalent to a frozen image map. The next manifest
must use task IDs, not only selectors.

| Scaffold | Current selector | Exact task set for next image map | Status |
| --- | --- | --- | --- |
| qwen-code | `QWEN_NATIVE_SUBSET=smoke_n20` | 20 IDs from `/data/nips/aci_evolve/experiments/preregistration/verified_subsets_seed42_v1.json` | Partial worker cache: 10 present, 10 missing |
| mini-swe-agent | `MINI_SWE_SLICE=0:1` over Verified test split | `astropy__astropy-12907` | Worker cache present |
| swe-agent | default smoke regex in `run_swebench_verified.sh` | `astropy__astropy-12907`, `matplotlib__matplotlib-20488`, `sympy__sympy-12096`, `scikit-learn__scikit-learn-10844`, `sphinx-doc__sphinx-10435` | Partial worker cache: only `astropy__astropy-12907` present |
| OpenHands | repo suite currently sets `OPENHANDS_EVAL_LIMIT=1`; shared OpenHands config fixes smoke to `sphinx-doc__sphinx-8595` | Use `sphinx-doc__sphinx-8595` if keeping the shared OpenHands runtime pretag policy | Missing base image, pretag source, and runtime target on worker |

Qwen `smoke_n20` is not the old image-migration `swebench_base_pilot_20.txt`.
The current Qwen runner reads the preregistration JSON above. The older pilot
20 image file is all Astropy images and should not be used as the Qwen
`smoke_n20` map.

## Worker cache: qwen-code smoke_n20

Rootless Docker on worker was inspected with
`DOCKER_HOST=unix:///tmp/rl/run/docker.sock`. Worker summary from the same probe:
`ServerVersion=26.1.3`, `Driver=overlay2`, `Containers=0`, `Images=240`,
`swebench_tags=134`, `swerex_tags=237`, `openhands_runtime_tags=0`.

| # | Instance | Base tag | Worker image ID | SWE-ReX tag status |
| --- | --- | --- | --- | --- |
| 1 | `astropy__astropy-7671` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-7671:latest` | `sha256:8d93e2be662f474b5def839e24a5ccd9de792d2abcd081c9485ef4828b952b6a` | Present: `...-00527122c8e98259`, `...-7a419d4dd4e186bf` |
| 2 | `django__django-11087` | `swebench/sweb.eval.x86_64.django_1776_django-11087:latest` | `sha256:8459f3393b3793ad06d07d4ac91e39078a1601a01b87656a081b35c8c14e6472` | Present: `...-82f4e4757c7e9e78`, `...-2d8db77938b386db` |
| 3 | `django__django-11400` | `swebench/sweb.eval.x86_64.django_1776_django-11400:latest` | `sha256:f26464da652d466358ec8446891916c27c2c868146a61722dbaaa8ec246b1bfc` | Present: `...-f71f519b6415559f`, `...-a8b9c081b53afc79` |
| 4 | `django__django-11603` | `swebench/sweb.eval.x86_64.django_1776_django-11603:latest` | `sha256:c0216a113b4268ba4d898ba769c15ba91b46eec70ea7710fc35f6727c375be0d` | Present: `...-d7479cdf21908f8f`, `...-e60c7e18a4844e5e` |
| 5 | `django__django-11740` | `swebench/sweb.eval.x86_64.django_1776_django-11740:latest` | `sha256:da785bee09263935ecf304712078d539aced71e2a674814e338b6fa8f8b7b52a` | Present: `...-0daf729c7fc69b4f`, `...-a33754cababdb703` |
| 6 | `django__django-11848` | `swebench/sweb.eval.x86_64.django_1776_django-11848:latest` | `sha256:fef266270c4328b924aec6ecbf15db35f68084a099f0f96098020105e18b42c4` | Present: `...-c04e35e4caa9a0fb`, `...-29cdd46be8b8879a` |
| 7 | `django__django-11951` | `swebench/sweb.eval.x86_64.django_1776_django-11951:latest` | `sha256:adabffa8cc1b9515a780f766ea22502436b0ac2212832a05f4dc6bbb37879a21` | Present: `...-2ec6b4d85f6fab60`, `...-fe57480c903b5fd8` |
| 8 | `django__django-11999` | `swebench/sweb.eval.x86_64.django_1776_django-11999:latest` | `sha256:2221b21954bd8d2e9fa3944a3220008e880823c1ec50acd7c9a8f7be7bc58a9a` | Present: `...-c91638743e0d5762`, `...-fc89a4af4a76c164` |
| 9 | `django__django-12155` | `swebench/sweb.eval.x86_64.django_1776_django-12155:latest` | `sha256:400c9de82a91cf14670671ca389b3933299a98d43f7bdacd0ffda81941ea7053` | Present: `...-056444737240e288`, `...-dfb5a91fcf698219` |
| 10 | `django__django-12193` | `swebench/sweb.eval.x86_64.django_1776_django-12193:latest` | `sha256:5a35ccc16f587266d0e213bbb6030888805458eb2e2cd59c5073a41a0e261aec` | Present: `...-376c8cafe30a087d`, `...-735fbc53091af77a` |
| 11 | `matplotlib__matplotlib-21568` | `swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-21568:latest` | Missing | Missing |
| 12 | `matplotlib__matplotlib-24026` | `swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-24026:latest` | Missing | Missing |
| 13 | `pydata__xarray-3151` | `swebench/sweb.eval.x86_64.pydata_1776_xarray-3151:latest` | Missing | Missing |
| 14 | `pytest-dev__pytest-6197` | `swebench/sweb.eval.x86_64.pytest-dev_1776_pytest-6197:latest` | Missing | Missing |
| 15 | `scikit-learn__scikit-learn-12682` | `swebench/sweb.eval.x86_64.scikit-learn_1776_scikit-learn-12682:latest` | Missing | Missing |
| 16 | `sphinx-doc__sphinx-7748` | `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-7748:latest` | Missing | Missing |
| 17 | `sphinx-doc__sphinx-8265` | `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8265:latest` | Missing | Missing |
| 18 | `sympy__sympy-12481` | `swebench/sweb.eval.x86_64.sympy_1776_sympy-12481:latest` | Missing | Missing |
| 19 | `sympy__sympy-13031` | `swebench/sweb.eval.x86_64.sympy_1776_sympy-13031:latest` | Missing | Missing |
| 20 | `sympy__sympy-13647` | `swebench/sweb.eval.x86_64.sympy_1776_sympy-13647:latest` | Missing | Missing |

## Worker cache: mini-swe-agent and swe-agent smoke

`MINI_SWE_SLICE=0:1` resolves to the first row of the local Verified parquet:
`astropy__astropy-12907`.

| Scaffold | Instance | Base tag | Worker image ID | SWE-ReX tag status |
| --- | --- | --- | --- | --- |
| mini-swe-agent | `astropy__astropy-12907` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest` | `sha256:3bfd24c0b7c240615398d43176eee1efad9f5e18bde1f186e2241c119150f785` | Present: `...-896d8eb0c3be14d2`, `...-951a5c9bae620989`, `...-ecc09a6528009288` |
| swe-agent | `astropy__astropy-12907` | `swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest` | `sha256:3bfd24c0b7c240615398d43176eee1efad9f5e18bde1f186e2241c119150f785` | Present: `...-896d8eb0c3be14d2`, `...-951a5c9bae620989`, `...-ecc09a6528009288` |
| swe-agent | `matplotlib__matplotlib-20488` | `swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-20488:latest` | Missing | Missing |
| swe-agent | `sympy__sympy-12096` | `swebench/sweb.eval.x86_64.sympy_1776_sympy-12096:latest` | Missing | Missing |
| swe-agent | `scikit-learn__scikit-learn-10844` | `swebench/sweb.eval.x86_64.scikit-learn_1776_scikit-learn-10844:latest` | Missing | Missing |
| swe-agent | `sphinx-doc__sphinx-10435` | `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-10435:latest` | Missing | Missing |

## Worker cache: OpenHands

The shared OpenHands config identifies the smoke task and runtime pretag policy:

- `OPENHANDS_SELECTED_IDS` for smoke: `sphinx-doc__sphinx-8595`
- pretag source: `openhands_smoke4_recover:sphinx8595`
- pretag target/runtime image:
  `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`

Worker status:

| Required item | Worker status |
| --- | --- |
| `swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8595:latest` | Missing |
| `openhands_smoke4_recover:sphinx8595` | Missing |
| `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98` | Missing |

This is the OpenHands runtime blocker. The OpenHands checkout exists under
`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen/OpenHands-0.54.0`,
and its official `all-swebench-verified-instance-images.txt` contains 500 base
image refs, but no runtime image/tar was found in the bounded shared-path probe.

## Shared tar artifacts

Bounded listing under
`/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`
found one tar:

| Artifact | Size | Mtime | Use |
| --- | ---: | --- | --- |
| `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/qwen-code/runs/manual_transfer_astropy_7671_20260613_220547/astropy_7671.image.tar` | 2719902720 bytes | `2026-06-13 22:08:44 +0800` | Fallback candidate for `astropy__astropy-7671`, which is in current Qwen `smoke_n20` and already cached on worker |

No OpenHands runtime tar/name hit was found under the bounded roots:

- `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified`
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/openhands_qwen`
- `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench`

## Manifest rows needed before required image_preflight

Do not flip any of the four suite rows to required preflight yet. Required mode
would fail today because selected task images are missing and OpenHands runtime
is absent.

Add or regenerate `manifests/images/swebench_verified.yaml` rows in this order:

1. Qwen `smoke_n20` base image rows:
   one required row per exact task above, with `task_id`, `scaffolds:
   [qwen-code]`, `role: swebench_task_image`, exact `local_refs`, worker image
   ID if present, `RepoDigests` if later available, and `fallback_tars` only
   when a tar exists with sha256 recorded.
2. Qwen missing image rows:
   keep rows for the ten missing Qwen tasks, but do not enable required
   preflight until each has either a worker-local tag, a P0 digest that can be
   pulled in a controlled preload lane, or a verified fallback tar. Missing
   tasks are entries 11-20 in the Qwen table.
3. Mini-swe-agent row:
   required base row for `astropy__astropy-12907` plus the observed SWE-ReX
   aliases if mini-swe-agent still relies on SWE-ReX-prebuilt local refs.
4. SWE-agent rows:
   required rows for all five default smoke regex instances. Only
   `astropy__astropy-12907` is ready on worker; the four missing tasks must be
   staged or the smoke regex must be narrowed before required preflight.
5. OpenHands base row:
   required row for `sphinx-doc__sphinx-8595` only if the suite is aligned with
   the shared OpenHands smoke config via `OPENHANDS_SELECTED_IDS`. Current repo
   suite only has `OPENHANDS_EVAL_LIMIT=1`, which is not a frozen selected ID.
6. OpenHands runtime row:
   required row for
   `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`
   with either a P0 digest, a verified tar fallback, or a verified worker-local
   tag/pretag source. Today all three are missing.
7. Optional fallback row:
   add the existing `astropy_7671.image.tar` only after recording its sha256 and
   confirming it loads to the expected image ID in a separate preload lane. This
   report did not hash, load, or mutate Docker data.

Minimum row fields needed for a useful required preflight:

- `id`: stable row ID, for example `swebench_verified_qwen_smoke_n20_001_base`
- `task_id`: exact SWE-bench instance ID
- `scaffolds`: one or more of `qwen-code`, `mini-swe-agent`, `swe-agent`,
  `openhands`
- `role`: `swebench_task_image`, `swerex_prebuilt`, or `openhands_runtime`
- `required: true`
- `local_refs`: exact Docker tags, no globs
- `worker_cache`: worker endpoint, observed image ID, observed at timestamp
- `repo_digests`: P0/registry digest when available; empty local `RepoDigests`
  are not enough
- `fallback_tars`: exact tar path plus sha256 when available
- `needs_network: false` for the actual smoke run

Only after those rows are complete should the four suite rows move from
`image_policy: optional` to required preflight.

## Blockers

1. Qwen `smoke_n20` is only half cached on worker: 10 of 20 selected base images
   present; 10 missing.
2. SWE-agent default smoke is only 1 of 5 cached on worker.
3. OpenHands selected smoke is not frozen in the repo suite row. The shared
   OpenHands config uses `sphinx-doc__sphinx-8595`, but the suite row only sets
   `OPENHANDS_EVAL_LIMIT=1`.
4. OpenHands runtime image
   `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98`
   is missing on worker and no tar/P0 digest was found in the bounded probe.
5. The only tar found is `astropy_7671.image.tar`; it helps one cached Qwen task
   but does not cover the missing Qwen/SWE-agent/OpenHands images.
6. Worker-local image IDs are not portable registry digests. Required preflight
   can check local cache, but a durable multi-worker manifest still needs P0
   digests or verified tar sha256 values.

## Evidence commands

All commands were read-only except creating this report.

| Command | Exit |
| --- | ---: |
| `sed -n '1,380p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md; cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-; pwd` | 0 |
| Local repo reads of `manifests/suite.example.yaml`, `manifests/images/swebench_verified.yaml`, `manifests/bench_registry.yaml`, `manifests/datasets.example.yaml`, `manifests/harnesses.example.yaml`, relevant reports, and image preflight scripts | 0 |
| Worker explicit SSH: `docker image inspect` for `django-13810`, `astropy-12907`, `astropy-7671`, OpenHands runtime; `docker images` counts; `docker info` summary | 0 |
| Dev bounded shared-path scan for key paths, tars, and OpenHands runtime names | 255 |
| Dev exact manifest/runner/OpenHands probe after narrowing the scan | 0 |
| Dev Qwen runner subset probe and SWE-agent runner read | 0 |
| Dev Verified parquet first-row check for mini-swe-agent slice `0:1` | 0 |
| Worker explicit SSH Qwen `smoke_n20` cache probe | 0 |
| Worker explicit SSH SWE-agent smoke cache probe | 0 |

The first dev shared-path scan was stopped after it began traversing historical
run snapshots; the targeted follow-up commands above superseded it and exited 0.
