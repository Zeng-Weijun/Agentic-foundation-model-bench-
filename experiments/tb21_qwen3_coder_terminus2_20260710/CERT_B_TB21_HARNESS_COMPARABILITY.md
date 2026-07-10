# CERT_B — TB2.1 三-harness 可比性独立签核（第二签核人)

**签核问题（与第一签核人不同):** 不是「某个 run 的分数有没有效」,而是
**「terminus-2 / qwen-code native / qwen-code host-bridge 三种 harness 在 TB2.1 上的分数,能不能放在一起当作『交互模式效应』的证据。」**
本人任务是**尽力证明它们不可比**。

**独立性声明:** 本人**未读** `CERT_A_TB21_TERMINUS2.md`,亦未读 `CERT_B_TB21_EVIDENCE.md`。
本报告全部结论从 run 原始产物(run_metadata / results.json / serving snapshot / trace / dataset 文件)独立推出。
**只读合规:** 未 commit/push、未 kill 进程、未重启服务、未改任何 run_root 下文件。唯一网络动作 = 对
`http://100.100.104.140:30001/get_server_info`+`/get_model_info` 的**只读 GET**(与各 run 自身取证同款)。key 未落屏/落盘。
**主机:** Pod A `env-kvm-15238487-rlgbn`(所有 run 产物均在共享盘,故一台即可读全)。

---

## 0. 六个 run 的定位(搜过的路径)

TB 官方 harness 产物根: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/`
编排壳根: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/`
(先搜 `swe/bench/terminalbench2.1`(旧 canonical 壳)与 `/data`、`/docker-data-15238487` 无今日 run → 定位到上面两根)

| ID | harness | 分数 | TB 产物根 basename |
|---|---|---|---|
| **A** | terminus-2 (官方) | **12/89** | `tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0710064916_attempt1_medium_c32` |
| **B** | terminus-2 (官方) canon 07-05 | **9/89** | `..._terminus-2_c32_tb21_qwen_official_medium_c32_stage1_20260705t15481783266492z_attempt1_medium_c32` |
| **C** | qwen-code 0.16.2 容器内原生 | **10/89** | `tb21_native_qwencode0162_promptfixed_bridgefix_full89_c32_20260710t1002z` |
| **D-today** | qwen-code host-bridge 07-10 | **13/89** | `..._qwen-code-host-bridge_c32_tb21qcb32_0710034854` |
| D-run2 | qwen-code host-bridge 07-09 | 12/89 | `..._qwen-code-host-bridge_c32_tb21qcb32_0709201834` |
| **D-canon** | qwen-code host-bridge 07-06 | **15/89** | `..._qwen-code-host-bridge_c32_qwencode_full89_c32_20260706t08041783325051z` |

分数全部与 brief 给定一致(12/9/10/13/15/12),`n_resolved`+`accuracy` 直接取自各自 `results.json`。

---

## 1. 是不是同一批 89 题?  ——  **题目集相同,但 dataset 内容有 4 个不同快照(差异仅在 harness plumbing)**

**task_ids 集合:** 6 个 run 的 `run_metadata.json.task_ids` **集合 SHA256 完全相同 = `5c7ed05c61e6768b…`**(89 题)。
顺序 SHA256 各不相同 → 并发调度洗牌,不影响判分。→ **同一批 89 题,✅。**

**dataset_path 快照名 不同:**
- A / B / D-canon → `terminal-bench-2.1-yaml-full89-r7-final-20260703`(canonical)
- C → `terminal-bench-2.1-yaml-full89-r7-**nativeqwen0162-sharedbridge-promptfixed**-20260710`
- D-today → `…/tb21_kvm_device_datasets/tb21qcb32_0710034854/dataset`(每-run 拷贝)
- D-run2 → `…/tb21_kvm_device_datasets/tb21qcb32_0709201834/dataset`

**Merkle(逐文件 sha256 → 排序 → 汇总 sha256,各 1002 文件):**
| 快照 | 用于 | merkle |
|---|---|---|
| canonical_r7final | A,B,D-canon | `ff52c626f9a327b3…` |
| C_promptfixed | C | `2c3280a7d829cb49…` |
| D_today_devcopy | D-today | `7438728453f4f7f4…` |
| D_run2_devcopy | D-run2 | `810f9f4164664a58…` |

**4 个不同 merkle。** 但逐文件 diff(canonical↔C、canonical↔D-today):**唯一变化的文件 = 每 run 89 个 `docker-compose.yaml`,别无其他。**
`task.yaml`/instruction、`tests/`、`solution.sh` **逐字节相同**(判分逻辑一致)。docker-compose 的实际改动:
- **canonical→C:** `network_mode: none → bridge`(容器获网以便**容器内** qwen 打 sglang)+ 只读挂载 `qwen_native_swebench/.npm-root-0.16.2:/opt/qwen-native/.npm-root`。
- **canonical→D-today:** payload 挂载源路径改为每-run 拷贝 + `devices: /dev/kvm`;`network_mode` 仍 `none`。

⇒ **结论:同 89 题、判分文件逐字节相同;dataset 差异纯属 harness 环境 plumbing(网络策略/挂载/设备),不动题面与测试。**
**但该 plumbing 差异本身就是三种交互模式不可分割的一部分(C 有网、挂了工具;A/B/D 无网)。**

---

## 2. Agent affordance 可比吗?  ——  **不可比:三种交互模式,trace 实证**

| harness | 大脑在哪 | 容器网络 | 工具面 | trace 实证 |
|---|---|---|---|---|
| **A/B terminus-2** | **宿主机** | `network_mode: none` | **一个活的终端**:模型每 episode 产出 → 敲进 tmux,读回屏幕 | `…/portfolio-optimization/…/agent-logs/episode-{6,9,11,…,25}/{prompt,response,debug}.txt/json`,逐 episode 一次 LLM 调用 |
| **C 原生** | **容器内**(`qwen --channel CI --yolo --output-format stream-json --prompt=…`) | `network_mode: bridge` | **全套原生工具** | `agent.log` 实测调用:`read_file`(5)`run_shell_command`(4+1)`edit`(3)`write_file`(2+1)`Replace`(2)`todo_write list_directory grep glob shell` —— 单题 **18 tool_use / 18 tool_result** |
| **D host-bridge** | **宿主机** | `network_mode: none` | **单一工具 `run_tb_command`** | `qwen_command.json`: `--allowed-tools run_tb_command` + `--exclude-tools` 显式禁掉 Shell/Bash/read_file/write_file/edit/glob/grep/list_directory/todo_write/skill/agent… **全部**原生工具 |

**特别核 D(按 brief 要求):**
- 真的只有一个工具? **是。** 源码 `scripts/qwen_tb21_bridge.py`:`if tool_name != "run_tb_command": reject`;`run_tb_command` = `docker exec -w /app -u <user> <container> <cmd>`。
- 真的读不到宿主机 `solution.sh`/`tests/`? **确认读不到。** D 的 `tool_calls.jsonl` 第一条:模型 `find /mnt/shared-storage-user/…/runs/…/portfolio-optimization -type f`(一个**宿主机**路径)→ **`exit_code=1, stderr="find: '/mnt/shared-storag…'"`** —— 因为 run_tb_command 是 `docker exec` **进容器**,宿主机 oracle 路径在容器里不存在。**单工具 + 只达容器,宿主机题解不可达。**

⇒ **三种 affordance 在 trace 层实证成立,互不等价。A=键盘/终端;C=容器内全工具;D=容器外单 shell-into-container。**

---

## 3. Serving 栈可比吗?  ——  **只有 A↔C 可确证同 serving;B 与 D-canon 的 serving = NOT RECORDED**

| run | endpoint | random_seed | sglang | 取证 |
|---|---|---|---|---|
| A | `100.100.104.140:30001` | **598954308**(见下 bracket) | 0.5.13 | A 自身**未存** serving snapshot;endpoint/temp 见 command.sh |
| C | `100.100.104.140:30001` | **598954308**(before+after 一致) | 0.5.13 | `control/serving_config_{before,after}.json` 完整,`model_path=…/Qwen3-Coder-30B-A3B-Instruct` |
| D-today | `100.100.104.140:30001` | (同期) | — | qwen_command 记 endpoint;无 seed snapshot |
| D-run2 | `100.100.104.140:30001` | — | — | 同上 |
| **B** | `100.103.228.120:30000` **DEAD** | **NOT RECORDED** | **NOT RECORDED** | 全树 grep `get_server_info` = 0;仅 command.sh/run.env/debug 有 base_url 串;主机已死不可回探 |
| **D-canon** | `100.103.228.120:30000` **DEAD** | **NOT RECORDED** | **NOT RECORDED** | 同 B,无 serving snapshot |

**A 与 C 同 seed 证明(A 自身没存,用时间 bracket A 的 06:52–16:58 窗口):**
seed=`598954308` 出现于 —— 06:54:55 / 07:03(before+after) / 09:21(before+after) 的晨间 native run snapshot、C 的 17:22(before)+17:41(after)、**以及本人此刻 live GET**。
全天恒定 598954308,**无重启迹象** ⇒ :30001 是**同一个从未重启的 sglang 进程**,横跨 A 与 C 全窗口。
⇒ **A、C、D-today、D-run2 打的是同一个 serving 进程。**

**B / D-canon:** endpoint = 已死的 `100.103.228.120:30000`,serving 参数、seed、sglang 版本、**权重身份**全部**从未记录**。
注意 sglang **不校验 model 字段**(resources.yaml 已载),故 B/D-canon 的「Qwen3-Coder-30B」身份**无法从任何字段证实**,且主机已死**不可复现**。

⇒ **可说「同 serving」的对:A–C(证实)、A–D-today、C–D-today、D-today–D-run2(同 endpoint 同期)。**
⇒ **不能说同 serving 的对:任何含 B 或 D-canon 的对**(即 `A vs B`、`D-canon vs D-today`)—— serving 未记录且不可回探。

---

## 4. 采样与确定性  ——  **A/B(temp=0)与 C/D(qwen-code 默认,未捕获)口径不同**

- **A/B terminus-2:** litellm,`command.sh` 显式 `--agent-kwarg temperature=0.0`;A 的 `agent-logs/episode-*/debug.json` `optional_params` 实测 `"temperature": 0.0`。`top_p`/`top_k` **未发**(服务端默认)。
- **C/D qwen-code:** `command.sh` / `qwen_command.json` **不带任何采样参数**(`qwen --channel CI --yolo --auth-type openai --output-format stream-json --prompt=…`)。
  逐 trace grep `temperature|top_p|top_k|generationConfig` = **0 命中** ⇒ **on-wire 采样 = NOT CAPTURED**(qwen-code 客户端默认,无法从产物证实)。服务端 `preferred_sampling_params: null`、`enable_deterministic_inference: false`。
- ⇒ **A 与 C 采样口径不同(temp=0 explicit vs 未捕获默认),这是必须声明的偏差。** 且 `c=32` 批处理 + 非确定性推理 ⇒ 单 run 不可逐位复现(brief 已量 bridge 同配置 Jaccard≈0.39)。

---

## 5. 差异显著吗?  ——  **四对 McNemar 精确二项检验,全部不显著**

从各 `results.json.resolved_ids` 集合直接算(89 题公共集,精确双侧二项 p):

### A(terminus2 today) vs B(terminus2 canon0705)  —— 独立复算,**复现 brief 给定**
`a=8  b=4  c=1  d=76  discordant=5`  → **p = 0.3750**
- 只 A 解出(4): `cobol-modernization, fix-code-vulnerability, nginx-request-logging, qemu-startup`
- 只 B 解出(1): `openssl-selfsigned-cert`
- (brief 给 a=8,d=76,discordant 1/4,p=0.375 —— 完全一致,仅 b/c 命名镜像。)

### A(terminus2) vs C(native qwencode)  —— ★「交互模式」头号对
`a=5  b=7  c=5  d=72  discordant=12`  → **p = 0.7744**
- 只 A 解出(7): `cobol-modernization, configure-git-webserver, constraints-scheduling, fix-code-vulnerability, nginx-request-logging, pypi-server, qemu-startup`
- 只 C 解出(5): `build-cython-ext, fix-git, modernize-scientific-stack, multi-source-data-merger, pytorch-model-cli`

### C(native) vs D-today(bridge)  —— ★最干净的 affordance 对比(同 qwen-code / 同 serving / 同采样族)
`a=8  b=2  c=5  d=74  discordant=7`  → **p = 0.4531**
- 只 C 解出(2): `prove-plus-comm, pytorch-model-cli`
- 只 D-today 解出(5): `build-pov-ray, cobol-modernization, constraints-scheduling, polyglot-rust-c, pypi-server`

### D-canon(0706) vs D-today(0710)  —— 同 harness run-to-run
`a=9  b=6  c=4  d=70  discordant=10`  → **p = 0.7539**
- 只 D-canon 解出(6): `adaptive-rejection-sampler, configure-git-webserver, hf-model-inference, kv-store-grpc, nginx-request-logging, pytorch-model-cli`
- 只 D-today 解出(4): `build-cython-ext, build-pov-ray, cobol-modernization, git-leak-recovery`

**四对 p ∈ {0.375, 0.774, 0.453, 0.754},无一显著(全 > 0.35)。**
注:**未**跨 harness 搬用那位工程师量的 `σ_diff≈3.32`(其本人明令禁止);此处一律用集合直算 McNemar。

---

## 6. 可比性总表 + 能不能进论文

| 对 | dataset 判分文件 | serving | 采样口径 | affordance | McNemar p | 可比性判定 |
|---|---|---|---|---|---|---|
| **A vs B** | 同(canonical,merkle 同) | **B 未记录/已死** ✗ | 同 temp=0 ✓ | 同 terminus-2 ✓ | 0.375 | **同 harness 内**最干净,但 serving 混淆且 B 权重身份不可证 → 只能说「同一 harness 两次 run 也分不出」 |
| **A vs C** | 题面同,容器环境不同(none↔bridge+挂工具) ~ | **同 serving(证实)** ✓ | **不同**(temp=0 vs 未捕获) ✗ | **不同**(终端 vs 原生工具) ✓ | 0.774 | **不可比为纯交互模式**:采样+容器环境同时变;差异落在噪声里 |
| **C vs D-today** | 题面同,plumbing 不同 ~ | 同 serving ✓ | 同族(qwen-code,均未捕获) ~ | **不同**(全工具 vs 单 run_tb_command) ✓ | 0.453 | 最接近「纯 affordance」对比,但**仍分不出** |
| **D-canon vs D-today** | 不同(canonical vs devcopy) ✗ | **D-canon 未记录/已死** ✗ | 同族 | 同 bridge ✓ | 0.754 | 同 harness run-to-run(15/13/12),**证明标题级 2-3 题波动就是噪声** |

### 「TB2.1 上交互模式效应塌了」—— 证据支持吗?

**不支持(作为正向发现)。** 四对 McNemar 全部不显著,这张表**唯一能诚实说的是「在 n=89、每格单跑的条件下,我们分不出这三种 harness」**。
这是一个**功效不足的 null,不是等价性证明**:每格 9–15/89(base rate ~11–17%),discordant 仅 5–12,检验功效极低;
且已知同配置 run-to-run 就洗牌(Jaccard≈0.39、bridge 15→13→12)。**"分不出" ≠ "没差异"。**

**而且这张表本就不是干净的交互模式对照**,四类未控混淆:
1. **serving 未记录:** B、D-canon 打已死的 :30000,seed/版本/**权重身份**全无记录、不可回探(sglang 不校验 model 名)。
2. **采样口径不同:** terminus-2 temp=0 显式 vs qwen-code on-wire 未捕获。
3. **容器环境随 harness 变:** network none↔bridge、是否挂 qwen 工具、/dev/kvm —— 烤进各自 dataset 的 docker-compose,与「交互模式」纠缠不可分。
4. **单格单跑 + 非确定推理:** c=32、`enable_deterministic_inference=false`,无格内方差估计。

**要证明「塌了」还需要:** (a) 每格 **≥3–5 次重复**以估格内方差;(b) 跨 harness **统一 dataset/采样/serving**(把 1–4 全控住,尤其重建 B/D-canon 于**活的、已记录**的 serving 上);(c) 提高统计功效——**更大 n 或换 base-rate 更高的 bench**(对照 SWE-V 原生 48.6% vs bash-only 23.4% 差 25 点,是因为那里 base rate 高、差距大才可检出;TB2.1 的 ~13% 低 base rate 把任何中等效应都淹了)。

---

## 结论(一句话)

> **这张三-harness 对照表 = 不能作为「交互模式效应」的证据发表(能/不能/证据不足 → 判「不能 + INSUFFICIENT_EVIDENCE」)。**
> 四对 McNemar p 全不显著(0.375 / 0.774 / 0.453 / 0.754),叠加 serving(B、D-canon)未记录、采样口径不一、容器环境随 harness 变、单格单跑四重未控混淆。
> 这张表**唯一诚实的读法是「我们分不出来」**,而非「交互模式在 TB2.1 上没有效应」。
