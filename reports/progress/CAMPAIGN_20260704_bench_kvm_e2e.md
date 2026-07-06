# 战役进度汇总 — bench KVM E2E（2026-07-04）

> 整理:85(by-85)| 范围:tau3 / full500(SWE-V) / TB2.1 / V2 runner / 官方榜对照
> 权威细节见:`_coordination/bench_kvm_e2e_20260704/{DECISIONS,HANDOFF}.md`、`reports/full500_midrun_audit_20260704.md`、`reports/tau3_transport_proof_20260704.log`、`reports/official_leaderboard_vs_relay_20260704.md`

---

## 1. tau3 transport-proof —— 双签正式关闭 ✅

- **状态:** DoD-③ COMPLETE / **口径 = spec-closed·execution-blocked**（`dockerfile_offline_ready=false` 保留:内网 mirror + commit-pin 物化,非 offline-build-ready)。
- **镜像(P0 by-digest,均实测 200):**
  - main `100.97.118.137:8555/swe-data-harness/tau3-full-main@sha256:3591be51f3901080271eb4a9c1bd9c680fc999ced3c44fc42ccec7d788e81645`
  - runtime `@sha256:bf0f3ab41886d31db8f7c93f874d63420c1679733dcce1e4c0663c1c11117fa8`
- **构建修复:** `[all]` extra + `build-essential`(gcc+libc6-dev)→ 解 `tau2.voice→scipy/pyaudio` import 崩溃;apt/pip 内网 mirror。
- **数据集冻结:** 隔离 2 个畸形 WIP 目录(`tau3-{telecom,banking_knowledge}-0`,其 `task_config.json` 竟是目录)→ freeze **恢复到** `350576c2`;preflight 硬化为按 frozen taskid_list(`ef22ab27`)fail-closed,PASS 375/375。
- **Pod A transport-proof(env-kvm-15238487-rlgbn):PASS 4/4** —— 每域每任务 5 检:`TASKCFG_SHA_MATCH`(挂载 sha256==源)+ `SIDECAR_8000_UP` + `IMPORT_TAU2_FASTMCP_DOMAINS_OK`(55#1)+ `MAIN_TO_SIDECAR_LINK_OK` + `NO_PUBLIC_NET_CONFIRMED`(55#3)。
- **双签:** 85 交付 + **55 复核 PASS**(独立 Pod A 重跑 airline-0 完整复现)。
- **Commits(origin/main):** `0c69e60` → `9be6e20` → `623eeab` → `3adbfe3`。**证据:** `reports/tau3_transport_proof_20260704.log`。

---

## 2. full500(SWE-V)—— 停止点(用户令),账本冻结快照 + 审计双签

**停止点:** 用户令停,账本冻结快照留档(Pod B `swev_full500_model_20260702`,中期,gpt-5.4-mini)。独立审计(surface:86,只读)结论 = **数值可签字,可复现性脆弱**:

- **对账(真值源=每实例 `report.json`):** resolved **154/219 = 70.3%**;clean-report 196 实例账本 vs harness 真值 **0 mismatch**;零造假信号(抽样 resolved 全真跑 pytest,unresolved 全 agent-fail、harness 健康)。
- **154 口径的脆弱性(可争 151/154/155):** 154 = 151 clean shard + **3 个真 resolved 藏在被改名的废弃后缀目录**(`.dockerinstability`);对 clean 目录重算只得 **151** → 账本当前无法从 clean 复现;换口径可争 155(补 django-11749)或 151(剔那 3 个)。
- **★ 70.3% 严禁对榜:** 已完成集 = astropy 22 + django 197(纯 django 偏易,无 sympy/matplotlib/sphinx 硬库)→ 代表性偏斜,是**口径孤儿**(与 9/89 同类);gpt-5.4-mini 三榜均无官方锚。
- **四 ISSUE(见 audit 报告):** ①3 resolved 只由废弃目录背书(须收编/落 provenance,对账前禁删后缀目录)②astropy-14995 双评双写(去重+查 chunk 重叠)③废弃目录 resolved 规则不一致(须定确定性规则)④70.3% 是 django 偏斜中期数(全 500 或分层前不报 rate,改 per-repo)。
- **档案:** `reports/full500_midrun_audit_20260704.md`。

---

## 3. TB2.1 金丝雀 8 任务重跑 —— 进行中

- **canonical oracle 账目:79/89 resolved**(`reports/scores/tb21_full89_oracle_infra_map_r5_final_20260703.{md,json}`)。
- **10 个未解:** 8 属旧 rootless docker 栈的 `docker_api_eof_before_injection`(**环境类**),正在 **privileged 栈(fuse-overlayfs)金丝雀重跑**,预计多数转绿 → **预期 ~87/89**;剩 2(`rstan-to-pystan`/`query-optimize`)待官方 baseline 判决,可能归档 upstream-bug。
- **口径:** bug-for-bug,不改官方缺陷;qemu 类任务需 `/dev/kvm` 才贴官方。**55 执行 / 85 审查**(跨家族对抗)。

---

## 4. V2 runner 转向 —— 设计中

- SWE-V 全量入口将从当前 shard 式 runner 换成 **V2 runner**:**去 shard** + **run-eval 串联**(取消跑/评两段分离)+ **并发 c100**。
- 目标:消除 full500 审计暴露的 chunk→instance 分配重叠(ISSUE-2)+ 双写(ISSUE-2)+ 后缀目录漂移(ISSUE-1/3)类脆弱性。
- 状态:51 设计/实现中;就绪后更新 E2E 文档 §1.3(`docs_handoff/E2E_REPRO_SWEV_TB21_20260704.md`)。

---

## 5. 官方榜 × 中转站对照 —— 进行中

报告 `reports/official_leaderboard_vs_relay_20260704.md`(源=官方 JSON/HTML,非三方聚合):

- **干净可复现锚仅 2 个:** ① SWE-V bash-only(mini)**gpt-5.2-high = 72.8% / 500 pass@1**(=我方口径,首选验 harness 合格证);② TB2.1 terminus-2 **gpt-5.5 = 78.2% / 89×5**。
- **选型:** P0 先打 gpt-5.2-high→72.8% 作 harness 合格证;P1 gpt-5.5+terminus-2→78.2%。
- **口径警示(硬):** ①**TB2.1 = 5 attempts 非 ×3**(发射器须改)②SWE-V 榜冻结~2026-02(5.3/5.4/5.5 不在榜)③三方站 "GPT-5.5 82.6%/Opus4.8 88.6%/Fable5 95%" 官方 0 命中 **严禁引** ④RepoZero 官方 **400 案非 188**、无 LLM judge ⑤**gpt-5.4-mini 三榜全无官方锚** → full500 不可直接对榜(佐证 §2 的 70% django 虚高)。
- TB2.0(勿混):Qwen3-Coder-480B 23.9 ✓ 锚吻合。

---

*红线(全程守):所有容器 `--network none`/compose 内网;bug-for-bug 不改官方;0 无授权模型调用;Pod B full500 运行中零扰动(审计全程只读)。*

---

## UPDATE 2026-07-05

- **full500 停止点审计终稿:** 去重重算 **resolved = 177 / mismatch = 0**(可签字）。**70.5% 严禁对榜**（django 偏斜、gpt-5.4-mini 三榜无官方锚）。django-11133 裁定 = **选项 A**（4 份独立 eval 佐证 verdict，patch 抖动非造假；任何引用 177 处加脚注"1 例 provenance 例外"）。
- **V2 runner:** 设计**已批准**；smoke10 在跑，放行门槛 = **10/10 rows、0 failed**。
- **TB2.1 收口金丝雀:** 55 执行 + 85 独立复审 **双 PASS** —— privileged 栈消除 `docker_api_eof_before_injection` 类（3 可跑任务达真 pytest 执行、0 EOF），四项最小修复清单 1:1 对应根因且覆盖全 8 → **修复放行**。
- **运维教训三条:** ① cmux `send` 后须单发 Enter（竞态，漏则卡输入框）；② gpfs 全树 `find` 禁用（灾难性空转，按精确证据路径直读）；③ flaky ssh 长内联命令中途断连 → 改**共享盘脚本 setsid 后台跑 + 经 dev 读结果文件**验证。

---

## 终章 2026-07-05 — 战役闭合

### 两 bench 终分（同口径,board-comparable）

| bench | 口径 | 终分 | 官方锚对照 |
|---|---|---|---|
| **SWE-bench Verified** | gpt-5.5 high · mini-swe-agent v2.0.0 bash-only · 单次 pass@1 · 0 infra | **386/500 = 77.2%** | 同口径 gpt-5.2-high 72.8% → **+4.4pp** |
| **Terminal-Bench 2.1** | gpt-5.5 terminus-2 medium · 单次 pass@1 · Pod A privileged | **63/89 = 70.8%**（headless-terminal parse_error 假阴性修正,原 62/89） | 官方 78.2±2.4 为 **5 跑均值**;差距=单样本方差+medium 档+env 天花板+小幅真差距 |

**口径红线:** 两分均**单跑**(方差 ±3-4pp),gpt-5.5 均**不在**冻结官方榜 → 皆为**延伸官方锚的同口径新基线**,非"官方榜分"。SWE-V 可宣称对 gpt-5.2-high +4.4pp;TB2.1 单跑 70.8% 不异常于 78.2% 五跑均值,但**不可直接当榜数**。

### 修复链（三大,全 dual-sign PASS）

1. **tau3 DoD-③**（transport-proof)：`[all]`+build-essential 解 scipy/pyaudio import 崩溃;冻结恢复 350576c2+隔离 2 畸形目录;preflight 硬化(frozen taskid_list);Pod A 四域 transport-proof 4/4。→ spec-closed/execution-blocked。
2. **TB2.1 收口金丝雀**：privileged 栈消除 `docker_api_eof_before_injection` 类;四修复(symlink-payload/tqdm/toml/git-protocol)→ 8 EOF 任务 6 恢复 → canonical map **79/89 → 85/89**。
3. **SWE-V v2→v2.1**：docker-125 镜像-preflight harness bug(211/212 no_patch=agent 容器没起)→ 43.6%(harness 分) **→ 77.2%(模型分)**。★最大教训:低分先查 harness 再归模型。

### 全部教训

**运维:**
- cmux `send` 后须单发 Enter(竞态,漏则卡输入框)。
- gpfs 全树 `find` 禁用(灾难性空转)→ 按精确证据路径直读。
- flaky ssh 长内联命令中途断连 → **共享盘脚本 setsid 后台跑 + 经 dev 读结果文件**验证。
- 维护机杀进程树(nohup 不保)→ 脚本上共享盘 + 一键重跑;P0 registry 与 builder 同机=脆弱。

**复审方法（对抗）:**
- `eval_rc=0` 只量 eval 步,**漏 agent-side infra**(docker-125)→ 分层核 agent 与 eval 两步。
- `parse_error`/scorer 假阴性(headless-terminal ctrf 7/7 却算未解)→ 交叉核 ctrf vs strict scorer。
- `external_network_marker` 假阳性(匹配 pytest 警告里的 docs URL)→ marker 须排除 docs/warning URL。
- jq 嵌套路径 bug(patch 嵌 instance_id 键下)→ 读真结构,别信首层。
- **单跑 ≠ 5 跑均值;harness-bug 分 ≠ 模型分**——对外口径前必拆解。
- 模型可赢过 oracle(git-multibranch/rstan 模型过 oracle 官方解挂)→ oracle map 非绝对天花板。

### 红线全程守住
所有容器 `--network none`/compose 内网 · bug-for-bug 不改官方 · 0 无授权模型调用 · Pod B full500 运行中零扰动(审计只读) · 数据集畸形目录**隔离非删**(可逆) · git 全走隔离 worktree(零触碰他人脏树 WIP)。

**战役 bench-review 链正式闭合。** 交付:tau3 镜像+manifest / TB2.1 canary map 提案 85/89 / SWE-V 77.2% 终分 / E2E 复现命令包 / 全审计+归因表。

---

## 二期总结 2026-07-06 — 复审链全收官

二期 = 85 金丝雀审查位对 55/51 执行的全部真模型 run 的对抗复审。核心产出:**把 harness/scaffold/环境噪声从模型真实力里剥出来**。

### ★ 五点交互模式梯度（终稿,同一 SWE-V-500 / TB2.1-89）

| 模型 | scaffold | 交互模式 | 分 | 状态 |
|---|---|---|---|---|
| Qwen3-Coder-30B | QwenCode 0.15.6 | 原生多-tool-call | **48.6%** | ✅ canonical Qwen 原生(取代未验证 49% README 锚) |
| Qwen3-Coder-30B | mini-swe-agent | 单-bash-块 | 23.4% | ✗ scaffold 压低(100% 多-bash 拒绝) |
| Qwen3-Coder-30B | terminus-2 | live tmux | 10.1% | ✗ scaffold 压低(churning avg 105.8 轮) |
| gpt-5.5 | mini-swe-agent | 单-bash-块 | 77.2% | ✅ 模型-scaffold 契合 |
| gpt-5.5 | terminus-2 | live tmux | 70.8% | ✅ 模型-scaffold 契合 |

**结论:** 交互复杂度(原生→bash-块→live-终端)单调扼住 Qwen(48.6→23.4→10.1);gpt-5.5 在两 scaffold 都稳(77.2/70.8)。**自研 harness ROI 在交互层不在模型**:mini 类需修多-bash parser;terminal 类需屏幕摘要+收敛护栏。

### RepoZero 翻案链(28.2 → 67.0 → 67.55)

| 跑 | 分 | 判定 |
|---|---|---|
| 原始 | 28.2%(127/188) | ✗ 无效:磁盘满,68% oracle_rc=126 不可评分 |
| rejudge v1 | 67.0%(126/188) | ✗ 不可验证:rejudge 期间磁盘二次满,48/53 pass-claim 与证据矛盾 |
| **v2** | **67.55%(127/188)** | ✅ **PASS**:证据一致断言+冻结快照+磁盘监控+3600s watchdog(0 触发);127 passes 全 storage_error=false |

67.55% caveat:188 rescue 偏子集(非 400 官方)、无 LLM judge、单跑 → 非榜数、不可 vs Claude。

### 补跑/报废配额记录(55/51 真模型消耗)

以下 run 因 harness/环境噪声产出不可用数,需补跑(compute 报废,非模型问题):
- SWE-V gpt-5.5 v2 **43.6%**(docker-125 镜像未 preflight,42% agent 容器没起)→ 补跑 v2.1 **77.2%**。
- RepoZero 原始 **28.2%** + rejudge v1 **67.0%**(磁盘满×2)→ 补跑 v2 **67.55%**。
- QwenCode 6 月 frozen **23.4%**(v4.3+116 未完成 infra 降级)→ 补跑 v2.1 **48.6%**。
- 教训:低分先查 harness/环境(docker-start/磁盘/scaffold-fit)再归模型;`eval_rc=0` 不代表 agent 端无 infra。

### ⛔ 禁引用数字清单（口径孤儿 / scaffold 压低 / 已报废）
`23.4%`(Qwen mini)· `10.1%`(Qwen terminus-2)· `28.2%`/`67.0%`(RepoZero 磁盘)· `43.6%`(SWE-V v2 docker-125)· `23.4%`(QwenCode 6月降级)。

### ✅ 可引用终分（带各自 caveat)
| bench | 模型·scaffold | 分 |
|---|---|---|
| SWE-bench Verified | gpt-5.5 · mini v2.0.0 | **77.2%** |
| SWE-bench Verified | Qwen3-Coder-30B · QwenCode 0.15.6 | **48.6%** |
| Terminal-Bench 2.1 | gpt-5.5 · terminus-2 | **70.8%**(headless 假阴性修正后) |
| RepoZero(188 子集) | gpt-5.5 · codex Py2JS | **67.55%** |

**复审方法论沉淀:** eval_rc 只量 eval 步(漏 agent-side docker-125)· parse_error/scorer 假阴性交叉核 ctrf · extnet 假阳性排 docs-URL · 磁盘证据须冻结快照防二次覆盖 · scaffold-fit ≠ 模型力 · 单跑 ≠ 均值。

**本战役 bench 复审链正式全收官。**
