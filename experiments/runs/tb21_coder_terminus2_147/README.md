# TB2.1 x Qwen3-Coder x terminus-2 (official harness) — evidence package

Clean rerun **2026-07-12**, `RUN_ID = tb21_coder_t2_c32_0711211754`, on KVM Pod B.
**Result: 10 / 89 resolved = 11.24% (mean_pass_at_1 = 0.11235955), infra_fail = 0, status = finalized.**

Serving: Qwen3-Coder-30B-A3B-Instruct @ `100.100.104.147:30001` (sglang 0.5.13, seed 484925000),
IDENTITY_OK before + after. Harness: terminal-bench 0.2.18, terminus-2, dataset
terminal-bench-2.1-yaml-full89-r7-final-20260703.

## Contents
| path | what |
|---|---|
| `summary.md` / `summary.json` | headline result, counts, resolved ids |
| `calibration.md` | TB2.1 caliber; anchors; **infra_fail=0 vs the old false `infra_fail=89`**; why the gate still says `blocked` |
| `repro_closure.md` | tb 0.2.18, dataset, exact tb command, sglang config, image digests, untracked-script SHA256 |
| `results.json` | **tb-native** run results (89 rows) |
| `verdict/per_task_verdict.tsv` | 89-row per-task verdict (is_resolved, failure_mode, parser, tokens, episodes) |
| `verdict/resolved_tasks.md` | the 10 passes with condensed terminus trace |
| `verdict/batched_scores.json` | batched-runner v4 scored ledger (config + per-task) |
| `serving/` | `get_model_info` + `get_server_info` before+after, + `identity_summary.md` |
| `launch.sh` | the coder-profile launcher (= full_run_147.sh) |
| `scripts/` | vendored driver `stage_tb21_official_qwen_launcher.sh` + identity/net-isolation/dryrun helpers |
| `run.env.summary` | tb env summary (model, dataset, 89 task ids, concurrency) |
| `run_console_excerpt.log` | meaningful lines from the run console |
| `TRACE.md` | where the full agent.cast / episode traces live on the shared disk |
| `SHA256SUMS` | seal over every file in this package |

## One-line caliber guard
TB2.1 terminus-2 single pass@1. Not comparable to SWE-V or Multilingual. No official TB2.1 Qwen anchor claimed.
