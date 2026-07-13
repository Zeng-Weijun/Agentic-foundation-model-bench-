# Cross-family Auditor A sign-off — SWE-bench Multilingual × Qwen3-30B-A3B-Instruct-2507 (set -e re-adjudication)

- **Auditor:** Claude (Opus) — cross-family blind auditor **A**, one of the two cross-family signatures.
- **Date (UTC):** 2026-07-14
- **Run under audit:** `sweml_instruct2507_qwencode_full300_147_20260712T090033Z`
- **Bundle:** `experiments/runs/sweml_instruct2507_full300_147/` (evidence branch `evidence/sweml-full300-147-20260713`)
- **Audit commit re-checked:** `c49474b` ("set -e audit: remove 7 stale-artifact false positives from Multilingual qwencode bundles")
- **Claim under audit:** the set-e re-adjudicated score **9.33 % (28 / 300)** — i.e. original buggy-harness **32 → 28** after removing **4** stale-artifact false positives (`fmtlib__fmt-2457`, `fmtlib__fmt-2310`, `nlohmann__json-4237` [C++], `javaparser__javaparser-4561` [Java]).
- **Mandate:** try to prove **9.33 % (28/300) is FAKE** (removed-too-many / removed-too-few / missed-FP / denominator-shrinkage). If it cannot be broken → **REAL**.

## VERDICT: **REAL** — I could not break it.

Every adversarial angle was tested with **independent fresh-container re-runs** (not by trusting the audit notes). All evidence corroborates 28/300 = 9.33 %.

---

## Method (independent, not trace-only)

For each sampled instance I started a **fresh container** of the exact instance image, applied the model `patch.diff` as the harness does (`git apply`), then ran the harness's **own** per-instance `eval.sh` rewritten only by `set -uxo pipefail → set -euxo pipefail`. I recorded: model-patch apply result, **sha256 of the test binary before/after the build**, whether the `>>>>> Start Test Output` section was reached, and the script rc. Driver: `.../agentic-foundation-model-bench/tmp/setE_audit_A/reprod_set_e.sh`. Host: KVM eval pod (docker 26.1.3), all SWE-bench Multilingual images present.

Adjudication rule (same as SWE-bench + the audit): a resolved row is a **false positive** iff, under strict `set -e`, the script **aborts before the test section** (build or gold-test-apply fails); for build-failure cases the pre-baked test binary sha256 is **byte-identical** before/after (zero rebuild). It is **genuine (REAL)** iff the build/apply succeed, the test section runs on **freshly-built** artifacts (binary sha256 changes / Maven `BUILD SUCCESS`), and the tests pass.

---

## 1. The 4 removed rows are genuinely stale false positives (NOT removed-too-many)

All 4 abort under `set -e` before any legitimate test on fresh artifacts. The three C++ binary hashes I measured **match the audit's recorded hashes exactly**.

| instance | lang | set-e rc | reached test? | test binary | sha256 before → after | signature |
|---|---|---:|---|---|---|---|
| `fmtlib__fmt-2457` | C++ | 2 | **no** | `/testbed/build/bin/ranges-test` | `9ba87169…` → `9ba87169…` **identical** | `no member named format_specs` → gmake Error 2 |
| `fmtlib__fmt-2310` | C++ | 1 | **no** | `/testbed/build/bin/format-test` | `2faa459c…` → `2faa459c…` **identical** | `CMake Error … add_executable` → CMake generate failed |
| `nlohmann__json-4237` | C++ | 2 | **no** | `/testbed/build/tests/test-udt_cpp11` | `5b97afe9…` → `5b97afe9…` **identical** | `is_unsigned_v is not a member of std` (C++17-in-C++11) → make Error 2 |
| `javaparser__javaparser-4561` | Java | 1 | **no** | (Maven / `~/.m2` jar) | n/a | gold-test `git apply --reject` → `already exists in working directory` (flavor-2) |

Cross-check on the **original** buggy run confirms the false pass: e.g. `javaparser-4561`'s original `test_output.txt` shows both `already exists in working directory` (gold-test apply failed) **and** `BUILD SUCCESS` / `Tests run: 1, Failures: 0` — the stale base test file "passing". Identical hashes + `already-exists` are direct proof these 4 were never legitimately resolved. **Removal is correct.**

## 2. No stale false positive survives among the 28 retained (NOT removed-too-few)

Of the 28 retained resolved, exactly **6 are C/C++/Java** (the only stale-artifact-eligible languages); the other **22 are Go/Rust/Ruby/PHP/JS/TS** (compiled/interpreted at test-invocation → no pre-baked binary to fall back to → immune). I re-ran **all 6 risky ones** plus one immune Go control. Every one is a **genuine** pass under `set -e` (build succeeds, binary rebuilt / `BUILD SUCCESS`, tests pass):

| instance | lang | set-e rc | reached test? | binary before → after | result |
|---|---|---:|---|---|---|
| `fmtlib__fmt-3729` | C++ | 0 | yes | `8f0c20a2…` → `5d65a985…` **changed** | ctest 13 tests passed |
| `micropython__micropython-13039` | C | (1)\* | yes | `e1abbc1e…` → `3bfdff22…` **changed** | run-tests.py 15 tests passed |
| `redis__redis-9733` | C | 0 | yes | `e3afb51f…` → `d19354c4…` **changed** (distclean+make) | `\o/ All tests passed` |
| `google__gson-2024` | Java | 0 | yes | Maven | `BUILD SUCCESS`, 3 tests, 0 failures |
| `google__gson-1093` | Java | 0 | yes | Maven | `BUILD SUCCESS`, 0 failures |
| `google__gson-2134` | Java | 0 | yes | Maven | `BUILD SUCCESS`, 0 failures |
| `gin-gonic__gin-2121` | Go (immune control) | 0 | yes | `go test` rebuilds | `PASS` / `ok` |

\* `micropython-13039` rc=1 comes only from the **post-test** cleanup `git checkout` of a pre-baked test path (after `>>>>> End Test Output`); the binary was genuinely rebuilt (hash changed) and 15 tests passed on it — a REAL resolution. `fmt-3729` is the decisive control: same repo/CMake system as two of the removed FPs, but here the patch **compiles**, the binary **rebuilds** (hash changes), and tests pass — proving the audit discriminated genuine-vs-stale rather than blanket-dropping C++.

The per-language distribution of the 28 retained IDs (C 2, C++ 1, Go 6, Java 3, JS 2, PHP 1, Ruby 6, Rust 6, TS 1 = 28) **exactly matches** the audited `calibration.md` per-language table.

## 3. Denominator is intact (NOT shrunk) and arithmetic is correct

- `results.jsonl`: **300** rows, **300** unique `instance_id`. `denom_assert.txt`: `rows==declared AND unique==rows ⇒ PASS`; stamped `denominator INVARIANT (300 rows unchanged); resolved corrected 32→28`.
- Exactly **4** rows carry `set_e_audit_false_positive:true` + `resolved_original:true`; parent commit `c49474b~1` has **32** `resolved:true`, `c49474b` has **28**. 32 − 4 = 28.
- 28 / 300 = **0.093333 = 9.33 %**. Per-language resolved sum = 28. (Denominator was **not** shrunk to inflate the rate; the corrected rate is in fact *lower* than the buggy 32/300.)

## 4. Serving identity = Instruct-2507 (not Coder) & inter-model sanity

- `runner_config.json`: `base_url = http://100.100.104.147:30000/v1`, `model = Qwen/Qwen3-30B-A3B-Instruct-2507`.
- Agent traces: **426** API responses echo `"model":"Qwen/Qwen3-30B-A3B-Instruct-2507"` (direct from the :30000 server).
- `calibration.md`: `serving identity before==after: True (model_path=…/models/Qwen3-30B-A3B-Instruct-2507, sglang=0.5.13, seed=61643818)`.
- The **Coder** bundle is a distinct run (`model_path=…/Qwen3-Coder-30B-A3B-Instruct`, seed `484925000`) scoring 70/300 = 23.33 %. Two different weights/seeds → the Instruct run was not accidentally Coder. **Instruct 9.33 % < Coder 23.33 %** is the expected direction and a reasonable magnitude for a general-instruct vs a code-specialised model on multilingual SWE tasks.

---

## Adversarial attempts and why each FAILED to prove FAKE

- **Removed too many** → refuted: all 4 removed rows independently abort under `set -e` (3× byte-identical stale binaries matching audit hashes; 1× gold-test-apply failure). None was a genuine pass.
- **Removed too few / missed FP** → refuted: all 6 risky C/C++/Java retained rows genuinely rebuild+pass; the remaining 22 are stale-artifact-immune languages (confirmed premise via Go control `gin-2121`).
- **Denominator shrinkage** → refuted: 300 invariant, unique==rows==300, stamped; correction only flips 4 booleans.
- **Arithmetic / identity** → refuted: 28/300 = 9.33 % exact; per-language sums to 28; serving is genuinely Instruct-2507.

**Conclusion: 9.33 % (28 / 300) for SWE-bench Multilingual × Qwen3-30B-A3B-Instruct-2507 is REAL.** — Claude, cross-family auditor A.
