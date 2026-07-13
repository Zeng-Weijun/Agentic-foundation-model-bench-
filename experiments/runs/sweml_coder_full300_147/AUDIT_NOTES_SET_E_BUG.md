# AUDIT_NOTES_SET_E_BUG.md

**Audit date:** 2026-07-13T11:56:14Z
**Auditor:** Claude (set -e stale-artifact re-adjudication), following a Codex-family review finding.
**Scope:** re-adjudication of `resolved` for this bundle's run under strict `set -e` semantics.

## The bug (harness defect, not a model result)
SWE-bench per-instance `eval.sh` (this harness, swebench 4.1.0) begins with:

    #!/bin/bash
    set -uxo pipefail          # <-- NO `-e`

Because `-e` is absent, a **non-zero exit of a build or gold-test-patch-apply command does NOT
abort the script**. Execution falls through to the test-run/parse step, which then reads a
**stale, pre-baked artifact** left in the instance image. The SWE-bench log parser sees the
stale artifact's output as a pass and marks the instance **resolved** — a false positive.

Two false-positive flavors were observed (both fixed by `set -e`):
1. **Stale binary (build-failure).** C/C++ (CMake/ctest, `make`) targets whose test executable is
   pre-compiled into the image. When the model patch breaks compilation, `cmake --build` / `make`
   returns non-zero; without `-e`, `ctest`/`./test` runs the **pre-baked binary** (byte-identical
   sha256 before/after == zero rebuild) and the old test set "passes".
2. **Stale test file (test-patch-apply-failure).** Java (Maven) and any case where the gold test
   patch fails to apply (`git apply --reject` -> "already exists in working directory" / "does not
   apply"). Without `-e`, the test command runs the **base/stale test file** (not the gold test)
   and the pre-existing test "passes". For Java, a failed `mvnw clean install -am` also leaves the
   **stale base module jar in ~/.m2**, which the subsequent test step resolves against.

## Re-adjudication method (hard evidence)
- **All 31 high-risk (C/C++/Java) resolved tasks** across both Multilingual runs were re-run in a
  fresh container of the exact instance image, model patch applied as the harness does, with
  `eval.sh` rewritten to `set -euxo pipefail`. Captured: script rc, whether the `>>>>> Start Test
  Output` section was reached, and **sha256 of the test binary before/after the build**.
  - **FALSE_POS** iff the script aborts before the test section under `set -e` (build or gold-test
    apply fails). For build-failure cases the test binary sha256 is **byte-identical** before/after
    (zero rebuild) — direct proof of stale-binary reuse.
  - **REAL** iff build+apply succeed, the test section runs on freshly-built artifacts (sha256
    changes / genuine test pass).
- **Every resolved task in all 4 runs (459 total)** was statically scanned for a pre-test build or
  git-apply failure signature. Exactly the false positives below were found; **SWE-V = 0/354**,
  Multilingual low-risk languages (Go/Rust/Ruby/PHP/JS) = 0.

## Verdict for THIS bundle
This bundle contains **3 false-positive resolved rows** (reclassified to unresolved):

| instance_id | lang | flavor | evidence |
|---|---|---|---|
| `fmtlib__fmt-3863` | C++ | build-failure | ranges-test build FAILED (gmake Error 2); STALE /testbed/build/bin/ranges-test sha256 18c58be9.. identical before/after (zero rebuild) -> false pass |
| `google__gson-1014` | Java | test-patch-apply-failure | gold test patch `git apply --reject` FAILED ('JsonTreeReaderTest.java: already exists in working directory'); without set -e, mvnd test ran the STALE/base JsonTreeReaderTest -> false pass |
| `javaparser__javaparser-4561` | Java | test-patch-apply-failure | gold test patch `git apply --reject` FAILED ('Issue4560Test.java: already exists in working directory'); without set -e, mvnw test ran the STALE/base Issue4560Test -> false pass |

## Corrected headline
- original (buggy harness): **score 0.243333  (resolved 73 / 300)**
- corrected (set -e):       **score 0.233333  (resolved 70 / 300)**

## Cross-line summary (whole audit)
| line | bench | original | corrected | false positives |
|---|---|---|---|---|
| Instruct-2507 x qwen-code | SWE-bench Multilingual (300) | 32 (10.67%) | **28 (9.33%)** | 4 (C++/Java) |
| Coder x qwen-code | SWE-bench Multilingual (300) | 73 (24.33%) | **70 (23.33%)** | 3 (C++/Java) |
| Instruct-2507 x qwen-code | SWE-bench Verified (500) | 120 (24.0%) | **120 (24.0%)** | 0 (SAFE, Python) |
| Coder x qwen-code | SWE-bench Verified (500) | 234 (46.8%) | **234 (46.8%)** | 0 (SAFE, Python) |

Raw per-instance evidence for the buggy verdicts remains in `verdict_pack.tar.gz` / `results.jsonl`
(the `resolved` flag of the false-positive rows is flipped to `false` with
`set_e_audit_false_positive: true` and `resolved_original: true` for traceability).
