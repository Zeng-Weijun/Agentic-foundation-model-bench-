# Gold validation -- the proof that 0 is real, not a judging bug

## The logic
A resolve requires **reward=1**, which the task verifier grants only when the code change makes
the task's tests pass (baseline regression suite green **and** the new tests green).

For every one of the 113 tasks the audit ran TWO containers off the same image:
1. **GOLD**: apply `solution/solution.patch`, run the verifier -> `gold_reward`.
2. **AGENT re-verify**: apply the agent's `prediction.patch.diff` (from the generation run),
   run the same verifier -> `agent_reward`.

## The result (after the NO_PROXY correction; see AUDIT_NOTES.md)
- **gold_reward==1 on 106 tasks** (`gold_valid=106`). The verifier CAN reach reward=1 with a correct
  patch => **the judging environment is correct** for these 106 tasks.
- On those **same 106** judging-correct tasks, **agent_reward!=1 for every one** (91 scored a real
  patch = fail; 15 produced no applicable patch). **0 / 106.**
- **gold_reward!=1 on 7 tasks** (`gold_broken=7`). Here the gold solution itself cannot reach
  reward=1 (baseline+new not both green / task-env broken) **even in auditor-A's clean env**. These are
  **excluded** from the valid denominator, so they cannot be blamed for the 0 either.

## Correction 2026-07-13 (gold_valid 102 -> 106)
The original bundle had gold_valid=102 / gold_broken=11. Auditor-A's independent clean-env re-verify showed
4 of those 11 were **NO_PROXY judging-pollution false-reds** (driver `container_env()` put the sglang IP
`100.100.104.147` + `100.100.0.0/16` into `NO_PROXY`, which false-failed the httpx `test_get_environment_proxies`
baseline). In a clean env they reach gold=1: `httpx-multipart-response-parsing`, `httpx-streaming-json-iteration`,
`httpx-deterministic-cookie-store`, `happy-dom-abort-pending-body-reads`. They moved gold_broken -> gold_valid.
The agent still scores 0 on all 4 in the clean env, so the numerator is unchanged (0/106).
Evidence: `../../../deepswe_pathA/runs/audit2_independent/broken.log`.

## Why this rules out a judging bug
If the 0 were a scoring/environment bug, the gold solution would also fail the verifier. Instead the
gold solution PASSES on 106 tasks. The only variable that changes between the reward=1 run and the
reward=0 run is **the patch** (gold vs agent). Therefore the 0 is the agent's, not the judge's.

See `gold_valid_ids.txt` (106), `gold_broken_ids.txt` (7 + reasons), `gold_vs_agent.tsv` (113),
`../AUDIT_NOTES.md` (dual-sign REAL + all judging bugs/caveats), and `../verdict/samples/` for four
per-language worked examples.
