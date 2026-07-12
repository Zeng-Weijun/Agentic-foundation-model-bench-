# Traces — location of full terminus-2 recordings + run timeline

Per-task condensed verdicts: `verdict/per_task_verdict.tsv` (89 rows); the 3 passes are detailed in
`verdict/resolved_tasks.md`; per-task re-adjudication artifacts in `verdict_pack.tar.gz`. FULL traces stay on the shared disk.

Base (tb-native run dir):
```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_inst2507_t2_c32_0712170859_attempt1_medium_c32
```
Per task `<task_id>/<task_id>.1-of-1.<job>/`:
- `results.json`               — tb-native per-task verdict
- `sessions/agent.cast`        — asciinema recording of the agent terminal
- `sessions/tests.cast` / `sessions/tests.log` — test phase recording / log
- `agent-logs/episode-<N>/{prompt,response,debug}` — per-episode prompt / model response / tokens+tool-calls
- `panes/{pre-agent,post-agent,post-test}.txt` — captured panes
The `recording_path` column in `verdict/per_task_verdict.tsv` gives the exact relative `sessions/agent.cast` path.

Launcher log dir:
```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/tb21-gpt55-launcher-s55/_coordination/20260625_harbor_bench/logs/tb21_terminus2_147_clean_20260712
```
- `tb21_instruct_run.out`  — full run console (excerpt vendored as run_console_excerpt.log)
- `serving_run_tb21_inst2507_t2_c32_0712170859/`  — get_model_info + get_server_info before+after (vendored into serving/)
- `net_isolation_*`, `disk_watch_*`, `dataset_assert_*` — watchdog logs (0-byte gaps disclosed in calibration.md)

## Timeline (UTC)
- **2026-07-12T17:08:59Z** — run start (`tb21_inst2507_t2_c32_0712170859`; tmux `tb21_instruct`, run_id encodes 07-12 17:08:59). Launcher captured serving IDENTITY (before) = Instruct-2507.
- 17:30:14Z — mailman trial starts; agent runs 17:30–18:05 (~35 min), leaves postfix broken.
- 18:05:59Z — mailman test phase starts; **hangs** and hits the 7200s test-timeout at 20:05:59Z (is_resolved=null).
- ~17:09–20:2xZ — 28 tasks exhaust the 7200s **agent** budget (agent_timeout); tune-mjcf agent loops on the mujoco speed target (`Time ~100%%, need 60%%`), container `3bdb9767` becomes a live zombie.
- **2026-07-12T20:26Z** — evidence-collection agent captures serving identity + zombie panes, then `docker kill 3bdb9767 && docker rm -f` so terminus can finalize (r5–r10 finalization watch loop).
- 2026-07-12T20:29:49Z — batched v4 strict ledger generated.
- **2026-07-12T20:30:23Z** — tb-native results.json finalized to 89 rows: **n_resolved=3, n_unresolved=86, accuracy=0.03370787**; `tb run` process exits; tb2-offline containers = 0. `tb_rc=0`, `runner_rc=0`, identity (after) = Instruct-2507. Run cleanly finished.
