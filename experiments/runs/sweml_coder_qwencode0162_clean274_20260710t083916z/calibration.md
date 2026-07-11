# calibration.md — 口径卡 (v6)

run_id: `sweml_coder_qwencode0162_clean274_20260710t083916z`
bench: **SWE-bench Multilingual**  model: **Qwen/Qwen3-Coder-30B-A3B-Instruct**  scaffold: **qwen-code (qwen-code 0.16.2)**

## Headline
- **score = 0.208029** (resolved **57** / denominator **274**)
- serving identity before==after: **True** (model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct, sglang=0.5.13, seed=598954308)

## 1. resolved 的定义 (adjudication rule)
SWE-bench harness rule (schema_version 2): an instance is **resolved** iff, after applying the
agent `model_patch`, **every** `FAIL_TO_PASS` test transitions to PASS **and every** `PASS_TO_PASS`
test stays PASS. Per-instance `tests_status` (FAIL_TO_PASS / PASS_TO_PASS / FAIL_TO_FAIL / PASS_TO_FAIL)
is preserved in `verdict_pack/<instance>/report.json`, so each verdict is **re-checkable offline**
from this pack alone — no shared-disk trace needed.

## 2. eval harness 版本
- swebench **4.1.0** @ git `f7bbbb2ccdf479001d6467c9e34af59e44a840f9`
- editable install: `-e git+https://github.com/SWE-bench/SWE-bench.git@f7bbbb2ccdf479001d6467c9e34af59e44a840f9#egg=swebench`
- report schema_version: 2  (per-instance report.json under eval/logs/run_evaluation/)

## 3. include_unverified
- **No** include_unverified / no gold-less admission here: all 274 rows carry a real docker eval.
- Denominator = clean subset (not padded with unverified rows). See `denom_assert.txt`.

## 4. anchor 对齐
- No official SWE-bench Multilingual cell exists for Qwen/Qwen3-Coder-30B-A3B-Instruct under this scaffold; this run is reported as a NEW measurement.
- Denominator caveat: this run scores the **clean274 subset** = full300 − 26 offline-Gradle
  false-zero tasks; official SWE-bench Multilingual uses 300. Compare per-language, not raw overall,
  against any official number. Per-language resolved/total below.

| language | resolved | total | score |
|---|---|---|---|
| C | 7 | 30 | 0.233 |
| C++ | 6 | 12 | 0.500 |
| Go | 8 | 42 | 0.190 |
| Java | 0 | 17 | 0.000 |
| JavaScript | 6 | 33 | 0.182 |
| PHP | 4 | 43 | 0.093 |
| Ruby | 9 | 44 | 0.205 |
| Rust | 15 | 43 | 0.349 |
| TypeScript | 2 | 10 | 0.200 |

## 5. 口径差 / 已知 caveat (disclosed, not hidden)
- **provenance_status = MIXED_EVAL_ENVIRONMENTS_DISCLOSED**
- MIXED eval environments: The eval-only repair instantiated the patched MultilingualQwenCodeRunner in the completed run root. Its _write_eval_wrap() rewrote run_root/eval_wrap.py with ContainerCollection.list(ignore_removed=True).
  - main without ignore_removed rows evaluated **without ignore_removed**;
  - 3 cleanup-race repair rows evaluated **with ignore_removed=True** (eval-only frozen-patch repair), all resolved=false.
  - original launch eval_wrap.py: **ORIGINAL_LOST** (severity CRITICAL).
- Effect on score: the 3 repaired rows are unresolved either way, so the mixed environment does
  **not** inflate the resolved count; disclosed for full provenance honesty.

## 6. denominator
- results rows = 274, unique = 274, declared = 274  → see `denom_assert.txt` (PASS).
