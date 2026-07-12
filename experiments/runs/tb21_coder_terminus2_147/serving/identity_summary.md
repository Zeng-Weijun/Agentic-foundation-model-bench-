# Serving identity — before + after (IDENTITY_OK both)

Read-only `/get_model_info` + `/get_server_info` were captured immediately BEFORE the
tb run started and immediately AFTER it finished (the launcher `identity_capture_147.py`
never runs inference; it also scans values for leaks -> `value_scan_leaks=0`,
`api_key type=NoneType`, values never printed).

| field | before | after |
|---|---|---|
| verdict | IDENTITY_OK | IDENTITY_OK |
| model_path | .../models/Qwen3-Coder-30B-A3B-Instruct | .../models/Qwen3-Coder-30B-A3B-Instruct |
| tokenizer_path | .../models/Qwen3-Coder-30B-A3B-Instruct | .../models/Qwen3-Coder-30B-A3B-Instruct |
| served_model_name | Qwen/Qwen3-Coder-30B-A3B-Instruct | Qwen/Qwen3-Coder-30B-A3B-Instruct |
| architecture | Qwen3MoeForCausalLM | Qwen3MoeForCausalLM |

Server config (from get_server_info_after.json, sglang):

- endpoint: `http://100.100.104.147:30001/v1`  (slime GPU pod .147, Coder port 30001)
- version 0.5.13 | context_length 262144 | tp 2 | tool-call-parser qwen3_coder
- mem_fraction_static 0.85 | attention_backend fa3 | **random_seed 484925000**
- max_total_num_tokens 1946895 | max_prefill_tokens 16384 | api_key = null (no auth)
- request-side: temperature 0.0, api_base http://100.100.104.147:30001/v1

Why this matters: on this stack the request/response `model` string is NOT validated
(self-hosted sglang echoes any name; the API relay does the same). Only
`/get_model_info -> model_path` proves the weights that answered. Both captures resolve to
the on-disk Qwen3-Coder-30B-A3B-Instruct weights, so the identity is established by the
endpoint+weights, not by a trusted name field.
