# TB2.1 x QwenCode Native Full89 20260706

- Agent: host-side QwenCode 0.15.6 with docker-exec bridge (`qwen-code-host-bridge`).
- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`; base URL `http://100.103.228.120:30000/v1`; reasoning effort disabled/empty.
- Run: `tb21_full89_batched_batch_01_of_01_qwen-code-host-bridge_c32_qwencode_full89_c32_20260706t08041783325051z`; concurrency c32; attempts=1.
- Raw score: 15/89 = 16.8539%.
- Strict clean_pass: 15/89; infra_fail=1; timeout=1; parse_error=0; missing_artifact=0. Raw failure modes: unset=87, test_timeout=1, agent_timeout=1.
- Docker residue after run: checked as 0 running containers at closeout.

## Resolved Tasks
- adaptive-rejection-sampler
- build-pmars
- cancel-async-tasks
- configure-git-webserver
- constraints-scheduling
- fix-git
- hf-model-inference
- kv-store-grpc
- modernize-scientific-stack
- multi-source-data-merger
- nginx-request-logging
- polyglot-rust-c
- portfolio-optimization
- pypi-server
- pytorch-model-cli

## Timeout/Infra Rows
- sqlite-with-gcov: strict_status=timeout notes=['fatal_timeout']

## External Network Markers
- pypi-server: Home-page: https://github.com/qwen/vectorops
- sam-cell-seg: https://github.com/pytorch/pytorch/blob/main/SECURITY.md#untrusted-models for more details). In a future release, the default value for `weights_only` will be | /usr/local/lib/python3.11/site-packages/mobile_sam/build_sam.py:91: FutureWarning: You are using `torch.load` with `weights_only=False` (the current default value), which uses the default pickle module implicitly. It is possible to construc

## Artifacts
- results_json: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_qwen-code-host-bridge_c32_qwencode_full89_c32_20260706t08041783325051z/results.json`
- strict_summary: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_qwencode_full89/tb21_batched_qwen-code-host-bridge_qwencode_full89_c32_20260706t08041783325051z/batch_01_of_01/tb21_strict_summary.json`
- launcher_log: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-image-fixes-r3/_coordination/20260625_harbor_bench/logs/tb21_qwencode_full89_qwencode_full89_c32_20260706t08041783325051z.log`
