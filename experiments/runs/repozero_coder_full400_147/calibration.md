# Calibration -- how to read 98/400 = 24.5%

## What was measured
- **Bench**: RepoZero **Py2JS OFFICIAL 400** (`valid_ids`). One base image `repoarena-new`
  carries all task data (per-case dataset + oracle executable + 60-cap testcase samples).
  The task: re-implement a Python library's CLI behavior in **JavaScript** (`.mjs`) so its
  stdout matches the reference **oracle executable** across every testcase sample.
- **Agent (Path A)**: `qwen-code` native CLI, in-container, `--max-session-turns 40`,
  driving a self-hosted model. `workers=4`, per-case container isolation, resumable.
- **Model**: `Qwen/Qwen3-Coder-30B-A3B-Instruct` @ `http://100.100.104.147:30001/v1` (sglang 0.5.13).
- **Judge (RepoZero official `eval_case`)**: for each case, run `oracle_executable ARGS`
  and `node ENTRY.mjs ARGS` for EVERY sample; compare **normalized-line** stdout equality.
  `all_pass = (passed == total and total > 0)`; `reward = int(all_pass)`. **No model in the judge.**

## The number
- **Headline: 98 / 400 = 24.5% all_pass** (eval_timeout **10s**, the value the run used).
  Denominator = **400, not shrunk**.
- 98 all_pass (reward=1), 302 not (reward=0). Per-library table: `by_lang.md`. Rows: `results.jsonl`.
- **Three calibers (all disclosed — see `AUDIT_NOTES.md`):**

  | caliber | eval timeout | eval node | all_pass | rate |
  |---|---|---|---:|---:|
  | committed headline (the run) | 10s | qwen node v20.20.2 | **98/400** | **24.50%** |
  | **RepoZero official** | **5s** | qwen node v20.20.2 | **95/400** | **23.75%** |
  | node-image floor (A) | 10s | image node v18.19.1 | 97/400 | 24.25% |

  24.5% (10s) is **REAL** (A+B dual-sign). The official **5s** value
  (`rejudge_official5s.json`) is the stricter, more faithful number and can only be
  ≤ 24.5% (5s is a subset of what 10s admits). See the two subsections below.

## Is the number real? (denominator integrity + crash cases)
- `results.jsonl` has **400 unique** cases (no dup, no missing) -- see `denom_assert.txt`.
- **4** cases (`rsa/test5, rsa/test2, rsa/test17, mpmath/test14`) crashed **during the judge
  step** (driver hit a 10s exec timeout inside `eval_case`, so it never wrote `summary.json`;
  the orchestrator recorded them as `all_pass=false`, error `no summary.json`). They were
  **conservatively counted as fails** in the 400 denominator (never over-counts passes).
- Those 4 were **re-judged serving-free** against their already-generated `.mjs`
  (`scripts/rejudge_missing4.py` -> `rejudge_missing4.json`): **0 / 4 recovered passes**. Two
  were ORACLE-side timeouts (RSA keygen for `--bits 3178`/`4728` legitimately exceeds 10s, so
  those cases cannot score all_pass under this harness regardless of the agent), one hung the
  agent's own `.mjs`, one graded cleanly as 0/16. **=> 98/400 is airtight.**

## Anchor -- BAND ONLY, do NOT claim alignment
- The RepoZero arXiv anchor **54.70% +- 2.55** is **Mini-SWE-Agent + Claude-4.6-Sonnet**.
- This run is **qwen-code (native scaffold, NOT Mini-SWE-Agent) + Qwen3-Coder-30B-A3B-Instruct
  (NOT Claude-4.6-Sonnet)**. **Both the scaffold AND the model differ.** This is therefore a
  **NEW measurement with no matching official cell** -- use 54.70% only as a coarse ruler /
  sanity band, **never** as a same-model same-scaffold comparison. The 24.5% vs 54.70% gap
  reflects a smaller open 30B model + a different agent scaffold, not a harness defect (the
  grader is proven real: reference `.mjs` -> all_pass=1, empty `.mjs` -> all_pass=0; and every
  `judge.result.json` shows concrete oracle-vs-node stdout diffs).

## Harness caveat #1 -- eval timeout: run used 10s, RepoZero official is 5s (disclosed)
- The run used `eval_timeout = 10s` per sample (driver + orchestrator argparse default).
  **RepoZero's own judge hardcodes `timeout=5`** (`evaluate/eval_py2js_docker.py` lines 52 & 59).
  10s is **2x looser** and can only ADMIT passes the official 5s would reject, so **98/400 is an
  UPPER bound relative to the official 5s harness** -- a real, disclosed slack in the agent's favor.
- **Official 5s re-judge of all 400 already-generated `.mjs` (serving-free): 95/400
  = 23.75%** (`scripts/rejudge_official5s.py` -> `rejudge_official5s.json`; same qwen node
  v20, only the timeout changed 10s->5s; parallel then serial contention-free re-verify of any
  boundary flip; conservative -- a >5s sample counts the case as fail). Delta = **-3 cases**,
  all compute-heavy `networkx`/`deepdiff` samples that legitimately exceed 5s single-threaded
  (serial-verified: pass@10s, timeout@5s) -- and in all 3 the >5s side is the **ORACLE
  (reference executable)**, not the agent's node, i.e. the same slow-reference class as the
  `rsa` oracle-timeout caveat below, NOT an agent-JS failure. 3 further Phase-1 flips were
  parallel-contention artifacts and correctly kept as passes; **0 anomalies** (5s passes are a
  clean subset of 10s passes).
- For 2 `rsa` cases the **oracle itself** exceeds even 10s (large-key RSA keygen), so they are
  unscoreable-as-all_pass under either timeout regardless of the agent, and counted as fail.
  Excluding just those 2 gives 98/398 = 24.6% -- immaterial. Reported denominator stays **400**.

## Harness caveat #2 -- eval node: qwen node v20, not the image node (disclosed, 0.25pp)
- The judge's `node <entry>.mjs` runs on the **mounted qwen node v20.20.2 (OpenSSL 3.0.19)**, NOT
  the image's native node v18.19.1 (OpenSSL 3.0.13): `start_container` puts the qwen tree first on
  the container `PATH`, and `dexec_plain` (eval) does not override it. (The driver docstring
  previously claimed the image node was used -- **corrected** in this bundle; see `AUDIT_NOTES.md`.)
- **Impact 0.25pp:** re-scoring the 10 crypto/RSA `all_pass` cases under image node-18 leaves
  **9/10 unchanged**; only `rsa/test11` flips (node-18 rejects a legacy SHA-1 digest name node-20
  accepts) -> node-image floor **97/400 = 24.25%**. Direction is defensible (node-20 faithfully
  reproduces the Python oracle's legacy SHA-1), so this is a coarse floor, not a correction.
