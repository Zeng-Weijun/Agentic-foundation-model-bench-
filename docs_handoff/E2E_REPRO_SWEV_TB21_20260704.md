# SWE-V + TB2.1 端到端离线复现命令包

> 交付对象:用户 / harness 测试团队 | 整理:bench 战役 85(by-85) | 日期:2026-07-04
> **本文只收敛已实测文档,不发明新流程。** 源文档(权威,冲突时以源为准):
> - `docs_handoff/SWEV_OFFLINE_DOCKER_USAGE_20260703.md`
> - `docs_handoff/TB21_OFFLINE_DOCKER_USAGE_20260703.md`
> - `repo/_coordination/20260625_harbor_bench/pod_b_bootstrap.sh`（pod bootstrap 可重跑配方）
> - `repo/scripts/run_terminal_bench_2_1_full89_offline.sh`（TB2.1 一键 runner）
>
> 共同前提:能访问共享盘 `/mnt/shared-storage-user/mineru2-shared/`;机器**无公网**也能完整跑通(这是本套资产的设计目标)。所有容器 `--network none` / compose 内网。
>
> ⚠ **SWE-V 入口即将切换**为 51 正在写的 **V2 runner**(去 shard + run-eval 串联 + c100)。V2 就绪后本文 §1.3 更新;当前记录的是 2026-07-03 实测入口。

---

## §0. 公共前置(两 bench 同一 Docker 运行时配方)

privileged Linux + root。**从本地 tmux 起,再 `ssh -CAXY <pod>`**(长跑防断)。一键脚本 `repo/_coordination/20260625_harbor_bench/pod_b_bootstrap.sh`;等价手工步骤:

```bash
# 0.1 data-root 必须本地盘(放 gpfs/NFS 会挂)
DR=/docker-data-local            # 每 pod 换唯一名,如 /docker-data-<podid>
mkdir -p "$DR"

# 0.2 apt 走内网镜像(无公网),直连不走代理
cat >/etc/apt/sources.list <<'EOF'
deb http://mirrors.i.h.pjlab.org.cn/repository/apt-jammy-proxy/ubuntu/ jammy main restricted universe multiverse
deb http://mirrors.i.h.pjlab.org.cn/repository/apt-jammy-proxy/ubuntu/ jammy-security main restricted universe multiverse
deb http://mirrors.i.h.pjlab.org.cn/repository/apt-jammy-proxy/ubuntu/ jammy-updates main restricted universe multiverse
EOF
printf 'Acquire::http::Proxy "false";\nAcquire::https::Proxy "false";\nAcquire::Retries "3";\n' >/etc/apt/apt.conf.d/99local

# 0.3 fuse-overlayfs(rootfs 本身是 overlay 时 overlay2 无法叠加,必须 fuse-overlayfs)
command -v fuse-overlayfs >/dev/null || { DEBIAN_FRONTEND=noninteractive apt-get update; \
  DEBIAN_FRONTEND=noninteractive apt-get install -y fuse-overlayfs fuse3; }

# 0.4 dockerd:本地 data-root + P0 insecure-registry,detached,本地 log
docker info >/dev/null 2>&1 || setsid bash -c "exec dockerd \
  --host=unix:///var/run/docker.sock \
  --storage-driver=fuse-overlayfs \
  --data-root=$DR \
  --insecure-registry=100.97.118.137:8555 \
  >/var/log/dockerd_pod.log 2>&1" </dev/null &

# 0.5 健康检:用 docker ps(★不要 docker version,旧 rootless 栈上会假死)
sleep 3; docker ps >/dev/null && echo "docker ps OK (rc=0)"
```

- **不想用 insecure-registry** → 装 CA:`repo/scripts/install_worker_registry_ca.sh`(证书 `.../nips2026/swe-data-harness/registry/certs/domain.crt`)。
- **TB2.1 额外要求:`docker compose` 插件必须可用**(任务用 compose 编排;缺插件→整批 `unknown_agent_error`)。SWE-V 不需要 compose。
- P0 registry:`https://100.97.118.137:8555`(host swe_dev2,self-signed TLS)。

---

## §1. SWE-bench Verified(SWE-V,500 实例)

### 1.1 前置
§0 公共配方即可(**不需要** compose 插件)。

### 1.2 资产路径(镜像双路 + 映射表)
| 资产 | 路径 |
|---|---|
| P0 registry(主路) | `https://100.97.118.137:8555` 上 `swe-data-harness/swebench-verified-<org>-<repo>-<id>`(500 全齐) |
| **实例→镜像映射表(关键)** | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json` |
| fallback tars(备路) | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/swerex_images/chunks/*.tar`(先验 sha256) |
| conda 环境 | `/data/conda_envs/swebench`(py3.11,含 minisweagent + swebench) |
| 标准 scaffold | `.../swe/bench/swe-bench-verified/mini-swe-agent`(版本锁 `scaffold_versions.yaml`) |
| gold/oracle 验证器 | `.../swev_gold_disk_revalidate_20260702/diskval_orchestrator.py`(0 模型 token) |
| 一键 runner(当前) | `repo/scripts/run_swebench_verified_full_offline.sh` ← **将被 51 的 V2 替换,见 §1.3 注** |

映射表单条(harness 认的是 `local_ref`,拉完 digest 必须 retag):
```json
"astropy__astropy-12907": {
  "p0_digest_ref": "100.97.118.137:8555/swe-data-harness/swebench-verified-astropy-astropy-12907@sha256:8be43389...",
  "local_ref":     "swebench/sweb.eval.x86_64.astropy_1776_astropy-12907:latest",
  "fallback_tar":  ".../swe/swerex_images/chunks/astropy-1776-astropy_00.tar",
  "fallback_tar_sha256": "784d80536d79..."
}
```

### 1.3 可直接复制的命令块

```bash
MAP=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json

# (a) 取镜像:每实例三步(首拉并发 ≤4;registry 后端是共享盘,首轮大镜像写放大)
INST=astropy__astropy-12907
REF=$(jq -r ".\"$INST\".p0_digest_ref" "$MAP")
TAG=$(jq -r ".\"$INST\".local_ref"      "$MAP")
docker pull "$REF"          # 实测 ~3.17GB / ~20s (rjob pod)
docker tag  "$REF" "$TAG"
# 备路(P0 拉不动时):sha256sum <fallback_tar> 比对 fallback_tar_sha256 后 docker load -i <fallback_tar>

# (b) oracle / gold 模式(0 模型 token,验环境+eval 通路,金标准)
python /mnt/.../swev_gold_disk_revalidate_20260702/diskval_orchestrator.py   # 内含用法;支持按实例过滤
# 我方全量账目对照:offline-PASSED 484 + offline-induced 16 = 500(账本 V5_GOLD_LEDGER.md)

# (c) 真模型模式(标准 scaffold = mini-swe-agent)
source /data/conda_envs/swebench/bin/activate
python -m minisweagent.run.benchmarks.swebench \
  --subset verified --split test \
  --filter '^(astropy__astropy-12907)$' \
  --workers <N> -o <outdir> \
  -m gpt-5.4-mini --model-class minisweagent.models.litellm_model.LitellmModel \
  -c <minisweagent>/config/benchmarks/swebench.yaml -c <你的 overlay.yaml>
# 模型端点:离线 worker 走 dev relay http://100.96.122.22:18540/v1(worker curl /v1/models 返回 401 即通)
# API key:从 /data/nips/shared_bench/api_config.env 取(OPENAI_API_KEY);★key 字面量不写进任何文档/日志
```

> **★ §1.3 注(入口切换):** 上面 (c) 的 minisweagent 直调 + 当前 `run_swebench_verified_full_offline.sh` 是 2026-07-03 实测入口。**SWE-V 全量入口将换成 51 在写的 V2 runner(去 shard + run-eval 串联 + c100)**。V2 就绪后本节以 V2 的确切调用行 + env 更新。

### 1.4 验收清单
- [ ] P0 by-digest pull 成功 + retag 成 `local_ref`
- [ ] 任一实例容器 `--network none` 起得来
- [ ] gold 流:任选 10 实例 gold → eval 全 resolved
- [ ] fallback tar 路:断 registry,tar+sha 校验 → load → 同样跑通
- [ ] 落账:每实例 `{instance_id, resolved: bool, 证据路径}`

---

## §2. Terminal-Bench 2.1(TB2.1,89 任务)

> **官方 Harbor CLI 的 `-d` 数据集解析链离线不可用**(要连 hub.harborframework.com),必须走本文 vendored 资产路线。

### 2.1 前置
§0 公共配方 **+ `docker compose` 插件可用**(任务用 compose 编排)。

### 2.2 资产路径(canonical 数据集 + 镜像双路)
| 资产 | 路径 |
|---|---|
| **任务 spec 数据集(canonical)** | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703` ← **r7-final 为最新;旧的 r5-b7 / 无后缀版均过时勿用** |
| P0 registry 镜像(主) | `https://100.97.118.137:8555` 上 `swe-data-harness/terminal-bench-2-1-<task>`(89 全齐) |
| digest 映射生成 | `repo/scripts/build_tb21_prebuilt_image_map.py`(catalog 查询必须 `?n=1000`,默认 500 分页会截断) |
| 官方原始 tar(备,~85GB) | `/mnt/shared-storage-user/mineru2-shared/yuhongyu/harbor-eval/offline-cache/terminal-bench-2-1/docker-images/alexgshaw_<task>_20251031.tar`(90 个;官方未修复版,注意与我方 baked 版差异) |
| 一键 runner | `repo/scripts/run_terminal_bench_2_1_full89_offline.sh`(batched,fail-closed) |
| 辅助脚本 | 同目录 `load_offline_images.sh` / `install_worker_registry_ca.sh` / `cleanup_tb21_worker.sh` / `check_offline_images_manifest.py` |
| oracle 全量账目 | `repo/reports/scores/tb21_full89_oracle_infra_map_r5_final_20260703.{md,json}`(79/89 resolved) |

### 2.3 可直接复制的命令块

```bash
DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703

# (a) 取镜像:catalog 必须 n=1000
curl -sk "https://100.97.118.137:8555/v2/_catalog?n=1000" | jq '.repositories[]' | grep terminal-bench
docker pull 100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-<task>@sha256:<digest>
docker tag  <上面的 ref> <compose.yaml 引用的本地 tag>     # tag 以任务 spec compose 为准
# 备路:docker load -i .../docker-images/alexgshaw_<task>_20251031.tar
# ★ B7 教训:一个任务 compose 可能引用多个镜像;preheat 必须覆盖 rerun 会引用的全部镜像,
#   否则"容器起不来→unknown_agent_error"假失败。清理 docker 数据后重跑前先 check_offline_images_manifest.py 对账。

# (b) oracle 模式(官方 solution 当 agent,0 模型 token)—— runner 为 env 驱动:
export TB2_OFFLINE_TEST_BOOTSTRAP=1        # ★必须=1;=0 的 smoke 模式撞 RO /tests → unknown_agent_error
export TB21_FULL89_DATASET="$DS"
export TB21_FULL_CONCURRENCY=<c>
export TB_AGENT=oracle
bash repo/scripts/run_terminal_bench_2_1_full89_offline.sh    # fail-closed:缺资产直接报错不静默跳过
# 参数/环境以脚本内实现与 --help 为准;文档等价 flag 形式:--dataset "$DS" --tasks <t1,t2|all> --mode oracle --concurrency <c>
# 单任务机制链(自行实现时按序):docker compose up -d → 注入 tests(★bind-mount,不用 put_archive)
#                              → 执行 solution → strict parser 判 resolved → teardown

# (c) 真模型模式(标准 scaffold = terminus-2,oracle 收口后才开)
export TB_AGENT=terminus-2
export OPENAI_BASE_URL=http://100.96.122.22:18540/v1     # dev relay(pod 侧);runner 无此 env 时有 host 默认
export OPENAI_API_KEY=<从 /data/nips/shared_bench/api_config.env 取,key 字面量不落文档>
bash repo/scripts/run_terminal_bench_2_1_full89_offline.sh   # terminus-2 + gpt-5.4-mini xhigh, pass@1, timeout ×1.0
```

### 2.4 验收清单
- [ ] compose 插件可用,P0 拉取 + retag 后任一任务 compose up 成功
- [ ] oracle 跑任选 10 任务,与 `r5_final` map 的 resolved 一致(允许 8 个 docker-EOF 类比我们多转绿)
- [ ] tests 注入走 bind-mount,teardown 干净(无残留容器)
- [ ] 断 registry 走官方 tar 备路,同样跑通
- [ ] 落账:每任务 `{task, resolved: bool, 失败归因, 证据路径}`

---

## §3. 通用红线(两 bench 共用,拿血泪换的)
1. 容器一律 `--network none` / compose 内网;"需要联网才跑通"算环境缺陷,不算任务失败。
2. **bug-for-bug**:官方任务/gold 自身缺陷不修(修了与官方分数对不齐);失败先二分——官方环境也失败→归档 upstream-bug,只我方失败→环境要修。
3. eval 阶段 Docker 抖动(ReadTimeout/EOF)不记为模型失败 → 回滚重跑;privileged dockerd(§0)基本根治。
4. cache 命中 ≠ 拉取验证:验 P0 通路看真实 `docker pull` 日志,不是本地已有镜像。
5. data-root 千万别放共享盘;健康检用 `docker ps` 不用 `docker version`。
6. qemu 类任务(`qemu-alpine-ssh`/`install-windows-3.11`)在有 `/dev/kvm` 的机器上最贴官方;无 KVM 走软件模拟超时高,不据此判任务坏。
