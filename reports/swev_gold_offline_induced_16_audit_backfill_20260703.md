# SWE-V Gold — 16 offline-induced: fix-status audit + backfill plan (2026-07-03)

**Scope:** audit the 16 offline-induced gold failures from `V5_GOLD_LEDGER.md` (`offline-PASSED 484 + offline-induced 16 + upstream-archived 0 = 500`). Per-case fix status + fix path + backfill plan. **No runs launched — plan only, awaiting approval.**

**Source of truth (all cross-checked, not taken on trust):**
- Gold run: `swe/rootless/reports/swev_gold_full500_20260702/gold_results.jsonl`
- Disk re-validation: `swe/rootless/reports/swev_gold_disk_revalidate_20260702/diskval_results.jsonl`
- Ledger: `swe/rootless/reports/swev_gold_disk_revalidate_20260702/V5_GOLD_LEDGER.md`

## Ledger reconciliation — VERIFIED against raw artifacts

Recomputed from the raw set (not the ledger's stated numbers):

| Check | Raw-computed | Ledger | Match |
|---|---|---|---|
| gold_results.jsonl rows | 517 (17 dup rows; 1 conflict `pydata__xarray-7229` False→True on rerun) | — | — |
| unique instances | **500** | 500 | ✅ |
| resolved / resolved_false | **432 / 68** | 432 / (53+15) | ✅ |
| resolved_false split | matplotlib 34 + xarray 19 + real 15 | 53 error + 15 real | ✅ |
| error-class disk-fixed | **52** (of 53) | 52 | ✅ |
| error-class still-unfixed | **1** = `matplotlib-20488` | 1 | ✅ |
| 15 real resolved_false disk-fixed | **0** | 0 | ✅ |
| **offline-PASSED** | **432 + 52 = 484** | 484 | ✅ |
| **offline-induced (unfixed)** | **1 + 15 = 16** | 16 | ✅ |

> Minor footnote: `diskval_results.jsonl` has 57 resolved of 58 re-run — the extra 5 over "52" are re-validations of already-native-passing non-error instances (confirmatory), not new fixes. Net error-class fixes = 52. No accounting impact.

## Fix-status audit — all 16 are 未修 (UNFIXED / fix-pending)

Verified: **0 of the 16 appear as resolved in any offline re-validation** (`diskval_results.jsonl`). None fixed. Classification (offline-induced, not upstream) rests on the SWE-bench Verified guarantee + failing-test evidence; **0 upstream-archived**.

### A. Network-dependent (10) — 未修. Fix = offline local network service + re-eval

| # | instance | failing test (signature) | online-confirmed offline-induced? | fix path |
|---|---|---|---|---|
| 1 | `psf__requests-2931` | `test_connect_timeout` (network) | ✅ **CONFIRMED** (resolves online; evidence `baseline_online/`) | local timeout/httpbin mock |
| 2 | `psf__requests-1724` | httpbin HTTP/DIGEST/BASICAUTH | pending confirmatory (shared signature) | local httpbin |
| 3 | `psf__requests-1766` | httpbin | pending | local httpbin |
| 4 | `psf__requests-1921` | httpbin | pending | local httpbin |
| 5 | `psf__requests-2317` | httpbin | pending | local httpbin |
| 6 | `psf__requests-5414` | httpbin | pending | local httpbin |
| 7 | `sphinx-doc__sphinx-7985` | `test_build_linkcheck` (URL check) | pending | local URL mock |
| 8 | `sphinx-doc__sphinx-8269` | linkcheck | pending | local URL mock |
| 9 | `sphinx-doc__sphinx-8475` | linkcheck | pending | local URL mock |
| 10 | `matplotlib__matplotlib-20488` | `test_https_imread_smoketest` (HTTPS fetch) | online False = proxy `URLError('no host given')` quirk, NOT dead URL → offline-induced | fix proxy URL handling / direct egress; the sole unfixed error-class instance |

### B. Env-dependent (6) — 未修. Fix = env/deps (proxy cannot fix)

| # | instance | failing test | root | fix path |
|---|---|---|---|---|
| 11 | `astropy__astropy-7606` | `test_compose_roundtrip[]` | flaky (empty parametrization) | retry / test-quirk handling |
| 12 | `astropy__astropy-8707` | `test_card_from_bytes` + 7 P2P (fits header) | both variants fail offline → dep/env | dep/env fix + re-eval |
| 13 | `astropy__astropy-8872` | `test_preserve_dtype` + 80 P2P (units/quantity) | both variants fail → dep/version | dep/version pin + re-eval |
| 14 | `sphinx-doc__sphinx-10435` | `test_latex_images` | latex/tex env missing | install latex/tex deps |
| 15 | `pylint-dev__pylint-4661` | `test_pylint_home` | `PYLINTHOME` env | set PYLINTHOME |
| 16 | `django__django-10097` | auth template tests (PasswordChange/Reset) | template/env | template/env fix |

## Backfill plan (DO NOT run until approved)

**Boundary rules (charter v5, honored):** offline fixes + offline re-validation only; networked-online eval is triage-evidence only, stored in `baseline_online/`, **never mixed into offline scores**; no official image/gold/test modified; bug-for-bug — fix only what our offline env lost.

- **Phase 1 — network (10 instances).** Stand up offline local network mocks on the eval host and inject into task containers:
  - `httpbin`-equivalent service (covers 6 psf__requests) — offline container, no egress.
  - linkcheck URL mock (covers 3 sphinx linkcheck).
  - HTTPS image-fetch mock / proxy-URL fix for `matplotlib-20488`.
  - Re-run offline eval for the 10 → move passers to offline-PASSED.
  - Sequence first: `psf__requests-2931` (already online-confirmed) as the Phase-1 canary.
- **Phase 2 — env (6 instances).** Per-case: latex/tex deps (`sphinx-10435`), `PYLINTHOME` (`pylint-4661`), Django template env (`django-10097`), astropy dep/version pin (`8707`,`8872`), flaky-retry (`7606`). Re-run offline.
- **Re-validation:** on `swe_dev2` disk docker (or the new KVM worker — proven put_archive/teardown-clean, see `kvm_worker_bench_pilot_20260703.md`), offline; append to `diskval_results.jsonl`-style ledger; update `V5_GOLD_LEDGER.md` 3-part counts.
- **ROI flag (from ledger):** "Low ROI for 16 instances — pending user decision whether to invest." All 16 are already correctly classified offline-induced / 0-upstream, so the score is defensible as-is at 484/500 offline-PASSED with 16 transparently accounted; backfilling is optional polish, not a correctness fix.

## Decision requested
Invest in the backfill (Phase 1 + 2), or leave the 16 as transparently-accounted offline-induced fix-pending? If invest: full send both phases, or network-only (higher ROI: 10/16)?
