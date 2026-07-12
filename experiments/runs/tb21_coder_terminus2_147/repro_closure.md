# Reproduction closure

## Harness / dataset / agent
- **terminal-bench == 0.2.18** (venv `.../nips2026/shared_bench/terminal-bench/.venv`, Python 3.13). The venv was the shared-disk python3.13 tb install; `tb` has no `--version` flag, version read via `importlib.metadata.version("terminal-bench")`.
- **agent = terminus-2** (official). Runs on the HOST, reaches serving over HTTP.
- **dataset = terminal-bench-2.1-yaml-full89-r7-final-20260703** (89 task ids; full list in `run.env.summary`).
- **image manifest (r7 closure)**: `.../repo/.worktrees/tb21-image-fixes-r3/manifests/images/terminal_bench_2_1_full89_p0_closure_r7.yaml`.

## Exact tb invocation (from run_console_excerpt.log / run.env.summary)
```
.venv/bin/tb run --agent terminus-2 \
  --model openai/Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --n-concurrent 32 \
  --dataset-path .../terminal-bench-2.1-yaml-full89-r7-final-20260703 \
  --output-path  .../shared_bench/terminal-bench/runs \
  --global-timeout-multiplier 1.0 --global-agent-timeout-sec 7200 --global-test-timeout-sec 7200 \
  --agent-kwarg api_base=http://100.100.104.147:30001/v1 --agent-kwarg temperature=0.0 \
  --no-rebuild  <89x --task-id ...>
```
Environment flags that made this run canonical (vs the 07-10 "false-blocked" line):
`TB21_ENABLE_KVM_DEVICE=0` (canonical r7, no /dev/kvm-derived dataset copy) and
`TB2_RUNTIME_CLOSURE_REPAIR=""` (skip the mutate-the-frozen-dataset repair; static closure gate already proves closed=89/open=0 on r7).

## Serving (sglang)
- host: slime GPU pod `.147` (`100.100.104.147`), port `30001`, model `Qwen3-Coder-30B-A3B-Instruct`.
- sglang 0.5.13, tp2, context 262144, parser qwen3_coder, mem_fraction 0.85, attn fa3, **seed 484925000**, api_key null.

## Docker images (tb2-offline/*, KVM Pod B, docker 26.1.3) — sampled `docker inspect`
248 `tb2-offline/*` images present; `--no-rebuild` used. Samples (local Id + project-registry RepoDigest):

| task | local image Id (sha256) | registry RepoDigest |
|---|---|---|
| build-pmars (resolved) | 32008d23e8ea190637ab66e9152f3a18d2ffebf7da967db7b31f8be31cbb86fd | 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-build-pmars@sha256:7f074452233b04b863d2aef11adc8d4482d31e82c8a4d073ccf07ee7226b71f5 |
| extract-elf (resolved) | f15edf621a02f957fe09ea7f7e062fa6aea89e7d23747f1d9bb2110c0bc40d73 | 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-extract-elf@sha256:c803d406665d25e4ae0044b310e4f0721eb3a07ef61057a3b613c586c87e1833 |
| pypi-server (resolved) | 861bbaaf7742c5aae409cdd45a5bc0ae8845bd746ceed56eb8c2e32f5b7e0f71 | 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-pypi-server@sha256:4b59a734fc833f4749044d366754748c8c30a279d4c35797b7dc17a0069408e5 |
| adaptive-rejection-sampler | 38d89c573031836f61fb465f682ddb0d8d8ef4f298e7cbcc99eb757eb9cbc227 | 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-adaptive-rejection-sampler@sha256:e4748787bc2ec1754dfa787074a755892d7d1053e44d18cac199c0ea4b3b52c7 |
| headless-terminal (parse_error) | c8910c4c6f954b536b23824ef7af0e658ea2f296aa66b25a494a85d8ebf95f31 | 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-headless-terminal@sha256:9e3bf00f3e5c77826d976f05da5194389ed79927a004188b12489265886bb040 |

## Untracked launcher/driver scripts (SHA256) — sign what git did not track
A dual-signed audit noted the launcher / batched-runner / driver are UNTRACKED in the source tree.
They are vendored into `launch.sh` + `scripts/` in this package so they are now committed; their
source-tree SHA256 at collection time:

| script | source sha256 | source-tree git status |
|---|---|---|
| full_run_147.sh (-> launch.sh) | 71606ab0e0a3f122f710e8bc74e2ff5e1478368a4125e37c00a26c75e9e68179 | untracked |
| stage_tb21_official_qwen_launcher.sh (driver/batched-runner) | a9d0434bbfcf80329fa7b20d59ce8f743d488ada1165a8370e05c7e36ba611d7 | **untracked** |
| identity_capture_147.py | 7b0a1f1bcc5af233c3bfbcd1c47fb2bf3468c9fdfb56d993ed17b63feb78370f | untracked |
| assert_net_isolation.sh | 0f5dcc63f95b8b1c34539b50ec7b51893536221e7493a50e980abd58faae695f | untracked |
| dryrun_147.sh | c409ea7ab2b704a9128d964977b705b2a2da0476f2dd103a939a9c18a6bd7843 | untracked |

(Package-internal SHA256 of the committed copies is in `SHA256SUMS`.)

## On-disk source of truth (full artifacts, not vendored due to size)
- tb-native run dir (results.json + 89 per-task dirs w/ agent-logs + sessions/*.cast):
  `.../shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32/`
- batched-runner run_root:
  `.../agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda/tb21_coder_t2_c32_0711211754/medium_c32/attempt_1/tb21_batched_terminus-2_.../`
- launcher log dir (serving captures, net-isolation, disk-watch, console):
  `.../repo/.worktrees/tb21-gpt55-launcher-s55/_coordination/20260625_harbor_bench/logs/tb21_terminus2_147_clean_20260712/`
- full console log: `<launcher log dir>/tb21_coder_run2.out` (333 KB); strict ledger (576 KB) + scores (285 KB) under the launcher worktree `reports/`.
