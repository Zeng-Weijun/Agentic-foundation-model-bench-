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
`--fail-on-optional-image-preflight`.

Add `--pull` only for digest-pinned images in the internal P0 registry. Add
`--load-fallback` only after the fallback tar checksum is expected to match.

Dry-run the current Terminal-Bench 2.1 one-task smoke wrapper:

```bash
scripts/run_terminal_bench_2_1_smoke.sh --dry-run
```

Run a narrow executable legacy smoke:

```bash
./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --execute --only tau2_paper_core --output-dir /tmp/agentic_bench_tau2_smoke
```

This command should be run from `dev` after `dev` can SSH to `worker-j9jjd`. At the time of the preflight, local Mac -> worker SSH works, but `dev` -> worker SSH returns `Permission denied (publickey)`.

Use `--only tau2_paper_core,repozero_py2js` for a narrow smoke and `--max-concurrency N` to override suite-level benchmark concurrency. Per-benchmark worker counts remain in YAML so large runs can be reviewed before execution.

Pending adapters are present but disabled in `manifests/suite.example.yaml`:

- Terminal-Bench 2.1
- MCP-Atlas
- Tool-Decathlon
- tau3-bench
- programbench
- NL2Repo
