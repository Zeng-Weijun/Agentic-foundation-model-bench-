# Sign-off — ProgramBench × Qwen (both models) × qwen-code (Path A) — Auditor A

**Auditor A = Claude (Opus). Honest labeling. Mandate: default the score is fake; falsify hard; REAL only if unfalsifiable.**
date: 2026-07-16 · pod: KVM eval pod (env-kvm-57740737-bzw56) · sglang 0.5.13 tp=2

| Bench | Model | Scaffold | Headline (honest) | Denom | Verdict |
|-------|-------|----------|-------------------|-------|---------|
| ProgramBench | Qwen3-Coder-30B-A3B-Instruct | qwen-code PathA | **11 / 200** (mean_score; 12 if 7 harness-eval-fails excluded) | 200 | **REAL** |
| ProgramBench | Qwen3-30B-A3B-Instruct-2507 | qwen-code PathA | **0 / 200** (mean_score 0.15%) | 200 | **REAL** |

ProgramBench = reconstruction bench: black-box executable + docs → rebuild codebase → offline `compile.sh`→`./executable` → hidden pytest → JUnit → `score = passed%`. **No LLM judge.** Headline = mean per-instance score over the fixture-excluded benchmark.

## What I checked (falsification attempts — all failed to break it)
1. **Mean recomputed 2 independent ways** = finisher: official `score_run` (Coder 22.8385/200=0.114193→11; Instruct 0.302184/200=0.001511→0) AND official CLI `programbench info` re-run by me (`Average 11 / 200`, `Average 0 / 200`). Naive raw pass-rate cross-check same order (16.6 / 0.2); the official active-branch filter only *lowers* the score.
2. **Denominator = 200**, provably complete: `benchmark_instances()`=200 (fixture `testorg__calculator` excluded, leaked=[]); both lanes present=200, missing=0, not-benchmark=0. No silent drops; a missing task would be excluded (not 0), none missing.
3. **Independent Docker re-eval (capstone, anti-fabrication)**: re-ran official `programbench eval` on the Coder cmatrix submission in the cleanroom image (isolated /tmp, original untouched) → **0.8182 (82), identical to recorded**, passed 652/fail 112/skip 5, **executable_hash byte-identical**. eval.json is faithful.
4. **gold-sanity**: gold cmatrix → **1.0000 (100) SOLVED** — compile→test→score chain reaches 100 with correct source (768/769; 1 fail on an ignored branch, correctly filtered).
5. **Coder = real skill**: cmatrix agent genuinely reverse-engineered (wrote src/cmatrix.c 14KB + compile.sh, probed the binary, 35 turns). Leak ruled out by the gold gap (gold 100 vs Coder 82). 139/200 compiled.
6. **Instruct 0 = real failure**: 195/200 never emit source (190 compile_failed + 5 copy_executable_failed); sampled instruct cmatrix submission has **no source at all** (only provided docs) — agent ran the binary instead of writing code. Same-harness gold=100 / Coder=82 / 5 instruct-nonzero prove the harness is sound; the 0 is the model's.
7. **quinn disclosed**: `eval_results_read_failed` (harness eval failure, 0 tests read) counted as 0 — conservative; excluding it Coder is still 11.
8. **serving identity** grounded in local on-disk weights (model_path + seed, not a client label): Coder 30001 seed 484925000, Instruct 30000 seed 61643818, both before==after. Consistent with REPRODUCTION_INDEX serving table.

## Direction check
Coder (code-specialist) 11 > Instruct-2507 (general) 0 — consistent with every other bench in this campaign (Coder > Instruct). ProgramBench is hard (0 SOLVED for both; best single task cmatrix 82 for Coder).

## Findings ledger
- BLOCKER: none.
- MAJOR: none.
- MINOR / disclosure (do not change verdict):
  - Headline uses denom = # present eval.json (=200 here). If a task were missing it would be excluded, not 0 — matches `info` semantics; all 200 present so moot.
  - Coder 11 is a conservative lower bound: 7 whole-task harness-eval-failures (1 `eval_results_read_failed` quinn + 6 `eval_failed_or_timeout`) counted 0; excluding them → 12. 16 tasks carry per-branch `results_read_failed`/`no_expected_test_list` that depress specific scores. No inflation path.
  - "Instruct all compile_failed" is imprecise: 190 compile_failed + 5 copy_executable_failed + 5 compiled-with-partial-credit. Headline 0 unaffected.
- REPRO: cmatrix Coder re-eval byte-exact (82, hash match); gold cmatrix 100 SOLVED; mean reproduced by score_run + CLI info on both lanes.

**Signed: Auditor A (Claude). Verdict REAL for both ProgramBench Coder (11/200) and Instruct (0/200).**
