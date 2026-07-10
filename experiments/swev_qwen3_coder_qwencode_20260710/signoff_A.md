# SIGNOFF — surface:86 — SWE-V full500 × Coder-30B × QwenCode (adversarial, 1st stamp)

Auditor: surface:86 (Claude), **READ-ONLY**, no interference with the live run. Mandate: try hardest to prove the score FAKE; stamp only on failure to do so. Audited **while live** (snapshot ~02:10 local: `results.jsonl` = 478 rows).

**run_id verified** (per the "same score ≠ same run" prior): `run_manifest.json` → run_root `…/swev_qwencode_full500_surface55_20260709t160554z/full500_c20`, `created_utc 2026-07-09T16:07:11Z`, `model Qwen/Qwen3-Coder-30B-A3B-Instruct`, `base_url http://100.100.104.140:30001/v1`, worktree `swev-qwencode-v21-agent51` — all match the brief. Canonical compare = 243/500=48.6%; live snapshot **233 resolved / 478 = 48.7%** (converging on canonical).

---

## Attack 1 — is the trace real? → **REFUTED** (could not prove fake)
Sampled 10 cases (5 resolved + 5 unresolved), each: nested `prediction.json[iid].model_patch`, `agent/*stdout.jsonl` tool-call count, test-file-touch scan.
| instance | resolved | patch | files | testtouch | tools | model | eval |
|---|---|---|---|---|---|---|---|
| astropy-7671 | True | 942b | 1 | **False** | 20 | Qwen3-Coder-30B | res=1 empty=0 err=0 |
| astropy-7166 | True | 2526b | 1 | False | 26 | ok | res=1 empty=0 |
| django-10914 | True | 713b | 1 | False | 25 | ok | res=1 empty=0 |
| django-10880 | True | 639b | 1 | False | 33 | ok | res=1 empty=0 |
| astropy-7606 | False | 818b | 1 | False | 20 | ok | res=0 empty=0 |
| django-10554 | False | 2447b | 1 | False | 35 | ok | res=0 empty=0 |
| astropy-8872 | False | 1342b | 1 | False | 34 | ok | res=0 empty=0 |
| astropy-8707 | False | 1311b | 2 | False | 27 | ok | res=0 empty=0 |
- Every case (resolved AND unresolved): **non-empty patch, 20-35 real tool calls, ZERO test-file modifications, model=Qwen3-Coder-30B**. Unresolved cases genuinely worked (real patch+tools) then failed tests — not empty/timeout spinning.
- Evidence: `instances/astropy_u_astropy-12907/agent/qwen_attempt_1.stdout.jsonl` = 200 events (system 1 / assistant 127 / user 71 / result 1), 71 `"name"` tool invocations; patch touches `astropy/modeling/separable.py` (source, not test).
- No `empty_patch` in the whole ledger among sampled; global `empty_patch_instances=0` in each eval report.

## Attack 2 — did eval really run? → **REFUTED**
- `resolved` is NOT derived from `eval_rc`. Orchestrator `full500_qwencode_orchestrator_v21.py:893`: `resolved = spec.instance_id in set((report or {}).get("resolved_ids", []))`. Global check: `eval_rc==0` for all 478 rows, yet resolved splits **233 True / 245 False** → `eval_rc=0` does not force resolved. The known docker-125/eval_rc trap is structurally avoided.
- Real test execution + counts>0, verified in the SWE-bench per-instance `report.json` + `test_output.txt`:
  - `astropy-12907` (resolved): `FAIL_TO_PASS success=2 failure=0`, `PASS_TO_PASS success=13 failure=0`, `test_output.txt` → "15 passed"; `eval.log` shows a real 6:47 test run (`✓=1`).
  - `astropy-7606` (unresolved): `FAIL_TO_PASS 1/0` but **`PASS_TO_PASS success=240 failure=1`** → resolved=False is a *genuine regression* (patch broke 1 of 240 previously-passing tests), "242 passed" real run.
- Eval used the AGENT's patch, not oracle/cache: `eval/logs/.../patch.diff` is **byte-identical** to `prediction.json` model_patch (504b==504b for 12907; 818b==818b for 7606; `identical=True`), `patch_successfully_applied=True`.

## Attack 3 — false-green in scoring code? → **REFUTED** (with one watch-item, not a confirmed defect)
- **Dedup solid**: ledger idempotent, keyed by instance_id; a second write → `{"type":"duplicate_score_suppressed"}` event (`orchestrator:240-248`). Observed **478 rows / 478 unique instance_ids** (0 duplicates).
- **no_patch → resolved=False** (in denominator), not skipped: 6 `no_patch` cases, all `resolved=False`; `resolved_but_not_patch = []` (no case is resolved without an agent patch).
- **SWE-V has NONE of the TB2.1 reducer's 3 blind spots**: no `ready`-requires-`unresolved==0` gate (resolved is read directly from SWE-bench `resolved_ids`); resolved = strict SWE-bench (all FAIL_TO_PASS + all PASS_TO_PASS), no lenient/strict split; infra is a distinct status, not silently folded.
- ★ **Watch-item (the one real structural finding):** infra/eval errors get **NO ledger row** — `orchestrator:910-921` on `agent.status=="infra_error"` or `eval_out.status!="ok"` does `preserve_failure(...)` + `return` without `append_score_once`. Currently **4 cases in `failed/`** (`django-11138`, `django-11276`, `django-11433`, `sympy-19346`) are NOT in `results.jsonl`. This would inflate accuracy ONLY IF the final reducer used `resolved/len(ledger)`. It does not: the prior Qwen final (`swev_qwencode_v21_full500_final_20260706.json`) is `resolved 243 + unresolved 257 = 500` → **denominator is fixed /500, failed/infra fold into unresolved**. Agent infra errors are also retried in-instance (`run_agent_with_retries:833-843`). ⇒ not a false-green as long as finalization keeps /500 and the 4 failed cases are re-run or counted unresolved. **Verify at close.**

## Attack 4 — raw vs corrected trap? → **REFUTED**
- Canonical `swev_qwencode_v21_full500_final_20260706.json`: `resolved=243, unresolved=257` (=500). **No `corrected`/`raw`/`accuracy`/`note` field, no manual-correction/scorer-bug note** in the `.md`. The TB2.1 headless-terminal +1 correction is TB2.1-only and was NOT applied to SWE-V.
- This live run has **no pre-baked `run_metadata.accuracy`** (searched) → no `run_metadata` raw-value trap; accuracy is computed as `resolved/500` by the reducer at close, not carried in a quotable-but-wrong field.

## Attack 5 — is the serving evidence trustworthy? → **partial: secrets/consistency CONFIRMED; exact ps-match INSUFFICIENT_EVIDENCE**
- **Secrets: independently re-scanned (did not trust the brief).** `SERVING_CONFIG_20260710.json`: `api_key`/`admin_api_key` = `"<REDACTED>"` (L161/162/1200/1201), `ssl_keyfile_password: null`, the 124 "token" hits are ServerArgs names (`max_total_tokens` etc.). Value-scan for `sk-…`/`bearer …`/`eyJ…`/32+-char hex (excluding tokens/paths) = **empty**. → no residual secret. ✅
- **Internal consistency**: config is sglang's own ServerArgs self-report — `tp_size=2`, `context_length=262144`, `port=30001`, `served_model_name`/`model_path` present; matches `runner_config.json` (`context_limit 262144`, base_url `…30001`, model Qwen3-Coder-30B) and the brief (tp=2). `captured_from Pod B env-kvm-57740737-bzw56` @ 2026-07-09T17:29Z. ✅
- **Live serving corroborated by the run itself**: 478 instances completed with coherent Qwen3-Coder-30B source-code patches (`model_name_or_path=Qwen/Qwen3-Coder-30B-A3B-Instruct` in every prediction), ≈12k successful LLM calls — the server is demonstrably live serving that exact model. ✅
- **Exact `ps -o args` cmdline match → INSUFFICIENT_EVIDENCE.** sglang does NOT run on Pod B (Pod B `nvidia-smi` returns empty → no GPU; it is the CPU run-host). It serves from a separate GPU node at tailscale `100.100.104.140`, which I have no SSH path to; and I declined to curl 55's serving endpoint (`/get_server_info`) to respect the "禁干扰" red line. **No discrepancy was found — I simply could not perform the exact process-cmdline comparison the brief requested.** What is missing: SSH access to the sglang host (or explicit permission for a read-only `/get_server_info` GET).

---

## Endorsement
> **背书 (endorse).** I tried to break it on all five lines and failed: traces are real (tool calls + non-empty non-test patches), eval genuinely runs the SWE-bench tests (FAIL_TO_PASS+PASS_TO_PASS counts>0, agent's own patch, resolved from `resolved_ids` not `eval_rc`), the scoring code dedups correctly and carries none of TB2.1's blind spots, and the canonical is a clean /500 with no raw-vs-corrected trap. I endorse that **this run's `resolved/total` reflects the agent's true capability**, subject to two non-blocking conditions: (1) finalization keeps the **/500 denominator** and re-runs or counts-as-unresolved the `failed/` infra cases (Attack 3 watch-item); (2) the exact serving process cmdline (Attack 5) is corroborated but not ps-verified — provide the sglang host or authorize a read-only `/get_server_info` GET to close it fully.

## Commands run (read-only)
- `ssh dev` reads of `run_manifest.json` / `runner_config.json` / `results.jsonl` (478 rows, 478 unique) / per-instance `prediction.json`,`agent/*stdout.jsonl`,`eval/*.json`,`eval/logs/.../report.json`,`test_output.txt`,`patch.diff`.
- `ssh dev` reads of `.worktrees/swev-qwencode-v21-agent51/scripts/full500_qwencode_orchestrator_v21.py` (L240-248 dedup, L845-894 run_eval/resolved, L905-935 infra handling, L833-843 retries).
- local reads + secret scan of `_coordination/bench_kvm_e2e_20260704/SERVING_CONFIG_20260710.json`.
- `ssh Pod B` (`env-kvm-57740737-bzw56…pod@h.pjlab.org.cn`): `PODB_OK`, no sglang proc, `nvidia-smi` empty (no GPU).
- did NOT: kill/restart anything, submit any inference, or curl 55's serving.

— end surface:86 signoff (SWE-V full500) —
