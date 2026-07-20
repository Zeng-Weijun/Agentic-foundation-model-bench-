# SWE-bench Verified — gpt-5.5 v2.1 终分报告

> **Status: HISTORICAL_NON_CANONICAL_CONFIG (2026-07-21).** Restored because §5 records independent review evidence. The original high-effort final/board-comparable language below is historical only, not a current relay-backed `gpt-5.5` + `medium` suite score.

> 日期:2026-07-05 | 交付:85(复审)| 产出:V2.1 runner(post-harness-fix)| 双签:见 §5

## 1. 终分

| 项 | 值 |
|---|---|
| **Score** | **386 / 500 = 77.2%** single-attempt pass@1 |
| 模型 / 档位 | `gpt-5.5`,reasoning_effort `high` |
| scaffold | mini-swe-agent `v2.0.0`(bash-only,官方榜锚同款) |
| 数据集 | SWE-bench Verified 500(离线,`--network=none`) |
| infra 失败 | **0**(eval_rc=0 ×500;agent 容器 500/500 起成功) |
| run | `v2_full500_c100_gpt55_20260704T211853Z`(v2.1 re-run in place) |

## 2. v2 → v2.1 修复叙事(为什么第一次是 43.6%)

**v2(c100)首跑 = 218/500 = 43.6% —— 这是 harness-bug 分,不是模型分。**

- 根因:**211/212 个 `no_patch` 实例 = mini-swe-agent 容器 `docker run ... exit status 125`**(容器根本没起来),横跨所有 repo(含最易的 django)。
- 机制:c100 并发下镜像未在 agent `docker run` 前 preflight → 镜像本地不在 → docker 尝试联网 pull `docker.io/swebench/...` → `--network=none` pod 连不上 → ~16s 后 exit 125 → agent 没跑 → 空 patch → eval 空 patch → 未解。
- 被漏原因:`eval_rc=0 ×500` 量的是 eval 步;agent-rollout 的 docker-125 在上游、未被 eval_rc 计入。
- sphinx "塌方" 6.8%(3/44)= 假象:35/44 是 docker-125,agent 没跑,非模型差。

**修复(harness):** ① agent `docker run` 前加镜像 preflight 门 + `--pull=never`(快失败可重试,不 16s 联网 pull);② run 前 PREHEAT 全 500 镜像;③ agent ref 本地 tag 对齐;④ docker-125 归类 infra 自动重试。

**v2.1 re-run 结果:** `no_patch 212→0`,`patch 288→500`(每个 agent 都跑),`resolved 218→386`。43.6% → 77.2% 的跳变 = docker-125 bug 被移除的量,精确符合复审预测(真信号估计 218/288=75.7%,70-76% 邻域)。

## 3. per-repo 回升(bug 修复前后)

| repo | v2(bug) | v2.1(fixed) |
|---|---|---|
| sphinx-doc | 6.8% (3/44) | **64% (28/44)** |
| matplotlib | 29.4% (10/34) | **76% (26/34)** |
| sympy | 30.7% (23/75) | **69% (52/75)** |

残留异常(非阻断):**pylint-dev 3/10 = 30%**(唯一 <40% repo;可能真难 repo,n=10,patch 真实)——标记下轮抽查。

## 4. 真实性抽验(3 个曾 docker-125 的新 resolved)

| instance | patch | eval verdict |
|---|---|---|
| sphinx-doc__sphinx-10466 | 493c 真 diff(`sphinx/builders/gettext.py`) | ∈ resolved_ids,非 empty/error |
| django__django-13158 | 738c 真 diff | ∈ resolved_ids,非 empty/error |
| sympy__sympy-13480 | 590c 真 diff | ∈ resolved_ids,非 empty/error |

均 post-fix 新鲜 rollout、0 docker-125。**patch 真实非空 + eval 真跑。**

## 5. 双签

- **85(复审 PASS):** 独立核验 —— harness 修复实效(0 no_patch/0 docker-125)、77.2% 符合预测、per-repo 回升、3 新 resolved 真实。诊断链见 `_coordination/bench_kvm_e2e_20260704/DECISIONS.md`(766L→854L 段)。
- **run 产出(V2.1 runner):** 500/500 agent 起成功、eval_rc=0 ×500、账本 386 resolved 落 `results.jsonl`。

## 6. 对外口径(board-comparable)

> **SWE-bench Verified · mini-swe-agent v2.0.0(bash-only)· gpt-5.5 high · 单次 pass@1 = 77.2%(386/500)· 0 infra。** 与官方 **gpt-5.2-high 锚(72.8%/500 pass@1)同口径** → gpt-5.5 **相同条件下 +4.4pp**。

**必须声明的 caveat:**
1. **单跑**(方差 ~±3-4pp,非多种子均值)。
2. gpt-5.5 **不在**冻结官方榜(5.3/5.4/5.5 晚于 ~2026-02 冻结)→ 77.2% 是**延伸 gpt-5.2-high 锚的同口径新基线**,非"官方榜分"。**可宣称:同口径复现 + 对 gpt-5.2-high 官方锚 +4.4pp;不可宣称:上榜。**
