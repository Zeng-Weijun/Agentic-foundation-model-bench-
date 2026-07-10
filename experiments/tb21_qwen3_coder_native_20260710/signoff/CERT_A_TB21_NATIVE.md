# CERT A — TB2.1 native qwen-code full89 (第一签核人 · 对抗证伪)

- **run_id**: `tb21_native_qwencode0162_promptfixed_bridgefix_full89_c32_20260710t1002z`
- **run_root**: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_native_qwencode0162_promptfixed_bridgefix_full89_c32_20260710t1002z`
- **evidence bundle**: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_native_qwencode_full89/tb21_native_qwencode0162_promptfixed_bridgefix_full89_c32_20260710t1002z/`
- **声称分数**: 10/89 = 11.24% · failure_mode {'unset':89}
- **审计时刻(UTC)**: 2026-07-10 ~12:00Z · host `rjob-500d7b83e2ec7b38...` (Pod A) · 只读
- **判定**: **A. 有效,可引用**(六条全 CONFIRMED;含2处**不影响分数**的声明精度注记)

窗口:start_time `2026-07-10T10:03:19Z` → end_time `2026-07-10T10:21:31Z`(run_metadata.json)。commit `1a6ffa96`。

---

## 1. 容器内原生 vs 宿主机 bridge — **REFUTED(确为容器内原生)**
- 全 `run.log` **`docker exec` 计数 = 0**(bridge 唯一标志缺失)。
- 全 89 题 `commands.txt` 命令**打进容器 tmux 终端**,签名逐字相同:
  `qwen --channel CI --yolo --auth-type openai --output-format stream-json --prompt='...'`
  例:`.../build-pmars/build-pmars.1-of-1.<run_id>/commands.txt` 第5行。
- `panes/pre-agent.txt` = 容器 shell `root@6b38222bf9c0:/app#`。
- `docker-compose.yaml`(dataset `.../build-pmars/`): `.npm-root-0.16.2:/opt/qwen-native/.npm-root:ro` + `network_mode: bridge` + `image: tb2-offline/... pull_policy: never`。
- launcher(final_evidence.json `command`): `--agent-import-path scripts.tb21_native_qwencode_agent:NativeQwenCodeAgent`(原生类,非废弃 bridge `tb21_qwencode_agent.py`)。
- **全 89 题:`--allowed-tools`=0, `--exclude-tools`/`excludeTools`=0** → 全套原生工具无限制(与 bridge 单一 `run_tb_command` 相反)。
- 注:dataset 名里的 "sharedbridge" = Docker bridge 网络 + 共享 .npm-root bind,**不是** host-exec bridge。

## 2. leading-dash bug 是否真修 — **CONFIRMED(已修)**
- 全 89 题用 `--prompt=<value>`(带 `=`)形式 → dash 落在值内,argparse 不当 flag。
- 全 run 唯一 prompt 内容以 `- ` 开头者 = `pytorch-model-recovery`,现为 `--prompt='- You are given...'`;
  其 trial `results.json`:`agent_started 10:07:22 → agent_ended 10:13:56`(~6.5min),**30 tool_use**,`test_model_file_exists=passed`(agent 真产出 model.pt),因重建错误 unresolved(合法)。
- 上一次作废的 `..._clean_20260710t070319z`(SHA 6a242aff, status=blocked)正因此题 argv 破损;本 run 已修。

## 3. 分数 — **CONFIRMED 10/89**
- 独立重数 `results.json`:resolved=10 / 79 unresolved / **89 唯一题名**(无重复无缺失);metadata `accuracy=0.11235955=10/89` 精确;`dataset_size=89`。
- `failure_mode {unset:89}` = TB "正常完成"哨兵(agent 跑完+测试执行),**非"零错误"**。
- 清点全 89 agent.log:**`Error code:` 400/429/5xx=0,context_length_exceeded=0**。仅3题偶发 `[API Error: terminated (cause: Body Timeout Error)]`(build-pov-ray/make-mips-interpreter/protein-assembly,**均 unresolved**,只会压低分数)。
- ⚠️ 声明精度注记:final_evidence.json `llm_health.infra_class.read_timeout=0`,但上述3处 body-timeout 未计入;**不影响 10/89**。

## 4. trace 真实性 — **CONFIRMED(真)**
- 全 89 题 tool_use > 0(1~71 有机分布),**零假0**;总 **tool_use=2061 / tool_result=2061 完美配对**。
- 独立计数与编排者 `control/native_tool_events.json`(2061/2061, agent_log_count=89, status=pass)及 final_evidence.json `stream`(2061/2061)**逐字相符**。
- **10个 resolved 全真**:每题 `sessions/verifier/reward.txt=1` + `ctrf.json` 全 pass(fail=0) + parser_results 全 passed。
- **无测试篡改**:`/tests` 在 docker-compose 中为 **read_only bind**(10/10 resolved 已验 RO);唯一 tamper-regex 命中(build-cython-ext)是模型**评论文字**非写操作。

## 5. 模型身份 + serving — **CONFIRMED**
- `control/serving_config_{before,after}.json`(嵌 get_model_info/get_server_info):
  `model_path=/mnt/.../models/Qwen3-Coder-30B-A3B-Instruct`(前后一致),`served_model_name=Qwen/Qwen3-Coder-30B-A3B-Instruct`,`tokenizer_path=<redacted>`。
- **`random_seed=598954308` 前后完全相同** ⇒ sglang 进程全程未重启(比 model_path 硬一层)。
- `control/qwen_version_inside_container.txt` = **`0.16.2`**(容器内实测,非仅挂载路径)。
- `control/network_preflight.log`: sglang :30001 **HTTP 200** remote_ip=100.100.104.140;pypi **rc28 超时**;github **rc28 超时**(离线-除-sglang)。

## 6. 证据完整性 — **CONFIRMED**
- **复算** `final_evidence.json` SHA256 = `12195cc418edf3146f0290bdc571e925b641550cfe0311084debb9a27c3e8a1d` = **声称值逐字符相符**。
- `results.json` SHA=`9c932a26...`、`run_metadata.json` SHA=`53366f94...` 均与 `FINAL_SHA256SUMS` 相符。
- `find run_root -newermt "2026-07-10 18:21:32"` = **空** → run 结束后**无任一文件被改**(区别于 eval_wrap.py 就地改事故)。
- `.npm-root-0.16.2` mtime 13:11 CST、dataset 07-04 —— 均早于 run 起始 18:03。evidence bundle 18:25–18:37 CST 为**事后签名产物**(读 run,不改测量文件)。

---

## 判定:**A. 有效,可引用**
六条攻击线全部 CONFIRMED,10个 resolved 无假绿,SHA 复算相符,run 后零篡改,random_seed 前后一致。
本 run 是 **qwen-code 0.16.2 容器内原生、全工具无限制、Qwen3-Coder-30B-A3B-Instruct 真身、TB2.1 全89题** 的干净单跑,**10/89 = 11.24%** 可引用。

**声明精度注记(不影响分数,仅供记录)**:
1. `llm_health.read_timeout=0` 未计入3处 body-timeout 事件(所涉3题均 unresolved,只压低不抬高)。
2. `stream.qwen_result_success=88/89`(install-windows-3.11 有29工具调用但无终结 result 事件)—— 编排者已在 `effective_attempts.tool_backed_without_terminal_task_ids` **主动披露**,且该题本就 unresolved,不改分数。

参照系:terminus-2 官方 12/89、canonical 9/89、bridge 15/12/13。本 run 10/89 落在带宽内(非背书理由,判据是上述证据)。

— 第一签核人(对抗证伪已尽力,未能证伪)
