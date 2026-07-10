# 对抗式签核报告 — SWE-bench Verified · Qwen3-30B-A3B-Instruct-2507

- **审计对象 run_root**: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_qwencode_full500_poda_20260709t183239z`
- **serving 宿主**: `slime-96879589-667jv.zengweijun+root.ailab-sciverseh.pod@h.pjlab.org.cn`（sglang :30000）
- **审计执行宿主（run_root/编排所在）**: `env-kvm-15238487-rlgbn...pod@h.pjlab.org.cn`
- **bench**: SWE-bench Verified (500) · **harness**: qwen-code 0.15.6, c=16, attempts=1
- **审计日期**: 2026-07-10 · **模式**: 只读（无 commit/kill/rm/重启/改 run_root；无 key 落盘/落屏）
- **审计人**: Claude Opus 4.8（对抗式签核）

## 结论总表

| # | 攻击线 | 判定 |
|---|--------|------|
| 1 | 137 个 `no_patch` 是模型能力还是脚手架/协议问题 | **REFUTED**（脚手架说被驳倒；是模型行为） |
| 2 | 107 个 resolved 是否真实 | **CONFIRMED**（真实） |
| 3 | 2 个被丢弃 instance + `append_score` bug | **CONFIRMED**（编排者说法属实，缺陷只少记不多记） |
| 4 | eval 是否真跑了 | **CONFIRMED**（真跑，42,456 次测试执行） |
| 5 | 模型身份是否为 Instruct-2507 | **CONFIRMED**（不是 Coder） |
| 6 | 留档合规 + 是否泄漏密钥 | **CONFIRMED**（已脱敏，按值扫 0 命中） |

**诚实口径 `108/500 = 21.6%`；保守口径 `107/500 = 21.4%`；`107/498 = 21.49%` 不可引用（分母被 bug 缩水 2 个）。**

参照锚：nebius base Instruct-2507 ≈ **25.7%**；同日同 bench 同 harness 同 serving 宿主 Coder-30B = **242/500 = 48.4%**（no_patch 仅 3）。

---

## 账目独立复算（全量）

`results.jsonl` 498 行 / 498 unique / 0 dup；`sha256 = 49b1f5f41e492eae2a39b869308fbc698a71d6972d34eb7a9633c754f8bafe98`（**我在 disk 上独立 `sha256sum` 精确复现**，且等于 `ledger_summary.json` 与 `SHA256SUMS` 记录值）。

- `agent_status`: no_patch=137, patch=361
- `resolved`: True=107, False=391
- `eval_rc`: 498/498 全 0 · `agent_attempts`: 498/498 全 1
- 交叉表 `(agent_status, resolved)`: `(no_patch,False)=137`, `(patch,False)=254`, `(patch,True)=107`
- **107 个 resolved 全部来自 patch 行；no_patch 行 resolved=True 的数量 = 0**

---

## 攻击线 1 ★★ — 137 个 `no_patch`：模型能力 vs 脚手架/协议 → **REFUTED**

**方法**：写脚本遍历**全部 137** 个 no_patch 的 `evidence_dir/agent/qwen_attempt_1.stdout.jsonl`，在**正确的层**计数工具事件——遍历每行 JSON，对 `type=="assistant"` 取 `message.content[]` 中 `type=="tool_use"`，对 `type=="user"` 取 `message.content[]` 中 `type=="tool_result"`（**非**顶层 `tool_calls`/`function_call`）。这是**普查，不是抽样**。全部 137 个 `prediction.patch.diff` 均为 0 字节。

### 分类（编排者口径 a–e，普查，∑=137）

| 类 | 定义 | 计数 | 性质 |
|---|------|-----:|------|
| **(a)** | 零工具调用（协议/解析失败） | **0** | — |
| **(b)** | 有工具调用但没产出 diff（探索无果 / edit 反复失败 / 放弃） | **94** | 模型行为 |
| **(c)** | rollout/请求超时 | **13** | 8 wall-clock + 5 请求级 |
| **(d)** | 崩溃 / API 错误（HTTP 400，上下文自撑爆 @ ~228K tokens） | **30** | 模型行为 |
| **(e)** | 主动判定无需改动 | **0** | — |
| | **合计** | **137** | ✓ |

> **关于 (a)=0 的澄清**：按“字面零工具调用”统计确有 **2** 例（`pytest-dev__pytest-5787`、`pytest-dev__pytest-5809`），但二者的终态都是**第 1 轮就 `[API Error: Request timeout after 483s]`**——是 serving 延迟超时，**不是** parser 读不出模型输出。真正的“协议/解析失败”（qwen parser 无法解析模型输出）= **0**。故按根因将这 2 例归入 (c) 超时。全语料共产生数千个合法 `tool_use` 事件 + 361 个成功 patch，证明 `tool_call_parser=qwen` 对 Instruct-2507 完全可用。

### 按根因归并
- **模型行为 = (b)94 + (c)中 wall-clock 超时 8 + (d)30 = 132（96.4%）**
- **serving 延迟（请求级 483s 超时）= 5（3.6%）**
- **协议/解析失败 = 0（0%）**

### 关键机制证据（路径 + 计数）
- `instances/django_u_django-15930/agent/qwen_attempt_1.stdout.jsonl`：**grep_search ×1072 + read_file ×263 + edit ×0**，1343 turns，context 涨到 **229,337** tokens → `[API Error: 400 status code (no body)]`。无收敛的搜索循环。
- `instances/django_u_django-10999/agent/qwen_attempt_1.stdout.jsonl`：**edit ×6，6 个 tool_result 全 `is_error=true`** → 模型 6 次改都没匹配上 `old_string`，放弃。
- `instances/django_u_django-14608/agent/qwen_attempt_1.stdout.jsonl`：**read_file ×982 + edit ×3（全 err）**，993 turns，clean exit 无 diff。极端循环。
- `instances/astropy_u_astropy-14539/agent/qwencode_attempt_1.log`：read_file ×46 + edit ×0，input_tokens 逐步 205K→226K，最后一次 `read_file column.py offset=739 limit=2013`（读整文件）后下一次请求 400。
- **30 个 400 全部聚集在 224K–229K tokens（median 228,697）**，serving `context_length=262144`。是**上下文触顶**，不是低 token 的畸形请求（畸形请求会散布在各 token 量级）。
- 8 个 no-result：7/8 的 `qwencode_attempt_1.log` 带 `qwen_timeout` 标记（编排器 `TimeoutExpired` 分支 line 744 `add_log("qwen_timeout",...)`），stderr 43 字节 = `[v2-qwencode] ROLLOUT_TIMEOUT after 3000s`。即模型在 **3000s（50 分钟）** 墙钟预算内绕圈被杀。

### 配置无不利偏差（回应“45× no_patch 差距”）
两 run 逐项对比（`runner_config.json` + `launch_full500.sh` + orchestrator 默认 line 1265/1250/1251/1255）：

| 项 | Instruct-2507 | Coder-30B |
|---|---|---|
| rollout_timeout | **3000s**（默认，未设 SWEV_ROLLOUT_TIMEOUT） | **3000s**（同上） |
| context_limit | 262144 | 262144 |
| max_output_tokens | 65536 | 65536 |
| qwen_max_session_turns | -1 | -1 |
| qwen_code_version | 0.15.6 | 0.15.6 |
| concurrency | **16** | 20 |

除并发外**逐项一致**；Instruct 用**更低**并发（16<20），serving 竞争更小，**对 Instruct 更有利**。→ **没有任何不利偏差能解释 45× 的 no_patch 差距；差距来自模型**（弱于 agentic 收敛：读整文件/狂 grep 撑爆上下文、edit 无法命中）。

**判定：REFUTED。** “21.6% 是脚手架分”被驳倒。no_patch 96.4% 是模型行为，协议/解析失败 0%。脚手架（工具、parser、eval）工作正常；瓶颈是模型。附带效应：no_patch 全部 unresolved，脚手架相关因素（无 compaction、5 例 serving 超时）**只会压低、不会抬高**分数 ⇒ 21.6% 是偏保守的能力下界。

---

## 攻击线 2 — 107 个 resolved 是否真实 → **CONFIRMED**

- 全 107 个 `prediction.json` 的 `model_patch` 非空；**空 patch 却 resolved 的 = 0**。
- **107 个 resolved 的 patch 触碰测试文件的 = 0**（用 diff 头 `diff --git a/… b/…` 解析路径，匹配 `tests?/`、`test_*.py`、`conftest.py` 等）——模型连碰测试都没碰，全是改非测试源码。
- 抽样 `astropy__astropy-7336`：patch 改 `astropy/units/decorators.py`（源码），detailed `report.json` = `patch_successfully_applied:true, resolved:true`，FAIL_TO_PASS 1/0，PASS_TO_PASS ~340/0。
- **测试重置保护在位**：`eval.sh:384-385` 先 `git checkout <base> <testfiles>` 再 `git apply` gold test_patch —— 即便模型改了测试也会被官方 gold 覆盖（本 run 无此情形）。
- resolved 取自官方 `resolved_ids`：orchestrator `run_eval` line 893 `resolved = spec.instance_id in set((report or {}).get("resolved_ids", []))`。

---

## 攻击线 3 — 2 个被丢弃 instance + `append_score` bug → **CONFIRMED**

`events.jsonl` 两条 `infra_error, stage=eval, "official eval returned nonzero", rc=1`：`django__django-12050`、`matplotlib__matplotlib-23299`。

- **两者栈顶同一竞态**：`eval.log` 尾 `docker.errors.NotFound: 404 ... No such container`，位于 `swebench/harness/reporting.py:107 make_run_report → client.containers.list(all=True)`——**测试跑完后的清理竞态**，非执行失败。
- **`django-12050` 是真解**：`failed/django_u_django-12050/eval/logs/run_evaluation/.../report.json` = `resolved:true`，FAIL_TO_PASS `test_iterable_lookup_value` 1/0，PASS_TO_PASS 10/0；`prediction.json` 的 patch 649B 改 `django/db/models/sql/query.py`（源码）。→ 被 bug 丢掉的是一个**真 resolve**。
- **`matplotlib-23299`（穷尽搜索）**：`prediction.json` 的 `model_patch=""`（空）；`find failed/matplotlib_u_matplotlib-23299 -name report.json -o -name test_output.txt` → **无任何输出**。确无 report.json/test_output.txt ⇒ 空 patch 判未解决**正确**。
- **bug 定位**：orchestrator `pipeline()` line 912–915（agent `infra_error`）与 line 918–921（`eval_error`）两分支均 `preserve_failure` + `append_event` 后 **`return`，不调用 `append_score_once`**；只有成功路径 line 939 `append_score_once(result)`。⇒ 500→498 行，且丢掉 django 的真 resolve。

(a) 编排者三项说法均属实。(b) matplotlib 确无 report（穷尽 find 已列）。(c) 缺陷**只在失败路径丢行**，只能少记不能多记；丢的要么未解决（matplotlib），要么本应 +1（django-12050）⇒ **诚实 108/500=21.6%，保守 107/500=21.4%，107/498 不可引用**。

---

## 攻击线 4 — eval 是否真跑 → **CONFIRMED**

- 遍历各 instance 的 detailed `report.json` 求和：**FAIL_TO_PASS 201 通过 / 346 失败；PASS_TO_PASS 38,340 通过 / 3,569 失败；合计 42,456 次单测执行**（跨 333 份 detailed report）。远大于 0。
- **ledger 的 107 resolved 集合 == detailed report `resolved:true` 集合，symdiff = ∅**；`resolved-but-no-report=0`，`resolved-but-zero-F2P=0`。
- eval 命令：`-d princeton-nlp/SWE-bench_Verified -s test`（orchestrator `run_eval`），resolved 源自官方 `resolved_ids`（line 893）。
- 165 个无 detailed report 的 instance（137 no_patch 空 patch + 28 patch 未应用/未解决）**全部 unresolved** ⇒ `eval_rc=0` 未在“测试没跑”时造出任何假 resolve（已知 docker exit-125 坑未触发）。

---

## 攻击线 5 — 模型身份 → **CONFIRMED（Instruct-2507，非 Coder）**

- **before/after 一致**：`serving/get_model_info_{before,after}.json` 两份 sha256 相同（`d87bcf86…`），`model_path=/mnt/.../models/Qwen3-30B-A3B-Instruct-2507`；`get_server_info_{before,after}.json` `served_model_name=Qwen/Qwen3-30B-A3B-Instruct-2507`，`context_length=262144`，`tp_size=2`，sglang `0.5.13`。
- **对活进程核**：serving 宿主 `ps` PID **668** = `python -m sglang.launch_server --model-path /mnt/.../models/Qwen3-30B-A3B-Instruct-2507 --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 --tp-size 2 --port 30000 --tool-call-parser qwen`；**Coder-30B 隔离在 `--port 30001 --tool-call-parser qwen3_coder`（GPU 6,7）**。`:30000` 上**唯一** LISTEN = PID 668。run 的 `base_url=…:30000` ⇒ 必打 Instruct-2507 权重。
- **覆盖整窗 + 无重启**：serving 宿主时区 = UTC；`/tmp/sgl_instruct.log:6` server_args `model_path=Instruct-2507, api_key=None`，启动 08:24:33Z（远早于 run 18:32Z），全 log **无 traceback/OOM/killed/SIGTERM/restart** 标记，单 PID 持续至今（覆盖 18:32→23:39Z）。
- **run 内连续探针**：`disk_identity_monitor.py` 每 600s 打 `/get_model_info` 并在 model_path 不含 `Qwen3-30B-A3B-Instruct-2507` 时写 STOP；`monitor/disk_identity_*.json` **31 份快照（18:36:31Z→23:36:33Z）全部 model_path=Instruct-2507，model_error=""**。
- **注意（诚实标注）**：两模型 `config.json` 架构字段完全相同（同属 Qwen3-30B-A3B MoE），故 config 不足以区分权重；身份结论建立在“独立端口/进程/parser + 31 次连续探针 + 行为签名 21.6%↔Coder 48.4%”。若 :30000 偷跑 Coder 权重，结果会像 Coder（~48%、极少 no_patch），而实测是典型 Instruct（21.6%、137 no_patch）。

---

## 攻击线 6 — 留档合规 + 密钥 → **CONFIRMED**

- `serving/*.json` 中 `api_key`/`admin_api_key`/`ssl_keyfile_password` 均 `<redacted>`（`capture_serving_info.py` 按键名脱敏，偏保守/过度脱敏，但目标密钥字段确已盖住）。
- **按值独立扫密**（`sk-`/`hf_`/`Bearer`/JWT/≥40 hex/≥32 字母数字，遍历 serving/*.json + launch.env + runner_config.json）：**0 命中**。且服务本身无鉴权（启动日志 `api_key=None`，`launch_full500.sh` `OPENAI_API_KEY=EMPTY`）——**本就无 key 可泄**。
- `SHA256SUMS`（9 项）`sha256sum -c` 全 **OK**；`SHA256SUMS.prelaunch`（6 项）全 **OK**；results.jsonl 哈希精确复现。覆盖关键产物（results/日志/serving 快照/压测摘要/脚本）。

---

## 最有杀伤力的 3 条证据

1. **模型身份为真**（关最危险的伪造向量）：serving 宿主 `ps` PID 668 = `sglang.launch_server --model-path …/Qwen3-30B-A3B-Instruct-2507 --port 30000 --tool-call-parser qwen`，Coder 隔离于 `--port 30001 --tool-call-parser qwen3_coder`；`:30000` 唯一 listener=668；`monitor/disk_identity_*.json` 31 份快照全 Instruct-2507。
2. **no_patch 是模型行为非脚手架**（破核心攻击）：`instances/django_u_django-15930/agent/qwen_attempt_1.stdout.jsonl` = grep_search×1072 + read_file×263 + **edit×0** → 229,337 tokens → `[API Error: 400 no body]`；`instances/django_u_django-10999/…` = edit×6 全 `is_error=true`。对照 361 个成功 patch 证明 edit 工具可用、137 个中协议/解析失败=0。
3. **eval 真跑 + resolved 真实 + 可复现**：42,456 次单测执行；ledger 的 107 resolved == 官方 `resolved_ids` 集合（symdiff ∅）；0 空 patch resolved、0 触测试 resolved；orchestrator line 893 取 `resolved_ids`；`eval.sh:384-385` gold-test 重置；`sha256sum results.jsonl` = `49b1f5f4…` 精确匹配。

---

## 一句话结论

> 我**愿意背书**：该 run 的 `resolved/total` 反映了 **Instruct-2507 的真实 agentic coding 能力**——诚实口径 **108/500 = 21.6%**（保守 107/500 = 21.4%，**不是** 107/498）。137 个 no_patch 经**全量普查**为 96.4% 模型行为、0% 协议/解析失败；eval 真跑（42,456 次单测）、resolved 真实（==官方 resolved_ids）、模型确为 Instruct-2507（非 Coder）、留档合规无密钥泄漏；已知的 `append_score` 缺陷与无-compaction 上下文触顶等脚手架因素**只会压低、绝不抬高**分数,故 21.6% 是可引用的、偏保守的能力真值。

**背书。**

---

### 附：需修复/声明（不阻断背书）
1. `append_score` bug（orchestrator line 912–921）应修：eval 清理竞态失败仍应落分。当前丢了 `django-12050` 一个真 resolve ⇒ 对外报 **108/500=21.6%**（从其 detailed report.json 恢复），**严禁引用 107/498**。
2. 30 个上下文触顶 400 + 8 个 rollout 超时：可考虑开启 qwen-code compaction 或加“触顶前强制 submit”，以减少保守低估（属产出率优化，非正确性问题）。
3. 5 例请求级 483s serving 超时（c=16 下）：轻微 infra 因素，最多影响 1%。
