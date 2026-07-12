# Traces — where the full recordings live (not fully vendored; size)

Condensed per-task verdicts: `verdict/per_task_verdict.tsv` (113 rows) and
`gold_validation/gold_vs_agent.tsv`. Four per-language worked examples with full verifier stdout and the
agent's real patch are under `verdict/samples/`. The FULL agent trajectories stay on the shared disk.

Generation run (qwen-code agent, per task `<task>/agent/`):
```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/full113_20260712T114730Z/<task>/agent/
```
- `qwen_command.txt`        — exact CLI (base-url http://100.100.104.147:30001/v1, model Qwen3-Coder-30B-A3B-Instruct)
- `qwen.stdout.jsonl`       — full stream-json trajectory (model init shows served model; assistant turns)
- `stream_analysis.json`    — json_events / assistant_turns / has_real_interaction
- `prediction.patch.diff`   — the agent's produced patch (scored)
- `prompt.txt`, `qwen.stderr.txt`, `post_agent_git_status.txt`, `verifier.*`

Audit re-score run (gold + agent re-verify, per task `<task>/`):
```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/audit_full113_20260712T173528Z/<task>/
```
- `solution/verifier.stdout.txt` + `verifier.result.json`      — GOLD apply+verify (reward=1 on valid tasks)
- `agent_reverify/verifier.stdout.txt` + `verifier.result.json` — AGENT patch apply+verify (reward=0)
- `summary.json`                                                — gold vs agent_reverify + status
