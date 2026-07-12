# Gold validation — the proof that 0 is real, not a judging bug

## The logic
A resolve requires **reward=1**, which the task verifier grants only when the code change makes
the task's tests pass (baseline regression suite green **and** the new tests green).

For every one of the 113 tasks the audit ran TWO containers off the same image:
1. **GOLD**: apply `solution/solution.patch`, run the verifier -> `gold_reward`.
2. **AGENT re-verify**: apply the agent's `prediction.patch.diff` (from the generation run),
   run the same verifier -> `agent_reward`.

## The result
- **gold_reward==1 on 102 tasks** (`gold_valid=102`). The verifier CAN reach reward=1 with a correct
  patch => **the judging environment is correct** for these 102 tasks.
- On those **same 102** judging-correct tasks, **agent_reward==0 for every one** (87 scored a real
  patch = fail; 15 produced no applicable patch). **0 / 102.**
- **gold_reward!=1 on 11 tasks** (`gold_broken=11`). Here the gold solution itself cannot reach
  reward=1 (baseline+new not both green / task-env broken). These are **excluded** from the valid
  denominator, so they cannot be blamed for the 0 either.

## Why this rules out a judging bug
If the 0 were a scoring/environment bug, the gold solution would also fail the verifier. Instead the
gold solution PASSES on 102 tasks. The only variable that changes between the reward=1 run and the
reward=0 run is **the patch** (gold vs agent). Therefore the 0 is the agent's, not the judge's.

See `gold_valid_ids.txt` (102), `gold_broken_ids.txt` (11 + reasons), `gold_vs_agent.tsv` (113),
and `../verdict/samples/` for four per-language worked examples.
