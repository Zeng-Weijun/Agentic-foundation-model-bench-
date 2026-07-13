# Cross-family Auditor B sign-off — SWE-bench Multilingual × Qwen3-30B-A3B-Instruct-2507 (set -e re-adjudication)

- **Auditor:** identity-honest disclosure — the orchestrating harness for this task is a **Claude
  (Sonnet 5)** sub-agent. Per the "身份诚实" mandate, I did **not** impersonate Codex: I invoked a real
  local `codex-pro` session (`gpt-5.6-sol`, `reasoning.effort=ultra`) as an independent second-family
  read-only reviewer (see §5). The Mac was under heavy concurrent load (a dozen+ other `gpt-5.6-sol`
  sessions running on unrelated projects at invocation time — `ps aux` confirms), so per the task's own
  fallback rule ("多个并发 gpt-5.6-sol 抢 Mac 就串行/等或自己 Claude 做并标注") the **primary, complete**
  signature below is mine (Claude), done by hands-on fresh-container reproduction, not by trusting the
  audit's own notes; the **codex-pro** run is a genuinely independent supplementary cross-check that
  converged on the same facts for everything it reached before this report was finalized (§5).
- **Date (UTC):** 2026-07-13/14
- **Run under audit:** `sweml_instruct2507_qwencode_full300_147_20260712T090033Z`
- **Bundle:** `experiments/runs/sweml_instruct2507_full300_147/` (evidence branch `evidence/sweml-full300-147-20260713`)
- **Audit commit re-checked:** `c49474b` ("set -e audit: remove 7 stale-artifact false positives from Multilingual qwencode bundles")
- **Claim under audit:** set-e re-adjudicated score **9.33 % (28 / 300)**, i.e. original buggy-harness
  **32 → 28** after removing 4 stale-artifact false positives (`fmtlib__fmt-2457`, `fmtlib__fmt-2310`,
  `nlohmann__json-4237` [C++], `javaparser__javaparser-4561` [Java]).
- **Mandate:** try to prove 9.33 % (28/300) is FAKE (missed-exclusion among the 28 kept / denominator
  shrink / serving-identity swap / arithmetic error). Could not break it → **REAL**.
- **Note on `af190732`:** the task brief cites commit `af190732` as the source of the "bash -e strict
  重判" result. That hash does **not** resolve to any git object in this repo — not by local
  `git cat-file`, not after `git fetch origin` from `dev` (full internet), not as a text string
  anywhere in commit messages, `_coordination/`, or tracked `*.md` files (checked across all branches).
  This is a **discrepancy in the task briefing**, flagged for the record. It does not change the
  verdict: the identical substantive evidence (31-task `set -e` rerun, per-instance sha256 hashes,
  32→28 correction) lives in the **valid, pushed** commit `c49474b`, which I independently re-verified
  from scratch below rather than trusting either hash.

## VERDICT: **REAL** — could not break it.

## Method (independent, fresh-container reproduction — not trace-reading)

For every instance I checked below I started a **brand-new container** from the exact cached instance
image on the KVM eval pod (`env-kvm-57740737-bzw56...`, docker 26.1.3, `--network=none`), applied the
recorded agent `patch.diff` with `git apply` exactly as the harness does, then ran the harness's own
`eval.sh` **byte-for-byte** except `set -uxo pipefail` → `set -euxo pipefail`. I captured: apply result,
sha256 of the compiled test artifact (binary/`.class`) **before my own run** and **after**, whether the
`>>>>> Start/End Test Output` markers were reached, and the script's exit code. All containers were
`docker rm -f`'d after use; nothing in the repo was modified.

## 1. Full census (not a 3-4 sample) of the 6 C/C++/Java rows kept "resolved" in the 28 — all genuine

Independent recount of `results.jsonl`: **28** `resolved:true` rows. Cross-referenced against known
repo→language mapping, exactly **6** of the 28 are in the bug's risk class (C/C++/Java); the other 22
are Go/Rust/Ruby/PHP/JS/TS (test command self-rebuilds on invocation, no pre-baked artifact to fall
back to). I reran **all 6**, not just a 3-4 sample:

| instance | lang | strict rc | reached test section | artifact sha256 before → after | result |
|---|---|---:|---|---|---|
| `fmtlib__fmt-3729` | C++ | **0** | yes | `8f0c20a2…` → `5d65a985…` **changed** | ctest: 13/13 passed (incl. FAIL_TO_PASS `std_test.path`) |
| `micropython__micropython-13039` | C | 1\* | yes | `e1abbc1e…` → `3bfdff22…` **changed** | run-tests.py: 15/15 passed |
| `redis__redis-9733` | C | **0** | yes | `e3afb51f…` → `a987f3d6…` **changed** (`make distclean && make`) | `\o/ All tests passed`, incl. new `COMMAND GETKEYS EVAL {with,without} keys` |
| `google__gson-1093` | Java | **0** | yes | Maven: `Changes detected — recompiling the module!` ×2/invocation | `BUILD SUCCESS` × 5/5 invocations, 0 failures; decompiled `.class` (javap) confirms `testNonFiniteDoublesWhenLenient`/`testNonFiniteBoxedDoublesWhenLenient` bytecode present |
| `google__gson-2024` | Java | **0** | yes | Maven: `Changes detected — recompiling the module!` ×3/invocation | `BUILD SUCCESS` × 3/3, 0 failures |
| `google__gson-2134` | Java | **0** | yes | Maven: 1st invocation `Changes detected`; 2nd/3rd `Nothing to compile` (correctly reusing *this run's own* fresh compile, not the image bake) | `BUILD SUCCESS` × 3/3, 0 failures |

\* `micropython-13039`'s rc=1 is **not** a grading-relevant failure: it comes from the eval.sh
template's own bug — the final cleanup line `git checkout … tests/basics/slice_indices.py` runs from
`cwd=/testbed/tests` (never `cd`'d back after `cd tests` for the test run), so git looks for a
nonexistent `tests/tests/basics/...` path (`pathspec … did not match any file(s)`). This happens
**strictly after** the `>>>>> End Test Output` marker that the SWE-bench log parser scores from — the
15/15 test pass and the binary-hash change both happened cleanly beforehand. Confirmed benign; does not
affect the verdict.

**Cross-validation:** `fmt-3729` before-hash, `micropython-13039` before/after-hash, and `fmt-2457`
before/after-hash (see §2) are **byte-identical** to the independently-measured hashes in Auditor A's
already-pushed signoff (`5c5b144`) and to `codex-pro`'s own from-scratch measurements (§5) — a 3-4-way
convergent check, not just "trust the same commit". The one hash that *differs* from Auditor A
(`redis-9733` after-rebuild: mine `a987f3d6…` vs A's `d19354c4…`) is explained, not concerning: Redis's
build embeds a generated `release.h` build-id (hostname+timestamp) via `mkreleasehdr.sh`, so two
genuinely-fresh independent rebuilds of the *same* source are expected to hash differently — this is
actually corroborating evidence of "genuinely rebuilt each time" (a truly stale/cached binary would
hash identically across reruns, matching the pre-existing baseline; ours don't, and neither matches the
baseline `e3afb51f…`).

## 2. Negative controls: 2 of the 4 *removed* rows independently reproduced as genuine false positives

To validate that my rerun methodology actually detects the bug (not just rubber-stamping "REAL" no
matter what), I reran two already-excluded rows myself:

| instance | lang | strict rc | mechanism observed |
|---|---|---:|---|
| `fmtlib__fmt-2457` | C++ | 2 (abort) | genuine compile error `class …basic_format_context<…>' has no member named 'format_specs'`; binary sha256 **`9ba87169…` → `9ba87169…` identical** (zero rebuild) — matches AUDIT_NOTES's recorded hash and Auditor A's exactly |
| `javaparser__javaparser-4561` | Java | 1 (abort) | `git apply` of the new gold test file failed: `already exists in working directory` — the file was already present in this image (baked in from an earlier warm-up/rebuild of this "mavenfix"-tagged offline image), so under buggy `-uxo pipefail` the script would fall through to grading against a pre-existing stale artifact |

Both abort under `-e` before the graded section, confirming the exclusions are correct. (Note: my
`javaparser-4561` abort point — `git apply` conflict on a pre-existing file — differs in mechanism
detail from AUDIT_NOTES's stated "COMPILATION ERROR: cannot find symbol", which is plausible given this
specific image has clearly been rebuilt/reused multiple times in the last 2 days for the offline-p0
Java path; either way the script aborts pre-test under `-e`, so the exclusion conclusion is unaffected.)

## 3. Denominator = 300, honest; 28 = correct arithmetic

- `results.jsonl`: **300** rows (`wc -l`), **300** unique `instance_id` (independent Python parse, 0
  duplicates).
- `denom_assert.txt`: `rows==declared AND unique==rows ⇒ PASS`; `SHA256SUMS` verified with
  `sha256sum -c` (13/13 OK) — `results.jsonl` matches its sealed hash, i.e. not edited after sealing.
- Independent recount: **28** `resolved:true`. Per-language table in `calibration.md` sums to 28
  resolved / 300 total exactly (`C 2/30, C++ 1/12, Go 6/42, Java 3/43, JS 2/33, PHP 1/43, Ruby 6/44,
  Rust 6/43, TS 1/10`).
- `agent_status` × `resolved` cross-tab: `(patch,False)=192, (no_patch,False)=80, (patch,True)=28`,
  sums to 300; **zero** `no_patch`-but-`resolved` anomalies — the 80 instances where the agent produced
  no patch are honestly counted as unresolved in the denominator, not dropped.
- The **same 300** `instance_id` set is used for the sibling Coder run (`sweml_coder_full300_147/`) —
  set equality confirmed by independent Python diff (0 symmetric difference) — i.e. this is not a
  cherry-picked subset relabeled "full 300" for one model only.

## 4. Serving identity = Instruct-2507, not Coder

- `serving/IDENTITY_SUMMARY.json` + `get_model_info_{before,after}.json` (byte-identical, confirmed via
  `SHA256SUMS`): `model_path=/mnt/…/models/Qwen3-30B-A3B-Instruct-2507`, `architectures:
  ["Qwen3MoeForCausalLM"]`, `sglang=0.5.13`, `seed=61643818`, `before_equals_after: true`.
  `serving/IDENTITY_SUMMARY.json` was committed in `39fec44` (the original v6 evidence commit) — **not**
  touched by the `c49474b` set-e audit diff, so it predates and is independent of the correction being
  audited.
- Confirmed on disk: `/mnt/…/models/Qwen3-30B-A3B-Instruct-2507/` exists (dated May 28 2026,
  `config.json` → `qwen3_moe`/`Qwen3MoeForCausalLM`) and is a **physically distinct directory** from
  `/mnt/…/models/Qwen3-Coder-30B-A3B-Instruct/` — not a symlink alias or relabel.
- Sibling Coder run's own `calibration.md` independently states
  `model_path=…/Qwen3-Coder-30B-A3B-Instruct`, different `seed=484925000` — two different weight dirs,
  two different seeds; the Instruct run was not accidentally serving Coder weights.

## 5. Sanity: 9.33 % (Instruct) < Coder, and codex-pro cross-check

- Coder sibling (`sweml_coder_full300_147/calibration.md`, independently recomputed): **70/300 =
  23.33 %**. Instruct 9.33 % is materially lower, the expected direction (general-instruct vs a
  code-specialised checkpoint on SWE-style multilingual tasks).
- Per-language, Coder ≥ Instruct in **all 9/9 languages** (C 7>2, C++ 5>1, Go 12>6, Java 6>3, JS 9>2,
  PHP 6>1, Ruby 10>6, Rust 13>6, TS 2>1) — a consistent per-cell pattern, not just an aggregate
  coincidence.
- **codex-pro (`gpt-5.6-sol`, `reasoning.effort=ultra`)**, launched genuinely and independently (own SSH
  session, own container reruns, no access to my findings), was still in progress at report time due to
  heavy Mac-wide contention (10+ concurrent unrelated `gpt-5.6-sol` sessions observed via `ps aux`) and
  `ultra` reasoning latency. Before finalizing it had **independently reproduced, from a cold start**:
  `ROWS 300 / UNIQUE 300 / DUPLICATES [] / RESOLVED_TRUE 28`, the exact same 28 `instance_id` list, the
  same C/C++/Java risk-class identification (fmt-3729, micropython-13039, redis-9733, gson-1093/2024/2134),
  and — via its own fresh `docker run --rm --network none` probes — **byte-identical baseline sha256
  hashes** to mine for `fmt-3729` (`8f0c20a2…`), `micropython-13039` (`e1abbc1e…`), `redis-9733`
  (`e3afb51f…`), and `gson-1093`'s `JsonWriterTest.class` (`871458e4…`). This is a genuine second-family
  data point converging on the same facts, not a rubber stamp; full transcript at
  `/tmp/claude-501/.../scratchpad/audit_b/codex_pro_output.log` (local to the auditing session) if the
  raw log is wanted.

## Adversarial attempts and why each failed

- **Missed exclusion among the 28** → refuted: full census (6/6, not a 3-4 sample) of every C/C++/Java
  retained row independently rebuilds fresh and passes.
- **Removed too many** (wrongly dropped genuine passes) → refuted for 2/4 spot-checked removed rows
  (both independently abort pre-test under `-e`, one with a hash match to two other independent
  auditors).
- **Denominator shrinkage** → refuted: 300 invariant, unique==rows==300, SHA256-sealed, identical
  instance-id set across sibling Coder/Instruct runs.
- **Serving-identity swap** → refuted: model_path, architecture, and on-disk directory all confirm
  Instruct-2507, distinct from the Coder run's own model_path/seed.
- **Score sanity** → refuted: Instruct < Coder in the aggregate and in every one of 9/9 languages.

**Conclusion: 9.33 % (28/300) for SWE-bench Multilingual × Qwen3-30B-A3B-Instruct-2507 is REAL.**
— Auditor B (Claude Sonnet 5, primary; codex-pro gpt-5.6-sol ultra, genuinely invoked, partial
independent corroboration under Mac contention — see §5 for exact scope).
