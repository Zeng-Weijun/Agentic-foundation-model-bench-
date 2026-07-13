# Calibration -- how to read 98/400 = 24.5%

## What was measured
- **Bench**: RepoZero **Py2JS OFFICIAL 400** (`valid_ids`). One base image `repoarena-new`
  carries all task data (per-case dataset + oracle executable + 60-cap testcase samples).
  The task: re-implement a Python library's CLI behavior in **JavaScript** (`.mjs`) so its
  stdout matches the reference **oracle executable** across every testcase sample.
- **Agent (Path A)**: `qwen-code` native CLI, in-container, `--max-session-turns 40`,
  driving a self-hosted model. `workers=4`, per-case container isolation, resumable.
- **Model**: `Qwen/Qwen3-Coder-30B-A3B-Instruct` @ `http://100.100.104.147:30001/v1` (sglang 0.5.13).
- **Judge (RepoZero official `eval_case`)**: for each case, run `oracle_executable ARGS`
  and `node ENTRY.mjs ARGS` for EVERY sample; compare **normalized-line** stdout equality.
  `all_pass = (passed == total and total > 0)`; `reward = int(all_pass)`. **No model in the judge.**

## The number
- **Headline: 98 / 400 = 24.5% all_pass.** Denominator = **400, not shrunk**.
- 98 all_pass (reward=1), 302 not (reward=0). Per-library table: `by_lang.md`. Rows: `results.jsonl`.

## Is the number real? (denominator integrity + crash cases)
- `results.jsonl` has **400 unique** cases (no dup, no missing) -- see `denom_assert.txt`.
- **4** cases (`rsa/test5, rsa/test2, rsa/test17, mpmath/test14`) crashed **during the judge
  step** (driver hit a 10s exec timeout inside `eval_case`, so it never wrote `summary.json`;
  the orchestrator recorded them as `all_pass=false`, error `no summary.json`). They were
  **conservatively counted as fails** in the 400 denominator (never over-counts passes).
- Those 4 were **re-judged serving-free** against their already-generated `.mjs`
  (`scripts/rejudge_missing4.py` -> `rejudge_missing4.json`): **0 / 4 recovered passes**. Two
  were ORACLE-side timeouts (RSA keygen for `--bits 3178`/`4728` legitimately exceeds 10s, so
  those cases cannot score all_pass under this harness regardless of the agent), one hung the
  agent's own `.mjs`, one graded cleanly as 0/16. **=> 98/400 is airtight.**

## Anchor -- BAND ONLY, do NOT claim alignment
- The RepoZero arXiv anchor **54.70% +- 2.55** is **Mini-SWE-Agent + Claude-4.6-Sonnet**.
- This run is **qwen-code (native scaffold, NOT Mini-SWE-Agent) + Qwen3-Coder-30B-A3B-Instruct
  (NOT Claude-4.6-Sonnet)**. **Both the scaffold AND the model differ.** This is therefore a
  **NEW measurement with no matching official cell** -- use 54.70% only as a coarse ruler /
  sanity band, **never** as a same-model same-scaffold comparison. The 24.5% vs 54.70% gap
  reflects a smaller open 30B model + a different agent scaffold, not a harness defect (the
  grader is proven real: reference `.mjs` -> all_pass=1, empty `.mjs` -> all_pass=0; and every
  `judge.result.json` shows concrete oracle-vs-node stdout diffs).

## Harness caveat (disclosed)
- `eval_timeout = 10s` per sample. For 2 `rsa` cases the **oracle itself** exceeds 10s
  (large-key RSA keygen), so they are unscoreable-as-all_pass under this harness and counted
  as fail. Excluding just those 2 gives 98/398 = 24.6% -- immaterial. Reported denominator
  stays **400**.
