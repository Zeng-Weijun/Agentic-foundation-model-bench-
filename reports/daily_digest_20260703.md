# 2026-07-03 日终战报

> **Status: HISTORICAL_NON_CANONICAL_CONFIG.** 本页是 2026-07-03 战役快照；其中未盖章模型分数及 FINAL/primary/current 语义已撤回，不得作为当前 relay-backed `gpt-5.5` + `medium` 套件入口。

## 总结

今天的主线是**基础设施代际迁移 + 三本账收敛**:用户 19:00 直令 CHARTER v6——把整套离线 bench 从退役的 rootless-vfs-tmpfs 栈全面迁移到新的 **privileged rjob KVM worker**（Pod A=TB2.1 主场，Pod B=SWE-V full500 主场），并在新栈上把 TB2.1 与 SWE-V 两本账重新对齐、放量。中途吃了一次 upstream relay 502 长事故、一个 SWE-V 离线 eval 的外网暗雷、一个 c=2 挂载竞态，都定位并绕过/修复。

**历史战役口径（下列“权威/收官”语义已于 2026-07-21 撤回，仅作取证）:**
- **Terminal-Bench 2.1**:privileged 单轮 c=2 strict **76/89**（真数，payload 修复完全生效）；c=2 `/oracle` bind-mount 竞态把 6 例压成假红（@c1 可过）→ 真 canonical **≈82/89 待 c=1 定向补跑定榜**；旧 pending-baseline 的 **query-optimize + rstan-to-pystan 在新栈直接回收**；**5 例 oracle-ran 真回归候选**待 c=1 复核。
- **SWE-bench Verified**:gold **487/500 offline-PASSED + 13 offline-induced + 0 upstream**（昨日 484→今日 +2 Pod-B 复验 +1 backfill）；离线 eval 外网依赖暗雷已修（离线 requirements/env cache）；**policy canary s008 4/4 resolved**；full500 **恢复放量中**。
- **RepoZero — RETRACTED:** 历史账本曾记录 **260/400 strict（65%）**；该未盖章结论不再是 active/current score，也不得作为“可信且更高”的对榜结论。
- **CHARTER v6 迁移**:pilot 四件套 → runbook → Pod A/B bootstrap → canary/confirm → payload 大坑+preflight 门 → full89 定榜进行时。

## 三主 bench 历史快照（非当前权威）

| bench | 今日权威口径 | 证据源 | 备注 |
|---|---:|---|---|
| Terminal-Bench 2.1 | **c=2 strict 76/89**;真 canonical **≈82/89 待 c=1** | `reports/scores/tb21_full89_poda_privileged_poda_full89_privileged_oracle_c2_r7_payloadfixed_20260703t1350z_summary.md`（total=89 clean_pass=76 resolved=76 unresolved=13 parse_error=0 infra_fail=0 timeout=0 external_network_marker=3 0token）；`_coordination/20260625_harbor_bench/reports/tb21_full89_payloadfixed_final_audit_20260704.md` | 76 是真数（逐行 `is_resolved`）；13 unresolved=7 c2 mount-race+5 回归候选+1 git-multibranch |
| SWE-bench Verified | **gold 487 offline-PASSED + 13 offline-induced + 0 upstream = 500**;policy canary **4/4** | `swe/rootless/reports/swev_gold_disk_revalidate_20260702/V5_GOLD_LEDGER.md`（=432 native+52 disk-fixed+2 Pod-B+1 backfill）+ 仓内快照 `reports/V5_GOLD_LEDGER_20260703.md`;canary `swev_s008_eval_by85_20260704/gpt-5.4-mini.s008eval_by85.json` | 昨日 gold 432→今日 offline-PASSED 487;full500 恢复放量 |
| RepoZero | **RETRACTED historical `gpt-5.4-mini` ledger claim: former strict 260/400（65%）** | [专用撤回侧车](scores/repozero_gpt54mini_full400_20260703.RETRACTED_NON_CANONICAL.md) | 未盖章且 full400 raw provenance 不完整；不得作为 current/primary RepoZero 分数 |

## relay 502 事故与恢复

- **事故**:upstream relay 持续 **502 约 5.5h**,所有真模型线（full500 rollout / TB2.1 model run）全部 parked;用户在 chat ping 检查 relay 服务。证据:`_coordination/20260625_harbor_bench/HANDOFF.md`（"Upstream 502 now ~5.5h"、"~2.5h"）。
- **恢复判据**:85 按 **3×200+choices** 自恢复判据（20% 失败容忍 fallback）验证 relay 复活;`RELAY 事故结束:dev→18540 401@0.14s`,51 用真 `chat/completions` 验 3/3 200+choices → 恢复确认后真模型线才放开。
- **教训沉淀**:relay 事故期真模型线一律 park + 单点自恢复判据（3×200），不盲目续跑污染账本。

## CHARTER v6 全面迁移 rjob（用户直令 2026-07-03 19:00）

新栈 = **privileged rjob KVM worker**（full caps + `/dev/kvm` + fuse-overlayfs + 本地 3.5T overlay），严格强于退役的 rootless jvm9z/pg89q（无 shim、无 vfs 并发上限、无 rootless teardown 病）。

| 波次/环节 | 交付 | 证据 |
|---|---|---|
| **可行性 + pilot 四件套** | Pod A（env-kvm-15238487）dockerd(fuse-overlayfs,本地 data-root)+P0 by-digest 拉取+`--network none` smoke+qemu-kvm 加速;TB2.1 oracle put_archive/teardown 证无病（Harbor `-d` 数据集离线不可达已标） | `reports/kvm_worker_bench_pilot_20260703.md`、`reports/pjlab_harbor_rjob_feasibility_20260703.md` |
| **runbook** | 退役→新栈迁移手册(pod 清单、data-root 铁律、CA/insecure-registry、P0 preheat 硬超集) | `_coordination/20260625_harbor_bench/MIGRATION_RUNBOOK_RJOB_20260703.md` |
| **W1 Pod B bootstrap（前置门）** | env-kvm-57740737 dockerd(fuse-overlayfs `/docker-data-57740737`)+P0 by-digest+`--network none` smoke+relay 401,4 件套全绿 | `_coordination/20260625_harbor_bench/POD_B_BOOTSTRAP_20260703.md` |
| **W2 full500 cutover→Pod B** | 51 造 cutover 机械件 + canary chunk + s002 回滚验证 PASS;s008 canary→full resume | `swev_full500_model_20260702_podb_canary_*/`、`surface51_podb_*` |
| **W3 Pod A=TB2.1 主场** | 86 canary→full89 payloadfixed oracle rerun（c=2, r7）→终核定榜进行时 | `tb21_full89_..._c2_r7_payloadfixed_*` |
| **payload 大坑 + preflight 门** | c=2 早期 3 parse_error（bn-fit-modify/mteb-leaderboard/circuit-fibsqrt）疑 payload 缺口 → payload 修复后 r7 **parse_error=0** 完全生效;preflight 门（preheat present=89/missing=0）进 DoD | 同上 summary（parse_error=0） |

RepoZero 已收官**不迁**;55 preheat 目标 pg89q→Pod A。

## Terminal-Bench 2.1 账目演进（80→79→c2 76→真值≈82）

- **80 → 79**:昨日 tick 曾报 80/89 = off-by-one 错;r5_final JSON 权威 **total 89 / resolved 79**（旧 rl-vfs 复合 map，89 行 EVIDENCE_MISSING=0）。证据:`reports/scores/tb21_full89_oracle_infra_map_r5_final_20260703.json`。
- **c=2 76**:新栈 privileged 单轮干净 strict **76/89**（真数,逐行 `is_resolved`;parse_error/infra_fail/timeout 全 0,~44min）。
- **c=2 mount-race → 真值≈82**:86 终核根因=c=2 `/oracle` bind-mount 竞态（`bash: /oracle/solution.sh: No such file`,oracle 没跑）把 **7 例** 压成假红（其中 6 例 @c1 已证能过;make-doom-for-mips 竞态下另压真 MIPS 问题）→ 真 canonical **≈82/89 待 c=1 定向补跑定榜**。证据:`_coordination/.../tb21_full89_payloadfixed_final_audit_20260704.md`。
- **query/rstan 意外回收**:旧 `pending_baseline_online_oracle_comparison` 的 `query-optimize` + `rstan-to-pystan` 在 privileged 栈**直接 RESOLVE**（我另做的官方在线 oracle 判决也确认双双 offline-induced,reward=1.0;vendor-bake 可能免了）。证据:`_coordination/.../reports/tb21_pending2_baseline_verdict_20260703.md`。
- **5 回归候选（oracle-ran 真败,旧绿新红,须 c=1 复核）**:`compile-compcert`（ran 212s,compcert_valid 败）、`install-windows-3.11`（ran 66s,win-311-core-files 败）、`feal-differential-cryptanalysis`（attack test 败）、`configure-git-webserver`（hello_html 败,no output）、`headless-terminal`。
- **净迁移效应 vs 旧栈**:+8 回收 / −5 回归候选（未证）/ 2 持久。真 canonical 定榜等 55 的 c=1 定向补跑 13 任务 + runner c=2 mount-race 修复（fail-closed 挂载验证 + 单测）。**TB2.1 线全程 0 token。**

## SWE-bench Verified（gold 484→487 + 13、暗雷修复、canary 4/4、full500 放量）

- **gold 账本 484→487**:昨日 offline-PASSED 484（432 native + 52 disk-fixed);今日 Pod-B privileged 复验 16 例 offline-induced,**2 回收**（`psf__requests-2931`+`5414`）→ 486;pip-mirror bake backfill **+1**（`pylint-dev__pylint-4661`,appdirs 从内网镜像装通）→ **487**。剩余 **13 offline-induced**(8 网络类需本地 httpbin/linkcheck mock=vendor 类 HELD + 5 环境类)、**0 upstream**。证据:`V5_GOLD_LEDGER.md` + `reports/{swev_gold16_podb_revalidate,swev_gold13_backfill_fix_spec,swev_gold_offline_induced_16_audit_backfill}_20260703.md`。
- **外网依赖暗雷修复**:51 Pod B canary 抓到 swebench eval 的 `requests.get(MAP_REPO_TO_REQS_PATHS / MAP_REPO_TO_ENV_YML_PATHS)` 外网依赖（raw.githubusercontent)——离线 pod 上 eval 必炸。修法=dev 预取全 500 实例 requirements/env yml 建离线 cache（`swe/bench/swe-bench-verified/offline_eval_req_env_cache_20260703`）+ harness offline patch（additive/可回退,`swev_offline_eval_cache_patch.py`,经 `eval_wrap.py` 继承）。证据:`swev_full500_monitor_surface51_20260703.md`。
- **policy canary s008 4/4（85 顶班）**:51 撞 Codex 同池限额,85 顶班对 s008 的 4 正常 pred + django-11138 no-patch 过官方 eval:**resolved 4/4**(django-11095/11099/11119/11133)、django-11138 empty_patch(合法模型失败,20 调用 19 正常返回无 5xx)、**rc 0 / 外网痕迹 0 命中 / 无 STOP** → RESUME-CLEARED。证据:`swev_s008_eval_by85_20260704/{eval.log,gpt-5.4-mini.s008eval_by85.json}`。
- **full500 恢复放量**:00:54 限额解除后 51 full resume（Pod B 稳态并发,30min 报账,挂 tmux `swev_podb_full_resume_20260703T171014Z`）;账本实证移动 **done_chunks 8→9 / rows 32→36 / resolved 20→23 / STOP=F / s009 active**,~470 任务待跑（gpt-5.4-mini,通宵)。证据:`swev_full500_model_20260702_podb_canary_*/full500_results.jsonl` + monitor 报告。

## RepoZero 历史账本记录（RETRACTED；原 260/400 结论非当前分数）

- 历史账本曾记录 `gpt-5.4-mini` strict **260/400（65%）**；其 active/final publication status 已撤回，且没有可核实的 sealed full400 raw/merge provenance。
- **当前裁决:** 原“内部 65% 高于官方范围且可信”的主动结论已撤回；模型、scaffold、协议与证据合同均不足以支撑 current/primary 对榜。参见[专用撤回侧车](scores/repozero_gpt54mini_full400_20260703.RETRACTED_NON_CANONICAL.md)。

## handoff_docs 交付（两份外部使用说明)

用户要交外部 harness 团队,全路径实测:
- `handoff_docs/SWEV_OFFLINE_DOCKER_USAGE_20260703.md`
- `handoff_docs/TB21_OFFLINE_DOCKER_USAGE_20260703.md`
（数据集 canonical 已同步修正为 `terminal-bench-2.1-yaml-full89-r7-final-20260703`,r6video 及无后缀版过时。)

## 经验教训表

| 教训 | 今日踩点 | 沉淀规则 |
|---|---|---|
| **payload preflight** | c=2 早期 3 parse_error（payload 缺口）；payload 修复后 r7 parse_error=0 | 每轮 full89 前 preheat present=89/missing=0 + payload 完整性进 DoD;parse_error!=0 一律先修 payload 再定榜 |
| **多 checkout 分叉** | monitor 报告 committed 到 origin 但未同步 live local 工作副本 → 盘上看似缺失;dev/swe_dev2 跨 checkout 并写 `manifests/bench_registry.yaml` → rebase 撞车 | 交付物必须落到"人/agent 实际读的那份盘上"并附 ls 证据;跨 checkout 同文件并写=分叉源,pull --rebase 前查重叠,撞则 abort 不硬合 |
| **Direct-Notify 验收** | 86 的 c=1 工单发错 surface（96481vm4 而非 surface:55）→ 55 pane 无输入 | Direct-Notify 后必须 read-screen 验证对方开工,目标一律 `surface:N` |
| **Codex 同池限额** | 51 与 55 同池 Codex 限额,双双 00:54 恢复,阻塞 full resume + c=1 补跑 | 同池 Codex 限额会同时打掉多 lane;限额期用非 Codex agent 顶关键门（如 85 顶 policy canary eval,只吃 docker 0 token）|
| **heredoc 引号** | 无引号 heredoc 里 python f-string 的反引号被 bash 命令替换,MD 行被 mangle | 复杂 python/文本进 heredoc 用 `<<'EOF'`（quoted）或写文件 scp,禁无引号 heredoc 带反引号/`$` |
| **turn 交付纪律** | 85 第一次顶班未落地即回 standby | turn 结束二选一:交付物已落盘（附 ls 证据）或 BLOCKED+具体卡点,不许静默放下 |
