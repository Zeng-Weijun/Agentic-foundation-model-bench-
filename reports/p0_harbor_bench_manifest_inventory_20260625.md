# P0 Harbor/OCI Bench Image Manifest Inventory

Date: 2026-06-25

Scope: surface:51 bench image manifest inventory lane. This is a read-only
inventory from local repo reports/manifests plus bounded shared-path checks via
`ssh dev`. No internet research, benchmark run, image pull, Docker build,
commit, or push was performed. No `swe-dev`/`swe_dev` host was used.

## Executive State

Only RepoZero currently has a complete P0 offline OCI image contract in this
repo: registry digest recorded, shared tar present, checksum present, metadata
present, and worker image verified present in prior reports.

SWE-bench Verified multi-scaffold and Terminal-Bench 2.1 are partial: both need
Docker, both have useful existing cache/assets, but neither has a complete
per-task image manifest with digest/tar coverage that is safe to treat as
offline-ready.

MCP-Atlas, Tool-Decathlon, tau3-bench, ProgramBench, and NL2Repo remain P0
manifest gaps: no usable checkout/dataset/image contract is present in the repo
state inspected here. tau3-bench has a Harbor adapter source, but its generated
dataset and sidecar image manifest are missing.

VitaBench is currently docker-free for the inspected smoke path.
CoCoBench/CoCoA is docker-blocked: the Python/runtime path is unblocked, but
task sandbox startup hits the worker rootless Docker `/version` failure before
model calls.

## Inventory Table

| Bench | Needs Docker? | Registry Digest Available? | Fallback Tar / OCI Archive | Dataset / Task Path | Next Image Action |
|---|---|---|---|---|---|
| SWE-bench Verified multi: qwen-code, mini-swe-agent, swe-agent, OpenHands | Yes. SWE task containers are required; OpenHands additionally needs runtime images. | No complete P0 registry digest manifest in repo. Existing evidence is worker cached tags: 134 `swebench/*`, 237 `swerex-prebuilt:*`; exact digest/task map is not frozen. | Partial only. One historical tar exists at `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/qwen-code/runs/manual_transfer_astropy_7671_20260613_220547/astropy_7671.image.tar`; bounded image migration check found scripts only, no complete tar set. | Dataset manifest points to `/data/swe/datasets/SWE-bench_Verified/data/test-00000-of-00001.parquet`; canonical shared path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/swe_dev/datasets/SWE-bench_Verified/data/test-00000-of-00001.parquet`. Scaffold roots exist under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/{qwen-code,mini-swe-agent,swe-agent,openhands}`. | Freeze the selected task set per scaffold, enumerate required image refs/digests, compare against worker rootless cache, then write a run-specific offline image manifest with one row per required image. Stage missing tars with sha256 under shared image roots. OpenHands must also stage `ghcr.io/all-hands-ai/runtime:oh_v0.54.0_twmj64zvbfnlyth0_se606gwapm7q4m98` or an exact approved replacement. |
| Terminal-Bench 2.1 | Yes. Per-task `tb2-offline/<task>:20260425` images are required. | No registry digest. The available source is a local Docker/OCI archive manifest, not a registry digest manifest. | Partial. `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/manifest.jsonl` has 86 rows; bounded live check found 50 `.tar` files. `fix-git.tar` exists with sha256 `6e77528d2b758fbb4d6ac1b8ca7528aa0ef79c0626640c8be085ff4a1a8a2511` but fails rootless `docker load` with `unlinkat /app/resources/patch_files: input/output error`. The attempted rebuild output dir `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild` exists but contains no files because `dev` Docker/BuildKit failed. | Source tasks: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks` with 89 task dirs. YAML dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml` with 89 `task.yaml` files. | Recover or replace the `dev` build host before rerunning `scripts/rebuild_tb21_fix_git_image.sh --execute`; rebuild/resave `fix-git` into a flattened archive; then write a full TB2.1 image manifest containing task id, tag, tar path, tar sha256, load status, and known-bad exclusions. Do not run TB2.1 until worker TB CLI Python 3.13 and image load coverage are both fixed. |
| MCP-Atlas | Expected yes. Existing repo evidence says real MCP servers/container service state are required, but no local runnable contract exists. | No. No registry/Harbor digest found. | None found. | Not located. Explicit misses in prior inventory included `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/MCP-Atlas`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/mcp-atlas`, and `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/mcp_atlas`. Current bounded name search found only unrelated MCP material under Terminal-Bench. | Stage checkout/dataset on `dev`, define MCP server reset and exposed-tool manifests, enumerate every server image ref/digest, save/load tars or approved internal registry refs, then add a disabled one-task smoke row. |
| Tool-Decathlon / Toolathlon | Expected yes or at least image/cache-backed tool servers; current repo state has no runnable assets to prove otherwise. | No. | None found. | Not located. No exact Tool-Decathlon/Toolathlon checkout or dataset path was found in local reports or bounded shared searches. | Stage upstream checkout/data on `dev`; freeze one task split; identify tool-server lifecycle and OCI image list; create image manifest before any suite enablement. |
| tau3-bench | Yes. Harbor adapter evidence describes Dockerized runtime plus `tau3-runtime` MCP sidecar. | No. | None found. | Adapter source exists: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench`. Expected generated dataset is missing: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench`. The tau3 adapter currently depends on the upstream source checkout at `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench`; treat that as a tau3 source dependency, not a separate tau2 bench target. | Generate/freeze the Harbor dataset on `dev`; add a shared `run_tau3_bench.sh`; enumerate and stage `tau3-runtime`/sidecar images with digest/tar metadata; add DB/server reset snapshot before a no-model runtime smoke. |
| ProgramBench | Unknown from staged assets; treat as needing a P0 runtime/fixture manifest before execution. | No. | None found. | Not located. No ProgramBench checkout, tasks, hidden-test/grader fixtures, compiled-program archive, or runtime image plan was found. | Stage upstream checkout/data; identify whether tasks need containerized execution or only package/wheel caches; then write either an OCI image manifest or an explicit docker-free asset manifest. Keep suite row disabled. |
| RepoZero / RepoArena Py2JS | Yes. Runtime image `ghcr.io/jessezzzzz/repoarena-new:latest` is required. | Yes. Source digest is recorded as `ghcr.io/jessezzzzz/repoarena-new@sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3`; image id `sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c`. | Yes. Shared tar and metadata exist under `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/`: `repoarena-new_latest.tar` (`1242024448` bytes), `.tar.sha256`, `.docker-inspect.json`, `.manifest.json`. Prior worker verification reports tar sha256 OK and worker image present. | RepoZero checkout: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero`. Py2JS dataset: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/dataset`; `data_repozero.zip` also exists in `Py2JS`. Shared wrapper: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/repozero/py2js/run.sh`. | No image staging action remains for the current Py2JS smoke image. Keep the manifest pinned, run the rootless health guard before any smoke, and ensure harness outputs are back-linked into `BENCH_RUN_DIR`. If expanding beyond this image, require the same digest/tar/check/load contract. |
| NL2Repo | Unknown until upstream assets are staged; likely Python repo-generation sandbox plus dependency cache, and possibly Docker. | No. | None found. | Not located. No NL2Repo checkout, task split, pytest/grader contract, or offline dependency cache was found. | Stage checkout/data on `dev`, freeze one pytest task, enumerate dependency cache and runtime isolation requirements, then decide whether the P0 manifest is OCI-image based or docker-free wheel/cache based. Keep disabled. |
| DeepSWE | Yes. Existing evidence says DeepSWE uses Pier/Docker or R2E-Gym-style Docker backend. | No complete registry/image digest manifest found. | None found for DeepSWE/R2E. Worker has generic SWE/SWErex images, but no proven DeepSWE/R2E tags and no DeepSWE-specific tar source. | Legacy path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe`; task path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe/tasks` with prior inventory reporting 113 `task.toml` files. Projectized source: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe/deepswe-agent`; shared runner: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh`. | Enumerate exact R2E-Gym/SWE-Bench images from DeepSWE/R2E metadata; compare to worker cache; stage missing tars with sha256; prove rootless container networking/model relay, especially any `host.docker.internal` assumption, before model smoke. |
| VitaBench | Current one-task smoke path appears docker-free. Source grep in prior report found no Docker, package install, git clone, or dataset download path under `src/vita`. | N/A. | N/A. | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench`; delivery task JSON includes pinned task `10711001`. | No OCI action for current one-task smoke. Add Python env/data manifest and keep the one-task suite row separate from full multi-domain execution. |
| CoCoBench / CoCoA | Docker-blocked. It uses sandbox/container startup through docker-compose. | No image digest manifest found. | None found. | CoCoA root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent`. Current smoke task: `cocoabench-example-tasks`, `linear-regime-estimation`. | First fix rootless Docker `/version` / Python Docker SDK negotiation or make CoCoA bypass that version probe. Then enumerate sandbox/compose images and create image rows if task containers are not fully build-free/cache-free. |

## P0 Gaps By Priority

1. **RepoZero is image-ready.** It has digest, tar, sha256, inspect metadata,
   registry manifest metadata, and worker image-present evidence.
2. **Terminal-Bench 2.1 has shared tars but not a clean P0 manifest.** The
   `fix-git` tar is known-bad under worker rootless Docker; the rebuild attempt
   produced no tar because `dev` Docker/BuildKit failed. The next image action
   is build-host recovery plus `fix-git` rebuild/resave.
3. **SWE-bench Verified multi has worker cache but no exact manifest.** Existing
   tags are useful but not sufficient. The next action is task-to-image
   enumeration across qwen-code, mini-swe-agent, swe-agent, and OpenHands.
4. **DeepSWE needs R2E image enumeration.** It should not run on generic
   SWE/SWErex cache assumptions.
5. **MCP-Atlas, Tool-Decathlon, ProgramBench, and NL2Repo have no staged
   dataset/image contract.** These should stay disabled until the checkout,
   task split, runner, and OCI/cache contract are concrete.
6. **tau3-bench is closer than the other disabled Harbor rows but still
   blocked.** The adapter exists; the generated dataset and sidecar image
   manifest do not.
7. **VitaBench is docker-free for the current smoke; CoCoA is docker-blocked.**
   Do not spend OCI work on VitaBench unless the adapter changes. Spend CoCoA
   effort on the rootless Docker `/version` boundary first.

## Evidence Sources

Local files read:

```text
reports/all_bench_offline_gap_matrix_20260625.md
reports/offline_docker_asset_plan_20260625.md
reports/pending_adapter_inventory_20260625.md
reports/repozero_image_staging_20260625.md
reports/repozero_worker_load_verification_20260625.md
reports/rootless_repozero_load_postmortem_20260625.md
reports/terminal_bench_2_1_image_load_debug_20260625.md
reports/terminal_bench_fix_git_rebuild_execution_20260625.md
reports/vitabench_suite_entry_20260625.md
reports/vitabench_repozero_worker_preflight_20260625.md
reports/cocoabench_worker_smoke_20260625.md
manifests/suite.example.yaml
manifests/datasets.example.yaml
manifests/harnesses.example.yaml
manifests/offline_images.example.yaml
manifests/offline_images.tb21_fix_git.yaml
manifests/offline_images.repozero.yaml
```

Bounded shared-path checks run from `dev`:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425 exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260625-fix-git-rebuild exists, no files
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/repozero/py2js exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench missing
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench exists as tau3 upstream source checkout
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench exists
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/cocoabench/source/cocoa-agent exists
```

Additional live observations:

```text
Terminal-Bench 2.1 prebuilt manifest lines: 86
Terminal-Bench 2.1 tar count in 20260425 dir: 50
RepoZero tar size: 1242024448 bytes
RepoZero image digest: ghcr.io/jessezzzzz/repoarena-new@sha256:b3ced2dcf006c8af8b733b74326f55c76d7c251210d2bbb903bb3dc550372cb3
RepoZero image id: sha256:e01d5505ea767f8583e3ac23cb53c8f2331a35a647d880f52e71f1c860c5f00c
```

## Commands Run In This Lane

```bash
sed -n '1,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_surface51_manifest_inventory_read.txt && cd /Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench- && pwd
find reports manifests -maxdepth 2 -type f | sort
rg -n -i '<bench/image terms>' reports manifests
git status --short -- reports/p0_harbor_bench_manifest_inventory_20260625.md manifests scripts reports
sed -n '1,260p' reports/all_bench_offline_gap_matrix_20260625.md
sed -n '1,260p' reports/offline_docker_asset_plan_20260625.md
sed -n '1,260p' manifests/offline_images.example.yaml
sed -n '1,220p' manifests/offline_images.tb21_fix_git.yaml
sed -n '1,220p' manifests/offline_images.repozero.yaml
sed -n '1,260p' reports/repozero_image_staging_20260625.md
sed -n '1,260p' reports/repozero_worker_load_verification_20260625.md
sed -n '1,260p' reports/rootless_repozero_load_postmortem_20260625.md
sed -n '1,260p' reports/terminal_bench_fix_git_rebuild_execution_20260625.md
sed -n '1,260p' manifests/suite.example.yaml
sed -n '260,430p' manifests/suite.example.yaml
sed -n '1,220p' manifests/datasets.example.yaml
sed -n '1,220p' manifests/harnesses.example.yaml
sed -n '1,240p' reports/pending_adapter_inventory_20260625.md
sed -n '1,220p' reports/shared_disk_layout_research_20260625.md
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<bounded path existence, TB count, RepoZero files, name-match find>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<RepoZero metadata and SWE image_migration bounded files>'
ssh -o BatchMode=yes -o ConnectTimeout=20 dev '<RepoZero Py2JS dataset listing>'
sed -n '1,240p' sed -n '1,280p' reports/vitabench_suite_entry_20260625.md
sed -n '1,220p' reports/vitabench_repozero_worker_preflight_20260625.md
sed -n '1,340p' reports/cocoabench_worker_smoke_20260625.md
```
