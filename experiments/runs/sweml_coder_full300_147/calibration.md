# calibration.md — 口径卡 (v6)

run_id: `sweml_coder_qwencode_full300_147_20260712T064508Z`
bench: **SWE-bench Multilingual**  model: **Qwen/Qwen3-Coder-30B-A3B-Instruct**  scaffold: **qwen-code (qwen-code 0.16.2)**

## Headline
- **score = 0.243333** (resolved **73** / denominator **300**)
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
- **No** include_unverified / no gold-less admission here: all 300 rows carry a real docker eval.
- Denominator = **full 300** SWE-bench Multilingual test set (not padded, not subset). See `denom_assert.txt`.

## 4. anchor 对齐
- Official SWE-bench Multilingual publishes **per-language** cells. Compare THIS run's
  per-language resolved/total (below) against the official per-language numbers; do **not**
  compare a single overall percentage.
- The former local relay GPT overall comparator was removed from the current publication tree on
  2026-07-21. It was not a comparable anchor for this Qwen3 run and must not be reconstructed here.
- Denominator = **full 300** (complete SWE-bench Multilingual test set), including the **26 Java tasks
  served from offline-ised p0 images** (`--network=none`). No subset, no exclusion — NOT a clean-274 run.
  Per-language resolved/total below.

| language | resolved | total | score |
|---|---|---|---|
| C | 7 | 30 | 0.233 |
| C++ | 6 | 12 | 0.500 |
| Go | 12 | 42 | 0.286 |
| Java | 8 | 43 | 0.186 |
| JavaScript | 9 | 33 | 0.273 |
| PHP | 6 | 43 | 0.140 |
| Ruby | 10 | 44 | 0.227 |
| Rust | 13 | 43 | 0.302 |
| TypeScript | 2 | 10 | 0.200 |

## 5. 口径差 / 已知 caveat (disclosed, not hidden)
- serving endpoint: `http://100.100.104.147:30001/v1` (sglang; model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct); before==after=True.
- **Java offline**: 26 Java tasks run from pre-built **offline p0 images** with `--network=none`;
  this applies identically to Coder and Instruct-2507, so cross-model comparison is unaffected.
- **Gradle parser caveat**: 10 Gradle-based tasks are subject to the official multilingual harness's
  Gradle test-output **parser semantics**; this affects **both models identically**, so the
  Coder-vs-Instruct-2507 comparison stays fair. Disclosed, not hidden.
- **Infra recovery (real verdicts — nothing force-marked)**:
  - agent re-run after container-death (agent container died at start → 0-byte stdout → the
    **AGENT** was re-run on the same serving endpoint): apache__lucene-12196, apache__lucene-13704. Real trajectory + real docker eval.
  - Per-row provenance in `results.jsonl`; each recovered row carries a REAL resolved/unresolved
    verdict from tests_status, re-checkable offline in `verdict_pack/<instance>/report.json`.

## 6. denominator
- results rows = 300, unique = 300, declared = 300  → see `denom_assert.txt` (PASS).

## 双签审计 (2026-07-12, 2 auditor 各自独立判 REAL)
两个盲审 auditor 各自:全 300 独立复判 **0 不一致**、live 探测两端口权重路径不同(seed 484925000 vs 61643818,config.json inode 物理独立→非标签互换)、全语言真 test_output(Go/Rust/TS/C/Ruby/PHP + Java 26 offline 真 build+eval)、恢复 3 行全 resolved=false(不抬分)、calibration 无串味(grep 无 SWE-V/princeton 泄漏)、SHA256SUMS 12/12。★结论 **REAL**。遗留 cosmetic(launch.sh 截断/模板残留 .140/report_path 指 run-level 汇总 JSON)不影响判定,launch.sh 本次补回。
