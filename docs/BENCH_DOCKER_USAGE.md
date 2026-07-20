# Bench Docker 使用文档 — SWE-V & TB2.1(给别的项目 copy-paste 用)

> 2026-07-12 · 作者 = bench 文档 agent。本轮**只覆盖 SWE-V 和 TB2.1 两个 bench**(其余 5 个另行)。
> 两个 bench 的「跑一个 task」命令都**真起容器验证过**(gold/oracle 路径,零模型),验证输出原样贴在各节。
> 所有 docker 操作在 KVM 执行机上;共享盘根 `$B=/mnt/shared-storage-user/mineru2-shared/zengweijun`。

## 执行环境(两个 bench 通用)

| 项 | 值 |
|---|---|
| KVM 执行机(docker 活/镜像在此) | `ssh -CAXY env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn` |
| Docker | Server 26.1.3,`/var/run/docker.sock`,root,storage=fuse-overlayfs,`/dev/kvm` 可用 |
| 共享盘在 KVM | 已挂载(`$B` 直接可读),conda env / HF 缓存 / 数据集都走共享盘 |
| OCI registry("Harbor") | `100.97.118.137:8555`,命名空间 `swe-data-harness/`;自签 TLS(`curl -k --noproxy '*'`,daemon 需 `--insecure-registry`) |
| ★不要碰在跑的批 1 容器 | 名字含 `swev_*_full500_v5_147_*` / `sweb.eval.*.v2_*`(SWE-V 全量模型跑正在进行) |

---

## 总览表

| Bench | task 数 | 镜像命名 | registry | 拉取方式 | 判分机制 | 端到端验证状态(诚实) |
|---|---|---|---|---|---|---|
| **SWE-V** | 500 | `swebench/sweb.eval.x86_64.<inst>:latest`(`__`→`_1776_`) | Docker Hub `swebench/` + Harbor `swe-data-harness/swebench-verified-*`(500/500 digest) | 在线 `docker pull`(Hub 或 Harbor by-digest);离线 = 96 个 repo-chunk tar load 后 retag 到 base ref | `swebench.harness.run_evaluation` → `report.json` 的 `FAIL_TO_PASS`+`PASS_TO_PASS` 全过 ⇒ `resolved:true` | **gold-oracle 真验过**(astropy-12907 本 agent 2026-07-12 + 仓内 50/50 子集);**模型 full500 无 sealed 分**;transport 500/500 |
| **TB2.1** | 89 | 本地 `tb2-offline/<task>:20260425[-closure-rN]`;Harbor `terminal-bench-2-1-<task>` | Harbor `swe-data-harness/terminal-bench-2-1-*` | 在线 `docker pull <harbor>@<digest>`;离线 `docker load -i <tar>` | task 自带 `run-tests.sh` → `/logs/verifier/reward.txt`(0/1)+ `ctrf.json`;tb 原生 harness → `results.json` 的 `is_resolved` | **manual-oracle 本 agent 真验过**(log-summary-date-ranges,2026-07-12,reward=1);canonical oracle 84/89(jvm9z);模型 gpt-5.5-medium 70.8%(63/89) |

---

## SWE-V(SWE-bench Verified, 500)

### 概况
- **task 数 500**,纯 **Python**,12 个上游 repo(astropy / django / pytest / pylint / requests / matplotlib / sympy / scikit-learn / sphinx / xarray / flask / seaborn 等)。
- **数据集**:`princeton-nlp/SWE-bench_Verified`(split=test)。共享盘 HF 缓存已就位、可离线:
  `$B/.cache/huggingface/datasets/princeton-nlp___swe-bench_verified/`(`HF_HOME=$B/.cache/huggingface`)。
- 每个 instance 自带 `patch`(gold 补丁)、`test_patch`、`FAIL_TO_PASS` / `PASS_TO_PASS` 测试集(datasets 里的字段)。

### 镜像
- **命名 = SWE-bench 官方标准**:`swebench/sweb.eval.x86_64.<instance>:latest`,其中 instance 里的 `__` 被替换成 `_1776_`。
  例:instance `astropy__astropy-12907` → 镜像 `swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest`。
- KVM worker 上**已全部就位**(批 1 正在用;`docker images | grep sweb.eval` 可见,约 500 个 instance 镜像 + swerex 派生)。
- **Harbor 镜像**:同镜像也镜像到 `100.97.118.137:8555/swe-data-harness/swebench-verified-*`(P0 registry `_catalog` 里 SWE-V 占大头)。
- **digest 权威表(source of truth)**:`$B/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json`
  — 500 条,**500/500 都有 `p0_digest_ref`(Harbor)**;每条 schema `{instance_id, local_ref, p0_digest_ref, fallback_tar, fallback_tar_sha256, expected_base_ref}`。
  (另有 06-28 的 `repo/manifests/images/swebench_verified_full500.yaml`,但那版 `p0_digest_ref: None`,是 fallback-tar 时代;Harbor digest 是 07-03 才在上面这个 p0_map 里落地的。)
- **离线 tar**:`$B/swe/swerex_images/chunks/<repo>-1776-<repo>_NN.tar` — 500 instance 归到 **96 个 repo-chunk tar**,每块带 `fallback_tar_sha256`;索引 `$B/swe/swerex_images/manifest.tsv`(728 行,列 = `instance_id \t repo_key \t chunks/<tar> \t swerex-prebuilt-wrapper-ref`)。worker 上 `docker load` 每块后 **retag wrapper ref → `swebench/sweb.eval.x86_64.<inst>:latest` base ref**。不依赖公网 pull。

### 拉取
```bash
# 方式1 官方 Docker Hub(需外网):
docker pull swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest

# 方式2 Harbor by-digest(worker 内网可达;daemon 需 --insecure-registry 100.97.118.137:8555)
#   下面这个 digest 已实测 registry manifest HTTP 200:
docker pull 100.97.118.137:8555/swe-data-harness/swebench-verified-astropy-astropy-12907@sha256:8be433890e09c182a635cd45c1ab2e87bc417764870177098d49da2b7edcd45f
docker tag  100.97.118.137:8555/swe-data-harness/swebench-verified-astropy-astropy-12907@sha256:8be433890e09c182a635cd45c1ab2e87bc417764870177098d49da2b7edcd45f \
            swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest

# 方式3 离线 tar(无外网):load repo-chunk tar 后 retag(chunk↔instance 见 manifest.tsv 第4列)
docker load -i $B/swe/swerex_images/chunks/astropy-1776-astropy_00.tar   # sha256 784d80536d79d76024be5ced8e2f447dfe454122a73c87e390335d1f63615b9c
```
> 注:本文档的 gold-oracle 验证用的是 worker 上**已存在的本地镜像**(批 1 已就位),没走 pull;上面 digest 的 HTTP 200 是在 registry manifest 层实测的。

### ★跑一个 task 端到端(gold-oracle,零模型)— 本 agent 真验过

判 docker 端到端是否通,用 **swebench 自带的 `--predictions_path gold`**:它自动取每个 instance 的 gold 补丁当预测、起容器、跑 `FAIL_TO_PASS`/`PASS_TO_PASS`,resolved 应为 true。**不需要任何模型/serving。**

```bash
# 在 KVM 执行机上。用共享盘的 swebench conda env(4.1.0)+ 共享盘 HF 缓存。
B=/mnt/shared-storage-user/mineru2-shared/zengweijun
PY=$B/conda_envs/swebench/bin/python
export HF_HOME=$B/.cache/huggingface HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1
export DOCKER_API_VERSION=1.44          # 生产 eval_wrap.py 里对 docker-py 的 pin,避免 API 协商问题
W=$B/nips2026/agentic-foundation-model-bench/tmp/oracle_$(date +%Y%m%dT%H%M%SZ); mkdir -p "$W"; cd "$W"

$PY -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified --split test \
  --predictions_path gold \
  --instance_ids astropy__astropy-12907 \
  --run_id oracle_doc_verify \
  --namespace swebench --cache_level env \
  --max_workers 1 --timeout 1800
```
- `--namespace swebench` → 直接用本地 `swebench/sweb.eval.x86_64.*:latest`,**不会重建**("Found 1 existing instance images. Will reuse them.")。
- 判分 grading 容器名 = `sweb.eval.<inst>.<run_id>`,跑完 swebench 自动删。用完把 `$W` 删掉即可。

**真实验证输出(2026-07-12,network 正常,零模型):**
```
Using gold predictions
Found 1 existing instance images. Will reuse them.
Running 1 instances...
# 汇总 gold.oracle_doc_verify.json:
{ "total_instances":1, "completed_instances":1, "resolved_instances":1,
  "unresolved_instances":0, "error_instances":0, "completed_ids":["astropy__astropy-12907"] }
```

### 判分
verdict 在 `report.json`:`logs/run_evaluation/<run_id>/gold/<inst>/report.json`(汇总另有 `<model>.<run_id>.json`,gold 模式下 `<model>`=`gold`)。
`resolved=true` 的判据 = **`FAIL_TO_PASS` 全 success 且 `PASS_TO_PASS` 全 success**。

**真实 report.json(astropy-12907,截断):**
```json
{ "astropy__astropy-12907": {
    "patch_successfully_applied": true,
    "resolved": true,
    "tests_status": {
      "FAIL_TO_PASS": { "success": [
        "astropy/modeling/tests/test_separable.py::test_separable[compound_model6-result6]",
        "astropy/modeling/tests/test_separable.py::test_separable[compound_model9-result9]" ], "failure": [] },
      "PASS_TO_PASS": { "success": [ "...test_coord_matrix", "...test_cdot", "...(13 个全过)" ], "failure": [] } } } }
```

**生产(模型)打分路径**:orchestrator `scripts/full500_qwencode_orchestrator_v21.py` 把模型补丁写进 `prediction.json`,再调 `<run_root>/eval_wrap.py`(= `run_evaluation` 的薄封装,内含 `DOCKER_API_VERSION=1.44` pin + 离线 eval 依赖 cache patch),同样产 `report.json` → resolved。实况命令:
```
$B/conda_envs/swebench/bin/python <run_root>/eval_wrap.py \
  -d princeton-nlp/SWE-bench_Verified -s test -p <prediction.json> -i <inst> \
  --max_workers 1 -id v2_<inst_key> -n swebench --cache_level env --report_dir <dir> -t 1800
```

### 验证状态(诚实)
- **transport → worker**:500/500 都有 Harbor digest(p0_map;抽查 6/6 返回 HTTP 200)+ 96 个 chunk tar 全带 sha256。
- **gold-oracle 端到端**:✅ 两处证据:
  1. **本 agent 2026-07-12 真跑 1 个 instance**(`astropy__astropy-12907`,resolved:true,FAIL_TO_PASS 2/2 + PASS_TO_PASS 13/13)。证据 `$B/nips2026/agentic-foundation-model-bench/tmp/oracle_doc_verify_20260712T032125Z/`。
  2. 仓内既有 **50-task gold 子集**跑过、**50/50 resolved**(2026-06-29):`$BENCH/runs/swev_gold50_harness_nsss8_20260629T002855/`(top report `gold.swev_gold50_...json` total=50 resolved=50 error=0)。
  - ⚠️ **没有 full-500 的 gold run**(只有 50-task + 我这 1 个)。
- **模型全量 500:** 当前没有可发布的 v5-sealed full-500 模型分。以下 run id 只用于定位历史 live、terminated 或 partial 诊断证据；其分子、分母和百分比都不是可发布分数:
  - `swev_coder_full500_v5_147_20260711T165758Z` — 历史 live diagnostic run。
  - `swev_coder_full500_v5_147_20260711T145108Z` — 历史 terminated diagnostic run。
  - `swev_instruct2507_full500_v5_147_20260711T165758Z` — 历史 partial diagnostic run。
  - 先前的 “48.6%” claim 在本路径没有 sealed 证据，现已从本操作文档撤回。
- **封样机制**:v5 launcher 把 `report.json` 汇成 13 字段 `results.jsonl`(`instance_id,resolved,run_id,dataset,dataset_size,harbor_digest,reward,...`),带分母守卫 `len(results)==500`(`scored_runs/lib/scored_run_v5_lib.sh` `v5_seal`)。
- 官方锚(非本仓复现):SWE-bench Verified bash-only gpt-5.2-high 72.8%。

### 事实来源路径
- gold 内部实现:`swebench/harness/run_evaluation.py:608`(`--predictions_path gold`)→ `harness/utils.py:42`(从 dataset `patch` 字段自动造预测)。
- 实况 orchestrator/eval 命令:`ps -ef`(KVM,pid 1529994/1529995 + eval_wrap 子进程);orchestrator `repo/.worktrees/swev-qwencode-v21-agent51/scripts/full500_qwencode_orchestrator_v21.py`(1296 行)。
- `<run_root>/eval_wrap.py`(run_root = `$B/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_v5_147_20260711T165758Z/`)
- swebench 4.1.0:`$B/swe/SWE-bench/swebench/`;env `$B/conda_envs/swebench/bin/python`
- digest 权威表:`$B/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json`;chunk 索引 `$B/swe/swerex_images/manifest.tsv`
- 既有 gold50 run:`$BENCH/runs/swev_gold50_harness_nsss8_20260629T002855/`;seal lib `$BENCH/scored_runs/lib/scored_run_v5_lib.sh`
- 我的 gold-oracle run:`tmp/oracle_doc_verify_20260712T032125Z/{run.log, gold.oracle_doc_verify.json, logs/run_evaluation/oracle_doc_verify/gold/astropy__astropy-12907/report.json}`

---

## TB2.1(Terminal-Bench 2.1, 89)

### 概况
- **task 数 89**,终端/CLI/软件工程/数据科学任务(crypto、编译器、qemu/MIPS、torch/ML、sqlite、git、LaTeX、COBOL 等)。
- 上游 = Harbor Hub dataset `terminal-bench/terminal-bench-2-1`(相对 2.0 修了 26 个 task)。leaderboard 协议 = Terminus-2 agent + pass@1(3 次平均)。
- 每个 task 目录自带:`task.yaml`(instruction+`parser_name: pytest`+timeout)、`docker-compose.yaml`、`solution.sh`(oracle 参考解)、`run-tests.sh`、`tests/`、`Dockerfile`。

### 镜像
- **本地 tag**:`tb2-offline/<task>:20260425`,以及闭包修复版 `:20260425-closure-r1/-r2/-r7`(**跑分用 closure 版**,不是裸 `20260425`)。KVM 上已就位。
- **Harbor**:`100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-<task>`(多 tag)。
- **闭包镜像是"离线自洽"的**:pytest 8.4.1 已 baked 进 `/opt/tb21-offline-verifier/site/`;`apt-get` 被 shim 拦截(`update`→exit0;`install` 非白名单包→非零 → 触发 `set -e`)。→ **裸 `solution.sh` 里若 `apt-get install grep/coreutils` 会在离线镜像下中止**;跑分数据集 `-full89-r7-final` 已把这些 `solution.sh` **patch 成离线干净**(去掉 apt-get)。
- **离线 tar**(每个 `.tar` 带 `.sha256`):
  - `$B/swe/bench/terminalbench2.1/prebuilt-images/20260425/`(51 个 base tar)
  - `$B/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/offline-e2e-r*/`(增量修复批)
- **per-task digest**:有(`terminal_bench_2_1.yaml` 记 `image_ref @sha256:...`;`dataset.toml` 记 89 个 task-content digest)。

### 拉取
```bash
# 在线 pull-by-digest(ref+digest 取自 terminal_bench_2_1.yaml;daemon 需 --insecure-registry 100.97.118.137:8555)
docker pull 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-multi-source-data-merger@sha256:80420107291d5c86fcf37d3c4abfef5ef8be6de086f11a8601a30855b3aa6bf9

# 离线 load(带 sha256 sidecar)
docker load -i $B/nips2026/agentic-foundation-model-bench/images/terminalbench2.1/offline-e2e-r71p0-flat/multi-source-data-merger.tar
```

### ★跑一个 task 端到端(manual-oracle,零模型)— 本 agent 真验过

> ⚠️ **本 KVM 上共享盘的 tb CLI venv 是坏的**(`.venv/bin/python3: bad interpreter: No such file or directory`;canonical 跑分在 jvm9z worker 上跑)。
> 所以给别的项目的**可移植**跑法是下面这个「纯 docker + task 自带 solution/tests」的 manual-oracle:**不依赖 terminal-bench CLI**,只用 docker + 闭包镜像 + 数据集里的 `solution.sh`/`run-tests.sh`。judging 的 reward 信号与 tb harness 同源(都是那套 pytest)。

```bash
B=/mnt/shared-storage-user/mineru2-shared/zengweijun
# 用 r7-final 数据集(solution/run-tests 已 patch 成离线干净),配 closure-r2 镜像
DS=$B/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703/log-summary-date-ranges
IMG=tb2-offline/log-summary-date-ranges:20260425-closure-r2
C=tb_oracle_verify

docker rm -f $C >/dev/null 2>&1
docker run -d --name $C --network none -w /app $IMG sleep infinity      # 起 task 容器(离线,network none)
docker exec $C mkdir -p /tests /logs/verifier
docker cp $DS/solution.sh   $C:/solution.sh
docker cp $DS/run-tests.sh  $C:/run-tests.sh
docker cp $DS/tests/.       $C:/tests/
docker exec $C bash -lc 'chmod +x /solution.sh /run-tests.sh; /solution.sh'   # 跑 oracle 参考解 → 生成 /app/summary.csv
docker exec -w /app $C bash -lc '/run-tests.sh'                               # 跑 task 自带 pytest → 写 reward.txt
docker exec $C cat /logs/verifier/reward.txt                                  # 读 verdict(1=pass)
docker rm -f $C                                                               # 用完删
```

**真实验证输出(2026-07-12,`--network none`,零模型):**
```
# solution.sh → /app/summary.csv 16 行(header+15 行真实计数):
period,severity,count
today,ERROR,370
today,WARNING,463
today,INFO,1433
...
# run-tests.sh(python3 -m pytest,baked 离线):
platform linux -- Python 3.13.7, pytest-8.4.1, pluggy-1.6.0
collected 2 items
../tests/test_outputs.py ..                                              [100%]
PASSED ../tests/test_outputs.py::test_summary_file_exists
PASSED ../tests/test_outputs.py::test_summary_structure_and_counts
============================== 2 passed in 0.29s ===============================
# 最终 verdict:
reward=1
```

### 判分
- **manual-oracle 的 reward**:`run-tests.sh` 跑 `python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py`,rc==0 则 `echo 1 > /logs/verifier/reward.txt`,否则 0。→ **reward 从 `/logs/verifier/reward.txt`(0/1)读**,细节在 `/logs/verifier/ctrf.json`。
- **canonical tb harness 的 reward**:`tb run` 产 `<TB_ROOT>/runs/<run_id>/results.json`,per-task verdict 字段 = **`is_resolved`(bool)**,顶层有 `n_resolved`/`accuracy`/`resolved_ids`。两条路都源自 task 的同一套 pytest。
- **canonical harness 跑法(需可用的 tb venv;本 KVM 的坏了)**:
  ```
  TB_AGENT=oracle scripts/run_terminal_bench_2_1_smoke.sh --execute --load-image --task-id <task>
  # 或全 89 privileged runner(所有真跑分走这条,注入 /dev/kvm + oracle mount 守卫):
  TB21_ALLOW_PRIVILEGED_DOCKER=1 DOCKER_HOST=unix:///var/run/docker.sock \
    bash .worktrees/tb21-image-fixes-r3/scripts/run_terminal_bench_2_1_full89_batched_privileged_offline.sh
  ```

### 验证状态(诚实)
- **transport → worker**:89/89(`preheat_present:89`,`preheat_tar_verified:89`)。
- **manual-oracle 端到端**:✅ **本 agent 2026-07-12 在本 KVM 真跑过 1 个 task**(`log-summary-date-ranges`,reward=1,2/2 pytest 过,`--network none`)。
- **canonical oracle(tb harness,gold 无模型)**:84/89(jvm9z worker,mount-race 修正后;残 5 = compile-compcert / feal-differential / configure-git-webserver / git-multibranch / make-doom-for-mips)。**本 KVM 未复现**(tb venv 坏)。
- **模型跑分**:gpt-5.5-medium pass@1 单次 = 63/89 → 校正 **70.8%**(canonical);gpt-5.4-mini xhigh = 9/89(timeout 为主)。官方锚 GPT-5.5-medium 78.2%(e2b,5 次均)≠ 我们的 privileged/fuse-overlayfs sandbox 单次采样。
- **★分清**:transport 89/89 ≠ 端到端;canonical oracle 84/89 在 jvm9z 上;本文档 copy-paste 的 manual-oracle 只在**本 KVM 亲验 1 个 task**。

### 事实来源路径
- task 目录:`$B/nips2026/shared_bench/terminal-bench-2.1-yaml/<task>/`(base)与 `...-yaml-full89-r7-final-20260703/<task>/`(跑分用,solution 已 patch)
- 闭包镜像内:`/opt/tb21-offline-verifier/site/`(baked pytest)、`/usr/local/bin/apt-get`(offline shim)
- smoke wrapper:`repo/scripts/run_terminal_bench_2_1_smoke_privileged.sh`;shared runner `$B/swe/bench/shared/runners/run_terminal_bench_2_1.sh`
- manifest:`repo/manifests/images/terminal_bench_2_1.yaml`、`tb21_prebuilt_image_map_full89_closure_r2.json`
- 分数:`repo/reports/scores/tb21_gpt55_official_20260705.{json,md}`;canonical oracle `repo/_coordination/20260625_harbor_bench/reports/tb21_canonical_final_verdict_84of89_20260704.md`

---

## 现在能不能给别人 copy-paste 跑通?

| Bench | copy-paste 现状 | 还缺什么 |
|---|---|---|
| **SWE-V** | ✅ **能**。gold-oracle 命令本 agent 亲验(resolved:true)。别的项目只需:共享盘 swebench env + HF 缓存 + 本地 `swebench/*` 镜像。 | 换模型打分要接 serving + prediction.json(生产 orchestrator 已有);离线 chunk→instance 映射查 p0 manifest。 |
| **TB2.1** | ✅ **能(manual-oracle 路径)**。纯 docker + r7-final 数据集 solution/tests + closure 镜像,本 agent 亲验(reward=1)。 | 完整 tb-harness(`tb run`)路径需要**可用的 terminal-bench venv**(本 KVM 的坏了,canonical 在 jvm9z);要复现官方 leaderboard 数需 terminus-2 + 模型 + e2b(非本仓 sandbox)。 |
