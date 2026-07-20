# YAML Suite Launcher Draft

Date: 2026-06-25

## Current Repository Check

Current tracked layout:

```text
README.md
manifests/
  README.md
  datasets.example.yaml
  harnesses.example.yaml
  models.example.yaml
  runs.schema.json
  suite.example.yaml
reports/
  README.md
  agentic_bench_landscape_20260625.md
  agentic_bench_matrix_20260625.csv
  deployment_plan_20260625.md
  rootless_worker_research_20260625.md
  shared_disk_layout_research_20260625.md
  trace_manifest_template.yaml
  yaml_suite_launcher_plan_20260625.md
scripts/
  agentic_bench_suite.py
  README.md
  run_suite_from_yaml.sh
  test_agentic_bench_suite.py
traces/
  README.md
```

Relevant existing decisions:

- GitHub should contain lightweight source, manifests, schemas, reports, and runner wrappers.
- Shared storage should contain datasets, harness checkouts, raw traces, and large run outputs.
- `dev` is the controller/staging host.
- `worker` is treated as an offline rootless execution target.
- Real secrets must stay in environment variables, not YAML or scripts.

## Added Launcher Shape

The draft entrypoint is:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml
```

It calls:

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml
```

Default behavior is dry-run. The launcher builds an auditable plan with:

- `controller_host: dev`
- `worker_host`
- `execution_host`
- `DOCKER_HOST=unix:///tmp/rl/run/docker.sock`
- suite and per-bench concurrency
- `network_policy: offline_or_internal_only`
- `rootless_required`
- selected model profile
- required environment variable names
- per-bench command preview
- adapter wiring status

The Python script uses PyYAML when available. If PyYAML is absent, it falls back to a restricted YAML parser that supports the subset used by `manifests/suite.example.yaml`.

## Model Profiles

The example suite includes:

- `gpt54mini_8130`: OpenAI-compatible relay at `http://8.130.49.170/v1`, API key from `OPENAI_API_KEY`.
- `gpt54_8130`: same relay for the larger `gpt-5.4` profile.
- `qwen3_coder_30b_a3b_sglang_future`: future SGLang OpenAI-compatible endpoint via `SGLANG_OPENAI_BASE_URL`, with API key policy allowing empty/local-compatible keys.

No real API key is written to the repo.

## Safety Guards

- `--dry-run` is the default.
- `--execute` refuses to continue while any selected bench is not marked `adapter_status: wired` or `adapter_status: wired_legacy`.
- `suite.controller_host` must be `dev`.
- Host fields reject `swe_dev` and `swe-dev`.
- Literal secret-like keys such as `api_key`, `token`, and `password` are rejected unless empty or environment-substituted placeholders.
- Command previews include environment variable names and smoke parameters, not secret values.

## 2026-06-25 Worker Preflight Update

`worker-j9jjd` has a usable rootless Docker daemon only when jobs inject:

```text
DOCKER_HOST=unix:///tmp/rl/run/docker.sock
```

Rootless bind-mount micro-smoke passed with cached SWE-bench image:

```text
swebench/sweb.eval.x86_64.django_1776_django-13810:latest
```

Model-calling benchmark smoke is currently blocked:

- worker -> `http://8.130.49.170/v1/models`: timeout after 8 seconds;
- `dev` -> `http://8.130.49.170/v1/models`: HTTP 503;
- `dev` -> worker SSH: `Permission denied (publickey)`;
- local Mac -> worker SSH: ok.

Therefore the suite can produce and execute non-model/rootless checks now, but real model benchmark smoke needs either a healthy reachable relay, a `dev`-side model proxy, or the future SGLang endpoint.

## How To Run

Human-readable dry-run:

```bash
./scripts/run_suite_from_yaml.sh
```

JSON dry-run:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --json
```

Emit an audit plan:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --json --emit-plan /tmp/agentic_bench_suite_plan.json
```

Force smoke mode even if a future YAML changes the suite mode:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --smoke
```

## Adapter Status

The suite currently has two adapter classes:

- `wired_legacy`: existing `/data/nips/bench/run_*.sh` scripts that can be called on `worker-j9jjd` for smoke attempts.
- `pending_adapter`: benchmarks still needing a located or written wrapper.

Before promoting a legacy adapter to final shared-runner status, each adapter still needs a worker-safe wrapper that:

- consumes `BENCH_RUN_DIR`, `BENCH_SUITE_ID`, `BENCH_RUN_ID`, `BENCH_MODEL_PROFILE`, and `BENCH_OFFLINE`;
- writes `run_manifest.json`, `worker_manifest.json`, logs, and native result pointers;
- uses a unique temp root and compose project name;
- avoids public downloads on the offline worker;
- never writes API keys into command logs or manifests.

Current pending adapters:

- Terminal-Bench 2.1
- MCP-Atlas
- Tool-Decathlon
- tau3-bench
- programbench
- NL2Repo
