# DeepSWE full113 x Qwen3-Coder-30B-A3B-Instruct x qwen-code (Path A) — v6 evidence bundle

**Result: resolved = 0.**  Headline **0 / 113 = 0.00%**; valid-only (honest) **0 / 102 = 0.00%** (11 `gold_broken` excluded).

This bundle records a *zero* score honestly. Its central job is to **prove the 0 is real**
(genuine agent-capability failure) **and not a judging/scoring bug**. The proof is the
gold-validation audit: on **102** tasks the gold solution passes the exact task verifier
(reward=1 => judging is correct), and on those same 102 judging-correct tasks the agent's
patch scores 0 for every one.

## Contents
- `results.jsonl` — 113 per-task rows (gold_reward, agent_reward, status, target_ref).
- `report.json` — audit conclusion (gold_valid=102, gold_broken=11, agent_resolved=0, honest_rate=0).
- `orchestrator.log` — audit run log (`AUDIT` / `ALL_DONE` lines).
- `STATUS_AUDIT.md` — why the audit exists (venv/pytest verifier bug found + FIXED, then honest re-score).
- `agent_run_report.json`, `agent_run_orchestrator.log` — the generation run (qwen-code agent on :30001 Coder).
- `denom_assert.txt` — the two denominators (113 headline / 102 valid) + the 11 broken names & reasons.
- `by_lang.md` — per-language resolve table (all languages: resolved=0).
- `gold_validation/` — **core 0-is-real evidence**: 102 valid ids, 11 broken ids, gold-vs-agent table.
- `serving/` — serving identity (agent phase :30001 Coder weights, before+after; audit probe).
- `verdict/` — `per_task_verdict.tsv` (113) + `samples/` deep-dives (go/python/typescript/rust).
- `repro_closure.json` — per-task image ref/digest (`target_ref`) for all 113.
- `calibration.md` — what 0 means, anchors, and why it is not a bug.
- `verdict_pack.tar.gz` — packed copy of `verdict/` (portable evidence archive).
- `SHA256SUMS` — checksums of every file above.

## One-line reading
Same verifier, same tests: **gold => reward=1**, **agent => reward=0**, on 102 tasks. 0 is real.
