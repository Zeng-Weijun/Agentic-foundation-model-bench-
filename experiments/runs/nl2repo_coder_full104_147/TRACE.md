# TRACE — NL2RepoBench × Qwen3-Coder-30B Path A (nl2repo_coder_full104_147)

Chronological investigation trace (KVM env-kvm-57740737-bzw56, serving :30001 pod .147), 2026-07-13.

1. **Serving identity** — `GET :30001/get_model_info` → `Qwen3-Coder-30B-A3B-Instruct`
   (qwen3_moe, Qwen3MoeForCausalLM). Recorded in `serving/`.

2. **Gold self-check (no serving), 11/11** — ran `--mode gold` on all 11 tasks that have a
   reference wheel. Every task produced real pytest counts (7×1.000; 4 <1.0 = gold-oracle version
   drift, not a chain failure). Offline judging chain + build-backend wheelhouse coverage validated.
   Evidence `gold/gold_selfcheck_11.json`.

3. **Dep-heavy coverage probe** — the wheelhouse holds only build backends. Probed the dep-heavy
   base images (`--network none`): sklearn/scipy/pandas/torch/statsmodels/… are pre-baked and
   `pip check` is clean → offline `pip install -e .` resolves runtime deps. No fake-zero from
   missing runtime deps for the dep-heavy cohort. Gate passed → launched the full run.

4. **Full 104 agent run** — `full104_launch.sh` (conc=8, serving :30001, setsid). Each task:
   docker load (sha256-verified) → native qwen-code writes source → official post_processor scoring
   → rmi.

5. **★ argv-overflow bug discovered mid-run** — several early tasks showed `turns=0`,
   `workspace=only start.md`, and `qwen.stderr` = `/usr/bin/env: Argument list too long`. Root
   cause: the driver inlined the whole `start.md` into a single `-p` argv element; for the 18 tasks
   with `start.md` ≥ 131072 B this exceeds Linux `MAX_ARG_STRLEN`. Contamination is bidirectional:
   false-zeros (boltons, deslib, …) AND a false-POSITIVE (`databases` 0.922 with turns=0 via
   base-image package leakage).

6. **Fix + validation** — qwen reads the prompt from stdin (`-p` help: "Appended to input on
   stdin"). PONG smoke → proper stream-json; boltons (0.2 s failure before) → 46 turns + real
   source, `pip install` rc=0, 3/423. Patch `patch_driver_stdin.py` (backup `.py.bak.argv`).

7. **Stuck-run recovery** — the base run wedged at 99/104 (coordinator killed a 42-min tqdm judging
   hang). Killed the stuck xargs/driver tree; identified 5 incomplete (1 argv-overflow + 4
   judging-hang).

8. **Fixed rerun (22 tasks)** — 18 argv-overflow ∪ 4 judging-hang, `rerun_fixed.sh` with a
   hang-watchdog. 19/22 produced summaries; 3 could not (`dbutils` pytest deadlock, `more-Itertools`
   missing transport tar, `pytorch-grad-cam` manifest-row defect) → isolated.

9. **Merge** — `merge_aggregate.py` (per-task: rerun overrides primary) → 101 scored + 3 isolated
   over denom 104. `databases 0.922 → 0.026`, `boltons 0 → 0.007`, `ipytest hang → 0.486`.

10. **Fake-zero classification** — `classify_zeros.py` over all 104: 61 nonzero, 34 model-true-0
    (28 test-fail + 6 build-fail, e.g. `six` SyntaxError), 6 install-infra fake-0 (isolated —
    verified each hit "No matching distribution" for a real missing dep), 3 infra/judging isolated.

11. **Result** — macro 0.1555 (95 model-valid) / 0.1462 (101 valid) / 0.1420 (all-104 conservative);
    micro 0.0844 (95-model-valid). See `headline.json`, `taxonomy.json`, `calibration.md`.

Scripts for every step in `scripts/`. Raw run roots on the KVM:
`nl2repo_pathA/runs/full104_20260713T004127Z` (primary) + `…/rerun_fixed_20260713T023519Z` (override).
