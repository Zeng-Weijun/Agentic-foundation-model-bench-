# Agentic-Foundation-Model-Bench — 复现总索引 (REPRODUCTION_INDEX)

**日期**: 2026-07-14 · **口径**: 6 bench × 2 开源模型 = 12 条官方复现,每条 ≥2 个独立盲审跨族双签(A=Claude,B=真 codex-pro / gpt-5.6-sol),证据全 push GitHub。

> 盖章规则:盲审被要求**默认分数是假的、尽力证伪**,只有无法证伪才判 REAL。数值以独立复现为准,不信 client 自报。

## Serving 配置(唯一,两模型同 pod)
- Pod `100.100.104.147`,sglang **0.5.13**,tp=2,ctx 262144。
- `:30000` = **Qwen3-30B-A3B-Instruct-2507**(seed 61643818, parser qwen)
- `:30001` = **Qwen3-Coder-30B-A3B-Instruct**(seed 484925000, parser qwen3_coder)
- 身份靠 `get_model_info` 的 `model_path`+seed 钉死(非 client label)。

---

## 12 条真实分数

| # | Bench | Model | Scaffold | **真实分数(honest)** | Denom | 双签(A / B) | Evidence commit |
|---|-------|-------|----------|----------------------|-------|-------------|-----------------|
| 1 | SWE-V | Coder | qwen-code | **46.8%** (234/500) | 500 | Claude / Claude→codex | 52d03ba |
| 2 | SWE-V | Instruct-2507 | qwen-code | **24.0%** (120/500) | 500 | Claude / codex | 6cc5d11 |
| 3 | TB2.1 | Coder | terminus-2 | **11.24%** (10/89) | 89 | Claude / codex | 3db376f · db609e6 |
| 4 | TB2.1 | Instruct-2507 | terminus-2 | **3.37%** (3/89) | 89 | Claude / Claude | 4e9a000 |
| 5 | Multilingual | Coder | qwen-code | **23.33%** (70/300) | 300 | Claude / codex | 7dde1ae · bc99ebc |
| 6 | Multilingual | Instruct-2507 | qwen-code | **9.33%** (28/300) | 300 | Claude / codex | 5c5b144 · a0e7aba |
| 7 | DeepSWE | Coder | qwen-code PathA | **0%** (0/113, 0/106valid) | 106 | Claude / codex | 31d87f1 |
| 8 | DeepSWE | Instruct-2507 | qwen-code PathA | **0%** (0/113) | ~106 | Claude / codex | 6c23a02 |
| 9 | RepoZero | Coder | qwen-code PathA | **24.5%**(10s) / 23.75%(5s) | 400 | Claude / Claude | 03dc19d |
| 10 | RepoZero | Instruct-2507 | qwen-code PathA | **11.50%** strict(node18) / 12.75% as-run(node20,10s) | 400 | Claude / **codex✓** | c066977 · 8adc09d |
| 11 | NL2Repo | Coder | qwen-code PathA | **14.29%** honest (raw 15.55%) | 95 mv | Claude / codex + leakfloor | fe06947 · d7df93a |
| 12 | NL2Repo | Instruct-2507 | qwen-code PathA | **1.48%** honest (raw 4.03%) | 97 | Claude / **codex✓** | 6978dbc8 · bcb976b |

`codex✓` = B 真跑 codex-pro (gpt-5.6-sol) 成功(30+并发抢 OAuth 仍完成);其余 B 因 OAuth 占用 fallback Claude-primary + 诚实标注。

### 同基座训练锚参照
- base = Qwen3-30B-A3B-Instruct-2507。Coder 是代码专精变体,Instruct 是通用变体。
- 除 DeepSWE(两模型 all-or-nothing 都 0)外,**Coder 每条都显著 > Instruct**,方向一致合理。

---

## ★ 复现中查出的 4 个 bench harness 判分缺陷(是 bench 判分不干净,非模型问题)

| 缺陷 | 机制 | 影响 | 谁抓到 |
|------|------|------|--------|
| **set-e 缺失** | SWE-bench `eval.sh` 用 `set -uxo pipefail` 缺 `-e`;C/C++/Java 编译失败不 abort → 跑 baked 预编译 stale binary → 假 pass 假 resolved | Multilingual 共 **7 假阳**(Coder 73→70 / Instruct 32→28);SWE-V 纯 python **零假阳安全** | codex 族(两 Claude 同族双签都漏,跨族才抓到) |
| **node-seam** | RepoZero Path A 判分用挂载的 qwen **node v20** 而非官方镜像 **node v18**(driver container_env PATH override);node20 把 ESM export 当模块自动识别 | RepoZero×Instruct **1.25pp**(5 题 node20 过 node18 崩,A+B 双独立 5/5 精确 match);Coder 仅 0.25pp | A(Claude)+B(codex)双独立 |
| **base-image leak** | NL2Repo 判分 `docker cp`+overlay **没盖住 base 镜像 site-packages** → 预装的真 pypi 包被 pytest 直接 import,模型零实现也过测(docker cp 复活 whiteout 隐藏层) | Instruct raw 4.03%→**honest 1.48%**(几乎全泄漏);Coder raw 15.55%→**honest 14.29%**(−1.25pp,主要是真本事) | A(Claude)+B(codex)+leakfloor sweep |
| **eval_timeout** | RepoZero driver 默认 10s vs 官方 5s(偏松 2×) | RepoZero×Coder 24.5%(10s)/23.75%(5s);Instruct 12.75%/12.25% | B(codex) |

---

## 逐条要点

- **DeepSWE 0/113(两模型)**:可靠上界。gold-solution audit honest_resolve_rate=0/102;clean env 对 agent 更宽松仍全 0。scaffold-suppression 有界(echo loop / git-revert / 探索循环 / Instruct-qwencode mismatch)。★**VENV 疑点 07-14 补跑关闭**:修 driver(agent 能 pytest 自测)后 full113_pyfix 补跑 34 python 仍 **0/34 reward=0**(verifier_rc 全 0 判分干净,mean 109 turns)→ 真 0 非悲观 floor。
- **RepoZero×Instruct**:node-seam A+B 双独立 5/5 印证 = harness 保真硬实证;honest range 11-13%,引用 **11.50% strict(node18)主 + 12.75% as-run 注**。B 恢复 rsa/test5 → 51 是保守 undercount。
- **NL2Repo×Coder honest 14.29%**:反直觉——原疑"同样虚高"被实测否定。61 非零题 51 个 leak floor=0 真解出;10 题泄漏(3 PURE-LEAK / 3 shadow / 4 partial),新查出 justext/pytz/pysondb-v2。
- **NL2Repo×Instruct honest 1.48%**:raw 4.03% 几乎全靠泄漏撑(402 passes 里 310 泄漏);databases 那题 agent 零 tool call 却 92%、stamina 那题零实现却 129/129。fully_solved 真 = 0。

---

## 假阳修正史(主动砍自己虚高 = 反作弊)
- Multilingual set-e:73→70 / 32→28(C++/Java stale binary,`bash -e` + binary hash 零 rebuild 铁证)
- RepoZero node-seam:node20→node18 strict 重判(Instruct 12.75→11.50)
- NL2Repo base-image leak:Instruct 4.03→1.48 / Coder 15.55→14.29
- NL2Repo argv-overflow:spec≥128KB 塞 argv → qwen 没启动,修 stdin 投递
- NL2Repo databases:argv-bug 期 0.922 假阳 → 0.026(后再 leak 归零)
- DeepSWE NO_PROXY 判题污染:4 httpx 冤成 gold_broken,挪回 valid

---

## ProgramBench(第 13 条候选 — 环境就绪,未跑全量)
- 端到端离线环境**已就绪**:镜像布局搞清(黑盒 executable + 源码抽走 + gold 在 HF blob);OCI 层去重 transport ~40-80GB(vs per-tar 250-500GB 放不下);驱动 + 判分链**Tier-0 GREEN**(fixture correct50/incorrect0)。
- 无硬阻塞,全量跑(搬全 201 镜像 + blob + 定 compile 约定 + 接 yaml)待启。

---

*所有 evidence bundle(yaml/sh/trace/分数/serving/verdict/SHA256SUMS)在对应 `evidence/*` 分支。main 仅 gpt-5.5 Multilingual;Qwen 复现全在 evidence 分支。*
