# Qwen3-Coder SWE-bench Qwen Code Retry Cases

Date: 2026-05-29

Model: `qwen3-coder-30b-a3b-instruct`

Serving: SGLang on `worker_rkn9p`, `http://100.103.11.77:8503/v1`

Agent scaffold: Qwen Code `0.15.6`

Raw full run:

- Run root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/code_model_suites/qwen3_coder_30b_a3b_instruct_swebench_qwen_code_full_262k_retag_20260528_181844/swebench_verified_qwen_code/qwen_native_outputs/qwen_code_qwen3_coder_30b_a3b_instruct_qwen3_coder_30b_a3b_instruct_swebench_qwen_code_full_262k_retag_20260528_181844_paper_n500`
- Score: `245/500 = 49.0%`
- Summary: `completed=486`, `errors=1`, `empty_patch=14`

Selective retry after runner fix:

- Run root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/code_model_suites/qwen3_coder_30b_a3b_instruct_swebench_qwen_code_selective_retry3_20260529_123916/swebench_verified_qwen_code/qwen_native_outputs/qwen_code_qwen3_coder_30b_a3b_instruct_selective_retry3_20260529_123916_paper_n500`
- Corrected score: `245/500 = 49.0%`
- Retry contribution: `0` newly resolved cases
- Machine-readable score artifact: `selective_retry_corrected_score.json`

## Case Notes

| Instance | Difficulty | Original symptom | Retry outcome | Interpretation |
|---|---:|---|---|---|
| `sphinx-doc__sphinx-9591` | `<15 min fix` | `qwen_returncode=53`, patch collection hit `UnicodeDecodeError` | `qwen_returncode=0`, 1002-byte patch, verifier ran, `resolved=false` | Not inherently hard by label; the original failure was partly a runner decode bug. After the fix, the agent produced a real but incorrect patch. |
| `sphinx-doc__sphinx-11510` | `1-4 hours` | `qwen_returncode=124`, agent timeout, empty patch | `qwen_returncode=0`, still empty patch, `resolved=false` | This is the one clearly harder case by SWE-bench difficulty label. Retry removed the timeout but the model still did not submit a patch. |
| `matplotlib__matplotlib-26208` | `<15 min fix` | `qwen_returncode=53`, max-session-turn style empty patch | `qwen_returncode=0`, still empty patch, `resolved=false` | Not hard by label, but this scaffold/model combination failed to produce a patch even after the runtime symptom disappeared. |

## What To Look At Later

- `sphinx-doc__sphinx-9591`: inspect the produced patch and verifier logs to understand whether the model found the right code path but made a bad edit.
- `sphinx-doc__sphinx-11510`: inspect the Qwen Code trace for why it exits cleanly with no tracked source diff.
- `matplotlib__matplotlib-26208`: inspect whether the model spent turns on exploration/reproduction and never reached submit, or whether its edits were outside tracked source files.
