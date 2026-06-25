# SWE-bench Verified and TerminalBench2.1 Image Inventory - 2026-06-26

## Scope

This checks the user's warning that shared-path bench folders may not be complete and that `swe_dev:/data` or local Docker cache may hold the actual end-to-end images.

Hosts checked:

- `swe_dev` hostname: `zwj`
- `worker-j9jjd` hostname: `zwj2-64rlk-3469265-worker-0`, Docker socket `unix:///tmp/rl/run/docker.sock`

## swe_dev Local State

Filesystem hits under `/data`:

```text
/data/swe/SWE-bench
/data/conda_envs/swebench
/data/tmp/swe-agent-runtime-swebench
/data/tmp/tb2-prebuild-save
```

Sizes observed:

```text
/data/swe/SWE-bench: 0
/data/conda_envs/swebench: 774M
/data/tmp/swe-agent-runtime-swebench: 304M
```

Docker image cache counts on `swe_dev`:

```text
swebench-related: 1229
swerex-prebuilt: 728
tb2-offline/TB2.1: 89
repozero/repoarena: 1
tau3: 0
```

Example SWE-bench refs include `swebench/sweb.eval.x86_64.sympy_1776_sympy-24539:latest` and matching `swerex-prebuilt:*` tags. Example TerminalBench2.1 refs include `tb2-offline/headless-terminal:20260425` and other `tb2-offline/<task>:20260425` images.

## worker-j9jjd Current Cache

Docker image cache counts on worker:

```text
swebench-related: 371
swerex-prebuilt: 237
tb2-offline/TB2.1: 5
repozero/repoarena: 1
tau3: 0
```

This is not a complete mirror of `swe_dev`. Worker has enough for selected smokes but not for full SWE-bench Verified or TerminalBench2.1 without additional image staging.

## Shared Path State

SWE-bench Verified shared tree exists at:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified
```

It contains qwen-code, mini-swe-agent, swe-agent, openhands, swe-agent-runtime, harness, and image migration manifests. The image migration manifest directory has 24 files, but this is not equivalent to a complete worker Docker cache.

TerminalBench2.1 shared tree exists at:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1
```

Observed shared prebuilt image artifacts:

```text
prebuilt-images/20260425/*.tar or *.tar.gz: 51
prebuilt-images/20260425/manifest.jsonl lines: 86
```

This confirms the shared tar set is partial relative to the 89 local `tb2-offline:*:20260425` images present in `swe_dev` Docker cache, and much larger than the 5 currently loaded on worker.

## Machine-Readable Cache Inventory

A `swe_dev` Docker-cache inventory was generated with the tracked image tool and stored at:

```text
reports/swe_dev_docker_cache_inventory_20260626.json
```

The inventory is filtered to the prefixes `tb2-offline/`, `swebench/`, `swerex-prebuilt`, and `ghcr.io/all-hands-ai/runtime`. Counts in that JSON are:

```text
total: 1317
tb2-offline: 89
swebench: 500
swerex-prebuilt: 728
```

Use this JSON as the input list for P0 registry promotion or verified shared-tar export. It records Docker refs and image IDs only; digest-pinned P0 refs still need to be produced by a promotion step before worker full runs are considered reproducible.

## TB2.1 Verified Image-Smoke Candidate

`gcode-to-text` is now the first required Terminal-Bench 2.1 image-smoke candidate in `manifests/images/terminal_bench_2_1.yaml`:

```text
local ref: tb2-offline/gcode-to-text:20260425
P0 ref: 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-gcode-to-text@sha256:4453cf8e9ff6a4f0295bc3289e49fe2f048438fb03b653972350792671ff3251
fallback tar sha256: d1a85ebdf789dfb2f3b07e321b5824999d1484b3ace4a87880685fd66b3b9231
```

Worker rootless direct manifest check with `--load-fallback --run-smoke` returned `missing=0`, `present=1`, `tar_verified=1`, `smoke_passed=1`, and `errors=0`. The old `fix-git` row is optional known-bad evidence and is not loaded by this smoke path.

## Operational Implication

For one-command worker execution:

- Treat `swe_dev` Docker cache as the current source of truth for SWE-bench and TerminalBench2.1 image reconstruction.
- Do not assume the shared bench folders alone are complete.
- Export or push missing images from `swe_dev`/`swe_dev2` into P0 registry or verified shared tars, then update per-bench image manifests with exact refs/checksums.
- Worker preflight must compare required task image refs against worker cache before full runs; current worker cache is partial for both SWE-bench Verified and TerminalBench2.1.
