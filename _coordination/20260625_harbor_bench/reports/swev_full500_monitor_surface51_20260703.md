
---

## by-85 顶班: s008 policy-canary official eval (2026-07-04 ~00:25)
51 hit Codex quota (recovers 00:54); 85 ran the s008 policy-canary eval per handoff. **NOT a full resume** — full500 resume is left for 51.
- **Predictions:** 51's 4 s008 rollout preds (django-11095/11099/11119/11133, real model patches) + `django__django-11138` explicit no-patch record (the straggler dropped by the 5400s ROLLOUT_TIMEOUT).
- **Eval:** official `swebench.harness.run_evaluation` via 51's `eval_wrap.py` (inherits the offline requirements-cache patch `swev_offline_eval_cache_patch` + docker API 1.44 pin), Pod B `unix:///var/run/docker.sock`, `--cache_level env`, c=4, **isolated** report dir `swev_s008_eval_by85_20260704/`. **0 rollout token** (eval = docker only).
- **RESULT (green):** submitted 5, completed 4, **resolved 4/4** (django-11095/11099/11119/11133), empty_patch 1 (django-11138, expected), unresolved 0, **errors 0**.
- **Acceptance:** eval rc 0 (errors 0, report written) ✓ | external-net stack trace (raw.githubusercontent / github / pypi / ConnectionError) = **0 hits** ✓ | STOP generated in eval dir = **none** ✓.
- **Evidence:** `swev_s008_eval_by85_20260704/eval.log` + `gpt-5.4-mini.s008eval_by85.json`.
- **RESUME-CLEARED**: the offline eval pipeline (eval_wrap + offline requirements cache) is verified clean on Pod B for s008 (offline-clean, no STOP, 4/4 resolve). **51 may take over the full500 resume at 00:54** — 85 did NOT resume. 51's STOP / ledger / run dirs left untouched (read-only throughout).
