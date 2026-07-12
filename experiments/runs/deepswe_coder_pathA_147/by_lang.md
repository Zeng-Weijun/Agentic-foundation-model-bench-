# DeepSWE full113 x Coder x qwen-code (Path A) -- by-language resolve table

Honest audit (fixed verifier, gold-validated, NO_PROXY correction applied). `resolved` = gold_reward==1 AND agent patch passes the same verifier.

| lang | valid (gold=1) | broken (gold=0) | total | resolved | resolve_rate(valid) |
|---|---:|---:|---:|---:|---:|
| go | 34 | 0 | 34 | 0 | 0/34 = 0.00% |
| javascript | 5 | 0 | 5 | 0 | 0/5 = 0.00% |
| python | 30 | 4 | 34 | 0 | 0/30 = 0.00% |
| rust | 5 | 0 | 5 | 0 | 0/5 = 0.00% |
| typescript | 32 | 3 | 35 | 0 | 0/32 = 0.00% |
| **TOTAL** | **106** | **7** | **113** | **0** | **0/106 = 0.00%** |

Correction 2026-07-13 (see `AUDIT_NOTES.md`): was python 28 valid / 6 broken and typescript 30 valid / 5 broken.
Auditor-A's clean-env re-verify reclassified 4 NO_PROXY-false-red tasks gold_broken -> gold_valid
(python +2: httpx-multipart-response-parsing, httpx-streaming-json-iteration; typescript +2:
httpx-deterministic-cookie-store, happy-dom-abort-pending-body-reads). Every language is still resolved=0.

The 76 non-python valid tasks (go 34, typescript 32, rust 5, javascript 5) were scored with the agent's
native toolchain (no venv handicap) and independently anchor the overall 0%. python 0/30 is a pessimistic
floor -- the agent ran python generation without `/opt/venv` on PATH and could not self-run pytest; the true
python ceiling needs a fix-and-rerun that was NOT performed (see `AUDIT_NOTES.md`).
