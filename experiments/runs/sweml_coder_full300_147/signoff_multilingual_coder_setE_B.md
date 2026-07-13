# signoff_multilingual_coder_setE_B.md

**Auditor:** auditor B, cross-family co-signer alongside auditor A (Claude/Opus,
`signoff_multilingual_coder_setE_A.md`, commit `7dde1ae`).
**Identity-honesty disclosure (mandatory per task):** the agent that performed the hands-on
SSH/docker/container verification below is a **Claude (Sonnet 5)** instance, not a native
Codex session. Per the mandate's "身份诚实" rule, I did **not** relabel my own Claude output as
Codex. Instead I genuinely invoked `codex-pro` (`gpt-5.6-sol`, `reasoning.effort=ultra`,
`--dangerously-bypass-approvals-and-sandbox`) locally on the Mac control plane with a full brief
(SSH access, evidence paths, exactly which instances were already covered so it would pick new
ones, explicit "try to prove FAKE" mandate). **Contention check (`ps aux`), as the task anticipated:**
at launch there were already **6-7 unrelated, actively-running `gpt-5.6-sol --dangerously-bypass`
`exec` sessions** on this Mac (a different agent's repo2env bug-hunt, started ~01:17, still running
17-20+ min later) plus a dozen idle parked `resume` panes. My own codex-pro process (PID 51146,
launched 01:31) stayed alive but accumulated only **~13s of CPU over 9m17s wall-clock** (`ps -o
etime,time`) — i.e. genuinely queued/rate-limited behind the other sessions on the shared OAuth
account, not a bug on my side. I gave it a fair, verified window (repeated `ps aux`/`ps -o etime`
checks, not a guess) before proceeding per the task's own explicit fallback ("串行/等或直接自己
Claude 做并诚实标注"). **If the backgrounded codex-pro run produces output after this file lands,
it will be appended as a dated addendum in a follow-up commit — it does not block this signoff
because my own findings below are independent, hard, reproducible evidence, not opinion.**

**Audit date:** 2026-07-14 (HKT).
**Claim under audit:** SWE-bench Multilingual x `Qwen/Qwen3-Coder-30B-A3B-Instruct` (qwen-code
0.16.2), after `set -e` strict re-adjudication (commit `c49474b`), score = **23.33% (70/300)**,
corrected down from a buggy 24.33% (73/300, itself previously same-family double-signed and now
superseded — see `git log --oneline -- '*/sweml_coder_full300_147/*'`, commit `8392524`). 3 rows
removed as stale-artifact false positives: `fmtlib__fmt-3863` (C++), `google__gson-1014` (Java),
`javaparser__javaparser-4561` (Java).
**Mandate:** try hard to prove 23.33% (70/300) is FAKE. Could not disprove -> REAL.

## VERDICT: **REAL** (could not prove FAKE)

---

## 1. Full C++/Java coverage of the retained 70 (not just a 3-4 sample)

The Coder-70 contains **11** C++/Java rows (`calibration.md`: C++ 5/12, Java 6/43). I covered
**all 11**, at two evidence tiers:

### 1a. Fresh-container `bash -e` reruns (highest tier — own containers, own run, today)
Method: `docker run` a fresh container from the exact cached harness image
(`swebench/sweb.eval.x86_64.<owner>_1776_<repo>-<num>:latest`, confirmed present via `docker
images`), `git apply -v /tmp/patch.diff` (the same `patch.diff` the harness recorded), copy
`eval.sh` with `set -uxo pipefail` rewritten to `set -euxo pipefail`, run it, capture exit code
and whether `>>>>> End Test Output` was reached.

| instance | lang | strict rc | reached End marker | independent proof |
|---|---|---|---|---|
| `fmtlib__fmt-2317` | C++ | 0 | yes | `format_test.format_double` OK; binary `build/bin/format-test` mtime **`Jul 13 17:19`** (my rerun time) vs image build **14 months ago** = fresh rebuild, not stale reuse |
| `nlohmann__json-4237` | C++ | 0 | yes | doctest XML `OverallResultsAsserts successes="70" failures="0"` **exact match** to the original stored `test_output.txt`; binary `build/tests/test-udt_cpp11` mtime **`Jul 13 17:19`**, sha256 `66170f23…`. Note: this exact instance_id is one of the Instruct-bundle's 4 excluded FPs, so it was the highest-value adversarial pick — Coder's own patch uses a C++11-safe `std::is_signed<T>{}` tag-dispatch (not the C++17-only `is_unsigned_v` that presumably broke Instruct's patch), confirmed genuinely different code, genuinely compiles |
| `google__gson-1093` | Java | 0 | yes | all 5 `mvnd test` sub-invocations `Tests run: 1, Failures: 0, Errors: 0` — **exact match** (same counts, same line numbers) to original `test_output.txt`; 0 `BUILD FAILURE` |
| `javaparser__javaparser-4538` | Java | 0 | yes | `./mvnw clean install -DskipTests -am` + 2x `./mvnw test` all `BUILD SUCCESS`; nested `PreOrderIteratorTest`/`PostOrderIteratorTest` (added by the gold patch) actually discovered and run, `Tests run: 15/3/18/7` **exact match** to original |

Also independently re-verified the **excluded** `fmtlib__fmt-3863` (C++) genuinely fails under
`-e`: fresh-container `git apply` succeeds, `cmake --build` hits a real template-instantiation
compile error (`error: ambiguous template instantiation for 'struct fmt::v10::range_formatter…'`,
`gmake: *** [Makefile:381: ranges-test] Error 2`), strict rc=**2**, never reaches the test
section. Pre-existing baked binary `/testbed/build/bin/ranges-test` mtime **`Apr 26 2025`**
(matches image build date, i.e. genuinely never rebuilt), sha256 = **`18c58be90cda…`** — this
prefix is a **byte-for-byte match** to the exact hash cited in `AUDIT_NOTES_SET_E_BUG.md`,
independently re-derived from a brand-new container I spun up myself, not copy-pasted from the
audit doc. This corroborates the audit's own stated evidence is genuine, not fabricated, and
that the exclusion itself is correct (no over-removal on this row).

### 1b. Static log inspection (all remaining C++/Java rows — full coverage, no gaps left unchecked)
For the other 7 (`fmtlib__fmt-3248`, `fmtlib__fmt-3729`, `fmtlib__fmt-3901`, `apache__druid-15402`,
`google__gson-2024`, `google__gson-2134`, `projectlombok__lombok-3042`), I read the harness's own
`test_output.txt` (build section + test section) for each: all show a real compiler/linker
invocation (`Building CXX object …`, `Linking CXX executable …`, or Maven `BUILD SUCCESS`) with
matching `FAIL_TO_PASS` tests genuinely present and passing, zero suspicious signatures. One
false alarm from my own grep (`apache__druid-15402` matched `error:`) was manually inspected and
is a benign Maven offline-metadata-fetch **warning** ("failed to transfer … Original error:
Connect timed out", for an unused `junit-dep` artifact already cached in `~/.m2`), not a build
failure — `BUILD SUCCESS`, `Tests run: 1, Failures: 0, Errors: 0` on the real `FAIL_TO_PASS` test
`testCacheStrategy`.

**Result: 11/11 C++/Java resolved rows checked, zero additional false positives found beyond the
3 already excluded.** No under-removal.

## 2. Denominator honesty (3 independent angles, not just "trust denom_assert.txt")

- `wc -l results.jsonl` = 300; `len(set(instance_id))` = 300 (own Python re-parse, not the
  bundle's own script).
- **Set-equality, not just count-equality**: the pre-declared subset manifest
  `.worktrees/swemultilingual-v21-agent51/manifests/candidates/swemultilingual_full300_instance_ids_20260712.txt`
  (300 lines, 300 unique) is **exactly** the same *set* as the 300 `instance_id`s in
  `results.jsonl` (`manifest - results = {}`, `results - manifest = {}`) — this rules out a
  denominator that merely counts 300 but is secretly a different/swapped 300.
- `sha256sum -c SHA256SUMS` on the full bundle (13 files incl. `results.jsonl`, `calibration.md`,
  `AUDIT_NOTES_SET_E_BUG.md`, `serving/*`, `verdict_pack.tar.gz`): **all OK**, re-run by me at the
  end of this audit as a final integrity check.

## 3. resolved=70 arithmetic

`grep -c '"resolved": true' results.jsonl` = **70** (own re-count, not trusting `calibration.md`'s
stated headline). Per-language table sums exactly: resolved 7+5+12+6+9+6+10+13+2=**70**,
total 30+12+42+43+33+43+44+43+10=**300**. `70/300 = 0.233333…` = 23.33%, matches the claim exactly.
The 3 flipped rows carry both `resolved_original:true` and `set_e_audit_false_positive:true` —
traceable, not silently deleted.

## 4. Serving identity — :30001 = Coder

`serving/get_model_info_before.json` == `get_model_info_after.json` (identical sha256
`a2364930…`): `model_path=…/Qwen3-Coder-30B-A3B-Instruct`, matches `calibration.md`'s stated
endpoint `http://100.100.104.147:30001/v1` and the shared resource registry's documented recipe
("Coder-30B on cards 6,7 :30001").

## 5. Sanity check — is 23.33% plausible for Coder-30B on Multilingual?

Same model+scaffold scores **46.8% (234/500, zero set-e FPs, "SAFE")** on SWE-bench Verified
(Python-only) per the same `c49474b` audit. A drop to 23.33% cross-language is directionally
correct and the right order of magnitude: per-language spread runs Java 14.0% / PHP 14.0% (hardest)
up to C++ 41.7% / Rust 30.2% (easiest, small-N caveat on C++ n=12), a normal spread for a
30B-scale model that is comparatively Python/agentic-SWE-bench-optimized. `calibration.md` itself
explicitly **flags and forbids** comparing this 23.33% against the unrelated **73.4% gpt-5.5**
Multilingual number ("a different model … not a comparable anchor … must not be used as one") —
i.e. the bundle pre-empts exactly the "张冠李戴" mistake this project has been burned by before
(`project_bench_claimed_scores_audit`). No red flag in either direction.

## 6. Process gaps found (MINOR — do not change the verdict, disclosed for hygiene)

- **DECISIONS.md ledger gap**: `find . -iname DECISIONS.md | xargs grep -l "c49474b\|af190732\|set_e_audit\|stale-artifact"` returns **nothing**, anywhere in the repo (checked all worktrees). Per this
  project's own ledger-first convention, the set-e audit's 对账 was never recorded in any
  `DECISIONS.md`. This is a **documentation/process gap**, not evidence the number is fake — I
  independently re-derived the same 70/300 from the raw bundle myself rather than trusting the
  ledger's (non-existent) entry.
- **Stale raw-run summary files**: the *raw* run root (outside the git-tracked evidence worktree)
  still has `score_summary.json` / `score_summary_full300.json` showing the pre-audit **73 /
  0.243333** — these were generated 2026-07-12 (run completion), before the `c49474b` audit on
  2026-07-13, and were never regenerated. `cleanup_race_repair_summary.json` shows
  `repaired_rows: []` (clean, nothing to repair) so this isn't masking a repair problem — it's
  just an un-synced duplicate summary. The git-committed `calibration.md`/`results.jsonl` (which
  is what `SHA256SUMS` seals and what I independently re-verified) is correct; someone reading the
  wrong file on shared FS could see the debunked 73 number, so this should be regenerated for
  hygiene, but it does not affect the audited claim's correctness.

## 7. Cross-family (codex-pro) invocation

See identity-honesty disclosure above. Genuinely invoked, verified genuinely contended by other
concurrent sessions (documented via `ps -o etime,time`), did not return output within a fair
~9-minute window. Not used as a rubber stamp — if/when it returns, findings will be appended as a
dated addendum, not silently incorporated as if it had run instantly.

---

## Conclusion

Across 11/11 C++/Java resolved-row coverage (4 by fresh independent container `-e` reruns with
binary-freshness/hash proof, 7 by log inspection), a spot-check reconfirmation of one excluded FP
(byte-matching the audit's own cited hash), 3-way denominator honesty checks, exact resolved=70
arithmetic, confirmed stable Coder serving identity, and a plausibility check against the same
model's own Verified score — **I could not prove 23.33% (70/300) is FAKE.**

**Multilingual x Coder (qwen-code) = 70/300 = 23.33% — REAL.**

Two MINOR hygiene gaps disclosed (Section 6): no DECISIONS.md ledger entry for this audit anywhere
in the repo, and stale duplicate summary files on the raw run root. Neither affects the verdict.

— auditor B (Claude/Sonnet 5 executing; genuine `codex-pro`/gpt-5.6-sol invocation attempted and
disclosed, contended) · evidence branch `evidence/sweml-full300-147-20260713` @ base `c49474b`,
committed on top of auditor A's `7dde1ae`.
