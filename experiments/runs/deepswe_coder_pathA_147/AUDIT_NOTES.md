# AUDIT_NOTES -- DeepSWE x Coder x qwen-code (Path A) 0/113: dual-sign REAL + judging-bug disclosure

**TL;DR.** Two independent blind auditors (A = general, B = codex-reviewer) both conclude the score is
**REAL**: `resolved = 0` is a genuine agent-capability failure, not a scoring/judging bug. Headline
**0 / 113 = 0.00%**, valid-only **0 / 106 = 0.00%**. During the audit both found that the bundle's own
judging pipeline carried **undisclosed bugs**; this file discloses them in full. The most important one
(NO_PROXY pollution) was **under-counting gold_valid** (102 instead of 106) -- it wrongly failed 4 *gold*
solutions, so fixing it **raises** the valid denominator but **does not change the 0** (the agent still
scores 0 on those tasks in a clean env). None of the bugs masks an agent solve.

This is an **evidence-quality correction, not a score reversal.** The 0 is not overturnable: A+B cannot
break it.

---

## 1. Dual-sign REAL verdict and each auditor's method

### Auditor A (general) -- independent clean-env re-run from scratch
A did **not** call the bundle's driver. A wrote its own re-verify harness
(`deepswe_pathA/runs/audit2_independent/audit2_verify.sh`) that: `unset http_proxy https_proxy HTTP_PROXY
HTTPS_PROXY`, does its own `docker run` **without** the driver's polluting `container_env`, re-activates
`/opt/venv` when present, applies the gold or the recorded agent patch, and runs the task's real `test.sh`.
Coverage and result (logs in `deepswe_pathA/runs/audit2_independent/`):
- **gold spot-checks: 12/12 = reward 1** across go/python/typescript/rust/javascript
  (`batch1.log`: bandit, aiomonitor, fastapi-implicit-head-options, abs-module-cache-flags, kea, fd, yjs, httpx-multipart, ...; `broken.log`: the 4 flips).
- **agent re-verify: all reward 0** -- 15 valid-spot tasks (`batch1.log` igel/aiomonitor/abs = 0; `validspot.log`
  actionlint/claude-code-by-agents/boa = 0) plus **4 lock-stripped** tasks (`filt.log`, see bug #2) = all 0.
- **16 None** (agent produced no applicable patch): the original in-tree judging already gave reward 0.
- **the 4 NO_PROXY victims: gold = 1 in clean env** (`broken.log`; see bug #1).
- **Conclusion:** A's clean env is strictly **more lenient** to the agent than the bundle driver (no proxy
  pollution, no atomic-apply drops) yet the agent still resolves **0** -> **0 is a reliable upper bound.**

### Auditor B (codex-reviewer) -- hand-reproduction
B hand-reproduced representative failures at the source level:
- `actionlint-action-pinning-lint`: the agent's Go patch **fails to compile** (`undefined: NewRuleActionPinning`)
  -> the new tests can never pass -> `agent_reward=0` is a genuine capability failure. (A's `validspot.log`
  independently shows actionlint agent reward=0: Baseline exit 1 / New tests exit 1.)
- `numba-stencil-boundary-modes`: corroborated as a genuine miss.
- **Conclusion:** the 0 is genuine, not a judging artifact.

Both auditors independently reach the same verdict: **0/113 REAL.**

---

## 2. The 5 judging bugs / caveats (full disclosure)

### Bug 1 -- NO_PROXY judging pollution (most severe; corrected here)
`deepswe_qwencode_driver.py :: container_env()` (~L179-201) builds `NO_PROXY`/`no_proxy` from
`base_host = 100.100.104.147` (the sglang serving IP parsed from `--openai-base-url`) **plus the
`100.100.0.0/16` CIDR**, and `dexec()` injects that env into the container that runs the verifier.
The httpx baseline regression suite's `test_get_environment_proxies` asserts `proxies == {}` when no proxy
is configured, but with those values present it reads a proxy mapping for `all://100.100.104.147` and
**fails** -> the whole baseline goes red -> **`gold_reward=0` false-red**. This wrongly binned httpx-family
(and happy-dom) *gold* solutions as `gold_broken`.

- **Evidence (code):** `container_env()` no_proxy list includes `"100.100.0.0/16"` and `base_host`, returned as
  `"NO_PROXY": no_proxy, "no_proxy": no_proxy`.
- **Evidence (clean-env re-verify):** `deepswe_pathA/runs/audit2_independent/broken.log` -- with proxy vars
  unset and no `container_env` injection, these 4 reach **gold reward=1**:
  - `httpx-multipart-response-parsing` [python] -- gold: `1272 passed ... Baseline exit 0 / 122 passed New exit 0 -> reward=1`
  - `httpx-streaming-json-iteration` [python] -- gold: `1411 passed ... Baseline exit 0 / 108 passed -> reward=1`
  - `httpx-deterministic-cookie-store` [typescript] -- gold: `1285 passed ... Baseline exit 0 / 115 passed -> reward=1`
  - `happy-dom-abort-pending-body-reads` [typescript] -- gold: `163 passed Baseline exit 0 / 19 passed -> reward=1`
- **Correction applied:** these 4 moved `gold_broken -> gold_valid`. **gold_valid 102 -> 106, gold_broken 11 -> 7.**
- **Score impact: none.** In the same clean env the **agent** still scores **0** on all 4 (genuine, distinct
  failures -- e.g. httpx-multipart agent `84 failed`, httpx-deterministic-cookie-store agent
  `ModuleNotFoundError: httpx._cookies`, happy-dom agent `14 failed`), so the bug only ever hit tasks the
  agent could not solve. Headline **0/113** and valid-only **0/106** are both unchanged at 0.00%.
- **Note on mechanism:** the 3 httpx tasks are the clean NO_PROXY signature (proxy-env-sensitive baseline test);
  `happy-dom-abort-pending-body-reads` recovers under the same clean-env re-verify (driver-env-injection
  sensitive) and is reclassified on the same empirical basis (gold=1 in clean env). `httpx-deterministic-cookie-store`
  keeps the bundle's original `typescript` language tag (its tests are python-httpx); the tag is preserved as-is and
  does not affect any denominator.

### Bug 2 -- `git apply` is atomic with no `--reject` (agent-patch replay artifact)
`deepswe_full113_orchestrator.py :: _apply_patch_file()` (L217) runs
`git apply --whitespace=nowarn /tmp/<tag>.patch` -- **atomic, no `--reject`**. When an agent patch also edits a
dependency-lock / generated file (`package-lock.json`, `go.sum`, `yarn.lock`, `numba/__init__.py`) and that one
hunk conflicts, git apply drops the **entire** patch -> `agent_reward=None`. Affected: `awilix-async-container-
initialization` (package-lock.json), `kgateway-consistent-hash-policy` (go.sum), `katex-multicolumn-array-spans`
(yarn.lock), `numba-stencil-boundary-modes` (numba/__init__.py).
- **This is a replay artifact, not a hidden solve.** The original in-tree generation run already judged these 0.
- **Proof (no hidden solve):** auditor-A's `deepswe_pathA/runs/audit2_independent/filt.log` -- exclude the
  lock/generated file, apply the rest of the agent patch, run the real verifier -> **reward=0** for all 4.
- These 4 stay `gold_valid` with the agent unsolved (`None`). No numerator impact.

### Bug 3 -- `git diff --binary` capture misses untracked NEW files (agent-patch capture artifact)
`deepswe_qwencode_driver.py` (L328) captures the agent's work with `git -c core.fileMode=false diff --binary
<base_ref>`, which **omits untracked new files**. When the agent solves by adding a new file (e.g. `dasel`,
`sqlfmt`), the captured patch is empty/partial -> `agent_reward=None`.
- **This is a capture artifact, not a hidden solve.** The original run's in-tree `git add -A` state was judged 0.
- These tasks stay `gold_valid`, agent unsolved (`None`). No numerator impact.

### Bug 4 -- python venv handicap: python 0/30 is a pessimistic FLOOR, not a proven ceiling (CAVEAT)
The agent **generation** phase ran python tasks **without `/opt/venv` on PATH**, so the agent could not run
`pytest` to self-check its own python edits (same root cause as the verifier venv bug that STATUS_AUDIT.md fixed,
but on the agent side of generation). Therefore **python 0/30 is a pessimistic floor**, not a proven ceiling for
these weights.
- The intended faithful fix is to **re-run the AGENT** on python with the venv-fixed driver
  (`python3 deepswe_full113_orchestrator.py --mode agent --langs python --run-root runs/full113_pyfix_<ts>
  --concurrency 4 --max-session-turns 100`). **This was NOT done** -- there is no `full113_pyfix` run root. It is
  flagged here honestly as a known caveat + recommended follow-up, and is **not** presented as a true ceiling.
- The **76 non-python valid tasks** (go 34, typescript 32, rust 5, javascript 5) ran with the agent's native
  toolchain (no venv handicap), are validly judged (gold=1, agent=0), and **independently anchor the overall 0%.**

### Bug 5 -- "no-patch" narrative was not re-verified inside the audit (overclaim)
The bundle's "15 no-patch / 15 None" phrasing is a **raw generation-run statistic**; it was not independently
re-derived inside the audit re-score. Its true corroboration lives in the original generation run root
(`deepswe_pathA/runs/full113_20260712T114730Z/<task>/agent/`) and in auditor-A's `filt.log` spot-checks
(awilix/kgateway/katex/numba), which confirm the `None`s hid no solve. Stated here so the count is not read as an
audit-derived fact.

---

## 3. Honest qualitative summary

> **0/113 is REAL.** Auditor-A's independent clean-env re-run is a reliable **upper bound**: it is strictly more
> lenient to the agent than the bundle driver, yet the agent still resolves 0. The judging pipeline nonetheless
> carried a **NO_PROXY judging-pollution bug** and two **patch replay/capture bugs** -- but every one of them only
> struck tasks the agent could not solve anyway (clean-env re-verify and filtered re-apply confirm agent=0 with
> **no hidden solve**), so **none masked an agent solve.** **python 0/30 is a pessimistic floor** under a venv
> handicap; the true python ceiling needs a fix-and-rerun that was **not** performed. The **76 non-python valid
> tasks** are validly judged (gold=1 / agent=0) and independently anchor the 0%.

---

## 4. Raw layer vs corrected-conclusion layer (what changed and what did not)

To keep the raw measurement honest, the **raw polluted-run records are preserved byte-unchanged**; only the
**derived conclusion** was corrected.

- **RAW (unchanged, still show gold_reward=0 for the 4 NO_PROXY victims):**
  `results.jsonl`, `verdict/per_task_verdict.tsv`, `orchestrator.log`, `agent_run_orchestrator.log`,
  `agent_run_report.json`, `repro_closure.json`, `serving/`, `verdict/samples/`.
- **CORRECTED CONCLUSION (gold_valid=106 / gold_broken=7):**
  `report.json` (+`correction` block), `summary.json` (+`correction` block), `denom_assert.txt`, `by_lang.md`,
  `calibration.md`, `README.md`, `gold_validation/gold_vs_agent.tsv`, `gold_validation/gold_valid_ids.txt`,
  `gold_validation/gold_broken_ids.txt`, `gold_validation/gold_validation.md`, and this file.
- A naive `count(gold_reward==1)` over the raw `results.jsonl` therefore returns 102, while the corrected
  conclusion is 106. This gap is **intentional and documented**: the 4-task delta is auditor-A's clean-env
  re-verify (`deepswe_pathA/runs/audit2_independent/broken.log`) superseding 4 NO_PROXY false-reds.

---

## 5. Corrected numbers

| metric | original bundle | corrected | note |
|---|---:|---:|---|
| resolved (numerator) | 0 | 0 | unchanged -- the 0 is REAL |
| headline | 0/113 = 0.00% | 0/113 = 0.00% | unchanged |
| valid-only | 0/102 = 0.00% | **0/106 = 0.00%** | denominator up (NO_PROXY fix), still 0 |
| gold_valid | 102 | **106** | +4 NO_PROXY false-reds recovered |
| gold_broken | 11 | **7** | genuinely broken (gold fails in clean env too) |
| agent dist on valid | 87x0 + 15xNone | **91x0 + 15xNone** | +4 (all agent=0) |
| by lang (valid/broken) | py 28/6, ts 30/5 | **py 30/4, ts 32/3** | go 34/0, rust 5/0, js 5/0 unchanged |

**Moved gold_broken -> gold_valid (4):** httpx-multipart-response-parsing, httpx-streaming-json-iteration
[python]; httpx-deterministic-cookie-store, happy-dom-abort-pending-body-reads [typescript].
**Remaining gold_broken (7):** langchain-request-coalescing, mnamer-daemon-watch-lifecycle,
narwhals-rolling-window-suite, skrub-duration-encoding [python]; eicrud-keyset-pagination-cursor,
prometheus-transactional-reload-status, quill-shared-toolbar-focus [typescript].

Auditor-A evidence root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/audit2_independent/`
(`audit2_verify.sh`, `audit2_filtered.sh`, `broken.log`, `validspot.log`, `filt.log`, `batch1.log`).
