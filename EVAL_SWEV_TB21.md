# 离线端到端 Eval — SWE-V & TB2.1（可直接跑的命令 + 配置）

> 全部命令从各自 evidence bundle 的真实 `launch.sh` / serving 脚本抠出（未编造）。
> 执行机 = KVM Pod B `env-kvm-57740737-bzw56`（privileged docker 26.1.3）；serving = pod `100.100.104.147`。
> 真实分数：**SWE-V×Coder 46.8%(234/500) · ×Instruct 24.0%(120/500)** ｜ **TB2.1×Coder 11.24%(10/89) · ×Instruct 3.37%(3/89)**。

---

## 0. 前置:起 serving（sglang 0.5.13,两模型同 pod,tp=2）

`experiments/serving/sglang_launch_20260711.sh` 原文:

```bash
#!/usr/bin/env bash
set -euo pipefail
MODEL_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/models
export PATH=/usr/local/nvidia/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}

# :30000 = Instruct-2507  (parser qwen)
tmux new-session -d -s sgl_instruct \
  "CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507 \
     --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
     --tp-size 2 --host 0.0.0.0 --port 30000 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen --trust-remote-code 2>&1 | tee /tmp/sgl_instruct.log"

# :30001 = Coder-30B  (parser qwen3_coder ← 关键,工具调用解析靠它)
tmux new-session -d -s sgl_coder \
  "CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct \
     --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
     --tp-size 2 --host 0.0.0.0 --port 30001 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen3_coder --trust-remote-code 2>&1 | tee /tmp/sgl_coder.log"
```

**身份核对（每次跑前必做,不信 client label）:**
```bash
curl -s --noproxy '*' http://100.100.104.147:30001/get_model_info | grep Qwen3-Coder-30B-A3B-Instruct   # Coder
curl -s --noproxy '*' http://100.100.104.147:30000/get_model_info | grep Qwen3-30B-A3B-Instruct-2507    # Instruct
```
serving 身份靠 `model_path`+seed 钉死（Coder seed 484925000 / Instruct 61643818）。

---

## 1. SWE-V（SWE-bench Verified,500 Python,官方判定）

- **scaffold**: qwen-code 0.15.6（容器内 native）· **判分**: SWE-bench Verified 官方 `FAIL_TO_PASS 全过 ∧ PASS_TO_PASS 全过`
- **配置形态**: 纯 CLI 参数,**无 yaml**（`full500_qwencode_orchestrator_v21.py`）
- **离线**: `HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1` + 镜像本地已 load + `no_proxy` 含 serving host

### 1a. Coder（:30001 → 期望 234/500 = 46.8%）

```bash
#!/usr/bin/env bash
set -uo pipefail
WT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/swev-qwencode-v21-agent51
PY=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python
BASE=http://100.100.104.147:30001/v1 ; INFO=http://100.100.104.147:30001
TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_${TS}
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/serving" ; cd "$WT"

# 身份 guard（before）
curl -s --max-time 8 --noproxy '*' "$INFO/get_model_info" > "$RUN_ROOT/serving/get_model_info_before.json"
grep -q Qwen3-Coder-30B-A3B-Instruct "$RUN_ROOT/serving/get_model_info_before.json" || { echo FATAL serving mismatch; exit 3; }

export DOCKER_HOST=unix:///var/run/docker.sock
export OPENAI_API_KEY=EMPTY
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.147"
export NO_PROXY="$no_proxy"

"$PY" scripts/full500_qwencode_orchestrator_v21.py \
  --run-root "$RUN_ROOT" --base-url "$BASE" \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct" --reasoning-effort "" \
  --agent-scaffold qwencode --qwen-code-version 0.15.6 \
  --concurrency 15 --min-free-pct 8 --min-free-gb 300 --disk-guard-path / --keep-images \
  > "$RUN_ROOT/logs/runner.log" 2>&1

# 身份 guard（after,趁 sglang 没关）
curl -s --max-time 8 --noproxy '*' "$INFO/get_model_info" > "$RUN_ROOT/serving/get_model_info_after.json"
echo "resolved=$(grep -c '\"resolved\": true' $RUN_ROOT/results.jsonl)/$(wc -l < $RUN_ROOT/results.jsonl)"
```

### 1b. Instruct-2507（同脚本,只换三处 → 期望 120/500 = 24.0%）
```
BASE / INFO 端口 30001 → 30000
--model "Qwen/Qwen3-Coder-30B-A3B-Instruct" → "Qwen/Qwen3-30B-A3B-Instruct-2507"
身份 grep Qwen3-Coder-30B-A3B-Instruct → Qwen3-30B-A3B-Instruct-2507
```

### 1c. 出分
`results.jsonl` 每行一 instance,`resolved:true` 计数 / 500。denom_assert 要求 `results.jsonl 行数 == dataset 500`。

---

## 2. TB2.1（terminal-bench 2.1,full-89,官方 terminus-2 harness,tb 0.2.18）

- **scaffold**: terminus-2（跑在 host,容器 `network_mode: none`）· **配置形态 = yaml 数据集**
- **★"yaml" = 89 个 task 的 yaml 数据集**: `terminal-bench-2.1-yaml-full89-r7-final-20260703`（`tb_dataset_name=terminal-bench/terminal-bench-2-1`）
- **tb 二进制**: `/mnt/.../shared_bench/terminal-bench/.venv/bin/tb`
- 一键入口 `full_run_147.sh <coder|instruct>`,内部调官方 launcher。

### 2a. 关键离线/正确性 env（踩过的坑,必须设）
```bash
export DOCKER_HOST=unix:///var/run/docker.sock
export TB21_ALLOW_PRIVILEGED_DOCKER=1
export TB21_ENABLE_KVM_DEVICE=0        # FIX1: 别用 kvm 派生数据集副本,回到 canonical r7
export TB2_RUNTIME_CLOSURE_REPAIR=""   # FIX2: 别跑 closure repair(会改冻结的共享数据集)
export OPENAI_API_KEY=tb-terminus2-placeholder
export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
export NO_PROXY="100.100.104.147,127.0.0.1,localhost,::1,10.0.0.0/8,100.96.0.0/12,100.100.0.0/16,.pjlab.org.cn"
```

### 2b. 核心调用（`full_run_147.sh` 内部,coder 期望 10/89=11.24% / instruct 3/89=3.37%）
```bash
# coder:    PORT=30001  MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct  LAUNCHER=stage_tb21_official_qwen_launcher.sh
# instruct: PORT=30000  MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507   LAUNCHER=stage_tb21_official_qwen_launcher_terminus2.sh(打过 patch 接受 Instruct)
BASE_URL="http://100.100.104.147:$PORT/v1"
RUN_ID="tb21_${TAG}_t2_c32_$(date -u +%m%d%H%M%S)"   # 必须全小写(uppercase 会 fork run_root)

bash "$LAUNCHER" \
  --execute \
  --mode medium \
  --attempts all \
  --concurrency 32 \
  --model "$MODEL" \
  --relay-url "$BASE_URL" \
  --timeout-sec 7200 \
  --timeout-multiplier 1.0 \
  --run-id "$RUN_ID"
```
launcher 内部 = `tb run`,数据集固定指 `terminal-bench-2.1-yaml-full89-r7-final-20260703`（89 task）,agent=terminus-2,pass@1,c=32。

### 2c. ★两个"假 blocked"陷阱（07-10 曾误判,必避）
1. **别在 teardown 时 SIGTERM/^C tb 进程** → 否则 batch-level `tb_rc=143` 让 89 行全继承 `infra_fail=89`(假)。跑到自然 exit 0;teardown 真卡就调大 `TB_DOCKER_COMPOSE_DOWN_TIMEOUT_SEC`,别 kill。
2. **`external_network_marker`(~10-12) 是预期不是污染**：89 个 compose 都 pin `network_mode: none`,terminus-2 跑在 host 上。

### 2d. 出分
`summary.json` 里 `resolved / 89`。launch.sh 自带:数据集断言(`tb_dataset_path` 必须 == r7 + `tb_task_ids` 计数 == 89)、运行时 net-isolation 采样(`NetworkMode==none`)、身份 before/after(`identity_capture_147.py`)、磁盘 watch(<10% 停)。

---

## 3. 离线保证 & 口径纪律（两 bench 通用）

| 项 | 保证 |
|---|---|
| 推理离线 | SUT 全走本地 sglang `:30001/:30000`;`no_proxy` 含 serving host;不打外网 |
| 数据离线 | SWE-V `HF_*_OFFLINE=1`;TB2.1 数据集是共享盘冻结的 r7 yaml |
| 镜像离线 | 提前 `load_offline_images.sh` 本地 load,`--keep-images` |
| 判分 | SWE-V=官方 FAIL/PASS_TO_PASS;TB2.1=官方 terminus-2 harness;都不含 LLM judge |
| 身份 | 每次 before/after `get_model_info` grep,serving 身份靠 model_path+seed,不信 client label |
| 网络隔离 | TB2.1 容器 `network_mode:none` + 运行时采样断言 |

**SWE-V 无 yaml（CLI 参数式）;TB2.1 的"yaml"= 89 个 task 的 terminal-bench yaml 数据集。**
两条都是 evidence bundle 里 `launch.sh` 的真实复刻,证据在 `experiments/runs/{swev_coder_full500_v5_147, tb21_coder_terminus2_147}/`。
