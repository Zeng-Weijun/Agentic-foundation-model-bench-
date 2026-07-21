# CERT_B — SWE-bench Multilingual dual-sign (SECOND signer, independent)

- **Signer role:** second sign-off. Independent recompute from raw run artifacts. **CERT_A_MULTILINGUAL.md was NOT read** (double-sign independence preserved).
- **Mandate:** try hardest to prove the scores wrong; write `INSUFFICIENT_EVIDENCE` where proof is missing; prefer an honest "not comparable" verdict over rubber-stamping.
- **Host:** `env-kvm-57740737-bzw56...pod@h.pjlab.org.cn` (hostname `rjob-ac00b0a8...`). Read-only; no file under any run_root modified; sglang intentionally down (`100.100.104.140:3000x` unreachable — expected, disk-only audit).
- **A** = `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_coder_qwencode0162_clean274_20260710t083916z` (Coder-30B, claims 57/274 = 20.80%)
- **B** = `.../runs/sweml_instruct2507_qwencode0162_clean274_20260710t103651z` (Instruct-2507, claims 22/274 = 8.03%)
- Scan scripts (local scratchpad): `analyze_run.py`, `lombok_scan.py`, `cheat_scan.py`.

---

## Line 1 — Score independent recompute → **CONFIRMED (both)**

Recomputed directly from `results.jsonl` (not from score_summary):

| | rows | unique | dup | resolved=True | eval_rc | sha256(results.jsonl) | claimed sha |
|---|---|---|---|---|---|---|---|
| A | 274 | 274 | 0 | **57** | all 0 (274) | `aab29ee4bfbe7e6e79070020be82ef9e2cb602b6227d1097322aead99ac1caed` | `aab29ee4…` ✓ |
| B | 274 | 274 | 0 | **22** | all 0 (274) | `cc41b1de7bed1fd491c1d59132001e763705ac09dfed65d5f59fd4e26a516fd9` | `cc41b1de…` ✓ |

- Denominator = 274 for both. 57/274 = 0.208029, 22/274 = 0.080292 — match `score_summary_clean274.json` exactly.
- `resolved_other` (null/non-bool) = 0 in both. agent_status A: patch 255 / no_patch 19; B: patch 185 / **no_patch 89** (consistent with a weaker model).

## Line 2 — resolved backed by official harness, not orchestrator field → **CONFIRMED (both)**

- For **every** one of the 274 rows in each run, opened the harness top-level report (`instances/<id>/eval/Qwen__<model>.v2_<id>.json`, field `resolved_ids`). **Mismatch results.resolved vs harness = 0** in both runs; 0 missing report files; 0 unparsable; 0 internal-inconsistent. `resolved_true_ids == harness_resolved_ids` exactly (57 / 22).
- Deep official product also present and genuine: `.../eval/logs/run_evaluation/v2_<id>/Qwen__<model>/<id>/report.json` carries full SWE-bench `tests_status` with **real test names** (e.g. `astral-sh__ruff-15443` FAIL_TO_PASS `rules::flake8_bandit::…s102…`, `patch_successfully_applied:true`, `resolved:true`).
- `eval_wrap.py` merely wraps the official module `runpy.run_module("swebench.harness.run_evaluation")` plus an offline env-cache + a docker `ContainerCollection.list(ignore_removed=True)` cleanup-race shim — it does **not** compute verdicts. Grading is the official harness.

## Line 3 — Evidence integrity & A/B comparability → **CONFIRMED asymmetric caveats; comparable only at harness-verdict level**

- `eval_wrap.py` byte-identical in both: sha `81cb668d25cecce85f0c86799716895ce2671c8db8aa2c4c320c1009da777d25`. mtimes **differ**: A = `2026-07-10 18:27:03 +0800`, B = `2026-07-10 18:37:13 +0800` (each inside its own eval-staging window; 10 min apart, sequential).
- **A carries `MIXED_EVAL_ENVIRONMENTS` (self-disclosed, CRITICAL).** `FINAL_CODER_CLEAN274_STATUS.json → critical_eval_wrap_caveat`: the frozen `eval_wrap.py` is **not** the main-run execution snapshot; `original_eval_wrap: ORIGINAL_LOST`; `main_271_rows_eval_environment: "without ignore_removed"`, the 3 repair rows `"with ignore_removed=True"`. Cause: 3 instances (`facebook__docusaurus-8927`=TS, `projectlombok__lombok-3479`=Java, `tokio-rs__tokio-7139`=Rust) hit a docker cleanup-race `404 NotFound` **after** the official test result (`three_discarded_evals_environment: "…inspect-404 after official test result"`), giving eval_rc=1 → run correctly **BLOCKED** at 271 rows (`DENOMINATOR_BLOCKED.json`, status `blocked_denominator_mismatch`) instead of reporting 271. An eval-only frozen-patch repair (`cleanup_race_repair_summary.json`) restored the 3 rows — **all 3 resolved=False, reports under `/repairs/`** → added **0** to the 57. That repair's `_write_eval_wrap()` overwrote run_root/eval_wrap.py (the disclosed provenance loss). model_path before=after=post_repair.
- **B carries an IDENTITY caveat but a CLEAN eval_wrap.** `provenance/EVAL_WRAP_LAUNCH_PIN.json` pins eval_wrap sha `81cb668d…`+mtime at launch (10:37:13 UTC) plus shas of orchestrator/launcher/contract/clean274-ids; `provenance/EVAL_WRAP_FINAL_VERIFY.json` → `exact_match:true` (launch==final) → **eval_wrap NOT overwritten**. B has **no** repairs/ dir, **0** rows sourced from `/repairs/`, 0 failed — all 274 first-pass.
- The `ignore_removed` shim only suppresses a container-listing 404 during **cleanup**, after grading; it cannot change any resolved verdict. So both caveats are **provenance-purity flaws, not grading flaws**.
- **Independent comparability verdict:** A-main (without-shim, snapshot lost) and B (with-shim, pinned) were **not executed under byte-identical eval wrappers**, and their disclosed integrity gaps are **asymmetric** (A: eval_wrap provenance lost; B: post-run model-identity unverifiable). Neither gap is shown to affect any verdict. ⇒ Comparable at the *official-harness-verdict level* (same 274 subset, same scaffold qwen-code 0.16.2, same launcher, sequential on one host), but **NOT a byte-clean provenance-symmetric comparison.**

## Line 4 — Model identity → **CONFIRMED A (before+after); B before CONFIRMED, after UNVERIFIABLE (reasonable)**

- **A** `serving_config/get_model_info_{before,after,post_repair}.json` all = `/mnt/.../models/Qwen3-Coder-30B-A3B-Instruct`. A **did** capture an after-snapshot (18:22, serving still up).
- **B** `provenance/INSTRUCT_RUN_QUARANTINE_STATUS.json`: `get_model_info_before = …/Qwen3-30B-A3B-Instruct-2507`, `get_model_info_after_file_exists:false`. Post-run rechecks `get_model_info_postrun_recheck.json` (14:19:58 UTC, `<urlopen error timed out>`) and `_noproxy` (15:05 UTC, curl rc=28) both fail. **B's last results row ts = 14:05:23 UTC**, i.e. all 274 evaluated **before** the first failed probe (14:19). A finished eval ~10:28 UTC, B launched 10:36 UTC → **sequential**, so the Coder→Instruct swap (ports :30001→:30000 per contract) happened cleanly between runs. B-after UNVERIFIABLE is **benign & reasonable**.
- Supporting: report model tags = `Qwen__Qwen3-Coder-30B-A3B-Instruct.v2` (A, 274/274) and `Qwen__Qwen3-30B-A3B-Instruct-2507.v2` (B, 274/274) — distinct.
- Independent LLM-transport error recount (adapter stderr/log only, excluding repo/prompt text): A & B each conn-refused 0, http-5xx 0, read-timeout 1 (a tool/command "timed out", not LLM transport). ≈0 transport errors ⇒ stable serving during agent execution. **SUPPORTING, not proof** (cannot exclude a silent restart).

## Line 5 — Lombok 0/17 + cheat scan → **CONFIRMED model self-harm; cheat scan CLEAN (both)**

Uniform scan of harness `patch.diff` + `test_output.txt` + `report.json` under `eval/logs/run_evaluation/`:

| run | lombok | resolved | patch→`buildScripts/tests.ant.xml` | `Target "test.instance" does not exist` | BUILD FAILED |
|---|---|---|---|---|---|
| A (Coder) | 16 (+1 in repairs) | **0** | 15 | 15 | 15 |
| B (Instruct) | 17 | **0** | 17 | 17 | 17 |

- Qwen-side causal proof: both qwen-code runs rewrite `buildScripts/tests.ant.xml`, destroy the Ant `test.instance` target, and then hit `BUILD FAILED`. Lombok 0/17 is **model/scaffold self-harm**, identical for A and B (neutral to the comparison), categorically **distinct** from the 26 Gradle env false-zeros. The former local relay GPT control row and result were removed on 2026-07-21.
- **Cheat scan CLEAN both runs** (all 57 / 22 resolved reports inspected): empty-patch-but-resolved = **0**; resolved-but-patch-not-applied = **0**; resolved-but-zero-FAIL_TO_PASS-success = **0**; resolved-but-tool_use==0 = **0**. Every resolved instance has a real applied patch, ≥1 genuinely-passing FAIL_TO_PASS test, and non-zero tool_use.

## Line 6 — per-language + denominator → **CONFIRMED (both)**

- Independent per-language recompute (repo→language via official-harness rule, CPP/TS refinement per `scripts/full300_swemultilingual_orchestrator_v21.py:141`) reproduces **both** score_summaries exactly: A = C7/30, C++6/12, Go8/42, Java0/17, JS6/33, PHP4/43, Ruby9/44, Rust15/43, TS2/10 (Σ=57); B = C3,C++3,Go2,Java0,JS2,PHP1,Ruby6,Rust3,TS2 (Σ=22). Totals Σ=274, matching unit-test assertion `scripts/test_swemultilingual_qwencode_clean274.py:51`.
- Denominator: `manifests/candidates/swemultilingual_clean274_contract_20260710.json` → full=300, clean=274, excluded=26 = druid 5 + lucene 9 + gson 9 + javaparser 2 + rxjava 1 (reason "Gradle build chain not closed under offline eval → false zeros"). Contract set arithmetic gives exactly 26 with the same repo breakdown, and clean274 ⊂ full300. Frozen dataset `data/test-00000-of-00001.parquet` sha256 `28b7f874…` matches contract.
- **Java 0/17 (lombok, Ant, model self-harm) ≠ the 26 excluded (Gradle, env false-zero).** Distinction verified. Scores stated on 274, never 300. Contract also discloses scaffold deviation qwen-code 0.16.2 vs earlier 0.15.6 (neutral to A-vs-B, both 0.16.2).

## Independence / anti-fabrication cross-check
- A∩B resolved = 19; **A-only = 38, B-only = 3** (`faker-ruby__faker-2970, redis__redis-10095, sharkdp__bat-2650` resolved by Instruct but not Coder). Both directions non-empty ⇒ genuinely independent runs; B is not a copy/subset of A. McNemar b/c = 38/3.

---

## Per-run verdict
- **A (Coder-30B) = 57/274 = 20.80% → VALID-WITH-CAVEAT.** Score real, harness-backed, cheat-free, correct denominator. Caveat: `MIXED_EVAL_ENVIRONMENTS` — frozen eval_wrap ≠ main-271 snapshot (original lost); 3 rows re-evaluated with a grading-neutral docker-race shim, all unresolved (0 score impact). Disclosed at CRITICAL severity.
- **B (Instruct-2507) = 22/274 = 8.03% → VALID-WITH-CAVEAT.** Score real, harness-backed, cheat-free, correct denominator, eval_wrap cryptographically pinned+verified (not overwritten). Caveat: post-run `get_model_info_after` UNVERIFIABLE (serving down after eval); before=Instruct-2507 confirmed, corroborated by 274/274 report tags + benign timing.

## Comparability verdict
**Qualified YES.** Both scores are individually valid and cheat-free on the identical 274 subset, same scaffold/launcher/harness, sequential on one host; the 20.80% vs 8.03% gap (57 vs 22; b/c=38/3) is driven by real resolved instances across all languages, not any artifact. **But it is not a byte-clean, provenance-symmetric comparison:** the two runs carry *different* disclosed integrity gaps (A: eval_wrap provenance lost / mixed shim; B: post-run identity unverifiable) and were not run under byte-identical eval wrappers. Neither gap is shown to change any verdict. Report the pair **with both caveats attached**, not as a pristine head-to-head.
