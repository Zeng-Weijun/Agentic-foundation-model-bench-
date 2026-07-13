# signoff_multilingual_coder_setE_A.md

**Auditor:** Claude (Opus) — independent **blind cross-family auditor A**, one signature of the
cross-family double-sign (co-signer = Codex family, auditor B).
**Audit date:** 2026-07-14 (UTC+8 HKT).
**Claim under audit:** SWE-bench Multilingual × Qwen3-Coder-30B-A3B-Instruct, after the `set -e`
strict re-adjudication (commit `c49474b`), true score = **23.33 % (70 / 300)** — i.e. the earlier
double-signed value **24.33 % (73/300)** was polluted by a harness `set -e` bug, and **3** stale-artifact
false positives (`fmtlib__fmt-3863` C++, `google__gson-1014` Java, `javaparser__javaparser-4561` Java)
were removed.
**Mandate:** try to prove **23.33 % (70/300) is FAKE**. If it cannot be disproved → **REAL**.

## VERDICT: **REAL** ✅  (could not prove FAKE)

Every FAKE hypothesis (over-removal, under-removal, denominator shrink, arithmetic error, wrong
serving identity, dishonest disclosure) was tested and refuted by **independent container re-runs**
(`bash -e`, my own script, not the re-judgment's) plus documentary cross-checks.

---

## 1. Independent `set -e` container re-runs (my own; images byte-identical to eval images)

Method: fresh container of the exact instance image, hash baked test artifact, apply the model
`patch.diff` exactly as the harness does (`git apply`), rewrite `eval.sh` `set -uxo pipefail`
→ `set -euxo pipefail`, run it, capture rc / whether `>>>>> Start Test Output` was reached /
artifact sha256 after. Log: `tmp/set_e_audit/claudeA_rerun.log`, `claudeA_results.jsonl`,
`claudeA_<iid>.strict.txt`.

### 1a. The 3 REMOVED rows — all independently confirmed genuine FALSE POSITIVES

| instance | lang | flavor | my strict rc | reached_test | evidence |
|---|---|---|---|---|---|
| `fmtlib__fmt-3863` | C++ | stale-binary (build-fail) | **2** | **0** | model patch → real C++ compile errors (`error: ambiguous template instantiation`; `'…underlying_' has incomplete type`) → **`gmake: *** [Makefile:381: ranges-test] Error 2`**. Baked `/testbed/build/bin/ranges-test` sha256 `18c58be90cda…` **identical before/after (zero rebuild)** → original harness scored the STALE prebuilt binary. |
| `google__gson-1014` | Java | stale-test (apply-fail) | **1** | **0** | gold test patch `git apply --reject` → **`error: …JsonTreeReaderTest.java: already exists in working directory`** → aborts before test under `-e`. |
| `javaparser__javaparser-4561` | Java | stale-test (apply-fail) | **1** | **0** | gold test patch `git apply --reject` → **`error: …Issue4560Test.java: already exists in working directory`** → aborts before test under `-e`. |

→ **Over-removal DISPROVED**: all 3 removed rows genuinely fail under `set -e`; none is actually resolvable.

### 1b. Retained rows — sampled, all independently confirmed genuinely REAL

| instance | lang | my strict rc | reached_test | rebuild evidence |
|---|---|---|---|---|
| `fmtlib__fmt-3729` | C++ | 0 | 1 | `std-test` sha `8f0c20a25b48…` → `4d045e46bfa2…` (**rebuilt**), tests pass |
| `redis__redis-9733` | C | 0 | 1 | `*-server` sha `f6fb37ac18fb…` → `53ce9a3bb210…` (**rebuilt**), FAIL_TO_PASS passes |
| `javaparser__javaparser-4538` | Java | 0 | 1 | Maven build+test reached & passed under `-e` |
| `apache__druid-15402` | Java | 124 (timeout only) | 1 | Only rc≠0 retention. Original log: model + **gold test patch applied cleanly**, **BUILD SUCCESS**, `Tests run: 1, Failures: 0, Errors: 0` on FAIL_TO_PASS `testCacheStrategy`. `reached_test=1` under `-e` proves the gold patch applied; rc=124 is purely the 600 s re-run cap on a huge Maven build, **not** a stale artifact. Correct to keep. |

→ **Under-removal DISPROVED** on the sample.

Cross-family reproducibility: my independent hashes match the re-judgment's exactly
(fmt-3863 stale `18c58be90cda`; fmt-3729 rebuilt `4d045e46bfa2`).

## 2. Coverage — no high-risk row was skipped

`score_summary.json` per-language totals: **C 30/7, C++ 12/6, Java 43/8** ⇒ the only build-vulnerable
(compiled-language) resolved rows number **7+6+8 = 21**. The re-judgment's strict re-run set
(`strict_rerun.sh` ∪ `strict_rerun2.sh`) equals **exactly these 21** instance ids (verified by set
diff against the original resolved list). Go/Rust/Ruby/PHP/JS/TS (immune: test command self-recompiles
and aborts on failure) were correctly excluded. → **under-removal by omission DISPROVED**.

## 3. Denominator, arithmetic, ledger

- `denom_assert.txt`: 300 rows == 300 unique == declared 300 (subset manifest 300); **PASS**. Per-language
  totals sum to 300. **Denominator invariant** across the fix (300 unchanged).
- Original `results.jsonl`: 300 rows, **73** resolved. Corrected `results.jsonl` (evidence worktree):
  300 rows, **70** resolved, differing from the original by **exactly 3 rows**, each carrying
  `set_e_audit_false_positive:true`, `resolved:false`, `resolved_original:true`
  (`fmt-3863`, `gson-1014`, `javaparser-4561`). No other row changed.
- 73/300 = 0.243333; **70/300 = 0.233333 = 23.33 %**. Arithmetic correct.

## 4. Serving identity — :30001 = Coder (confirmed, stable)

`serving/get_model_info_{before,after}.json` and `get_server_info_{before,after}.json`:
`model_path = …/models/Qwen3-Coder-30B-A3B-Instruct`, `port: 30001`, before AND after the run.
`runner_config.json`: `base_url = http://100.100.104.147:30001/v1`, `model = Qwen/Qwen3-Coder-30B-A3B-Instruct`,
`scaffold = qwen-code`, `bench = SWE-bench Multilingual`. → serving :30001 was Qwen3-Coder for the whole run.

## 5. Disclosure honesty

`AUDIT_NOTES_SET_E_BUG.md` accurately describes the harness defect (`set -uxo pipefail`, no `-e`),
both false-positive flavors, the hash-based method, the exact 3 removed rows, and the 73→70 / 24.33→23.33
correction. It matches my independent findings with no overstatement or omission.

---

## Conclusion

The `set -e` re-judgment removed **neither too many nor too few**: the 3 removed rows are genuine
stale-artifact false positives (independently reproduced), all 21 build-vulnerable resolved rows were
re-checked with 100 % coverage, the retained sample genuinely builds and passes under `set -e`, the
denominator stayed 300, the arithmetic is exact, serving was Qwen3-Coder at :30001, and the disclosure
is honest. **I could not prove 23.33 % (70/300) FAKE → it stands as REAL.**

**Multilingual × Coder (qwen-code) = 70 / 300 = 23.33 %  — REAL.**

— Claude (Opus), cross-family auditor A · evidence branch `evidence/sweml-full300-147-20260713` @ base `c49474b`
