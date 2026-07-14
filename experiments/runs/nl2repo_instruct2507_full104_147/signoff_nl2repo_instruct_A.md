# Sign-off: NL2RepoBench x Qwen3-30B-A3B-Instruct-2507 (independent auditor A)

**Auditor identity: Claude (honest, adversarial "assume it is fake" review).**
This is the 12th and final reproduction of the 6-bench x 2-model campaign.

## Verdict: REAL -- headline honest macro = 1.48% (RAW as-recorded 4.03%)

I defaulted to disproving the 4.03% and could not falsify it as fabricated: the data is
internally consistent, the serving is the real Instruct-2507, the judge is a byte-faithful
port of the official post_processor, and the prompt is delivered untampered via stdin. So the
RAW 4.03% is a genuine harness output -> **REAL**. HOWEVER, it is inflated ~2.7x by a
base-image package leak inherent to the official NL2RepoBench images. The honest,
leak-corrected macro is **1.48%** (micro 0.38%, fully_solved 0). This is a LARGER correction
than the brief anticipated (which expected only the databases leak -> ~3.1%).

## Severity-graded findings

- **BLOCKER**: none (no fabrication; correct model; correct formula; reproducible).
- **MAJOR -- base-image package leak (7/12 nonzero tasks)**: every official `<pkg>:1.0` image
  ships the real pypi package in site-packages; strip/overlay never touch site-packages.
  7 tasks score entirely from the leak (recorded_sr == leak_floor_sr): stamina (1.0),
  databases (0.9221), autorccar (0.4615), google-images-download (0.0333), tsfresh (0.0315),
  python-pytest-cases (0.0153), aiofiles (0.0047). 310 of 402 passes are leaked.
- **MAJOR -- databases not reproducible clean**: recorded 142/154; a clean run of the exact
  driver (`pip install -e .` uninstalls the leaked 0.9.0) gives 0 passed. Model delivered no
  source. Honest databases = 0.
- **MAJOR -- "fully_solved=1" is false**: the only fully-solved task (stamina) is a pure leak
  (pytest banner prints leaked `stamina: 24.2.0`; reproduced 129/129 with zero model source).
  Honest fully_solved = 0.
- **MINOR -- anchor caveat**: the Coder-30B anchor (15.55%) corrected only databases; the
  stamina/autorccar/tsfresh leaks are image-level and likely also affect Coder -> the anchor
  may be leak-soft beyond databases.
- **REPRO**: reproduced databases (leak floor 142 / clean-install 0), stamina (leak 129 with
  no source), and a leak-floor sweep of all 12 nonzero tasks (docker 26.1.3, official tars).

## Honest numbers (multi-kouju, like the Coder sign-off)

| | RAW (recorded) | honest (leak-corrected) |
|---|---|---|
| macro | 4.03% (0.040285) | **1.48% (0.014836)** |
| micro | 1.66% (402/24158) | 0.38% (92/24158) |
| fully_solved | 1 | 0 |
| scored denom | 97 | 97 |

- Sum of 97 success_rates = 3.907603 (= 0.040285 x 97, verified).
- Leak sum (7 tasks) = 2.468540 -> honest sum = 1.439063 -> /97 = 1.48%.
- databases-only correction (brief expectation) = 3.08%; full sweep = 1.48%.

## 7 no-summary tasks (excluded from the 97 scored)

| task | class |
|---|---|
| more-Itertools | empty/infra |
| pytorch-grad-cam | empty/infra |
| pyquery | rollout_timeout/infra |
| pytest-cov | rollout_timeout/infra |
| pythonprojecttemplate | install-fail |
| pytz | install-fail |
| synthetic | degenerate/special |

## Serving

`/get_model_info` -> `model_path .../Qwen3-30B-A3B-Instruct-2507`; `/v1/models` ->
`Qwen/Qwen3-30B-A3B-Instruct-2507`; in-band `container_probe.txt` agrees. Real Instruct-2507.

## Bundle contents

`calibration.md`, `leak_reproduction.txt`, `aggregate.json`, `AGGREGATE.txt`,
`serving_get_model_info.json`, `denom_assert.txt`, `sampled_summaries/` (databases, stamina,
retrying, pysondb-v2, autorccar, tsfresh, fuzzywuzzy, arguably), `SHA256SUMS`.

_Signed: auditor A (Claude), independent blind reproduction review._
