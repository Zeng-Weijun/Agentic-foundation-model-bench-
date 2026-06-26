# RepoZero w100 Trace Health Audit - Round 53

Date: 2026-06-26
Lane: read-only trace-health audit
Inspection host: `zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn`
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Run artifact: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/output_codex/gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900`

Scope: read-only artifact audit. No production code, manifests, tests, benchmark outputs, Docker state, commits, or pushes were changed. No token, raw prompt, generated source body, raw stderr payload, or environment secret is printed in this report.

Note: `swe_dev2` printed `The host machine is under maintenance, recommend to restart the workspace.` on SSH, but shared-path reads succeeded.

## Verdict

Primary verdict: **FAIL for benchmark score acceptance**.

Trace-health verdict: **WARN**. This is the correct completed w100 RepoZero Py2JS run, and the per-case trace bundle is structurally present: 400 unique result rows, 400 prompts, 400 Codex logs, 400 attempt logs, and 400 case-result files. The trace is good enough to audit what happened.

It is not healthy enough to publish the raw benchmark score. The raw summary reports `185 / 400` all-pass cases, but the raw score includes rows where Codex did not complete cleanly:

```text
raw all_pass cases:   185 / 400
clean all_pass cases: 131 / 400
timeout rows:         119
nonzero Codex rc:     242
nonzero/all_pass:      54
timeout/all_pass:      38
entry_missing rows:   131
```

Reportable status:

- Do not report raw `185 / 400` as a valid benchmark score.
- `131 / 400` is reproducible from the raw trace as a strict clean-gated audit number, but it should be labeled diagnostic/derived until the runner implements the clean scoring gate itself.
- Raw tests in `summary.json` are `10429 / 19352`; strict clean all-pass rows account for `6530 / 6530` tests on those clean rows, or `6530 / 19352` if every non-clean row is treated as non-scoreable.

## Evidence Commands

Workflow preflight:

```bash
sed -n '1,260p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md
```

Inspection host/path check:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 \
  'zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn' \
  'hostname; date -Is; test -d <run-artifact> && echo artifact_dir_ok; test -d <worktree> && echo worktree_ok'
```

Structured artifact/count probe:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 \
  'zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn' \
  'python3 - <<PY
from pathlib import Path
import json, collections, statistics, time
root = Path("<run-artifact>")
summary = json.loads((root / "summary.json").read_text())
rows = [json.loads(l) for l in (root / "results.jsonl").read_text().splitlines() if l.strip()]
# Count only structured fields and path existence; do not print prompt/source/log payloads.
PY'
```

Safe abnormal sample probe:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 \
  'zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn' \
  'python3 - <<PY
# Select deterministic abnormal case ids and print only structured metadata:
# case id, all_pass, codex_returncode, codex_timeout, path existence, passed/total,
# and boolean log-pattern hits. Do not print log/prompt/generated contents.
PY'
```

Network/config/orphan signature scan:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 \
  'zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn' \
  'python3 - <<PY
# Search only codex.log/codex_attempt_1.log and runner log for safe strings:
# provider-name error, raw.githubusercontent.com, curl/wget, pip install,
# network errors, orphan/PPID markers. Print counts and case ids only.
PY'
```

External dedup evidence read:

```bash
ssh -CAXY -o BatchMode=yes -o ConnectTimeout=20 \
  'zengweijun+zwj3-image.group-ailab-sciversealign-sciversealign-cpu+root.ailab-sciversealign.ws@h.pjlab.org.cn' \
  'cd <worktree> && grep -nE "orphan|PPID|codex_exec_orphan|timeout cleanup|nonzero/all-pass|timeout/all-pass|raw.githubusercontent.com|public-network" \
    _coordination/20260625_harbor_bench/lanes/repozero-scoring-trace-bughunt-round49.md \
    _coordination/20260625_harbor_bench/lanes/repozero-full-run-trace-audit-round48.md'
```

## Run Identity

This is the recently completed 100-concurrency run, not the earlier invalid 38-second config-failure run.

Artifact identity:

```text
run_name=gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900
artifact_dir=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/output_codex/gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900
runner_log=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/worker_repozero_full/repozero_full_worker_w100_codexhome_20260626_153900.log
```

Runner log safe markers:

```text
START 2026-06-26T15:38:57+08:00
HOST zwj2-64rlk-3469265-worker-0
RUN_TAG repozero_full_worker_w100_codexhome_20260626_153900
COMMAND full run_repozero_py2js.sh workers=100 run_name=gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900 CODEX_HOME=<dedicated shared CODEX_HOME>
model=gpt-5.4-mini
base_url=http://100.96.1.101:18540/v1
max_concurrency=100
created_at=2026-06-26T15:38:57+08:00
python tools_repozero_codex_full.py ... --model gpt-5.4-mini --base-url http://100.96.1.101:18540/v1 --workers 100 --timeout-s 2400 --codex-attempts 1 --run-name gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900 --case-source official --resume --include-excluded
ALL_PASS_CASES 185 / 400
TESTS 10429 / 19352
END 2026-06-26T17:37:36+08:00 rc=0
```

Timestamps and file state:

```text
summary.json exists: yes, size=645506, mtime=2026-06-26T17:37:36+0800
results.jsonl exists: yes, size=576628, mtime=2026-06-26T17:37:36+0800
runner log exists: yes, size=636101, mtime=2026-06-26T17:37:36+0800
```

Important profile note:

- This run used `gpt-5.4-mini`.
- The observed runner log and dedicated `CODEX_HOME/config.toml` use `base_url=http://100.96.1.101:18540/v1`, the dev/internal proxy path, not direct `http://8.130.49.170/v1`.
- The dedicated `CODEX_HOME/config.toml` has a valid `[model_providers.packyapi]` block with `name = "packyapi"` and `wire_api = "responses"`. The env-key line was redacted in the probe output.

CODEX_HOME provider check:

```text
codex_home_config_exists=True
[model_providers.packyapi]
name = "packyapi"
base_url = "http://100.96.1.101:18540/v1"
env_key = <redacted>
wire_api = "responses"
provider_name_present=True
provider_name_empty_signature_present=False
```

## Observed Counts

Summary safe fields:

```text
cases_total=400
cases_all_pass=185
tests_passed=10429
tests_total=19352
workers=100
elapsed_seconds=7118.93
model=gpt-5.4-mini
```

Results row integrity:

```text
results.jsonl rows=400
unique cases=400
duplicate cases=0
case_result mismatch with results.jsonl=0
```

Per-case artifact presence:

```text
output_dir exists:      400 / 400
prompt.txt exists:      400 / 400
codex.log exists:       400 / 400
codex_attempt_1.log:    400 / 400
case_result.json:       400 / 400
entry path exists:      269 / 400
generated js/mjs any:   273 / 400
entry missing:          131 / 400
```

Score/status counts:

```text
raw_allpass=185
clean_allpass=131
timeout=119
nonzero=242
rc0=158
rc1=123
rc124=119
nonzero_allpass=54
timeout_allpass=38
entry_missing=131
missing_entry_fail_examples=168
entry_exists_but_missing_entry_fail=37
entry_absent_but_allpass=0
```

Cross-tab:

```text
131 | allpass | rc0   | notimeout | entry
 99 | fail    | rc1   | notimeout | noentry
 49 | fail    | rc124 | timeout   | entry
 38 | allpass | rc124 | timeout   | entry
 32 | fail    | rc124 | timeout   | noentry
 27 | fail    | rc0   | notimeout | entry
 16 | allpass | rc1   | notimeout | entry
  8 | fail    | rc1   | notimeout | entry
```

Per-row seconds:

```text
n=400
sum=565506.74
p50=1379.09
p90=2421.87
p95=2426.02
max=2591.02
```

The `missing_entry_fail_examples=168` versus `entry_missing=131` difference is itself evidence of unhealthy timing/trace semantics: 37 rows have an entry file present now but still carry a `missing generated entry file` failure example in the scored result. This is consistent with post-timeout or post-score output mutation risk and dedups to the process-cleanup family rather than a new independent finding.

## Sample Abnormal Cases

The sample probe printed only structured fields and boolean safe-pattern hits.

| Category | Case | all_pass | rc | timeout | entry exists | passed/total | seconds | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| timeout_allpass | `fractions/test15.py` | true | 124 | true | true | 15/15 | 2411.36 | Raw score counts it all-pass despite timeout; log has `raw.githubusercontent.com` and curl/wget signatures. |
| nonzero_allpass | `bencoder/test6.py` | true | 1 | false | true | 60/60 | 1606.57 | Raw score counts it all-pass despite nonzero Codex rc. |
| missing_entry | `canonicaljson/test20.py` | false | 1 | false | false | 0/60 | 235.64 | Missing entry is correctly a failed row. |
| entry_exists_but_missing_entry_fail | `idna/test9.py` | false | 124 | true | true | 0/60 | 2401.97 | Entry exists now but scored result still has missing-entry failure. |
| timeout_fail | `idna/test6.py` | false | 124 | true | true | 0/51 | 2402.14 | Timeout row with entry present, not scoreable. |
| clean_fail | `bech32/test9.py` | false | 0 | false | true | 22/26 | 217.86 | Clean execution but functional/model failure. |
| timeout_allpass | `pyaes/test17.py` | true | 124 | true | true | 20/20 | 2411.86 | Raw score counts it all-pass despite timeout; log has `raw.githubusercontent.com`, curl/wget, and `pip install` signatures. |
| timeout_allpass | `bech32/test4.py` | true | 124 | true | true | 26/26 | 2412.25 | Raw score counts it all-pass despite timeout. |
| timeout_allpass | `construct/test12.py` | true | 124 | true | true | 20/20 | 2419.90 | Raw score counts it all-pass despite timeout. |
| timeout_allpass | `bech32/test12.py` | true | 124 | true | true | 60/60 | 2424.77 | Raw score counts it all-pass despite timeout; log has `raw.githubusercontent.com` signature. |

Conclusion from samples: yes, the scorer/summary is counting unhealthy traces as `all_pass`. The case-level trace is sufficient to see why, but the raw summary is not a healthy benchmark score.

## Network, CODEX_HOME, And Orphan Evidence

### CODEX_HOME / provider-name contamination

Artifact-level evidence:

```text
provider_name_empty per-case log count: 0
Error loading config.toml per-case log count: 0
runner log provider-name error count: 0
dedicated CODEX_HOME config has name = "packyapi"
```

Conclusion: the earlier `model_providers.packyapi: provider name must not be empty` contamination did not recur in this w100 codexhome run. This run is not the invalid 38-second 400/400 config-failure run.

### Host-side network attempts

Artifact-level per-case log counts:

```text
raw.githubusercontent.com case-log hits: 62
curl/wget case-log hits:              33
pip install case-log hits:            32
network is unreachable hits:           0
Could not resolve hits:                0
```

Runner log string counts for those network terms were 0, so the evidence is inside per-case Codex logs, not the outer runner log.

Conclusion: task containers may still be offline, but host-side Codex behavior in this artifact includes public-network attempt signatures. This is not score-fatal by itself, but it blocks an offline-clean claim and dedups to #27.

### Orphan/process evidence

Artifact-level scan:

```text
per-case log orphan/PPID/codex_exec_orphan hits: 0
runner log orphan/PPID/codex_exec_orphan hits: 0
artifact filename process/orphan hits: []
```

External Round49 evidence for the same run, while it was live:

```text
orphan codex exec PPID 1 count: 53
orphan_ppid1=52
all 52 orphaned rows had codex_returncode=124 and codex_timeout=true
8 orphaned timeout rows already had all_pass=true
orphan_fd_attempt_log_refs=104
```

Conclusion: the completed artifact does not itself preserve live `/proc` orphan evidence. The orphan/process-health finding is external live-probe evidence from Round49 for this same run and dedups to #30. The artifact still shows symptoms compatible with that issue: 37 rows now have entries while their scored result records missing generated entry, and 38 timeout rows are counted all-pass.

## Issue-Ready Findings Or Dedup Notes

No new issue is needed from Round53. The unhealthy behavior is real, but already covered by existing issues:

- Dedup #26: timeout/nonzero Codex executions are counted as all-pass. Round53 final artifact confirms `54` nonzero/all-pass and `38` timeout/all-pass at 400/400.
- Dedup #30: timeout cleanup leaves orphaned Codex descendants and trace mutability risk. Round53 artifact does not contain `/proc` evidence, but final trace still shows post-score inconsistency: `entry_exists_but_missing_entry_fail=37`.
- Dedup #27: host-side Codex logs contain public-network attempt signatures. Round53 final artifact shows `raw.githubusercontent.com` in 62 case logs, curl/wget in 33, and `pip install` in 32.
- Dedup #24: prior CODEX_HOME/provider-name failure is not active here. This run has valid dedicated CODEX_HOME provider configuration and zero provider-name-empty signatures.
- Dedup #23: trace coverage exists for per-row audit, but a claim-safe normalized closed-source benchmark bundle still needs the broader provenance contract.

## Final Answer To User Question

Yes, this is the just-completed w100 RepoZero Py2JS run:

```text
run_name=gpt-5.4-mini_repozero_full_worker_w100_codexhome_20260626_153900
workers=100
start=2026-06-26T15:38:57+08:00
end=2026-06-26T17:37:36+08:00
summary rows=400
results rows=400
unique cases=400
```

Trace correctness:

- Structurally correct and complete enough for audit: PASS/WARN.
- Score health: FAIL.

What can be reported:

- Raw `185 / 400` from `summary.json`: do not report as a valid benchmark score.
- Clean `131 / 400`: reproducible audit-derived clean score, but should be reported only as diagnostic unless the runner itself implements that scoring gate.
- If using test totals, raw is `10429 / 19352`; strict clean rows account for `6530 / 19352` under a non-clean-as-zero policy.

Bottom line: the trace is real and mostly complete, but the benchmark result is unhealthy because raw scoring includes timeout/nonzero Codex executions.
