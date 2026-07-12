# Calibration — how to read this 0.00%

## What was measured
- **Bench**: DeepSWE full113 — 113 SWE-bench-style tasks across go/python/typescript/rust/javascript,
  scored by each task's own `tests/test.sh` (baseline regression suite + new tests, reward=1 iff both green).
- **Agent (Path A)**: qwen-code CLI agent, `--max-session-turns 100`, driving a self-hosted model.
- **Model**: `Qwen/Qwen3-Coder-30B-A3B-Instruct` @ `http://100.100.104.147:30001/v1` (sglang).
- **Score rule**: single-attempt pass@1; `resolved = #(gold_reward==1 AND agent patch passes same verifier)`.

## The number
- Headline **0 / 113 = 0.00%**. Valid-only (honest) **0 / 102 = 0.00%** (11 gold_broken excluded).
- All five languages: resolved = 0 (go 0/34, python 0/28-valid, typescript 0/30-valid, rust 0/5, javascript 0/5).

## Is 0.00% plausible? (why it is NOT an infra/harness artifact)
1. **Gold passes on 102/113** -> the harness, images, verifier, and reward extraction all work; a correct
   patch reaches reward=1. So this is not a whole-suite environment collapse.
2. The agent DID run and DID produce substantial patches (42-2958 lines across the four samples), calling
   the Coder endpoint for 58-123 assistant turns each. It is failing on *correctness*, not on plumbing.
3. This audit was made **after** fixing a real verifier bug (python `/opt/venv` not on PATH -> bare
   `python -m pytest` -> "No module named pytest" -> false reward=0 even for gold). Post-fix, gold=1 was
   restored (proof: `igel-persist-feature-schema` gold 0->1) and the honest re-score is still 0.

## Anchors / caveat
- qwen-code is a **generic CLI agent scaffold**, not the DeepSWE-native harness; scaffold choice moves SWE
  scores several-fold, so this 0.00% is the *Path A qwen-code x Coder* operating point, not a ceiling for
  the weights. It is reported as an honest lower-bound data point for this exact (model x scaffold x bench).
- The `external_network_marker` style offline-attempt noise is not relevant here: tasks ran in the task
  containers with the task verifier; the discriminating evidence is gold=1 vs agent=0 on identical tests.
