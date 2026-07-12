# DeepSWE Path A -- AUDIT of full113 (fake-0 investigation)

## Why this run exists
The first full113 agent run (`runs/full113_20260712T114730Z`) reported **0/113
resolved**. Investigation found the 0 is **partly a verifier bug, not all real**:

- **pytest-not-activated (FIXED):** many python task images ship their test deps
  in a venv at `/opt/venv` (image Config.Env sets `PATH=/opt/venv/bin:...` +
  `VIRTUAL_ENV=/opt/venv`). The driver hardcoded a PATH without `/opt/venv/bin`,
  and the verifier ran under a login shell (`/etc/profile` resets PATH), so the
  repo test.sh's bare `python -m pytest` hit `/usr/local/bin/python` -> "No module
  named pytest" -> reward=0 **even for the gold solution**. Proof: `igel-persist-
  feature-schema` gold=0 before fix, **gold=1 after fix** (baseline 2 passed / new
  24 passed). Fix = re-activate `/opt/venv` when present (driver `VENV_PREFIX`),
  applied to BOTH the verifier and the agent.
- **baseline-not-green (task/env, NOT agent, NOT the venv bug):** some tasks' gold
  solution makes the NEW tests pass but the BASELINE regression suite still fails
  (reward=1 needs BOTH green). Seen: `skrub-duration-encoding` (py, new "130 passed"
  but base fails) and `eicrud-keyset-pagination-cursor` (ts, new "18 passed" but
  "Baseline exit code: 1"). These tasks are **not validly scorable as-run**.

## What this audit does (mode=audit, NO serving calls)
For every one of the 113 tasks, one image load, two containers:
1. **GOLD**: apply `solution/solution.patch` -> fixed verifier -> `gold_reward`.
   `gold_reward==1` => the task is validly scorable.
2. **AGENT re-verify**: apply the prior run's `agent/prediction.patch.diff` ->
   fixed verifier -> `agent_reward`. This RE-SCORES the exact patches the first
   run produced, now with the corrected verifier.

Status per task:
- `resolved`              gold==1 AND agent patch passes -> a real solve (was hidden by the bug).
- `unsolved_valid`        gold==1, agent patch fails -> HONEST unsolved.
- `task_broken_gold_fail` gold==0 -> not validly scorable (exclude from denominator).
- `gold_evalerror`        gold verifier could not produce a reward.

## Honest metric
`honest_resolve_rate = resolved / gold_valid` where `gold_valid = #(gold_reward==1)`.
The denominator is NOT 113 -- broken tasks are excluded.

## Run
- Run root: `runs/audit_full113_20260712T173528Z/`
- results.jsonl (per task: gold_reward, agent_reward, status, verifier times, ...)
- report.json (final: gold_valid / gold_broken / agent_resolved_on_valid /
  honest_resolve_rate / by_lang / resolved_task_ids / broken_task_ids)
- orchestrator.log (grep AUDIT / DONE)

## Recommended follow-up (the true "rerun")
The first-run agent was ALSO handicapped on python venv tasks: it ran WITHOUT
`/opt/venv` on PATH, so it could not run `pytest` to self-check. This audit only
re-scores those blind patches. For a fully faithful score, re-run the AGENT (not
just re-verify) on the venv-affected tasks with the fixed driver:
```
python3 deepswe_full113_orchestrator.py --mode agent --langs python \
  --run-root runs/full113_pyfix_<ts> --concurrency 4 --max-session-turns 100 \
  --rollout-timeout 2400 --verifier-timeout 1800
```
(uses serving; keep c=4 to share the Coder endpoint with Multilingual).
Non-python (go/rust/ts/js) were validly scored in the first run (gold=1, agent=0),
so their 0 is real and they do NOT need re-running -- except the few
`task_broken_gold_fail` ones the audit flags.
