# Pending Benches Worker-Offline Inventory Round34

Lane: pending benches bug-hunt/inventory agent
Date: 2026-06-26
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Expected head: `008d466`
Writable scope used: this report only

## Result

FAIL for worker-offline one-click readiness.

Static readiness reports all five requested targets blocked. Four targets, `MCP-Atlas`, `Tool-Decathlon`, `programbench`, and `NL2Repo`, are disabled `pending_adapter` placeholders with no concrete checkout, runner, image transport, or parser contract. `DeepSWE` is enabled and wired as legacy, but its image manifest is still a placeholder, the concrete task set enumerates 113 public ECR images with no local/P0/fallback tar coverage in the inspected evidence, and suite result parsing still falls through to `no_parser` for non-RepoZero adapters.

No public download, Docker pull/build/run/save/load, model call, or benchmark execute was run.

## Command Log

| command | rc | evidence |
|---|---:|---|
| `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Workflow read first before remote work. |
| `ssh dev "cd <worktree> && hostname && pwd && git branch --show-current && git rev-parse --short HEAD && git log -1 --oneline && git status --short"` | 0 | Host `zwj2`; branch `feat/image-warmup-policy`; head `008d466`; log `008d466 Align active bench taxonomy`. |
| `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --target-benches MCP-Atlas,Tool-Decathlon,programbench,NL2Repo,DeepSWE --json` | 1 | `counts={blocked: 5, missing: 0, ready: 0, total: 5}`. Blockers: four pending benches have `no_enabled_suite_entry,suite_entry_disabled,adapter_not_wired,image_manifest_not_materialized`; DeepSWE has `image_manifest_not_materialized`. |
| `for b in mcp_atlas tool_decathlon programbench nl2repo deepswe; do python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only "$b"; done` | 0 per bench | `mcp_atlas/tool_decathlon/programbench/nl2repo` each returned `run_count=0`; `deepswe` returned `run_count=1`. |
| `test -e` / `stat` for five adapter runner paths and DeepSWE paths | 0 | `run_mcp_atlas.sh`, `run_tool_decathlon.sh`, `run_programbench.sh`, `run_nl2repo.sh` missing under `/data/nips/bench`; DeepSWE legacy runner, shared runner, source dir, and agent wrapper exist. |
| bounded `find` for MCP/Atlas/Decathlon/ProgramBench/NL2Repo under shared roots | 0 | No exact requested benchmark checkout found. Only `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas` matched atlas terms, and its README identifies SWE Atlas, not MCP-Atlas. |
| `docker image ls --format ... | grep -Ei "mcp|atlas|decathlon|programbench|nl2repo|deepswe|r2e|pier|swe-bench-202605"` on dev | 0 wrapper, grep rc 1 | No matching local dev Docker images surfaced by the read-only filter. |
| DeepSWE task grep under `/data/nips/bench/deep-swe/tasks` | 0 | `task_toml_count=113`, `docker_image_count=113`, `unique_image_count=113`, `allow_internet_values=false`; sampled refs are `public.ecr.aws/d3j8x8q7/swe-bench-202605:<tag>`. |
| cache inventory grep for requested terms | 0 | `reports/swe_dev_docker_cache_inventory_20260626.json` had 0 matches for requested pending/DeepSWE/R2E/Pier terms; worker-j9jjd cache inventory file was absent at the checked coordination path. |

## Inventory Table

| bench | source / dataset path | runner / adapter path | needs Docker? | image manifest present? | fallback tar / digest present? | worker smoke possible? | result parser / artifact contract | exact next action |
|---|---|---|---|---|---|---|---|---|
| MCP-Atlas | No exact MCP-Atlas checkout or dataset located. Existing `reports/pending_adapter_inventory_20260625.md:33` records no exact checkout; bounded search this round found only unrelated `swe-atlas`, whose README is for SWE Atlas. | Suite placeholder at `manifests/suite.example.yaml:286-294` points to `run_mcp_atlas.sh`; `/data/nips/bench/run_mcp_atlas.sh` is missing. Adapter status is `pending_adapter`. | Expected yes, because the prior inventory calls out MCP server containers/service state and tool exposure, but no contract exists. | Only placeholder rows in `manifests/images/pending_benches.yaml:10-16`; readiness JSON `readiness_20260626.json:240-291` marks the target blocked. | None found in manifests, reports, or filtered dev image cache. | No. The suite row is disabled and `--only mcp_atlas --dry-run --json` returns `run_count=0`. | None. Suite parser only handles RepoZero; no MCP-Atlas artifact contract exists. | Stage upstream checkout and dataset on dev; define MCP server reset, exposed-tool manifest, judge/eval artifacts, and rootless image preload rows; add runner/parser; enable only a one-task smoke after dry-run and image preflight are concrete. |
| Tool-Decathlon | No exact Tool-Decathlon or Toolathlon checkout/data located. Existing inventory `reports/pending_adapter_inventory_20260625.md:34` records no checkout, runner, task split, tool server lifecycle, grader, or image/cache plan. | Suite placeholder at `manifests/suite.example.yaml:296-304` points to `run_tool_decathlon.sh`; `/data/nips/bench/run_tool_decathlon.sh` is missing. Adapter status is `pending_adapter`. | Likely yes for tool-server/container assets, but upstream contract is not staged. | Only placeholder rows in `manifests/images/pending_benches.yaml:17-23`; readiness JSON `readiness_20260626.json:293-340` marks the target blocked. | None found. | No. Disabled row; dry-run `--only tool_decathlon` returns `run_count=0`. | None. No result parser or artifact schema exists. | Stage upstream checkout/data; freeze one smoke task, tool server lifecycle/reset, grader output, and image/cache manifest; implement a worker-safe runner and parser before enabling. |
| ProgramBench | No ProgramBench checkout, tasks, hidden-test/grader fixtures, compiled-program archive, or runtime image plan located. Existing inventory `reports/pending_adapter_inventory_20260625.md:36` records this gap. | Suite placeholder at `manifests/suite.example.yaml:342-350` points to `run_programbench.sh`; `/data/nips/bench/run_programbench.sh` is missing. Adapter status is `pending_adapter`. | Unknown until upstream is staged; likely sandbox/runtime or language dependency images. | Only placeholder rows in `manifests/images/pending_benches.yaml:24-30`; readiness JSON `readiness_20260626.json:424-474` marks the target blocked. | None found. | No. Disabled row; dry-run `--only programbench` returns `run_count=0`. | None. No result parser or artifact schema exists. | Stage upstream source/data; identify hidden-test and runtime contract; create dataset manifest plus rootless image/cache preload plan; implement runner/parser; enable only after one offline smoke task is reproducible. |
| NL2Repo | No NL2Repo checkout, task split, pytest/grader contract, or offline dependency cache located. Existing inventory `reports/pending_adapter_inventory_20260625.md:37` records this gap. | Suite placeholder at `manifests/suite.example.yaml:352-360` points to `run_nl2repo.sh`; `/data/nips/bench/run_nl2repo.sh` is missing. Adapter status is `pending_adapter`. | Unknown until upstream is staged; likely Python repo-generation sandbox plus package cache. | Only placeholder rows in `manifests/images/pending_benches.yaml:31-36`; readiness JSON `readiness_20260626.json:518-569` marks the target blocked. | None found. | No. Disabled row; dry-run `--only nl2repo` returns `run_count=0`. | None. No result parser or artifact schema exists. | Stage upstream checkout/data; freeze one pytest/grader smoke and dependency cache contract; add image/cache manifest, runner, and parser before enabling. |
| DeepSWE | Legacy dataset path exists at `/data/nips/bench/deep-swe/tasks` and shared equivalent `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe/tasks`. This round counted 113 `task.toml` files with 113 unique `public.ecr.aws/d3j8x8q7/swe-bench-202605:<tag>` image refs and `allow_internet=false`. Projectized/source evidence exists under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe`. | Suite row `manifests/suite.example.yaml:245-258` is enabled, `wired_legacy`, and points to `run_deepswe.sh`. `/data/nips/bench/run_deepswe.sh`, shared runner `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh`, and `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/deepswe/deepswe-agent/run.sh` exist. | Yes. Legacy runner uses Pier with `DEEPSWE_ENVIRONMENT=docker` and `host.docker.internal`; shared runner documents R2E-Gym/SWE-Bench Docker gyms with local Docker backend. | Placeholder only. `manifests/images/deepswe.yaml:1-19` says `status: missing_r2e_image_manifest`, lists exact blockers, and contains only `deepswe_r2e_images_todo`; readiness JSON `readiness_20260626.json:571-617` marks the target blocked. | None proven. Round27 evidence says bounded image scan found 0 DeepSWE `.tar` and `.sha256`; this round found 0 matching dev Docker cache refs for DeepSWE/R2E/Pier/public ECR image tags. | Dry-run only. `--only deepswe --dry-run --json` returns one planned run, but worker offline execute is not safe until images, Pier/runtime wheels, rootless Docker, and model relay are proven. | Partial native artifacts only. Legacy runner writes secret-bearing `pier.env`, then expects Pier `result.json` and writes `artifact_manifest.json`; shared runner writes `summary.tsv`. Suite parser code `scripts/agentic_bench_suite.py:1553-1611` parses only RepoZero and otherwise returns `parser_status=no_parser`. | Generate `manifests/images/deepswe.yaml` from the 113 task TOMLs; stage P0/fallback tar+sha256 coverage; pre-stage Pier/runtime wheels or choose the shared R2E runner; prove rootless container-to-relay networking; make image policy required or disable execution until materialized; add a DeepSWE parser that consumes safe artifact metadata and never copies `pier.env`. |

## Reusable Assets

- DeepSWE has the only directly reusable bench assets among the five: legacy task tree `/data/nips/bench/deep-swe/tasks`, legacy runner `/data/nips/bench/run_deepswe.sh`, shared R2E runner, and projectized wrapper/source tree.
- `swe-atlas` exists under `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas`, but this is SWE Atlas, not MCP-Atlas. Treat it only as possible Harbor pattern/reference material, not as a staged MCP-Atlas asset.
- The four pending placeholders all share `manifests/images/pending_benches.yaml`, but that file is explicitly a gap inventory, not an offline image manifest.

## ISSUE-READY

### ISSUE-READY: Explicit `--only` on disabled pending benches returns an empty successful dry-run plan

- file:line: `scripts/agentic_bench_suite.py:1732-1752`; `manifests/suite.example.yaml:286-304` and `342-360`.
- static repro: from the worktree, run `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only mcp_atlas`, and repeat for `tool_decathlon`, `programbench`, and `nl2repo`. Each command exits 0 and emits `runs: []`. The only empty-plan hard failure is scoped to `--image-preflight-only` at `scripts/agentic_bench_suite.py:1732-1734`; regular dry-run returns 0 at `scripts/agentic_bench_suite.py:1750-1752`.
- impact: a user can explicitly ask the one-click suite for a named pending benchmark and receive a successful empty plan instead of a clear blocked/not-ready error. This hides missing checkout, runner, image, and parser assets.
- fix: when `--only` is supplied and the selected plan is empty, fail nonzero unless `--allow-empty-plan` is set; include selected IDs and readiness blockers in the error. Keep current behavior only for intentionally broad/default dry-runs.
- dedup: overlaps with the known pending-adapter inventory, but this is a runner UX/gating bug, not just an asset gap.

### ISSUE-READY: DeepSWE is enabled/wired while worker-offline image/runtime gates are still placeholders

- file:line: `manifests/suite.example.yaml:245-258`; `manifests/images/deepswe.yaml:1-19`; `/data/nips/bench/run_deepswe.sh:37-47`, `58-62`, `147-173`; `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh:1-15`, `45-59`.
- static repro: readiness command exits 1 with DeepSWE blocker `image_manifest_not_materialized`; dry-run `--only deepswe` exits 0 with one planned run. Task inventory under `/data/nips/bench/deep-swe/tasks` finds 113 unique public ECR image refs, but `manifests/images/deepswe.yaml` has only a non-required placeholder and local cache probes show no matching DeepSWE/R2E/Pier refs.
- impact: DeepSWE can enter the one-click execute path despite lacking mandatory offline image coverage, rootless container networking proof, and pre-staged Pier/runtime dependencies. The legacy runner can attempt `uv pip install datacurve-pier` and `git clone https://github.com/datacurve-ai/deep-swe` if prerequisites are missing, which violates worker-offline expectations.
- fix: do one of these before execution: disable DeepSWE or make its image policy required until a generated 113-row image manifest has P0 or fallback tar+sha256 coverage. Also pre-stage Pier/runtime wheels or select the shared R2E runner, remove public-install/clone fallbacks from the worker path, and record rootless relay proof.
- dedup: overlaps with Round27 `DEEPSWE-R2E-01`; current issue is the active suite gating failure around an enabled row with unresolved offline runtime requirements.

### ISSUE-READY: DeepSWE and other non-RepoZero adapters lack a suite result parser contract

- file:line: `scripts/agentic_bench_suite.py:1553-1611`; `/data/nips/bench/run_deepswe.sh:247-289`; `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_deepswe.sh:63-90`.
- static repro: `_benchmark_result_for_run` has a RepoZero-specific parser only. For any successful non-RepoZero adapter, including DeepSWE, it returns `parser_status: no_parser`, `status: unknown`, `metric: none`, and `failure_category: native_artifact_missing`. DeepSWE runners can produce native artifacts (`result.json`/`artifact_manifest.json` or `summary.tsv`), but the suite never consumes them.
- impact: even after images/runtime are staged, a DeepSWE one-click run cannot produce a normalized score or reliable pass/fail result. A nonzero adapter exit also skips native side-artifact parsing, which makes infra/model/agent failure classification weak.
- fix: add a DeepSWE parser that consumes safe artifact pointers from `BENCH_RUN_DIR`, prefers `artifact_manifest.json` plus Pier `result.json` or shared `summary.tsv`, emits normalized score fields, and redacts/excludes `pier.env`. Parse available side artifacts even when adapter exit is nonzero.
- dedup: partially overlaps earlier result-artifact and secret-sidecar notes around issue #1/#10; this report keeps it scoped to DeepSWE readiness and parser materialization.

## Worker-Safe Smoke Boundary

- For the four pending placeholders: no worker smoke should run yet. The first allowed check after staging is a local dry-run that returns exactly one smoke run and a materialized image/cache manifest. Do not execute on worker until the runner, dataset, image rows, and parser exist.
- For DeepSWE: the only safe current action is static/dry-run. First worker smoke should be no more than one task, `MAX_CONCURRENCY=1`, after `docker image inspect` proves every selected task image is present in the rootless worker store and the container can reach the configured relay without public egress. Do not copy `pier.env` into normalized artifacts.

## Final State

- Ready now: 0/5.
- Reusable now: DeepSWE task/runner/source assets only; not enough for offline execute.
- Main blocking class: missing materialized manifests and runner/parser contracts, not model capacity.
