# TRACE -- DeepSWE full113 x Instruct-2507 (Path A)

1. Serving identity probed on http://100.100.104.147:30000 -> model_path=Qwen3-30B-A3B-Instruct-2507 (:30001 is Coder; not used here).
2. Driver/orchestrator: `deepswe_qwencode_driver_instruct.py` + `deepswe_full113_orchestrator_instruct.py`
   (copies of the Coder versions; only DEFAULT_BASE_URL->:30000, DEFAULT_MODEL->Instruct-2507, identity guard->Instruct-2507).
3. Smoke (1 task) confirmed real :30000 hit + pipeline before the full run.
4. Agent run: full_launch_instruct.sh, c=6 turns=100 -> `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/full113_instruct_20260713T103633Z` -> 113/113, resolved=0, ALL_DONE.
5. Audit run: audit_full_launch_instruct.sh --mode audit --prev-run-root <agent> -> `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/audit_full113_instruct_20260713T144617Z`:
   gold-validation + agent re-verify -> report.json.
6. Bundle: this dir. Denominators 113 (headline) / 106 (valid). NO_PROXY correction applied to gold split.
7. SHA256SUMS sealed over every file.
