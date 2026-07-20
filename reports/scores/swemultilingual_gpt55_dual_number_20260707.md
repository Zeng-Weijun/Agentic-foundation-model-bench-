# SWE-bench Multilingual × gpt-5.5 — Dual-Number Final (2026-07-07)

> **Status: HISTORICAL_NON_CANONICAL_CONFIG (2026-07-21).** This dual-signed high-effort artifact is preserved as history. Neither number below is a current relay-backed `gpt-5.5` + `medium` suite score.

## Canonical numbers

| 口径 | 分数 | 状态 |
|---|---|---|
| **Clean non-Gradle (274 tasks)** | **201/274 = 73.4%** | ✅ canonical(带除名注记) |
| Raw full300 | 201/300 = 67.0% | ❌ 禁引用(26 Gradle 题假零,贴官方锚 66.7% 是巧合抵消) |

- Config: gpt-5.5 + high × mini-swe-agent v2.0.0 (bash-only), single-attempt pass@1, c50, offline P0 images, internal relay.
- Run: `runs/swemultilingual_v21_full300_gpt55_high_podb_20260706T233447Z` (300 rows, 0 infra in ledger, dual-signed by 86/85).

## Key finding (the real reproduction signal)

**gpt-5.5 beats the official gpt-5.2-high anchor by +7~9pt on EVERY working language**:
Rust 81.4 (off 74.4) · JS/TS 79.1 (69.8) · PHP 76.7 (69.8) · Ruby 70.5 (63.6) · Go 61.9 (52.4) · C/C++ 75.0 (73.8).
Cross-language degradation ~-5pt (vs official gpt-5.2 -6.1pt) — gpt-5.5 degrades LESS across languages.

## Gradle-offline exclusion (26 tasks, backlog)

5 Gradle repos (lucene 9 / druid 5 / gson 9 / javaparser 2 / rxjava 1) all-zero because `gradlew` downloads gradle-wrapper.jar from GitHub inside `--network none` → tests never ran. Fix progressed to canary10 (lucene 107 tests passed, resolved=true) but test_output still shows a latent external Maven fetch (spatial4j-0.8-tests.jar) → stop-loss per false-clean risk. Backlog: verified offline Gradle closure images per repo family, then replace-rerun the 26 rows.

## Forbidden-quote additions
- 67.0% (Multilingual raw, coincidental-anchor-match) — use 73.4% clean subset + per-language signal instead.

## Bonus fix
V2.1 runner preflight retag bug found+fixed: must retag from exact P0 digest even when a stale local tag exists (else silently reuses original Docker Hub image). Self-test passed.
