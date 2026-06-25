# Scripts

This directory is reserved for lightweight, GitHub-tracked runner wrappers and deployment utilities.

The current local workspace still contains historical `run_*.sh` launchers at the repository root. Before promoting any of them into this directory, audit whether the script is:

- a stable benchmark adapter,
- a legacy launcher,
- a shared-disk-only operational script,
- or a one-off historical runner.

Rootless workers should wrap benchmark adapters rather than treating existing `run_*.sh` files as worker infrastructure.

## YAML Suite Draft

Default dry-run:

```bash
./scripts/run_suite_from_yaml.sh
```

Explicit suite path:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml
```

Machine-readable plan:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --json
```

Write an audit plan without launching benchmark adapters:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --json --emit-plan /tmp/agentic_bench_suite_plan.json
```

The wrapper defaults to dry-run. `--execute` is guarded: it refuses to proceed while any selected suite entry is not marked `adapter_status: wired` or `adapter_status: wired_legacy`. This keeps the one-key entry reviewable before real benchmark adapters are wired.

The Python implementation has no required third-party dependency. If PyYAML is installed it uses `yaml.safe_load`; otherwise it accepts the restricted YAML subset used by `manifests/suite.example.yaml`.

Secret policy:

- Put secret values in environment variables only.
- Use fields such as `api_key_env: OPENAI_API_KEY`.
- Do not add `api_key`, `token`, `password`, or similar literal secret fields to YAML.

Defaults:

- dry-run is on unless `--execute` is passed;
- control/staging host is recorded as `dev`;
- execution kind is `ssh_worker`;
- the worker is treated as `offline_or_internal_only`;
- `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` is injected for worker jobs;
- model profile defaults to the 8.130 relay `gpt-5.4-mini`;
- `dev_proxy_gpt54mini_8130` points workers at a `dev`-hosted internal proxy on `http://100.96.1.101:18540/v1`;
- SGLang/Qwen is present as a future profile and can be selected in YAML after serving is opened.

Start the `dev` relay proxy from the shared checkout on `dev`:

```bash
BENCH_PROXY_PORT=18540 scripts/start_dev_relay_proxy.sh
```

Check offline/rootless Docker image readiness on the worker:

```bash
scripts/load_offline_images.sh --check
```

Validate the P0 Harbor/OCI image manifest index:

```bash
python3 scripts/agentic_bench_images.py validate --registry manifests/bench_registry.yaml
```

Check one bench image manifest against the worker rootless Docker cache:

```bash
python3 scripts/agentic_bench_images.py check \
  --image-manifest manifests/images/repozero.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --docker-host unix:///tmp/rl/run/docker.sock
```

Inventory a Docker-heavy host cache before staging missing images into P0/shared tars:

```bash
python3 scripts/agentic_bench_images.py inventory-cache \
  --docker-host unix:///var/run/docker.sock \
  --prefix tb2-offline/ \
  --prefix swebench/ \
  --prefix swerex-prebuilt \
  --prefix ghcr.io/all-hands-ai/runtime \
  --output reports/swe_dev_docker_cache_inventory_20260626.json \
  --json >/tmp/agentic_bench_cache_inventory_stdout.json
```

Run only suite image preflights, without launching benchmark adapters:

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml \
  --image-preflight-only \
  --only repozero_py2js_smoke \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_repozero_preflight
```

The preflight-only command writes `run_manifest.json`,
`image_preflight_summary.json`, and `logs/<bench>.image_preflight.log`. Optional
preflights are skipped by default; include them with
`--include-optional-image-preflight`, and make optional failures fatal with
`--fail-on-optional-image-preflight`. If a filter selects zero runs, the command
exits 2 unless `--allow-empty-plan` is set.

Suite `image_preflight` can forward `pull`, `load_fallback`, and `run_smoke` to
the checker. Use `pull` only for digest-pinned images in the internal P0
registry. Use `load_fallback` only after the fallback tar checksum is expected to
match; pair it with `run_smoke` when the manifest contains a container smoke
command. `image_preflight.max_concurrency` caps first-time image transport
separately from model/benchmark suite concurrency; keep it small, normally 2-4
per worker.

Dry-run the current Terminal-Bench 2.1 one-task smoke wrapper:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --dry-run --task-id gcode-to-text
```

Run the enabled image-only suite preflight for the verified TB2.1 smoke image:

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml \
  --image-preflight-only \
  --only terminal_bench_2_1_image_smoke \
  --model-profile dev_proxy_gpt54mini_8130 \
  --output-dir /tmp/agentic_tb21_image_smoke
```

Run a narrow executable legacy smoke:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --execute --only repozero_py2js_smoke --output-dir /tmp/agentic_bench_repozero_smoke
```

`--execute` writes process-level adapter status plus a normalized result artifact
per run under `results/<bench>.result.json`. The controller `summary.json`
keeps the historical `status`/`exit_code` fields and adds
`execution_status`, `benchmark_status`, `score_claim_valid`, and `result_path`.
RepoZero Py2JS has the first parser, based on native `ALL_PASS_CASES` and
`TESTS` lines, so an adapter exit 0 can still be recorded as
`benchmark_status: fail`.

This command should be run from `dev` after `dev` can SSH to `worker-j9jjd`. At the time of the preflight, local Mac -> worker SSH works, but `dev` -> worker SSH returns `Permission denied (publickey)`.

Use `--only repozero_py2js_smoke,vitabench_delivery_one_task_smoke` for a narrow smoke and `--max-concurrency N` to override suite-level benchmark concurrency. Per-benchmark worker counts remain in YAML so large runs can be reviewed before execution. The 8.130 relay profile is staged for suite-level concurrency 40 and should stay at or below 50 unless the relay capacity changes.

Pending adapters are present but disabled in `manifests/suite.example.yaml`:

- Terminal-Bench 2.1
- MCP-Atlas
- Tool-Decathlon
- tau3-bench
- programbench
- NL2Repo
