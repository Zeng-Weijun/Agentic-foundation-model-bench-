# RepoZero Suite Execute With Image Preflight Smoke - 2026-06-25

## Scope

This smoke validated the new suite-level required image preflight path after
commit `74640d5`.

It was run from a local tmux session as required for a potentially long worker
job. The suite command SSHed to `worker-j9jjd`, first checked the RepoZero image
manifest against worker rootless Docker, then launched the existing legacy
RepoZero Py2JS adapter.

No source code or Docker state was changed by this report.

## Command

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml \
  --execute \
  --only repozero_py2js_smoke \
  --model-profile dev_proxy_gpt54mini_8130 \
  --max-concurrency 1 \
  --output-dir /tmp/agentic_repozero_exec_74640d5
```

## Result

Suite wrapper status:

```text
repozero_py2js_smoke    pass
exit_code: 0
```

Controller summary:

```text
/tmp/agentic_repozero_exec_74640d5/summary.json
/tmp/agentic_repozero_exec_74640d5/logs/repozero_py2js_smoke.log
```

Shared run artifacts:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/dev_worker_smoke_dryrun/repozero_py2js_smoke
```

## Image Preflight Evidence

The required image preflight ran before the adapter command.

```text
bench_id: repozero_py2js_smoke
image: repozero_py2js_repoarena_runtime
status: present
docker_host: unix:///tmp/rl/run/docker.sock
fallback_tar_sha256_status: match
present_ref: ghcr.io/jessezzzzz/repoarena-new:latest
counts:
  present: 1
  missing: 0
  tar_verified: 1
  tar_missing: 0
  tar_mismatch: 0
```

This proves the suite `--execute` path now blocks on required image readiness
before starting the adapter.

## Adapter/Harness Evidence

Adapter command:

```text
python tools_repozero_codex_full.py \
  --repo-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero \
  --model gpt-5.4-mini \
  --base-url http://100.96.1.101:18540/v1 \
  --effort xhigh \
  --workers 1 \
  --timeout-s 1200 \
  --codex-attempts 1 \
  --docker-image ghcr.io/jessezzzzz/repoarena-new:latest \
  --run-name gpt-5.4-mini_dev_worker_smoke_dryrun_smoke \
  --case-source official \
  --resume \
  --cases base58/test1.py
```

The adapter completed and returned `0`, but the benchmark case itself did not
pass:

```text
case: base58/test1.py
passed: 0
total: 60
all_pass: false
codex_returncode: 1
codex_timeout: false
fail_example: missing generated entry file
```

RepoZero summary:

```text
ALL_PASS_CASES 0 / 1
TESTS 0 / 60
artifact=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/output_codex/gpt-5.4-mini_dev_worker_smoke_dryrun_smoke
```

Interpretation: this is an infrastructure pass, not a benchmark-score pass. The
new image preflight and worker/model plumbing worked; the one selected RepoZero
task failed at generation/evaluation quality.

## Follow-Up

1. Keep `repozero_py2js_smoke` as the current end-to-end infrastructure smoke
   because it exercises suite planning, required image preflight, worker Docker,
   model relay, and legacy adapter execution.
2. Do not count the suite wrapper `pass` as a task success metric. Parse
   RepoZero summary artifacts separately when reporting benchmark scores.
3. If RepoZero is used for model comparison, add a result parser that records
   `ALL_PASS_CASES`, `TESTS`, per-case `all_pass`, and `codex_returncode` into
   the normalized run manifest.
