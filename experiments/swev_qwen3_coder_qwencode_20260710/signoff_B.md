# SIGNOFF (2nd, independent) — SWE-V QwenCode full500 c=20

- Auditor: independent 2nd sign-off. Did NOT read `SIGNOFF_86_*`. All facts re-derived from primary artifacts.
- Run: `swev_qwencode_full500_surface55_20260709t160554z/full500_c20`
- run_root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_qwencode_full500_surface55_20260709t160554z/full500_c20`
- Status at audit: **FINISHED** — `runner.rc=0`, `runner.done` present, orchestrator process gone, `.running`=0, `results.jsonl` stable at 496 rows.
- Bench: SWE-bench Verified (500), harness qwen-code 0.15.6, serving `http://100.100.104.140:30001/v1`.
- **Ground truth (independently recomputed): 240 resolved / 496 scored rows. Honest full-500 (recovering 2 dropped-but-truly-resolved) = 242/500 = 48.4%.** Canonical reference 243/500 = 48.6% → within 1 instance.

---

## Line 1 — trace is real: **REFUTED (attack fails; traces are genuine)**

- **Zero spinning.** Tool-use count over all 496 traces (parsed from `message.content[]` `type==tool_use`, the correct QwenCode location): min=2, p10=20, median=35, max=128, **zero_count=0**. `health_latest.json`: `total_calls_estimate_assistant_records=35359`, `completed_sessions_result_records=500`, `stdout_files=500`, `sum_num_turns=19234`.
- **8-case sample (resolved + unresolved, cross-repo):**
  - Resolved patch NON-test source & pass gold tests, e.g. `astropy__astropy-12907` (71 tool_use, patch `astropy/modeling/separable.py`, F2P 2/0, P2P 13/0); `matplotlib__matplotlib-13989` (patch `_axes.py`, F2P 1/0, P2P 411/0).
  - Unresolved are **genuine model failures**: real non-test patches but gold F2P still fails, e.g. `matplotlib__matplotlib-14623` (112 tool_use, patch `lib/matplotlib/ticker.py`, F2P 0/1); `django__django-10097` (patch `django/core/validators.py`, F2P 431 ok / **7 fail** → unresolved).
- **No empty-patch resolves: 0/496** (`prediction.json` model_patch non-empty for every resolved case).
- **Test-file cheating checked — all clear.** 17 resolved cases whose patch touches a test file:
  - 15/17: model edited the exact test file the harness resets. eval.sh (e.g. `instances/django_u_django-13821/.../eval.sh`) does `git checkout <base_commit> tests/backends/sqlite/tests.py` then `git apply` the **gold** test_patch BEFORE running tests → model's test edits are discarded.
  - 2/17 (`pytest-dev__pytest-5631`, `sympy__sympy-24213`): model touched a *different* test file that the eval command **never runs**. pytest-5631 eval runs only `pytest -rA testing/python/integration.py` (holds the F2P + all 15 P2P nodes, and is reset); model's added test in `testing/test_compat.py` is never executed. sympy-24213 eval runs only `bin/test .../test_quantities.py` (holds F2P `test_issue_24211`, reset); model's brand-new `test_equivalent_dimensions.py` is never run. Both resolves come from the real **source** fix.

## Line 2 — eval really ran: **REFUTED (attack fails; eval is genuine)**

- **Tests actually executed:** across scored cases, F2P nodes executed total = **1448**, P2P = **57764**. eval.sh contains real invocations (`runtests.py` / `pytest` / `bin/test`) between `>>>>> Start/End Test Output`.
- **`resolved` derives from official report, honestly:** orchestrator `run_eval` (`scripts/full500_qwencode_orchestrator_v21.py:893`) `resolved = instance_id in set(report.get("resolved_ids", []))`; missing report → `resolved=False` (safe). Independent recount of resolved from official `resolved_ids` = **240 = ledger** exactly, **0 mismatches**, 0 missing reports, 0 missing predictions.
- **Cache patch does NOT inject verdicts.** `swev_offline_eval_cache_patch.py` overrides ONLY `py_spec.get_requirements_by_commit` and `get_environment_yml_by_commit` (dependency/env-setup text), fail-closed (`raise RuntimeError` on cache miss). It does not touch test execution, `resolved_ids`, or tests_status. This is genuinely `--cache_level env`.
- **`eval_rc=0` false-zero pitfall checked:** every in-ledger row has eval_rc=0 AND a populated tests_status with counts>0. The 4 rc≠0 cases were EXCLUDED, not silently passed (see Line 3).

## Line 3 — scoring false-green: **one benign defect CONFIRMED, but NOT score-inflating**

- **Dedup correct:** `append_score_once` (orchestrator:239-258) keyed by instance_id under flock, suppresses duplicates. 496 rows / 496 unique / **0 duplicates**. Self-test `duplicate_ledger` covers it.
- **CONFIRMED defect (the "缺产物→静默跳过" pattern):** `pipeline` (orchestrator:912-921) sends `infra_error`/`eval_error` to `failed/` + an event, and does **NOT** write a score row. `load_specs` re-queues only non-`completed_ids`, but the launcher runs the orchestrator **once** (no resume loop). Result: `results.jsonl` has **496 rows, not 500**; 4 cases dropped. If a headline used 240/**496**, the denominator is understated.
- **Why it does not inflate:** the 4 dropped are a **post-test harness flake**, not model or test failures. All 4 crash identically at `swebench/harness/reporting.py:107 make_run_report → client.containers.list(all=True) → docker.errors.NotFound 404 No such container` (concurrent-container-removal race during cleanup). `test_output.txt` shows tests fully ran. Recovered true verdicts from their `report.json`: `django-11276`=**True**, `sympy-19346`=**True**, `django-11138`=False, `django-11433`=False. So the drop removes **2 real resolves** + 2 unresolved (≈50%, same as overall) → it slightly **under-credits** the model. Honest full-500 = (240+2)/500 = **242/500 = 48.4%**; 240/500 = 48.0% (conservative); 240/496 = 48.39%. All ~48%, none inflated.
- **Not isomorphic to TB2.1's harmful blind spots — healthier:** model-layer give-ups ARE scored as unresolved here (`no_patch` rows = 6, all resolved=False), the OPPOSITE of TB2.1 `infra_fail` excluding LLM-layer failures. Only genuine infra/harness races are excluded.
- **No TB2.1-style `run_metadata.accuracy` mismatch:** this run writes NO precomputed accuracy field. `runner_config.json`/`run_manifest.json`/`health_latest.json` carry only raw counts (resolved=240, rows=496). Nothing to misquote.

## Line 4 — model identity: **REFUTED (identity is correct = Coder-30B)**

- Live `GET :30001/get_model_info` → `model_path = /mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct` (the only trustworthy signal).
- Live sglang process on serving host (`slime-96879589-667jv…`, PID 673, `--port 30001`): `--model-path .../Qwen3-Coder-30B-A3B-Instruct --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct --tp-size 2 --tool-call-parser qwen3_coder`, **STARTED Thu Jul 9 08:24:33 UTC**, still running — covers the entire run window (16:09–18:48 UTC). No mid-run swap.
- Distinct `--tool-call-parser qwen3_coder` (:30001) vs `qwen` (:30000, Instruct-2507) confirms these are two genuinely different models, not one relabeled. The "sglang doesn't validate model field" trap is avoided because :30001 truly serves Coder-30B. Matches the 48.6% canonical model.

## Line 5 — serving evidence trustworthy: **CONFIRMED**

- `experiments/serving/SERVING_CONFIG_20260710.json` `port_30001` block (model_path L1046, served_model_name L1202, `"port": 30001` L1588, context_length 262144, tp 2) matches the live process args exactly.
- **Independent secret scan** (value-based, not name-based): no `sk-` / `Bearer ` / `hf_<token>` values anywhere; the only secret-named field is `api_key`, present as `"<REDACTED>"` (L161, L1200) or `null` (L658, L1697). No leak. No `OPENAI_API_KEY`/env dump present.

---

## Residual caveats (do not undermine "reflects true ability")

1. Report headline should be stated over /500 (242/500=48.4% recovering the 2 dropped resolves, or conservatively 240/500=48.0%), NOT 240/496. Even 240/496 does not inflate (dropped set is verdict-neutral).
2. The run's own doc `FULL500_SWEV_QWENCODE_20260709.md` already honestly discloses this is a **current-serving retest**, NOT a strict same-serving reproduction of 243/500=48.6% (context_length/serving-config difference). That is an orthogonal comparability caveat, not a validity problem.
3. Transient serving errors during the run (`http_5xx=245`, `http_429=12` markers, `retry_exhausted=2`) were absorbed by the retry layer; they do not affect the 240 verified resolves.

## Verdict

The 240 resolves are each independently verified genuine (real tool-driven rollouts, non-empty non-test source patches, official gold F2P/P2P executed and passed, test-file edits neutralized, correct Coder-30B serving). The single confirmed scoring defect (4 dropped rows) is a benign post-test harness race that under-credits rather than inflates.

> 我是否愿意为「该 run 的 resolved/total 反映了 agent 的真实能力」背书? **背书**
