# Round35 review: SWE-bench django10097 helper readiness

## Scope

Report-only review of the current unstaged changes around `swebench_verified_django10097_swe_agent_image_smoke`, `manifests/suite.example.yaml`, `scripts/test_agentic_bench_suite.py`, and the readiness aggregation path in `scripts/agentic_bench_suite.py`. No production code, manifests, or tests were edited by this lane.

Remote worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`

Observed branch/head: `feat/image-warmup-policy` at `bf25a33`.

## Findings

### PASS: helper suite entry is scoped as image smoke and does not replace the full SWE-bench Verified entries

- Location: `manifests/suite.example.yaml:229`
- Evidence: the new entry `swebench_verified_django10097_swe_agent_image_smoke` is `adapter: swe_agent`, uses `readiness_role: image_smoke`, points to `manifests/images/swebench_verified_django10097.yaml`, sets `image_policy: required`, and pins `SWEBENCH_INSTANCE_ID: django__django-10097` at `manifests/suite.example.yaml:229-245`.
- Impact reviewed: this is an image-smoke/helper entry, not a full target replacement. The original full-ish `swebench_verified_swe_agent` row still points at `manifests/images/swebench_verified.yaml` with `image_policy: optional` at `manifests/suite.example.yaml:214-228`, so the full readiness blocker remains visible.
- Repro/probe: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --only swebench_verified_django10097_swe_agent_image_smoke --json` returned rc 0 and produced one run with `image_preflight.manifest=manifests/images/swebench_verified_django10097.yaml`, `image_preflight.policy=required`, `image_preflight.required=True`, `SWEBENCH_INSTANCE_ID=django__django-10097`, and `SWEBENCH_MODE=smoke`.

### PASS: readiness aggregation stays blocked for full SWE-bench Verified even though the helper is ready

- Location: `scripts/agentic_bench_suite.py:987`
- Evidence: `build_readiness_report` filters `full_entry_reports` and uses them as `aggregation_entries` when any full entries exist at `scripts/agentic_bench_suite.py:987-987`. Target status is derived from `ready_entries` inside those aggregation entries at `scripts/agentic_bench_suite.py:991-1010`, while `ready_entry_count` still exposes all ready entries for observability at `scripts/agentic_bench_suite.py:1021-1022`.
- Repro/probe: `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --target-benches swe-bench-verified --json` returned rc 1, expected for a blocked readiness target. Parsed result:
  - `target_id=swebench_verified_multi`
  - `status=blocked`
  - `blockers=image_manifest_not_materialized`
  - `entry_count=5`
  - `aggregation_entry_count=4`
  - `ready_entry_count=1`
  - `aggregation_ready_entry_count=0`
  - helper entry `swebench_verified_django10097_swe_agent_image_smoke` was `image_smoke ready=True`
  - the four full entries remained `ready=False` with `image_manifest_not_materialized`
- Impact reviewed: this preserves the intended distinction between a usable one-task image-smoke helper and the blocked full SWE-bench Verified target.

### PASS: regression coverage exercises the helper and blocked aggregation behavior

- Location: `scripts/test_agentic_bench_suite.py:1065`
- Evidence: `test_example_manifest_has_enabled_swebench_verified_django10097_image_smoke_without_full_readiness` verifies the helper is enabled, uses `readiness_role: image_smoke`, uses the django10097 manifest, pins `SWEBENCH_INSTANCE_ID`, builds a dry-run with that environment variable, and asserts the SWE-bench target remains blocked with `image_manifest_not_materialized` at `scripts/test_agentic_bench_suite.py:1065-1085`.
- Test evidence: focused unit run returned rc 0 for:
  - `test_example_manifest_has_enabled_swebench_verified_django10097_image_smoke_without_full_readiness`
  - `test_readiness_report_covers_target_benches_and_blocks_unready_assets`
  - `test_cli_dry_run_rejects_explicit_empty_plan_without_allow_empty_plan`
- Full static suite evidence: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agentic_bench_suite` returned rc 0, `Ran 38 tests in 2.815s`, `OK`.
- Optional hardening note: the helper test currently checks blocked status and blocker text. It would be slightly stronger if it also asserted `aggregation_entry_count == 4` and `aggregation_ready_entry_count == 0`, matching the probe above, but this is not a blocking issue because the current probe and aggregation implementation already satisfy the contract.

## ISSUE-READY findings

None found in this review round.

## Commands and exit codes

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_read_round35 && wc -l /tmp/codex_workflow_read_round35`: rc 0, read 973 lines.
- `ssh dev 'cd <worktree> && pwd && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all'`: rc 0, branch `feat/image-warmup-policy`, head `bf25a33`; unstaged modified files observed in `manifests/suite.example.yaml`, `scripts/agentic_bench_suite.py`, and `scripts/test_agentic_bench_suite.py`.
- `git diff -- manifests/suite.example.yaml tests scripts/test_agentic_bench_suite.py`: rc 0.
- `git diff -- scripts/agentic_bench_suite.py`: rc 0.
- `nl -ba`/`grep` static reads for the modified suite, runner, and test regions: rc 0.
- Focused unit command: rc 0, 3 tests OK.
- SWE-bench readiness probe: rc 1, expected blocked target; parsed evidence listed above.
- Helper dry-run probe: rc 0; parsed evidence listed above.
- Full unit command: rc 0, 38 tests OK.

## Review conclusion

PASS. The current unstaged helper entry and tests preserve the intended readiness semantics: django10097 can be represented as a required image-smoke helper, while full SWE-bench Verified remains blocked until the broad manifest is materialized.
