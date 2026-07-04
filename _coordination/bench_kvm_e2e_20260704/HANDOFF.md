# bench KVM 端到端离线复现 — LIVE HANDOFF

> 主 agent = surface:84。最后更新：tick-30 (~23:35)，**用户重大转向**。通信协议：>6 行结论写 `DECISIONS.md`；派活必须验证「输入框清空 + Working」。

## 用户转向指令（2026-07-04 23:30，最高优先）

1. **停 full500**（shard 式旧 runner 淘汰）。
2. **V2 runner**：无 shard、全局队列、**每实例 run→eval 串联不解耦**、**c=100**、幂等账本、断点续跑、模型 env 外置。
3. 整理 **SWE-V + TB2.1 端到端复现 yaml/sh 命令包**（交付物）。
4. 查 **官方榜 × 中转站模型** 对照（SWE-V / TB2.1 / RepoZero），选模型+harness 按官方口径 100 并发复现。
5. 其他 bench 继续推进；RepoZero 已有 runner（tools_repozero_codex_full.py + strict 4-criteria + packyapi provider，历史 pilot c=4 修复过 relay 过载），等对照表后定复现方案。

## 三条线状态

### ✅ tau3 — 双签关闭（spec-closed/execution-blocked）
全链+Pod A 断网证明 PASS 4/4 + 55 复核 PASS（独立重跑 airline-0 复现）。commits 0c69e60/9be6e20/623eeab。

### 🔻 full500 — 停止中（用户令）
- 51 执行优雅停止：STOP 机制、在跑实例收尾、不开新 shard、账本冻结终局快照 → DECISIONS。
- 已有 ~225 行成绩保留（86 审计+55 抽核双签：数值真实）。**86 的收官四查改为停止点快照审计，等 GO**。
- 收官三要求（去重/后缀收编/snapshot 冻结）仍适用于停止点账本。

### 🔄 TB2.1 — 金丝雀进行中
55 在 Pod A 重跑 8 个 docker-EOF 任务（oracle，c≤4），85 审查位。79/89 → 预期 ~87/89。

## Surface → 角色（tick-30 起）

| Surface | 模型 | 任务 | 状态 |
|---|---|---|---|
| 84 | Claude 本会话 | 主编排 | 600s tick |
| 51 | codex | ①优雅停 full500（tick-31：WAIT_TICK 等在跑实例收尾中）②V2 runner 设计（待 84 批） | Working |
| 55 | codex | TB2.1 金丝雀执行 @ Pod A（用 batched_privileged 版 runner） | Working 15m+ |
| 85 | claude(ctx 满) | tau3 closure 双签已记（含 3adbfe3 push）；E2E 命令包已写完，批准后 push repo（含 key 自查） | Working |
| 86 | claude | 官方榜×中转站对照：3 个子 agent 并行查（swebench/tbench/repozero+relay 模型），等合成 | Working |

## V2 runner 需求（拍板依据，51 设计中）

无 shard 全局队列 / 每实例 pipeline：镜像就位→agent run→**立即 eval**→原子账本一行 / c=100（relay retry+退避）/ instance_id 幂等+canonical 唯一目录 / 断点=账本已完成集合 / 模型参数 env 外置 / 新文件不覆盖旧 orchestrator。

## 输入框草稿定性

4 条"神秘草稿"（收编s002 / GO四查 / 55exec时ping85审查 / 就位等agent）风格一致，**定性为用户本人在 pane 手打未回车**。处理原则：与当前安排一致的直接提交生效；涉及改账目/越门槛的先审计确认再执行。

## 红线

- 55 金丝雀不碰 Pod B；不改 canonical map。
- full500 停止=优雅收尾，不删数据；停止点账本仍走审计口径。
- key 不落文件不上屏；pod 不打公网；不 /clear。
- 100 并发首跑=对 relay 的压测，观察超时率再定型。

## 下一 tick

- 确认 full500 停止干净（无新容器、账本冻结快照落 DECISIONS）。
- 收 51 的 V2 设计块 → 批。
- 收 86 对照表初稿、85 命令包、55 金丝雀首批。
