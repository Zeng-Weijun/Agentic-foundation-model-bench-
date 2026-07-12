# Calibration — TB2.1 terminus-2 caliber (Instruct-2507) — do NOT mix with SWE-V / Multilingual

## What "resolved" means here
- **Caliber**: Terminal-Bench 2.1 (TB2.1), full **89** tasks, **official `terminus-2` agent**, **single pass@1** (attempts=1, temperature=0.0). `score_rule = single_attempt_pass_at_1_over_89_tasks`.
- **resolved** = terminus-2 solved the task and the task's own tests passed (`is_resolved=true` in tb-native `results.json`). This is the TB2.1 harness verdict, not an LLM judge.
- Not comparable to SWE-V (bash-only SWE) or the Multilingual lane. No official TB2.1 Qwen anchor is asserted (single pass@1 compatibility probe).

## Score
- **3 / 89 resolved = 0.03370787 = 3.37%** (`accuracy` == `mean_pass_at_1`, identical because attempts=1).
- resolved_ids: `configure-git-webserver`, `hf-model-inference`, `modernize-scientific-stack`.

## Denominator = 89 (v4 口径 for the two special tasks)
The tb-native harness scored **all 89** rows. is_resolved distribution: **true=3 / false=84 / null=2**; the harness folds the 2 null rows into `n_unresolved` (86 = 84 false + 2 null). Both null rows are adjudicated **FALSE** and **counted** in the denominator:

### mailman — is_resolved=null, failure_mode=test_timeout -> FALSE (agent_not_converged)
- The agent left postfix/mailman3 non-functional. Its own post-agent pane ends with `ConnectionRefusedError: [Errno 111] Connection refused` on SMTP `:25` while running `/app/eval.py` — the mail server never came up correctly.
- When the task's official test ran, it collected 3 items from `test_outputs.py` then **hung**, and hit the **7200s test-timeout** (`Test command timed out after 7200.0s for task mailman`). tb-native recorded `is_resolved=null`.
- Root cause = **agent-side non-convergence** (a working solution would let the test pass in seconds). **Not infra**: serving was healthy the whole run (see below). Evidence in `special_evidence/mailman.*`.

### tune-mjcf — is_resolved=null, failure_mode=unknown_agent_error -> FALSE (agent_not_converged)
- A mujoco simulation-speed task requiring `Time pctg <= 60.00%`. The agent's `eval.py` loop is stuck at `Time pctg ~100%% (need 60.00%%)`, `Speedup 1.00x`, `Final state difference: 0.0000` (correctness OK, speed never improves). It optimized from 100.21%→100.04% but can never reach 60%.
- Its container (docker id `3bdb9767`) was still a **live zombie** after the rest of the run finished; it was `docker kill`ed at **2026-07-12T20:26Z** so terminus could finalize. tb-native then recorded the 89th row as `is_resolved=null` (unknown_agent_error) and wrote the final results.json (3/89). Evidence in `special_evidence/tune-mjcf.*`.

**Consequence**: numerator stays 3, denominator = 89, score = **3/89 = 3.37%** — not 3/88.

## The strict-v4 `infra_fail=2` is a heuristic label, NOT a serving failure
The run's own v4 strict ledger (`verdict/tb21_strict_summary.json`, generated 2026-07-12T20:29:49Z during finalization) reports `infra_fail=2, missing_artifact=1, timeout=1`. Those flags map to **exactly the two special tasks**:
- `mailman` -> strict_status=`timeout`, `infra_fail=true` (heuristic: test_timeout -> infra).
- `tune-mjcf` -> strict_status=`missing_artifact`, `infra_fail=true` (heuristic: no per-task results.json at scoring time because its zombie container was killed) + an `external_network_marker` from the agent's failed offline attempts.

Neither is a real infrastructure failure — both are **agent-side non-convergence**. **Serving-health proof** (`batch_01_of_01/terminal_bench.log`, 679 lines): **0** RateLimit, **0** HTTP 429, **0** 500/502/503, **0** InternalServerError, **0** ServiceUnavailable, **0** Connection/APIConnection errors. The only `timed out` lines (29) are **28 agent-7200s-timeouts + 1 mailman test-timeout** — task-budget exhaustion, not serving. `/get_model_info` + `/get_server_info` both resolve to the Instruct-2507 weights before and after (seed 61643818 stable). So `infra_fail=2` does **not** license removing anything from the denominator; per the explicit口径 both tasks are unresolved and counted. (This differs from the Coder run's clean `infra_fail=0`; here the 2 flags are the two agent-timeout/zombie special tasks, reconciled above.)

## external_network_marker = 13
EXPECTED, not contamination. All 89 r7 composes pin `network_mode: none` on the task container; terminus-2 runs on the HOST and reaches serving from the host, so the container itself has no network. The markers are the model's *failed* offline attempts (e.g. `Temporary failure resolving 'httpproxy-headless.kubebrain.svc.pjlab.local'`, apt mirror fetch failures) — substring-scanned. 0 successful egress.

## Why the tb-native gate still says `blocked` / `ready=false`
Inherent: the tb-native readiness gate requires `clean_pass == total` (oracle 89/89). **Every** real model run trips it. The authoritative completion signal is `tb_rc=0` + batched `status=finalized` + `mean_pass_at_1`.

## Serving identity
`100.100.104.147:30000`, `model_path .../models/Qwen3-30B-A3B-Instruct-2507`, seed 61643818, IDENTITY_OK before+after (`serving/IDENTITY_SUMMARY.txt`). Names are not trusted on this stack; endpoint+weights are the evidence.

## Watchdog gaps (same as Coder bundle, disclosed)
`net_isolation_runtime_*.jsonl` and `dataset_assert_*.log` are 0-byte (empty-filter / silent watchdog fail). Network isolation stands on the **static compose gate (89/89 `network_mode:none`)** + marker texture (0 successful egress); dataset identity on `run.env.summary` `tb_dataset_path` + 89 task ids.
