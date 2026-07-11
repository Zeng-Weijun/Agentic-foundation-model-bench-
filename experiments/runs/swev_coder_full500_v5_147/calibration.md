# calibration.md — 口径卡 (v6)

run_id: `swev_coder_full500_v5_147_20260711T165758Z`
bench: **None**  model: **Qwen/Qwen3-Coder-30B-A3B-Instruct**  scaffold: **None (qwen-code 0.15.6)**

## Headline
- **score = None** (resolved **None** / denominator **None**)
- serving identity before==after: **True** (model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct, sglang=0.5.13, seed=484925000)

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
- **No** include_unverified / no gold-less admission here: all 500 rows carry a real docker eval.
- Denominator = clean subset (not padded with unverified rows). See `denom_assert.txt`.

## 4. anchor 对齐
- No official SWE-bench Multilingual cell exists for Qwen/Qwen3-Coder-30B-A3B-Instruct under this scaffold; this run is reported as a NEW measurement.
- Denominator caveat: this run scores the **clean274 subset** = full300 − 26 offline-Gradle
  false-zero tasks; official SWE-bench Multilingual uses 300. Compare per-language, not raw overall,
  against any official number. Per-language resolved/total below.

## 5. 口径差 / 已知 caveat (disclosed, not hidden)
- No mixed-environment caveat recorded for this run.

## 6. denominator
- results rows = 500, unique = 500, declared = 500  → see `denom_assert.txt` (PASS).
