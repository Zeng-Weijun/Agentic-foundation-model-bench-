# 离线端到端 Eval — DeepSWE · NL2Repo · RepoZero（给同事:命令 + docker 都在共享盘）

> 三个都是 **Path A（qwen-code 容器内 native）× 官方判分**。命令从各自 evidence bundle 的真实 `launch.sh`/orchestrator 抠出。
> `$B=/mnt/shared-storage-user/mineru2-shared/zengweijun` · `$BM=$B/nips2026/agentic-foundation-model-bench` · serving = pod `100.100.104.147`。
> 真实分数：**DeepSWE×Coder 0/113(valid 0/106)·×Instruct 0/113** ｜ **NL2Repo×Coder honest 14.29%(raw 15.55)·×Instruct honest 1.48%(raw 4.03)** ｜ **RepoZero×Coder 24.5%(10s)/23.75%(5s)·×Instruct 11.50%(node18)/12.75%(node20,10s)**。

---

## 0. 前置:起 serving（sglang 0.5.13,tp=2,两模型同 pod）

```bash
MODEL_ROOT=$B/models
# :30001 = Coder (parser qwen3_coder) ; :30000 = Instruct-2507 (parser qwen)
CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
  --model-path $MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --tp-size 2 --host 0.0.0.0 --port 30001 --context-length 262144 --mem-fraction-static 0.85 \
  --tool-call-parser qwen3_coder --trust-remote-code &
CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
  --model-path $MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507 --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
  --tp-size 2 --host 0.0.0.0 --port 30000 --context-length 262144 --mem-fraction-static 0.85 \
  --tool-call-parser qwen --trust-remote-code &
```
身份核对:`curl -s --noproxy '*' http://100.100.104.147:3000{1,0}/get_model_info | grep <model名>`。

---

## 1. ★Docker 镜像都在共享盘（同事直接 `docker load` 即可,无需联网 pull）

| Bench | 位置（共享盘） | 大小 | 数量 | load 方式 |
|---|---|---|---|---|
| **RepoZero** | `$BM/images/repozero/repoarena-new_latest.tar` | **1.2G** | ★**1 个(全 400 题共用)** | `docker load < repoarena-new_latest.tar`（一次搞定） |
| **NL2Repo** | `$BM/images/nl2repo/*.tar` + manifest `nl2repo_transport_manifest.jsonl` | **124G** | 104（每 task 一个） | driver 自动按 manifest `docker load`(sha256 校验)→跑完 `docker rmi` |
| **DeepSWE** | `$BM/images/deepswe/*.tar` + manifest `full113_final_manifest.jsonl` | **314G** | 102 unique tar（覆盖 113 task,部分共享） | orchestrator 按 manifest `docker load` |

> 每个 `.tar` 旁都有 `.tar.sha256`（load 前可校验）。NL2Repo/DeepSWE 的 manifest 里每行 = `{task, ghcr, harbor_ref, harbor_digest}`（记录镜像来源 + digest）。

---

## 2. DeepSWE（113 task,5 语言 go/py/ts/rust/js,Path A）

- **判分**：pass@1;`resolved = (gold_reward==1) ∧ (agent patch 过同一 verifier)`。gold 先跑证明 harness/镜像/verifier 都对(gold 过 106/113),再判 agent。**无 LLM judge**。
- **口径**：headline **0/113**;valid-only **0/106**（剔 7 个 gold_broken)。5 语言全 0（agent 真跑 100+ turns 但没解出/自我破坏,非 harness bug）。

```bash
# 目录 $BM/deepswe_pathA/（含 deepswe_qwencode_driver.py + full113 orchestrator）
# 原始 run 参数(从 orchestrator.log):manifest=113 unique_tars=102 concurrency=6 turns=100 base=:30001
cd $BM/deepswe_pathA
python3 deepswe_full113_orchestrator.py \
  --base-url http://100.100.104.147:30001/v1 \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct" \
  --manifest $BM/images/deepswe/full113_final_manifest.jsonl \
  --concurrency 6 --turns 100
# Instruct: --base-url :30000  --model Qwen/Qwen3-30B-A3B-Instruct-2507
# 单题原子单元 = deepswe_qwencode_driver.py --mode {agent|gold} --task <id>（orchestrator 内部调）
# 出分:run_root/summary.json + results.jsonl（每行 status/reward）
```
> ⚠️ 精确 CLI flag 以 `deepswe_pathA/` 里的 orchestrator 源码为准（bundle 无独立 launch.sh,此命令按 orchestrator.log 观测参数重建）。

---

## 3. NL2Repo（104 task,NL spec→整库实现,Path A）

- **判分**：官方 `post_processor` 移植 —— strip 模型交的包/测试文件 → overlay 到**全新 base 镜像** `/workspace` → `pip install -e .` + `pytest --network none`(离线 wheelhouse)→ `success_rate = min(passed/total, 1)`（通过占比,非二元）。**无 LLM judge**。
- **★base-image leak 已披露**：官方镜像 site-packages 预装了真 pypi 包,raw 分虚高 → 我们做了 leak-floor 校正:Coder raw 15.55→**honest 14.29%**、Instruct raw 4.03→**honest 1.48%**。见 `nl2repo-coder-leakfloor` 分支。

```bash
# 一键(Coder,:30001);driver 每题自动 docker load→qwen-code→官方判分→rmi
cd $BM/nl2repo_pathA
CONC=8 TURNS=40 ROLLOUT=2400 CMDTO=1800 \
BASE_URL=http://100.100.104.147:30001/v1 \
MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct \
  bash scripts/full104_launch.sh          # setsid 后台,resumable
# Instruct: BASE_URL=:30000 MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
# 出分:runs/full104_<ts>/{aggregate.json, AGGREGATE.txt}(macro_mean_success_rate = 每题 success_rate 均值)
```
★**用 stdin driver**（`nl2repo_qwencode_driver.py`,已修 argv-overflow:spec≥128KB 塞 argv 会让 qwen 不启动;别用 `.PREFIX_argv_bug` 那版）。

---

## 4. RepoZero（Py2JS OFFICIAL 400,Path A,★单一 base 镜像）

- **判分**：`all_pass = (passed==total>0)`,`reward=int(all_pass)`（oracle stdout vs agent 生成 node .mjs stdout 逐行比对）。**无 LLM judge**。
- **口径开关**：`eval_timeout` 10s(run 值) vs 官方 5s;判分 node 版本 node20(run) vs 官方镜像 node18（node-seam,Instruct 影响 1.25pp）。

```bash
docker load < $BM/images/repozero/repoarena-new_latest.tar     # ★单一镜像,全 400 共用
cd $BM/repozero_pathA                                          # 含 repozero_full400_orchestrator.py + full400_launch.sh
WORKERS=4 BASE_URL=http://100.100.104.147:30001/v1 MODEL=Qwen/Qwen3-Coder-30B-A3B-Instruct \
  bash full400_launch.sh                                       # 断点续: RESUME=1 bash full400_launch.sh
# Instruct: BASE_URL=:30000 MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
# 出分:runs/<run_name>/summary.json  (98/400=24.5%@10s)
# 双口径 wrapper: scripts/run_repozero_offline.sh --execute --eval-timeout {10|5} --eval-node {node20|node18}
```
WORKERS ≤8（serving 共享,别抢）。

---

## 5. 三个通用（Path A 共性 + 离线保证）

| 项 | 说明 |
|---|---|
| scaffold | qwen-code 容器内 native,直连本地 serving(不经 relay);SUT=被测模型 |
| 判分 | 全部官方 harness,**都不含 LLM judge**（DeepSWE verifier / NL2Repo post_processor / RepoZero oracle-diff） |
| 镜像 | 全在 `$BM/images/<bench>/`,`docker load` 离线;NL2Repo/DeepSWE per-task(跑完 rmi 省盘),RepoZero 单镜像 |
| 离线 | pytest `--network none` + 离线 wheelhouse(NL2Repo);容器不打外网;serving 走 `no_proxy` |
| 身份 | 每 run before/after `get_model_info`,靠 model_path+seed 钉身份,不信 client label |
| 资源 | DeepSWE 314G / NL2Repo 124G 镜像盘;RepoZero 1.2G。concurrency 别把共享 serving :30001 打满 |

**证据 bundle**（含 calibration/results/serving/SHA256SUMS）:
- `experiments/runs/deepswe_coder_pathA_147/` · `experiments/runs/nl2repo_coder_full104_147/` · `experiments/runs/repozero_coder_full400_147/`
- ×Instruct + NL2Repo leak-floor 在 `evidence/*` 分支（`deepswe-instruct2507-pathA` / `nl2repo-instruct-full104-A,B` / `nl2repo-coder-leakfloor` / `repozero-instruct-full400-A,B`）。
