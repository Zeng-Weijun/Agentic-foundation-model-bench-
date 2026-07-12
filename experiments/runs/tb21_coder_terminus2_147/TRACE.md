# Traces — location of full terminus-2 recordings (not vendored; size)

Per-task condensed verdicts are in `verdict/per_task_verdict.tsv` (89 rows) and the 10
passes are detailed in `verdict/resolved_tasks.md`. The FULL traces stay on the shared disk:

Base (tb-native run dir):
```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0711211754_attempt1_medium_c32/
```
Per task `<task_id>/<task_id>.1-of-1.<job>/`:
- `results.json`                         — tb-native per-task verdict
- `sessions/agent.cast`                  — asciinema recording of the agent terminal (~64 KB)
- `sessions/tests.cast`                  — asciinema recording of the test phase
- `agent-logs/episode-<N>/prompt.txt`    — per-episode prompt sent to the model
- `agent-logs/episode-<N>/response.txt`  — per-episode model response
- `agent-logs/episode-<N>/debug.json`    — per-episode debug (tokens, tool calls)
- `panes/post-test.txt`                  — captured post-test pane (root of the parse_error for headless-terminal)

The `recording_path` column in `verdict/per_task_verdict.tsv` gives the exact relative
`sessions/agent.cast` path for every task.

Other on-disk logs (launcher log dir
`.../repo/.worktrees/tb21-gpt55-launcher-s55/_coordination/20260625_harbor_bench/logs/tb21_terminus2_147_clean_20260712/`):
- `tb21_coder_run2.out`                    — full run console (excerpt vendored as run_console_excerpt.log)
- `net_isolation_runtime_...jsonl` + `..._watch.log` — runtime per-container network-isolation samples
- `disk_watch_...log`, `dataset_assert_...log`        — disk + dataset-path assertions
