# Calibration — ProgramBench × Qwen3-30B-A3B-Instruct-2507 × qwen-code (Path A)

run: `runs/programbench_full201_instruct` · finisher: `programbench_pathA/CAMPAIGN_finisher.log`
auditor: **A = Claude (Opus), honest labeling.** Mandate: assume the score is fake, try to falsify; REAL only if unfalsifiable.

## Score
- **mean_score = 0 / 200**  (official `programbench info` Average).
- Independent recompute (`score_run`): sum(fractions)=**0.302184**, mean=0.302184/200=**0.001511 → display 0** (`{avg*100:.0f}`). Official CLI `programbench info` re-run by me → `Average 0  200 instances`. Matches finisher exactly.
- scoring: same official pipeline as coder (no LLM judge). SOLVED=**0**, nonzero=**5/200**, zero=195.
- the 5 nonzero (compiled + partial credit): hexyl 15.3, lz4 6.4, xsv 6.3, typst 1.3, lnav 0.9. Mean over 200 = 0.15% → rounds to 0.

## Denominator (200)
- identical to coder: `benchmark_instances()` = 200 (fixture `testorg__calculator` excluded, leaked=[]); instruct lane present=200, not-benchmark=[], missing=0. denom==present==200. See `denom_assert.txt`.

## Bench × Model × Harness
- bench: **ProgramBench** (reconstruction), image_tag `task_cleanroom_v6`, offline cleanroom Docker.
- model: **Qwen/Qwen3-30B-A3B-Instruct-2507** (qwen3_moe, the general/base instruct sibling of Coder).
- serving identity (local sglang, on-disk weights): `model_path=/mnt/.../models/Qwen3-30B-A3B-Instruct-2507`, port **30000**, sglang **0.5.13**, seed **61643818**, before==after. See `serving_IDENTITY_SUMMARY.json`.

## The 0 is a real model/tool-use failure, NOT a harness bug
- error_code distribution over 200: **compile_failed = 190**, copy_executable_failed = 5, None (compiled) = 5. So **195/200 never produced a buildable submission**.
- Sampled `abishekvashok__cmatrix` (instruct, compile_failed): submission.tar.gz contains **only the provided docs** (`cmatrix.1`, `README.md`, `COPYING`, `data/img/*`) — **no `src/`, no `cmatrix.c`, no `compile.sh`**. The agent (model=Qwen3-30B-A3B-Instruct-2507) repeatedly **ran the black-box binary** (`./executable -V`, garbled long option strings) and **never emitted `write_file`** to reconstruct source → empty build → `compile_failed` → all tests `not_run` → 0.
- **Not a harness bug**, proven three ways on the *same* task + *same* harness: gold cmatrix = 100 SOLVED; Coder cmatrix = 82; Instruct cmatrix = 0 (empty submission). And the harness *can* score Instruct when it produces something — 5 instances compiled and earned partial credit. So 0 reflects the model failing the reconstruction task, not an infra block.

## harness-eval-failures
- instruct lane whole-task harness-eval-failures = **0** (no `eval_results_read_failed`, no `eval_failed_or_timeout`). 1 per-branch `results_read_failed` on `burntsushi__xsv` only (that task still scored 6.3 from other branches). Headline 0 is clean.

## Independent verification (auditor A)
1. **Recompute** (2 ways): `score_run` → 0.1511→0; official CLI `programbench info` → `Average 0  200 instances`.
2. **Empty-submission mechanism** confirmed by direct inspection of the compile_failed submission tar + agent log (above) — the model genuinely did not attempt source reconstruction.
3. Cross-task control: on the identical harness, gold=100 and Coder=82 for cmatrix; the harness is sound — Instruct's 0 is the model's.
4. Auditor **B** (codex second-opinion, concurrent, isolated) independently re-evaluating `instruct_hexyl` (one of the 5 nonzero) — complementary coverage.

## Verdict
**REAL.** Could not falsify. Headline **Instruct = 0 / 200** (mean 0.15%). The failure mode is genuine: 195/200 never emit source (compile_failed / copy_executable_failed), and where the model does produce output the harness scores it (5 nonzero). Same-harness gold=100 / Coder=82 rule out an infrastructure cause.
