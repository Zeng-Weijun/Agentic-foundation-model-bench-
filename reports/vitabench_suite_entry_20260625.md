# VitaBench Suite Entry - 2026-06-25

## Scope

- Read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` before work.
- Repository: `/Users/Zhuanz1/Desktop/ssh_work/paper_reading/Agentic-foundation-model-bench-`.
- Host constraint: `swe_dev` / `swe-dev` not used.
- Write scope used:
  - `manifests/suite.example.yaml`
  - `scripts/test_agentic_bench_suite.py`
  - `reports/vitabench_suite_entry_20260625.md`
- Pre-existing unrelated modified file left untouched:
  - `reports/cocoabench_worker_smoke_20260625.md`

## Change

Added a separate enabled suite entry:

```yaml
id: vitabench_delivery_one_task_smoke
benchmark: vitabench
adapter: vitabench
adapter_script: run_vitabench.sh
adapter_status: wired_legacy
model_profile: gpt54mini_8130
concurrency: 1
params:
  VITA_DOMAIN: delivery
  VITA_TASK_SET_NAME: delivery
  VITA_TASK_IDS: 10711001
  NUM_TASKS: 1
  NUM_TRIALS: 1
  MAX_CONCURRENCY: 1
  VITA_MAX_STEPS: 20
  VITA_ENABLE_THINK: 0
  VITA_LANGUAGE: english
```

The existing `vitabench_full` entry was left intact and still points at `run_vitabench_full.sh`, preserving its broader multi-domain intent.

## TDD Evidence

Added the focused test first:

```bash
python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_example_manifest_vitabench_one_task_smoke_uses_verified_runner
```

RED result before the manifest change:

```text
FAIL: test_example_manifest_vitabench_one_task_smoke_uses_verified_runner
AssertionError: 0 != 1
```

GREEN result after the manifest change:

```text
Ran 1 test in 0.011s

OK
```

## Dry-Run Verification

Command:

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only vitabench_delivery_one_task_smoke --model-profile dev_proxy_gpt54mini_8130
```

Exit code: `0`.

Exact dry-run evidence:

```text
"bench_id": "vitabench_delivery_one_task_smoke"
"script_path": "run_vitabench.sh"
"model": {
  "profile_id": "dev_proxy_gpt54mini_8130",
  "endpoint": "http://100.96.1.101:18540/v1",
  "provider": "openai_compatible_dev_proxy"
}
"runtime_env": {
  "BENCH_MODEL_PROFILE": "gpt54mini_8130",
  "OPENAI_BASE_URL": "http://100.96.1.101:18540/v1",
  "BASE_URL": "http://100.96.1.101:18540/v1",
  "VITA_DOMAIN": "delivery",
  "VITA_TASK_SET_NAME": "delivery",
  "VITA_TASK_IDS": "10711001",
  "NUM_TASKS": "1",
  "NUM_TRIALS": "1",
  "MAX_CONCURRENCY": "1",
  "VITA_MAX_STEPS": "20",
  "VITA_ENABLE_THINK": "0",
  "VITA_LANGUAGE": "english"
}
"params": {
  "MAX_CONCURRENCY": 1,
  "NUM_TASKS": 1,
  "NUM_TRIALS": 1,
  "VITA_DOMAIN": "delivery",
  "VITA_ENABLE_THINK": 0,
  "VITA_LANGUAGE": "english",
  "VITA_MAX_STEPS": 20,
  "VITA_TASK_IDS": 10711001,
  "VITA_TASK_SET_NAME": "delivery"
}
```

The rendered command ends with the verified one-task runner:

```text
cd /data/nips/bench
exec ./run_vitabench.sh
```

The command preview contains:

```text
DRY_RUN=1 ... BENCH_MODEL_PROFILE=gpt54mini_8130 ... OPENAI_BASE_URL=http://100.96.1.101:18540/v1 ... VITA_DOMAIN=delivery VITA_TASK_SET_NAME=delivery VITA_TASK_IDS=10711001 NUM_TASKS=1 NUM_TRIALS=1 MAX_CONCURRENCY=1 VITA_MAX_STEPS=20 VITA_ENABLE_THINK=0 VITA_LANGUAGE=english run_vitabench.sh
```

No `run_vitabench_full.sh` appears in the one-task run.

## Validation Commands

```bash
python3 -m unittest scripts.test_agentic_bench_suite
```

Result:

```text
Ran 6 tests in 0.122s

OK
```

YAML parse / launcher-load check:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util

root = Path.cwd()
suite_path = root / 'manifests' / 'suite.example.yaml'
try:
    import yaml
except ModuleNotFoundError:
    yaml = None
if yaml is not None:
    data = yaml.safe_load(suite_path.read_text(encoding='utf-8'))
    print('pyyaml_safe_load=ok')
    print('bench_count=' + str(len(data['benches'])))
else:
    print('pyyaml_safe_load=skipped_missing_pyyaml')

spec = importlib.util.spec_from_file_location('agentic_bench_suite', root / 'scripts' / 'agentic_bench_suite.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module.load_suite_config(suite_path)
ids = [bench['id'] for bench in config['benches']]
print('launcher_load_suite_config=ok')
print('has_vitabench_delivery_one_task_smoke=' + str('vitabench_delivery_one_task_smoke' in ids).lower())
PY
```

Result:

```text
pyyaml_safe_load=skipped_missing_pyyaml
launcher_load_suite_config=ok
has_vitabench_delivery_one_task_smoke=true
```

## Current Verification Pass

This pass found the assigned lane files already dirty and preserved the existing
manifest/test changes. Re-ran the relevant checks from the repository root on
2026-06-25 without using `swe_dev` / `swe-dev`.

```bash
python3 -m unittest scripts.test_agentic_bench_suite
```

Exit code: `0`.

```text
Ran 6 tests in 0.151s

OK
```

```bash
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only vitabench_delivery_one_task_smoke --model-profile dev_proxy_gpt54mini_8130
```

Exit code: `0`.

Confirmed fields in the JSON plan:

```text
bench_id=vitabench_delivery_one_task_smoke
script_path=run_vitabench.sh
model.profile_id=dev_proxy_gpt54mini_8130
runtime_env.BENCH_MODEL_PROFILE=gpt54mini_8130
runtime_env.OPENAI_BASE_URL=http://100.96.1.101:18540/v1
runtime_env.VITA_DOMAIN=delivery
runtime_env.VITA_TASK_SET_NAME=delivery
runtime_env.VITA_TASK_IDS=10711001
runtime_env.NUM_TASKS=1
runtime_env.NUM_TRIALS=1
runtime_env.MAX_CONCURRENCY=1
runtime_env.VITA_MAX_STEPS=20
runtime_env.VITA_ENABLE_THINK=0
runtime_env.VITA_LANGUAGE=english
command_preview includes run_vitabench.sh and does not include run_vitabench_full.sh
```

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util

root = Path.cwd()
suite_path = root / 'manifests' / 'suite.example.yaml'
try:
    import yaml
except ModuleNotFoundError:
    yaml = None
if yaml is not None:
    data = yaml.safe_load(suite_path.read_text(encoding='utf-8'))
    print('pyyaml_safe_load=ok')
    print('bench_count=' + str(len(data['benches'])))
else:
    print('pyyaml_safe_load=skipped_missing_pyyaml')

spec = importlib.util.spec_from_file_location('agentic_bench_suite', root / 'scripts' / 'agentic_bench_suite.py')
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
config = module.load_suite_config(suite_path)
ids = [bench['id'] for bench in config['benches']]
print('launcher_load_suite_config=ok')
print('has_vitabench_delivery_one_task_smoke=' + str('vitabench_delivery_one_task_smoke' in ids).lower())
PY
```

Exit code: `0`.

```text
pyyaml_safe_load=skipped_missing_pyyaml
launcher_load_suite_config=ok
has_vitabench_delivery_one_task_smoke=true
```
