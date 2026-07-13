# Calibration -- what 0/113 means for Instruct-2507 on DeepSWE (Path A, qwen-code)

- **Headline 0/113 = 0.00%**, valid-only **0/106 = 0.00%**.
- Same-family anchor: **Coder-30B** on the identical bench+scaffold = **0/113 (0/106 valid)** (dual-signed).
  Instruct-2507 lands at the same headline; DeepSWE full113 is hard enough that neither 30B model resolves a task.
- **Ruler, not an official cell**: qwen-code native scaffold (NOT the DeepSWE paper's harness); this is a
  NEW measurement, not an official-cell match.
- **Behavioral caveat (Instruct vs Coder handicap, disclosed):** Instruct-2507 produced a captured patch on
  1 of 106 valid tasks; the remainder are no-patch from (a) exploration loops (repeated glob/read
  until max session turns), (b) 262144-token context overflow surfacing as `[API Error: 400 (no body)]` after
  greedy multi-file reads, and (c) narrating completion with zero edits. These are genuine Instruct behaviors,
  NOT scaffold bugs -- per-sample proof shows edits, when they happen, ARE captured in the git diff and verified.
- **The 0 is not a judging bug**: gold passes the same verifier on 106 tasks (see gold_validation/).
