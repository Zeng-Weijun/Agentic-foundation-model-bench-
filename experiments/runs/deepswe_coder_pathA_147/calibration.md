# Calibration -- how to read this 0.00%

## What was measured
- **Bench**: DeepSWE full113 -- 113 SWE-bench-style tasks across go/python/typescript/rust/javascript,
  scored by each task's own `tests/test.sh` (baseline regression suite + new tests, reward=1 iff both green).
- **Agent (Path A)**: qwen-code CLI agent, `--max-session-turns 100`, driving a self-hosted model.
- **Model**: `Qwen/Qwen3-Coder-30B-A3B-Instruct` @ `http://100.100.104.147:30001/v1` (sglang).
- **Score rule**: single-attempt pass@1; `resolved = #(gold_reward==1 AND agent patch passes same verifier)`.

## The number
- Headline **0 / 113 = 0.00%**. Valid-only (honest) **0 / 106 = 0.00%** (7 gold_broken excluded).
- All five languages: resolved = 0 (go 0/34, python 0/30-valid, typescript 0/32-valid, rust 0/5, javascript 0/5).

## Is 0.00% plausible? (why it is NOT an infra/harness artifact)
1. **Gold passes on 106/113** -> the harness, images, verifier, and reward extraction all work; a correct
   patch reaches reward=1. So this is not a whole-suite environment collapse.
2. The agent DID run and DID produce substantial patches (42-2958 lines across the four samples), calling
   the Coder endpoint for 58-123 assistant turns each. It is failing on *correctness*, not on plumbing.
3. Two independent auditors (A clean-env re-run, B hand-repro) confirm the 0 is REAL. A's clean env is
   strictly *more lenient* to the agent (no proxy pollution, no atomic-apply drops) yet the agent still
   resolves 0 -> the 0 is a reliable upper bound.

## Correction: NO_PROXY judging pollution (gold_valid 102 -> 106)
The original bundle reported gold_valid=102 / gold_broken=11. That **under-reported** gold_valid: the driver's
`container_env()` (deepswe_qwencode_driver.py) built `NO_PROXY`/`no_proxy` from the sglang serving host
`100.100.104.147` **plus the `100.100.0.0/16` CIDR**, and `dexec()` injected that env into the verify container.
The httpx baseline suite's `test_get_environment_proxies` asserts `proxies == {}` with no proxy configured, but
with those values present it reads a proxy for `all://100.100.104.147` and fails -> the whole baseline regression
goes red -> **gold_reward=0 false-red** on httpx-family (and happy-dom) tasks. Auditor-A re-verified these in a
clean env (proxy vars unset, no `container_env` injection) and got **gold=1** on 4 of them:
`httpx-multipart-response-parsing`, `httpx-streaming-json-iteration`, `httpx-deterministic-cookie-store`,
`happy-dom-abort-pending-body-reads`. They are moved gold_broken -> gold_valid, so **gold_valid = 106,
gold_broken = 7**. Evidence: `deepswe_pathA/runs/audit2_independent/broken.log`.
**The 0 conclusion is unchanged**: the same clean env shows the agent still scores 0 on all 4 (genuine test
failures, not the proxy artifact), so headline 0/113 and valid-only 0/106 are both still 0.00%.

## python venv-handicap floor (honest caveat, NOT a proven ceiling)
The agent GENERATION phase ran python tasks **without `/opt/venv` on PATH**, so the agent could not run
`pytest` to self-check its own python edits. Therefore **python 0/30 is a pessimistic FLOOR, not a proven
ceiling** for these weights. The intended faithful fix is to re-run the AGENT on python with the venv-fixed
driver (`--mode agent --langs python --run-root runs/full113_pyfix_<ts>`); **this was NOT done** (no
`full113_pyfix` run root exists). The 76 non-python valid tasks (go/typescript/rust/javascript) had the
agent's native toolchain and are unaffected; their 0/76 independently anchors the overall 0%.

## Anchors / caveat
- qwen-code is a **generic CLI agent scaffold**, not the DeepSWE-native harness; scaffold choice moves SWE
  scores several-fold, so this 0.00% is the *Path A qwen-code x Coder* operating point, not a ceiling for
  the weights. It is reported as an honest lower-bound data point for this exact (model x scaffold x bench).
- The discriminating evidence is gold=1 vs agent=0 on identical tests, in a clean env, on 106 validly-judged tasks.
