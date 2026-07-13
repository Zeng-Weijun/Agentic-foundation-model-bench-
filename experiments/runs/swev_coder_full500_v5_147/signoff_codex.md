# Independent Codex-family adversarial signoff: SWE-bench Verified × Qwen3-Coder 234/500

**Verdict: REAL.**

Claim audited: SWE-bench Verified × `Qwen/Qwen3-Coder-30B-A3B-Instruct` × qwen-code scaffold = **234/500 = 46.8%**, for raw run `swev_coder_full500_v5_147_20260711T165758Z` and sealed bundle `experiments/runs/swev_coder_full500_v5_147/`.

## Reviewer identity and independence

I am the Codex-family independent reviewer for this signoff. The system identity visible to me says that I am an OpenAI Codex agent based on GPT-5. I cannot independently attest to a more specific backend slug, account-auth mode, or transport path, so I do **not** claim to be `gpt-5.6-sol`, OAuth-authenticated, Claude, or an internal relay model.

I read the two prior Claude reviewers' findings as an audit brief, but I did not accept their verdict as evidence by itself. The checks marked **PERSONALLY VERIFIED** below were rerun by me against the KVM raw run or a freshly fetched GitHub ref. Checks marked **PRIOR CLAUDE CONTEXT ONLY** were not rerun by me and are not necessary to my independent REAL verdict.

## Basis for the REAL verdict

### 1. Denominator and exact dataset membership — PERSONALLY VERIFIED

On the KVM pod, I ran:

```bash
RUN=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_v5_147_20260711T165758Z
wc -l "$RUN/results.jsonl" "$RUN/events.jsonl" "$RUN/results.jsonl.bak_before_recover6"
```

Observed:

```text
500 results.jsonl
6 events.jsonl
494 results.jsonl.bak_before_recover6
1000 total
```

I then parsed every JSONL row and loaded the locally cached official dataset with all network access forced offline:

```bash
HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface \
HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python -
# Python: parse results.jsonl; load_dataset("princeton-nlp/SWE-bench_Verified", split="test"); compare IDs.
```

Key output:

```text
RESULT_ROWS 500
RESULT_UNIQUE_INSTANCE_IDS 500
RESULT_DUPLICATES []
RESOLVED_COUNTS {False: 266, True: 234}
EVAL_RC_COUNTS {0: 500}
PERCENT 46.800000000000004
DATASET_ROWS 500
DATASET_UNIQUE_INSTANCE_IDS 500
DATASET_DUPLICATES []
MISSING_FROM_RESULTS []
EXTRA_IN_RESULTS []
EXACT_ID_SET_EQUAL True
EXACT_ID_SEQUENCE_EQUAL False
```

The cached dataset configuration was `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`, last modified 2026-06-17. The sequence order differs, but the exact 500-ID set is equal. There is no shrunk denominator, duplicate substitution, missing official instance, or extra non-dataset instance.

### 2. Every claimed true verdict is backed by an official report — PERSONALLY VERIFIED

I opened every `report_path` named by all 500 result rows and handled both report schemas present in the run: the normal one-instance summary schema and recover6's detailed per-instance schema. I derived `resolved` from each report rather than trusting `results.jsonl`.

Observed:

```text
REPORT_PATH_SCHEMA_COUNTS {'summary': 494, 'detailed': 6}
REPORT_CLASS_COUNTS {'error': 18, 'resolved': 234, 'unresolved': 240, 'empty_patch': 8}
DERIVED_RESOLVED_TOTAL 234
RESULT_RESOLVED_TOTAL 234
REPORT_VS_RESULTS_MISMATCH_COUNT 0
REPORT_VS_RESULTS_MISMATCHES []
TRUE_WITHOUT_RESOLVED_REPORT_COUNT 0
TRUE_WITHOUT_RESOLVED_REPORT []
NONRESOLUTION_CLASS_TOTAL 266
DENOM_CLASS_SUM 500
```

The 18 official evaluation-error cases and eight empty-patch cases are all counted false. That is conservative and cannot inflate the 234 numerator. Most importantly, there are zero `resolved:true` rows without a report-derived true verdict.

### 3. Recover6 did not flip or delete earlier verdicts — PERSONALLY VERIFIED

I independently compared `results.jsonl.bak_before_recover6` with the final `results.jsonl` and parsed all six events.

Observed:

```text
BACKUP_ROWS_UNIQUE 494 494
CURRENT_ROWS_UNIQUE 500 500
COMMON_IDS 494
ADDED_IDS ['astropy__astropy-14096', 'django__django-13109', 'django__django-13449', 'django__django-13810', 'django__django-15467', 'sphinx-doc__sphinx-9698']
REMOVED_IDS []
COMMON_VERDICT_FLIPS []
COMMON_FULL_ROW_CHANGES_COUNT 0
EVENT_TYPE_COUNTS {'infra_error': 6}
EVENT_IDS_EQUAL_ADDED_IDS True
```

The six detailed official reports derive four resolved and two unresolved, exactly matching the six appended result rows. Recovery added the six previously absent infra-error instances; it did not alter any of the 494 common rows.

### 4. Serving identity before, after, and live — PERSONALLY VERIFIED

I hashed and read both sealed run snapshots, compared them byte-for-byte, and queried the live endpoint from the KVM pod:

```bash
sha256sum "$RUN/serving/get_model_info_before.json" "$RUN/serving/get_model_info_after.json"
cmp -s "$RUN/serving/get_model_info_before.json" "$RUN/serving/get_model_info_after.json"
curl --fail --silent --show-error --max-time 20 http://100.100.104.147:30001/get_model_info
```

Observed:

```text
a23649304fefebe031e696efece0dcbbba4b5b17c3eb3ccccaae091f0227b936  get_model_info_before.json
a23649304fefebe031e696efece0dcbbba4b5b17c3eb3ccccaae091f0227b936  get_model_info_after.json
SERVING_SNAPSHOTS_BYTE_IDENTICAL=yes
```

Before, after, and live all returned:

```json
{"model_path":"/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct","tokenizer_path":"/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct","is_generation":true,"preferred_sampling_params":null,"weight_version":"default","has_image_understanding":false,"has_audio_understanding":false,"model_type":"qwen3_moe","architectures":["Qwen3MoeForCausalLM"]}
```

I also read `launch_info.txt`, `runner_config.json`, and `overlay.yaml`; they consistently specify `.147:30001`, the Qwen3-Coder model, qwen-code `0.15.6`, 262144 context, 65536 output-token cap, and offline/`--pull=never` evaluation settings. I rely on `/get_model_info`'s `model_path`, not the spoofable request/response `model` string.

### 5. Official harness and offline patch integrity — PERSONALLY VERIFIED

I read the complete 532-byte `eval_wrap.py`. It imports the cache patch, pins Docker API version `1.44`, and executes:

```python
runpy.run_module("swebench.harness.run_evaluation", run_name="__main__")
```

I read the complete cache patch (`sha256 b65f785ec94b822c9a847bf7af6e54a89c07c0a04bb4edad70097edb0f126a7b`). Its only monkeypatch assignments are:

```python
py_spec.get_requirements_by_commit = cached_requirements
py_spec.get_environment_yml_by_commit = cached_environment_yml
```

It does not replace grading, test-log parsing, resolution comparison, or report generation.

The harness checkout reported:

```text
origin  https://github.com/SWE-bench/SWE-bench.git (fetch)
origin  https://github.com/SWE-bench/SWE-bench.git (push)
HEAD    f7bbbb2ccdf479001d6467c9e34af59e44a840f9
MODIFIED_TRACKED_COUNT=0
DELETED_TRACKED_COUNT=0
UNTRACKED_COUNT=2
PYTHON_UNTRACKED_PATHS=<empty>
```

The two untracked files are top-level historical JSON report outputs:

```text
250522_anthropic_filemap_simple_review__openai--gpt-5.4__t-0.00__p-1.00__c-5.00___swe_bench_verified_test__verified_smoke5_localrelay_20260425.verified_smoke5_eval_20260425.json
smoke5_20260508.smoke5_20260508.json
```

This is a precision correction to the prior Claude statement that `git status --porcelain` was empty. The checkout is not literally porcelain-clean now, but no tracked grading code is modified, deleted, or staged, and neither untracked file is Python or imported by the wrapper. I find no rigged harness seam here.

### 6. Fresh official-harness reproduction — PERSONALLY RERUN

After the user's follow-up narrowed the original two-instance request to exactly one missing fresh run, I chose a resolved instance that was not in the prior Claude sample: `matplotlib__matplotlib-13989`. I used the original prediction file (`sha256 bbd8a473380a4b58ffc0acdf1c46240c29b56a7b4425b5ebf65de391012a0ca8`) and a unique run ID. The command ran from a local persistent tmux shell into the KVM pod:

```bash
ssh -o ConnectTimeout=30 -o BatchMode=yes -o StrictHostKeyChecking=no -CAXY \
  env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'timeout 300 env \
    HF_HOME=/mnt/shared-storage-user/mineru2-shared/zengweijun/.cache/huggingface \
    HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    /mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python \
    /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_v5_147_20260711T165758Z/eval_wrap.py \
    -d princeton-nlp/SWE-bench_Verified -s test \
    -p /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/swev_coder_full500_v5_147_20260711T165758Z/instances/matplotlib_u_matplotlib-13989/prediction.json \
    -i matplotlib__matplotlib-13989 --max_workers 1 \
    -id codex_audit_gpt_matplotlib_20260713T105905Z -n swebench \
    --cache_level env --report_dir /root/codex_audit_recheck_gpt_20260713T105905Z -t 280'
```

Observed official-harness output:

```text
Found 1 existing instance images. Will reuse them.
Running 1 instances...
Evaluation: 100%|██████████| 1/1 [01:26<00:00, 86.90s/it, ✓=1, ✖=0, error=0]
All instances run.
Total instances: 1
Instances submitted: 1
Instances completed: 1
Instances resolved: 1
Instances unresolved: 0
Instances with empty patches: 0
Instances with errors: 0
Unstopped containers: 0
```

The newly written summary and detailed report independently read back as:

```text
/root/Qwen__Qwen3-Coder-30B-A3B-Instruct.codex_audit_gpt_matplotlib_20260713T105905Z.json
resolved_instances: 1
resolved_ids: ["matplotlib__matplotlib-13989"]

/root/logs/run_evaluation/codex_audit_gpt_matplotlib_20260713T105905Z/Qwen__Qwen3-Coder-30B-A3B-Instruct/matplotlib__matplotlib-13989/report.json
"resolved": true
```

The harness wrote its summary and log tree under the remote working directory `/root` despite the supplied `--report_dir`; this path behavior is a caveat about artifact placement, not the verdict. The run ID and output are fresh and separate from the claimed bundle and the Claude reviewer's scratch.

### 7. Current GitHub ancestry and sealed bundle reachability — PERSONALLY VERIFIED

On the internet-enabled `dev` host I performed a real, successful fetch of current `main`:

```bash
git -c http.version=HTTP/1.1 fetch --no-tags origin main:refs/remotes/origin/main
```

Observed before adding this signoff:

```text
FETCH_MAIN_RC=0
ORIGIN_MAIN_HEAD_BEFORE_SIGNOFF=2762dd2e7e49d2c9dd5f6c5c375b885b53a21e3e
COMMIT_08b5e60_ANCESTOR_OF_ORIGIN_MAIN=yes
```

`git ls-tree` at that freshly fetched tip showed the sealed files:

```text
100644 blob 4a82664f0b1d588448dc21b498cba151b62339a2    1066  SHA256SUMS
100644 blob 6caf03141a98056bcb1dce9787ac4906f6317306    1711  calibration.md
100644 blob c061761d5fc0c034b760b29953fc54371c1f3cc6     252  denom_assert.txt
100644 blob e774fc672ae387ccb6334c33d2a0d2dd68e8e62d 4047894  verdict_pack.tar.gz
```

The signoff itself was authored in a new isolated worktree/branch based on that fetched tip. The pre-existing dirty main checkout was not staged, stashed, reset, or otherwise modified.

## Prior Claude evidence not personally rerun

**PRIOR CLAUDE CONTEXT ONLY:** I did not rerun the prior Claude reviewers' three named spot checks, their full `verdict_pack.tar.gz` traversal, their quoted 12/12 sealed SHA check, their historical `.140` serving-seed probe, or the historical 49.0%/48.6% cross-anchor. Those remain corroborating context only. My verdict rests on my own exact 500-ID dataset comparison, all-500 report-derived resolution comparison, recover6 diff, serving identity query/snapshots, harness-code inspection, fresh single-instance official evaluation, and current GitHub fetch/ancestry check.

## Caveats and final adversarial assessment

- The follow-up instruction explicitly reduced the fresh rerun from two new instances to one. My independently rerun sample is therefore exactly one: `matplotlib__matplotlib-13989`.
- The KVM harness checkout has two harmless untracked JSON outputs, so “porcelain clean” is no longer literally true. Tracked harness code remains unmodified and unstaged.
- Eighteen official report summaries are evaluation errors and eight are empty patches; all are counted false. This can reduce, but cannot inflate, the score.
- `/get_model_info` proves the configured/live model path, not a cryptographic hash of every weight shard. The before/after snapshots are byte-identical and the live path matches them.
- The offline dataset comparison used the named cached official Verified configuration stated above; public-network dataset access was deliberately disabled.

I actively looked for the requested failure modes: denominator shrinkage, duplicate/substituted IDs, fabricated `resolved:true` rows, recover-time verdict flips, serving-name spoofing, and grading-code monkeypatches. I found none. The exact official dataset denominator is present; all 234 true rows have report-derived true verdicts; recover6 changes only the six missing infra-error IDs; the trustworthy serving path is consistent before/after/live; tracked official harness grading code is unchanged; and a fresh official evaluation reproduced one independently selected true verdict.

**Final independent Codex-family verdict: REAL — the evidence supports 234/500 = 46.8%.**
