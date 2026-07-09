#!/usr/bin/env bash
# sglang serving for the Qwen reproduction lines — captured verbatim from `ps -eo args`
# on the 4-card host, 2026-07-10T01:40Z. Not reconstructed, not idealised: this is
# what was actually running while the runs below were executing.
#
#   host      100.100.104.140  (rjob-1577c47262481b45-...-0, 8x H200)
#   quota     cards 4-7 only. Cards 0-3 belong to another tenant. Do not touch them.
#   version   sglang 0.5.13  (via /get_server_info)
#   captured  experiments/serving/SERVING_CONFIG_20260710.json  (402 server args per port, secrets redacted)
#
# ── Why this file exists ───────────────────────────────────────────────────────
# The serving stack that produced the canonical Qwen scores was never recorded
# alongside its runs. Its host (100.103.228.120) is now dead. The scores survive;
# the conditions that produced them do not. That is not recoverable, and it is the
# reason §0 makes `serving_config` mandatory.
#
# ── Read this before pointing anything at these ports ─────────────────────────
# sglang does NOT validate the `model` field. Ask :30000 for the Coder model and it
# returns HTTP 200, runs Instruct-2507, and echoes "Qwen3-Coder-30B-A3B-Instruct"
# back at you in the response body. Verified 2026-07-10:
#
#     curl :30000/v1/chat/completions -d '{"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct",...}'
#     -> HTTP 200, {"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct","content":"OK",...}
#     while /get_model_info reports model_path=.../Qwen3-30B-A3B-Instruct-2507
#
# So the `model` string in a request, in a response, or in an agent trace is not
# evidence of which weights ran. It is a string you sent to a server that echoes it.
# The only identification of the weights is `model_path` from `/get_model_info`,
# fetched from that exact host:port at run time. Ports are not stable identifiers
# either: :30000 served Coder-30B on the old host and serves Instruct-2507 here.

set -euo pipefail

export PATH=/usr/local/nvidia/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:$LD_LIBRARY_PATH
# ^ nvidia-smi needs BOTH. With only PATH set it fails with a driver-mismatch error
#   that reads like a broken install.

MODEL_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/models

# ── :30000 — Qwen3-30B-A3B-Instruct-2507 ──────────────────────────────────────
# tmux session `sgl_instruct`, up since 2026-07-09T08:24:33.
# NOTE the parser: `qwen`, not `qwen3_coder`. A qwen-code scaffold speaks the
# Coder tool-call dialect; this server will not parse it, will emit zero tool
# calls, and will score 0 while every quality gate reports success.
CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
  --model-path "$MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507" \
  --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
  --tp-size 2 \
  --host 0.0.0.0 --port 30000 \
  --context-length 262144 \
  --mem-fraction-static 0.85 \
  --tool-call-parser qwen \
  --trust-remote-code 2>&1 | tee /tmp/sgl_instruct.log

# ── :30001 — Qwen3-Coder-30B-A3B-Instruct ─────────────────────────────────────
# tmux session `sgl_coder`, up since 2026-07-09T08:24:33.
CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
  --model-path "$MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct" \
  --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --tp-size 2 \
  --host 0.0.0.0 --port 30001 \
  --context-length 262144 \
  --mem-fraction-static 0.85 \
  --tool-call-parser qwen3_coder \
  --trust-remote-code 2>&1 | tee /tmp/sgl_coder.log

# ── Verify what is actually serving, before trusting any score ────────────────
#   curl -s --noproxy '*' http://100.100.104.140:30000/get_model_info | jq .model_path
#   curl -s --noproxy '*' http://100.100.104.140:30001/get_model_info | jq .model_path
#   curl -s --noproxy '*' http://100.100.104.140:30001/get_server_info \
#     | jq '{tp_size,context_length,mem_fraction_static,tool_call_parser,attention_backend,version}'
#
# Expected for :30001
#   tp_size 2 · dp_size 1 · context_length 262144 · mem_fraction_static 0.85
#   tool_call_parser qwen3_coder · attention_backend fa3 · dtype auto
#   quantization None · reasoning_parser None · version 0.5.13
