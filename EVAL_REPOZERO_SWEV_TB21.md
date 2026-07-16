# 离线端到端 Eval — RepoZero · SWE-V · TB2.1（一键命令 + docker 镜像用在哪）

> 命令全部从各自 evidence bundle 的真实 `launch.sh`/serving 脚本抠出（未编造）。
> 执行机 = KVM Pod B `env-kvm-57740737-bzw56`（privileged docker 26.1.3）；serving = pod `100.100.104.147`；
> `$B=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`。
> 真实分数：**SWE-V×Coder 46.8%(234/500)·×Instruct 24.0%(120/500)** ｜ **TB2.1×Coder 11.24%(10/89)·×Instruct 3.37%(3/89)** ｜ **RepoZero×Coder 24.5%(10s)/23.75%(5s)·×Instruct 11.50%(node18)/12.75%(node20,10s)**。

---

## 0. 前置:起 serving（sglang 0.5.13,两模型同 pod,tp=2）

```bash
MODEL_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/models
export PATH=/usr/local/nvidia/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}

# :30000 = Instruct-2507 (parser qwen)
tmux new-session -d -s sgl_instruct \
  "CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507 --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
     --tp-size 2 --host 0.0.0.0 --port 30000 --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen --trust-remote-code 2>&1 | tee /tmp/sgl_instruct.log"

# :30001 = Coder-30B (parser qwen3_coder ← 工具调用解析靠它)
tmux new-session -d -s sgl_coder \
  "CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
     --tp-size 2 --host 0.0.0.0 --port 30001 --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen3_coder --trust-remote-code 2>&1 | tee /tmp/sgl_coder.log"
```
身份核对（每跑必做,不信 client label）：`curl -s --noproxy '*' http://100.100.104.147:3000{1,0}/get_model_info | grep <model名>`。

---

## 1. ★Docker 镜像用在哪（三个 bench 各不同）

| Bench | 镜像 | 位置 | 数量/大小 | 怎么用 |
|---|---|---|---|---|
| **RepoZero** | ★**单一 base** `ghcr.io/jessezzzzz/repoarena-new:latest` | `$B/images/repozero/repoarena-new_latest.tar` | **1 个（全 400 题共用）** 1.2G | `docker load < repoarena-new_latest.tar`;每题在同一镜像内起容器跑 |
| **TB2.1** | 每 task 一套 compose 容器（r67 离线批） | `$B/images/terminalbench2.1/`（`offline-e2e-r67{local,p0,p1,p3}` 等 18 dir） | **89 task** 130G | terminus-2 harness 从 r67 yaml 起 compose,容器 `network_mode:none` |
| **SWE-V** | 每 instance 一个 `swebench/sweb.eval.x86_64.<id>` | 预载入**本地 docker daemon**;`$B/images/swebench/` 存样本(`django10097` 2.7G) | **500 per-instance** | orchestrator 起容器判分,`--keep-images` 保留;★全 500 须先 pull/build 入本地 daemon |

**统一离线 load**：`scripts/load_offline_images.sh --load`（manifest `manifests/offline_images.example.yaml`,`--asset-root $B`,`DOCKER_HOST` 默认 rootless `unix:///tmp/rl/run/docker.sock`）。先 `--check` 看清单齐不齐再 `--load`。

---

## 2. RepoZero（Py2JS OFFICIAL 400,qwen-code Path A）

- **镜像**：单一 `repoarena-new`（先 `docker load`）· **判分**：`all_pass=(passed==total>0)`,`reward=int(all_pass)`,**不含 LLM**
- **口径开关**：`eval_timeout` 10s（run 用值）vs 官方 5s；判分 node 版本 node20(run) vs 官方镜像 node18（node-seam,见 AUDIT_NOTES §3）

```bash
# 一键（Coder,:30001 → 98/400=24.5%@10s / 95/400=23.75%@5s）
docker load < $B/images/repozero/repoarena-new_latest.tar
cd <repozero_pathA>            # 含 repozero_full400_orchestrator.py + full400_launch.sh
WORKERS=4 \
BASE_URL=http://100.100.104.147:30001/v1 \
MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct \
  bash full400_launch.sh
# 断点续:   RESUME=1 bash full400_launch.sh
# 出分:     runs/<run_name>/summary.json

# Instruct(:30000 → 11.50%strict-node18 / 12.75%node20@10s)
WORKERS=4 BASE_URL=http://100.100.104.147:30000/v1 \
MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507 bash full400_launch.sh
```
launcher 内部 = preflight（`curl /v1/models` grep Qwen3-Coder）→ setsid `python3 repozero_full400_orchestrator.py --run-name --workers --base-url --model [--resume]`。WORKERS ≤8（serving 共享别抢）。
仓里另有 wrapper `scripts/run_repozero_offline.sh --execute`（带 `--eval-timeout {10|5}` + `--eval-node {node20|node18}` 双口径开关）。

---

## 3. SWE-V（SWE-bench Verified 500 Python,qwen-code 0.15.6）

- **镜像**：per-instance sweb.eval（预载 daemon）· **判分**：官方 `FAIL_TO_PASS 全过 ∧ PASS_TO_PASS 全过` · **无 yaml（CLI）**

```bash
WT=$B/repo/.worktrees/swev-qwencode-v21-agent51
PY=/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python
BASE=http://100.100.104.147:30001/v1 ; INFO=http://100.100.104.147:30001   # Coder
RUN_ROOT=$B/runs/swev_coder_full500_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/serving" ; cd "$WT"

curl -s --noproxy '*' "$INFO/get_model_info" > "$RUN_ROOT/serving/get_model_info_before.json"
grep -q Qwen3-Coder-30B-A3B-Instruct "$RUN_ROOT/serving/get_model_info_before.json" || { echo FATAL; exit 3; }
export DOCKER_HOST=unix:///var/run/docker.sock OPENAI_API_KEY=EMPTY
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface
export no_proxy="10.0.0.0/8,100.96.0.0/12,.pjlab.org.cn,localhost,127.0.0.1,100.100.104.147" NO_PROXY="$no_proxy"

"$PY" scripts/full500_qwencode_orchestrator_v21.py \
  --run-root "$RUN_ROOT" --base-url "$BASE" \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct" --reasoning-effort "" \
  --agent-scaffold qwencode --qwen-code-version 0.15.6 \
  --concurrency 15 --min-free-pct 8 --min-free-gb 300 --disk-guard-path / --keep-images \
  > "$RUN_ROOT/logs/runner.log" 2>&1

curl -s --noproxy '*' "$INFO/get_model_info" > "$RUN_ROOT/serving/get_model_info_after.json"
echo "resolved=$(grep -c '\"resolved\": true' $RUN_ROOT/results.jsonl)/$(wc -l < $RUN_ROOT/results.jsonl)"
```
**Instruct**：端口 30001→30000、`--model`→`Qwen/Qwen3-30B-A3B-Instruct-2507`、身份 grep 换 `Qwen3-30B-A3B-Instruct-2507`。出分 = `results.jsonl` 里 `resolved:true` / 500。

---

## 4. TB2.1（terminal-bench 2.1 full-89,官方 terminus-2 harness,tb 0.2.18）

- **镜像**：`images/terminalbench2.1/` 的 r67 批（terminus-2 起 compose,容器 `network_mode:none`）· **★"yaml" = 89 task 数据集** `terminal-bench-2.1-yaml-full89-r7-final-20260703`

```bash
export DOCKER_HOST=unix:///var/run/docker.sock TB21_ALLOW_PRIVILEGED_DOCKER=1
export TB21_ENABLE_KVM_DEVICE=0        # FIX1: 用 canonical r7,别用 kvm 派生副本
export TB2_RUNTIME_CLOSURE_REPAIR=""   # FIX2: 别改冻结的共享数据集
export OPENAI_API_KEY=tb-terminus2-placeholder
export http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
export NO_PROXY="100.100.104.147,127.0.0.1,localhost,::1,10.0.0.0/8,100.96.0.0/12,100.100.0.0/16,.pjlab.org.cn"

bash full_run_147.sh coder      # Coder(:30001) → 10/89=11.24%
# bash full_run_147.sh instruct # Instruct(:30000) → 3/89=3.37%(用 patch 过的 launcher 接受 Instruct)
```
`full_run_147.sh` 内部核心：
```bash
BASE_URL="http://100.100.104.147:$PORT/v1"   # coder=30001 / instruct=30000
RUN_ID="tb21_${TAG}_t2_c32_$(date -u +%m%d%H%M%S)"   # 必须全小写
bash "$LAUNCHER" --execute --mode medium --attempts all --concurrency 32 \
  --model "$MODEL" --relay-url "$BASE_URL" --timeout-sec 7200 --timeout-multiplier 1.0 --run-id "$RUN_ID"
#  LAUNCHER: coder=stage_tb21_official_qwen_launcher.sh / instruct=..._terminus2.sh(patch 接受 Instruct)
#  内部 = tb run,数据集固定 terminal-bench-2.1-yaml-full89-r7,agent=terminus-2,pass@1,c=32
```
★**两个"假 blocked"坑**：① 别 teardown 时 SIGTERM tb 进程（否则 `tb_rc=143` → 89 行全假 `infra_fail`,跑到自然 exit 0）；② `network_mode:none` 的 `external_network_marker`(~10-12) 是预期不是污染。
出分 = `summary.json` 里 `resolved / 89`。

---

## 5. 离线保证 & 口径纪律

| 项 | 保证 |
|---|---|
| 推理离线 | SUT 全走本地 sglang `:30001/:30000`,`no_proxy` 含 serving host,不打外网 |
| 数据离线 | SWE-V `HF_*_OFFLINE=1`；TB2.1 冻结 r7 yaml；RepoZero 单镜像自带 |
| 镜像离线 | RepoZero 单 tar `docker load`；TB2.1 r67 批；SWE-V per-instance 预载 daemon；统一 `load_offline_images.sh --load` |
| 判分 | 都是官方 harness,**不含 LLM judge**（SWE-V FAIL/PASS_TO_PASS · TB2.1 terminus-2 · RepoZero oracle stdout 逐行）|
| 身份 | 每次 before/after `get_model_info`,靠 model_path+seed 钉身份 |
| 网络隔离 | TB2.1 容器 `network_mode:none` + 运行时采样断言 |

证据：`experiments/runs/{repozero_coder_full400_147, swev_coder_full500_v5_147, tb21_coder_terminus2_147}/`（各含 `launch.sh`/`calibration.md`/`results`/`serving`/`SHA256SUMS`）。
