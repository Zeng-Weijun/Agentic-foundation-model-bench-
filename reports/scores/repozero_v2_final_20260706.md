# RepoZero gpt-5.5 — 终分报告（v2,证据一致收口）

> 日期:2026-07-06 | 复审:85 | 产出:v2 reducer(evidence-consistent)| 状态:**PASS,正式收口**
> 权威源:`gpt-5.5_repozero_optionb_rejudge_full188_v2_20260705T185709Z/scores.json`(schema `repozero.rejudge_scores.v2`)

## 1. 终分

| 项 | 值 |
|---|---|
| **Score** | **67.55%(127 / 188)** strict all-tests-pass |
| 模型 / 生成 | `gpt-5.5`,codex Py2JS(单次) |
| 案集 | RepoZero **option-b 188 子集**(离线 docker,`--network none`) |
| 证据一致 | `evidence_consistent=true`;127 passes 全 `storage_error=false`;`pass_but_incomplete=0` |
| 基础设施 | `storage_error_cases=[]`、`timeout_cases=[]`(0 磁盘失败、0 超时) |
| 独立复算 | 127(从 results.jsonl 独立重算,与分数一致) |

## 2. 翻案链叙事（为什么前面的数字不能用）

**28.2% → 67.0% → 67.55%** —— 三跑,只有最后一个可信:

1. **28.2%(127/188 原始跑)= 无效。** eval 跑到一半**磁盘满**:128/188(68%)命中 `oracle_rc=126` + "no space left on device",oracle 参考自身也挂 → 不可评分。后半程整族(jsonschema/markdown/whoosh/yaml…)全 0 是磁盘耗尽时间线,非模型。
2. **67.0%(126/188 rejudge v1)= 不可验证。** 修盘后重判,但**磁盘在长 rejudge 期间(~17:27)又满**,覆盖了自己的 case_result 证据;抽样 **48/53 pass-claim 与盘上证据矛盾**。真分大概率 60% 段,但当时不可复现。
3. **67.55%(127/188 v2)= 证据一致,可复现。** v2 补齐:证据一致性断言 + 冻结快照(source vs rejudge 分离,reducer 不再把历史 rc126 当当前失败)+ 全程磁盘水位监控 + 3600s watchdog(零触发)。独立核实:127 passes 全 storage_error=false、0 incomplete、0 storage/timeout case。**这是唯一可引用的 RepoZero 数字。**

## 3. 三条强制 caveat（引用时必须同时声明）

1. **rescue 有偏子集:** 188 是上轮 infra-fail 的救援子集,**非 400 案官方 RepoZero**。
2. **无 LLM judge:** strict 全测通过判定,非官方 LLM-judge 口径。
3. **单次:** single-run,非多种子均值(方差未量化)。

→ **67.55% 是内部 188-子集测量(磁盘校正 + 证据验证),非官方榜数。** 与任何官方/Claude RepoZero 数(如 ~55%)**不可比**(案集不同);**禁做 gpt-5.5 vs Claude 结论**。

## 4. ⛔ 禁引用数字清单（口径孤儿 / 已 REJECT)

| 数字 | 出处 | 为什么禁 |
|---|---|---|
| **28.2%** | RepoZero 原始跑 | 磁盘满,68% 不可评分 |
| **67.0%** | RepoZero rejudge v1 | 证据被二次磁盘满覆盖,不可验证 |
| **23.4%** | Qwen3-Coder-30B SWE-V(mini) | scaffold 协议摩擦压低(100% 多-bash 拒绝),非模型分 |
| **10.1%** | Qwen3-Coder-30B TB2.1(terminus-2) | 终端交互 churning 压低(avg 105.8 轮),非模型分 |

仅 **67.55%(RepoZero,带上述 caveat)** 可引用。
