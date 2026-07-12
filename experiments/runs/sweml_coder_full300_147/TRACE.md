# TRACE.md — full trace pointer (big trace stays on the filesystem)

Full trace is NOT copied into git (241M). It lives on the shared filesystem:

```
HOST_PATH : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_coder_qwencode_full300_147_20260712T064508Z
du -sh    : 241M
instances : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_coder_qwencode_full300_147_20260712T064508Z/instances (240M)
```

## Top-level integrity anchors
- namelist+size manifest sha256 (this collect): `cc8f0908f8ebe9366601158f592d871ac5942d5b1f80bb161450de3c95775fd3`
  (sha256 over a sorted `relpath<TAB>size` listing of every file under the run root — a cheap,
  independent anchor pinning the directory state without reading 225M of content.)
- run's own SHA256SUMS sha256: `0af1c0c990fe363e72d8cb970b90884f79806309ad89fbdcfaf76195e4480f65`  (906 per-file hashes sealed at run end)

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
