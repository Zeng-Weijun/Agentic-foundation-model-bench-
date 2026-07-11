# TRACE.md — full trace pointer (big trace stays on the filesystem)

Full trace is NOT copied into git (225M). It lives on the shared filesystem:

```
HOST_PATH : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_coder_qwencode0162_clean274_20260710t083916z
du -sh    : 225M
instances : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_coder_qwencode0162_clean274_20260710t083916z/instances (220M)
```

## Top-level integrity anchors
- namelist+size manifest sha256 (this collect): `5ad6162fc9ffc2b59828bd6e597a089f4fea335fcbdc8bbe446de5e593ef4b6d`
  (sha256 over a sorted `relpath<TAB>size` listing of every file under the run root — a cheap,
  independent anchor pinning the directory state without reading 225M of content.)
- run's own SHA256SUMS sha256: `b275d775b12cddb4c64113695a0dfe95d70d1818723c34b1b4d016bd6b246936`  (830 per-file hashes sealed at run end)

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
