# TB2.1 x Qwen3-30B-A3B-Instruct-2507 x terminus-2 (official harness) — run summary

- **Run**: `tb21_inst2507_t2_c32_0712170859`, 2026-07-12 on KVM Pod B (`env-kvm-57740737-bzw56`).
- **Score**: **resolved = 3 / 89**, accuracy = **mean_pass_at_1 = 0.03370787 (3.37%)**.
- **Serving**: Qwen3-30B-A3B-Instruct-2507 @ `100.100.104.147:30000` (sglang 0.5.13, tp2, seed 61643818), IDENTITY_OK before+after.
- **Harness**: terminal-bench **0.2.18**, agent **terminus-2**, dataset **terminal-bench-2.1-yaml-full89-r7-final-20260703** (89 tasks), concurrency 32, attempts 1, temperature 0.0, timeout 7200s.
- **Completion**: `tb_rc=0`, `runner_rc=0`, batched-runner `attempt=complete -> run=finalized`. Serving healthy throughout (0 5xx/429/connection errors).

## Score partition (tb-native results.json, 89 rows)

| bucket | count | note |
|---|---:|---|
| resolved (is_resolved=true) | 3 | `configure-git-webserver`, `hf-model-inference`, `modernize-scientific-stack` |
| unresolved, solution failed tests (false/unset) | 55 | agent produced a solution, task tests failed |
| unresolved, agent_timeout (7200s) | 28 | agent exhausted the 2h agent budget |
| unresolved, context_length_exceeded | 1 | agent ran out of context |
| unresolved, mailman (null / test_timeout) | 1 | agent not converged (broken postfix); test hung 2h |
| unresolved, tune-mjcf (null / unknown_agent_error) | 1 | agent not converged (speed target unmet); zombie killed |
| **total** | **89** | **denom = 89** |

**mean_pass_at_1 = 3/89 = 0.03370787 = 3.37%.** See `calibration.md` for the v4 口径 (esp. mailman/tune-mjcf and the strict `infra_fail=2` heuristic), `denom_assert.txt` for the denominator proof, `repro_closure.json`/`repro_closure.md` for exact repro, `verdict/` for per-task judgments, `serving/` for identity, `special_evidence/` for the agent-not-converged proofs.

## Resolved task ids (3)
`configure-git-webserver`, `hf-model-inference`, `modernize-scientific-stack`
