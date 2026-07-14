# REPRO_GAPS.md — what is not yet one-click

Companion to `REPRODUCE.md`. Everything below is a known gap between "sealed score
exists" and "clone + one command reproduces it". None of these block the 9 lines that
have committed evidence bundles; they are the remaining turnkey polish.

## 1. Three ×Instruct evidence bundles are not committed

`experiments/runs/` contains **10** bundles. The Coder side of DeepSWE / RepoZero /
NL2Repo is sealed, but the **Instruct-2507** side of those three is not — the scores are
known (from the audits / DECISIONS ledger) but there is no `experiments/runs/*_instruct*`
bundle to point at.

| Missing bundle | Known score | Regenerate with |
|---|---|---|
| DeepSWE × Instruct | 0.00% | DeepSWE Path A driver on `:30000` / Instruct model |
| RepoZero × Instruct | 11.50% (node18) / 12.75% (node20·10s) | `REPOZERO_BASE_URL=…:30000 REPOZERO_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507 scripts/run_repozero_offline.sh --execute --mode full` |
| NL2Repo × Instruct | 1.48% honest / 4.03% raw | `full104_launch.sh` pointed at `:30000` / Instruct model |

**Recommendation:** re-run each on `:30000` and seal a bundle (results.jsonl + summary +
calibration + serving identity) next to its Coder sibling, so the table's evidence column
stops saying "regenerate".

## 2. SWE-V runner lives in a worktree, not `scripts/`

The SWE-V orchestrator is `full500_qwencode_orchestrator_v21.py` under
`repo/.worktrees/swev-qwencode-v21-agent51/scripts/`; the turnkey entry is the run-bundle
`launch.sh`. There is **no** `scripts/run_swev_offline.sh` (SWE-V is the one line without a
`scripts/run_*` entry). **Recommendation:** add a `scripts/run_swebench_verified_offline.sh`
wrapper (mirror `run_repozero_offline.sh`) or vendor the orchestrator into the bundle.

## 3. The sibling `run_*_offline.sh` are dry-run-only skeletons

`run_deepswe_offline.sh`, `run_nl2repo_offline.sh`, `run_swebench_multilingual_offline.sh`
support `--dry-run` (emit a planned-command JSON) but **fail closed (`exit 78`)** on real
execution — the real runs used each bundle's `launch.sh` / driver, not these scripts. Only
the new `run_repozero_offline.sh` actually executes (behind `--execute`).
**Recommendation:** promote the other three to real wrappers over their bundle drivers, the
same way `run_repozero_offline.sh` wraps the RepoZero orchestrator.

## 4. DeepSWE bundle has no `launch.sh`

Unlike the other bundles, `deepswe_coder_pathA_147/` ships no `launch.sh`; the runner is
`deepswe_qwencode_driver.py` + orchestrator on the shared disk
(`deepswe_pathA/runs/full113_*`, `audit_full113_*`, pinned in `TRACE.md`).
**Recommendation:** vendor the driver + a `launch.sh` into the bundle's `scripts/`.

## 5. RepoZero node18 caliber is analytical only

The node-image floor (97/400 = 24.25%) is a re-score of 10 crypto/RSA cases under image
node18 (AUDIT_NOTES §3), not a full re-run. `run_repozero_offline.sh --eval-node node18`
fails closed on purpose. **Recommendation:** if a real node18 caliber is ever needed, add a
`PATH` override in `repozero_qwencode_driver.py::dexec_plain` so eval `node` resolves to the
image's `/usr/bin/node`, then wire it into the script.

## 6. τ³ (`run_tau3_offline.sh`) is an empty shell — out of scope

Left as a stub; τ³ has its own separate lane. Not part of these 12. Do not treat the stub as
a runnable line.

## 7. A Multilingual variant sits next to the canonical run

`experiments/runs/sweml_coder_qwencode0162_clean274_20260710t083916z/` (274-instance subset)
lives alongside the canonical `sweml_coder_full300_147/` (full 300). **Canonical = full300.**
**Recommendation:** add a one-line note in the subset bundle marking it non-canonical to avoid
future confusion.

## 8. The 13th bench (ProgramBench) is still running

Not yet sealed; excluded from the 12. Add it to `REPRODUCE.md` §3 once its bundle lands.

## 9. Runner scripts are spread across three trees

Real per-line runners currently live in `scripts/` (skeletons + helpers), `runners/`
(SWE-V, tb21), and `experiments/runs/<line>/scripts/` (the sealed orchestrators). This is
fine for evidence but makes "which script do I run?" non-obvious. **Recommendation:** make
`scripts/run_<bench>_offline.sh` the single documented entry per bench (as
`run_repozero_offline.sh` now is), each delegating to the sealed bundle runner.
