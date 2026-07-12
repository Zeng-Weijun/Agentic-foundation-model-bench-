# TB2.1 x Qwen3-30B-A3B-Instruct-2507 x terminus-2 (official harness) — evidence package

Run **2026-07-12**, `RUN_ID = tb21_inst2507_t2_c32_0712170859`, on KVM Pod B (`env-kvm-57740737-bzw56`).
**Result: 3 / 89 resolved = 3.37% (mean_pass_at_1 = 0.03370787), tb_rc=0, status = finalized.**

Serving: Qwen3-30B-A3B-Instruct-2507 @ `100.100.104.147:30000` (sglang 0.5.13, tp2, seed 61643818),
IDENTITY_OK before + after. Harness: terminal-bench 0.2.18, terminus-2, dataset
terminal-bench-2.1-yaml-full89-r7-final-20260703 (89 tasks). Single pass@1, temperature 0.0.

## Contents
| path | what |
|---|---|
| `summary.md` / `summary.json` | headline result, counts, resolved ids, special-task handling |
| `calibration.md` | TB2.1 caliber; denom=89; **mailman + tune-mjcf = agent_not_converged (FALSE, counted)**; strict `infra_fail=2` heuristic explained; serving-health proof |
| `denom_assert.txt` | denominator proof: rows==89, score = 3/89 = 3.37%, why mailman & tune-mjcf count |
| `repro_closure.json` / `repro_closure.md` | tb 0.2.18, dataset + 89-task hash, exact tb command, sglang config, **per-task image digests**, vendored-script SHA256 |
| `results.json` | **tb-native** run results (89 rows, authoritative) |
| `results.jsonl` | 89 adjudicated per-task rows (null->false); mailman & tune-mjcf rows carry `reason=agent_not_converged` |
| `verdict/per_task_verdict.tsv` | 89-row per-task verdict (is_resolved, failure_mode, parser, tokens, dur, episodes) |
| `verdict/resolved_tasks.md` | the 3 passes with condensed terminus trace |
| `verdict/batched_scores.json` | per-task pass@1 ledger (derived from tb-native) |
| `verdict/tb21_strict_summary.json` | the run's own v4 strict ledger (verbatim) |
| `verdict_pack.tar.gz` | per-task results.json + panes + tests.log + final-episode trace — **offline re-adjudicable** |
| `serving/` | `get_model_info` + `get_server_info` before+after, + `IDENTITY_SUMMARY.txt` |
| `special_evidence/` | mailman (ConnectionRefused :25) + tune-mjcf (Time ~100%>60%) panes proving agent-not-converged |
| `launch.sh` | the profile launcher (`full_run_147.sh instruct`) |
| `scripts/` | `stage_tb21_official_qwen_launcher_terminus2.sh` + accept-instruct patch + identity/net-isolation/dryrun helpers |
| `run.env.summary` | tb env summary (model, dataset, 89 task ids, concurrency) |
| `run_console_excerpt.log` | meaningful lines from the run console |
| `TRACE.md` | full agent.cast / episode trace locations on shared disk + timeline |
| `SHA256SUMS` | seal over every file in this package |

## One-line caliber guard
TB2.1 terminus-2 single pass@1, denom=89. Not comparable to SWE-V or Multilingual. No official TB2.1 Qwen anchor claimed.
Companion: `../tb21_coder_terminus2_147/` (Qwen3-Coder, 10/89 = 11.24%).
