# MCP-Atlas Smoke Round43 Inventory

Date: 2026-06-26
Lane: Round43 MCP-Atlas execution inventory
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/mcp-atlas-smoke-round43`
Base: `origin/feat/image-warmup-policy` at `6e86f1e`

## Result

MCP-Atlas cannot be advanced to a real worker smoke from current staged assets.
The current shared tree has no exact MCP-Atlas checkout, dataset, runner, server reset/tool exposure contract, image transport manifest, or result parser. The only atlas-like shared tree found is SWE Atlas, which is not MCP-Atlas.

This lane therefore made MCP-Atlas fail closed instead of pretending readiness: `manifests/suite.example.yaml` now points `mcp_atlas` at a dedicated required manifest, `manifests/images/mcp_atlas.yaml`, whose required placeholder has no digest or fallback tar. The suite row remains `enabled: false` and `adapter_status: pending_adapter`.

## Inventory

| surface | state |
|---|---|
| source/dataset | Missing. Checked shared names including `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/MCP-Atlas`; no exact checkout or task data found. |
| runner/adapter | Missing. `/data/nips/bench/run_mcp_atlas.sh` is absent; suite row remains `pending_adapter`. |
| image manifest | Added fail-closed manifest `manifests/images/mcp_atlas.yaml` with one required placeholder and no offline transport. |
| worker smoke | Not possible without source/dataset/runner/images. No worker pull/build/run was attempted. |
| trace/result contract | Missing. No MCP server reset, exposed-tool manifest, judge artifact, or suite parser exists. |

## Next Action

Stage the authoritative MCP-Atlas source and dataset on `dev`, freeze one smoke task with MCP server lifecycle/reset and exposed-tool contract, enumerate server/runtime images with P0 digest refs or fallback tar sha256 values, then implement `run_mcp_atlas.sh` and a result parser. Only enable the suite row after dry-run, image lint, and a worker-safe smoke are concrete.
