# DeepSWE full113 x Qwen3-Coder-30B-A3B-Instruct x qwen-code (Path A) -- v6 evidence bundle

**Result: resolved = 0.**  Headline **0 / 113 = 0.00%**; valid-only (honest) **0 / 106 = 0.00%** (7 `gold_broken` excluded).

This bundle records a *zero* score honestly. Its central job is to **prove the 0 is real**
(genuine agent-capability failure) **and not a judging/scoring bug**. The proof is the
gold-validation audit: on **106** tasks the gold solution passes the exact task verifier
(reward=1 => judging is correct), and on those same 106 judging-correct tasks the agent's
patch scores 0 for every one. The 0 is **dual-signed REAL** by two independent auditors
(A clean-env re-run + B hand-repro) -- see `AUDIT_NOTES.md`.

## Correction (2026-07-13, see `AUDIT_NOTES.md`)
The original bundle reported gold_valid=102 / gold_broken=11. An independent audit found the driver
polluted `NO_PROXY` with the sglang serving IP, false-failing 4 httpx/happy-dom **gold** solutions.
Those 4 were reclassified `gold_broken -> gold_valid` (**gold_valid 102 -> 106, gold_broken 11 -> 7**).
The score is unchanged (numerator still 0): headline **0/113** and valid-only **0/106** are both 0.00%.
`AUDIT_NOTES.md` discloses all 5 judging bugs/caveats + the python venv-handicap floor.

## Contents
- `AUDIT_NOTES.md` -- **dual-sign REAL verdict (A+B) + full disclosure of 5 judging bugs/caveats** (NO_PROXY, atomic git-apply, untracked-file capture, python venv floor, no-patch narrative).
- `results.jsonl` -- 113 per-task rows (gold_reward, agent_reward, status, target_ref). **RAW polluted-run record** (4 NO_PROXY tasks still show gold_reward=0 here; superseded by the corrected conclusion -- see AUDIT_NOTES.md).
- `report.json` -- audit conclusion (gold_valid=106, gold_broken=7, agent_resolved=0, honest_rate=0) + `correction` block.
- `orchestrator.log` -- audit run log (`AUDIT` / `ALL_DONE` lines).
- `STATUS_AUDIT.md` -- why the audit exists (venv/pytest verifier bug found + FIXED, then honest re-score) + the NO_PROXY update.
- `agent_run_report.json`, `agent_run_orchestrator.log` -- the generation run (qwen-code agent on :30001 Coder).
- `denom_assert.txt` -- the two denominators (113 headline / 106 valid) + the 7 broken names & reasons.
- `by_lang.md` -- per-language resolve table (all languages: resolved=0).
- `gold_validation/` -- **core 0-is-real evidence**: 106 valid ids, 7 broken ids, gold-vs-agent table.
- `serving/` -- serving identity (agent phase :30001 Coder weights, before+after; audit probe).
- `verdict/` -- `per_task_verdict.tsv` (113, RAW) + `samples/` deep-dives (go/python/typescript/rust).
- `repro_closure.json` -- per-task image ref/digest (`target_ref`) for all 113.
- `calibration.md` -- what 0 means, anchors, the NO_PROXY correction, and the python floor caveat.
- `verdict_pack.tar.gz` -- packed copy of `verdict/` (portable evidence archive).
- `SHA256SUMS` -- checksums of every file above (re-sealed after the correction).

## One-line reading
Same verifier, same tests: **gold => reward=1**, **agent => reward=0**, on 106 tasks (clean env, dual-signed). 0 is real.
