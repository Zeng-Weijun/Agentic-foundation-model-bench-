# CERT — SWE-bench Multilingual 两次 run 独立对抗签核

**签核人身份**: 独立签核人(与另一位互不可见)。任务 = 尽最大努力证明分数**错**。
**审计方式**: 只读盘上产物,host `env-kvm-57740737-bzw56...pod`(内部 `rjob-ac00b0a8ab8a50fe-...-0`);pod 时钟 UTC(本地 Mac 已跨到 07-11,pod 仍 07-10)。
**签核时间**: 2026-07-10T17:xx Z(pod 时钟)。sglang 已被用户主动关闭(`100.100.104.140:3000x` 不可达 = 预期,未探活)。

## 审计对象
```
A  Multilingual × Qwen3-Coder-30B-A3B-Instruct × qwen-code 0.16.2
   run_root .../runs/sweml_coder_qwencode0162_clean274_20260710t083916z
   声称 57/274 = 20.80% · results.jsonl sha256 aab29ee4...
   run 窗口: RUN_ID=08:39:16Z → results.jsonl mtime 10:28:22Z
B  Multilingual × Qwen3-30B-A3B-Instruct-2507 × qwen-code 0.16.2
   run_root .../runs/sweml_instruct2507_qwencode0162_clean274_20260710t103651z
   声称 22/274 = 8.03% · results.jsonl sha256 cc41b1de...
   run 窗口: RUN_ID=10:36:51Z → results.jsonl mtime 14:05:23Z
数据集: 274 clean = 官方 300 − 26 Java-Gradle 离线断链题
```

---

## 攻击线 1 — 分数 · **CONFIRMED(两 run 干净)**

独立复算(`python3 json.loads` 逐行,`resolved is True` 严格身份判定):

| | rows | unique | dup | resolved is True | resolved 值分布 | sha256 复算 |
|---|---|---|---|---|---|---|
| A | 274 | 274 | 0 | **57** | 57 True + 217 False | `aab29ee4bfbe7e6e79070020be82ef9e2cb602b6227d1097322aead99ac1caed` == 声称 |
| B | 274 | 274 | 0 | **22** | 22 True + 252 False | `cc41b1de7bed1fd491c1d59132001e763705ac09dfed65d5f59fd4e26a516fd9` == 声称 |

- 分母 = **274**(非"已完成行数"),两 run 均 274。无 None/null/字符串型 resolved。
- 57/274 = 0.208029 = 20.80% ✓ ; 22/274 = 0.080292 = 8.03% ✓。
- 路径: `<run>/results.jsonl` ; `<run>/score_summary_clean274.json`。

---

## 攻击线 2 — 分母缺陷 / 静默丢行 · **CONFIRMED(healthy,已修复且无虚增)**

**A 确实丢了 3 行**(orchestrator eval_error/infra_error 路径),3 行为 `facebook__docusaurus-8927 / projectlombok__lombok-3479 / tokio-rs__tokio-7139`:
- `DENOMINATOR_BLOCKED.json`: 丢行时 `status=blocked_denominator_mismatch, results_rows=271, missing_instance_ids=[上述3]` —— 编排者**没有**用 271 当分母硬报,而是 block 等修复。
- **★对抗关键**: `DENOMINATOR_BLOCKED.json` 在 271 行状态下 `resolved` 已经是 **57**。3 个 repair 行补回后全部 `resolved=false`。⇒ **57 分与 repair 完全无关,repair 只补分母不加分**。
- 3 repair 行 provenance(`repairs/<id>/.../REPAIR_PROVENANCE.json` + results 行):`agent_rerun:false`, `intermediate_mjs_reused:false`, `repair_eval_only:true`, `original_eval_rc:1 → eval_rc:0`, `source:repaired_after_cleanup_race`。
- **冻结 patch 逐字节验证**: docusaurus `input_model_patch.diff` sha256 = 原始 `failed/.../agent/prediction.patch.diff` sha256 = `7f83c8c6dc1707a8...`(相同)。未重跑 agent、未复用旧 .mjs、patch 冻结。
- cleanup race 属实: 栈顶 `docker.errors.NotFound: 404 ... No such container`(容器被清理引发 list 404)。A `FINAL_CODER_CLEAN274_STATUS.json` 注明 404 发生在"after official test result"(裁决已得出之后崩溃)。
- `cleanup_race_repair.rc=0`, `cleanup_race_repair_summary.json status=pass, results_rows_after=274`。

**B 无类似丢行**: 274 instances、**无 `failed/` 目录**(B 全程用带 ignore_removed 的 wrapper,不触发 cleanup-race 崩溃)。

**两 run instance_ids 精确 == clean274 manifest**(274 ids, 0 缺 0 多, A==B)。manifest sha256 `d68a0cb1ba9daebd...`。

---

## 攻击线 3 — 证据完整性 · **A=CRITICAL 缺陷(ORIGINAL_LOST)/ B=洁净自证** ★★决定性不对称

### eval_wrap.py 事故(今晚最严重)
- **A**: `eval_wrap.py` sha256 `81cb668d25cecce8...`,mtime **10:27:03.350656Z**(size 839)。A run 窗口 08:39→10:28Z,该文件在**结束前 75 秒被覆盖**。
- **B**: `eval_wrap.py` sha256 `81cb668d...`(**同 A**),mtime **10:37:13.033571Z**(B 于 10:36:51Z 启动,即启动时生成)。
- **⇒ A 与 B eval_wrap 现在字节相同(81cb668d),但成因相反**:A 是被 repair 覆盖后碰巧等于 B 的内容;B 是其真实 launch wrapper。

### A: `repairs/provenance_caveat_20260710T104300Z/EVAL_WRAP_PROVENANCE_AUDIT.json` — **severity=CRITICAL, status=ORIGINAL_LOST**(独立复核,证成编排者结论)
- `launch_original_status: "ORIGINAL_LOST: no launch-time eval_wrap sha256 or immutable snapshot exists"`。
- `overwrite_reason`: eval-only repair 实例化 patched runner,其 `_write_eval_wrap()` 用 `ContainerCollection.list(ignore_removed=True)` 重写了 run_root/eval_wrap.py(10:27:03Z)。
- `mixed_eval_environments`: 主环境 = **wrapper without ignore_removed**(271 rows);repair 环境 = **with ignore_removed=True**(3 rows)。
- recovery candidate = canary 的 `.../sweml_coder_qwencode0162_canary_pathfix_.../eval_wrap.py`(sha `dca24b59...`, **532B**, 无 ignore_removed),`matches_recovery_candidate_sha256:false` —— 与当前 839B 文件不符,仅内容候选,**无密码学链接,不能当原件**。
- A 现盘上的 `eval_wrap.py` 内容 = 含 `ContainerCollection.list` ignore_removed monkeypatch 的 **repair wrapper**,**不是**评了 271 主行的那个。A `FINAL_CODER_CLEAN274_STATUS.json` `provenance_status: MIXED_EVAL_ENVIRONMENTS_DISCLOSED`。

### B: 全程 pin 可自证(独立复核 = PASS)
- `provenance/EVAL_WRAP_LAUNCH_PIN.json`(launch,mtime_ns 1783679833033570808)与 `EVAL_WRAP_FINAL_VERIFY.json`(14:08:11Z 复验)三元组**精确相等**:sha256 `81cb668d...` / mtime_ns 1783679833033570808 / size 839,`exact_match:true, status:pass`。
- 我独立复算 B eval_wrap sha256 = `81cb668d...` 匹配。pin 为 run 活跃期 13:48Z 追溯创建(honest disclosed),但记录的 mtime = 10:37:13Z(launch),且 launch→final 全窗口 mtime_ns 不变 ⇒ B 全程 eval_wrap 未被改。

### 全量篡改扫描 · CLEAN
- A `instances/`+`failed/` 证据文件 mtime 晚于 run 结束(10:28:30Z)= **0** 个。
- B `instances/` 证据文件 mtime 晚于 run 结束(14:06Z)= **0** 个。
- 源脚本: orchestrator sha `1f57d23b...`(mtime 09:27:27Z)、launcher sha `66e04d2d...`(mtime 08:29:43Z)== B LAUNCH_PIN 记录;dataset parquet sha256 `28b7f874...` == contract。
- 注: orchestrator mtime 09:27:27Z **晚于 A 启动 08:39Z**(cleanup-race 发现后 ~09:27Z 打了 ignore_removed 补丁),但 A 的 Python 进程 08:39Z 已加载旧版;无法证明 A 主行 orchestrator 原貌 —— 与 eval_wrap 同为 A-provenance 弱点。B 于 10:36Z(补丁后)启动,用的是 pin 记录的 09:27Z 版,一致。

**⇒ A 与 B 能否洁净直比? 不能。** A 的 271 主行 eval wrapper 不可复原(ORIGINAL_LOST),B 全程 pin 自证。但差异变量 = `ignore_removed`(仅影响容器清理 404 是否崩溃,**不改变测试裁决**),且裁决独立由 harness report 背书(见线 5)。

---

## 攻击线 4 — 模型身份 · **A=完整验证 / B=valid-with-caveat(判定合理)**

- **A**: `serving_config/get_model_info_{before,after,post_repair}.json` model_path 全 = `.../models/Qwen3-Coder-30B-A3B-Instruct`(以要求后缀结尾)✓。**before + after 均抓到**,身份闭环。
- **B before**: model_path = `.../models/Qwen3-30B-A3B-Instruct-2507`(要求后缀)✓,arch `Qwen3MoeForCausalLM`,seed 525168126。
- **B after = UNVERIFIABLE(一级 caveat,非 invalid)** —— 独立核对判定合理:
  - launcher after 缺失;`provenance/get_model_info_postrun_recheck.json` 14:19:58Z `urlopen error timed out`;`..._noproxy.json` 15:05:17Z `curl rc=28 http 000`。端点确不可达。
  - 时序: B 末行 ts = **14:05:23Z**(serving 在线产出 274 行),首次失败 recheck = **14:19:58Z**(晚 14.5 分)。⇒ serving 在 run 期间在线,run 后才被关。**未观察到 mismatch**,只是 after 无法采集。
  - `INSTRUCT_FINAL_STATUS_WITH_IDENTITY_CAVEAT.json` 明列裁决规则: before/after mismatch → INVALIDATE;after 不可采 → **retain-score-with-primary-caveat**。observed_case = AFTER_CAPTURE_UNAVAILABLE ⇒ 保分+caveat 正确。早先 QUARANTINE 状态被此 caveat 诚实 supersede(未删)。
- **sglang 不校验 model 名** —— 只认 get_model_info 的 model_path(已认)。
- **agent 侧 LLM error 计数(独立复算)**: 548 adapter log/stderr 文件,`connection_refused=0 / http_5xx=0 / read_timeout=0`。
  - ★我的粗 grep 抓到 1 个 "timeout" = `axios_u_axios-4738/agent/qwencode_attempt_1.log` 里的 **axios 仓库源码** `AxiosError.ETIMEDOUT` / `'timeout of '+timeout+'ms exceeded'`(模型在编辑 `/testbed/lib/adapters/http.js`),是 repo 文本假阳性 —— 正是 audit 结构化排除 tool_result 文本的理由。⇒ audit 的 0/0/0 **诚实**。
  - 明确: 此为 **supporting evidence 非 proof**(不能证 serving 从未重启)。

---

## 攻击线 5 — trace 真实性 + 作弊 · **CONFIRMED 干净(全量,非仅抽样)**

工具事件按正确层计数(`message.content[]` 里 `type==tool_use/tool_result`,非顶层 tool_calls):

| run | resolved | resolved-空patch(≤1B) | resolved-零tool_use | resolved tool_use[min/med/max] | resolved patch_bytes[min/med/max] |
|---|---|---|---|---|---|
| A | 57 | **0** | **0** | 6/24/93 | 309/1158/5088 |
| B | 22 | **0** | **0** | 2/10/329 | 454/770/45929 |

- 空 patch 只出现在 unresolved(A 19 / B 89,agent 没产出 patch → 正确判 fail),零 tool_use 全局 = 0。
- **★最强完整性交叉**: results.jsonl 的 `resolved` vs 底层 SWE-bench harness report 的 `resolved_ids` 成员关系 —— 两 run 各 274/274 **零 mismatch、零缺 report**。纯从 report 重算 resolved = **57 / 22**,与声称完全一致。⇒ 分数确由真实 harness 裁决派生,无翻行。
- trace 抽样(工具名序列): A `astral-sh__ruff-15443`(resolved,26 工具: grep_search×5 / glob×6 / read_file×3 / write_file×2 / edit×2 / run_shell_command×5 / todo_write×3);B `axios__axios-5892`(resolved,6 工具: grep_search / read_file / edit / todo_write)。真搜索、真读文件、真改代码。

---

## 攻击线 6 — Lombok 0/17: 模型自伤 vs 评测污染 · **CONFIRMED 模型自伤(有效未解决,不该剔除)**

- 274 里 17 个 Java **全是** `projectlombok__lombok`(其余 Java 已在 26 排除里)。A 0/17,B 0/17。
- Qwen patch 注入 `test.instance` target 到 `buildScripts/tests.ant.xml`: `LOMBOK_FAILURE_PATTERN_AUDIT.json` 记 B 17/17 改该文件(16 个同签名 `e78250c8...`,15 个只改这一个文件);A 16/17 同模式。我读 patch 亲见 `+<target name="test.instance" depends="test.compile, test.formatter.compile" ...>`。
- **独立读 5 个 lombok test_output.txt**(3009/3042/2792/3052/3312)全部:
  ```
  BUILD SUCCESSFUL
  + ant test.instance
  BUILD FAILED
  Target "test.instance" does not exist in the project "lombok".
  ```
  ⇒ eval_rc=0 但**测试从未跑**(target 不存在)。
- 旧本地 relay GPT control 的 run id、分数与逐题结果已于 2026-07-21 从当前发布面移除；不得从本证书重建。
- **Qwen 自身证据链**:patch 改坏自己的评测构建文件，随后 `ant test.instance` 因 target 不存在而失败 → 有效"未解决",**不是**像 26 Gradle 那样的环境假零。**正确保留在 274 分母内**。
- caveat: `LOMBOK_FAILURE_PATTERN_AUDIT.json` 自标 `causal_limit`(patch+score 证成同一可观测失败模式,不单独证内部机制)—— 措辞谨慎,认可。

---

## 攻击线 7 — per-language 口径 · **CONFIRMED**

`swemultilingual_clean274_contract_20260710.json`:
- `full_task_count=300, excluded_task_count=26, clean_task_count=274`。
- 排除 26 = `apache/druid 5 + apache/lucene 9 + google/gson 9 + javaparser/javaparser 2 + reactivex/rxjava 1`(=26,全 Java-Gradle),reason = "Gradle build chain not closed under offline evaluation; tests did not run, producing false zeros"。
- dataset parquet sha256 `28b7f874...` 独立复算匹配(数据集冻结完好)。
- 两 run per_language 均 **9 语言** 求和 = 274:
  - A: C 7/30, C++ 6/12, Go 8/42, **Java 0/17**, JS 6/33, PHP 4/43, Ruby 9/44, Rust 15/43, TS 2/10 → 57。
  - B: C 3/30, C++ 3/12, Go 2/42, **Java 0/17**, JS 2/33, PHP 1/43, Ruby 6/44, Rust 3/43, TS 2/10 → 22。
- Java 栏零已由攻击线 6 解释。
- **scaffold caveat**: contract 声明本 run 用 qwen-code **0.16.2**(非旧 0.15.6),"非精确同脚手架复现";但 A/B **都用 0.16.2**,彼此脚手架一致(node/cli sha pin 齐)。
- 报分务必写 274 clean 子集(= 300 − 26),**不得简写成 300 的分数**。

---

## 最终判定

| run | 分数 | 判定 | caveat |
|---|---|---|---|
| **A** Coder | 57/274 = **20.80%** | **valid-with-caveat** | 分数本身 sound(harness 背书 / 分母 274 正确 / trace 真 / 模型 before+after 已验 / 57 分独立于 repair)。**CRITICAL provenance caveat**: eval_wrap ORIGINAL_LOST、271 主行 wrapper 不可复原(MIXED_EVAL_ENVIRONMENTS_DISCLOSED);此 caveat 关乎证据溯源与可比性,**不推翻分数**(差异变量 ignore_removed 只影响崩溃处理不改裁决)。 |
| **B** Instruct-2507 | 22/274 = **8.03%** | **valid-with-caveat** | 分数 sound(harness 背书 / 分母正确 / trace 真 / before-身份已验 / eval_wrap 全程 pin 自证 / 无 run 后篡改)。**primary caveat**: serving-identity-**after** UNVERIFIABLE(端点 run 后被关;before 已证、无重启证据、未见 mismatch)。 |

### 一句话结论
> **A 与 B 的分数各自成立**(均未虚增:分母 274 正确、resolved 由真实 SWE-bench harness report 逐题背书重算 = 57/22、无空-patch-resolved、无零-tool-resolved)。**但两者不能作为洁净并排比较**:A 的 271 主行 eval wrapper = ORIGINAL_LOST(CRITICAL,不可字节复核)、模型-after 已验;B 的 eval wrapper 全程 pin 自证、但模型-after = UNVERIFIABLE —— provenance 不对称。可作**方向性**结论(20.80% vs 8.03%,2.6× 差距远大于 ignore_removed 这种崩溃处理差异,且同数据集/同 274 子集/同 0.16.2 脚手架/同 harness),但**严禁**表述为字节洁净的配对 head-to-head,须并列声明上述不对称 caveat。编排者 `cross_run_comparison_caveat` 亦如此说,我独立复核得同一结论。

### 最有杀伤力的 3 条证据(带路径)
1. **A eval_wrap 被 run 内覆盖 → ORIGINAL_LOST**: `repairs/provenance_caveat_20260710T104300Z/EVAL_WRAP_PROVENANCE_AUDIT.json`(`severity:CRITICAL, status:ORIGINAL_LOST, overwrite_utc 2026-07-10T10:27:03.350656Z, main_scored_rows 271 = without ignore_removed`)。A 现盘 `eval_wrap.py`(81cb668d,839B)是 repair wrapper,非评 271 主行者。
2. **A 与 B eval_wrap sha256 现已相同(81cb668d)但成因相反** —— A `eval_wrap.py` mtime 10:27:03Z(被覆盖)vs B `provenance/EVAL_WRAP_{LAUNCH_PIN,FINAL_VERIFY}.json` mtime_ns 1783679833033570808 `exact_match:true`(pin 自证)。正是"看起来同一 wrapper 故可比"这一天真结论的陷阱。
3. **B 模型-after 不可证**: `provenance/INSTRUCT_FINAL_STATUS_WITH_IDENTITY_CAVEAT.json`(`serving_identity_after.status:UNVERIFIABLE`)+ `provenance/get_model_info_postrun_recheck.json`(14:19:58Z `urlopen error timed out`)—— B 无法证明末行(14:05:23Z)之后模型未被换(before 已证 Instruct-2507、无重启证据 = supporting 非 proof)。

### 补充: 我尝试证伪但失败的攻击(= 分数站得住的正面证据)
- 想抓虚增分: resolved 纯从 harness report 重算 = 57/22(0 mismatch),3 个 A repair 全 resolved=false 且 57 分在 repair 前已存在。**证伪失败**。
- 想抓作弊: 0 个 resolved 空 patch、0 个 resolved 零 tool_use(全量)。**证伪失败**。
- 想抓 Lombok 环境假零(该剔除):Qwen patch 与 test-output 的逐题因果链显示 target 被模型改坏。**证伪失败(是 Qwen 自伤,该保留)**；旧本地 GPT control 结果已移除。
- 想抓分母污染: 两 run ids 精确 == clean274 manifest,dataset parquet sha 冻结匹配。**证伪失败**。
- 想抓 run 后篡改证据: instances/+failed/ 零文件 mtime 晚于 run 结束。**证伪失败**。

**未能证明任一分数被高估。** 唯一实质缺陷是 A 的 eval-provenance(ORIGINAL_LOST)与 B 的 after-身份(UNVERIFIABLE)——均已被编排者主动披露,均属**可比性/溯源** caveat 而非分数错误。
