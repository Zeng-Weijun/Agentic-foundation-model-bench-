# OpenAI Codex independent blind audit signoff

- **Auditor identity:** OpenAI Codex CLI, model `gpt-5.6-sol`, reasoning effort `xhigh`, `codex-cli 0.144.1`
- **Audit date:** 2026-07-13 (Asia/Shanghai)
- **Audited run:** `tb21_coder_t2_c32_0711211754`
- **Claim:** Terminal-Bench 2.1, 89 tasks, Qwen3-Coder-30B-A3B-Instruct, official `terminus-2` harness, 10 resolved of 89, 11.24%, run on KVM Pod B on 2026-07-12
- **Verdict:** **REAL**

## Decision

I treated the claim as false until it survived independent falsification attempts. I did not use the vendored aggregate as the scoring authority: I reconstructed the denominator and the resolved count from the raw run tree, checked three resolved tasks not used in the stated Claude-side spot check against the real upstream test source, compared the captured serving identity with a live server response, and traced the `infra_fail` implementation and the historical SIGTERM artifacts.

I found no evidence that the score, task denominator, resolved task identities, tests, server identity, or current-run infrastructure status were fabricated or silently altered. Direct raw recomputation gives 10 resolved tasks among all 89 tasks, so `10 / 89 = 0.112359550562... = 11.235955...%`, which rounds to **11.24%**. Under the requested adversarial rule, the claim is therefore **REAL**.

This is a spot-check audit, not a fresh benchmark run. In accordance with the audit constraints, I launched no `tb` or `terminus-2` command and modified no raw or existing bundle artifact.

## Evidence roots and notation

The following absolute paths were inspected on KVM Pod B:

```text
B = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/evidence-sweml-full300-147/experiments/runs/tb21_coder_terminus2_147
R = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32
U = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1/tasks
D = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703
S = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/scripts/tb21_strict_batch_summary.py
W = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda/tb21_coder_t2_c32_0711211754/medium_c32/attempt_1/tb21_batched_terminus-2_tb21_coder_t2_c32_0711211754_attempt1_medium_c32/batch_01_of_01
H = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/terminal_bench_2_1_official_qwen_poda/tb21_coder_t2_c32_0710064916/medium_c32/attempt_1/tb21_batched_terminus-2_tb21_coder_t2_c32_0710064916_attempt1_medium_c32/batch_01_of_01
```

Line citations below use those aliases for readability. All command-output blocks are transcriptions of read-only probes run during this audit.

## Checklist 1 — denominator 89 was not shrunk

Independent filesystem and JSON probes produced:

```text
verdict_tsv_total_lines=90
verdict_tsv_data_rows=89
raw_top_level_task_dirs=89
raw_nested_per_task_results_json=89
dataset_docker_compose_yaml=89
dataset_network_mode_none=89
summary_resolved_ids=10
summary_unresolved_ids=79
summary_union=89
summary_overlap=0
raw_tsv_dataset_task_sets_equal=True
```

Concrete evidence:

- `B/verdict/per_task_verdict.tsv:1` is the header; lines 2–90 are 89 task rows. The final row is at line 90, so the table was not truncated.
- `B/summary.json:15-20` records `resolved=10`, `total=89`, and accuracy `0.11235955056179775`; `B/summary.json:51-62` contains the ten resolved IDs and `B/summary.json:63-143` contains 79 unresolved IDs. The two arrays have no duplicates or overlap, and their union is exactly the same 89 task IDs seen in the raw tree, TSV, and dataset.
- The raw run has exactly 89 top-level task directories and exactly one nested per-task `results.json` under each task. The raw root's four additional entries are `results.json`, `run.log`, `run_metadata.json`, and `tb.lock`; none was miscounted as a task.
- The exact dataset has 89 `docker-compose.yaml` files. Anchored parsing found `network_mode: none` in all 89 and no other network mode; for example `D/adaptive-rejection-sampler/docker-compose.yaml:5`, `D/make-doom-for-mips/docker-compose.yaml:5`, and `D/write-compressor/docker-compose.yaml:5`.

A direct grep over the 89 raw per-task result files, without consulting any aggregate, found exactly these ten files with `"is_resolved": true`:

```text
build-pmars
build-pov-ray
cancel-async-tasks
extract-elf
git-leak-recovery
modernize-scientific-stack
polyglot-rust-c
portfolio-optimization
prove-plus-comm
pypi-server
```

A structural JSON pass over the same 89 raw files found `true=10`, `false=78`, and `null=1`. The one non-boolean result is not silently dropped: `R/headless-terminal/headless-terminal.1-of-1.tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32/results.json:4-8` identifies `headless-terminal`, records `is_resolved=null`, `failure_mode="parse_error"`, and `parser_results=null`; `B/verdict/per_task_verdict.tsv:42` counts it unresolved, and `B/summary.json:94` includes it in `unresolved_ids`. Thus the full denominator is `10 true + 78 false + 1 null/parse_error = 89`, not a filtered 88-task subset.

## Checklist 2 — three independently selected resolved tasks are genuine

I selected `build-pov-ray`, `cancel-async-tasks`, and `extract-elf`, all different from the four tasks named as already spot-checked by the Claude-side pass. For each task, I compared the parser-result key set with Python test functions extracted from the real upstream source. The exact-set comparison returned:

```text
build-pov-ray       SETS_EXACTLY_EQUAL=true
cancel-async-tasks  SETS_EXACTLY_EQUAL=true
extract-elf         SETS_EXACTLY_EQUAL=true
```

### `build-pov-ray`

Let `P = R/build-pov-ray/build-pov-ray.1-of-1.tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32`.

- `P/results.json:4-12` identifies the task, records `is_resolved=true`, and records all three parser tests as passed: `test_illum1_render_and_verify`, `test_povray_version`, and `test_povray_built_from_correct_source`.
- The real upstream source defines those exact names at `U/build-pov-ray/tests/test_outputs.py:13`, `:78`, and `:92`. No parser name was invented and no upstream test was omitted.
- `P/sessions/tests.log:6-10` shows a real pytest session collecting three tests; `P/sessions/tests.log:17` records the rendered-image SSIM value `0.8731`, and `P/sessions/tests.log:19-22` shows the named tests passing and ends `3 passed in 10.47s`.
- `P/agent-logs/episode-0/debug.json:3,16-17` contains a real call ID `cde89f42-6deb-4119-8d78-caaf0ffc5b19` and `api_base=http://100.100.104.147:30001/v1/`. A late episode independently has call ID `f171530e-64de-4408-8cc7-62736c7d950a` and the same endpoint at `P/agent-logs/episode-48/debug.json:3,400-401`.
- An exhaustive lightweight scan found 49 debug files, 49 distinct nonempty top-level call IDs, and the exact endpoint in all 49 files; no nonmatching `api_base` line was found.

### `cancel-async-tasks`

Let `C = R/cancel-async-tasks/cancel-async-tasks.1-of-1.tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32`.

- `C/results.json:4-15` identifies the task, records `is_resolved=true`, and records all six parser tests as passed.
- Those six exact functions are defined by the real source at `U/cancel-async-tasks/tests/test_outputs.py:10`, `:17`, `:40`, `:71`, `:106`, and `:139`. The companion `tests/test.py` contributes no additional `test_*` function, so the exact-set comparison is complete.
- `C/sessions/tests.log:6-10` shows collection of six tests; `C/sessions/tests.log:16-22` names all six as `PASSED` and ends `6 passed in 14.10s`.
- `C/agent-logs/episode-0/debug.json:3,16-17` contains call ID `ffe40b8e-93e7-42c0-9451-394067f5c87c` and the exact Coder endpoint. `C/agent-logs/episode-8/debug.json:3,80-81` contains distinct call ID `7adfc1dd-f067-4485-8cce-6d2dcd6fa52a` and the same endpoint.
- All nine debug files have nine distinct nonempty top-level IDs and contain the exact endpoint; no nonmatching `api_base` line was found.

### `extract-elf`

Let `E = R/extract-elf/extract-elf.1-of-1.tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32`.

- `E/results.json:4-11` identifies the task, records `is_resolved=true`, and records both parser tests as passed.
- The real source defines exactly those two functions at `U/extract-elf/tests/test_outputs.py:309` and `:316`; the parser and upstream sets match with no missing or invented name.
- `E/sessions/tests.log:6-10` shows collection of two tests; `E/sessions/tests.log:16-18` names both as passed and ends `2 passed in 0.37s`.
- `E/agent-logs/episode-0/debug.json:3,16-17` contains call ID `19bab3bc-d31e-488b-8c59-24e63f07cd7b` and the exact endpoint. `E/agent-logs/episode-23/debug.json:3,200-201` contains distinct call ID `960f5499-dd95-4aad-a6c3-0248153d9054` and the same endpoint.
- All 24 debug files have 24 distinct nonempty top-level IDs and contain the exact endpoint; no nonmatching `api_base` line was found.

These are genuine per-task pytest transcripts and agent call records, not merely plausible aggregate labels.

## Checklist 3 — port 30001 is serving the claimed Coder model

The bundle's captured model information is stable and specific:

- `B/serving/get_model_info_before.json:2-4,8-11` and `B/serving/get_model_info_after.json:2-4,8-11` identify architecture `Qwen3MoeForCausalLM`, model type `qwen3_moe`, and both model/tokenizer path as `/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct`.
- The before and after model captures are byte-identical, both SHA-256 `22e321943eb33b7a2df8f46e60ce797067731eebbc1485d1c0f51efd5a121fd1`.
- `B/serving/get_server_info_after.json:21,811,922,938,990,994,1002` records context length `262144`, the Coder model path, random seed `484925000`, served name `Qwen/Qwen3-Coder-30B-A3B-Instruct`, tool parser `qwen3_coder`, tensor parallel size `2`, and server version `0.5.13`.

A live read-only query to `http://100.100.104.147:30001/get_model_info` and `/get_server_info` from KVM Pod B at `2026-07-13T11:00:06Z` returned those same identity/configuration values:

```text
model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct
tokenizer_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct
model_type=qwen3_moe
context_length=262144
tp_size=2
random_seed=484925000
served_model_name=Qwen/Qwen3-Coder-30B-A3B-Instruct
tool_call_parser=qwen3_coder
status=ready
version=0.5.13
```

Normalized recursive comparison found the live `/get_model_info` semantically identical to the captured-after file. In a separate normalized comparison probe earlier in the audit, the sole live-versus-capture `/get_server_info` difference was expected dynamic telemetry, `internal_states[0].last_gen_throughput`, changing from `10.089974397820283` to `169.29842406292772`; no identity or configuration field drifted. The bundle's before/after server captures likewise differ only in that throughput value (`135.64027600557225` to `10.089974397820283`). The configured model path also resolves to a real nonsymlink directory whose `config.json` reports the same architecture and model type.

## Checklist 4 — raw 10/89 recomputation and honest `infra_fail` handling

### Direct raw recomputation

The resolved count was recomputed from the 89 nested raw per-task `results.json` files, not from `B/results.json` or `B/summary.json`:

```text
raw_per_task_results=89
raw_is_resolved_true=10
raw_is_resolved_false=78
raw_is_resolved_null=1
raw_other_or_missing=0
```

The ten raw-true IDs exactly equal `B/summary.json:51-62`, while the other 79 IDs exactly equal `B/summary.json:63-143`. The arithmetic independently checks:

```text
10 / 89 = 0.11235955056179775
100 * 10 / 89 = 11.235955056179776
round(..., 2) = 11.24
```

### Current-run infrastructure classification

The scorer implements batch-level return-code propagation as real code:

- `S:21` defines the `tb_rc` pattern; `S:67-69` reads it.
- `S:168-170` selects the manifest's one batch-level exit-status artifact and reads `tb_rc` once before the task loop beginning at `S:193`.
- `S:218` requires `tb_rc == 0` for a row to be `clean`; `S:230-231` appends the same nonzero batch code to each affected task's notes.
- `S:250` defines `infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not in (0, None))`.
- `S:303` aggregates those row flags, and `S:309` requires zero infra failures for a ready batch.

The audited run is the uncontaminated case: `W/tb.exit_status:1` is `tb_rc=0`; `W/tb21_strict_summary.json:4-17` reports `clean_pass=10`, `infra_fail=0`, `missing_artifact=0`, `parse_error=1`, `resolved=10`, `timeout=0`, `total=89`, and `unresolved=78`. Parsing all strict-summary task rows found 89 rows, `infra_fail=true` on zero, `infra_fail=false` on all 89, and `clean=true` on ten. This agrees with the direct raw reconstruction.

### Historical 2026-07-10 SIGTERM explanation

The explanation in `B/calibration.md:15-18` is structurally and empirically supported, not narrative-only:

- `H/tb.exit_status:1` is `tb_rc=143`; 143 is the conventional `128 + SIGTERM(15)` exit code.
- `H/artifact_manifest.json:3-10` binds that exit-status file to the historical raw artifact directory, raw `results.json`, and Terminal-Bench log.
- `H/tb21_strict_summary.json:4-17` reports `clean_pass=0`, `infra_fail=89`, `missing_artifact=0`, `resolved=12`, `timeout=2`, and `total=89`. All 89 row notes receive the same `tb_rc=143`, exactly as the code predicts.
- The historical raw `results.json` was written at `2026-07-10T08:58:08.637713Z`; `H/tb.exit_status` was written at `2026-07-10T09:15:37.347759Z`; the strict summary followed at `09:15:38Z`. The score therefore existed 1,049 seconds (17 minutes 29 seconds) before the SIGTERM-derived exit artifact, after which the strict scorer propagated the nonzero batch return code.

Precision caveat: because the historical summary also has two timeout rows and `fatal_timeout` independently enters `S:250`, two rows might still have been infrastructure failures without the nonzero batch code. The exact supported statement is that `tb_rc=143` mechanically marked all 89 rows and inflated the aggregate by **at least 87** while forcing clean passes to zero. I do not claim that all 89 historical flags were individually false. This caveat does not affect the audited 2026-07-12 run, where `tb_rc=0`, `timeout=0`, and `infra_fail=0`.

## Cross-family signoff gap

I independently checked the Git metadata for the two existing bundle commits:

```text
39bf63a1da25d838032ee690bc0f058c6d1879a5
ac80ef8f19c0954b523b0096eaa1fdb911e2eb6d
```

Both commit bodies end with:

```text
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

Commit `ac80ef8` nevertheless describes the evidence as “dual-signed REAL.” The trailers do not prove who performed every underlying action, but they do show that the existing Git history does **not** establish cross-family auditor diversity: both existing audit-bearing commits attribute authorship to the same Claude family. Therefore the prior “2 independent blind auditors” framing overclaims the diversity evidenced by those commits.

This file supplies the missing genuinely cross-family pass. It records an independent OpenAI Codex CLI audit using the exact identity shown above; it does not repeat the earlier diversity claim unqualified.

## Final signoff

**VERDICT: REAL.** I tried to falsify the claim through denominator mismatch, raw/aggregate disagreement, invented parser-test names, fake pytest/call logs, serving-identity drift, silent infrastructure exclusion, and post-hoc SIGTERM narration. None succeeded. The supported headline is:

> Terminal-Bench 2.1 (89 tasks) × Qwen3-Coder-30B-A3B-Instruct × official terminus-2, run `tb21_coder_t2_c32_0711211754`: **10/89 resolved = 11.24%**, with `infra_fail=0`.
