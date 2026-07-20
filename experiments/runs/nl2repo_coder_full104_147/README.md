# NL2RepoBench × Qwen3-Coder-30B-A3B-Instruct — native qwen-code Path A (104 tasks)

> **Status: RETRACTED_NON_CANONICAL (2026-07-21).** The active headline is withdrawn. This Qwen/old-harness bundle remains audit evidence only and is not a current relay-backed `gpt-5.5` + `medium` NL2Repo score. See [RETRACTED_NON_CANONICAL.md](RETRACTED_NON_CANONICAL.md).

**Run id:** `nl2repo_coder_full104_147` · **Date:** 2026-07-13 · KVM pod (env-kvm-57740737-bzw56)

## Headline

`macro_mean_success_rate` (upstream metric = unweighted mean of per-task
`min(passed/total, 1)`), reported at three denominators for full transparency:

| denominator | macro | micro_pass_rate | what it excludes |
|---|---|---|---|
| **95 model-valid** | **0.1555** | 0.0844 (1745/20684) | 3 infra/judging + 6 offline-dep fake-zeros |
| 101 valid-scored | 0.1462 | 0.0708 (1745/24640) | 3 unscoreable infra/judging tasks |
| 104 all (conservative) | 0.1420 | — | nothing (gaps+isolated counted as 0) |

**The credibility-adjusted model-capability number is `macro = 0.1555` (15.55%)** over the 95
tasks that both scored and were model-scoreable offline (fake-zeros isolated, not model-0).
`denom = 104` total; see `denom_assert.txt`, `headline.json`, `taxonomy.json`.

## Serving identity (measured, not claimed)

`GET :30001/get_model_info` → `model_path =
/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct`,
`model_type qwen3_moe`, `Qwen3MoeForCausalLM` (pod .147, sglang). Full JSON in
`serving/get_model_info_30001.json`. The in-container `container_probe.txt` in each
`verdict_pack/*` re-proves the agent container reached this endpoint at run time.

## Zero taxonomy (the credibility core)

| class | n | counted as |
|---|---|---|
| nonzero (scored >0) | 61 | model score |
| MODEL_TEST_FAIL (agent ran, install ok, pytest ran, 0/total) | 28 | **model true-0** |
| MODEL_BUILD_FAIL (agent ran, model's own source/setup broke the build) | 6 | **model true-0** |
| WHEELHOUSE_GAP (offline `pip install` missing a real dep) | 6 | **install-infra fake-0 → isolated** |
| ISOLATED infra/judging (no summary: hang / transport / manifest defect) | 3 | **isolated** |

- **model true-0 = 34.** Genuine: the model ran (40–81 assistant turns), produced real source,
  but could not reproduce the library from the spec.
- **install-infra fake-0 = 6** (isolated): `boto`→botocore, `fastapi-users`→hatch-regex-commit,
  `markdownify`→beautifulsoup4, `pyautogui`→pymsgbox, `synthetic`→bootstrap-flask,
  `ydata-profiling`→setuptools version-pin. The base image + offline wheelhouse do not satisfy the
  base pyproject's deps offline; the model's source is irrelevant to these. NOT counted as model-0.
- **isolated infra/judging = 3:** `dbutils` (pytest deadlock → judging timeout), `more-Itertools`
  (transport incomplete — manifest row lacks `tar`, tar file absent), `pytorch-grad-cam`
  (manifest row missing `ghcr`/`tar` keys). Unscoreable in this offline harness.

## ★ argv-overflow judging bug — found, fixed, re-run (see calibration.md §4)

18 tasks with `start.md` ≥ 131072 B blew Linux `MAX_ARG_STRLEN` when the prompt was passed as a
single argv element (`qwen -p "$(cat …)"`) → `/usr/bin/env: Argument list too long` → qwen never
launched → false-zeros AND one false-POSITIVE (`databases` scored 0.922 with turns=0 because its
base image leaks the package). Fixed by delivering the identical prompt via **stdin**; all 18 (+4
judging-hangs) re-run. Example correction: `databases 0.922 → 0.026`; `boltons 0 → 0.007`.

## Reproduction closure

- Base images: `repro/image_digests.json` (102/104 carry a `harbor_digest` sha256 anchor;
  all carry `tar_sha256` for the offline transport tar).
- Scoring = faithful port of NL2RepoBench `openhands/post_processor.py` (`scripts/`),
  `--network none` + offline wheelhouse.
- Driver + all launch/merge/classify scripts in `scripts/` (incl. the pre-patch driver
  `nl2repo_qwencode_driver.py.PREFIX_argv_bug` for the bug diff).

## File index

- `headline.json`, `taxonomy.json`, `merged_aggregate.json` — metrics.
- `per_task_table.md`, `per_task.tsv` — all 104 per-task success_rate + class.
- `serving/` — get_model_info + /v1/models provenance.
- `gold/gold_selfcheck_11.json` — 11/11 offline gold self-check (chain validated, no fake-zero).
- `calibration.md` —口径 + full bug/fake-zero methodology (credibility point #9).
- `verdict_pack/{ipytest,decouple,databases,deslib,cerberus}/` — sampled end-to-end evidence
  (qwen real call to :30001 + `pip install -e .` + `pytest`).
- `repro/`, `scripts/`, `denom_assert.txt`, `TRACE.md`, `SHA256SUMS`.
