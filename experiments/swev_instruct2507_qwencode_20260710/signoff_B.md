# SIGNOFF (2nd, independent) — SWE-bench Verified × Qwen3-30B-A3B-Instruct-2507 × qwen-code

- **Signer role:** independent second sign-off. Did **not** read `SIGNOFF_SWEV_INSTRUCT2507.md`. All numbers recomputed from raw artifacts.
- **Run audited:** `runs/swev_instruct2507_qwencode_full500_poda_20260709t183239z` (Pod A, read-only).
- **Date of audit:** 2026-07-10.
- **Verdict:** **背书 / ENDORSE — with one MANDATORY main-table caveat** (21.6% is a *lower bound under this scaffold config*, not a capability ceiling). Details in §7.

Serving host had a second live run (TB2.1 bridge / Coder :30001) during my audit; I touched nothing on it.

---

## Headline numbers (independently recomputed)

| Quantity | Value | Source / check |
|---|---|---|
| rows in results.jsonl | 498 | recomputed |
| unique instance_ids | 498 | recomputed (0 dup) |
| resolved (field) | 107 | recomputed |
| resolved (from official `resolved_ids`) | 107 | **0 mismatch** vs field |
| empty-patch-but-resolved | **0** | recomputed |
| agent_status | patch 361 / no_patch 137 | recomputed, matches ledger |
| eval_rc | 0 for all 498 | ⇒ `resolved` is NOT derived from eval_rc |
| **honest score** | **108 / 500 = 21.6%** | 107 scored + django-12050 (dropped-but-resolved) |
| conservative | 107 / 500 = 21.4% | |
| **must NOT quote** | 107 / 498 = 21.49% | wrong denominator (drops the 2 failed) |

results.jsonl sha256 `49b1f5f4…8bafe98` matches both `ledger_summary.json` and `SHA256SUMS`.

---

## 1 — 137 `no_patch` classification (independent, full census; sums to 137)

Tool calls counted at the correct layer: `message.content[]` items with `type=="tool_use"` inside `qwen_attempt_1.stdout.jsonl` (NOT top-level `tool_calls`).

| Cat | Meaning | Count | Evidence |
|---|---|---|---|
| **(a)** | zero tool call / parser-protocol failure | **0** | see below |
| **(b)** | had tool calls, no diff | **90** | 25 made edit-type calls that all failed / didn't persist (0-byte git status + `is_error` tool_results) + 65 used read/grep/glob but never called an edit tool |
| **(c)** | rollout / request timeout | **12** | 5 × client `Request timeout after 483s` + 7 × harness `ROLLOUT_TIMEOUT after 3000s` (stderr) |
| **(d)** | crash / API 400 (context ceiling) | **31** | 30 × `[API Error: 400 …]` + 1 × Node.js V8 heap OOM crash (`django-15098`, stderr = `Mark-Compact … allocation failure` after 766 tool calls) |
| **(e)** | voluntary give-up | **4** | final assistant msg explicitly states inability, 0 edit calls |
| | **SUM** | **137** | ✓ |

Note: the (b)/(e) split is intrinsically fuzzy (both = "ran with tools, ended, no valid patch"); the robust aggregate is **(b)+(e)=94 model-terminated no-patch** vs **(c)+(d)=43 infra/envelope-terminated** (8.6% of 500).

### (a) = 0 — the two literal zero-tool-call cases are TIMEOUTS, not parser failures
`pytest-dev__pytest-5787` and `pytest-dev__pytest-5809`: `n_tool_use=0`, `num_turns=1`, **`peak_input_tokens=0`**, `duration≈483s`, `result="[API Error: Request timeout after 483s. Try reducing input length or increasing timeout … contentGenerator.timeout …]"`.
My independent judgment **agrees with the attribution to (c)**: a parser/protocol failure requires a *returned* response that fails tool-call extraction (input_tokens>0, some text). Here **no response ever returned** (0 tokens, duration == the client timeout threshold). The very first request timed out. This is a request timeout, not a parser failure. Separately, the qwen tool-call parser demonstrably works (361 patch + 135 no_patch instances DID extract tool calls). **→ (a)=0 is correct and robust.**

### (b) 25 "made edits, no diff" are NOT a diff-loss scaffold bug
Spot-checked `astropy-14096`, `django-11728`, `django-13089`: all have 0-byte `post_agent_git_status.txt` + 0-byte `prediction.patch.diff` **and** their tool_result stream contains `is_error:true` entries (edit `old_string` didn't match). Edits failed to apply → no diff. Model behavior, not lost diffs. (Diff pipeline proven working by 361 captured patches.)

---

## 2 — The 30 API-400 "context overflow": mechanism = context ceiling, NOT `max_output_tokens` squeeze

**400 error verbatim (client):** `[API Error: 400 status code (no body)]` — present in each instance's `qwen_attempt_1.stdout.jsonl` terminal `result` event and in `qwencode_attempt_1.log`. There is **no server body** (sglang returns 400 on a streaming chat request → the openai client reports "no body").

**400 verbatim (server, sglang stdout `/tmp/sgl_instruct.log`):**
`/sgl-workspace/sglang/python/sglang/srt/entrypoints/openai/serving_chat.py:938 … return self.create_error_response(str(e))` immediately followed by `INFO: … "POST /v1/chat/completions HTTP/1.1" 400 Bad Request` (38 such 400s in the shared log; ≥30 map to this run).

**Exact input-token count at trigger.** sglang's per-request prefill lines give the true prompt size. The last *accepted* (200 OK) request before each 400 had input in **224384 – 229363** tokens (median **228806**). Across all 27035 single-sequence prefills in the whole run: **MAX accepted single-request input = 229363; ZERO requests accepted above 230000.** The failing request itself is rejected pre-prefill (unlogged) and sits just above 229376. (Example: `astropy-14539` — prefill `#new-token 6263, #cached-token 220008 = 226271` → 200 OK; the *next* call → 400.)

**Is the ceiling 196608, 262144, or 262138? — NONE. It is 229376 (the "fourth mechanism").**
- `context_length = 262144`, `max_req_input_len = 262138` (= 262144 − 6), both from captured `get_server_info` and confirmed by the running process (`--context-length 262144`).
- **196608 (=262144−65536): REFUTED.** A **226271-token** input returned **200 OK** — impossible if the ceiling were 196608. Also `229363` accepted.
- **262144 / 262138: NOT binding.** Nothing was accepted above 230000, far below both.
- **Binding ceiling = 229376 = 262144 − 32768.** sglang's chat path rejects when `input_tokens + effective_max_new_tokens > context_length`, with **effective_max_new_tokens ≈ 32768** (proof: `229363 + 32768 = 262131 ≤ 262144` accepted; `226271 + 65536 = 291807 > 262144` would have been rejected but was accepted, so the reservation is **not** 65536). The observed 32768 is **half** the configured `QWEN_CODE_MAX_OUTPUT_TOKENS=65536` — a qwen-code-internal effective output budget.

**Interpretation (load-bearing for the caveat):**
- The specific hypothesis "被 `max_output_tokens=65536` 挤死 (ceiling 196608)" is **REFUTED**. The 30 die at the **229376** context ceiling.
- There *is* a config artifact: a 32768 output reservation lowers the effective input ceiling ~14% below the model's 262144 window (and below `max_req_input_len` 262138). No effective context-compaction fired.
- BUT the proximate cause is Instruct-2507's own context-hungry behavior (repeated large file reads without convergence). Same-host Coder (:30001, same `--context-length 262144`) hit this wall ~0 times (3 total no_patch). ⇒ the wall is **model-behavior-driven under a config-influenced ceiling**, not a config that would penalize any model equally.

**Coder used the same `max_output_tokens`?** **INSUFFICIENT_EVIDENCE** — the Coder run_root is on Pod B (not among my provided hosts); I searched `agentic-foundation-model-bench/runs/*` and `nips2026/*/runs/*` on the shared FS and found no Coder full500 config. However, the *serving-side* ceiling (which produces the 400s) is provably identical: both models are served by the same host, both launched `--context-length 262144` (both process cmdlines seen live).

---

## 3 — Are the 107 resolved real? YES

- `resolved` recomputed independently from each `report_path`'s `resolved_ids` = **107**, **0 mismatch** vs the results.jsonl field. `resolved` is taken from official `resolved_ids`, not `eval_rc` (which is uniformly 0).
- **0** empty-patch-but-resolved.
- **All 107** resolved patches scanned: **0** touch any test path (`/test`, `/tests/`, `*_test.py`, `test_*`). 8 sampled in detail: non-empty (475–874 B), 1 source file each.
- `eval.sh` (read from django-12050) enforces the anti-cheat: `git checkout <base_sha> tests/…` (wipes any model test edits) → `git apply` the **gold** `test_patch` → run tests → `git checkout <base_sha>` again. Model test edits cannot count.

---

## 4 — The 2 dropped instances: handled correctly; defect only UNDER-counts

**`django__django-12050` — a TRUE resolved that was dropped.**
- `report.json` exists at `…/eval/logs/run_evaluation/v2_django_u_django-12050/…/report.json`: `resolved: true`, `patch_successfully_applied: true`, **FAIL_TO_PASS 1/1** (`test_iterable_lookup_value`), **PASS_TO_PASS 10/10**, all failure lists empty. `prediction.patch.diff = 649 B`.
- `eval.log` stack top: `docker.errors.NotFound: 404 … /containers/bdc77e…/json: … No such container` — a **post-grading container-cleanup race** (report already written, then cleanup inspect 404 → eval_rc=1).

**`matplotlib__matplotlib-23299` — correctly unresolved.**
- `prediction.json` `model_patch` length = **0** (empty patch); `prediction.patch.diff = 0 B`. Exhaustive `find` shows **NO `report.json`** anywhere under the failed dir (only `eval/eval.log`). Empty patch ⇒ can never resolve. `eval.log` ends in the same docker-404 (during container list/inspect).

**⇒ honest 108/500 = 21.6%; conservative 107/500 = 21.4%; 107/498 must not be quoted.**

**Defect confirmed at code level** — `full500_qwencode_orchestrator_v21.py` (in `repo/.worktrees/swev-qwencode-v21-agent51/scripts/`):
- `run_eval` **L891-892**: `if rc != 0: return EvalOutcome(status="eval_error", …)` — diverts on nonzero eval rc **before** computing `resolved` (L893 `resolved = iid in resolved_ids`).
- `pipeline` **L918-921**: the `eval_out.status != "ok"` branch calls `preserve_failure` + `append_event(type=infra_error)` and `return`s — it **never calls `append_score_once`** (the success path L925+ does). So the instance is simply **absent** from results.jsonl.
- **Direction:** a dropped instance can only be removed from the tally. Dropped-resolved ⇒ undercount (django-12050); dropped-unresolved ⇒ neutral (matplotlib). It can **never** inflate resolved. ✓ "只会少记不会多记."

---

## 5 — Model identity: it IS Qwen3-30B-A3B-Instruct-2507

`sglang` does not validate the `model` field, so I relied only on `model_path` and the live process:
- Captured `get_model_info_{before,after}.json`: `model_path = …/models/Qwen3-30B-A3B-Instruct-2507` (both identical).
- Live serving host (`slime-96879589-667jv…`): `hostname -I` = **100.100.104.140** (== `base_url` host); live `GET :30000/get_model_info` → `model_path …/Qwen3-30B-A3B-Instruct-2507`.
- Actual process (PID 668, `SLl+`): `python -m sglang.launch_server --model-path …/Qwen3-30B-A3B-Instruct-2507 --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 --port 30000 --context-length 262144 --tool-call-parser qwen --trust-remote-code`.
- **STARTED Thu Jul 9 08:24:33 UTC 2026** (pod runs in UTC — my probe's `lstart` == `date -u`), still alive at Jul 10 04:04. **Covers the entire run window 18:32Z→23:39Z; single continuous PID; no mid-run restart.**
- sglang's own logged `server_args`: `served_model_name='Qwen/Qwen3-30B-A3B-Instruct-2507'`, `tool_call_parser='qwen'`.

---

## 6 — Redaction & secret hygiene: CLEAN

- `api_key` and `admin_api_key` are **REDACTED** in both `get_server_info_{before,after}.json` (and sglang's own args log shows both = `None`).
- **Independent value-based secret scan** (not key-name based) over all `serving/*.json` — patterns `sk-…`, `hf_…`, `gh[pousr]_…`, `Bearer …`, `AKIA…`, JWT, 40+ hex: **ZERO matches.** (No repeat of the orchestrator's `hf_chat_template_name` false-positive; that field's value is `None`.)
- **`SHA256SUMS` (9 files incl. results.jsonl) and `SHA256SUMS.prelaunch` (6 files) all recompute OK.** Coverage = results.jsonl + serving model/server info + logs + prelaunch scripts + preflight; it does NOT cover per-instance evidence dirs / events.jsonl / ledger_summary (dynamic/large) — acceptable, since the score source (results.jsonl) is hash-anchored.

---

## 7 — Verdict

Every arithmetic and provenance check passes: accounting exact; `resolved` from official `resolved_ids` with 0 mismatch, 0 empty-patch-resolved, 0 test-tampering (and eval.sh neutralizes any); model identity provably Instruct-2507 across the whole window; the 2 dropped instances handled honestly with an under-counting-only defect; no secret leak; hashes verify. **(a)=0 is correct** (the 2 zero-tool cases are genuine timeouts).

**> 我愿意为「该 run 的 `resolved/total` 反映了 Instruct-2507 的真实 agentic coding 能力」背书 —— 背书 (ENDORSE).**

### MANDATORY main-table caveat
`21.6%` (108/500) is a **lower bound under this scaffold configuration**, not a capability ceiling, because:
1. **1** true-resolved instance was silently dropped by the eval-rc gate (honest = 108, ledger = 107).
2. **43/500 (8.6%)** terminated on scaffold/serving envelope limits, not on a clean "model tried and failed": 30 at the **229376-token context ceiling** (= 262144 − a 32768 output reservation, i.e. ~14% below the model's real window; no effective compaction), 12 on 483s/3000s timeouts, 1 on a Node-heap OOM. A more forgiving context-management scaffold could convert some of these.

Correcting the record on the specific hypothesis I was asked to test: the 30 context-400s are **NOT** "squeezed out by `max_output_tokens=65536`" (that implies a 196608 ceiling — refuted; a 226271-token input was accepted 200 OK). They die at **229376**, driven primarily by Instruct-2507's own context-hungry behavior (same-host Coder hit the identical serving ceiling ~0 times). The caveat therefore reads: *lower bound under this scaffold*, with the config contribution being the 32768 output reservation, not a 65536 squeeze.

### INSUFFICIENT_EVIDENCE items
- Coder run's harness `max_output_tokens` value (Pod B run_root not reachable from provided hosts; serving-side ceiling proven identical instead).
