# CERT_A — TB2.1 × Qwen3-Coder-30B × terminus-2 官方复现认证 (第一签核人)

- **审计人**: 第一签核人 (Claude Opus 4.8), 独立于第二签核人, 互不可见
- **审计时刻 (UTC)**: 2026-07-10 ~09:00–09:30Z
- **审计对象 run_root**:
  `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0710064916_attempt1_medium_c32`
- **canonical run_root** (自行定位, 见 §2):
  `/mnt/.../shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_qwen_official_medium_c32_stage1_20260705t15481783266492z_attempt1_medium_c32`
  start_time `2026-07-05T15:55:10Z`, accuracy `0.10112359550561797` = **9/89** ✓ (与任务给定 canonical 锚一致)
- **本 run 状态**: 审计期间 **收尾完成**。`full.rc=143` 于 17:15 local 写出; `tb run` 进程 (pid 1203963) 已退出。**Condition 6 由 PENDING 转为可判**。

## 最终判定: **B — 官方 harness 的复现, 但 serving 栈不同 (declared deviation)**

Condition 5 = REFUTED (canonical serving 栈未记录, 原理上不可证等同); Condition 1/2/3/4/6 = CONFIRMED。
**尽力 REFUTE 失败**: 无法证明它不是"官方 harness 复现"; 但明确证明它**不是 strict 官方复现 (A)**, 因 serving 栈差异且 canonical 侧无记录。

---

## Condition 1 — harness 是否未经修改的官方 terminus-2 —— **CONFIRMED (附声明)**

- `run_metadata.agent_name` = `"terminus-2"`; live cmdline `--agent terminus-2`
  (run_root/`run_metadata.json` L "agent_name": "terminus-2"; `/proc/1203963/cmdline`).
  → 是 terminus-2 路径, **不是**两个非官方 harness (qwen-code-host-bridge / qwen-code 容器内原生): 本 run 走 `Terminus2` → `LiteLLM` → `litellm.completion(api_base=…:30001)`, 无 `--allowed-tools run_tb_command` 限制, 无宿主机 `docker exec` 桥。
- **比对方法**: vendored 库为 git checkout `/mnt/.../shared_bench/terminal-bench` (editable `.pth`), 版本 `terminal_bench-0.2.18`, HEAD `1a6ffa96…` == `run_metadata.commit_hash`; remote = `github.com/harbor-framework/terminal-bench.git`; `git branch -r --contains HEAD` → `origin/main` (真上游 commit)。用 `git status --porcelain` + `git diff` 对 working tree 与该 commit 逐文件比对。
- **★ working tree 是 dirty 的** (18 项), 含 `terminal_bench/agents/terminus_2/terminus_2.py`、`harness/harness.py`、`llms/lite_llm.py`、`handlers/trial_handler.py`、`terminal/{docker_compose_manager,tmux_session}.py`。`commit_hash` **不捕获**这些未提交改动。逐一评估对**本 run 配置**的行为影响:
  - `terminus_2.py` (+6 行) 与 `lite_llm.py` (+8 行): 仅新增 `reasoning_effort` 透传, 逻辑 `if self._reasoning_effort is not None: completion_kwargs.setdefault(...)`。本 run `REASONING_EFFORT=`(空, 见 `/proc/1203963/environ`), 命令未传 → `completion_kwargs == kwargs` → **与上游 `**kwargs` 调用路径逐字节等价 (INERT)**。
  - terminus-2 的**决策核心** (prompt-templates/terminus-json-plain.txt, terminus_json_plain_parser.py) 在 `git status` 中**未列出 = clean = 上游一致**。
  - `harness.py` (+13): env-gate `TB_SKIP_TEST_COPY_TASK_IDS` 跳过运行期 test 拷贝。本 run 该 env = **全 89 task** → 走 baked `/tests`。**测量中性性由 Condition 4 的 closure=[] + 静态 gate 89/89 closed 证成** (baked `/tests` == 数据集 run_tests, 逐字节)。
  - `trial_handler.py` (+8): `TB21_ORACLE_PREFER_SOLUTION_YAML` **仅影响 oracle agent**, 本 run 是 terminus-2 → 无关。
  - `tmux_session.py` (+7, mtime 2026-05-26) / `docker_compose_manager.py` (+130, 全 env-gate 的 docker-SDK 版本/teardown/force-rm fallback; `TB_DOCKER_COPY_METHOD` 未设 → cp 分支未触发): 皆 terminal/teardown 基础设施层, 且 mtime 均**早于 canonical**, canonical 与本 run 用**同一 tree** (见下 mtime)。
- 6 个改动文件 mtime 均早于 run 启动 (06:52Z) 且早于 canonical: terminus_2.py `07-04 03:38`, harness.py `07-02 09:27`, lite_llm.py `07-04 03:37`, trial_handler.py `07-04 01:51`, docker_compose_manager.py `07-02 10:09`, tmux_session.py `05-26`。
- **结论**: 是官方 terminus-2 agent; 决策/测量相关代码路径对本 run 配置**上游等价**; 全部 active 改动要么 INERT (reasoning_effort), 要么 closure-verified 等价 (test-copy), 要么与 canonical 完全相同的基础设施补丁。**声明**: 严格字面 "未修改" 不成立 (dirty tree), 但改动对测量中性且与复现目标 canonical 一致。

## Condition 2 — 命令是否同口径 —— **CONFIRMED**

- 独立取两 run 的 `command.sh` 并 token 级 diff:
  - 本 run: `/mnt/.../agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda/tb21_coder_t2_c32_0710064916/medium_c32/attempt_1/tb21_batched_terminus-2_…/batch_01_of_01/command.sh`
  - canonical: 同结构, run-id = `…_stage1_20260705t15481783266492z_…`
- 差异**仅两项**: `--agent-kwarg api_base=http://100.103.228.120:30000/v1` (canonical) vs `…100.100.104.140:30001/v1` (本 run); 以及 run-id label token (输出目录名, 非测量 flag)。
- **全同 (token 级)**: `--agent terminus-2` · `--model openai/Qwen/Qwen3-Coder-30B-A3B-Instruct` · `--n-concurrent 32` · `--dataset-path …-r7-final-20260703` · 89 个 `--task-id` (集合与顺序一致) · `--global-timeout-multiplier 1.0` · `--global-agent-timeout-sec 7200` · `--global-test-timeout-sec 7200` · `--agent-kwarg temperature=0.0` · `--no-rebuild`。
- 独立复核第二工程师结论: 属实。唯一非-task flag 差异 = `api_base`。

## Condition 3 — 数据集是否字节相同 —— **CONFIRMED**

- 数据集 `/mnt/.../shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703`, 1002 files。
- Merkle (sorted per-file sha256 再 sha256) = `4e0416e04c19d2e1ec8d4cf252650f476a9ecd42c8cc8dd60afa3b0591e8e18e`。
- 冻结证据: `find -newermt` 全库最新 mtime = `configure-git-webserver/solution.sh` @ `2026-07-04 05:26:09Z`; **早于 canonical (07-05) 与本 run (07-10)**。
  - files newer than `2026-07-05 00:00Z` = **0**; newer than `2026-07-04 05:27Z` = **0**。
- ⇒ canonical 跑时 (07-05) 与本 run 跑时 (07-10) 的数据集**字节相同** (自 07-04 05:26Z 起无任何文件改动)。

## Condition 4 — 脚本 provenance / 是否降 gate —— **CONFIRMED**

- 三处中和证据**独立复核, 全部成立**:
  1. **命令 token 级相同** (Condition 2 ✓)。
  2. **数据集字节相同** (Condition 3 ✓)。
  3. **canonical repair --execute changes=[]**: `_coordination/20260625_harbor_bench/artifacts/tb21_full89_runtime_closure_repair_20260705_155424.json` (07-05 15:54, = canonical 时刻): `changes:[]` (len 0), `run_tests_changed:0`, `test_outputs_changed:0`, `solution_files_changed:0`, `compose_files_changed:0` → prebuilt image 内 `/tests` == 数据集 run_tests, 0 改动。这是 Condition 1 中 `TB_SKIP_TEST_COPY` 用 baked `/tests` 的等价性证据。
- **"只有 r3 runner 晚于 canonical" 核实成立** (mtime UTC, 见本地 `runners/tb21_harness/PROVENANCE.tsv`):
  - `stage_tb21_official_qwen_launcher.sh` `2026-07-05 15:51:06Z` — **earlier** (canonical 15:55:10Z)
  - `run_terminal_bench_2_1_full89_batched_privileged_offline.sh` (r3) `2026-07-07 15:46:48Z` — **LATER (唯一)**
  - `run_terminal_bench_2_1.sh` (swe/bench/shared/runners) `2026-06-30` — earlier
  - `repair_tb21_full89_runtime_closure.py` `2026-07-02` — earlier
  - (PROVENANCE.tsv 另有 `…qwencode…`/`tb21_qwencode_agent.py` 标 LATER, 但属**非官方 qwen-code harness**, 本 terminus-2 run 未用。)
- r3 runner 的改动**不触碰任何 tb-run 测量 flag**: 仅管理 `TB_SKIP_TEST_COPY` (test 来源, 已中和)、closure gate (更严)、oracle-score gate (`--allow-oracle-score` 仅在 `TB21_ALLOW_ORACLE_SCORE==1` 时加, 本 run =0 → **真 agent 打分, 非 oracle**)、`--no-rebuild`。`--agent/--model/--n-concurrent/temperature/timeouts/dataset-path` 均原样透传 (Condition 2 已证 token 相同)。
- **`TB2_RUNTIME_CLOSURE_REPAIR=""` (跳过 repair) 未降 gate**: 本 run 于 06:49:19Z 重跑**静态 closure gate** 并 PASS —
  `…/runtime_closure_…_static_gate_….json`: `runtime_closure_closed:89, open:0, ready:true, status:"closed"`。跳 repair 安全, 因无需修复 (gate 已 closed)。
- **`TB21_ENABLE_KVM_DEVICE=0` 未降 gate**: 缺 /dev/kvm 只会**拖慢/拖垮** qemu 类任务 (降分), **不可能抬高** pass 率。非通胀路径。
- (env 全部来自 live `/proc/1203963/environ` 与 launcher/runner grep, 见 §附录。)

## Condition 5 — serving 栈 —— **REFUTED** (预判成立)

- canonical serving 参数 (sglang 版本 / tp_size / attention_backend / mem_fraction_static / tool_call_parser): **NOT RECORDED IN RUN ARTIFACTS**。
- 穷尽搜索路径 (均无 server 侧参数):
  - canonical `run_metadata.json`: 仅 `model_name`, 无 serving keys。
  - `…_preflight.md` / `…_ledger.json` / `logs/tb21_qwen_c32_launch_20260705T155226Z.log`: grep `sglang|--tp|attention.backend|mem.frac|tool.call.parser|get_model_info|model_path|served-model-name` → **唯一命中 "tensor-parallelism" 实为 task-id `torch-tensor-parallelism`, 非 serving 参数**。
  - `find … stage1_20260705t1548* (serv|model_info|identity|health)` → **空**。
  - `grep -rl 100.103.228.120` → 仅**客户端** api_base 配置文件。
  - canonical (07-05) 早于本 run 的 serving 抓取机制 (`identity_capture.py` mtime 07-10 13:04), 故无 get_model_info 捕获。
- 对照: **本 run serving 反而有完整记录** (`full_run.out` `[after]` + `serving_run/get_{model,server}_info_after.json`): `version=0.5.13 tp=2 parser=qwen3_coder mem_frac=0.85 attn=fa3 context_length=262144 port=30001`, `model_path=…/Qwen3-Coder-30B-A3B-Instruct endswith_Coder=True` (读真实 model_path, 破 "model 名不被校验" 陷阱)。
- ⇒ 一端 (本 run) 已知、另一端 (canonical, 且 host `100.103.228.120` **今日 DEAD**) 不可知 → **"serving 栈相同" 原理上不可证**。端点亦不同 (`:30000` host .120 vs `:30001` host .140)。
- **注**: 该差异**可能就是** canonical 9/89 vs 本 run 12/89 及 JSON-parse 失败率差异 (canonical ~0 "No valid JSON" vs 本 run 598) 的成因 — 不同 sglang 版本 + 固定 seed 598954308 下的 greedy 解码差异。故此为**实质性 (material)** deviation, 非技术性瑕疵。

## Condition 6 — 分数与 llm_health —— **CONFIRMED** (分数 valid; llm_health = content_class)

- **分数 12/89 = 0.1348314606741573 (分母=89, 已 SEAL)**:
  - 独立逐 trial 重数 `run_root/results.json`: 89 trials, 89 distinct task_id, `is_resolved` true = **12**。
  - 与 `run_metadata.accuracy` (`0.1348314606741573`) 及 native `results.json` (`n_resolved:12, n_unresolved:77`, `resolved+unresolved=89`) **三方对账一致**; `resolved_ids` 集合与我重数集合**逐项相等**。
  - 12 个 resolved: build-pmars, cancel-async-tasks, cobol-modernization, configure-git-webserver, constraints-scheduling, fix-code-vulnerability, git-leak-recovery, nginx-request-logging, portfolio-optimization, prove-plus-comm, pypi-server, qemu-startup。
  - **避开陷阱**: 早期活着的 `results.json` 曾为 12/85 (分母 85); 收尾后全 89 scored → 12/89。分母**用 89**。
- **llm_health = CONTENT_CLASS** (独立复核第二工程师定性, 结论一致):
  - 扫全部 **8559** 个 debug.json (本 harness 变体按 episode 保留, 非覆写) 的 `Error code: (\d{3})`: 仅 **7× HTTP 400**, 全部 `context_length_exceeded` (输入 262175/262267… > 262144); **0× 5xx, 0× 429**。
  - `terminal_bench.log`: `No valid JSON object found` **598**, `Extra text detected after JSON object` **5713**, 5xx/429/ConnectionError/ReadTimeout/retries-exhausted = **0**, 仅 **1× Timeout** (`RetryError[…raised Timeout]`)。
  - 输出形态: 8551 成功响应 `finish_reason` 全 `stop` (零 length 截断), content 全以 `{` 开头, `tool_calls` 一次未出现。对账 8551(stop)+7(400)+1(None/Timeout)=8559 ✓。
  - `completion_evidence/18_transport_grep.txt` = **2 bytes (空)** = 零 transport 错误。
  - ⇒ 主导失败模式是模型输出质量 (JSON 后附散文 / 偶发 context 溢出), **非** infra。全 run infra 命中 (5xx+429+conn+read-timeout+retry-exhausted) = **1/8559 ≈ 0.01%**。按 v4: content_class → **不判 forbidden**。
- **★ 实质性 CAVEAT (须上报)**: 本 run 退出码 `full.rc=143` (=128+SIGTERM)。`full_run.out` 顺序为 `Running tasks (89/89, 13.48%)` → `Results Summary 12/77/13.48%` → `Results written to results.json` → **`Terminated` → `tb_rc=143`** → `IDENTITY_OK`。即 **SIGTERM 发生在打分写盘之后的 teardown 阶段** (end_time 08:58:08Z 之后)。
  - wrapper strict summary 显示 `status:"blocked", ready:false, infra_fail:89`。但本 run 自己的 `reduce_scores.py` **明文标注**这是 rc 污染, 非 infra:
    - L84-89: `"downstream_artifacts_of_this_rc__NOT_infra_failures"`; `"infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not in (0,None))… A non-zero tb_rc therefore marks ALL 89 rows infra_fail… regardless of the run."`
    - L97-99 (v5): 非零 rc 若在 end_time 之后, 非失败, `"must not trigger blocked"`。
    - L162-164: 权威分数取自 89 个 per-trial `results.json`, `"never from the tb_rc-contaminated strict summary"`。
  - ⇒ 分数 **valid 且完整** (写盘先于 SIGTERM, 三方对账一致); `infra_fail:89/blocked` 是 tb_rc=143 的下游产物, 非逐-task 测量失败 (raw payload 逐-task infra=0 已独立证实)。**但**: 严格 clean 的官方复现应 exit 0; 此 rc=143 是 run hygiene 瑕疵, 提请第二签核人 / 用户注意。

---

## 附录 — 关键 ground-truth (only-read, 无改动/无 kill/无 docker 操作)

- live harness env (`/proc/1203963/environ`, 仅 TB-* 变量, 从不打印 key):
  `TB_AGENT=terminus-2` · `REASONING_EFFORT=`(空) · `TB2_RUNTIME_CLOSURE_REPAIR=`(空) · `TB21_ENABLE_KVM_DEVICE=0` · `TB21_ALLOW_ORACLE_SCORE=0` · `TB21_STRICT_CLOSURE_GATE=1` · `TB21_STATIC_RUNTIME_CLOSURE_GATE=1` · `TB2_USE_PREBUILT_IMAGES=1` · `TB2_OFFLINE_TEST_BOOTSTRAP=1` · `TB_SKIP_TEST_COPY_TASK_IDS=`(全 89) · `TB_AGENT_KWARGS=api_base=http://100.100.104.140:30001/v1 temperature=0.0`。
- launcher 设 (canonical+本 run 共用, mtime 07-05 15:51 早于 canonical): `TB21_ALLOW_ORACLE_SCORE=0`, `TB21_STRICT_CLOSURE_GATE=1`, `TB2_OFFLINE_TEST_BOOTSTRAP=1`, `TB2_USE_PREBUILT_IMAGES=1`。
- 本 run image map `…/tb21_prebuilt_image_map_full89_r7_official_qwen.json` (dated 07-05 15:51, 89 项, tag `tb2-offline/*:20260425-closure-r2`) — canonical 时刻生成、本 run 复用。
- 全局约束遵守: 仅 SSH 只读; 未 commit/push; 未 kill 进程; 未 docker rm/rmi; 未改 run_root; ps 用字符类防自匹配; API key 从未落屏/落盘 (环境中 8 个 KEY/TOKEN 变量仅计数未打印)。
