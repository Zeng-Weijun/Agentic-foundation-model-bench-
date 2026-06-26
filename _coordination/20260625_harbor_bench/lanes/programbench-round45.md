# ProgramBench Round45 Execution Inventory

Date: 2026-06-26
Lane: Round45 ProgramBench execution inventory
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/programbench-round45`
Branch: `feat/programbench-round45`
Base: `origin/feat/image-warmup-policy` at `6e86f1e`

## Result

ProgramBench cannot be advanced to a real worker/offline smoke from current staged assets. The current shared tree has no exact ProgramBench checkout, task data, compiled-program/fixture archive, hidden-test or grader contract, runner, runtime/image manifest, suite result parser, or trace contract.

This lane made ProgramBench fail closed instead of pretending readiness: `manifests/suite.example.yaml` now points `programbench` at a dedicated required manifest, `manifests/images/programbench.yaml`, whose required placeholder has no digest or fallback tar. The suite row remains `enabled: false` and `adapter_status: pending_adapter`.

No public download, Docker pull/build/run/save/load, model call, benchmark execute, TB2/tau3/RepoZero/MCP-Atlas/Tool-Decathlon file edit, or worker command was performed.

## Inventory

| surface | state |
|---|---|
| source/dataset | Missing. Checked shared names including `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/programbench`; no exact checkout or task data found. Existing reports mention ProgramBench public metadata only. |
| runner/adapter | Missing. `/data/nips/bench/run_programbench.sh` is absent; suite row remains `pending_adapter`. |
| image/runtime manifest | Added fail-closed manifest `manifests/images/programbench.yaml` with one required placeholder and no offline transport. |
| worker smoke | Not possible without source/dataset/runner/runtime. No worker command was attempted. |
| parser/trace contract | Missing. No hidden-test/grader output schema, fixture manifest, normalized parser, or trace artifact contract exists. |

## Expected External Contract Before Enablement

- Authoritative ProgramBench checkout and task data staged under shared storage by `dev`.
- One deterministic smoke task with executable/docs inputs, fixture archive, expected workspace layout, hidden-test/grader output schema, and artifact manifest.
- Runtime decision: docker-free dependency cache or container image map with digest-pinned P0 refs or fallback tar plus sha256.
- Worker-safe `run_programbench.sh` that never downloads on worker and writes artifacts under `BENCH_RUN_DIR`.
- Suite parser that consumes native score/artifact JSON and returns normalized pass/fail fields.


## Evidence Commands

| command | rc | evidence |
|---|---:|---|
| `git fetch origin feat/image-warmup-policy && git worktree add -b feat/programbench-round45 .worktrees/programbench-round45 origin/feat/image-warmup-policy` | 0 | Created isolated worktree on branch `feat/programbench-round45` at base `6e86f1e`. |
| `grep -RIn --exclude-dir=.git --exclude-dir=.worktrees -E "ProgramBench|programbench|Program Bench|program_bench" . | head -240` | 0 | Found only prior inventories, pending suite row, pending manifest placeholder, and metadata references; no runner/parser/adapter implementation. |
| `find /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026 /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench -maxdepth 5 \( -iname "*programbench*" -o -iname "*program-bench*" -o -iname "*program_bench*" -o -iname "ProgramBench" \)` | 0 | Found only this repo/worktree metadata paths, not a ProgramBench source checkout or dataset. |
| `test -e /data/nips/bench/run_programbench.sh` | 1 | Runner absent. |
| `test -e /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/programbench` | 1 | Shared ProgramBench dataset/checkouts absent at the expected shared-bench location. |
| `test -e /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/programbench` | 1 | Harbor adapter path absent. |
| `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --target-benches programbench --json` | 1 | Expected fail-closed status: `blocked`; blockers `no_enabled_suite_entry,suite_entry_disabled,adapter_not_wired,required_image_transport_missing`. |
| `python3 scripts/agentic_bench_images.py lint --image-manifest manifests/images/programbench.yaml --require-offline-transport --json` | 1 | Expected fail-closed image lint: one required image, one `missing_offline_transport`. |
| `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only programbench --model-profile dev_proxy_gpt54mini_8130` | 2 | Expected no-fake-green dry-run: `no runs selected for --only programbench`. |
| `PYTHONPATH=. python3 -m unittest scripts.test_agentic_bench_suite scripts.test_agentic_bench_images` | 0 | 69 tests passed. |
| `python3 scripts/agentic_bench_images.py lint-registry --registry manifests/bench_registry.yaml --manifest-id programbench --require-offline-transport --json` | 1 | Expected fail-closed registry lint: ProgramBench manifest selected, one required image without offline transport. |
| `git diff --check` | 0 | No whitespace/errors in diff. |
| scoped protected-manifest diff against TB2/tau3/RepoZero/MCP-Atlas/Tool-Decathlon paths | 0 | Byte count `0`; no protected existing benchmark manifests were touched. |
| scoped trailing-whitespace scan | 0 | `trailing_whitespace 0`. |
| scoped diff secret scan | 0 | `diff_secret_scan_matches 0`. |

## Issue-Ready Status

No new confirmed production-code bug was filed from this lane. The confirmed blocker is an inventory/readiness gap: ProgramBench lacks staged source/dataset/fixture-grader/runtime/parser/trace assets, so the correct action is the fail-closed manifest and disabled suite contract implemented here.

## Next Action

Stage the authoritative ProgramBench source and dataset on `dev`, freeze one smoke task plus fixture/grader and artifact contract, identify runtime/image/cache needs, then implement `run_programbench.sh` and a parser. Only enable the suite row after dry-run, image/runtime lint, and worker-safe smoke are concrete.
