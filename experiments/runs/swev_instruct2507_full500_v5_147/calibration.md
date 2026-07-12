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

## D1 补跑结果 (recover_instruct7, 2026-07-12,我方 in-place 更新)
7 题隔离 re-eval 真判定:**只 2 题(django-16901/17029)是 docker 撞名误判的真 resolved,5 题(django-17084/requests-1921/sphinx-7985/8269/8475)隔离后确认真 fail**(非撞名成功)。→ resolved 118→**120 = 24.0%**(比双签预估 25% 低,因 5 题真解不出,诚实)。7 题真 report 在 run 的 `recover_instruct7_eval/`。**最终分数:SWE-V×Instruct-2507 = 24.0%**。
