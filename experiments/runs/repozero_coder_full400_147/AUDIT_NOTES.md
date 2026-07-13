# AUDIT NOTES — RepoZero Py2JS full400 × Qwen3-Coder-30B-A3B-Instruct × qwen-code (Path A)

Two independent blind audits (A and B) each judged the headline **98/400 = 24.5%
all_pass REAL**, and each surfaced methodology-disclosure gaps that do **not**
overturn REAL but must be disclosed. This file records the dual-sign verdict, the
methods, and every gap — plus the **official 5s-timeout re-judge** and the
**docstring correction** commissioned in response.

**Bottom line (honest, three calibers):**

| caliber | eval timeout | eval node | all_pass | rate | status |
|---|---|---|---|---:|---|
| committed headline | 10s | qwen node v20.20.2 | **98/400** | **24.50%** | REAL (A+B dual-sign; not overturned) |
| **RepoZero official** | **5s** | qwen node v20.20.2 | **95/400** | **23.75%** | re-judge (this file, §2) — stricter, official timeout |
| node-image floor | 10s | image node v18.19.1 | 97/400 | 24.25% | A's node-seam re-score (§3) — 0.25pp |

The **24.5% (10s) figure remains REAL** — A and B could not overturn it. The
official 5s value is a **stricter, more faithful** number reported alongside it,
not a replacement; it can only be ≤ 24.5% because 5s is a subset of what 10s admits.

---

## 1. Dual-sign REAL verdict — what A and B each did

**Verdict (both, independently): 98/400 = 24.5% all_pass is REAL.** The judge is
serving-free (`eval_case`: oracle-executable stdout vs `node <entry>.mjs` stdout,
normalized-line equality across every testcase sample → per-case `all_pass`); no
model participates in scoring.

- **Auditor A** — independently started fresh containers and re-ran the judge on
  **10 cases** against their already-generated `.mjs`: **7 reproduced all_pass
  with exact-byte-identical oracle-vs-node output, 3 reproduced as genuine fails**
  (concrete oracle-vs-node stdout diffs). Conclusion: the grader is real and the
  per-case verdicts reproduce.
- **Auditor B** — re-ran **3 cases** in fresh containers AND **read RepoZero's own
  judging source** (`evaluate/eval_py2js_docker.py`) line-by-line, confirming the
  driver's `eval_case` is **byte-for-byte the same comparison** (same `"".join(line.split())`
  normalization, same `rc==0 && len>0 && equality` rule). B also **verified the
  commit locally on Mac** (0ccf90d).
- **Both** confirmed: denominator = **400** (no dup / no missing — `denom_assert.txt`);
  serving is the **real Coder** (`serving/identity_summary.md`, `:30001`); the agent
  really drove `:30001` (per-case `qwen.stdout.jsonl` trajectories); the image
  **digest is real** (`sha256:e01d5505…`, `serving/repoarena_image_inspect.json`).
- The **4 judge-step crash cases** (`rsa/test5, rsa/test2, rsa/test17, mpmath/test14`)
  were re-judged serving-free → **0/4 recovered passes** (`rejudge_missing4.json`),
  so 98 is airtight and the denominator honestly stays 400.

---

## 2. ★ MAJOR (Auditor B): eval timeout 10s vs official 5s — and the 5s re-judge

**Gap.** The run used `--eval-timeout` **10s** (driver `main` argparse default =10,
orchestrator argparse default =10 → passed through to every case). But RepoZero's
own judge **hardcodes `timeout=5`** in `evaluate/eval_py2js_docker.py` (lines 52 &
59, both the Python-oracle and the Node subprocess). **10s is 2× looser than
official** and can only **admit** passes the official 5s would reject (any sample
whose oracle/node runs 5–10 s). Therefore **98/400 is an upper bound relative to
the official 5s harness** — a real, disclosed methodological slack in the agent's
favor.

**Fix — official 5s re-judge of all 400 already-generated `.mjs` (serving-free).**
`scripts/rejudge_official5s.py` re-runs RepoZero's own `eval_case` on every one of
the 400 cases' committed `.mjs`, isolating **only** the eval-timeout variable
(10s→5s), on the **same eval node the run actually used** (qwen v20 — see §3), with
a **conservative rule**: any sample whose oracle/node exceeds 5s (TimeoutExpired) →
that case is `all_pass=False` (matching official — a timed-out sample cannot match).
For rigor at the timeout boundary, a case that was all_pass@10s but not
all_pass@5s in the parallel phase is **re-verified serially (contention-free)** at
5s and 10s, to separate a genuine >5s per-sample cost from a scheduling artifact.

**Result — official 5s caliber = 95/400 = 23.75%**
(vs 98/400 = 24.50% at 10s; Δ = **−3 cases**). Per-case 10s→5s rows and the
headline are in **`rejudge_official5s.json`**.
- 6 cases flipped pass@10s→fail@5s in the parallel phase; serial contention-free
  re-verify resolved each one cleanly:
- **Genuine 5s-timeout (3, stay fail): `networkx/test5`, `deepdiff/test3`,
  `networkx/test15`.** Each has ≥1 testcase sample that legitimately runs >5s even
  single-threaded — serial: **passes at 10s, times out at 5s** (`rejudge_official5s.json`
  records the per-case verdicts). Note: for all three the >5s side is the **oracle
  (the compiled reference executable)**, not the agent's `node` — i.e. the reference
  itself is slow on these heavy graph/diff inputs, so the case is unscoreable-as-all_pass
  under a 5s reference timeout *regardless of the agent's JS*. This is the **same class**
  as the disclosed `rsa` oracle-timeout cases (§4 / calibration.md): the −3 official-5s
  penalty is slow-reference-oracle, **not** an agent-JS failure. (RepoZero's official
  `eval_py2js_docker.py` times the raw `python <src>` at 5s where this driver times the
  compiled oracle executable; both are the reference side, and a >5s reference cannot
  produce a matched sample under a 5s wall.)
- **Parallel-contention artifacts (3, kept as PASS): `networkx/test3`,
  `networkx/test2`, `networkx/test1`.** Same compute-heavy family but per-sample
  cost sits just under 5s; the 8-way Phase-1 pushed them past the wall, but the
  serial 5s re-run **passes** — so they are correctly kept as passes (the −3 is
  **not** inflated by our own concurrency).
- **Anomalies (fail@10s→pass@5s): none (0)** — confirms determinism: every 5s pass
  is also a 10s pass, i.e. the 5s pass-set is a clean subset of the 10s pass-set, as
  a stricter timeout must be. **Investigate: none (0).**

All three genuine flips (and all three contention flips) are the compute-heavy
`networkx` graph algorithms + one `deepdiff` structural diff — the only library
family in the 400 whose per-sample runtime brushes the 5s wall. Everything else
(string/encoding/crypto/math) runs in well under a second and is timeout-insensitive.
Net: the official 5s harness costs exactly **3** genuine cases → **95/400 = 23.75%**.
24.5% (10s) stays the REAL headline; 23.75% is the stricter official-timeout caliber.

---

## 3. ★ (Auditor A) node seam — eval used the mounted qwen node, not the image node

**Gap.** The driver docstring claimed *"Eval always uses the IMAGE's native node
(not the mounted qwen node) for scoring fidelity."* This is **FALSE**.
`start_container` sets the container `PATH` to the mounted qwen tree
(`container_env`: `PATH="/opt/qwen-native/.npm-root/node_modules/node/bin:…"`), and
`dexec_plain` runs `docker exec` **without** overriding `PATH`, so the judge's
`node <entry>.mjs` resolves to the **mounted qwen node**, not the image node.

**Empirically confirmed (this audit):**
```
image native node    = /usr/bin/node                                  v18.19.1  (OpenSSL 3.0.13)
qwen-mounted node    = /opt/qwen-native/.npm-root/.../node/bin/node    v20.20.2  (OpenSSL 3.0.19)
container started as start_container does, then `docker exec … node`  → v20.20.2  ← eval actually used this
```

**Impact (Auditor A quantified) — immaterial, 0.25pp.** A re-scored the 10
crypto/RSA `all_pass` cases under the **image node-18**: **9/10 unchanged**; only
**`rsa/test11`** flips — node-18 **rejects** a legacy SHA-1 digest name that
node-20 **accepts**. So the worst-case node-image floor is **97/400 = 24.25%**
(a 0.25 pp seam). **Direction is defensible either way:** node-20 (the run's node)
faithfully reproduces the Python oracle's own legacy SHA-1 behavior, so accepting
it is arguably *more* correct; node-18 is the stricter/official-image interpretation.
Because it is a single-case 0.25pp effect, a full node-18 re-run was **not**
warranted (A verified it immaterial); the honest floor is reported as 97/400.

The same "node 18" mislabel also appears in the **agent prompt** (`build_prompt`
tells the agent *"native Node.js 18 is on PATH"*, echoed in every frozen
`verdict/samples/*/agent/prompt.txt`). In fact the agent's `node` during
development was also the mounted **v20**. The prompt text is left verbatim (it is
part of the frozen run record) but a code comment now flags the discrepancy.

**Docstring corrected** in `scripts/repozero_qwencode_driver.py`: the module
docstring (former L40–41) and the `dexec_plain` docstring now state that eval runs
on the mounted qwen node **v20.20.2**, not the image node **v18.19.1**, with the
0.25pp seam noted; a `build_prompt` comment flags the same node-label discrepancy.
(No functional change — the run's numbers are unaffected and the emitted prompt is
unchanged; only the false claims are annotated/removed.)

**Note on calibers.** The official-5s re-judge in §2 keeps the **same qwen node
v20** as the run, so it isolates *only* the timeout. The strictest conceivable
caliber (5s **and** image node-18) is bounded above by min(95, 97) and
is likewise immaterial to any conclusion; it was not separately computed
(node seam already shown to move ≤1 case).

---

## 4. MINOR gaps (disclosed, no score impact)

- **`rsa/test5` crash-narrative sample mismatch.** `calibration.md` / the commit
  narrated the crash as oracle `--bits 3178`. That arg is what the **single-container
  re-judge** (`rejudge_missing4.py`, no contention) hit. In the **original 4-worker
  run**, the case actually tripped the 10s wall on `--bits 2048` under concurrency
  slowdown (CPU contention across 4 parallel RSA keygens made a normally-sub-10s
  keygen exceed the wall). Both are genuine timeouts and both keep the case a fail,
  so the **verdict is unchanged**; only the illustrative sample differs. Large-key
  RSA keygen is inherently >5–10s, so these `rsa` cases are unscoreable-as-all_pass
  under either timeout regardless of the agent.
- **Grader positive/negative provenance not annotated.** The grader-realness proof
  (reference `.mjs` → all_pass=1, empty `.mjs` → all_pass=0) drew its known-good
  reference from a prior `base58-test1` smoke run; the source path was not written
  next to the grader artifacts. The proof itself stands (discrimination is shown);
  only the provenance annotation was missing.

## 5. Open / unverifiable (disclosed)

- **Serving process-level uptime not closed-loop.** The auditors could confirm
  serving identity and zero application-level anomalies (every case's
  `qwen.stdout.jsonl` shows real assistant/tool interaction with the `:30001`
  Coder, and `serving/*_after.json` capture identity after the run), but **could
  not SSH the serving worker** to prove process-level uptime across the full run.
  This is an application-level confirmation, not a process-level one — flagged as
  a residual gap, not a defect in the measured 98/400.

---

## 6. Reproduce

```bash
# official 5s re-judge (serving-free, deterministic; ~80 min @ 8 workers -- Phase-1
# 400 cases ~33 min, then Phase-2 serial contention-free re-verify of the boundary
# flips (heavy networkx/deepdiff 10s re-runs) dominates the rest):
cd .../agentic-foundation-model-bench/repozero_pathA
python3 rejudge_official5s.py 8          # -> runs/<run>/rejudge_official5s.json

# node seam (one-shot proof the eval node is qwen v20, not image v18):
docker run --rm --pull=never IMG node --version                       # v18.19.1 (image)
docker run -d --name t -e PATH=/opt/qwen-native/.npm-root/node_modules/node/bin:... \
  -v QWEN_ROOT:/opt/qwen-native/.npm-root:ro IMG tail -f /dev/null
docker exec t node --version                                          # v20.20.2 (what eval uses)
```
