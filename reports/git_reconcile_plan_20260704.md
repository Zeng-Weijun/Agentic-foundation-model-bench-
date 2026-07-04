# Git reconvergence plan — shared checkout (by-85, 2026-07-04, PLAN ONLY / no git writes performed)

For the silent window **after the 3-regression fixes land**. Pure read-only inventory below; the operation sequence (§3) is to be executed IN the window, not now. Repo: `.../nips2026/agentic-foundation-model-bench/repo`, HEAD `main@5719bfb`, **ahead 2 (+1 dangling 74ada78) / behind 32**.

## 1. The 21 modified tracked files — by owner/lane + commit/discard verdict
| group (owner/lane) | files | in-origin-32? | verdict |
|---|---|---|---|
| **Live coordination** (lead / all lanes) | `HANDOFF.md`, `DRIVER.md` | no | **commit** as a coordination sync — but ONLY after writers paused (concurrent-append risk). Reconcile against 74ada78's stale HANDOFF snapshot (do NOT restore that). |
| **Bench manifests** (image/enable lane — 55/86) | `manifests/images/{pending_benches,README,repozero,terminal_bench_2_1}.yaml`, `manifests/suite.example.yaml` | no | **commit** — bench-enable manifest work; clean rebase. |
| **⚠ CONFLICT** (image lane) | `manifests/bench_registry.yaml` | **YES (in origin 32)** | **manual-merge** at rebase — 31-line diff local↔origin, both sides intentional (registry rows for different benches). Do NOT clobber either. |
| **Bench tooling** (infra lane) | `scripts/{agentic_bench_images.py, agentic_bench_suite.py, check_offline_images_manifest.py, check_rootless_docker_worker.sh, load_offline_images.sh, rebuild_tb21_fix_git_image.sh, run_terminal_bench_2_1_smoke.sh, stage_repozero_image.sh}`, `scripts/test_{agentic_bench_images,agentic_bench_suite,offline_images_manifest}.py`, `scripts/README.md` | no | **commit** — bench tooling; ★run the 3 `test_*.py` first to confirm intentional/green before committing★; clean rebase. |
| **Root doc** | `README.md` | no | **diff-review** — commit if an intentional doc update, else discard. |

## 2. ahead-2 (+dangling) vs behind-32
- **ahead 2 = `5077974` (r5 TB2.1 map) + `5719bfb` (SWE-V gold-16 audit).** ★Both their files are ALREADY on `origin/main`★ (verified: `tb21_full89_oracle_infra_map_r5_final_20260703.json` + `swev_gold_offline_induced_16_audit_backfill_20260703.md` both `cat-file -e origin/main` = present). **⇒ these 2 commits are DUPLICATES — they will become empty during `pull --rebase` and drop out.** Do not force-push them; expect them to vanish. (They were re-landed on origin via today's worktree commits.)
- **dangling `74ada78`** (86's reset, "TB2.1 truemodel canonical 9/89 + coordination docs"): on disk via reflog ("留盘"). Bundles `HANDOFF.md +1853` / `BENCH_STATUS.md +130` / `DRIVER.md` **+** truemodel scores (`...c89_ulimit65535_r7_...scores.yaml`, `targeted13 scores/summary`). **Verdict:** do NOT restore wholesale (the coordination-doc part is a stale snapshot superseded by the live docs + today's origin commits). **Cherry-pick ONLY the truemodel/targeted13 `scores.yaml`/`summary.md`** — and first check they aren't already on origin (86 may have re-pushed them). Otherwise leave 74ada78 dangling as a reflog backup.
- **behind 32** = origin's advance = today's by-85 reports (daily_digest, regression, RepoZero PAUSED, BENCH_STATUS, tau3 ×4) + 55/86/51 pushes. The shared checkout must `pull --rebase` these onto a clean local.

## 3. Silent-window operation sequence (execute IN the window)
1. **Quiesce writers.** Signal 55/86/51 to stop: (a) editing tracked files (esp `HANDOFF.md`/`DRIVER.md`/`manifests/*`/`scripts/*`), (b) writing run output into the tree. Confirm no active writer (no live tmux touching the repo tree) before touching git.
2. **Safety snapshot.** `git branch backup/pre-reconcile-20260704 HEAD` + `git stash list` check (cheap local ref; nothing lost if the rebase goes wrong).
3. **★ Create `.gitignore` FIRST ★** (see §4 — none exists): ignore `runs/`, `logs/`, `*.bak*`, `*_run*/`, `tmp/`, scratch scores dirs — so run output can't be accidentally staged.
4. **Triage + discard.** `git checkout -- README.md` if not intentional; delete `*.bak_by85_*`; leave untracked run/logs alone (now gitignored).
5. **Commit grouping (targeted `git add <paths>`, NEVER `git add -A`):**
   - Commit A — `git add manifests/images/*.yaml manifests/suite.example.yaml` → "bench manifests: image/enable updates".
   - Commit B — `git add scripts/` → "bench tooling updates" (after `test_*.py` green).
   - Commit C — `git add _coordination/.../HANDOFF.md _coordination/.../DRIVER.md` → "coordination sync".
   - Hold `manifests/bench_registry.yaml` for step 6.
6. **`git pull --rebase origin/main`.** The ahead-2 drop (duplicates). Resolve the ONE conflict `manifests/bench_registry.yaml` by hand (merge both registry-row sets, 31-line diff); `git add` it + `git rebase --continue`. Clean files replay without conflict.
7. **(optional) cherry-pick** 74ada78's unique `scores.yaml`/`summary.md` if not already on origin.
8. **`git push origin main`.**
9. **Verify:** `git status` clean; `git log --oneline origin/main -1` == local HEAD; today's reports present (`git ls-files reports/ | grep 20260704`); run dirs/logs/monitors on disk untouched; `git rev-list --count origin/main..HEAD` == 0 and `HEAD..origin/main` == 0.

## 4. Risk points (call out explicitly)
- **★ NO `.gitignore` exists (verified) ★** — `runs/`, `logs/`, `*.bak`, scratch scores are all untracked-and-unignored → a stray `git add -A` would commit gigabytes of 55's run output. **Create `.gitignore` before any `git add`; use targeted adds only.**
- **55's run-output dirs / `logs/`** — huge, must NEVER be committed. The many untracked `laneB/C/D_round*.md` + `*_snapshot_*.md` are stale coordination artifacts — leave untracked (or archive separately), do not bulk-add.
- **Live monitor files** — `HANDOFF.md` / `DRIVER.md` / `BENCH_STATUS.md` are appended every tick by multiple lanes; commit them only in the quiesced moment (step 1) or they'll race. `BENCH_STATUS.md.bak_by85_20260704` is my backup → discard.
- **`manifests/bench_registry.yaml`** — the single rebase conflict; manual merge, keep both benches' rows.
- **ahead-2 duplication** — expect `5077974`/`5719bfb` to vanish in rebase; if git offers to keep them, that's a duplicate-commit trap — drop them.
- **74ada78 stale HANDOFF (+1853)** — do NOT `git checkout`/`cherry-pick` it wholesale; it predates the live HANDOFF + today's origin.

## 5. One-line summary for the window operator
Quiesce → gitignore → 3 grouped commits (manifests / scripts / coordination) holding bench_registry → `pull --rebase` (ahead-2 self-drop, hand-merge bench_registry only) → push → verify clean + run-dirs untouched.

**Refs:** verified read-only via `git status/log/rev-list/cat-file/diff` (no writes). Conflict set = `{manifests/bench_registry.yaml}`; ahead-2 = duplicates; no `.gitignore`.
