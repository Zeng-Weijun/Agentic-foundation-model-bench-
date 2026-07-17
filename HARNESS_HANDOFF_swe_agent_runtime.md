# 交接文档:让 swe-agent-runtime 原生 rollout+export 全部 bench

> **给谁看**:swe-agent-runtime 的实施 agent。
> **来源**:3 方独立分析三角对齐 —— Claude 读码 + 真 codex-pro(gpt-5.6-sol)读码 + 在 KVM 上用中转站 gpt-5.5 **真跑实测**。标注 `【实测】`=真跑证实,`【读码】`=源码推断。
> **基准**:swe-agent-runtime `main` ≈ 091fa95 / 1a41b11(以你 clone 到的 HEAD 为准)。

---

## 0. 目标与范围(先读)

- **harness 只做两件事:rollout(跑 agent) + 导出轨迹/产物**。**verifier / reward / 判分一律不做** —— 那在数据工厂 / 训练侧做。
- 要能对 8 个 bench 的 task **原生** rollout+export,像 Claude Code / Codex 一样:**给一个镜像 + 镜像里烤好的工作区 + 一句任务说明,就在里面跑,然后把轨迹和最终产物导出**。考场(起始工作区)都烤在各 bench 镜像里,harness 不"布置考场"。
- 8 个 bench 的工作区形状:SWE-V/Multilingual/DeepSWE/SWE-bench-Pro = repo(SWE-V 在 `/testbed`);RepoZero = `/workspace` 里待翻译源码;NL2Repo = `/workspace` 清空 + 只 `start.md`;ProgramBench = `/workspace` = docs + 黑盒 executable(无源码);TB2.1 = docker-compose 多服务。

---

## 1. 关键定位(避免走错路)★

- ★**所有改动打在 `src/swe_agent_runtime/autodata/`**(`run_autodata_task` + `TaskEnvelope`,schema `autodata.task_envelope.v1`)—— 这是真正的数据工厂 seam(通用、从不打分、已有整树导出)。
- ★**不要碰 legacy `src/autoswe_workbench/swebench_harness.py`** —— SWE-bench 专用、`reset_task_workspace` 还联网 `pip install`(与"离线/harness-无关"背道而驰),是要被取代的旧路径。SWE-bench 也表达成一个 envelope 走 autodata,别再 per-bench 扩它。
- ★**不要加 verifier/reward** —— 已历史删除(commits `cdbc808`/`2534cb1`/`5e3d065`),`reward_contract` 是 envelope 里一个可选块、runner 完全忽略。**别重加**。
- ★**不要"跳过 bind-mount / 把 host_root 改可选不挂载"** —— 这是**错的方向**。Workspace 的 read/write/diff/secret-scan 是**宿主机 FS 操作**(`env/docker.py:499-511`、`workspace/workspace.py:263-290`),靠 host_root 1:1 bind-mount 到 container_root 才和容器里的 bash 对齐。不挂载会弄瞎 edit/read 工具、丢掉所有 bash 改动。**正确做法是"把镜像工作区抽取到宿主目录，再走现有 mount"(见 C1+C2)。**
- ★**别信 `README.md` / `AGENTS.md`** —— 已 drift(还写着删掉的 `run_tests`/`submit` 工具、引用不存在的 doc)。以 `docs/decisions/ADR-000*.md` + 直接读源码为准。

---

## 2. 已经做好、别动的(3 方确认)

| 能力 | 证据 |
|---|---|
| 声明式非-repo provisioning | `_copy_repo_snapshot` = `shutil.copytree(任意目录, symlinks=True)`,不要 git。【实测】只含 `start.md` 的空工作区(NL2Repo 式)照样正确铺好 |
| 整树导出(091fa95) | `expected_output_kind="workspace_state"` → `workspace_manifest.json`(path→{status,content_hash 真实字节 sha256,mode,is_symlink})+ patch.diff;`artifacts/workspace` 无条件导出完整树 + checksum。【实测】从零建 `greet/` 包 + submit → 导出可完整重建 submission |
| container_root 可覆盖 | `autodata/runner.py:823` `_resolve_container_root` 读 `interaction_contract.metadata["workspace_dir"]`(默认 `/workspace`),无 bench 分支,已测(T5) |
| 通用 prompt | `envelope.problem_statement_text` + `interaction_contract.system_prompt` 直进 loop,无 bench 模板 |
| 无 verifier/reward | 见 §1;runner 出 rollout bundle、defer 判分 |
| 6 工具无 git 耦合 | loop 按 `sandbox_tier=="container"` 能力门控(非 `isinstance(DockerEnv)`);无 git 依赖 |

**结论:你之前担心的"非-repo provisioning + 整树导出"其实都做好了。真正要动的见 §3。**

---

## 3. 要做的改动(按优先级)

### 🔴 P0 — 2 个当下就挡真 rollout 的 bug(【实测】撞到,不修啥都跑不起来)

**P0-1 `edit` 工具致命崩溃**
- **现象【实测】**:gpt-5.x 类模型爱**同时塞满 `content` + `edits` + `rename_to` 三个字段**。`tools/core.py` 对"非恰好一个字段"回 `error_code="invalid_file_mode"`,但**该值不在 `ToolResult.error_code` 枚举里** → pydantic `ValidationError` → **整个 rollout 被判 env 层错误、`rollout_executed=False` 直接崩**(第一条 edit 就挂)。**后果:gpt-5.x 类模型现在无法通过 harness 完成任何 edit。**
- **改**:(a) 把 `invalid_file_mode` 加进 `ToolResult.error_code` 允许枚举;(b) 更稳:学 `registry.py` 已有的"模型过度填充自动归一"——当 content+edits/rename_to 同时出现时按优先级归一成一个合法 edit,而非报错崩溃。
- **位置**:`src/swe_agent_runtime/tools/core.py`(edit 工具的字段校验 + error_code 枚举)。

**P0-2 `--storage-opt size=10g` 不可移植**
- **现象【实测】**:`DockerEnv` 默认 `disk_size="10g"` → `docker create --storage-opt size=10g`。overlay2 无 pquota 的 docker(如 KVM)直接 `Error response from daemon: --storage-opt is not supported` → **首次 bash/容器 exec 必挂**(`DockerCommandError`),且 runner 路径**没有 env/envelope 旋钮能覆盖**(只能改源码)。edit/read 走宿主 FS 不受影响,但 **bash 全废**。
- **改**:给 `disk_size` 加 envelope/env 旋钮,或探测 docker 是否支持 `--storage-opt` 再决定加不加(不支持就跳过)。默认值改成可关。
- **位置**:`src/swe_agent_runtime/env/docker.py`(`DockerContainerSpec.disk_size` / `create_container` 的 `--storage-opt`)。

> ★这两个必须先修,否则拿任何 bench 都跑不起来(edit 崩 + bash 废)。

---

### 🟠 P1 — extract-from-image:让"镜像自带工作区"原生可用(C1+C2)

> **★先查在建的**:这个修复**已经有人在 `swe_dev:.worktrees/wt-tier2`(base 091fa95,未合并)上做了**。**先确认它 merge 没 / 改没 / 弃没**,别重复造轮子。若还开着,合并前补下面 2 个洞。

- **C1**:`autodata/contracts.py` 的 `TaskMaterials.repo_snapshot_ref` 从**必填**改**可选**(`Any | None = None`);`TaskEnvelope.repo_snapshot_path` 在 ref 缺失时返回 `None` 而非 raise。
- **C2 ★核心**:`autodata/runner.py:~221` 分支:
  - `repo_snapshot_ref is not None` → 保持 `_copy_repo_snapshot(...)`(SWE-bench/host-snapshot 路径,字节不变)。
  - `else`(镜像自带工作区)→ 新 `_extract_workspace_from_image(docker_client, image_ref, container_root, workspace_root)`:`docker create <镜像> true` → `docker cp <容器>:<container_root>/. <workspace_root>/` → `docker rm -f`(try/finally)—— **在构造 DockerEnv 之前**把工作区灌进宿主挂载点。之后现有 mount → `mark_base()` → loop → 导出**一字不改**。
  - `SubprocessDockerClient` 现在**没有 `cp`、也没有"裸 create"**(`create_container` 总注入 `--volume`+`sleep infinity`),需在 `DockerClient` Protocol + `SubprocessDockerClient` 加 `copy_from_image(image, src_path, host_dest)`。
- **合并前必补的 2 洞(codex 挖到)**:
  - **[洞1]** `repo_snapshot_ref is None` 时**强制要求 `metadata["workspace_dir"]`(缺就 raise)**,别静默回退 `/workspace`(否则 `docker cp` 可能 cp 到错的/空的目录还不报错)。
  - **[洞2]** extract 用的临时容器**加上 owner labels**(和 `DockerEnv._container_labels()` 一样),否则进程中途死在 create 和 rm 之间时,orphan reaper 清不掉(reaper 的无标签 fallback 明确排除 `created` 态容器)。
- ⚠️ **注意(【实测】给的退路)**:**现在就有能跑的路** —— 你**自己把镜像工作区抽到一个宿主目录**、当 `repo_snapshot_ref` 传进去,harness **今天就能** rollout+export(非-repo 也验证过)。所以 **C1+C2 是"把抽取搬进 harness 做得更原生",不是硬阻塞** —— 若 wt-tier2 没就绪,可先用"外部预抽取 → host snapshot"路子跑起来。

---

### 🟠 P1 — C3:容器 exec 的 PATH 继承镜像(SWE-bench conda 必需)

- **现象**:每个 `docker exec` 跑 `env -i … PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`(`env/docker.py:40` `DEFAULT_CONTAINER_PATH` + `:829` `_container_exec_env`),忽略镜像自带 PATH。SWE-bench `sweb.eval.*` 镜像的 python 只在 conda env `/opt/miniconda3/envs/testbed/bin`(不在这 PATH)→ agent 跑 `python -m pytest` 报 `python: not found`。且 `PATH` **不在** exec allowlist(`:85` `_ALLOWED_EXPLICIT_ENV_EXACT`)——想传都传不进。
- **改**:加 `container_path: str | None = None`(默认=现值,零回归),穿进 create 的 PID-1 env 和 `_container_exec_env` 的 base PATH。来源:`interaction_contract.metadata["container_path"]`(仿 `container_root` 的 `_resolve_container_path`),或**从 `docker image inspect --format '{{json .Config.Env}}' <image>` 自动取镜像自带 PATH**。保留凭据/代理 denylist。
- **位置**:`env/docker.py:40 / :213-256 / :829-838 / :85`。**在建的 extract diff 没管这块 —— 这是独立的、全开的 BLOCKER。**

---

### 🟡 P2 — TB2.1 compose 多服务(唯一真结构性缺口,需拍板)

- **现状(3 方一致)**:env backend 只有 Local/Docker/MicroVM,**全单容器/单 VM**;全仓 grep `compose` **零命中**;`DockerEnv` 只会**自建**容器,无"连到已存在容器"模式。
- **两条路**:
  - **(A)** 新增 compose-aware / "attach 到已存在容器 id" 的 `Environment` backend —— 真·大新工作,不在 minimal 内。
  - **(B)** **把多服务拍平进镜像构建期**(所有服务烤成一个镜像的后台进程,harness 保持 compose-无知)—— **只有 (B) 符合"零 per-bench 代码"**,但这是真实的、非平凡的每-task-family 工程,只是搬到 harness 之外。
- **→ 需要一个 go/no-go 决定。minimal spec 覆盖不了 TB2.1。**

---

## 4. 操作接线(真 rollout 必读,【实测】)

- 中转站 `colabapi.com:2053` 从 **KVM 和 dev 都直连不通**;只有 **dev 经 kubebrain 代理** `http://httpproxy-headless.kubebrain.svc.pjlab.local:3128` 能到。
- harness `autodata/routes.py` **硬校验 live model base_url**:只认 `127.0.0.1:18404/v1`(loopback bridge,端口硬编码 18404)或内网 IP 白名单;dev 的 IP 被判 public → 拒。
- **实测通法**:`KVM 127.0.0.1:18404 → dev:18406(harness 自带 `autodata/dev_openai_proxy.py` 起的 OpenAI-compat 转发器,urllib 走 kubebrain 到 colabapi)`;model key 从 `SAR_MODEL_API_KEY` 注入。跑真 rollout 照这个接线。
- runner 硬编码 `network_disabled=True`/`--network none`(离线 bench 正好),如某 bench 要联网是个旋钮。

---

## 5. 验收计划(改后跑哪个 bench 验哪条)

| 改动 | 验收 |
|---|---|
| **P0-1/P0-2** | 任意 1 个 task 能真 rollout:edit 不崩 + bash 能跑(容器 exec 不报 storage-opt)|
| **C1+C2** | **RepoZero** 真镜像 envelope `{image:<RepoZero pinned>, workspace_dir:/workspace, workspace_source:image, output_kind:workspace_state}`(不给 repo_snapshot_ref)→ agent 首个 `bash ls /workspace`/`read_file` 看到**镜像里烤的待翻译源码** → rollout → `artifacts/workspace` 含编辑后的树 + `workspace_manifest.json` 枚举改动 |
| **C3** | **SWE-bench** 真镜像 `{image:sweb.eval.x86_64.<id>, workspace_dir:/testbed, output_kind:patch, metadata.base_commit:<sha>}` → agent `python -m pytest` 的 conda python 能解析(现在会 `python: not found`);`final_submission/patch.diff` 是合法 `git diff base_commit` |
| **NL2Repo / ProgramBench** | `start.md` / `docs+黑盒 executable` 随整树自动 materialize,零特殊处理;`output_kind:workspace_state` 导出整树 |
| **TB2.1** | 待 go/no-go |

---

## 6. 要在真镜像上验的风险(A+B 都提;【读码/未实测】)

1. **secret-scan symlink 守卫**:`env/setup()` 对 materialize 出的树跑 `scan_host_root_for_secrets`;**绝对/逃逸 symlink 是 blocking**(即使 `trust_tier=public_benchmark` 也只降级凭据类,不降 symlink_escape)。SWE-bench `/testbed` 常有绝对 symlink → 可能 setup 硬 fail。**真镜像上先验**,必要时给 materialize 路径一个 scan 策略。
2. **SWE-bench `/testbed` HEAD ≠ `base_commit`**(harness 自述):`git diff base_commit` 只在 base_commit 是 materialize 出的 repo 里的祖先对象时有效,否则退化成内容快照 fallback。逐镜像验。
3. **materialize 盘开销**:`docker cp` 整树到宿主,每 task 复制一份;共享盘全树 stat walk 慢。盯磁盘。
4. **非-git 工作区二进制保真**:`workspace_manifest` 是文本-only(跳非 UTF-8),二进制改动**不按名枚举**,但 `artifacts/workspace` 整树 artifact 有完整字节 + checksum → **可重建,只是索引不列名**(自述 Tier-2 已知,MINOR)。

---

## 7. 一句话执行顺序

1. **先修 2 个 P0 bug**(`edit` 枚举崩溃 + `storage-opt`)—— 否则任何 bench 都跑不起来。
2. **查 `swe_dev:.worktrees/wt-tier2` 的 extract-from-image**,补 2 洞(`workspace_dir` 强制 + extract 容器 label)后合并;或先用"外部预抽取 → host snapshot"跑起来。
3. **补 C3 的 PATH 继承**(SWE-bench 必需)。
4. **TB2.1 拍板** go/no-go(走"拍平进镜像"或暂缓)。
5. 全打在 `autodata` 路径;verifier/reward 不碰;别跳过 bind-mount。
6. 按 §5 逐 bench 验收;§6 风险在真镜像上确认。

---

*本文档由 Claude(Opus)综合 3 方独立分析(Claude 读码 + 真 codex-pro 读码 + KVM 真跑实测)三角对齐产出。所有 `【实测】` 项在 KVM 上用中转站 gpt-5.5 真跑证实;`【读码】` 项标注为源码推断。*
