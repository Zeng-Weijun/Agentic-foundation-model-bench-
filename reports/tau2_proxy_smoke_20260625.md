# tau2 Dev Proxy Worker Smoke

Date: 2026-06-25

Scope: one-task-per-domain tau2 smoke through the offline/rootless worker path, using the `dev` relay proxy profile. This was an infrastructure smoke, not a benchmark score claim.

## Topology

- Controller shell: local Mac control plane, per workspace workflow.
- Worker: `ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`
- Worker hostname observed earlier: `zwj2-64rlk-3469265-worker-0`
- Worker rootless Docker socket: `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`
- Model route: worker -> `dev` proxy `http://100.96.1.101:18540/v1` -> 8.130 relay
- Proxy tmux session: local `tmux` session `agentic_dev_proxy`, SSHing into `dev`
- Proxy log: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/dev_relay_proxy_18540.log`

The run did not use `swe_dev` or `swe-dev`. The remaining topology gap is still `dev -> worker-j9jjd` SSH publickey auth; current dispatch used local Mac -> worker while model traffic used worker -> `dev` proxy.

## Proxy

Started from the shared checkout on `dev`:

```bash
BENCH_PROXY_PORT=18540 \
BENCH_PROXY_LOG=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/logs/dev_relay_proxy_18540.log \
scripts/start_dev_relay_proxy.sh
```

Current listener check:

```text
0.0.0.0:18540 users:(("python3",pid=2059245,fd=3))
```

Worker model smoke through the proxy completed before the benchmark run:

```text
CHAT_STATUS=ok
MODEL=gpt-5.4-mini
CONTENT=ok
```

## Suite Command

Executed from this repository:

```bash
rm -rf /tmp/agentic_tau2_proxy_smoke3
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml \
  --execute \
  --only tau2_paper_core \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_tau2_proxy_smoke3
```

The launcher generated a worker command with:

```text
OPENAI_BASE_URL=http://100.96.1.101:18540/v1
MODEL_NAME=gpt-5.4-mini
LITELLM_MODEL=openai/gpt-5.4-mini
BENCH_MODEL_PROFILE=gpt54mini_8130
BENCH_OFFLINE=1
BENCH_NETWORK_POLICY=offline_or_internal_only
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
NUM_TASKS=1
NUM_TRIALS=1
MAX_CONCURRENCY=1
```

`BENCH_MODEL_PROFILE=gpt54mini_8130` is intentional: the legacy `/data/nips/bench` adapter still loads `profiles/${BENCH_MODEL_PROFILE}.env`, while the suite-level profile keeps the worker-facing endpoint at the `dev` proxy.

## Result

Suite summary:

```json
{
  "suite_id": "dev_worker_smoke_dryrun",
  "status": 0,
  "results": [
    {
      "bench_id": "tau2_paper_core",
      "status": "pass",
      "exit_code": 0,
      "started_at": "2026-06-25T12:50:00Z",
      "ended_at": "2026-06-25T12:54:42Z",
      "log_path": "/tmp/agentic_tau2_proxy_smoke3/logs/tau2_paper_core.log"
    }
  ]
}
```

Produced local suite artifacts:

```text
/tmp/agentic_tau2_proxy_smoke3/run_manifest.json
/tmp/agentic_tau2_proxy_smoke3/summary.json
/tmp/agentic_tau2_proxy_smoke3/status/tau2_paper_core.status
/tmp/agentic_tau2_proxy_smoke3/logs/tau2_paper_core.log
```

Produced shared tau2 result artifacts:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench/data/simulations/bench_gpt-5.4-mini_tau2_airline_dev_worker_smoke_dryrun/results.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench/data/simulations/bench_gpt-5.4-mini_tau2_retail_dev_worker_smoke_dryrun/results.json
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/paper_reading/external_benchmarks/tau2-bench/data/simulations/bench_gpt-5.4-mini_tau2_telecom_dev_worker_smoke_dryrun/results.json
```

Shared suite run directory:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/tau2_paper_core
```

## Domain Outcomes

Each tau2 domain completed one simulation and wrote `results.json`:

| Domain | Simulations | Termination | Duration | Reward |
|---|---:|---|---:|---:|
| airline | 1 | `user_stop` | 39.12s | 0.0 |
| retail | 1 | `user_stop` | 75.12s | 0.0 |
| telecom | 1 | `user_stop` | 130.70s | 0.0 |

Interpretation: this is a harness/proxy/worker pass, not a model-quality pass. The model produced valid API traffic and the tau2 harness completed, but the sampled tasks scored `0.0`.

## Fixes Validated By This Smoke

Two launcher issues were found during this smoke and fixed before the passing run:

1. Remote commands now use `bash -c` instead of `bash -lc`.

   Root cause: the worker login shell path sourced `/etc/profile.d/command_logging_simple.sh`, which references `ZSH_VERSION` under nounset and aborts before the benchmark body.

2. Suite model profiles can set a separate legacy `BENCH_MODEL_PROFILE`.

   Root cause: the legacy benchmark adapters load `/data/nips/bench/profiles/${BENCH_MODEL_PROFILE}.env`. A new suite profile name such as `dev_proxy_gpt54mini_8130` is correct for orchestration but not present in the legacy profile directory. The suite now exports `BENCH_MODEL_PROFILE=gpt54mini_8130` while preserving `OPENAI_BASE_URL=http://100.96.1.101:18540/v1`.

## Remaining Work

- Fix or provision `dev -> worker-j9jjd` SSH batch auth so the controller can dispatch directly from `dev`.
- Keep `dev_proxy_gpt54mini_8130` as the worker default until an SGLang endpoint is opened.
- Run the same YAML path against the next legacy smoke only after required Docker images or runtime assets are present on the rootless worker.
- Treat reward `0.0` as expected model behavior for this tiny smoke; do not use it as a tau2 leaderboard score.
