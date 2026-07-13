# Traces -- where the full recordings live (not fully vendored; size)

Condensed 400-row verdict: `verdict/per_task_verdict.tsv`. Five worked examples with the full
qwen `:30001` trajectory + generated `.mjs` + official oracle-vs-node `judge.result.json` are
under `verdict/samples/`. The FULL 400-case per-case recordings stay on the shared disk:

```
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/coder_full400_20260712T210354Z/cases/<lib>-<testN>/
  agent/qwen_command.txt      -- exact qwen-code CLI (base-url :30001, model Qwen3-Coder-30B-A3B-Instruct)
  agent/qwen.stdout.jsonl     -- full stream-json trajectory (assistant model field = served Coder)
  agent/stream_analysis.json  -- json_events / assistant_turns / has_real_interaction
  agent/whitebox.json         -- oracle sanity probe (a few sample args)
  agent/judge.result.json     -- OFFICIAL judge: per-sample oracle stdout vs node stdout (+ fail_examples)
  workspace_output/packages/<lib>/<testN>_pkg/<testN>.mjs   -- the generated JavaScript
  summary.json                -- per-case agent+judge summary
```

## Independently re-judge any case (serving-free, deterministic)
The judge needs NO model -- only the image (oracle executable + node) and the already-generated
`.mjs`. `scripts/rejudge_missing4.py` shows the exact pattern (import the driver, `start_container`,
`eval_case`). It reproduced the 4 crash cases -> **0/4 recovered passes** (`rejudge_missing4.json`).

## Official 5s re-judge of ALL 400 (serving-free) + node seam -- see AUDIT_NOTES.md
The run used `eval_timeout=10s`; RepoZero official hardcodes 5s. `scripts/rejudge_official5s.py`
re-judges every one of the 400 already-generated `.mjs` at the official **5s** (same qwen node
v20, only the timeout changed) -> **`rejudge_official5s.json`** (per-case 10s->5s + headline
95/400). The eval `node` is the mounted **qwen node v20.20.2**, not the image node
v18.19.1 (0.25pp seam, A). Full A+B audit + all three calibers: **`AUDIT_NOTES.md`**.

## Sample set in this bundle
- `base58-test1`  -- PASS (60/60)
- `schedule-test7` -- PASS
- `base58-test10`  -- FAIL (partial, 20/33; `judge.result.json` has up to 5 oracle-vs-node stdout diffs)
- `networkx-test6` -- FAIL (near-miss 59/60; `judge.result.json` shows the single oracle-vs-node stdout diff)
- `rsa-test5`      -- FAIL + crash-case (the oracle executable exceeded the 10s eval timeout -> original run crashed here; harness caveat, see calibration.md. Trajectory + generated .mjs + whitebox present; no judge.result.json because the oracle itself timed out.)
