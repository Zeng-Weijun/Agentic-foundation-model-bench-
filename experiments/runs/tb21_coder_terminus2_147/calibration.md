# Calibration — TB2.1 terminus-2 caliber (do NOT mix with SWE-V / Multilingual)

## What "resolved" means here
- **Caliber**: Terminal-Bench 2.1 (TB2.1), full 89 tasks, **official `terminus-2` agent**, **single pass@1** (attempts=1, temperature=0.0). `score_rule = single_attempt_pass_at_1_over_89_tasks`.
- **resolved** = terminus-2 solved the task and the task's own tests passed (`is_resolved=true` in tb-native `results.json`). This is the TB2.1 harness verdict, not an LLM judge.
- This number is **not comparable** to SWE-V (bash-only SWE) or the Multilingual lane. The v6 collection script had a bug that mixed those calibers; this document is TB2.1-only and makes no cross-bench claim. The run's own scores.json records: *"Qwen lane is a single pass@1 compatibility probe; no official TB2.1 Qwen anchor is claimed."*

## Score
- **10 / 89 resolved = 0.11235955 = 11.24%** (`accuracy` == `mean_pass_at_1`, identical because attempts=1).

## Anchor
- Historical claim for this line: **~10.1%**. This clean rerun lands at **11.24% (10/89)** — same ~10-13% band, now on a **clean, finalized, infra_fail=0** run.
- For full honesty: the launcher's own NOTES record that the earlier **2026-07-10 Coder run finalized a 12/89 score** but self-reported the strict gate as `blocked`. That "blocked" was a gate artifact, not a scoring failure (see below). So the defensible statement is: *Qwen3-Coder on TB2.1/terminus-2 pass@1 sits in the ~10-13% band; this run = 10/89 = 11.24% with a clean infra_fail=0 finalization.* No official TB2.1 Qwen anchor is asserted.

## infra_fail = 0 is the headline (this is what changed vs the old "blocked" run)
The 2026-07-10 run self-reported `status=blocked` with `infra_fail=89`. Per the launcher NOTES that `infra_fail=89` was **FALSE**: `tb21_strict_batch_summary.py` stamps `infra_fail` from the *batch-level* `tb_rc`, and the 07-10 process took a `SIGTERM` (`tb_rc=143`) during docker teardown **after** `results.json` was already written, so every one of the 89 rows inherited a bogus infra failure.
- **Fix applied this run**: run to natural completion, exit 0 (no `SIGTERM`/^C during teardown). Result: **`tb_rc=0`, `runner_rc=0`, `infra_fail=0`.**
- **v4 per-task scoring consequence**: with `infra_fail=0` there are no infra-poisoned rows to rescue, so **`clean_pass=10` is directly `resolved=10`.** No "rescue the blocked task" step is needed this time.

## The two remaining gate flags are expected, not contamination
1. **`external_network_marker = 12`** — EXPECTED. All 89 r7 composes pin `network_mode: none` on the task container; `terminus-2` runs on the HOST and reaches serving from the host, so the container itself has no network. The 12 markers are the *model's failed offline attempts* (substring scan for `github.com` / `/simple/` / "Could not resolve host"). The promoted gpt-5.5 canonical (63/89) carries the same class of markers. This run additionally captured a **runtime per-container net-isolation proof** (`scripts/assert_net_isolation.sh`, sampling live `tb2-offline/*` containers every 30s, asserting `NetworkMode==none` + zero attached networks), turning "trust the compose" into a positive proof.
2. **`parse_error = 1`** — `headless-terminal`: tb could not find a short test-summary in that task's post-test output ("It's possible that the tests failed to run"). It is folded into the unresolved set (tb-native `n_unresolved=79`).

## Why the tb-native gate still says `status=blocked` / `ready=false`
This is **inherent**: the tb-native readiness gate requires `clean_pass == total`, i.e. an oracle 89/89. **Every** real model run trips it. The authoritative completion signal is the batched-runner's `status=finalized` + `mean_pass_at_1`, exactly how the gpt-5.5 63/89 canonical was promoted under the v4 rules. Do not read this `blocked` as the 07-10 failure mode — that one was the false `infra_fail=89`; this one is the always-on oracle gate with a clean `infra_fail=0` underneath.

## Serving identity
- `100.100.104.147:30001`, `model_path .../Qwen3-Coder-30B-A3B-Instruct`, IDENTITY_OK **before and after** (see `serving/identity_summary.md`). Names are not trusted on this stack; the endpoint+weights are the evidence.
