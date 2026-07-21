# Qwen3-Coder-30B-A3B-Instruct — Canonical Bench Scores（定稿）

> 定稿日期:2026-07-06 | 用户拍板 | 复审:surface:85(dual-sign)
> 模型:`Qwen/Qwen3-Coder-30B-A3B-Instruct` | serving:vLLM(同 campaign)

## Canonical 分（引用时 caveat 必须随行）

| Bench | 分 | scaffold / 口径 | run |
|---|---|---|---|
| **SWE-bench Verified** | **48.6%**（243/500) | QwenCode 0.15.6 原生 · 单次 pass@1 | `swev_qwencode_v21_20260705T190754Z` |
| **Terminal-Bench 2.1** | **10.1%**（9/89) | terminus-2 官方 harness · 单次 | `tb21_qwen_official_medium_c32_stage1` |

> TB2.1 native-adapter 对照(非官方 harness,详见 §2):QwenCode 0.15.6 host-bridge = **16.85%**（15/89,run `qwen-code-host-bridge_c32_full89`)。canonical 仍 = 10.1%(terminus-2 官方)。

---

## 1. SWE-bench Verified = 48.6%（243/500）

- **scaffold:** QwenCode 0.15.6(Qwen 原生 agentic scaffold,`SWEV_QWEN_CODE_VERSION=0.15.6` launch-脚本实证)。
- **口径:** 单次 pass@1,SWE-V 500 全量,离线 `--network none`,eval_rc=0 ×500(0 infra),agent_status 497 patch / 3 no_patch。
- **复现:** vs 官方自报 ~51% 差 **-2.4pt**;vs README 49.0%(245)差 -2 题 → **在单跑方差(±2-3pp)内,复现成功**。
- **★ 附注(强制):** `mini-swe-agent` 口径下同模型仅 **23.4%**,是 **scaffold 兼容压低分**(Qwen 原生多-tool-call 撞 mini 单-bash-块 parser,100% "multiple bash" 拒绝)—— **禁作 Qwen 能力分引用**。QwenCode 原生下多调用顺畅(抽样 48 tool-call / 0 拒绝),48.6% 才是 Qwen 代表力。

## 2. Terminal-Bench 2.1 = 10.1%（9/89）

- **scaffold:** terminus-2(TB2.1 官方 harness,live tmux 终端交互)。
- **口径:** 单次,medium 档,Pod A privileged,89 任务;9 resolved 真实(parser_results "passed" 抽验)。
- **★ 附注(强制,caveat 必须随数字):**
  1. **交互压低分:** 10.1% 被 terminus-2 的 live-终端导航需求扼住,**非原始能力地板**。死法主导 = **churning**(unresolved 平均 **105.8 轮**、70/80 ≥15 轮、0 个 ≤5 轮;avg 389K input token);Qwen 格式用对(单命令/轮),但终端屏幕理解/收敛差。
  2. **无官方 Qwen 锚:** TB2.1 无 Qwen3-Coder-30B 官方分,10.1% 是我方 terminus-2 单跑,非对榜数。
  3. 与 SWE-V-native 48.6% 对读才有意义:反映**交互模式复杂度**(原生→live-终端)对 Qwen 的单调扼制。

- **★ native-adapter 对照 = 16.85%（15/89,run `qwen-code-host-bridge_c32_full89`,非官方 harness):** QwenCode 0.15.6 host-bridge(host 跑 QwenCode + docker-exec into 离线容器)。**canonical 仍 = 10.1%(terminus-2 官方)**;16.85% 是原生-adapter 对照点,**非官方 terminus-2 分,勿作官方 TB2.1 引用**。
  - 差集归因(vs terminus-2 9 pass):common=6;**QwenCode-only +9**(build/service/data/ML 命令友好型:kv-store-grpc/nginx/hf-inference/pytorch-cli/data-merger/fix-git/polyglot-rust-c…);terminus-only **-3**(git-leak-recovery/openssl-selfsigned-cert/prove-plus-comm);**~9 交互-TTY 边界**(qemu/install-windows/chess/doom…)QwenCode 命令式 docker-exec 做不了。
  - +6.7pt 归因:原生命令式 scaffold 高效(无 terminus-2 的 105.8 轮 churning)胜在命令友好型,减掉交互-TTY 边界任务。

---

## 附录:六点交互模式梯度终表（同 SWE-V-500 / TB2.1-89)

| 模型 | scaffold | SWE-bench Verified | Terminal-Bench 2.1 |
|---|---|---|---|
| Qwen3-Coder-30B | 原生(QwenCode 0.15.6 / host-bridge) | **48.6%** | **16.85%**（native-adapter 对照,非官方 harness) |
| Qwen3-Coder-30B | 官方非原生(mini / terminus-2) | 23.4% ✗ | 10.1% ✗（canonical) |
| gpt-5.5 | 官方(mini / terminus-2) | 77.2% | 70.8% |

**pattern:** 两 bench 上 Qwen 原生 scaffold 都胜非原生官方 harness(SWE-V 48.6>23.4 = **+25.2pt**;TB2.1 16.85>10.1 = **+6.7pt**);gpt-5.5 在官方 harness 两边都稳(77.2/70.8)。→ **scaffold-fit 对 Qwen 是一阶因子,对 gpt-5.5 是二阶。**

**一句话:** Qwen3-Coder-30B 代表力 = SWE-V 原生 **48.6%**;TB2.1 canonical(官方 terminus-2)**10.1%**(交互压低 caveat 强制随行),native-adapter 对照 **16.85%**;`23.4%` scaffold-兼容压低分禁引。
