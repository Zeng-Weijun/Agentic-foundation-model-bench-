# BENCH_STATUS — 唯一进度看板(每 tick 更新,漂移即可见)

Updated: 2026-07-04 06:10 lead=Claude (by-85 sync) | 章程: CHARTER + v2-v6 DELTA | DoD 四项缺一不算完成

| # | Bench | ①oracle/gold 全量 | ②真模型 full(标准 scaffold) | ③P0 传输证据 | ④one-click 重跑 | 下一步 |
|---|---|---|---|---|---|---|
| 1 | TB2.1 (89) | ✅ ★CANONICAL 84/89★(privileged oracle,mount-corrected,86 全链核证);残余 5=3 privileged 回归 root-caused(feal+compcert /tests-rw 已证 reward0→1,git-webserver master/main;修完冲 87)+2 双栈持久 | 🔄 full89 c=89 xhigh 收官中(round-1 fd事故作废→ulimit65535 重发全绿 89/89,fd 2.0%,xhigh live,待 86 终核出分) | ✅ | ✅ | 86 终核 full89 出分;3 回归修复应用待 55 Pod A 清场(spec=tb21_regression_fix_poda_by85_20260704.md) |
| 2 | SWE-V (500) | 🔶 gold 487+13+0 | ⛔ 旧 GPT relay model-run 分数和 live 计数已移除；外网依赖修复保留 | ✅ | 🔶 | 等新的正式封样运行 |
| 3 | RepoZero (400) | ⛔ 旧 GPT relay aggregate 已移除；无当前本地 GPT 分数 | ⛔ 不发布旧模型分 | 🔶 P0+fallback 齐 | 🔶 | 官方协议复现缺口照旧保留；等新的正式封样运行 |
| 4 | tau3 | 🔄 51 建设启动(worktree tau3-enable:快照脚本/registry 行/runner 骨架/parser) | ⬜ | ⬜ | ⬜ | enable 契约实现 |
| 5 | DeepSWE | 🔶 可行性报告落地 16:12(14KB 待审) | ⬜ | ⬜ | ⬜ | 审→enable 契约 |
| 6 | SWE-Multilingual | 🔶 可行性报告落地 17:29(15.6KB 待审) | ⬜ | ⬜ | ⬜ | 审→enable 契约 |
| 7 | NL2Repo | 🔶 可行性报告落地 17:44(18KB 待审) | ⬜ | ⬜ | ⬜ | 审→enable 契约 |
| 8 | ProgramBench | 🔄 拍板=建(数据公开 200task);51 建设启动 | ⬜ | ⬜ | ⬜ | enable 五件套 |
| 9 | MCP-Atlas | 🔶 拍板=先 local/replay smoke 契约,缓 full(judge LLM+公网 MCP 服务需 replay 层) | ⬜ | ⬜ | ⬜ | smoke 契约排队 |
| 10 | Monthly(快照制) | ⬜ 单月快照契约 | ⬜ | ⬜ | ⬜ | 降级建 |
| 11 | Tool-Decathlon | ⬜ 调研后定,允许弃 | — | — | — | 调研 |

## Infra 一级任务
| 任务 | 状态 | 备注 |
|---|---|---|
| 并发攻坚(用户直令:找最高稳定 c) | ✅ 完成: overlay2 c=4→128 全稳 0 失败(RAM 峰 59%@128),max stable ≥128,推荐运行点 c≈48-60(CPU 核限);vfs c=2→64×;gotcha:健康检必须 docker ps 非 docker version;报告 reports/jvm9z_overlay2_stress_20260702.md | jvm9z kernel 5.15→原生 overlay2;无 /dev/fuse;根源 vfs-on-tmpfs RAM 爆;86 证明链后起第二 dockerd 压测 c=4/8/12/16 |
| dev relay 契约 | ✅ 修复: 18540 进程死+IP 陈旧双根因; 正确 base_url=http://100.96.122.22:18540/v1(dev tmux bench_relay_18540,upstream 8.130.49.170); jvm9z 实测 401@0.12s 可达; 100.96.1.101 作废 |
| one-click bootstrap 脚本 | 🔶 真机试跑 pg89q 通过(I1-I7 问题清单待修:smoke 不真测/pull 无重试/CA 写复用栈 data-root 等 LOW) | shim+CA+P0 预拉+preflight ≤30min |
| registry GC/retention | ⬜ | 缓,量大后做 |

## 图例与红线
🔄 进行中 🔶 部分/待刷新 ⬜ 未开始 ✅ 完成(须证据路径)
红线:oracle 89/89 前不开新 full89;canary 先于 full;真模型 run 自主但每 tick 报账;cache 命中≠P0 pull;不打印 key。
每 tick 必做:更新本表 + HANDOFF 顶块;任何范围/口径变更必须在本表 Delta 段显式记录,禁止静默改。

## Delta log
- 2026-07-02: 看板建立(章程 v2 后初始快照)。
- 2026-07-02 14:05: SWE-V transport ✅(F5 gotcha 记录);hunt round-2 系统性发现:7 个 unresolved 同根因=Docker teardown 不稳定(video-processing/train-fasttext/sam-cell-seg/reshard-c4-data/pytorch-model-recovery/schemelike-metacircular-eval/make-doom-for-mips)→wave5 先重跑再定性,overlay2 可能根治;51 fix_plan phantom-green 已对质重派;真模型累计 0 case;batch23 in flight。

- 2026-07-02 14:20: TB2.1 run#1 完成(62/89, write-compressor 收官;batch23 因单 task 并发降 1 → run-id 后缀 c1,glob 教训已记);r3 契约 review PASS(headless-terminal/install-windows-3.11 需 wave4/wave1 资产协同);fix_plan 39KB 批准;pg89q 被 runner 重置为空(images=0)等 preheat;85→RepoZero strict 审计,51→canary 契约+relay 健康检+summarize glob 核对;真模型累计 0 case。

- 2026-07-02 14:35: 55 起 bake r3 wave1+2(后台)+ 修 summarize oracle_c1 glob(51 给了 patch 设计);85 交叉审 canary 契约+bootstrap;51 转 tau3 调研;86 压测超预期(c=4/8/12/16 全过,扩展阶梯 24-64 进行中);RepoZero 旧 GPT score audit 数字已于 2026-07-21 移除;relay 1-token 健康检通过。

- 2026-07-02 14:50: 并发攻坚✅(≥128 稳,推荐 48-60);86→铺 pg89q overlay2 栈;85→执行首次真模型 canary(SWE-V 2 case,mini-swe-agent+gpt-5.4-mini xhigh,jvm9z rl-ov2);51 tau3 报告二次缺失,已对质+要求 ls 存在性证据;bake r3 进程状态待 55 报告(log 只有 profile 噪声);正式汇总落 reports/scores/(missing=[]);round-4 双 PASS。

- 2026-07-02 15:40: 本地 DNS 抖动 ~10min 自愈;期间发现 canary 阻塞根因=relay 18540 进程死+base_url IP 陈旧(100.96.1.101→100.96.122.22),已重启(dev tmux bench_relay_18540)并从 jvm9z 验证可达,85 已放行开跑 canary;86 双 worker overlay2-ready 后跑 pg89q parity 阶梯;55 bake r3 重启为 PID 491906(TB21_ARTIFACT_ROOT 修正);51 tau3 三次督办中(新规:交付必附 ls 输出)。

- 2026-07-02 16:05: 勘误——tau3 报告实际 14:29 已交付,第二次 phantom-green 指控系我方 find 语法坑误判,已向 51 撤回(fix_plan 第一次缺失仍属实,ls 规则保留);bake r3 失败(smoke 命令引号 bug 或镜像缺修复,PID 死),55 修复重启中;86 parity 完成→bootstrap 真机试跑 pg89q;85 canary 真跑中(gold 契约 10.7KB 已先落);核验手法教训:目标路径直接 ls 不用 find -newermt,P0 catalog 查询必须 n=1000(500 分页截断)。

- 2026-07-02 16:25: 85/86(两 Claude lane)撞 session limit,16:30 重置后续跑 canary 与 bootstrap 试跑;canary 报告 14:35 版是 relay 修复前的 BLOCKED 记录(0 token,红线合规),修复后真跑被限流打断;bake r3 第二次失败=真 build 错误(wave2 cv2 镜像 apt/pip RUN 步骤 exit 1,55 修模板级根因);51 交付 DeepSWE 报告→转 SWE-Multilingual 调研;真模型累计消耗仍=1 探针。

- 2026-07-02 17:30: 限流重置后 85 继续 canary(Working);bake r3 第三次启动 ALIVE(skip_existing=1 断点续烤,日志 091612Z);86 bootstrap 真机试跑 PASS-with-issues(报告 7.2KB)→转 RepoZero 限流 rerun 试点(8 case,c≤4,pg89q rl-ov2,strict 四条对照);51 SWE-Multilingual 调研中;真模型消耗:1 探针+canary in flight+即将 RepoZero 8 case。

- 2026-07-02 17:45: 85 canary 修复两 blocker 后台重跑中(完成后自收报告);51 交付 SWE-Multilingual 报告→转 NL2Repo 调研;55 bake 后台继续(尚无 push 记录,烤第一批中)→并行修 bootstrap I1-I7;86 在挖 RepoZero 旧 run 输出目录选 rerun case。可行性报告库存:tau3/DeepSWE/SWE-Multilingual 三份待主 agent 审。

- 2026-07-02 18:00: ★bake r3 push 10/10 完成(进程收尾存 tar)★;55→校验产物+生成 targeted rerun 计划(分片A=wave1/2 12task 用 rl-vfs 保可比,分片B=wave5 7task 建议 overlay2);86 RepoZero 8-case rerun 真跑中(c=4,~80min,waiter);85 canary 后台中;51 NL2Repo 落地→ProgramBench 调研;可行性报告库存 4 份待审。

- 2026-07-02 18:20: ★用户解除消耗约束:中转站无限额度,并发 100+ 可用★;dev proxy=ThreadingHTTPServer 已验证无结构瓶颈;红线修订:RepoZero 全量 rerun 试点确认后可 c=50-100;SWE-V full500 真模型 run 在 canary+gold 门后直接排;canary先行门与每 tick 报账保留。

- 2026-07-02 18:40: 旧 SWE-V/RepoZero GPT canary 与 rerun 结果数字已于 2026-07-21 移除；TB2.1 targeted rerun、ProgramBench/MCP-Atlas 调研和基础设施放行事件照旧保留。

- 2026-07-02 19:15: ⚠️TB2.1 targeted rerun 首轮 19/19 unknown_agent_error——wrapper agent 调用层 bug(每 task ~30s agent 未启动,连 run#1 resolved 的 3 task 同挂,证明与 r3 镜像无关),55 诊断修复后先单 task 验证再放 18;full500 真模型已开跑 c=10 档(85,gold 并行);86 在部署修正版 c=25 RepoZero runner(自愈重试);51 调研线收官→tau3 建设启动;MCP-Atlas 报告 25KB 落地。

- 2026-07-02 19:30: ★pg89q tmpfs 90%(349/391G,rl-vfs vfs 全拷贝)= 真瓶颈(RAM 仅 12G)★;RepoZero 旧 GPT checkpoint 数字已移除；串行化与 tmpfs 控峰值决策、full500 并发监控和 tau3 建设事件保留。教训:vfs 栈与任何并行负载共存前先看 tmpfs 不是 RAM。

- 2026-07-02 20:05: TB2.1 62→69/89,第二轮 rerun 7 翻绿(gcc/toolchain/GitPython/rebake 修复生效);剩 20=B 分片 7(wrapper 修复后待真跑)+A 分片 6 unset(真实测试失败待归因)+wave3/4 共 8(vendor 化+gold 修复未开工);tmpfs 84% 稳(回收补丁 live);tau3 骨架五件套核验通过;51 转 DeepSWE 建设;85 full500 s000 resume;86 等 DNS 自愈续 RepoZero。

- 2026-07-02 20:20: full500 并发调度、DeepSWE/SWE-Multilingual 建设和 DNS 诊断事件保留；RepoZero 旧 GPT 进度数字已移除。

- 2026-07-02 20:35: pg89q 空间战争决策——rl-vfs 镜像清空释放 ~300G(A 分片使命完成,同栈可比性已验证;runner 自身有重置先例),B 分片/RepoZero/终验全走 rl-ov2;55 执行清理+B 重跑+A 归因;86 RepoZero ~25 codex 在跑(poll 命令 flake 但 runner 活);51 SWE-Multilingual 骨架交付待核验。

- 2026-07-02 20:55: tmpfs 8%(rl-vfs 清空生效,362G 可用);89 全图 scoreboard 落地(69/89 确认+防造数标注);B 分片空间清理后仍 compose startup 失败→新根因假设 rl-ov2 缺 compose v2 插件,55 诊断中;剩余分类:image_dep_incomplete 4/oracle 深层缺陷 1/compose 阻塞 7/wave3+4 未跑 11;51 NL2Repo 骨架交付(四 worktree 齐)→尾部 bench 决策单+Monthly 契约;85 gold 收尾在即;86 RepoZero 跑等 final strict。

- 2026-07-02 21:10: 尾部拍板:ProgramBench 建(51 启动 enable)/MCP-Atlas 先 smoke 契约缓 full/Monthly 维持降级;55 compose 修通等 video-processing 语义结果;85 自修 full500 路径上 matplotlib/xarray 镜像;86 等 RepoZero waiter。

- 2026-07-02 21:45: video-processing 在 overlay2 上翻绿(compose 插件修复生效)→55 放剩余 6 个 B task+紧接 wave3/4+A 残余(TB2.1 全绿最后一波);85 收 full500 s001 报告;86 自主决定 RepoZero 保持 c=25;51 ProgramBench 骨架交付→MCP-Atlas smoke 契约(建设线收官单)。

- 2026-07-02 22:00: ★gold 全验 432/500★(matplotlib/xarray 坏镜像路径的 68 待修后补);建设线六件全交付(tau3/DeepSWE/SWE-Multilingual/NL2Repo/ProgramBench/MCP-Atlas smoke)→86 cross-family 审六 worktree(waiter 并行),51 执行 tau3 真快照(第一个新 bench 推向可用);55 B 队列跑中;86 RepoZero c=25 waiter。

- 2026-07-02 22:15: ★章程 v4:TB2.1 口径改 infra-clean★(官方 gold bug 不修改归档;wave4 取消;wave3+A 镜像残余仍修);六 worktree 全 PASS(N1-N3 非阻塞);tau3 数据集真实落地(6543 文件+SHA256SUMS);51→修 N1-N3+DeepSWE 真快照;85 续 full500 recovery。

- 2026-07-02 22:35: ★85 context 97%→令写 SWEV_LANE_HANDOFF 自包含交接(gold 432/500+full500 recovery 状态),写完停手,下 tick 清+重派或转 86★;DeepSWE 数据集落地(deepswe-v1.1)→51 转 SWE-Multilingual 快照(资产落盘 3/6);55 B 队列跑中盯 tmpfs;86 waiter。

- 2026-07-02 22:55: ★85 换血完成★(handoff 10.9KB/7 节→/clear→fresh agent 读 handoff 接管 SWE-V lane,首任务=验证 full500 s000 eval 修复);快照落盘 3/6(tau3/DeepSWE/SWE-Multilingual)→51 转 NL2Repo;55 B 队列 50min 长跑中;86 查 RepoZero 进度 x/242。

- 2026-07-02 23:10: 快照 4/6(NL2Repo 落地)→51 转 ProgramBench(>10G 门);85 fresh agent 接手校准后已动(s000 验证);55 B 队列剩 make-doom 自然收口(克制不抢资源);86 RepoZero 自动监控挂好(tmpfs 90 暂停/85 续)+check 报数中。

- 2026-07-02 23:50: TB2.1、r4 契约、ProgramBench/MCP-Atlas 和 gold 补验事件保留；SWE-V/RepoZero 旧 GPT model-run 进度数字已移除。

- 2026-07-03 00:35: ★快照线 6/6 收官(MCP-Atlas 落地)+merge plan 出(待主 agent 审)★;gold、bake r4 和日终战报事件保留；SWE-V/RepoZero 旧 GPT model-run 进度数字已移除。

- 2026-07-03 00:50: ★merge plan 主 agent 审毕=批准★(fail-closed 骨架 only/不启 suite 行/registry 手工合并/N1-N3 闭);51 撞 session limit 23:51 重置→重置后执行:日终战报+merge(commit 后同轮 push);85/86 待命自提示;55 bake r4 长跑 46min。

- 2026-07-03 01:30: ★章程 v5:bug-for-bug 兼容,全 bench 通用★——官方 bug 不修只归档(修=与官方对不齐);85 令甄别 matplotlib/xarray 68 个:offline-induced 修/upstream-native 归档,已做修复回顾分类,偏离语义的回滚;gold 账目改三段式 x+y+z=500。

- 2026-07-03 02:00: ★六 bench enable 层 MERGED+PUSHED(origin/main=f54153c,6 commit:tau3/DeepSWE/SWE-Multilingual/NL2Repo/ProgramBench/MCP-Atlas smoke)★+日终战报落地(repo/reports/daily_digest_20260702.md);51 同步本地 checkout 后待命;85 v5 甄别大跑(41.9k tokens);55 bake r4 近 2h;86 RepoZero waiter。

- 2026-07-03 02:45: RepoZero 旧 GPT “收官”数字已于 2026-07-21 从当前发布面移除；其余当日基础设施事件保留。

- 2026-07-03 03:40: ★归档审计 5/5 CHALLENGE——84+5 图作废,目标上修★:headless-terminal(打包丢官方 solution/,86 修验中)/chess-best-move(我方 repair 脚本 artifact)/install-windows-3.11(我方 staging)已证我方 bug 转修复;rstan+query-optimize unproven 交 85 baseline-online 官方对照;bake r4 push 11/11 完成(收尾 tar);TB2.1 infra-clean 新目标≈87-89/89(视对照结果)。审计机制价值实证:防止把我方 bug 甩锅官方。

- 2026-07-03 05:00: ★TB2.1 ≈78/89★(62 基线+7 二轮+3 三修验 PASS+6 r4 targeted);55 最后冲刺包(B6 盘点补跑+r5 五修复+fail-closed 传播 bug+89 精确终图);85 resume full500+rstan/query 对照判词;relay outage 已恢复;三修验证据:headless/chess/install 各 resolved 1/1 附 digest+tar sha。

- 2026-07-03 08:00: ★TB2.1 终图 r5=76/89(修正后真实 79/89:三修验 3 个漏并)★;r5 战果:fix-ocaml/multi-source/pytorch-model-cli/qemu 翻绿;B7 卡 rlvfs teardown→已令转 rl-ov2 栈重跑(正解,压测已证);git-multibranch 剩 HTTPS 端点空一层;rstan/query 等 baseline 判词;上游 502 ~2.5h(85 按连续 3×200 自主 resume);oracle 线零 token。

- 2026-07-03 08:30: ★B7 on overlay2 仍全 unknown_agent_error——storage driver 排除★;新假设=重型镜像容器就绪慢于 harness agent 注入窗口(7 个全是视频/训练/大数据型);55 定向诊断 video-processing(注入时序对比+手动计时+timeout multiplier 2.0 验证);TB2.1 现 79/89+B7(注入窗口疑)+git 1+baseline 2。

- 2026-07-03 09:15: ★B7 根因破案:compose up exit 1=镜像不存在★(rl-vfs 清空删 r2 全镜像→preheat 只补 r4 的 11 个→B7 镜像无处存在→三轮重跑全在无镜像下跑);解法=P0 拉回 B7 七镜像+retag+重跑(55 执行);教训:清 docker 数据后 preheat 清单必须覆盖后续所有 rerun 的镜像。TB2.1 预期 B7 修复后冲 86/89。

- 2026-07-03 09:40: B7 镜像层修通(compose up/oracle 注入/solution 全过)→最后一层=put_archive 大 payload 打断 rootless API(RemoteDisconnected,F5 同族,jvm9z 同复现);解法=bind-mount tests 目录绕开大传输(55 执行:compose volume+harness 已存在检测小 patch,记录偏离);打穿即 86/89。

- 2026-07-03 10:55: ★video-processing resolved=True——B7 第一绿★(镜像恢复+bind-mount 绕 put_archive+symlink hardlink 三层修复全通);TB2.1=80/89,B7 剩 6 铺开中(train-fasttext 已进完整判定域);上游 502 已 ~5.5h 待用户查中转站。

- 2026-07-03 13:10: ★TB2.1=85/89★ B6 rerun 全完:train-fasttext/sam-cell-seg(补跑)/pytorch-model-recovery/schemelike/make-doom-for-mips 全绿,B7 总战果 6/7;剩 4=reshard-c4-data(真实第一因待修)+git-multibranch(HTTPS 端点)+rstan/query(baseline 判词);55 收尾三件→终图 v2 预期 87/89。

- 2026-07-03 14:05: ★TB2.1=86/89(git-multibranch r7 翻绿)★;剩 3=reshard-c4-data(r7 后仍 False 最后一层)+rstan/query(baseline 判词);85 context 97% 换血中(handoff v2→clear→re-brief);86 消融后台;上游 502 仍持续。

- 2026-07-03 14:35: ★★TB2.1 终图 v2=87/89, infra_unresolved=0——oracle 线 infra-clean 达成★★(reshard r7 uvfix 绿+git r7 绿+B7 全绿);剩 2=query-optimize/rstan pending baseline verdict;55 排干净 full89 oracle 终验(单次 run 复现 87,DoD① 存档证据);下一步=真模型 full89(等上游稳)。
- 2026-07-03 17:40: 新主 agent 接管；relay 恢复、gold/TB2.1/enable/迁移事件保留；SWE-V 与 RepoZero 的旧 GPT model-run 数字已于 2026-07-21 移除。
- 2026-07-03 18:10: TB2.1 账目修正 80→79/89(r5_final 核验,evidence 全齐);迁移 runbook 落地(Pod A 就绪/Pod B 待 bootstrap);lead 批准 Phase0 canary=8 docker-EOF 任务上 Pod A 重跑(TB2.1 收口+迁移金丝雀双重目的);gold-16 审计+scores commit/push 派 85。
- 2026-07-03 19:05: ★CHARTER v6:用户直令全面迁移 rjob KVM worker★ W1=Pod B bootstrap(85) W2=full500 cutover(51) W3=Pod A TB2.1 主场(86/55);jvm9z/pg89q 只留回滚现场不铺新；旧 GPT s002 账本数字已移除；85 三 commit 已上 origin。
- 2026-07-03 19:30: canary 判决=EOF 病根消灭(6/6);0-resolve 归因 smoke bootstrap=0 vs RO /tests;数据集 canonical 修正为 r7-final;55 接确认重跑(batched+privileged 适配),86 物化 2 缺镜像;handoff_docs 使用说明×2 交付用户。
- 2026-07-03 20:30: confirm 6/8(EOF/RO 清零,skip-copy 为决定性修复);TB2.1 期望 85/89;51 发现 swebench eval 外网依赖(offline cache 修复中,full resume 门前);55 发射 full89 clean oracle on Pod A;86 终核 confirm run。
- 2026-07-03 21:55: full89 首发无效砍除(payload 7/89 staged,82 必 parse_error);prep 补全+fail-closed payload preflight 门+re-sweep GO 流水线;教训=pre-staged 资产必须 launch 前完整性验证。
- 2026-07-03 23:50: gold 484→486(Pod B 复验 2 flip);14 例 backfill 启动;django-11138 单实例诊断中(full resume 门);full89 payloadfixed 长跑中。
- 2026-07-04 00:25: full89 payloadfixed strict 76/89 出数(0 parse/0 infra);86 三本账终核启动;gold 487+13(hold network-8 重投入);DoD④ one-click 在 rjob 全链实证。
- 2026-07-04 01:05: 终核=76 不定榜(c=2 mount 竞态压低,真值≈82);query-optimize/rstan 意外回收;5 回归候选待 c=1;批准 c=1 补跑 13 + runner 竞态修复;full500 resume 门授权(policy canary 过即放)。
- 2026-07-04 01:15: full500 恢复放量实证(账本移动,STOP=F);policy canary 全绿(85 顶班);c=1 补跑准备中。
- 2026-07-04 03:30: ★TB2.1 定榜 84/89 CANONICAL★(+8 c=1 回收,残余 5 真实);3 回归 documented 不阻塞;真模型 full89 发射准备；旧 SWE-V GPT partial 数字已移除。
- 2026-07-04 03:43: TB2.1 3 回归 root-caused(85):feal+compcert=/tests read_only:true 阻塞测试期写(C扩展build/ld probe),修=read_only:false,直连harbor判分序列证 reward0→1;git-webserver=git 默认分支 master→main 回归(客户端push master,新镜像bare HEAD=main未出生,hook checkout空→404)。report=tb21_regression_fix_poda_by85_20260704.md。
- 2026-07-04 04:08: ⚠️事故+教训——relay 18540 误杀(lead 误判故障重启,已恢复,如实入账)。假死根因:dev 非交互 shell 探测 relay 经代理。★教训:localhost/relay 健康探测必须 --noproxy(或 NO_PROXY),否则代理拦截→假死→误杀★。
- 2026-07-04 04:42: ⚠️事故+教训——full89 c=89 round-1 INVALID-INFRA(fd-exhaustion:launcher shell soft ulimit=1024→[Errno 24] Too many open files,仅 37/89 容器起)作废。★教训:真模型 launcher 进程必设 ulimit -n 65535★。
- 2026-07-04 05:20: full89 c=89 ulimit65535 重发(terminus2_full89_gpt54mini_xhigh_c89_ulimit65535_r7_20260703t205031z)t+27min ALL GREEN:89/89 容器、fd 2.0%/65535、infra/docker/relay 错误 0、xhigh live everywhere(reasoning_tokens>0 max 7850)——待 86 终核出分。
- 2026-07-04 06:00: RepoZero 官方协议 run PAUSED@Gate4；旧 GPT aggregate 不再维持为主数。不可识别 mini fork 与 scaffold 复现缺口照旧归档，见协议 spec。
