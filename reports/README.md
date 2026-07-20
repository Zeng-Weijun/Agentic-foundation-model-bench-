# Bench Reports

This directory holds the current working dossier for agentic SWE/tool-use benchmark organization.

## Files

- `agentic_bench_landscape_20260625.md`
  - Main narrative report.
  - Covers task shapes, harnesses, public score anchors, local Qwen/GPT evidence, trace observations, and attribution.

- `agentic_bench_matrix_20260625.csv`
  - Machine-readable benchmark matrix.
  - Use this as the source table if moving the dossier into GitHub, a spreadsheet, or a paper appendix.

- `shared_disk_layout_research_20260625.md`
  - Read-only research on the existing shared-disk benchmark layouts.
  - Distinguishes the older `nips2026/bench` launcher layer from the newer `/mnt/.../swe/bench` benchmark/scaffold layout.

- `rootless_worker_research_20260625.md`
  - Read-only research on the rootless worker testing architecture.
  - Defines controller/worker/runner layers, benchmark-specific container risks, and smoke order.

- `worker_j9jjd_preflight_20260625.md`
  - Live lightweight preflight of the `worker-j9jjd` rootless Docker environment.
  - Confirms cached SWE-bench image container start and bind-mount smoke, and records the current 8.130 relay reachability blocker.

- `deployment_plan_20260625.md`
  - Integrated plan for the GitHub repository, shared-disk project root, rootless worker contract, and milestones.

- `yaml_suite_launcher_plan_20260625.md`
  - Minimal dry-run-first `sh + yaml` suite launcher design, safety guards, legacy adapter execution status, and pending adapter list.

- `tau2_proxy_smoke_20260625.md`
  - First executable worker smoke through the `dev` relay proxy.
  - Confirms tau2 harness completion via YAML suite, records the proxy topology, and distinguishes infra pass from sampled task reward `0.0`.

- `offline_image_loader_20260625.md`
  - Offline/rootless Docker image preload/check helper.
  - Documents `scripts/load_offline_images.sh --check`, expected rootless Docker socket defaults, and fake-Docker verification.

- `offline_image_fix_git_manifest_20260625.md`
  - Exact Terminal-Bench 2.1 `fix-git` image manifest check.
  - Confirms `tb2-offline/fix-git:20260425` is missing from worker rootless Docker while the shared tar resolves.

- `cocoabench_prepare_smoke_20260625.md`
  - Worker-side CoCoA prepare-only smoke.
  - Confirms the correct shared `COCOA_ROOT` and records the Python 3.13 environment blocker for full CoCoA runs.

- `cocoabench_python313_unblock_20260625.md`
  - CoCoA Python 3.13 worker runtime unblock.
  - Records the shared conda env, worker-local uv Python symlink repair, and reusable `scripts/check_cocoabench_env.sh` verification.

- `cocoabench_worker_smoke_20260625.md`
  - CoCoA one-task worker smoke through the YAML suite and `dev` proxy.
  - Confirms suite/runner startup but classifies the current task failure as rootless Docker socket/compose infra, not model quality.

- `terminal_bench_2_1_smoke_plan_20260625.md`
  - Terminal-Bench 2.1 one-task smoke plan and dry-run wrapper.
  - Selects `fix-git`, records image/tb CLI blockers, and gives the exact post-unblock execute command.

- `terminal_bench_2_1_image_load_debug_20260625.md`
  - Terminal-Bench 2.1 `fix-git` image load root-cause analysis.
  - Shows another TB2.1 tar loads, while `fix-git` fails from shared storage and `/tmp` due a layer import path issue.

- `vitabench_repozero_worker_preflight_20260625.md`
  - VitaBench and RepoZero worker preflight.
  - Records a one-task VitaBench smoke through the `dev` proxy and the RepoZero `repoarena-new` Docker image blocker.

- `trace_manifest_template.yaml`
  - Per-task trace collection template.
  - Copy this next to each raw trace/result directory before citing a run.

## Current Local Score Policy

The former local Qwen score publication was removed on 2026-07-21 because it
was not sealed and independently dual-signed under the current evidence contract.
Historical evidence remains preserved beneath explicit status banners, but it is
non-canonical for the current suite. The next active local score must come from the relay-backed `gpt-5.5` +
`medium` configuration and satisfy the full evidence contract.

## GitHub Import Notes

Recommended initial repo layout:

```text
bench-dossier/
  README.md
  reports/
    agentic_bench_landscape_20260625.md
    agentic_bench_matrix_20260625.csv
    shared_disk_layout_research_20260625.md
    rootless_worker_research_20260625.md
    deployment_plan_20260625.md
    trace_manifest_template.yaml
  traces/
    README.md
  sources/
    README.md
```

Before public release, refresh all public leaderboard scores and replace internal-only remote paths with either archived artifacts or clearly marked private evidence pointers.
