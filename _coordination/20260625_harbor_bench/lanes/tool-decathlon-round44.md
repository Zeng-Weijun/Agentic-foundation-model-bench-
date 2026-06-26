# Tool-Decathlon Round44 Execution Inventory

Date: 2026-06-26
Lane: Round44 Tool-Decathlon execution inventory
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tool-decathlon-round44`
Branch: `feat/tool-decathlon-round44`
Base: `origin/feat/image-warmup-policy` at `6e86f1e`

## Result

Tool-Decathlon cannot be advanced to a real worker/offline smoke from current staged assets. The current shared tree has no exact Tool-Decathlon/Toolathlon checkout, dataset/task split, runner, tool-server lifecycle/reset contract, app state/tool exposure contract, image transport manifest, or suite result parser.

This lane made Tool-Decathlon fail closed instead of pretending readiness: `manifests/suite.example.yaml` now points `tool_decathlon` at a dedicated required manifest, `manifests/images/tool_decathlon.yaml`, whose required placeholder has no digest or fallback tar. The suite row remains `enabled: false` and `adapter_status: pending_adapter`.

No public download, Docker pull/build/run/save/load, model call, benchmark execute, TB2/tau3/RepoZero run, or MCP-Atlas file edit was performed.

## Inventory

| surface | state |
|---|---|
| source/dataset | Missing. Checked shared names including `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/Tool-Decathlon`; no exact checkout or task data found. Existing reports mention Tool-Decathlon/Toolathlon public metadata only. |
| runner/adapter | Missing. `/data/nips/bench/run_tool_decathlon.sh` is absent; suite row remains `pending_adapter`. |
| image manifest | Added fail-closed manifest `manifests/images/tool_decathlon.yaml` with one required placeholder and no offline transport. |
| worker smoke | Not possible without source/dataset/runner/images. No worker command was attempted. |
| trace/result contract | Missing. No app/tool-server reset, tool exposure manifest, grader artifact schema, or suite parser exists. |

## Expected External Contract Before Enablement

- Authoritative checkout and task data staged under shared storage by `dev`.
- One deterministic smoke task with frozen app state, tool-server lifecycle/reset, exposed-tool list, and grader output schema.
- App/tool-server/runtime image map with digest-pinned P0 refs or fallback tar plus sha256.
- Worker-safe `run_tool_decathlon.sh` that never downloads on worker and writes artifacts under `BENCH_RUN_DIR`.
- Suite parser that consumes native score/artifact JSON and returns normalized pass/fail fields.

## Next Action

Stage the authoritative Tool-Decathlon/Toolathlon source and dataset on `dev`, freeze one smoke task plus tool-server lifecycle/reset and grader contract, enumerate server/runtime images with P0 digest refs or fallback tar sha256 values, then implement `run_tool_decathlon.sh` and a parser. Only enable the suite row after dry-run, image lint, and worker-safe smoke are concrete.
