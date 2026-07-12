# TRACE.md — full trace pointer (big trace stays on the filesystem)

Full trace is NOT copied into git (333M). It lives on the shared filesystem:

```
HOST_PATH : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_full500_v5_147_20260711T165758Z
du -sh    : 333M
instances : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_instruct2507_full500_v5_147_20260711T165758Z/instances (328M)
```

## Top-level integrity anchors
- namelist+size manifest sha256 (this collect): `891d025bdd1e31344554fc8aefbacc099bb166145622b1dc54a0fdd6b570c657`
  (sha256 over a sorted `relpath<TAB>size` listing of every file under the run root — a cheap,
  independent anchor pinning the directory state without reading 225M of content.)

## Per-instance trace layout (for anyone re-adjudicating from the full trace)
```
instances/<instance>/agent/prediction.patch.diff          # agent's model_patch
instances/<instance>/agent/qwen_attempt_1.stdout.jsonl     # full agent transcript
instances/<instance>/eval/logs/run_evaluation/**/report.json      # tests_status (FAIL_TO_PASS/PASS_TO_PASS)
instances/<instance>/eval/logs/run_evaluation/**/test_output.txt  # full eval stdout
repairs/<instance>/cleanup_race_eval_only_*/               # 3 cleanup-race eval-only repairs
```
verdict_pack.tar.gz in THIS bundle already carries patch + report.json + test_output_tail per
instance, so offline re-adjudication does not require the full trace above.
