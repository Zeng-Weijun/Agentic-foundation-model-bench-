# VitaBench / RepoZero Worker Preflight - 2026-06-25

## Scope

- Workspace workflow preflight: read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before remote work.
- Control plane: local Mac.
- Remote hosts used: `dev` for shared repo/proxy checks, worker `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn` for benchmark preflight/smoke.
- Hosts not used: `swe-dev` / `swe_dev`.
- Worker Docker mode: rootless Docker only, `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`.
- Public internet on worker: not used. No image pull, package install, or build was launched.
- Repository write scope: this report only. Existing suite launcher, manifests, README, and old bench launchers were not edited.

## Executive Result

VitaBench is the next executable candidate after tau2.

RepoZero is blocked for worker smoke because the required Docker image is not present in the worker rootless image cache and no matching shared tar was found. The RepoZero launcher has no no-model/dry-run mode and the runner invokes host `codex` plus Docker, so it was not run.

## Active Paths Checked

| Item | Path | Status |
| --- | --- | --- |
| Worker active bench root | `/data/nips/bench` | Resolves to `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench` on worker. |
| VitaBench runner | `/data/nips/bench/run_vitabench.sh` | Exists, executable, hash `50e08d864c47f5a02b7b5e9c07dc6267df117027e68471e11d46c01d1541707b`. |
| VitaBench full runner | `/data/nips/bench/run_vitabench_full.sh` | Exists, executable, hash `88606a6a75ffe7d2a4da7e72482c1341b7216ea7443e62c3514ad334aab02fa5`; runs delivery, instore, ota, and cross_domain, so it is not a one-task smoke entrypoint. |
| RepoZero runner | `/data/nips/bench/run_repozero_py2js.sh` | Exists, executable, hash `398fc0338dd7e29bec6822342647e6eb67bbe59066f9eb346915e7d91c7ea0c4`. |
| VitaBench checkout | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench` | Exists with `.venv/bin/vita`, Python 3.12.13, and local task JSON. |
| RepoZero checkout | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero` | Exists with `tools_repozero_codex_full.py`, `tools_repozero_codex_smoke.py`, and `Py2JS/dataset`. |
| Shared active bench scripts | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_vitabench*.sh`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_repozero_py2js.sh` | Same hashes as `/data/nips/bench`. |
| Older shared runner copies | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_vitabench*.sh`, `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_repozero_py2js.sh` | Exist but have different hashes from active `/data/nips/bench` copies; inspected read-only. |
| Shared AFMB repo | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo` | At commit `2f1f9c3`; unrelated untracked files already present and not touched. |

## Commands Run

### Workflow and repository context

```bash
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
sed -n '261,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md

git status --short
git branch --show-current
git log --oneline -5

ssh dev 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo && git status --short && git rev-parse --short HEAD && git log --oneline -3'
```

Observed shared repo head: `2f1f9c3`.

### Worker launcher and path inspection

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   hostname
   realpath /data/nips/bench
   ls -l /data/nips/bench/run_vitabench*.sh /data/nips/bench/run_repozero_py2js.sh'

ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   sha256sum /data/nips/bench/run_vitabench.sh \
             /data/nips/bench/run_vitabench_full.sh \
             /data/nips/bench/run_repozero_py2js.sh
   nl -ba /data/nips/bench/run_vitabench.sh | sed -n "1,220p"
   nl -ba /data/nips/bench/run_vitabench_full.sh | sed -n "1,140p"
   nl -ba /data/nips/bench/run_repozero_py2js.sh | sed -n "1,220p"'
```

### Shared project path inspection

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
for p in \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_vitabench.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_vitabench_full.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_repozero_py2js.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_vitabench.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_vitabench_full.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_repozero_py2js.sh; do
  if [[ -e "$p" ]]; then sha256sum "$p"; else echo "MISSING $p"; fi
done'

ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
for f in \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_vitabench.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_vitabench_full.sh \
  /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/shared/runners/run_repozero_py2js.sh; do
  echo "=== $f ==="
  nl -ba "$f" | sed -n "1,140p"
done'
```

### VitaBench no-model preflight

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   VITA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench
   ls -la "$VITA_ROOT" | sed -n "1,80p"
   find "$VITA_ROOT/data" -maxdepth 4 -type f | sort | sed -n "1,120p"
   "$VITA_ROOT/.venv/bin/vita" --help
   "$VITA_ROOT/.venv/bin/vita" run --help'
```

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   VITA_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench
   cd "$VITA_ROOT"
   .venv/bin/python - <<'"'"'PY'"'"'
import json, pathlib
root = pathlib.Path("data/vita/domains")
for p in sorted(root.glob("*/tasks_en.json")):
    data = json.loads(p.read_text())
    first = "NA"
    if data:
        first = data[0].get("id") or data[0].get("task_id") or data[0].get("name") or data[0].get("user_id") or "NO_ID_FIELD"
    print(f"{p}: count={len(data)} first_id={first}")
PY'
```

Task files observed:

| Task file | Count | First ID |
| --- | ---: | --- |
| `data/vita/domains/cross_domain/tasks_en.json` | 100 | `A0812003` |
| `data/vita/domains/delivery/tasks_en.json` | 100 | `10711001` |
| `data/vita/domains/instore/tasks_en.json` | 100 | `10826004` |
| `data/vita/domains/ota/tasks_en.json` | 100 | `D0812006` |

Relevant source evidence:

- `src/vita/config.py` honors `VITA_MODEL_CONFIG_PATH`.
- `src/vita/utils/llm_utils.py` sends OpenAI-compatible requests with `requests.post(data["base_url"], ...)`.
- `src/vita/cli.py` exposes `--task-ids`, `--num-tasks`, `--max-steps`, `--re-evaluate-file`, but no explicit prepare/dry-run mode.
- `src/vita/run.py` filters by `task_ids`; if `num_tasks` is also set, it selects the first `num_tasks` tasks. For `NUM_TASKS=1` and `VITA_TASK_IDS=10711001`, the selected task remains `10711001`.
- Source grep found no Docker, package install, git clone, or dataset download path under `src/vita`; only `subprocess` use observed was `git rev-parse HEAD`.

### Dev proxy readiness check

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
printf "DEV_HOST=%s\n" "$(hostname)"
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true) | grep -E "(:18540|Local Address)" || true'

ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   source /data/nips/shared_bench/api_config.env >/dev/null 2>&1 || true
   curl -sS -m 8 -H "Authorization: Bearer ${OPENAI_API_KEY:-dummy}" \
     http://100.96.1.101:18540/v1/models | head -c 500
   printf "\nCURL_EXIT=%s\n" "$?"'
```

Observed:

- `dev` has a listener on `0.0.0.0:18540` owned by `python3`.
- Worker `/v1/models` probe returned model JSON including `gpt-5.4-mini`; curl exit `0`.

### VitaBench one-task worker smoke

Command run on worker:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
RUN_TAG="devproxy_worker_smoke_20260625_$(date +%H%M%S)"
export RUN_TAG
export BENCH_MODEL_PROFILE=gpt54mini_8130
export MODEL_NAME=gpt-5.4-mini
export MODEL_SLUG=gpt-5.4-mini
export LITELLM_MODEL=openai/gpt-5.4-mini
export OPENAI_BASE_URL=http://100.96.1.101:18540/v1
export BASE_URL=http://100.96.1.101:18540/v1
export NUM_TASKS=1
export NUM_TRIALS=1
export MAX_CONCURRENCY=1
export VITA_DOMAIN=delivery
export VITA_TASK_SET_NAME=delivery
export VITA_TASK_IDS=10711001
export VITA_MAX_STEPS=20
export VITA_ENABLE_THINK=0
export VITA_LANGUAGE=english
export VITA_SAVE_TO="bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_${RUN_TAG}"
printf "RUN_TAG=%s\n" "$RUN_TAG"
timeout 900 /data/nips/bench/run_vitabench.sh'
```

Observed runner command:

```bash
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/.venv/bin/vita run \
  --domain delivery \
  --task-set-name delivery \
  --agent-llm gpt-5.4-mini \
  --user-llm gpt-5.4-mini \
  --evaluator-llm gpt-5.4-mini \
  --num-trials 1 \
  --max-steps 20 \
  --max-concurrency 1 \
  --save-to bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847 \
  --language english \
  --num-tasks 1 \
  --task-ids 10711001
```

Status:

- Exit code: `0`.
- Duration in Vita log: `78.09s` for the single simulation; total `1.30min`.
- Harness status: `Successfully completed all simulations`.
- Tasks: `1`.
- Simulations: `1`.
- Failed task executions: `0`.
- Termination reason: `MAX_STEPS` due the deliberate `VITA_MAX_STEPS=20` cap.
- Reward: `0.0`, expected for this capped smoke and not treated as benchmark quality evidence.

Artifacts:

| Artifact | Path | Status |
| --- | --- | --- |
| Runner directory | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847` | Exists. |
| Runner summary | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847/run.env.summary` | Records model, base URL, task/trial/concurrency, artifact. |
| Runner command | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847/command.sh` | Records exact `vita run` command. |
| Runner log | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847/vitabench.log` | 43 KB, ends with successful completion summary. |
| Generated model config | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847/vita_models.yaml` | Exists, mode `0600`; contains generated OpenAI-compatible endpoint config. |
| Vita simulation JSON | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/data/simulations/bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847` | Exists, 52 KB, JSON parses with top keys `timestamp,info,tasks,simulations`; `tasks=1`, `simulations=1`, first task `10711001`, termination `max_steps`. |

Verification command:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   RUN_DIR=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/vitabench/gpt-5.4-mini_devproxy_worker_smoke_20260625_211847
   ART=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/VitaBench/data/simulations/bench_gpt-5.4-mini_delivery_devproxy_worker_smoke_devproxy_worker_smoke_20260625_211847
   ls -la "$RUN_DIR"
   sed -n "1,80p" "$RUN_DIR/run.env.summary"
   sed -n "1,40p" "$RUN_DIR/command.sh"
   ls -lh "$ART"
   file "$ART" || true
   python - "$ART" <<'"'"'PY'"'"'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1])
data = json.loads(p.read_text())
print("json_ok=true")
print("top_keys=" + ",".join(data.keys()))
sims = data.get("simulations", [])
tasks = data.get("tasks", [])
print(f"tasks={len(tasks)} simulations={len(sims)}")
if sims:
    s = sims[0]
    print("first_task_id=" + str(s.get("task", {}).get("id") or s.get("task_id") or "unknown"))
    print("termination=" + str(s.get("termination_reason") or s.get("terminationReason") or s.get("info", {}).get("termination_reason") or "unknown"))
PY
   tail -n 40 "$RUN_DIR/vitabench.log"'
```

## RepoZero Blocker Evidence

RepoZero was not run.

Wrapper behavior:

- `/data/nips/bench/run_repozero_py2js.sh` defaults `REPOZERO_DOCKER_IMAGE=ghcr.io/jessezzzzz/repoarena-new:latest`.
- In smoke mode, it defaults to cases `base58/test1.py bech32/test1.py bencoder/test1.py fractions/test1.py`.
- It invokes `tools_repozero_codex_full.py` when present, passing `--model`, `--base-url`, `--codex-attempts`, `--docker-image`, `--resume`, and cases.
- No no-model/dry-run argument is exposed by the wrapper.

Runner behavior:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   REPOZERO_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero
   grep -nE "docker run|docker_image|codex|dry|no-model|argparse|pull" \
     "$REPOZERO_ROOT/tools_repozero_codex_full.py" | sed -n "1,220p"'
```

Observed in `tools_repozero_codex_full.py`:

- `start_case_container(...)` calls Docker.
- Docker commands use `docker run --network none`.
- `run_case(...)` checks for host `codex` and `node`; missing either raises `RuntimeError("codex or node not found on PATH")`.
- Argparse includes `--docker-image`, `--codex-attempts`, `--workers`, `--timeout-s`, `--cases`, but no `--dry-run` or no-model flag.

Image status:

```bash
ssh -C -A -X -Y -o BatchMode=yes -o ConnectTimeout=20 \
  'ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn' \
  'set -euo pipefail
   export DOCKER_HOST=unix:///tmp/rl/run/docker.sock
   if docker image inspect ghcr.io/jessezzzzz/repoarena-new:latest >/dev/null 2>&1; then echo present; else echo missing; fi'
```

Observed: `missing`.

Shared tar search:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 dev 'set -euo pipefail
find /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images \
     /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/repozero \
     /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval \
     -maxdepth 5 -type f \( -iname "*.tar" -o -iname "*.tar.gz" -o -iname "*.sha256" \) \
     2>/dev/null | sort | sed -n "1,120p"'
```

Observed: no tar or checksum output for the RepoZero image.

## Decision

| Benchmark | Worker readiness | Smoke run status | Next action |
| --- | --- | --- | --- |
| VitaBench | Ready for a lightweight worker smoke through the dev proxy. Python venv and local task data exist; no Docker/image path found; one-domain runner supports pinned `VITA_TASK_IDS`. | Ran one pinned delivery task successfully at harness level. The smoke reached the deliberate 20-step cap and produced valid JSON artifacts. | Next executable candidate. For suite integration, add or switch to a single-domain `run_vitabench.sh` manifest entry with `VITA_DOMAIN=delivery`, `VITA_TASK_SET_NAME=delivery`, `VITA_TASK_IDS=10711001`, `NUM_TASKS=1`, `NUM_TRIALS=1`, `MAX_CONCURRENCY=1`, and a smoke-appropriate `VITA_MAX_STEPS`. Avoid `run_vitabench_full.sh` for tiny smoke because it fans out across four domains. |
| RepoZero | Not ready on worker. Checkout and runner exist, but image `ghcr.io/jessezzzzz/repoarena-new:latest` is absent from rootless Docker and no shared tar was found. | Not run. Running now would either fail on missing image or require an image pull/build, and the runner would call host `codex` with no no-model/dry-run guard. | Preload or build the exact image on an internet-capable host, publish a shared tar/checksum, `docker load` it into worker rootless Docker, then add a dry-run/no-model preflight or run a single explicit case only after confirming no pull path. |

## Recommendation for Main Integration Thread

1. Treat VitaBench as the next smoke target.
2. Do not use `vitabench_full` for the next tiny suite smoke; it executes four domain runs even with `NUM_TASKS=1`.
3. Add a single-domain VitaBench manifest entry pointing at `run_vitabench.sh`, not a new adapter, unless the suite launcher currently requires every benchmark entry to be a full benchmark wrapper.
4. Keep RepoZero out of executable smoke manifests until the `ghcr.io/jessezzzzz/repoarena-new:latest` image is available offline in the worker rootless cache and the runner has either a dry-run/no-model preflight or an explicitly approved one-case Codex path.
