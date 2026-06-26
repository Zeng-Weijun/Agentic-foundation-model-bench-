# Docs Taxonomy Audit Round 33

Date: 2026-06-26
Lane: docs audit
Scope: static audit only of `README.md`, top-level `docs/`, `reports/`, and `manifests/` in `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy` via `ssh dev`.

Constraints honored:

- No README, manifest, production-code, test, benchmark, Docker, or model-call edits.
- Wrote only this report: `_coordination/20260625_harbor_bench/lanes/docs-taxonomy-round33.md`.
- `docs/` does not exist in this worktree, so the final audit surface is `README.md`, `reports/`, and `manifests/`.

## Summary

Final current-state grep results:

| Surface | Exact stale-token result | Classification summary |
|---|---:|---|
| `README.md` | 0 matches, grep rc 1 | Clean in the final tree. A concurrent edit appears to have removed earlier README 2.0 text during this audit. |
| `manifests/` | 0 matches, grep rc 1 | Clean in the final tree. `manifests/suite.example.yaml` and `manifests/offline_images.example.yaml` are modified by another writer, not by this lane. |
| `reports/` | Matches remain, grep rc 0 | Mixed: 4 must-fix active-doc drift items, 8 historical okay items, and 8 tau3 dependency okay items. |
| `tau2_paper_core` | 0 matches, grep rc 1 | No occurrence found in the audited surface. |

Top-priority fixes:

1. `reports/pending_adapter_inventory_20260625.md:13` and `:41` still describe `terminal_bench_2_0` / Terminal-Bench 2.0 as directly suite-keepable active legacy work. That is active-doc drift; replace with Terminal-Bench 2.1 wording or move 2.0 to a clearly historical appendix.
2. `reports/agentic_bench_matrix_20260625.csv:5` keeps a valid historical public Qwen 2.0 caveat, but its local status still says local config includes `terminal_bench_2_0`. Replace the local-status phrase with current `terminal_bench_2_1` status.
3. `reports/agentic_bench_landscape_20260625.md:263` and `:793` still frame local follow-up work as if 2.0 may be active. Replace with Terminal-Bench 2.1 active-target wording.
4. Keep `tau2-bench` references only where they are explicitly upstream tau3 source/package dependencies. Do not expose them as a standalone active benchmark.

## Findings By Classification

### Must-fix active-doc drift

| File:line | Current text / issue | Suggested replacement |
|---|---|---|
| `reports/pending_adapter_inventory_20260625.md:13` | Says `terminal_bench_2_0` can be kept or added directly to `manifests/suite.example.yaml` as `wired_legacy`. This conflicts with the current active taxonomy. | Replace with `terminal_bench_2_1`: shared runner/dataset/image manifest exists but promotion depends on worker-safe image coverage; remove 2.0 from active inclusion readout. |
| `reports/pending_adapter_inventory_20260625.md:41` | Full table row presents `Terminal-Bench 2.0`, `terminal_bench_2_0`, `terminalbench2.0`, and `shared_bench/terminal-bench-2.0` as a suite-eligible legacy target. | Move row to a `Historical legacy assets` appendix, or replace with a Terminal-Bench 2.1 row pointing to `terminalbench2.1`, `run_terminal_bench_2_1.sh`, `shared_bench/terminal-bench-2.1`, and current TB2.1 image-manifest blockers. |
| `reports/agentic_bench_matrix_20260625.csv:5` | The closed-model/Qwen anchor correctly notes public Qwen data is Terminal-Bench 2.0-only, but `local_trace_status` says `Local config includes terminal_bench_2_0`. | Keep the 2.0 public-score caveat, but replace local status with `Local config targets terminal_bench_2_1; public Qwen 2.0 scores are not directly comparable; no local 30B Terminal-Bench 2.1 score inspected`. |
| `reports/agentic_bench_landscape_20260625.md:263` | Says local Qwen suite config includes `terminal_bench_2_0` under smoke and full benchmark lists. | Replace with `The active local suite target is terminal_bench_2_1; any terminal_bench_2_0 evidence is historical and not an active benchmark target.` |
| `reports/agentic_bench_landscape_20260625.md:793` | Follow-up work says `Terminal-Bench 2.1 or 2.0, whichever is actually reproducible in our harness`. That leaves 2.0 as an active fallback. | Replace with `Terminal-Bench 2.1 once reproducible in our harness; keep Terminal-Bench 2.0 only as a historical external Qwen-score anchor.` |

### Historical okay, but clarify if these docs remain active

| File:line | Why okay / risk | Suggested replacement or annotation |
|---|---|---|
| `reports/rootless_worker_research_20260625.md:162` | Historical rootless-research section comparing Terminal-Bench 2.0 and 2.1 requirements. | If the report is retained as historical, leave as-is. If surfaced as current guidance, change heading to `Historical Terminal-Bench 2.0 notes; active target is Terminal-Bench 2.1`. |
| `reports/rootless_worker_research_20260625.md:465` | Historical open question about which 2.0/2.1 tasks need rootless-incompatible capabilities. | Annotate `2.0` as legacy-only, or narrow the current question to `Which Terminal-Bench 2.1 tasks...`. |
| `reports/offline_docker_asset_plan_20260625.md:68` | Inventory of a discovered Terminal-Bench 2.0 first-four tar. It is not a current active target by itself. | Prefix with `legacy Terminal-Bench 2.0 asset, not active target`; keep adjacent Terminal-Bench 2.1 rows as the active path. |
| `reports/shared_disk_layout_research_20260625.md:97` | Static shared-disk tree includes `terminalbench2.0/`; directory existence is historical/layout evidence. | Keep if this is a layout snapshot, but annotate `legacy` if the report is reused in current public docs. |
| `reports/next_result_parser_contract_20260625.md:498` | Parser may need to read legacy historical `terminal_bench_2_0` results. The risk is that `Parser IDs` can look like active target IDs. | Replace with ``terminal_bench_2_0` (legacy historical result parser only)` or remove if no archived 2.0 result support is required. |
| `reports/agentic_bench_landscape_20260625.md:88` | Benchmark row is Terminal-Bench 2.1; 2.0 appears only as a public Qwen-score caveat. | Keep, but add `not comparable to local Terminal-Bench 2.1` if this table is reused externally. |
| `reports/agentic_bench_landscape_20260625.md:253` | Correctly states public Qwen report is for Terminal-Bench 2.0, not 2.1. | Keep as historical score provenance. |
| `reports/agentic_bench_matrix_20260625.csv:5` | The closed-model/Qwen anchor phrase `Terminal-Bench 2.0 only` is valid historical provenance. The same CSV row also has a must-fix local-status phrase listed above. | Keep the provenance phrase; change only the local-status field. |

### Dependency okay: tau3 upstream tau2 package/source only

| File:line | Why okay | Suggested replacement or annotation |
|---|---|---|
| `reports/pending_adapter_inventory_20260625.md:36` | `tau2-bench` appears as the upstream source checkout for `tau3-bench`, not as an active standalone tau2 benchmark. | Keep, but phrase as `upstream tau2 package/source used by the tau3 adapter`. |
| `reports/tau3_harbor_adapter_inventory_20260626.md:15` | `TAU3_SOURCE_ROOT` points at the upstream tau2-bench checkout used to generate tau3 datasets. | Keep; add a note that this is a tau3 source dependency if this snippet is copied elsewhere. |
| `reports/tau3_harbor_adapter_inventory_20260626.md:58` | Mentions generated Dockerfiles cloning `sierra-research/tau2-bench.git`; this explains an offline-build blocker in tau3 runtime materialization. | Keep as dependency evidence; do not present as standalone active tau2 benchmark. |
| `reports/p0_harbor_bench_manifest_inventory_20260625.md:39` | Explicitly says the tau3 adapter depends on the upstream tau2-bench checkout and is not a separate tau2 target. | Keep. This is the desired framing. |
| `reports/p0_harbor_bench_manifest_inventory_20260625.md:109` | Path inventory says tau2-bench exists as tau3 upstream source checkout. | Keep. This is the desired framing. |
| `reports/agentic_bench_matrix_20260625.csv:9` | tau3 primary source includes the upstream repository URL `github.com/sierra-research/tau2-bench`; this is tau3 source lineage. | Keep but label the field as `tau3 upstream source repository` if the CSV is edited. |
| `reports/agentic_bench_landscape_20260625.md:432` | Source URL for the tau3 lineage. | Keep as source provenance. |
| `reports/agentic_bench_landscape_20260625.md:812` | Source-links section says `tau3 upstream source repository: https://github.com/sierra-research/tau2-bench`. | Keep. This is the desired framing. |
| `reports/shared_disk_layout_research_20260625.md:101` | Static shared-disk tree includes `tau2-bench/`; likely source/dependency layout evidence, not active taxonomy. | Keep if this remains a layout snapshot; annotate `tau3 upstream source dependency` if reused in active docs. |

## Clean Surfaces In Final Current Tree

- `README.md`: no final matches for `tau2-bench`, `tau2_paper_core`, `Terminal-Bench 2.0`, `terminal_bench_2_0`, `terminalbench2.0`, or `shared_bench/terminal-bench-2.0`.
- `manifests/`: no final matches for the same exact stale-token set.
- `docs/`: absent, so no docs files were audited.
- `tau2_paper_core`: no matches anywhere in `README.md`, `reports/`, or `manifests/`.

Current `git status --short -- README.md manifests reports _coordination/.../docs-taxonomy-round33.md` before writing this report showed concurrent modified files:

```text
 M README.md
 M manifests/offline_images.example.yaml
 M manifests/suite.example.yaml
```

This lane did not modify those files. The final audit uses their current content as observed on disk.

## Exact Grep Commands And RC

| Purpose | Command | rc | Result |
|---|---|---:|---|
| Final exact stale-token audit | `PAT="tau2-bench|tau2_paper_core|Terminal-Bench 2\\.0|terminal_bench_2_0|terminalbench2\\.0|shared_bench/terminal-bench-2\\.0"; grep -RInE -- "$PAT" README.md reports manifests` | 0 | Matches remain only in `reports/`; no final `README.md` or `manifests/` hits. |
| Final `tau2_paper_core` audit | `grep -RIn -- "tau2_paper_core" README.md reports manifests` | 1 | No matches. |
| Final supplemental mixed-version audit | `PAT="Terminal[- ]Bench 2\\.0|Terminal Bench 2\\.0|terminal[_-]bench[_-]2[_\\.]0|terminalbench2\\.0|shared_bench/terminal-bench-2\\.0|tau2-bench|tau2_paper_core"; grep -RInEi -- "$PAT" README.md reports manifests` | 0 | Same current report hits; useful for punctuation/case variants. |
| Final semantic mixed wording audit | `PAT="2\\.0/2\\.1|2\\.1 or 2\\.0|2\\.0 only|terminal_bench_2_0|terminalbench2\\.0|shared_bench/terminal-bench-2\\.0"; grep -RInE -- "$PAT" README.md reports manifests` | 0 | Caught `reports/agentic_bench_landscape_20260625.md:793`, which the exact stale-token grep does not catch. |
| Final README exact check | `PAT="tau2-bench|tau2_paper_core|Terminal-Bench 2\\.0|terminal_bench_2_0|terminalbench2\\.0|shared_bench/terminal-bench-2\\.0"; grep -nE -- "$PAT" README.md` | 1 | No final README hits. |
| Final manifests exact check | `PAT="tau2-bench|tau2_paper_core|Terminal-Bench 2\\.0|terminal_bench_2_0|terminalbench2\\.0|shared_bench/terminal-bench-2\\.0"; grep -RInE -- "$PAT" manifests` | 1 | No final manifest hits. |

## Non-grep Static Commands Run

| Purpose | Command | rc | Result |
|---|---|---:|---|
| Workflow read | `sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Read required workflow. |
| Workflow continuation | `sed -n '261,620p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Continued workflow read. |
| Workflow continuation | `sed -n '621,1040p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Completed workflow read. |
| Remote worktree preflight | `ssh dev 'cd /mnt/.../.worktrees/image-warmup-policy && printf "PWD=%s\n" "$PWD" && git branch --show-current && git log --oneline -1 && git status --short -- ...'` | 0 | Confirmed branch `feat/image-warmup-policy`, HEAD `bd66566 Promote TB2 qemu-startup transport`. |
| Audit-surface file listing | `find README.md docs reports manifests -type f` with missing-path guard | 0 | `docs` reported missing; README/reports/manifests listed. |
| Context reads | `nl -ba <hit files> | sed -n <ranges>` | 0 | Read narrow context around matching lines for classification. |

