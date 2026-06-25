# cmux Agent Loop Driver - 2026-06-25

This is the shared driver doc for the four interactive cmux agents on the right-side panes.

## Global Goal

Make `Agentic-foundation-model-bench-` converge toward one-command, YAML-driven, offline/rootless worker execution for all benchmark families, with model traffic routed through the `dev` proxy now and SGLang later.

## Repo And Runtime

- Local repo: `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`
- GitHub: `https://github.com/Zeng-Weijun/Agentic-foundation-model-bench-.git`
- Current pushed commit before this cmux loop: `ca173cf`
- Shared checkout: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo`
- Worker: `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`
- Worker rootless Docker: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`
- Dev proxy: `http://100.96.1.101:18540/v1`
- Do not use `swe_dev` / `swe-dev`.

## Current Proven State

- tau2 one-task-per-domain worker smoke passed at suite/harness level through `dev_proxy_gpt54mini_8130`; sampled reward was `0.0`.
- VitaBench one-task worker smoke passed at harness level through the `dev` proxy; reward was `0.0` due capped `VITA_MAX_STEPS=20`.
- CoCoA Python 3.13 runtime blocker on worker was fixed by a worker-local symlink to the shared `conda_envs/cocoa` env.
- CoCoA suite entry launches, but task result is `status: error` because sandbox startup hits rootless Docker socket EOF before model calls.
- Terminal-Bench 2.1 wrapper exists. `llm-inference-batching-scheduler` image loaded successfully; `fix-git.tar` fails `docker load` with `unlinkat /app/resources/patch_files: input/output error`.
- RepoZero is blocked by missing `ghcr.io/jessezzzzz/repoarena-new:latest` in worker rootless Docker and no shared tar.

## Shared Rules

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before doing remote work.
- Local Mac is the control plane. Remote work only through SSH.
- No public internet actions on the worker: no image pull, package install, git fetch, or dataset download.
- Use `dev` for staging and inspection when internet or light tooling is needed.
- Do not edit files outside your assigned write scope.
- Do not revert other changes.
- Do not launch full benchmarks. Only targeted smokes/checks listed in your lane.
- Write concrete evidence: command, exit code, artifact path, and infra/model/task classification.

## Lane Assignments

| Surface | Lane | Write Scope |
|---|---|---|
| `surface:50` | Rootless Docker daemon/socket health | `reports/rootless_docker_health_20260625.md`, optional `scripts/check_rootless_docker_worker.sh` |
| `surface:54` | VitaBench one-task YAML suite entry | `manifests/suite.example.yaml`, optional `scripts/test_agentic_bench_suite.py`, `reports/vitabench_suite_entry_20260625.md` |
| `surface:51` | Terminal-Bench 2.1 `fix-git` image rebuild/resave path | `reports/terminal_bench_fix_git_rebuild_plan_20260625.md`, optional `scripts/rebuild_tb21_fix_git_image.sh` |
| `surface:55` | RepoZero image staging/manifest | `reports/repozero_image_staging_20260625.md`, optional `manifests/offline_images.repozero.yaml`, optional `scripts/stage_repozero_image.sh` |

## Acceptance For This Loop

- Each lane returns a report or patch in its assigned files only.
- Main orchestrator verifies with local tests/YAML parse/shell syntax and relevant remote dry-run checks.
- Main orchestrator commits and pushes only after verification.

## Loop Result Snapshot

Collected by the main orchestrator after all four cmux lanes completed.

- `surface:50` rootless Docker: added `reports/rootless_docker_health_20260625.md` and `scripts/check_rootless_docker_worker.sh`. The worker daemon was safely restarted with existing `/tmp/rl/data` preserved. `docker info`, image listing, `docker ps`, `docker compose ps`, and a cached-image `docker run --rm --network none ... echo` work. `docker version`, raw `/v1.45/version`, and Python Docker SDK negotiation still fail because dockerd panics in `fillRootlessVersion`.
- `surface:54` VitaBench: added `vitabench_delivery_one_task_smoke` to `manifests/suite.example.yaml`, added a focused unit test in `scripts/test_agentic_bench_suite.py`, and wrote `reports/vitabench_suite_entry_20260625.md`. The old `vitabench_full` entry remains separate and still points at `run_vitabench_full.sh`.
- `surface:51` Terminal-Bench 2.1: added `reports/terminal_bench_fix_git_rebuild_plan_20260625.md` and `scripts/rebuild_tb21_fix_git_image.sh`. The script is dry-run-first and targets a rebuilt `fix-git.tar` under the shared prebuilt-image tree without modifying the original `20260425/fix-git.tar`.
- `surface:55` RepoZero: added `reports/repozero_image_staging_20260625.md`, `manifests/offline_images.repozero.yaml`, and `scripts/stage_repozero_image.sh`. `dev` has Docker and can reach GHCR, but the current credentials are denied for `ghcr.io/jessezzzzz/repoarena-new:latest`; no tar was staged and no RepoZero benchmark was run.

Main-thread verification run after integration:

```text
python3 -m py_compile scripts/agentic_bench_suite.py scripts/test_agentic_bench_suite.py scripts/check_offline_images_manifest.py scripts/test_offline_images_manifest.py scripts/openai_relay_proxy.py -> 0
python3 -m unittest scripts.test_agentic_bench_suite scripts.test_offline_images_manifest -> 0, 8 tests
bash -n scripts/*.sh -> 0
scripts/rebuild_tb21_fix_git_image.sh --dry-run -> 0
scripts/stage_repozero_image.sh -> 0
ssh dev 'bash -s -- --dry-run' < scripts/rebuild_tb21_fix_git_image.sh -> 0
ssh dev 'bash -s --' < scripts/stage_repozero_image.sh -> 0
ruby YAML.load_file for suite/offline manifests -> 0
scripts/check_rootless_docker_worker.sh -> 1, expected because /version and Docker SDK remain unhealthy
git diff --check -> 0
```
