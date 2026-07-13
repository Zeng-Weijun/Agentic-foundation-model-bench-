# AUDIT NOTES -- DeepSWE full113 x Instruct-2507 (Path A)

## Verdict: 0/113 (valid-only 0/106) is REAL, not a judging/scoring bug.
- **Agent phase** (`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/full113_instruct_20260713T103633Z`): qwen-code CLI, native, in-container, talking to
  http://100.100.104.147:30000/v1 (Instruct-2507). 113/113 tasks ran; SERVING_BEFORE/AFTER both
  confirm model_path=Qwen3-30B-A3B-Instruct-2507. resolved=0 (all agent_reward!=1).
- **Audit phase** (`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/audit_full113_instruct_20260713T144617Z`): for every task, GOLD patch + verifier (gold_reward) AND the
  agent's prediction.patch.diff + the SAME verifier (agent_reward). No serving generation calls.

## Gold split + NO_PROXY correction (model-independent, reused from the dual-signed Coder audit)
- Raw audit: gold_valid=102 / gold_broken=11.
- 4 httpx/happy-dom gold tasks false-fail under NO_PROXY pollution (driver injects sglang IP +
  100.100.0.0/16 into NO_PROXY -> httpx test_get_environment_proxies reads a proxy for all://... and fails).
  Gold validity is a property of (gold patch, verifier, env) -- NOT the model -- so the Coder audit's
  auditor-A clean-env re-verify (dual-signed) applies verbatim: reclassify those 4 broken->valid.
  => gold_valid=106 / gold_broken=7. Numerator unchanged (agent still 0 on them).

## Disclosed caveats
1. NO_PROXY pollution (above) -- corrected in the denominator; results.jsonl/per_task_verdict hold the RAW gold_reward_raw column plus the corrected column.
2. Instruct context-overflow/explore-loop handicap -- some no-patch tasks are the model overflowing the
   262k window or looping on reads, not producing an edit. Disclosed, not corrected (it is genuine model behavior on the fixed scaffold).
3. Scaffold identical to the Coder run (same driver, same verifier, same turns=100); only base_url/model differ (:30000 Instruct-2507).
