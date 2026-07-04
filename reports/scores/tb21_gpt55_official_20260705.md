# TB2.1 GPT-5.5 official single-attempt score - 2026-07-05

## Verdict

Final corrected score: **63/89 = 70.8%**.

This adopts the surface85 final-review correction: `headless-terminal` was a scorer false negative (CTRf 7/7 pass) and is counted as passed. The raw reducer emitted 62/89 = 69.6629%; do not quote that raw number as the board score.

## Run Contract

| Field | Value |
|---|---|
| `bench` | `Terminal-Bench 2.1 full89` |
| `run_id` | `tb21_gpt55_official_medium_c89_single_20260704t195417z` |
| `agent` | `terminus-2` |
| `model` | `gpt-5.5` |
| `effort` | `medium/default; no reasoning_effort arg` |
| `attempts` | `1 single pass@1 sample` |
| `concurrency` | `89` |
| `timeout` | `global-timeout-multiplier 1.0; agent/test timeout 7200s` |
| `dataset` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703` |
| `image manifest` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-image-fixes-r3/manifests/images/terminal_bench_2_1_full89_p0_closure_r7.yaml` |
| `relay` | `http://100.96.122.22:18540/v1` |
| `artifact` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c89_tb21_gpt55_official_medium_c89_single_20260704t195417z_attempt1_medium_c89` |
| `source score JSON` | `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-gpt55-launcher-s55/reports/scores/tb21_gpt55_official_medium_c89_single_20260704t195417z_medium_c89_scores.json` |

## Score Semantics

- Raw reducer score: `62/89 = 0.6966292135`.
- surface85 correction: `headless-terminal` strict parser false negative; CTRf passed `7/7`.
- Final corrected score: `63/89 = 0.7078651685`, reported as `70.8%`.
- Official anchor note: `78.2% +/- 2.4` is a 5-run mean. This artifact is one independent pass@1 sample, so `+/-4-5pp` single-sample drift is expected and should be called out when comparing.

## Infra Statement

The run is valid for scoring under the current Pod A privileged path. Infrastructure scans found no Docker/P0/mount/relay transport failure signal:

- `run_rc`: `0`
- `rows`: `89/89`
- `xhigh_debug_count`: `0`
- `docker_api`: `0`
- `readtimeout`: `0`
- `connection_aborted`: `0`
- `no_such_container`: `0`
- `mount_guard`: `0`
- `solution_missing`: `0`
- `docker_api_version`: `0`
- `rate_limit_error`: `0`
- `preheat_errors`: `0`
- `preheat_present`: `89`
- `preheat_tar_verified`: `89`
- `preheat_retagged`: `248`

`install-windows-3.11` contains local in-container nginx/QEMU `502 Bad Gateway` traces against `127.0.0.1:8080`; this is classified as task-local environment ceiling, not external relay/P0/Docker transport infra.

## surface85 Correction Record

surface85 final review (`DECISIONS.md` lines 651-675) verified score/row consistency and issued one mandatory correction:

> `headless-terminal` parse_error is a real 7/7 pass masked by a scorer bug -> corrected score = 63/89 = 70.8%.

surface85 verdict: PASS with headless-terminal correction and attribution refinement before quoting the number.

## Original 27 Unresolved Rows And Final Attribution

| # | task_id | final category | counts as final failure? | note |
|---:|---|---|---|---|
| 1 | `model-extraction-relu-logits` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 2 | `cancel-async-tasks` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 3 | `mteb-leaderboard` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 4 | `regex-chess` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 5 | `dna-insert` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 6 | `filter-js-from-html` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 7 | `count-dataset-tokens` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 8 | `sanitize-git-repo` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 9 | `headless-terminal` | `scorer_parse_bug_corrected_pass` | `false` | CTRf passed=7 failed=0; strict parser hit pytest cacheprovider warning. Corrected to pass by 85. |
| 10 | `path-tracing` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 11 | `video-processing` | `real_model_gap` | `true` | 3/5 passed in 85 spot-check; oracle passed after toml fix. |
| 12 | `mteb-retrieve` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 13 | `dna-assembly` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 14 | `overfull-hbox` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 15 | `torch-pipeline-parallelism` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 16 | `install-windows-3.11` | `env_ceiling` | `true` | 3/4, subprocess assert plus local nginx/QEMU 502 on 127.0.0.1:8080; task-local service behavior, not relay/P0/Docker transport. |
| 17 | `raman-fitting` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 18 | `make-mips-interpreter` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 19 | `chess-best-move` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 20 | `extract-moves-from-video` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 21 | `fix-ocaml-gc` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 22 | `make-doom-for-mips` | `env_ceiling` | `true` | qemu timeout=30 / no KVM; oracle also timed out. |
| 23 | `schemelike-metacircular-eval` | `real_model_gap` | `true` | 8/63 passed in 85 spot-check; oracle passed canary8. |
| 24 | `query-optimize` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 25 | `gpt2-codegolf` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 26 | `path-tracing-reverse` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |
| 27 | `train-fasttext` | `model_or_task_unresolved_no_infra_signal` | `true` | Unresolved in native results; surface55 strict scan found no Docker/P0/mount/relay transport signal. Needs task/model-level review if pursued. |

Final accounting: 26 remaining failures plus 1 corrected scorer false negative = 63/89.

## Companion Artifact

Machine-readable companion: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/reports/scores/tb21_gpt55_official_20260705.json`.
