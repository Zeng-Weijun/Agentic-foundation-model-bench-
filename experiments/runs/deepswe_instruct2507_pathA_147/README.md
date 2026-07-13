# DeepSWE full113 x Qwen3-30B-A3B-Instruct-2507 x qwen-code (Path A) -- v6 evidence bundle

**Result: resolved = 0.**  Headline **0 / 113 = 0.00%**; valid-only (honest) **0 / 106 = 0.00%** (7 `gold_broken` excluded).

Records the score honestly and proves the number is real (genuine agent-capability failure, not a
judging/scoring bug) via the gold-validation audit: on **106** tasks the gold solution passes the exact
task verifier (reward=1 => judging correct), and on those same 106 judging-correct tasks the agent's
patch scores !=1 for every one.

## Serving (identity verified both phases)
- endpoint **http://100.100.104.147:30000/v1** (self-hosted sglang), weights **Qwen3-30B-A3B-Instruct-2507**.
- `serving/` holds get_model_info before+after (agent + audit) and a real per-task qwen_command
  (`--openai-base-url http://100.100.104.147:30000/v1 --model Qwen/Qwen3-30B-A3B-Instruct-2507`) + a live probe.

## Contents
- `results.jsonl` / `report.json` -- 113 per-task audit rows + audit conclusion.
- `agent_run_report.json`, `agent_run_orchestrator.log` -- generation run (qwen-code agent on :30000 Instruct-2507).
- `denom_assert.txt` -- the two denominators (113 headline / 106 valid) + NO_PROXY correction + 7 broken names.
- `by_lang.md` -- per-language resolve table.
- `gold_validation/` -- core 0-is-real evidence: 106 valid ids, 7 broken ids, gold-vs-agent table.
- `serving/` -- serving identity probes (before+after) + example qwen_command + live get_model_info/get_server_info.
- `verdict/` -- `per_task_verdict.tsv` (113) + `samples/` per-lang deep-dives (agent patch, gold pass, agent re-verify fail).
- `repro_closure.json` -- per-task image ref/digest (`target_ref`) for all 113.
- `calibration.md`, `AUDIT_NOTES.md`, `TRACE.md` -- reading, caveats, and the run trace.
- `verdict_pack.tar.gz` -- packed copy of `verdict/`.
- `SHA256SUMS` -- checksums of every file above.

## One-line reading
Same verifier, same tests: **gold => reward=1**, **agent => reward!=1**, on 106 tasks. The 0/113 is real.
