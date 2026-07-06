# Qwen3-Coder-30B-A3B-Instruct — Canonical Bench Scores（定稿）

> 定稿日期:2026-07-06 | 用户拍板 | 复审:surface:85(dual-sign)
> 模型:`Qwen/Qwen3-Coder-30B-A3B-Instruct` | serving:vLLM(同 campaign)

## Canonical 分（引用时 caveat 必须随行）

| Bench | 分 | scaffold / 口径 | run |
|---|---|---|---|
| **SWE-bench Verified** | **48.6%**（243/500) | QwenCode 0.15.6 原生 · 单次 pass@1 | `swev_qwencode_v21_20260705T190754Z` |
| **Terminal-Bench 2.1** | **10.1%**（9/89) | terminus-2 官方 harness · 单次 | `tb21_qwen_official_medium_c32_stage1` |

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

---

## 附录:五点交互模式梯度（同 SWE-V-500 / TB2.1-89)

| 模型 | scaffold | 交互模式 | 分 | 状态 |
|---|---|---|---|---|
| Qwen3-Coder-30B | QwenCode 0.15.6 | 原生多-tool-call | **48.6%** | ✅ canonical Qwen 原生 |
| Qwen3-Coder-30B | mini-swe-agent | 单-bash-块 | 23.4% | ✗ 兼容压低(100% 多-bash 拒绝) |
| Qwen3-Coder-30B | terminus-2 | live tmux | **10.1%** | ✅ canonical(TB2.1 官方 harness)· ✗ 交互压低 caveat 随行 |
| gpt-5.5 | mini-swe-agent | 单-bash-块 | 77.2% | 参照(模型-scaffold 契合) |
| gpt-5.5 | terminus-2 | live tmux | 70.8% | 参照 |

**一句话:** Qwen3-Coder-30B 代表力 = SWE-V 原生 **48.6%**;TB2.1 官方 harness **10.1%**(交互压低,caveat 强制随行);`23.4%` scaffold-兼容压低分禁引。
