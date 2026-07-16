# ProgramBench × Qwen (Coder / Instruct-2507) × qwen-code — Dual-Sign Review (Round 13 candidate)

**日期**: 2026-07-16 · **口径**: 与 REPRODUCTION_INDEX.md 12 条一致 — 每条 ≥2 个独立盲审跨族双签(A=Claude, B=真 codex-pro / gpt-5.6-sol reasoning=ultra)。默认分数是假的、尽力证伪,证不倒才判 REAL。

## 结论: **REAL**（A + B 双签独立收敛,证不倒）

| # | Bench | Model | Scaffold | 真实分数(honest) | Denom | 双签(A / B) |
|---|-------|-------|----------|----------------------|-------|-------------|
| 13a | ProgramBench | Coder | qwen-code | **mean 11** (raw 2282/200=11.41; exact pre-rounding 11.419252476, per-instance-rounded-then-averaged 11.41 — both round to 11) | 200 | Claude✓ / codex✓ (gpt-5.6-sol, real run, exit 0) |
| 13b | ProgramBench | Instruct-2507 | qwen-code | **mean 0** (raw 29/200=0.145; exact pre-rounding 0.151091785) | 200 | Claude✓ / codex✓ (gpt-5.6-sol, real run, exit 0) |

`codex✓` = B 真跑 codex-pro (gpt-5.6-sol) 成功。Dispatch 时系统已有 37 个 gpt-5.6-sol 进程 / 9 个 codex-pro exec 会话在跑(远超"6+"阈值),给了等待窗口后仍成功独立完成(未 fallback)。

## 复现方法论(A = Claude)
1. SSH 到 KVM (`env-kvm-57740737-bzw56...@h.pjlab.org.cn`),读 `runs/programbench_full201_{coder,instruct}/orchestrator.log`(326KB / 662KB,完整下载本地校验字节数)。
2. 独立 parse 最后一个完整 `PHASE3 EVAL-AGGREGATE...PHASE3 COMPLETE n_scored=200` 表(200/200 行,prefix-matching 处理长名截断),手工求和: Coder sum=2282/200=11.41,Instruct sum=29/200=0.145。
3. 用官方工具 `programbench info <eval_out/subs>`(只读,5.5s/1.4s)在**真实** eval_out 上重新聚合,与手工结果、与 orchestrator.log 完全一致。
4. **从零重跑官方判分**(`programbench eval`,真 docker 编译+测试,非读缓存)4 例: gold cmatrix(✅=100/506)、coder cmatrix(82/506)、instruct cmatrix(0 compile_failed)、instruct genact(0 compile_failed)。逐一 sha256sum 验证 submission.tar.gz 字节与原始一致。全部精确复现原分数。
5. 抽查 5 个 Instruct 非零分实例(hexyl/xsv/lz4/lnav/typst)的 `submission.tar.gz.agent.log`,确认真实 `write_file` 调用 + 真实 C/Rust 源码(如 lnav 的手写 CLI help text clone)。
6. 确认 quinn (`quinn-rs__quinn.bb359cc`) 在 Coder 侧标 `HAS_COMPILE` 后于 `eval_results_read_failed`(区别于 `compile_failed`),headline 保守记 0 分 — 是 harness 结果读取失败,非 model 0。
7. Diff ProgramBench 源任务目录(201)与 run 的 subs/(各 200),唯一差集精确为 `testorg__calculator.abc1234`(fixture),无其他静默排除。
8. 抽查 3 个 Coder 部分分实例(zip=29/zoxide=11/chroma=3)agent log,确认 35-60 轮真实多轮工具调用(非退化输出)。

## 复现方法论(B = codex-pro / gpt-5.6-sol, 独立无重叠样本)
- 独立 parse orchestrator.log 最后完整块 + `programbench info` 官方重聚合 → Coder=11/200, Instruct=0/200,与 A 完全一致。
- **读了 programbench 判分器源码**(`eval/eval_batch.py:109-118`, `eval/eval.py:219-222`)解释精确算法(active-branch/active-tests 过滤 + per-instance 先取整再平均 vs 精确分数平均的细微差异,两者都四舍五入到 11 / 0,非不一致)— 解决了 A 未能完全解释的 14-branch/769-vs-506-tests 疑点。
- 从零重跑 **不同于 A 的两个实例**(coder zoxide, instruct hexyl),docker 编译+测试,executable SHA256 精确匹配 cache 值(zoxide `aa8b68...`, hexyl `4c604c...`),分数精确匹配(zoxide 11/531, hexyl 15/906)。
- 独立确认 5 个 Instruct 非零实例的 write_file 调用计数(hexyl 9 / xsv 8 / lz4 9 / lnav 9 / typst 4)+ 具体文件路径。
- 独立确认 quinn:agent log 显示 `./compile.sh` 输出 "Build completed successfully" 且 `--help` 真实运行成功(比 A 的证据更强),eval.json 记 `eval_results_read_failed`(非 compile_failed)。
- 独立确认 cmatrix compile.sh 无 `cp/mv/install/reference/gold/binary` 作弊痕迹,491 LOC(与 A 精确一致)。
- 独立确认 denom=200,且 Coder/Instruct 两侧任务 ID 集合 SHA256 相同(`1727a2e9...`),排除任何 lane 间静默替换。

---

## Findings

### BLOCKER — None
两次独立复现(A、B)均无 BLOCKER。

### MAJOR — "Instruct 全 compile_failed 从不 emit write_file" 叙述不成立
Instruct 200 例中 5 例(2.5%)分数非零,agent log 证实真实 `write_file` 调用(A: 4-10 次;B 独立计数 hexyl 9/xsv 8/lz4 9/lnav 9/typst 4)与真实可编译源码(如 hexyl `main.c`+Makefile,lnav 手写 `-h` help text)。headline mean=0.145→0 **本身仍正确**(四舍五入),但"从不产出代码"这个定性描述是错的,应更正为"Instruct 200 例中 195 例(97.5%)compile_failed/零分,5 例产出真实但极不完整的实现"。**不影响 headline 数字,但影响对失败模式的定性描述,原 brief 表述需修正。**

### MINOR — Quinn 0 分是 harness eval_results_read_failed,非 model 0(已被 brief 正确预判,A+B 双独立证实更强证据)
Coder 侧 `quinn-rs__quinn.bb359cc`:driver 标 `HAS_COMPILE`;agent log 显示 `./compile.sh` 成功编译且 `--help` 真实运行成功;官方 eval 在结果读取阶段失败(`error_code=eval_results_read_failed`,非 `compile_failed`),保守记 0。headline 11 是**保守下界**,非虚高。

### MINOR — `copy_executable_failed` 类别(Coder 13/200, Instruct 5/200)语义存疑,未定论
Coder 侧另有 13 例(6.5%)标 `copy_executable_failed`(如 `sharkdp__bat.f822bd0`: driver 生成时标 `HAS_COMPILE`,官方 eval 报 `mv: cannot stat './executable': No such file or directory`)。这**可能**是模型 compile.sh 在生成时的宽松环境(可能有网络/缓存)下"看似成功"、但在官方离线 network-blocked 干净重跑下真实失败(即 compile.sh 未满足"deterministic and offline"要求 — 公平判 0),也**可能**是 harness 侧生成时检查与正式判分环境不一致。二者未定论,与 quinn 的明确 `eval_results_read_failed` 不同类,**未独立验证**,仅供后续 harness 审计参考,不改变本次 REAL 判定。

### REPRO — 两条 headline 均可从零复现(A+B 各自独立、样本不重叠)
- A: gold cmatrix=100✅, coder cmatrix=82, instruct cmatrix=0, instruct genact=0(4 例全部精确匹配)。
- B: coder zoxide=11/531(exact 11.299435%), instruct hexyl=15/906(exact 15.342163%),executable SHA256 精确匹配 cache(2 例全部精确匹配,含 byte-identical 可执行文件复现)。
- `programbench info` 官方只读重聚合在真实 eval_out 上两次独立跑出 Average=11(Coder)/ Average=0(Instruct),200 instances,与 orchestrator.log 及独立第三条 `CAMPAIGN_finisher.log`("FINISHER COMPLETE coder_scored=200 instruct_scored=200")三方一致。

### REPRO — Denom 200 披露准确
201 源任务 − 1 disclosed fixture(`testorg__calculator.abc1234`)= 200,A+B 双独立 diff 确认唯一差集,无其他静默排除/替换(B 额外用 SHA256 确认 Coder/Instruct 两侧任务 ID 集合完全相同)。

### REPRO — Coder 部分分是真实逆向工程,非泄漏
cmatrix: gold reference 在同一测试集上 100%(506/506),Coder 提交仅 82%(约 415/506)— 若为逐字拷贝泄漏应同样接近 100%,而非有区分度的部分分。compile.sh 纯 gcc 编译自 491 行原创 C 源码,无预置二进制拷贝痕迹(A+B 独立确认,搜索 `cp/mv/install/reference/gold/binary` 均无命中)。抽查 zip(29)/zoxide(11)/chroma(3)/genact 等均显示 35-60 轮真实多轮 agent 轨迹。

---

## 已知文档滞后(需主控更新,非本次复现问题)
- `repo/REPRODUCTION_INDEX.md`:ProgramBench 仍列为"第 13 条候选...全量跑待启",未反映本次已完成的 full201 结果。本报告即为该表新增两行(13a Coder / 13b Instruct)的依据。
- `repo/manifests/bench_registry.yaml`(WIP diff, 720 处未 commit 改动 —— 本报告未触碰):programbench 条目仍标 `status: fail_closed_contract_source_present_transport_missing` / `policy: disabled_required_contract_until_runner_parser_transport`,与已完成的 full201 跑不一致,需主控核实并更新。

## 证据路径(只读,未修改任何原始 campaign 数据)
- Coder run: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/programbench_full201_coder/{orchestrator.log, subs/, eval_out/subs/}`
- Instruct run: 同上 `programbench_full201_instruct/`
- Gold sanity: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/programbench_gold/gold_cmatrix_v2/`
- CAMPAIGN_finisher.log(第三方确认源): `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/programbench_pathA/CAMPAIGN_finisher.log`
- A 的独立复现 scratch(未改动原始数据,仅新增): `/root/pb_auditB_verify/`(KVM 远端)
- B 的独立复现 scratch: `/root/codex_secondopinion_verify/`(KVM 远端)
- push: 需 GitHub PAT,审阅者(A=Claude)未持有,故仅落盘此报告,由主控 review 后 `git add` + commit + push 到对应 `evidence/programbench-*` 分支(参照现有 12 条的 evidence branch 命名/内容惯例:每条 run README.md + SHA256SUMS 于 `runs/<run_name>/`)。

Co-signed: Claude Opus/Sonnet (A, 本次审阅) + codex-pro gpt-5.6-sol reasoning=ultra (B, 独立跨族复核, 真跑非 fallback)
