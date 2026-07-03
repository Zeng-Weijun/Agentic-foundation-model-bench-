# TB2.1 Full89 Oracle Infra Map r5 — verification note (2026-07-03)

**Verifies:** `tb21_full89_oracle_infra_map_r5_final_20260703.{md,json}` (canonical, generated 2026-07-03T00:02:06Z).

## Locating the map
- Tick log referenced `reports/scores/tb21_full89_oracle_infra_map_r5_20260703.md`. Main repo `reports/scores/` was **empty** (created 17:25).
- Real artifacts were in the **coordination dir**: `_coordination/20260625_harbor_bench/reports/scores/` — both the `_r5_` (07:02, prior) and `_r5_final_` (08:02, canonical) `.md`+`.json`. The tick path was relative to the coordination dir. **No rebuild needed.**

## Verification (authoritative = the `_final_` JSON)
| Check | Result |
|---|---|
| counts | `{total: 89, resolved: 79, unresolved_or_pending: 10}` |
| **evidence artifacts exist (all 89 rows)** | ✅ **EVIDENCE_MISSING = 0** (every row's `evidence` file/dir present on disk) |
| primary `fixture_helper` summary supports its rows | ✅ `resolved_count=62`; of 61 rows citing it, **0** absent from its `resolved_task_ids` |
| 20 resolved rows citing individual `results.json` | ✅ all exist |
| newer 80/89 map anywhere | ❌ none found |

## ⚠️ Accounting correction
Tick log claimed **80/89**; the authoritative final map is **79/89** (10 unresolved listed with per-case reason + evidence path). The "80" is an off-by-one miscount — **use 79/89**. The 10 unresolved: `git-multibranch`, `make-doom-for-mips`, `pytorch-model-recovery`, `query-optimize`, `reshard-c4-data`, `rstan-to-pystan`, `sam-cell-seg`, `schemelike-metacircular-eval`, `train-fasttext`, `video-processing` (8× `docker_api_eof_before_injection` on rl-ov2 upstream docker.sock, 2× `pending_baseline_online_oracle_comparison`).

## Landed
Canonical `_r5_final_` `.md`+`.json` copied to main repo `reports/scores/` (was empty). Uncommitted working-tree change — commit deferred to user.
