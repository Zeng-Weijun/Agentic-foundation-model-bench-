# QwenCode SWE-V — Qwen 原生 scaffold 终分报告

> **Status: HISTORICAL_NON_CANONICAL_CONFIG (2026-07-21).** Restored as reviewed historical evidence. The original PASS/final/representative-score language below is not current-suite authority; this Qwen/old-harness result must not be quoted as a current score.

> 日期:2026-07-06 | 复审:85 | 状态:**PASS,Qwen 代表分定稿**
> 权威源:`runs/swev_qwencode_v21_20260705T190754Z/full500_c20/results.jsonl`(500 行,wc 亲验)

## 1. 终分

| 项 | 值 |
|---|---|
| **Score** | **48.6%(243 / 500)** |
| 模型 | Qwen3-Coder-30B-A3B-Instruct |
| scaffold | **QwenCode 0.15.6 原生**(`SWEV_QWEN_CODE_VERSION=0.15.6`,launch 脚本实证) |
| 数据集 | SWE-bench Verified 500(离线,`--network none`),同 gpt-5.5/Qwen-mini 同一 500 案 |
| infra | eval_rc=0 ×500(0 infra)· agent_status 497 patch / 3 no_patch |
| 复现 | vs README 49.0%(245)= -2 题;vs 官方自报 ~51% = -2.4pt;**均在单跑方差(±2-3pp)内** |

## 2. 补跑叙事 + 与 6 月 degraded run 归因

**6 月 frozen(23.4%,117/500)是降级 run,非 Qwen 原生能力。**

| 维度 | 6 月 frozen(paper_n500) | 本次 v2.1(48.6%) |
|---|---|---|
| QwenCode 版本 | ~4.3 | **0.15.6** |
| completed | 384/500(**116 未完成**) | eval_rc=0 ×500 |
| patch 产出 | empty_patch=109 | **497/500 patch** |
| 判定 | infra + 版本降级 | 干净 |

→ 差异 = 新 scaffold(4.3→0.15.6)+ infra 修复(116 未完成 → 0)。**6 月 23.4% = 当时 infra/版本降级的产物,与 Qwen 原生真实力无关。**

## 3. trace 抽验(原生多调用顺畅,0 摩擦)

- astropy-7671(resolved):真 patch 903c、**48 个原生 tool-call、0 拒绝**(如 `name:glob`)。
- astropy-7606 / 7166(unresolved):真 patch 463c/1570c、agent_status=patch、**0 拒绝** → **真模型错解**(出 patch 但错),非 scaffold 摩擦。
- **497/500 patch(vs mini 441/59 no_patch):QwenCode 原生接受 Qwen 多-tool-call,与 mini 100% "multiple bash" 拒绝相反。**

## 4. '49% 锚'降级表述

- 先前贯穿全程的 **"QwenCode 49%"** 是 **README 记载 / 官方自报 ~51% 邻域,盘上无产物**。
- 本次 **48.6%(243/500)是首个盘上已验证的 canonical Qwen 原生分**,**取代**未验证的 49% 锚。

## 5. 对外口径（Qwen 代表分)

> Qwen3-Coder-30B-A3B · QwenCode 0.15.6(原生)· SWE-bench Verified 500 · 单跑 · **48.6%(243/500)** · 0 infra。复现官方自报邻域(~49-51%)。

- **这是 Qwen 代表数。** caveat:单跑(±2-3pp)。
- ⛔ **23.4%(mini)/10.1%(terminus-2)是 scaffold 压低,禁当 Qwen 能力引。**
