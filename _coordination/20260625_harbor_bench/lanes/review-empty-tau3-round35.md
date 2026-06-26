# Round35 Review: Empty `--only` And Tau3 Full Readiness

Scope: report-only review of the current unstaged diff for `scripts/agentic_bench_suite.py` and `scripts/test_agentic_bench_suite.py`, focused on explicit `--only` empty-plan handling and tau3 full readiness blockers.

Remote worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`

Observed branch/head: `feat/image-warmup-policy` / `bf25a33`

Files reviewed:

- `scripts/agentic_bench_suite.py`
- `scripts/test_agentic_bench_suite.py`
- `manifests/suite.example.yaml` was read as context because the tests and readiness probes depend on the active tau3 and SWE helper rows.
- Shared runner `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh` was read only to confirm tau3 runtime defaults.

## PASS: explicit `--only` empty plans now fail closed unless allowed

Status: PASS

Relevant code:

- `scripts/agentic_bench_suite.py:1755-1761`
- `scripts/test_agentic_bench_suite.py:530-591`

What changed:

- The CLI now rejects any empty run plan caused by an explicit `--only` filter when `--allow-empty-plan` is not present.
- This applies beyond `--image-preflight-only`; a dry-run with `--only` selecting no enabled runs now exits rc `2` instead of printing a green empty JSON plan.
- `--allow-empty-plan` preserves an intentional empty-plan escape hatch.

Repro / evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/run_suite_from_yaml.sh   manifests/suite.example.yaml   --dry-run --json --only definitely_not_a_bench
```

Result: rc `2`, stderr contained:

```text
no runs selected for --only definitely_not_a_bench
```

Allow-empty probe:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/run_suite_from_yaml.sh   manifests/suite.example.yaml   --dry-run --json --only definitely_not_a_bench --allow-empty-plan
```

Result: rc `0`, JSON had `runs == []`.

Focused unit coverage passed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_cli_dry_run_rejects_explicit_empty_plan_without_allow_empty_plan   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_image_preflight_only_fails_when_filter_selects_no_runs   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_tau3_full_entry_stays_blocked_when_enabled_with_smoke_params   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_example_manifest_has_enabled_tau3_oracle_direct_smoke_without_full_readiness
```

Result: rc `0`, `Ran 4 tests ... OK`.

Residual risk: none found for the reviewed `--only` path. The error reports the raw `--only` string, which is acceptable and useful for operator feedback.

## RESOLVED/PASS: tau3 full readiness now blocks missing mode params

Previous severity: medium

Refresh status: RESOLVED/PASS after orchestrator fix.

Location:

- `scripts/agentic_bench_suite.py:797-806`
- Runtime default source: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/run_tau3_bench.sh:10-11` and `54-58`
- Test gap: `scripts/test_agentic_bench_suite.py:986-1004` covers the current smoke-param row but not missing tau3 params.

Original pre-fix problem:

The earlier `_bench_specific_readiness_blockers()` only blocked tau3 full readiness when `TAU3_MODE` is present and not `full`, and when `TAU3_LIMIT` is present and not `0`:

```python
tau3_mode = str(params.get("TAU3_MODE", "")).strip().lower()
if tau3_mode and tau3_mode != "full":
    blockers.append("tau3_full_smoke_mode")
tau3_limit = str(params.get("TAU3_LIMIT", "")).strip()
if tau3_limit and tau3_limit != "0":
    blockers.append("tau3_full_limit_set")
```

But the shared tau3 runner defaults missing values to smoke mode and a one-task limit:

```bash
TAU3_MODE="${TAU3_MODE:-smoke}"
TAU3_LIMIT="${TAU3_LIMIT:-1}"
```

Before the orchestrator fix, that meant a future config could remove `params` from the full tau3 row, set `enabled: true`, `adapter_status: wired_legacy`, and `image_policy: required`, and the static readiness gate will report the full tau3 target ready even though the actual runner would still execute smoke semantics by default.

Original static repro:

```python
import copy, importlib.util
from pathlib import Path
root = Path.cwd()
spec = importlib.util.spec_from_file_location("suite", root / "scripts/agentic_bench_suite.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
config = mod.load_suite_config(root / "manifests/suite.example.yaml")
b = next(x for x in config["benches"] if x["id"] == "tau3_bench")
b.update({"enabled": True, "adapter_status": "wired_legacy", "image_policy": "required"})
b.pop("params", None)
report = mod.build_readiness_report(config, suite_path=root / "manifests/suite.example.yaml", target_benches=["tau3-bench"])
```

Original pre-fix observed result, retained for comparison:

```text
remove_tau3_params_but_required {"full_blockers": [], "full_ready": true, "target_blockers": [], "target_status": "ready"}
```

Original pre-fix control probes:

```text
flip_current_enabled_wired {"full_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_set", "tau3_full_image_policy_not_required"], "full_ready": false, "target_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_set", "tau3_full_image_policy_not_required"], "target_status": "blocked"}
explicit_full_required_limit0 {"full_blockers": [], "full_ready": true, "target_blockers": [], "target_status": "ready"}
```

Pre-fix impact, now resolved by the refresh below:

- The earlier blocker fixed the current suite row, but was not fail-closed for absent tau3 full-run parameters.
- Before the fix, a maintainer could make a plausible cleanup change by deleting smoke-only `params` while enabling/wiring the full tau3 row and setting image policy to required. Static readiness would then go green for the full tau3 target while the runner still defaults to `TAU3_MODE=smoke` and `TAU3_LIMIT=1`.
- Before the fix, this recreated the same class of unsafe full-readiness claim the patch is trying to prevent, only through omission rather than explicit smoke values.

Fix requested by the original review, now implemented:

- Make full tau3 readiness require an explicit full-mode declaration. For example:

```python
tau3_mode = str(params.get("TAU3_MODE", "")).strip().lower()
if tau3_mode != "full":
    blockers.append("tau3_full_mode_not_full")
```

- Keep the nonzero limit check, but consider naming it so it also covers default-risk clearly. If `TAU3_MODE=full` makes `TAU3_LIMIT` irrelevant in the runner, allow missing/`0`; otherwise require an explicit `TAU3_LIMIT: 0` or a full expected task count.
- Add a regression test that mutates `tau3_bench` to enabled + wired + required and removes `params`, then asserts target status remains `blocked` with a tau3 full-mode blocker.

Dedup note:

- This was a narrower follow-up to the tau3 full-readiness blocker issue recorded in the Round34 tau3 lane. The previous diff partially fixed the explicit smoke-param case; this finding is the remaining omission/default path.



### Refresh After Orchestrator Fix

Status: RESOLVED/PASS

The latest diff changes `_bench_specific_readiness_blockers()` so full tau3 readiness now requires explicit full-mode semantics:

- `scripts/agentic_bench_suite.py:801-803`: missing or non-`full` `TAU3_MODE` adds `tau3_full_smoke_mode`.
- `scripts/agentic_bench_suite.py:804-808`: missing or nonzero `TAU3_LIMIT` adds `tau3_full_limit_not_disabled`, and explicit nonzero values also add `tau3_full_limit_set`.
- `scripts/agentic_bench_suite.py:809-811`: image policy falls back through `image_config.default_policy` before requiring `required`.
- `scripts/test_agentic_bench_suite.py:1005-1022`: new regression `test_tau3_full_entry_requires_explicit_full_mode_and_disabled_limit` covers the missing-params case.

Rerun missing-params repro result:

```text
remove_tau3_params_but_required {"full_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_not_disabled"], "full_ready": false, "target_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_not_disabled"], "target_status": "blocked"}
```

Control results:

```text
flip_current_enabled_wired {"full_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_set", "tau3_full_limit_not_disabled", "tau3_full_image_policy_not_required"], "full_ready": false, "target_blockers": ["tau3_full_smoke_mode", "tau3_full_limit_set", "tau3_full_limit_not_disabled", "tau3_full_image_policy_not_required"], "target_status": "blocked"}
explicit_full_required_limit0 {"full_blockers": [], "full_ready": true, "target_blockers": [], "target_status": "ready"}
```

Focused tau3 tests rerun:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_tau3_full_entry_stays_blocked_when_enabled_with_smoke_params   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_tau3_full_entry_requires_explicit_full_mode_and_disabled_limit   scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_example_manifest_has_enabled_tau3_oracle_direct_smoke_without_full_readiness
```

Result: rc `0`, `Ran 3 tests ... OK`.

Current tau3 readiness CLI still fails closed:

```text
TAU3_READINESS_RC=1
status=blocked
blockers=[no_enabled_suite_entry, suite_entry_disabled, adapter_not_wired, tau3_full_smoke_mode, tau3_full_limit_set, tau3_full_limit_not_disabled, tau3_full_image_policy_not_required]
tau3_bench.ready=false
tau3_bench_oracle_direct_smoke.ready=true, role=image_smoke
```

Conclusion: the earlier ISSUE-READY finding is fixed by the latest diff. Keep this section as resolved evidence rather than an open issue.

## PASS: current tau3 suite row remains blocked and helper does not satisfy full target

Status: PASS with the issue above noted for missing params.

Relevant code:

- `scripts/agentic_bench_suite.py:792-810`
- `scripts/agentic_bench_suite.py:923-963`
- `scripts/agentic_bench_suite.py:985-1007`
- `scripts/test_agentic_bench_suite.py:986-1004`

Current CLI readiness probe:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/run_suite_from_yaml.sh   manifests/suite.example.yaml   --readiness --target-benches tau3-bench --json
```

Result: rc `1`, target blocked. Parsed summary:

```text
status=blocked
blockers=[no_enabled_suite_entry, suite_entry_disabled, adapter_not_wired, tau3_full_smoke_mode, tau3_full_limit_set, tau3_full_image_policy_not_required]
aggregation_entry_count=1
ready_entry_count=1
full.ready=false
helper.ready=true
helper.readiness_role=image_smoke
```

This confirms the image-smoke helper remains ready but excluded from full target aggregation. The full tau3 row remains blocked under the current checked-in suite state.

## Commands Run

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`; rc `0`.
- Memory grep for relevant Agentic-foundation/TB2/rootless context; rc `0`.
- Remote status/diff reads on `dev`; rc `0`. Observed branch/head `feat/image-warmup-policy` / `bf25a33`; modified files: `manifests/suite.example.yaml`, `scripts/agentic_bench_suite.py`, `scripts/test_agentic_bench_suite.py`.
- `git diff -- scripts/agentic_bench_suite.py scripts/test_agentic_bench_suite.py`; rc `0`.
- `git diff -- manifests/suite.example.yaml`; rc `0`, read only for context.
- Static line reads for suite code/tests and shared tau3 runner; rc `0`.
- Focused unittest command listed above; rc `0`.
- CLI `--only definitely_not_a_bench`; wrapper rc `0`, inner command rc `2` captured.
- CLI `--only definitely_not_a_bench --allow-empty-plan`; wrapper rc `0`, inner command rc `0` captured.
- CLI tau3 readiness probe; wrapper rc `0`, inner command rc `1` captured.
- In-memory tau3 readiness mutation probes; rc `0`.



### Refresh Commands Run

- Remote status/diff refresh on `dev`; rc `0`. Observed branch/head `feat/image-warmup-policy` / `bf25a33`; modified files remain `manifests/suite.example.yaml`, `scripts/agentic_bench_suite.py`, and `scripts/test_agentic_bench_suite.py`, plus review reports.
- `git diff -- scripts/agentic_bench_suite.py scripts/test_agentic_bench_suite.py`; rc `0`; latest diff includes explicit full-mode and disabled-limit blockers plus the missing-params regression test.
- Missing-params tau3 repro and controls; rc `0`; results listed in the resolved section.
- Focused tau3 tests; rc `0`, three tests passed.
- Tau3 readiness CLI probe; wrapper rc `0`, inner readiness rc `1`; current full target remains blocked while image-smoke helper remains ready but non-aggregating.

## Validation

- `git diff --check -- _coordination/20260625_harbor_bench/lanes/review-empty-tau3-round35.md`; rc `0`, no output.
- Because the report is untracked, `git diff --check --no-index -- /dev/null _coordination/20260625_harbor_bench/lanes/review-empty-tau3-round35.md` was also run; rc `1` because the files differ, with no whitespace diagnostics printed.
- `grep -n "[[:blank:]]$" _coordination/20260625_harbor_bench/lanes/review-empty-tau3-round35.md || true`; rc `0`, no output, interpreted as no trailing whitespace.
- Bounded secret-like scan for API keys, access/auth tokens, Authorization/Bearer assignments, or private-key headers; rc `0`, no output.
- `git status --short --untracked-files=all`; rc `0` before final write showed only the reviewed production diffs plus this report and concurrent `review-swe-helper-round35.md`; I did not edit production files or the other report.
