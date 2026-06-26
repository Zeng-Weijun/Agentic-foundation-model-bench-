# Round37 suite execute / tau3 parser diff review

Scope: report-only review for runner/results lane. Reviewed refreshed remote worktree only; no production code, manifests, tests, README, Docker state, benchmark runs, model calls, commits, or pushes. Current observed head: `9fc70ac` on `feat/image-warmup-policy`.

## NO-ISSUE: execute fail-closed path for non-executable adapters

Status: PASS / no new issue.

Evidence:
- `scripts/agentic_bench_suite.py:1795-1799` refuses `_execute_plan` before creating the controller output root when any selected run has `adapter_status` outside `EXECUTABLE_ADAPTER_STATES`.
- `scripts/agentic_bench_suite.py:1337-1359` also guards `_run_one` with `fail:adapter_not_wired`, rc 2, and no adapter command execution if called directly.
- `scripts/test_agentic_bench_suite.py:593-622` covers direct `_run_one` behavior: rc 2, `fail:adapter_not_wired`, no preflight marker, no adapter marker, and guard text in the log.
- Fresh execute probe selected `terminal_bench_2_1_image_smoke`; inner suite rc was 2 with stderr `refusing --execute because adapters are not wired: terminal_bench_2_1_image_smoke`, and no files were created under the requested output directory.

Impact reviewed:
- The current path does not fake-green `summary.json`; for the unwired image-smoke adapter, it exits before `run_manifest.json` or `summary.json` is materialized.
- This behavior is distinct from image-preflight-only readiness and does not mark Terminal-Bench task success.

## FIXED-DURING-REVIEW: tau3 verifier_status overclaim predicate

Status: fixed after initial probe; no ISSUE-READY item remains.

Old finding observed before orchestrator refresh:
- A synthetic tau3 run wrote `tau3_result_summary.json` with `status=direct_command_failed`, `direct_rc=7`, `reward=1.0`, and `verifier_status=passed`, then exited 7.
- Previous observed output incorrectly had `row_benchmark_status pass`, `benchmark_status pass`, `passed True`, and `score_claim_valid True` despite the adapter failure status.

Current fix evidence:
- `scripts/agentic_bench_suite.py:1632-1636` now treats tau3 as passed only when the top-level status is pass-like (`pass`, `passed`, `success`, `succeeded`) or when top-level status is empty and `verifier_status=passed`.
- `scripts/agentic_bench_suite.py:1646-1656` derives normalized `status`, `passed`, `score_claim_valid`, `failure_category`, `tau3_status`, and `verifier_status` from that guarded predicate.
- `scripts/test_agentic_bench_suite.py:765-823` adds the inconsistent-summary regression where `status=errors`, `verifier_status=passed`, and `reward=1.0` must remain benchmark `fail` with `score_claim_valid` false.
- Fresh replay of the original bad shape now returns `execute_rc 1`, `row_execution_status fail`, `row_benchmark_status fail`, `row_score_claim_valid False`, normalized `benchmark_status fail`, `passed False`, `score_claim_valid False`, `tau3_status direct_command_failed`, and `verifier_status passed`.

Dedup:
- This was a concrete #1-style execution-vs-benchmark-status overclaim in the tau3 parser. It is fixed in the refreshed diff, so it should not be filed as a new issue.
- Broader non-tau3 parser/provenance coverage from Round36 remains separate and is not widened by this diff.

## FIXED-DURING-REVIEW: syntax error in new tau3 test fixture

Status: fixed after initial probe; no ISSUE-READY item remains.

Old finding observed before orchestrator refresh:
- `python3 -m unittest scripts.test_agentic_bench_suite` previously failed at import time with `SyntaxError: unterminated string literal (detected at line 772)` in the newly added tau3 inconsistent-summary test.

Current fix evidence:
- `scripts/test_agentic_bench_suite.py:771-787` now writes the fixture script as valid concatenated strings with escaped newlines.
- Focused regression command passed with rc 0 and `Ran 1 test`.
- Full relevant suite command passed with rc 0 and observed `Ran 42 tests` in this checkout.

## NO-ISSUE: tau3 native artifact provenance and log-safety in current diff

Status: PASS / no new issue in the refreshed diff.

Evidence:
- `scripts/agentic_bench_suite.py:1668-1686` records `source.native_artifacts` as allowlisted/pointer metadata: `tau3_result_summary` is `parsed` with `read_policy=allowlist_json`, while `artifact_manifest.json` is `referenced_not_read` with `read_policy=pointer_only`.
- `scripts/test_agentic_bench_suite.py:692-763` verifies nonzero tau3 adapter exit still parses the native summary from `BENCH_RUN_DIR`, preserves counts, records source metadata, and does not serialize the test sentinel or API-key env name from adjacent artifacts.
- The parser does copy allowlisted `short_failure_note` from `tau3_result_summary.json`; that remains acceptable only if the tau3 wrapper keeps that field sanitized. Any future raw stderr/log copy belongs under the existing redaction/provenance issues, not a new Round37 diff regression.

## Commands and rc

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_round37_final && wc -l /tmp/codex_workflow_round37_final`: rc 0, 973 lines.
- `ssh dev 'cd ... && pwd && git branch --show-current && git rev-parse --short HEAD && git status --short --untracked-files=all && git diff --stat && nl -ba ...'`: rc 0. Head `9fc70ac`; no tracked diff in `git diff --stat`; unrelated untracked Round38 artifacts present.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agentic_bench_suite.AgenticBenchSuiteTest.test_tau3_native_summary_does_not_claim_pass_when_status_errors_despite_verifier_passed; ...'`: rc 0. Focused test rc 0.
- `ssh dev 'cd ... && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agentic_bench_suite; ...'`: rc 0. Full relevant suite rc 0, observed 42 tests.
- Synthetic original tau3 bad-shape replay via `python3 -`: rc 0. Current normalized and summary benchmark statuses are fail, and score claim is invalid.
- `ssh dev 'cd ... && rm -rf /tmp/round37_execute_fail_closed_current ... python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --execute --only terminal_bench_2_1_image_smoke --output-dir /tmp/round37_execute_fail_closed_current ...'`: wrapper rc 0; inner suite `EXECUTE_RC=2`; no output files created.

## Final decision

No ISSUE-READY finding in the refreshed Round37 diff. The two initially observed regressions were fixed during review, and the remaining parser/provenance cautions dedup to existing runner-results issues rather than a new confirmed root cause.

## Report validation

- `test -f _coordination/20260625_harbor_bench/lanes/runner-results-round37-diff-review.md`: rc 0.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runner-results-round37-diff-review.md`: rc 0. Note: file is untracked, so this scoped tracked-diff check is clean but does not include file content.
- `git diff --no-index --check /dev/null _coordination/20260625_harbor_bench/lanes/runner-results-round37-diff-review.md`: rc 1 with zero output lines; rc 1 is expected for a no-index added file diff, and zero output means no whitespace check findings.
- Trailing whitespace scan on the report: rc 1, no matches.
- Bounded secret-value/assignment scan on the report: rc 1, no matches.
- `git status --short --untracked-files=all | grep __pycache__ || true`: no pycache entries observed after tests.
