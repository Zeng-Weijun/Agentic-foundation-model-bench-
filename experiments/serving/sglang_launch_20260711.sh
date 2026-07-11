#!/usr/bin/env bash
# sglang serving for the Qwen reproduction lines — the .140 host in sglang_launch_20260710.sh
# was shut down. This is its replacement, started 2026-07-11T13:10:59 (pod local) and captured
# from the tmux launch + /get_server_info while it was serving. Not reconstructed.
#
#   pod       slime-77777210-q9tqc.zengweijun+root.ailab-sciverseh.pod   (rjob-110d4ab6b5a9ce78-…, 8x H200)
#   pod_ip    100.100.104.147   (internal; replaces dead 100.100.104.140)
#   namespace ailab-sciverseh   (NOT -sciversealign like the KVM bench pods)
#   quota     cards 4-7 only. Cards 0-3 belong to a co-tenant (~130GB each). Do not touch them.
#   version   sglang 0.5.13   (via /get_server_info, both ports)
#   captured  experiments/serving/SERVING_CONFIG_20260711_147.json   (402 server args per port, secrets redacted)
#
# ── Identity fingerprint (the thing that makes a run attributable to THIS serving) ──
#   :30000  Qwen3-30B-A3B-Instruct-2507   parser=qwen          random_seed=61643818   tp=2  mem_frac=0.85
#   :30001  Qwen3-Coder-30B-A3B-Instruct  parser=qwen3_coder   random_seed=484925000  tp=2  mem_frac=0.85
#   Both: --context-length 262144, --trust-remote-code. chat smoke 2026-07-11: both returned 'alive'.
#
# ── Reachability (verified 2026-07-11, sglang up) ──────────────────────────────
#   dev            → 100.100.104.147:30000 HTTP 200   :30001 HTTP 200   (--noproxy '*')
#   KVM Pod B      → .147 ping OK + route present (bench executor host)
#   Cross-pod serving confirmed usable for scored runs. Point launchers at .147, NOT .140.
#
# ── Same caveat as the .140 file: sglang does NOT validate the `model` field ────
# Asking :30000 for the Coder name returns HTTP 200 and runs Instruct-2507 anyway. Always pin
# identity by (port, random_seed, model_path from /get_model_info) — never trust the echoed name.
#
# ── Verbatim launch (what tmux actually ran; PATH/LD needed for nvidia-smi visibility) ─────────
set -euo pipefail
MODEL_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/models
export PATH=/usr/local/nvidia/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}

# Instruct-2507 on cards 4,5 → :30000
tmux new-session -d -s sgl_instruct \
  "CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507 \
     --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
     --tp-size 2 --host 0.0.0.0 --port 30000 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen --trust-remote-code 2>&1 | tee /tmp/sgl_instruct.log"

# Coder-30B on cards 6,7 → :30001
tmux new-session -d -s sgl_coder \
  "CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct \
     --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
     --tp-size 2 --host 0.0.0.0 --port 30001 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen3_coder --trust-remote-code 2>&1 | tee /tmp/sgl_coder.log"
