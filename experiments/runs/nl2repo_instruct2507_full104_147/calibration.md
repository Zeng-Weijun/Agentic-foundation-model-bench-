# NL2RepoBench x Qwen3-30B-A3B-Instruct-2507 -- Calibration (independent auditor A, Claude)

Run root: `nl2repo_pathA/runs/full104_instruct_20260713T223930Z`
Scaffold: qwen-code native in-container (Path A, stdin driver). Serving: sglang :30000.
Judge: faithful port of official `openhands/post_processor.py` (docker-cp overlay variant).

## Headline (honest)

| metric | as-recorded (RAW) | honest (leak-corrected) |
|---|---|---|
| macro_mean_success_rate | **4.03%** (0.040285) | **1.48%** (0.014836) |
| micro_pass_rate | 1.66% (402 / 24158) | 0.38% (92 / 24158) |
| fully_solved | 1 (stamina) | **0** |
| denominator (scored) | 97 | 97 |

**The honest headline is macro = 1.48%.** The RAW 4.03% is a genuine, internally
consistent, serving-verified output of the official-fidelity harness, but it is inflated
~2.7x by a base-image package leak inherent to the official NL2RepoBench images (below).
Verdict: **REAL** (not fabricated; correct model; correct formula; reproducible), with a
MAJOR leak caveat that materially lowers the true score.

## What was verified REAL

- **Internal consistency**: recomputed macro from the 97 rows = 0.040285 (exact match to
  the aggregate headline); micro = 402/24158 = 0.016640 (exact match).
- **Serving identity**: `/get_model_info` -> `model_path .../Qwen3-30B-A3B-Instruct-2507`;
  `/v1/models` -> `Qwen/Qwen3-30B-A3B-Instruct-2507`; in-band `container_probe.txt` captured
  during the run agrees. This is the real Instruct-2507, not Coder.
- **Formula fidelity**: `success_rate = min(passed/total, 1)` (driver L477 == official L478,
  byte-identical); `package_files` strip list identical (15 files, driver L89-94 == official
  L197-213); scoring overlays model source onto a fresh official base image `<pkg>:1.0`.
- **Prompt integrity (argv-overflow fix)**: driver delivers the spec via stdin
  (`qwen ... < /tmp/nl2repo_prompt.txt`; databases prompt = 132 KB, well over the 128 KB argv
  limit). No argv truncation, no prompt tampering.

## MAJOR finding: base-image package leak (7 of 12 nonzero tasks)

Every official `ghcr.io/multimodal-art-projection/nl2repobench/<pkg>:1.0` image ships the REAL
pypi package pre-installed in `/usr/local/lib/python3.11/site-packages`. Strip/overlay only
touch `/workspace`, never site-packages, so pytest imports the leaked package instead of the
model's (absent or broken) source. Confirmed by direct in-container probes and reproduction
(see `leak_reproduction.txt`).

Leak-floor sweep (pytest against the pristine base image, NO model source):

| task | recorded_sr | leak_floor_sr | verdict |
|---|---|---|---|
| stamina | 1.0000 | 1.0000 | LEAK (banner prints "stamina: 24.2.0") |
| databases | 0.9221 | 0.9221 (pure) | LEAK (clean pip-install run = 0) |
| retrying | 0.6087 | 0.0000 | GENUINE |
| pysondb-v2 | 0.5938 | 0.0104 | GENUINE |
| autorccar | 0.4615 | 0.4615 | LEAK |
| fuzzywuzzy | 0.1972 | 0.0141 | GENUINE |
| google-images-download | 0.0333 | 0.0333 | LEAK |
| tsfresh | 0.0315 | 0.0315 | LEAK (model did nothing: wf=2, turns=1) |
| pandarallel | 0.0230 | 0.0000 | GENUINE |
| pytestify | 0.0164 | 0.0000 | GENUINE |
| python-pytest-cases | 0.0153 | 0.0153 | LEAK |
| aiofiles | 0.0047 | 0.0047 | LEAK |

**7 LEAK** (recorded == leak floor; model marginal contribution ~0): stamina, databases,
autorccar, google-images-download, tsfresh, python-pytest-cases, aiofiles -- 310 leaked passes.
**5 GENUINE** (leak floor ~0; real model work): retrying, pysondb-v2, fuzzywuzzy, pandarallel,
pytestify -- 92 genuine passes.

Honest correction zeros the 7 leak tasks:
`(sum_97 3.907603 - leak_sum 2.468540) / 97 = 1.439063 / 97 = 0.014836 = 1.48%`.

### databases fake-high (0.9221 -> 0.000)

Base image ships `databases 0.9.0` in site-packages. The model delivered only `start.md`
(zero source; tool_calls=0, turns=1). The recorded pytest saw the leaked 0.9.0 -> 142/154.
A clean re-run of the exact driver sequence: `pip install -e .` uninstalls 0.9.0 and installs
an empty `databases 0.0.1` (base `setup.py` `get_packages("databases")` finds no source dir)
-> `import databases` ModuleNotFoundError -> pytest 5 errors, 0 passed. **Honest databases = 0.**
(The brief anticipated only this task, giving ~3.08%; the full leak sweep gives 1.48%.)

### stamina "fully solved" is a leak, NOT a real solve (1.0 -> ~0)

Base image ships `stamina 24.2.0`. The model delivered `src/stamina` + pyproject.toml; strip
removed pyproject.toml, so `pip install -e .` failed (rc=1) and the leak was never uninstalled.
The recorded pytest banner literally prints `stamina: 24.2.0` (the leaked version). Reproduced
129 passed with NO model source. The model's src/stamina is never imported. **No task is
genuinely fully solved; honest fully_solved = 0.**

## Denominator: 104 tasks, 97 scored, 7 excluded

The 7 no-summary tasks (correctly excluded from the 97 scored):

| task | classification |
|---|---|
| more-Itertools | empty agent dir (infra) |
| pytorch-grad-cam | empty agent dir (infra) |
| pyquery | rollout_timeout 2400s, no scoring (infra/timeout) |
| pytest-cov | rollout_timeout 2400s, no scoring (infra/timeout) |
| pythonprojecttemplate | install-fail (1 turn, cmd_0 ran, no summary) |
| pytz | install-fail (1 turn, cmd_0 ran, no summary) |
| synthetic | degenerate/special task, no scoring |

Among the 97 scored, 85 are 0.000; 32 of those had a failing `pip install -e .`. For NL2Repo
(the model must implement the whole package), a failing install is usually a real model
failure (broken/incomplete package), so these are true zeros rather than infra false-zeros.
A stricter "model-valid" denominator excluding genuine infra false-zeros would slightly raise
the leak-corrected macro, but the dominant correction is the 7-task leak (macro 1.48%).

## Anchor comparison

- Coder-30B (dual-signed REAL): macro **15.55%**. Note: the Coder audit corrected only
  databases (0.922 -> 0.026); the stamina/autorccar/tsfresh/etc. leaks demonstrated here are
  image-level and would also affect any model whose install fails on those tasks -- the Coder
  anchor may itself be leak-soft beyond databases.
- Instruct-2507 honest macro **1.48%** vs Coder 15.55% is consistent with a much weaker model
  failing to implement entire libraries from a natural-language spec.
- databases-only correction (brief's expectation): 3.08%. Full leak sweep: **1.48%**.
