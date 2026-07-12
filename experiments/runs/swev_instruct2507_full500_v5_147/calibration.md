# Calibration — SWE-V × Qwen3-30B-A3B-Instruct-2507 × qwen-code
run: swev_instruct2507_full500_v5_147_20260711T165758Z

## Score
- **resolved 118 / 500 = 23.6%**  (denom_assert PASS: 500 rows == 500)
- resolved 定义: FAIL_TO_PASS 全 success ∧ PASS_TO_PASS 全 success (SWE-bench Verified 官方判定)
- eval: swebench 4.1.0 (run_evaluation); include_unverified: NO — 4 个 eval_error 题隔离 re-eval 恢复真判定

## Bench × Model × Harness
- bench: SWE-bench Verified (500 Python, princeton-nlp/SWE-bench_Verified, test)
- model: Qwen/Qwen3-30B-A3B-Instruct-2507 (qwen3_moe) — ★同基座训练锚(与 Qwen3-Coder-30B 同基座)
- harness: qwen-code 0.15.6 native in-container, --yolo, 直连 serving
- serving: 100.100.104.147:30000, sglang 0.5.13, tp2, parser qwen, ctx 262144, random_seed 61643818 (before==after)

## Anchor & 同基座对比
- 同基座 prior: SWE-V×Instruct-2507 = 21.5% (2026-07-09, serving .140 已死). 本 run 23.6% 略高 = 采样+serving 节点自然波动.
- ★同基座能力差: 同一 SWE-V 500 上, Coder-30B **46.8%** vs Instruct-2507 **23.6%** — Coder(代码专精)约 2x Instruct(通用).
- 4 题 eval_error(scikit-26323/django-13786 fail, django-11119/16527 resolved)= 并发 docker make_run_report race, 隔离 re-eval 恢复. 见 TRACE.md.

## 双签审计更正 (2026-07-12, 2 auditor 各自独立判 REAL)
- 双签双 REAL:重判 500 题 report 级 + 22 题原始 docker 日志级 **0 不一致**(resolved 118==118);模型身份 Instruct-2507(服务端 model_path+seed 61643818,live 探测确认,非 Coder 掉包);qwen-code input_tokens 逐轮单调增长;**反向择优证据**——弃掉的 76 题局部 run 是 26.3%,高于保留 run 同子集 21.1%,若在择优不会弃高留低。23.6% 是不利于作假者的低分。
- ★DEFECT D1(方向压低分数):除 4 题 eval_error,另有 **7 题 docker 容器名撞名**(Coder+Instruct full500 同秒并行,eval 容器名 `sweb.eval.<iid>` 不含模型名)被保守计 False:django-16901/17029/17084、requests-1921、sphinx-7985/8269/8475。补隔离 re-eval 后真值最可能 **118→125 = 25.0%**。[补 re-eval 进行中]
- DEFECT(文档级):TRACE.md 的 `repairs/cleanup_race` 目录实际不存在(模板句失实);manifest namelist 锚不可复现——但完整性已由 git↔pack↔run-root 三方字节级独立确立。
