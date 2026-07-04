# full500 中期独立审计（只读）— surface:86

- **日期**: 2026-07-04
- **审计位**: surface:86（独立验证官，read-only）
- **对象**: Pod B `swev_full500_model_20260702` 账本可信度（中期，s046 在跑）
- **BASE**: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702`
- **方法**: 全程在 `dev` 通过共享 FS 只读遍历（零扰动 Pod B 运行中的 s046；未碰任何容器；未向 BASE 写入）。真值源 = 每实例 harness `report.json`（非账本汇总）。
- **模型**: gpt-5.4-mini · terminus/mini-swe-agent · SWE-V(erified) 任务集

---

## 一、总体判决

**账本"数值"可信，"可复现性"脆弱。** 三点定性：

1. **数值零错**：196 个有 clean `report.json` 的实例，账本 resolved 判定与 harness 真值 **100% 一致（0 mismatch）**；无任何造假信号（无 resolved-但-空 test_output、无 resolved-但-patch 未应用、无 resolved-但-FAIL_TO_PASS 有失败）。
2. **计数正确但证据脆弱**：账本 resolved=154 是**对的**（151 来自 clean shard + 3 来自被改名为 `.dockerinstability` 的**废弃后缀目录**里的真实 eval）。即：对 clean 目录重算只得 151，差的 3 个证据躺在"看着像垃圾"的目录里，一旦被当垃圾清掉，账本就无法从 clean 目录复现。
3. **70% 不是模型分**：已完成集 = astropy 22 + django 197（**纯 django 偏易**），无 sympy/matplotlib/sphinx 等硬库。HANDOFF 说的"70.4% 偏高"根因是**代表性/repo 组分**，不是计数 bug 也不是造假 → 现在对榜 = 口径孤儿（与 9/89 同类风险）。

---

## 二、重算对账表（authoritative = 每实例 report.json）

| 指标 | 账本值 | 独立重算值 | 差异 & 说明 |
|---|---|---|---|
| results.jsonl 总行数 | **220** | — | 比 unique 多 1（astropy-14995 双写，见 ISSUE-2）|
| 唯一 instance_id | 219 | 219 | 一致 |
| resolved（唯一） | **154** | **154** | 一致 = 151 clean report + 3 后缀目录真值（ISSUE-1）|
| — 其中 clean shard 有 report.json | — | **196** | 151 resolved / 45 unresolved |
| — clean-report 账本 vs 真值 mismatch | — | **0** | ★零错★ |
| — 仅在后缀目录有真值（resolved:true）| 3 | 3 | django-11099/11119/11133（ISSUE-1）|
| — 任何目录都无 report.json（真未评）| — | **20** | 19 空/无 patch(正确 false) + 1 incomplete |
| resolved rate（唯一，含后缀3） | 154/219 = **70.3%** | 154/219 | 仅 astropy+django，**不可对榜**（ISSUE-4）|
| resolved rate（仅 clean 可复现）| — | 151/219 = **68.9%** | clean-only 保守口径 |
| chunk 账本 done_chunks.txt | 46 | 46 = 6 astropy + 40 django | 与 219 实例自洽 |

- **抽样验真（check#4）**：resolved 抽 5（astropy-12907 / django-11451 / 13089 / 13933 / 15104）全部真跑 pytest（如 `15 passed in 0.56s`、test_output 17–55KB、patch 已应用、FAIL_TO_PASS 全 success）。unresolved 抽 3（astropy-13033 / django-11790 / 14140）全部 **agent-fail 形态**（patch 已应用、容器正常起停、具名 FAIL_TO_PASS 测试仍失败）——**无 harness-fail**，harness 健康。

---

## 三、发现（ISSUE-READY）

### ISSUE-1 — 3 个 resolved 只由"失败后缀目录"背书（MEDIUM · 可复现性/脆弱）
- **位置**: `full500_results.jsonl` 中 `django__django-11099 / -11119 / -11133`（resolved:true）；证据目录 = `full500_s002.dockerinstability_20260703T092608Z/`（及 `.flap_* / .evalrc1_*` 多份）。**clean `full500_s002` 目录内无这 3 个的 report.json**。
- **证据**: 全目录 hunt 显示这 3 个 report.json 仅存在于 `s002.{evalrc1,flap,dockerinstability}` 后缀变体；均 resolved=true、patch_successfully_applied=true、test_output 14–20KB、FAIL_TO_PASS 全 success、`>>>>> End Test Output` + git-checkout 真 pytest 痕迹 → **eval 是真的**。
- **影响**: 账本 154 正确**仅仅因为**这 3 个来自被运维改名为不稳定/废弃的目录。① 对 clean 目录做独立重算只得 **151**（我第一遍即漏掉这 3），账本**无法从 clean 目录复现**；② 若日后清理 `.dockerinstability/.flap`（名字像垃圾）→ **静默丢 3 个真 resolved** + 证据永久消失。
- **修法**: 在 canonical `full500_s002` 内**重跑**这 3 个（或把其 eval 目录 copy 进 clean `s002/logs/run_evaluation/`），使账本可从 clean shard 复现；或落一份 **provenance manifest**（每账本行 → 源 eval 目录）。**在对账完成前禁止删除任何后缀目录**。

### ISSUE-2 — astropy-14995 被评两次并双写账本（MEDIUM · 去重/分配)
- **位置**: `full500_results.jsonl` 第 15、16 行（均 resolved:true）；`full500_predictions.jsonl` 同；report.json 同时存在于 `full500_s000` 与 `full500_s001`；**两份 patch 不同**（s000=1522B，s001=1149B）。
- **证据**: 220 行 vs 219 unique；跨 shard report.json 命中 `{astropy-14995: [s000, s001]}`。
- **影响**: 该实例被分配到两个 shard（chunk 重叠或重派），模型跑了两次产出不同 patch。当前 resolved **集合不受影响**（两次都 true，去重后计 1）；但 ① 任何以 `resolved_rows / 220 原始行` 计算的比率会**双计**；② 暴露 chunk→instance **分配重叠**，若下次落到"一次 true 一次 false"就会**真正污染计数**。
- **修法**: 账本按 instance_id 去重（保留 canonical shard）；审 s000/s001 的 chunk→instance 分配重叠；账本 append 加 **unique-id 幂等守卫**。

### ISSUE-3 — 废弃目录 resolved 值处理不一致（LOW · 规则)
- **位置**: `django__django-11749`（账本 resolved:**false**）在 `full500_s003.dockerinstability_*` 里 report.json resolved:**true**；`django-11138`（账本 false）后缀目录亦 true。对比 ISSUE-1：11099/11119/11133 的"后缀-true"被**保留为 true**。
- **证据**: 全目录 hunt 表。
- **影响**: 账本对"废弃目录里的 resolved:true"时而保留（11099/11119/11133）时而丢弃（11749/11138），**规则不明**。当前 154 站得住，但换个口径可合法争成 155（补回 11749）或 151（剔除那 3 个）——**当前数字只是 append 顺序的偶然产物**。
- **修法**: 定一条确定性规则（"clean shard eval 为准" 或 "任何真 resolved eval 都算"），据此从 eval 目录重导账本。**推荐**：只认 clean（无后缀）shard 的 report.json 为 canonical，并强制在 clean shard 重评受影响的这 5 个实例（11099/11119/11133/11749/11138）。

### ISSUE-4 — 70.3% 是 django 偏斜的中期数，非模型 SWE-V 分（INFO · 高可见度)
- **位置**: 任何把"resolved 154/219 = 70%"当作 gpt-5.4-mini 的 SWE-V 成绩引用之处。
- **证据**: 已完成集 = astropy 22 + django 197；done_chunks = 6 astropy + 40 django chunk；**尚无 sympy/matplotlib/sphinx/scikit 等硬库**。django 是 SWE-bench 最易库之一。
- **影响**: 解释了 HANDOFF 的"70.4% 偏高 vs 官方 mini 40–55%"——**既非计数 bug**（196 实例 0 mismatch）**也非造假**（抽样真跑测试），而是**代表性**：当前分母排除了硬库，全 500 收官时该率会下降。现在报 70% = **口径孤儿**（与 9/89 教训同类）。
- **修法**: 全 500（或 repo 分层抽样）完成前**不报 resolved rate**；改报 **per-repo resolved rate**；任何对榜声明须以全集完成为门。

---

## 四、健康正信号（记录在案）

- clean-verified 196 实例账本 vs harness 真值 **0 mismatch**。
- 造假 sweep 全零：无 resolved-但-空 test_output、无 resolved-但-patch 未应用、无 resolved-但-FAIL_TO_PASS 有 fail、无 resolved-但-微型(<200B) test_output。
- 抽样 resolved 全真跑 pytest；抽样 unresolved 全为 **agent-fail**（harness 正常执行，模型 patch 未解），无 harness-fail。
- 20 个"真未评"实例均为**空 patch / 无 patch**（模型没产出 patch）→ 正确计 false，是**健康的失败会计**，非 bug。

---

## 五、给 lead 的一句话

**账本数值可签字（0 mismatch + 零造假 + 抽样真跑），但三条须动作**：① 把 3 个"藏在废弃目录"的真 resolved 收编进 clean shard 或落 provenance manifest（否则清垃圾会丢分且不可复现）；② astropy-14995 去重 + 查 s000/s001 chunk 重叠；③ **70% 严禁对榜**——纯 django 偏斜，等全 500 或分层抽样，改报 per-repo。收官终核建议按同一 report.json-真值法复跑本审计脚本。

*审计脚本（只读）: 本地 scratchpad `full500_audit.py` / `full500_audit2.py`，在 dev 经共享 FS 运行，未向 BASE 写入。*
