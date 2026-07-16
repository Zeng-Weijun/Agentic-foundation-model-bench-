# Calibration — ProgramBench × Qwen3-Coder-30B-A3B-Instruct × qwen-code (Path A)

run: `runs/programbench_full201_coder` · finisher: `programbench_pathA/CAMPAIGN_finisher.log`
auditor: **A = Claude (Opus), honest labeling.** Mandate: assume the score is fake, try to falsify; REAL only if unfalsifiable.

## Score
- **mean_score = 11 / 200**  (official `programbench info` Average, headline metric).
- Independent recompute (official `programbench.submission.score_run`): sum(fractions)=**22.8385**, mean=22.8385/200=**0.114193 → display 11** (`{avg*100:.0f}`). Matches finisher exactly.
- scoring: **no LLM judge.** Per instance, `score = passed / kept` over the JUnit test results, after `for_branches(active) + without_ignored` filtering; `is_resolved = (status=="passed")`. Headline = mean of per-instance fractions over the # of present eval.json. SOLVED (✅) iff score==1.0.
- distribution: SOLVED(=1.0)=**0**, nonzero=**138/200**, zero=62. top scores*100: 81.8(cmatrix) 71.0 50.8 49.7 49.3 45.8 …

## Denominator (200)
- `benchmark_instances()` excludes `FIXTURE_PREFIX="testorg__"` → **200** real instances (fixture `testorg__calculator` removed). fixture leaked into denom = **[]** (none).
- coder lane: present eval.json = **200**, present-but-not-benchmark = [], benchmark-but-missing = **0**. denom == present == 200, complete, no dupes, nothing silently dropped. See `denom_assert.txt`.
- `info` divides by # present eval.json (not a fixed 200); here all 200 are present so denom is the full fixture-excluded benchmark. A missing task would be **excluded** (not counted 0) — none are missing.

## Bench × Model × Harness
- bench: **ProgramBench** (reconstruction — given a black-box executable + docs, rebuild the codebase so `compile.sh` → `./executable` passes the hidden test suite). Meta ProgramBench, source `bench/sources/ProgramBench` (Meta Platforms license header).
- model: **Qwen/Qwen3-Coder-30B-A3B-Instruct** (qwen3_moe), served locally.
- serving identity (local sglang, NOT a relay — grounded in on-disk weights, not a client label): `model_path=/mnt/.../models/Qwen3-Coder-30B-A3B-Instruct`, port **30001**, tp=2, sglang **0.5.13**, `served_model_name=Qwen/Qwen3-Coder-30B-A3B-Instruct`, seed **484925000**, before==after. See `serving_IDENTITY_SUMMARY.json`. (Serving is down now; irrelevant to judging — scoring re-runs already-submitted patches.)
- eval: `programbench eval --image-tag task_cleanroom_v6 -w 1` in offline cleanroom Docker; tests pinned offline at `programbench_pathA/blobs` (202 entries). materialize seam: OCI store → `skopeo copy oci:store docker-archive` → `docker load` (skopeo docker-daemon broken on this pod), then bake pip.conf/pytest-timeout.

## Coder score is real skill (not leak / not fixture)
- cmatrix (score 82): agent log (`subs/abishekvashok__cmatrix.5c082c6/submission.tar.gz.agent.log`, model=Qwen3-Coder-30B) shows genuine black-box reverse-engineering — probed the reference binary (`executable -V`, `-h`), then hand-wrote `src/cmatrix.c` (14 KB) + `compile.sh` (offline gcc), compiled `./executable`, 35 turns / 237 s / ~1M input tokens. submission.tar.gz contains the reconstructed `./src/cmatrix.c` + `./compile.sh`.
- **Leak ruled out by the gold gap**: gold (reference source) = **100 SOLVED**; Coder reconstruction = **82** (imperfect). With the original source it would be ~100; 82 is a real partial reconstruction.
- 139/200 tasks reached `error_code=None` (compiled + produced test results) — broad genuine reconstruction, not a single lucky task.

## The headline is CONSERVATIVE, not inflated
- 1 task `quinn-rs__quinn` = `eval_results_read_failed` (branches=0, test_results=0, empty log) — a **harness eval failure**, counted as score 0. Excluding it: 22.8385/199 = 11.48 → still **11**.
- 6 tasks `eval_failed_or_timeout` (per-task 1800 s eval timeout) synthesized as score 0 (conservative floor; could be ≥0 if re-run without timeout).
- 16 tasks carry per-branch `results_read_failed` / `no_expected_test_list` (that branch's tests → 0) — depresses those task scores.
- Excluding all 7 whole-task harness-eval-failures from the denom: mean → **12**. So the reported **11 is a lower bound**; there is no path by which harness artifacts inflate it.

## Independent verification (auditor A)
1. **Recompute** (2 ways): official `score_run` → 11.4193→11; official CLI `programbench info` re-run by me → `Average 11  200 instances`. Naive raw pass-rate (no branch filter) = 16.6 (higher; the official active-branch filter lowers, never raises).
2. **Independent Docker re-eval (capstone)**: re-ran official `programbench eval` on the cmatrix submission.tar.gz in the cleanroom image, isolated `/tmp` out dir (original eval_out untouched) → **score 0.8182 (82), IDENTICAL to recorded**; `passed 652 / failure 112 / skipped 5`; **executable_hash byte-identical** (`4cc57cf3…`). Proves eval.json is faithful, not fabricated. Evidence: `reeval_cmatrix.log`.
3. **gold-sanity**: gold cmatrix eval.json → `score_instance = 1.0000 (100) SOLVED=True` (768/769 passed; the 1 failure is on an inactive/ignored branch, correctly filtered out) — proves the compile→pytest→JUnit→score chain reaches 100 with correct code.
4. Auditor **B** (codex second-opinion, concurrent, isolated `/root/codex_secondopinion_verify`) independently re-evaluating `coder_zoxide` — complementary coverage.

## Verdict
**REAL.** Could not falsify. Headline **Coder = 11 / 200** (conservative; 12 if 7 harness-eval-failures excluded). Independently reproduced: mean (2 methods) + 1 full Docker re-eval byte-exact (82) + gold-sanity 100.
