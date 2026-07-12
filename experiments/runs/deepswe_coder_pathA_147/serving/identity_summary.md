# Serving identity — Qwen3-Coder-30B-A3B-Instruct @ 100.100.104.147:30001

Two phases must be distinguished:

## 1) AGENT / generation phase (this is what produced the patches)
The qwen-code CLI agent generated every patch by calling the self-hosted endpoint:
```
qwen ... --auth-type openai --openai-base-url http://100.100.104.147:30001/v1 \
     --model Qwen/Qwen3-Coder-30B-A3B-Instruct --output-format stream-json --max-session-turns 100
```
(see `agent_run_qwen_command.example.txt`; every task's `verdict/samples/*/agent/qwen_command.txt`
is identical in base-url + model.)

Read-only `/get_model_info` probes of :30001 captured by the generation run:
- **before** (2026-07-12T11:47Z): `_ok=true`, `model_path=.../models/Qwen3-Coder-30B-A3B-Instruct`
- **after**  (2026-07-12T14:33Z): `_ok=true`, `model_path=.../models/Qwen3-Coder-30B-A3B-Instruct`
(`agent_run_get_model_info_before.json` / `_after.json`)

## 2) AUDIT / judging phase (re-scoring)
`mode=audit` performs **NO serving calls** — it only applies gold/agent patches inside the task
container and runs the task's own test.sh. The audit's `/get_model_info` probes
(`audit_get_model_info_before.json` / `_after.json`) merely confirm :30001 still served the same
Coder weights during re-verify.

## Why identity is established by endpoint+weights, not a name string
On self-hosted sglang the request/response `model` string is echoed unvalidated. Only
`/get_model_info -> model_path` proves the weights that answered. All four captures (agent
before/after, audit before/after) resolve to on-disk `Qwen3-Coder-30B-A3B-Instruct`
(`model_type=qwen3_moe`, `Qwen3MoeForCausalLM`). Identity = endpoint :30001 + these weights.
