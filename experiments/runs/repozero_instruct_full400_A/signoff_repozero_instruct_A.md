# Sign-off — RepoZero × Qwen3-30B-A3B-Instruct-2507 (Path A, full 400) — Blind Reviewer A

**Reviewer identity:** Claude (Anthropic) general-purpose agent, acting as independent blind reviewer **A**. Honest labeling; I am not the run author. A separate reviewer B audited the same run in parallel.
**Date:** 2026-07-14 (UTC).
**Mandate:** assume the score is FAKE; attempt every falsification; declare REAL only if it survives.

## Claim under review
RepoZero (Py2JS, official 400) × Qwen3-30B-A3B-Instruct-2507 × qwen-code native-in-container (Path A) = **51/400 = 12.75% all_pass** (per-sample eval timeout 10s).

## Final verdict: **REAL** — could not be disproven.
- As measured by the run's own deterministic judge: **51/400 = 12.75%** (node 20).
- Strict official RepoZero image node 18: **46/400 = 11.50%** (MAJOR caveat below; −1.25pp).

## Falsification attempts and outcomes
| # | Attempt to disprove | Outcome |
|---|--------------------|---------|
| 1 | Re-derive headline from raw `results.jsonl` (ignore summary aggregates) | 400 rows, 400 unique, all_pass=51, reward=51, sets identical, rewards∈{0,1}; 51/400=0.1275 EXACT. Not disproven. |
| 2 | Denominator gaming? | run 400 == official `valid_ids` (set-equal, 0 diff); the 4 `excluded_ids` are INCLUDED (~0% each) → conservative, not inflated. |
| 3 | Judge放水 / hardcoded reward / LLM-in-loop? | Read official + driver `eval_case` + orchestrator: deterministic oracle-vs-node normalized-line equality, both rc==0; `sum(all_pass)/400`, no LLM, no hardcoded reward, no post-hoc edit. |
| 4 | Are the all_pass labels fake (stored `.mjs` don't really pass)? | Independent re-judge with my OWN harness on 12 cases. 11/12 at face value; the 1 gap (base58/test6) was MY node-version harness bug → under faithful node-20 replication it passes → **12/12 agreement**. |
| 5 | Wrong model (scope says "x Coder")? | "x Coder" is a hardcoded template literal (orchestrator:108, assemble_docs:61). Real model = Instruct-2507, triple-confirmed (summary.model + serving :30000 get_model_info/v1_models + rollout qwen_command). |
| 6 | 8 judge-crashes hiding failures/inflation? | All are 10s `TimeoutExpired` (oracle RSA-keygen or node hang), recorded reward=0 = conservative (can only lower the headline). |
| 7 | Artifact of the loose 10s timeout? | Sampled all_pass max-latency ≤0.96s except networkx/test1 (one sample 5.07s, borderline at 5s). Effect small (cf. Coder 24.5%→23.75%). |
| 8 | Agent cheating (calls oracle / imports real lib)? | Inspected generated `.mjs`: genuine from-scratch reimplementations (base58 big-int encoder etc.); prompt forbids external libs; hermetic `--network none` judge reproduces results. 60/60 not whitebox-overfittable (4 shown vs ≤60 hidden samples). |
| 9 | Is the judging environment faithful to official RepoZero? | **NO (MAJOR).** Judge runs on mounted qwen node **v20.20.2**, not the image's official **node 18** — inflates 5 cases. See below. |

## Severity-graded findings
- **BLOCKER:** none.
- **MAJOR — judging node version:** the Path A judge's `node` resolves to the mounted qwen **node v20.20.2** (container PATH prepends it), not the RepoZero image's official **node v18.19.1**, contradicting the driver docstring ("Eval always uses the IMAGE's native node for scoring fidelity"). Node 20 auto-detects a `.js` helper with ESM `export` as a module; node 18 rejects it. **5 of 51** all_pass cases (`base58/test3`, `base58/test6`, `bencoder/test3`, `bidict/test3`, `bidict/test5`) pass only under node 20 and **all fail under strict node 18** (re-judged: 0 passed each, `SyntaxError: Named export not found`). ⇒ node-20 headline 12.75% (51/400) vs strict-node-18 11.50% (46/400). The claimed 12.75% is real-as-measured but +1.25pp lenient vs the official harness. Fix: judge with `/usr/bin/node`, or ensure agents emit `.mjs`/`type:module`.
- **MINOR — scope label:** `summary.json` `scope` mislabels the model as "x Coder" (stale hardcoded template). Cosmetic; every authoritative signal says Instruct-2507. Fix: interpolate `args.model` into the template.
- **MINOR — crash handling:** driver `eval_case` doesn't catch `subprocess.TimeoutExpired`, so an oracle/node timeout crashes the whole per-case run ("no summary.json") instead of scoring that sample as a fail. Effect is conservative (reward=0), but 8 cases are recorded as infra-crash rather than clean fail.
- **REPRO:** headline independently reproduced from raw `results.jsonl`; denominator set-equality, judge logic, model identity, generated-code authenticity, and a 12/12 sample of verdicts all confirmed.

## Honest disclosure
- Anchor 54.70% is a different scaffold+model sanity band, not an official cell — correctly labeled as such by the authors.
- I re-judged a sample of cases (12 for pass/fail agreement, 5 for the node-18 split), not all 400; full re-judge would need the full compute run. The sampled agreement + deterministic-judge source-read + identity triangulation are the basis for REAL.
- Reviewer B audited the same run in parallel; this is my independent A pass.

## Evidence bundle
`calibration.md`, `results.jsonl`, `summary.json`, `denom_assert.txt`, `serving/` (get_model_info + v1_models for :30000 and :30001, image inspect), `verdict/` (my rejudge report + JSON), `scripts/` (recompute, rejudge, driver, orchestrator), `SHA256SUMS`. See `denom_assert.txt` for the independent numeric assertions.

— Reviewer A (Claude)
