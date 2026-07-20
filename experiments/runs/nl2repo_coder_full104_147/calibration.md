# NL2RepoBench × Qwen3-Coder-30B-A3B-Instruct — Path A calibration & credibility

> **Status: RETRACTED_NON_CANONICAL (2026-07-21).** These calibration figures are preserved for forensic review, not as an active or current-suite NL2Repo score. See [RETRACTED_NON_CANONICAL.md](RETRACTED_NON_CANONICAL.md).

**Scope:** NL2RepoBench (M-A-P) 104-task benchmark, native qwen-code Path A, on the KVM pod
against sglang serving `:30001` (pod `.147`). Credibility point #9: what the headline means, the
offline scoring口径, and the exact handling of false-zeros so they do not pollute
`macro_mean_success_rate`.

## 1. Task and scoring口径 (faithful port of openhands/post_processor.py)

- **0→1 whole-repo generation:** the model gets only `start.md` (NL spec) in a wiped `/workspace`
  and must generate the entire runnable package from scratch (harder than SWE-bench patching).
- **Not binary:** per task `success_rate = min(passed / test_case_count, 1.0)` — the fraction of
  the ground-truth suite that passes.
- **Headline:** `macro_mean_success_rate` = unweighted mean of per-task success_rate (each task
  equal). `micro_pass_rate` = sum(passed)/sum(total) (test-weighted).
- **denom = 104.** Offline judging: strip package+test files from the model workspace → overlay
  onto a FRESH base image (restores base pyproject + ground-truth tests) → `pip install -e .` +
  `pytest` under `--network none` + offline wheelhouse; `PYTHONPATH=/workspace` puts model source first.

## 2. Final numbers

| denominator | macro_mean_success_rate | micro_pass_rate |
|---|---|---|
| **95 model-valid (fake-zeros isolated)** | **0.1555** | 0.0844 (1745/20684) |
| 101 valid-scored (excl 3 infra/judging) | 0.1462 | 0.0708 (1745/24640) |
| 104 all (gaps+isolated=0, conservative) | 0.1420 | — |

**Headline model-capability = macro 0.1555 (15.55%)** over the 95 tasks that scored and were
model-scoreable offline. Reported alongside the conservative all-104 = 0.1420 for transparency
(cf. the DeepSWE sibling's "113 (106 valid)" multi-denominator style).

## 3. Zero taxonomy (applied to EVERY zero; the credibility core)

| class | n | counted as |
|---|---|---|
| nonzero | 61 | model score |
| MODEL_TEST_FAIL (agent ran, install ok, pytest ran, 0/total) | 28 | model true-0 |
| MODEL_BUILD_FAIL (agent ran, model's own source/setup broke build) | 6 | model true-0 |
| WHEELHOUSE_GAP (offline pip install missing a real dep) | 6 | install-infra fake-0 (isolated) |
| ISOLATED infra/judging (no summary) | 3 | isolated |

- **model true-0 = 34.** Real (40–81 turns, real source; could not reproduce the library). Build
  fails verified as the model's own errors, e.g. `six` → `SyntaxError: invalid syntax` in the
  generated source, `tenacity` → broken editable-build config.
- **install-infra fake-0 = 6 (isolated, NOT model-0):** the base image + offline wheelhouse cannot
  satisfy the base pyproject's deps offline — the model's source is irrelevant. Exact missing dep:
  `boto`→`botocore<1.41,>=1.40.52`, `fastapi-users`→`hatch-regex-commit`,
  `markdownify`→`beautifulsoup4<5,>=4.9`, `pyautogui`→`pymsgbox`,
  `synthetic`→`bootstrap-flask>=2.2.0`, `ydata-profiling`→`setuptools<80,>=72` (wheelhouse ships
  83.0.0; version pin excludes it).
- **isolated infra/judging = 3:** `dbutils` (agent ran, install ok, then `pytest` deadlocked →
  25-min timeout crash, no summary), `more-Itertools` (transport incomplete — manifest row lacks
  `tar` and no tar file exists → unloadable offline), `pytorch-grad-cam` (manifest row missing
  `ghcr`/`tar` keys → driver `KeyError`; tar exists but metadata defect).

## 4. ★ The argv-overflow judging bug (18 tasks) — false-zeros AND a false-positive

**Root cause:** driver launched `qwen … -p "$(cat /tmp/nl2repo_prompt.txt)"`, inlining the whole
`start.md` into a single argv element. For 18 tasks with `start.md` ≥ 131072 B (Linux
`MAX_ARG_STRLEN`), exec fails `/usr/bin/env: Argument list too long` → qwen never launches →
`turns=0`, workspace = only `start.md`. Serving was reachable throughout (in-container `/v1/models`
returned the Coder model). Pure prompt-delivery bug, both-direction contamination:
- **false-zeros:** boltons, boto, deslib, deepdiff, dictdatabase, sortedcontainers, structlog,
  jinja, mootdx, wsgidav, rich-click, python-pytest-cases, tsfresh, ydata-profiling,
  stable-baselines3, pdfplumber-stable, more-Itertools.
- **false-POSITIVE (dangerous):** `databases` scored 0.922 with `turns=0` — its base image LEAKS
  the `databases` package into site-packages, so ground-truth tests pass on an empty workspace.

**Fix (faithful):** deliver the identical prompt via **stdin** (`qwen … < /tmp/nl2repo_prompt.txt`,
no `-p`; qwen's `-p` help: "Appended to input on stdin"). Verified: PONG smoke → proper
stream-json; boltons (0.2 s failure before) → 46 turns + real source. Model input is
byte-identical. All 18 argv-overflow + 4 judging-hang tasks re-run with the fixed driver.
Corrections: `databases 0.922 → 0.026`, `boltons 0 → 0.007`, `ipytest (was hang) → 0.486`,
`deslib 0 → 0.070`. Patch `scripts/patch_driver_stdin.py`; pre-patch driver kept as
`scripts/nl2repo_qwencode_driver.py.PREFIX_argv_bug`.

## 5. Gold self-check (offline chain validated, no fake-zeros) — 11/11

`--mode gold` overlays the reference wheel source and scores offline (no serving). All 11 produced
real pytest counts (7 at 1.000: boltons 423/423, emoji, python-slugify, sqlparse, tinydb, funcy,
sortedcontainers; deepdiff 0.185 / humanize 0.974 / aiofiles 0.995 / unidecode 0.985 = gold-oracle
version drift, NOT chain failure). Evidence: `gold/gold_selfcheck_11.json`. Dep-heavy cohort
(sklearn/tsfresh/ydata-profiling/stable-baselines3/pandarallel/deslib/pytorch-grad-cam) probed
`--network none`: scientific stack pre-baked, `pip check` clean → offline install resolves.

## 6. What the number is NOT

- Not an anchor match: NL2RepoBench's reference numbers use a different (OpenHands) scaffold and
  different models. This is a NEW measurement (qwen-code native scaffold + Qwen3-Coder-30B). Use
  only as a coarse band, never a same-scaffold same-model comparison.
- The 6 install-infra gaps are a *harness* offline-coverage limitation (missing wheels), not model
  ability; isolating them is why the model-valid macro (0.1555) > the conservative all-104 (0.1420).
