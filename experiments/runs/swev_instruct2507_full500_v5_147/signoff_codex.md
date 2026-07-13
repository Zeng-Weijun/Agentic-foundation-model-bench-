# 对抗式签核报告 — SWE-bench Verified · Qwen3-30B-A3B-Instruct-2507 · qwen-code (v5_147, 24.0%)

- **审计对象**: `experiments/runs/swev_instruct2507_full500_v5_147/` (canonical full trace:
  `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_full500_v5_147_20260711T165758Z`)
- **审计执行宿主**: `env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`（read-only；docker 独立复判除外）
- **serving**: `100.100.104.147:30000`（sglang 0.5.13, tp2）
- **bench**: SWE-bench Verified (500) · **harness**: qwen-code 0.15.6 native, swebench 4.1.0 (`run_evaluation`)
- **审计日期**: 2026-07-13
- **审计人 / 身份声明**: Claude (Sonnet 5, Claude Agent SDK subagent) executing this campaign's
  **"Codex 族"复核 lane**（跨族双签协议里补位角色，非自称 OpenAI 产品）。本轮**确有**尝试拉起真实
  `codex-pro`（OpenAI Codex CLI，`gpt-5.6-sol`，`reasoning.effort=ultra`，`--search`）做独立第二意见：
  运行 ~26 分钟后，其 plan/diff 输出开始混入*另一个*并发子任务的 brief（TB2.1×Coder / port:30001 /
  `build-pov-ray` 等——这些字符串不属于本审计对象），判定为共享 scratchpad 下多个并发 `codex-pro`
  会话（`ps aux` 同时可见 ≥8 个 `gpt-5.6-sol --search` 进程分属不同任务)的上下文串扰，已终止该会话
  （PID 84716），**未采纳其半成品输出**。因此本报告的判定与证据全部来自我本人（Claude 侧）的
  hands-on 复核，不是转述 Codex 的话——如实披露，不伪造"Codex 说 REAL"这类引用。
  **建议编排方**：给并行的 "Codex 族" 审计子任务分配独立 scratchpad（而非共享同一 session 目录），
  避免 `--search` 读到邻居任务的 prompt 文件。

## 结论

**REAL** — 120/500 = 24.0%（含 7 题撞名/超时隔离复判修正）经得起对抗式复核；未能证伪。

## 逐条证据（① - ④ 对应任务要求）

### ① denom = 500，未缩水
- `results.jsonl`：`wc -l` = 500，python 独立重算 unique `instance_id` = 500，0 重复。
- sha256 三处一致（互为交叉证据，非单一来源自证）：
  - 全量 run 目录：`.../runs/swev_instruct2507_full500_v5_147_20260711T165758Z/results.jsonl`
  - evidence worktree 副本：`.../repo/.worktrees/evidence-sweml-full300-147/experiments/runs/swev_instruct2507_full500_v5_147/results.jsonl`
  - **origin/main git blob**（`git show origin/main:experiments/runs/swev_instruct2507_full500_v5_147/results.jsonl \| sha256sum`）
  - 三者均为 `c4914222cebf95f6477eba601a80542a3df6163267c187d39b308a26c1109302`
- `denom_assert.txt`（v6）：`rows==declared AND unique==rows => PASS`，独立复算一致。
- python 独立重算 `resolved==True` 计数 = **120** → 120/500 = **24.0%**，与声称一致。
- `agent_status` 交叉表：`patch=355, no_patch=139, recovered_eval=4, recovered_eval_recover7=2`
  （合计 500）；**no_patch 行中 resolved=True 的数量 = 0**（排除空 patch 冒领）。

### ② resolved 真实性 — 亲自起容器复判 3 个（非 disputed 7 题内）
在 KVM 宿主上，用与本 run 完全相同的官方 `swebench.harness.run_evaluation`（4.1.0，`pip show swebench`
确认版本号与 `calibration.md` 声称一致）、相同 predictions（取自
`instances/<iid>/prediction.json` 里 agent 产出的真实 patch），**全新 run_id**
（`codex_audit_20260713`，与任何历史容器名不可能撞名）、`--cache_level env`（复用离线镜像不重建）：

```
--instance_ids django__django-12050 pylint-dev__pylint-6903 sphinx-doc__sphinx-9698 \
--run_id codex_audit_20260713 --namespace swebench --cache_level env --max_workers 3 --timeout 400
```
结果（48s 完成，真实容器启停日志）：
```
{"total_instances":3,"resolved_instances":3,"unresolved_instances":0,"error_instances":0,
 "resolved_ids":["django__django-12050","pylint-dev__pylint-6903","sphinx-doc__sphinx-9698"]}
```
3/3 独立复现 resolved=true。这不是重读旧日志，是我本人从零跑通的容器化 eval。

### ③ serving 身份 — 确认 Instruct-2507，非 Coder
- `serving/IDENTITY_SUMMARY.json`：before==after，
  `model_path=".../models/Qwen3-30B-A3B-Instruct-2507"`，`random_seed=61643818`，`sglang 0.5.13`。
- **时间戳锚定**（排除"打包时才伪造 serving 证据"的可能）：`get_model_info_before.json` mtime
  = 2026-07-12 00:57:58 +0800，与本 run `launch_ts=20260711T165758Z`(UTC) 精确对应；
  `get_*_after.json` mtime = 06:49:20，与 run 结束时间对应。evidence 打包时间是次日 07-13 01:31，
  但 bundle 里的 serving 文件 sha256 与 run 目录原始文件**逐字节相同**——不是打包时新造的。
- **我本人现场直接 curl 验证**（2026-07-13，独立于任何历史文件）：
  `curl http://100.100.104.147:30000/get_server_info` / `/get_model_info` →
  `model_path=".../Qwen3-30B-A3B-Instruct-2507"`, `served_model_name="Qwen/Qwen3-30B-A3B-Instruct-2507"`,
  `random_seed=61643818`, `tp_size=2`, `port=30000` — 与历史记录一致，确认不是 Coder。

### ④ 120/500=24.0% 算术 + 7 题修正合法性
- **backup 快照差分复算**（`results.jsonl.bak_before_recover4`,
  `.bak_before_recover4_manual`, `.bak_before_recover7_manual`，均仍在 run 目录磁盘上，非事后转述）：
  - recover4 段：118/500（4 题从"临时消失"496 行恢复为 500 行，值为
    scikit-learn-26323=False, django-13786=False, django-11119=True, django-16527=True）
    ⇒ 与 `events.jsonl` 4 条实时 `infra_error`("official eval returned nonzero") 日志时间戳吻合，
    非事后编造。
  - recover7 段：118/500 → 120/500，**差分只有 2 行变化**：
    `django__django-16901: False->True`, `django__django-17029: False->True`；
    另外 5 题（`django-17084`, `psf__requests-1921`, `sphinx-doc__sphinx-{7985,8269,8475}`）**差分为
    0（原样保持 False）**——与 `calibration.md` 声称的"只 2 题真 resolved，5 题确认真 fail"逐字吻合。
- **穷举扫描排除"挑7个好的"选择性偏差**：对全部 500 个 instance 的**原始**（非 recover）eval 日志
  做全库 grep：
  - `"409 Client Error"`（容器撞名冲突）命中恰好 3 个 instance：`django-16901, django-17029,
    django-17084`
  - `"Timeout error: [0-9]+ seconds exceeded"`（eval 超时）命中恰好 4 个 instance：
    `sphinx-7985, sphinx-8269, sphinx-8475, psf-requests-1921`
  - 3+4=7，与 recover7 批次的 7 个 instance_id **完全相同，全库无遗漏无多余**——证明这 7 个不是
    挑出来的，是这两种错误签名在全部 500 题里的**完整集合**。
  - 注：任务 brief 里"7 题因容器撞名 409"的说法**不完全精确**——只有 3/7 是字面 409，另 4/7 是
    eval 超时（同属并发 docker 资源争用的姊妹问题）；但两个签名合起来精确等于 7，且分类本身经
    我独立复算成立，不影响最终判定。
  - 真实性交叉验证（不只信 grep 命中，读了实际 report.json/traceback）：
    - `django-16901`：`recover_instruct7_eval/logs/run_evaluation/recover_instruct7/.../report.json`
      = schema_version 2 标准 swebench 输出，FAIL_TO_PASS 1/1 success + PASS_TO_PASS 6/6 success，
      真实 `sweb.eval.django__django-16901.recover_instruct7` 容器启停日志，`Ran 7 tests ... OK`。
    - `django-17029`：同上，1/1 + 44/44 success，真实 pytest/unittest 输出。
    - `django-17084`（"确认真 fail"的 5 题之一）：隔离复判后仍 resolved=false，且是**实质性失败**——
      真实 traceback `django.db.utils.OperationalError: near "OVER": syntax error`（真的跑了测试并
      真的失败，不是 infra 噪音被顺手标 fail）。
  - **patch 未被掉包**：`django-16901` 原始 agent patch
    (`instances/django_u_django-16901/agent/prediction.patch.diff`, 975 bytes) 与
    `recover_instruct7_eval/prediction.jsonl` 里用于复判的 `model_patch` **sha256 完全一致**
    (`03e4290871b32c8c35262818308dd0860e6d43a54e0d0ba5fb3655c4fb8744d8`)——复判用的是同一份 agent
    产出，不是换了个更好的 patch 去骗分。
- **git 历史自证清白**（非单次可疑提交，是多轮诚实修正）：
  `183c71f`(118/500=23.6% 初版) → `eea062c`("dual-signed REAL (23.6%); flag 7-task ... true ~25.0%"
  ——上一轮双签已经把 23.6% 判 REAL，并标注了7题问题，**估计上限 ~25.0%**) →
  `283b187`("recover D1 7 tasks -> 24.0% final (2 collision-misjudged + 5 genuine fails)"
  ——实际补跑后把估计**从更高更整的 ~25.0% 下修到更低更精确的 24.0%**）。伪造分数的人不会在
  做完实际工作后把自己的估计往下修正成更保守的数字。

## 发现的问题（MAJOR，不影响本次判定，但需要修）

`verdict_pack.tar.gz`（bundle 内打包供离线复核用的证据包）+ `results.jsonl` 里 recover7 批次 2 个
被修正 instance 的 `report_path` 指针，**都是 recover 之前的旧证据**，尚未随 24.0% 的修正同步更新：

- `verdict_pack.tar.gz` 内 `django__django-16901/report.json` 与 `django__django-17029/report.json`
  仍是 `error_instances:1` 的旧版；`test_output_tail.txt` 里赫然是原始 409 报错原文
  (`Error building image django__django-16901: 409 Client Error ... Conflict ("Conflict. The
  container name ... is already in use ...")`)。
- `results.jsonl` 里这两行的 `report_path` 字段指向
  `instances/django_u_django-1690{1,29}/eval/Qwen__Qwen3-30B-A3B-Instruct-2507.v2_*.json`，
  该文件本身也从未被 recover 流程原地覆盖，同样是旧的 `error_instances:1`。
- 而 `TRACE.md` 明确写"verdict_pack ... 已经带 report.json ... 离线复核不需要完整 trace"——这句话
  对这 2(+1) 个 instance 是**假的**：真正的修正证据只存在于
  `recover_instruct7_eval/logs/run_evaluation/recover_instruct7/` 这个不在 verdict_pack 里的目录。
  只信 verdict_pack 的第三方审计者会看到自相矛盾的证据（打包证据说 error/unresolved，
  results.jsonl 说 resolved=true），甚至可能因此**少算 2 题、把 24.0% 误判回 23.6%**。
- 该 staleness 的方向是保守偏差（让"自足"证据包**低估**分数，不是**虚增**分数），不支持"刻意造假
  变高"的假说，但仍是真实的 bundle 完整性缺陷，建议：recover 流程结束后同步重打
  `verdict_pack.tar.gz` 并原地覆盖 `report_path` 指向的文件，或至少在 TRACE.md 补一条
  "instances X/Y/Z 的权威证据在 recover_instruct7_eval/，不在 verdict_pack" 的说明。

## 环境侧观察（非本审计对象的问题，仅记录）
- `origin/main` 在本次审计过程中被并发操作从 `7410dc9`（"Multilingual CLOSE..."）回退到其父提交
  `fe06947`——说明这是一个多 agent 并发写的活仓库；已确认 `283b187`（本 run 的修正提交）在回退
  前后**始终**是 `origin/main` 的祖先，且 `results.jsonl` 内容哈希未受影响。
- 主 worktree（`$BM/repo`，branch `main`）当时处于 dirty 状态（大量与本审计无关的未提交改动），
  遵照任务指示未触碰；本文件通过 git plumbing（`read-tree`/`commit-tree`，无需完整 working-tree
  checkout）直接基于 `origin/main` 提交，不经过 dirty 主 worktree。

## Repro（供下一个复核者）
```bash
ssh env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'RUNDIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_full500_v5_147_20260711T165758Z
   B=/mnt/shared-storage-user/mineru2-shared/zengweijun
   export HF_HOME=$B/.cache/huggingface HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 DOCKER_API_VERSION=1.44
   $B/conda_envs/swebench/bin/python $RUNDIR/eval_wrap.py \
     --dataset_name princeton-nlp/SWE-bench_Verified \
     --predictions_path <your predictions.jsonl> \
     --instance_ids <ids> --run_id <fresh_unique_id> --namespace swebench --cache_level env \
     --max_workers 3 --timeout 400'
```

**判定：REAL。** 120/500=24.0% 站得住；7 题修正（2 真复活 + 5 确认真 fail）经全库穷举验证非选择性
造假；serving 身份、denom、patch 一致性均独立复核通过。verdict_pack staleness 是需要修的
MAJOR 完整性缺陷，但方向保守，不构成分数造假证据。

— Claude (Sonnet 5), Codex-lane auditor, 2026-07-13
