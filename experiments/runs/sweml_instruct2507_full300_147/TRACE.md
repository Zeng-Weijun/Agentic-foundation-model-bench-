# TRACE.md — full trace pointer (big trace stays on the filesystem)

Full trace is NOT copied into git (334M). It lives on the shared filesystem:

```
HOST_PATH : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_instruct2507_qwencode_full300_147_20260712T090033Z
du -sh    : 334M
instances : /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/sweml_instruct2507_qwencode_full300_147_20260712T090033Z/instances (332M)
```

## Top-level integrity anchors
- namelist+size manifest sha256 (this collect): `72a51ca1e96e3a067b674f51128e370b1ee7c3450cf2fd57726545a36c65f2c3`
  (sha256 over a sorted `relpath<TAB>size` listing of every file under the run root — a cheap,
  independent anchor pinning the directory state without reading 225M of content.)
- run's own SHA256SUMS sha256: `5b3cc6ff6921e58dad9cb1c72e6ec3347a6372563557b602429b5e51f87b4d41`  (905 per-file hashes sealed at run end)

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
