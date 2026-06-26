# Round39 runner/results one-command bug hunt

Scope: continuous bug-hunt lane `surface:54` for runner/results only. I read `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` first, then worked only through `ssh dev` in the shared worktree. No production code, manifests, tests, README, Docker state, benchmark execution, model calls, commits, pushes, or issue edits were performed. This report is the only intended file write.

Observed worktree:
- Path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
- Branch/head: `feat/image-warmup-policy` at `9f480fe`
- Initial status already had `?? scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc`; I did not create or remove it.

## Final decision

No new ISSUE-READY runner/results bug was confirmed in Round39.

The current runner surfaces still have important COMMENT-READY gaps, but they dedup to existing issues/reports:
- #1: benchmark result status and suite process/summary status remain distinct; non-RepoZero/tau3 parsers are still missing.
- #2: deterministic `run_id`, `run_dir`, `BENCH_RUN_DIR`, and `RUN_TAG` remain the known invocation-unique output problem.
- #10/#13: raw/native sidecars and image-preflight logs still need strict allowlist/redaction handling.
- #12: normalized result/source provenance still needs broader native artifact and image-check pointer coverage.

## Evidence matrix

### PASS: readiness does not overclaim the nine tracked full targets

Locations:
- `scripts/agentic_bench_suite.py:29-50` defines the tracked readiness targets: SWE-bench Verified multi, Terminal Bench 2.1, MCP-Atlas, Tool-Decathlon, tau3-bench, programbench, RepoZero, NL2Repo, and DeepSWE.
- `scripts/agentic_bench_suite.py:781-789` classifies helper rows as `image_smoke`.
- `scripts/agentic_bench_suite.py:969-1018` aggregates readiness from full-role rows when full rows exist, so image-smoke helpers cannot satisfy a full target.

Probe:
- `./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --readiness --target-benches "SWE-bench Verified multi,Terminal Bench 2.1,MCP-Atlas,Tool-Decathlon,tau3-bench,programbench,RepoZero,NL2Repo,DeepSWE" --json`
- rc 1.
- Counts: `ready=1`, `blocked=8`, `missing=0`, `total=9`.
- RepoZero was the only ready target.
- SWE-bench Verified multi, Terminal Bench 2.1, MCP-Atlas, Tool-Decathlon, tau3-bench, programbench, NL2Repo, and DeepSWE were blocked.
- Helper evidence did not satisfy full targets: SWE-bench had `entry_ready=1` but `aggregation_ready=0`; tau3 had `entry_ready=1` but `aggregation_ready=0`; Terminal Bench 2.1 had `aggregation_ready=0` and full blockers.

Dedup:
- No new issue. This aligns with prior readiness-role fixes and Round36/Round37 findings.

### PASS: disabled/pending full targets fail closed instead of becoming empty green runs

Locations:
- `scripts/agentic_bench_suite.py:1118-1121` skips disabled suite entries when building a run plan.
- `scripts/agentic_bench_suite.py:1876-1882` returns rc 2 for an empty `--only` selection unless explicitly allowed.
- `manifests/suite.example.yaml:277-285` keeps full Terminal Bench 2.1 disabled and pending adapter.
- `manifests/suite.example.yaml:304-312`, `314-322`, `324-338`, `360-368`, and `370-378` keep MCP-Atlas, Tool-Decathlon, full tau3, programbench, and NL2Repo disabled/pending.

Probe:
- `--dry-run --only terminal_bench_2_1`: rc 2, stderr `no runs selected for --only terminal_bench_2_1`, stdout empty.
- `--dry-run --only mcp_atlas`: rc 2, stdout empty.
- `--dry-run --only tool_decathlon`: rc 2, stdout empty.
- `--dry-run --only programbench`: rc 2, stdout empty.
- `--dry-run --only nl2repo`: rc 2, stdout empty.
- `--dry-run --only tau3_bench`: rc 2, stdout empty.

Dedup:
- No new issue. This is the desired fail-closed behavior for selected disabled full targets.

### PASS with operator caveat: execute refuses pending image-smoke rows before launching adapters

Locations:
- `scripts/agentic_bench_suite.py:1795-1799` refuses `--execute` if any selected run has a non-executable adapter state.
- `scripts/agentic_bench_suite.py:1337-1359` also guards direct `_run_one()` calls with `fail:adapter_not_wired`.
- `manifests/suite.example.yaml:287-302` enables `terminal_bench_2_1_image_smoke` with `adapter_status: pending_adapter` and required image preflight.

Probe:
- `./scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --execute --output-dir /tmp/round39_execute_default`
- rc 2.
- stderr: `refusing --execute because adapters are not wired: terminal_bench_2_1_image_smoke`.
- No controller output files were created under `/tmp/round39_execute_default`.

Interpretation:
- This does not overclaim benchmark success; it fails before adapter execution and before writing a green `summary.json`.
- Operator caveat: default `--execute` currently refuses the whole plan because an enabled image-smoke helper has `pending_adapter`. That is conservative, but a future one-command UX may want an explicit mode that excludes image-smoke-only pending rows from adapter execution after image preflight. This is not ISSUE-READY because the current behavior is fail-closed and prior Round37 covered the same adapter guard.

### COMMENT-READY for #1: suite status remains execution-only when a parsed benchmark fails

Locations:
- `scripts/agentic_bench_suite.py:1690-1718` parses RepoZero native log summaries and can return `benchmark_result.status=fail`.
- `scripts/agentic_bench_suite.py:1755-1789` writes row-level `execution_status`, `benchmark_status`, and `score_claim_valid` into the normalized result and summary row.
- `scripts/agentic_bench_suite.py:1803-1818` sets suite `summary.status` and process rc from adapter exit code only, not from parsed benchmark failure.
- `scripts/test_agentic_bench_suite.py:650-690` intentionally covers this split: RepoZero adapter exit 0 with `ALL_PASS_CASES 0 / 1` and `TESTS 0 / 60` yields row `benchmark_status=fail` while `_execute_plan()` returns rc 0.

Synthetic repro:
- A no-benchmark temp plan ran a command that printed RepoZero failure counters and exited 0.
- Probe rc 0.
- Current result: `execute_rc=0`, `summary_status=0`, row `status=pass`, `execution_status=pass`, `benchmark_status=fail`, `score_claim_valid=False`, `failure_category=agent_generation_failed`, normalized parser `parsed`, tasks `0/1`, tests `0/60`.

Impact:
- A CI/operator that only checks process rc or top-level `summary.status` can miss a semantic benchmark failure even though row-level result artifacts are correct.
- This is the same status-split root as #1, not a new issue. It is valuable fixture evidence if #1 is extended to define whether top-level suite rc should include benchmark failure, or whether a separate `benchmark_status_counts` / `overall_benchmark_status` is enough.

Fix direction for #1, not a new ticket:
- Keep `execution_status` and adapter rc independent.
- Add explicit suite-level benchmark aggregation fields, for example `benchmark_status_counts`, `overall_benchmark_status`, and `score_claim_valid_counts`.
- Decide whether `--execute` process rc should fail on parsed benchmark failure by default or expose a flag such as `--fail-on-benchmark-fail`.

### COMMENT-READY for #1/#12: parser coverage is still narrow outside RepoZero and tau3

Locations:
- `scripts/agentic_bench_suite.py:1619-1687` parses tau3 native summaries from `run_dir` / `runtime_env.BENCH_RUN_DIR` with pointer-only source metadata.
- `scripts/agentic_bench_suite.py:1690-1718` parses RepoZero log counters.
- `scripts/agentic_bench_suite.py:1721-1752` returns generic `no_parser/unknown/native_artifact_missing` for successful unsupported adapters, and `not_run/infra_error/adapter_crash` for nonzero unsupported adapters.

Static parser matrix, exit 0:
- SWE-bench Verified qwen-code, mini-swe-agent, swe-agent, and OpenHands: `no_parser`, `unknown`, `native_artifact_missing`.
- Terminal Bench 2.1: `no_parser`, `unknown`, `native_artifact_missing`.
- MCP-Atlas, Tool-Decathlon, programbench, NL2Repo: `no_parser`, `unknown`, `native_artifact_missing`.
- DeepSWE: `no_parser`, `unknown`, `native_artifact_missing`.
- Existing VitaBench and CoCoA rows also still return `no_parser`, `unknown`, `native_artifact_missing`.

Static parser matrix, exit 7:
- Unsupported named adapters return `not_run`, `infra_error`, `adapter_crash`, `metric=adapter_exit_code`.

Positive controls:
- RepoZero pass/fail log probes parse to `parsed/pass` and `parsed/fail` respectively.
- Synthetic tau3 direct summary with `status=passed`, `verifier_status=passed`, and `reward=1.0` parses to `parsed/pass`, `passed=True`, `score_claim_valid=True`, with `source.native_artifacts` containing `tau3_result_summary`.

Dedup:
- No new issue. This is exactly the open parser/provenance surface from #1/#12, with current tau3 and RepoZero progress noted.

### PASS: current active naming no longer exposes tau2 or Terminal-Bench 2.0 as active targets

Locations/evidence:
- `manifests/suite.example.yaml:277-302` uses Terminal Bench 2.1 full/helper rows.
- `manifests/suite.example.yaml:324-358` uses tau3-bench full/helper rows.
- `scripts/test_agentic_bench_suite.py:1098-1120` guards against active tau2 and active Terminal-Bench 2.0 suite rows.
- Active scan over `README.md`, `scripts`, `manifests`, and `docs` found no active `tau2-bench`, `tau2_paper_core`, `terminal_bench_2_0`, or Terminal-Bench 2.0 target references except the test guard itself.

Historical matches:
- Historical `reports/` and lane ledgers still contain tau2/TB2.0 context, including prior Round33 evidence. Those are not active runner targets and are already covered by docs-taxonomy/Round33 notes.

Dedup:
- No new issue. The prior active Terminal-Bench 2.0 drift was fixed before this round.

### COMMENT-READY: default dry-run includes enabled rows outside the nine-target readiness set

Evidence:
- Current default plan has 12 enabled runs at suite concurrency 40 and image-preflight concurrency 4.
- Runs include the nine-target helpers/full candidates plus existing VitaBench/CoCoA rows: `vitabench_full`, `vitabench_delivery_one_task_smoke`, and `cocoabench`.
- `READINESS_TARGETS` currently tracks the nine requested bench families and does not include VitaBench or CoCoA.

Interpretation:
- This is not a new runner/results issue for the requested nine-family surface, and VitaBench/CoCoA parser/redaction gaps are already tracked in prior reports (#1/#9/#10/#12/#13).
- It is worth documenting for one-command UX: readiness for the nine tracked targets is not the same as readiness for every enabled row in the default execute plan. If the default plan remains broader than the readiness target list, add an explicit `plan_targets` or `non_readiness_rows` field to readiness output rather than treating this as a hidden green state.

## Commands and rc

- `cat /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md >/tmp/codex_workflow_round39 && wc -l /tmp/codex_workflow_round39`: rc 0, 973 lines.
- Read systematic-debugging and verification-before-completion skills; rc 0.
- Memory grep for Agentic-foundation-model-bench / runner context; rc 0, used only for prior-context awareness.
- Remote preflight `pwd`, branch, head, status, HANDOFF excerpt, and lane file list: rc 0. Observed branch/head `feat/image-warmup-policy` / `9f480fe`; pre-existing untracked pycache noted above.
- Prior report reads for Round36/Round37, hunt-runner-results tail, hunt-runtime-images tail, and dedup grep: rc 0. Some output was truncated by the local display; used only for dedup context, not exact issue evidence.
- Static code reads for runner/result/readiness functions and manifest/test line refs: rc 0.
- Python inventory of suite entries, nine-target readiness report, and default plan: rc 0.
- Active stale-name scan over `README.md`, `scripts`, `manifests`, and `docs`: rc 0; only active-code hit was the negative test guard.
- Historical stale-name scan over `reports` and lane files: rc 0; historical matches summarized above.
- Parser matrix and tau3/RepoZero direct parser probes: rc 0, except one invalid RepoZero summary-status attempt with rc 127 and one invalid nested-quote attempt with rc 1. Both invalid attempts were discarded and rerun with a literal SSH heredoc.
- Literal SSH-heredoc RepoZero semantic-failure `_execute_plan()` repro: rc 0; output summarized above.
- Readiness CLI probe for the nine target families: wrapper rc 0, inner readiness rc 1, counts summarized above.
- Default `--execute` fail-closed probe: wrapper rc 0, inner execute rc 2, no controller output files created.
- Disabled `--only` probes for Terminal Bench 2.1, MCP-Atlas, Tool-Decathlon, programbench, NL2Repo, and full tau3: wrapper rc 0; each inner command rc 2 with empty stdout.
- Initial focused unittest command used a stale test selector and returned rc 1 with `AttributeError`; discarded and rerun.
- Corrected focused unittest command: rc 0, `Ran 8 tests`, `OK`.

## Validation plan

After writing this report, validate only this file with:
- `test -f _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`
- `git diff --no-index --check /dev/null _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`
- trailing whitespace scan on this report
- bounded secret-value/assignment scan on this report
- scoped `git status --short --untracked-files=all -- _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`

## Validation results

- `test -f _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`: rc 0.
- `git diff --check -- _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`: rc 0.
- `git diff --no-index --check /dev/null _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`: rc 1 with zero output lines; rc 1 is expected for a no-index added-file diff, and zero output means no whitespace diagnostics.
- Trailing whitespace scan on this report: rc 1, no matches.
- Bounded secret-value/assignment scan on this report: rc 1, no matches.
- Scoped report status: `?? _coordination/20260625_harbor_bench/lanes/runner-results-round39-bughunt.md`.
- Pycache status scan still shows the pre-existing `?? scripts/__pycache__/check_offline_images_manifest.cpython-310.pyc` observed before this lane ran tests; I did not modify or remove it because this lane is report-only.
