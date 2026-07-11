# Calibration — SWE-V × Qwen3-Coder-30B × qwen-code
run: swev_coder_full500_v5_147_20260711T165758Z

## Score
- **resolved 234 / 500 = 46.8%**  (denom_assert PASS: results.jsonl 500 rows == dataset_size 500)
- resolved 定义: FAIL_TO_PASS 全 success ∧ PASS_TO_PASS 全 success (SWE-bench Verified 官方判定)
- eval harness: swebench 4.1.0 (run_evaluation)
- include_unverified: NO — 6 个 eval_error 题由隔离 re-eval 恢复出真判定(非跳过、非补假)

## Bench × Model × Harness
- bench: SWE-bench Verified (500 Python tasks, princeton-nlp/SWE-bench_Verified, split=test)
- model: Qwen/Qwen3-Coder-30B-A3B-Instruct (qwen3_moe)
- harness: qwen-code 0.15.6 native in-container, --yolo, 直连 serving(非 host bridge)
- serving: 100.100.104.147:30001, sglang 0.5.13, tp2, parser qwen3_coder, ctx 262144, random_seed 484925000 (before==after)

## Anchor & 口径差
- 同基座 prior: SWE-V×Coder qwen-code = 48.6% (2026-07-09, serving .140, 已死). 本 run 46.8% 略低 = serving 节点(.147 vs .140)+采样的自然波动, 方向朝下, 无注水.
- 官方 SWE-bench Verified 锚(不同 harness, 不可比): bash-only gpt-5.2-high 72.8%.
- ★6 题 eval_error(astropy-14096, django-13109/13449/13810/15467, sphinx-9698)= 并发 docker 的 make_run_report container-list race(非模型/非patch), 隔离 re-eval(run_id recover6)恢复: 4 resolved + 2 真 fail. 见 TRACE.md.

## Independent verification
- 2026-07-12 双盲 auditor 双签 REAL: 两人各自独立复判全 500(0 不一致 vs results.jsonl), gold cross-check FAIL_TO_PASS==官方(0 relabeling), live 探测 serving seed 484925000(同 running 进程, 排除 label-swap), on-host 镜像 digest 匹配, SHA256SUMS 12/12.
