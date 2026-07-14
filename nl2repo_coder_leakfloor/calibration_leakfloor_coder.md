# NL2RepoBench × Qwen3-Coder-30B-A3B-Instruct — base-image LEAK-FLOOR correction (credibility point #9 recheck)

**Author:** Claude (correction recheck, NOT a fresh dual-sign). Reuses the base-image leak
mechanism already confirmed **A+B independently on the Instruct family** (`evidence/nl2repo-instruct-full104-A`
commit 6978dbc8 `leak_reproduction.txt`; `evidence/nl2repo-instruct-full104-B` commit bcb976b census).
This note re-checks whether the **Coder** headline `macro=0.1555` is inflated by the same
harness-level leak (the original Coder audit `fe06947` only corrected `databases` via the argv-stdin
fix; it did not sweep the other images for image-level leakage).

## TL;DR

| metric | recorded (headline `fe06947`) | **HONEST (strict, rec−floor)** | honest (generous upper bound) |
|---|---|---|---|
| **macro_95 (model-valid)** | **0.155454** | **0.142932  (−1.25 pp)** | 0.149444 |
| micro_95 | 0.084365 (1745/20684) | 0.079868 (1652/20684) | — |

**Coder honest macro ≈ 0.143 (strict) / 0.149 (generous). This is only ~1 pp below the headline —
Coder's number is MOSTLY GENUINE, unlike Instruct** (whose raw 0.0403 collapsed to honest ~0.0148
because its tiny score was dominated by the leak). Reason: **51 of Coder's 61 nonzero tasks have a
zero leak floor** (empty model source → 0 passing tests), i.e. Coder genuinely generated those
packages from the NL spec. Coder honest (0.143) still ≫ Instruct honest (0.0148), as expected.

## The leak mechanism (confirmed, not re-hypothesized)

Official offline scoring = start a FRESH base image, **`docker cp <staged>/. :/workspace`** (base
pyproject + ground-truth tests survive; model supplies only source), then `pip install -e .` +
`pytest` under `--network none`. The `docker cp` overlay triggers an **overlay-fs copy-up that
REVIVES whiteout-hidden reference source** shipped in the base image's `/workspace` lower layer, so
ground-truth tests pass **with zero model contribution** — the exact "opaque whiteout hidden layers,
`docker cp` + `pip install -e .` revives them" mechanism A+B documented.

**Leak floor = the driver's OWN `run_scoring` (official post_processor port) run with an EMPTY model
workspace** (zero model source; the empty-dir `docker cp` still triggers the revival). This is
byte-identical to the headline scoring except the model contributes nothing.

### Faithfulness validation (this is why the number is trustworthy)
- `databases` leak floor (empty source) = **142/154 = 0.922**, reproducing the pre-fix argv-bug
  false-positive `0.922` (turns=0) **exactly** — independent confirmation the probe matches the harness.
- Matrix proof the trigger is the `docker cp` overlay (not pip/env): fresh container + `pip install -e .`
  with **no** `docker cp` → `databases` deleted by pip-uninstall → 0 passed; **any** `docker cp`
  (even an empty dir) first → 142 passed. See `matrix_db` evidence.
- Sanity: recomputing the recorded scores over the 95-model-valid denom reproduces the headline
  **0.155454 / micro 1745/20684** to 6 dp, so the口径 is identical to `fe06947`.

## Per-task leak table (10 tasks with leak_floor > 0; the other 51 nonzero have floor = 0 = genuine)

| task | src | recorded pass/total (sr) | leak_floor pass/total | honest sr | class |
|---|---|---|---|---|---|
| fuzzywuzzy | orig | 39/71 (0.5493) | 1/71 (0.0141) | 0.5352 | partial (floor<rec) |
| google-images-download | orig | 16/30 (0.5333) | 1/30 (0.0333) | 0.5000 | partial (floor<rec) |
| justext | orig | 32/61 (0.5246) | 58/61 (0.9508) | 0.0000 | shadow-zeroed (rec<floor) |
| autorccar | orig | 6/13 (0.4615) | 6/13 (0.4615) | 0.0000 | **PURE-LEAK (rec==floor)** |
| tsfresh | rerun | 27/317 (0.0852) | 10/317 (0.0315) | 0.0536 | partial (floor<rec) |
| pytz | orig | 16/235 (0.0681) | 232/235 (0.9872) | 0.0000 | shadow-zeroed (rec<floor) |
| databases | rerun | 4/154 (0.0260) | 142/154 (0.9221) | 0.0000 | shadow-zeroed (rec<floor) |
| aiofiles | orig | 5/211 (0.0237) | 1/211 (0.0047) | 0.0190 | partial (floor<rec) |
| python-pytest-cases | rerun | 21/1372 (0.0153) | 21/1372 (0.0153) | 0.0000 | **PURE-LEAK (rec==floor)** |
| pysondb-v2 | orig | 1/96 (0.0104) | 1/96 (0.0104) | 0.0000 | **PURE-LEAK (rec==floor)** |

### How each class is handled (honest_sr = min(max(recorded_passed − leak_floor_passed, 0)/total, 1))
- **PURE-LEAK, rec == floor (3): `autorccar`, `python-pytest-cases`, `pysondb-v2`** — the model's real
  run scored *exactly* the pure-leak floor ⇒ the model added nothing ⇒ **zeroed (definitive).**
- **shadow, rec < floor (3): `justext`, `pytz`, `databases`** — the model produced real source that
  *scored below* the pure-leak floor (its source partly broke/shadowed the revived reference).
  Strict rule zeroes them (recorded is not attributable clean of the leak). If one instead credits
  the model's shadowed passes at face value, honest macro rises to the **0.149 generous bound**.
- **partial, floor < rec (4): `fuzzywuzzy`, `google-images-download`, `tsfresh`, `aiofiles`** — small
  image leak; subtract the floor, keep the genuine excess.

## Notable corrections vs the Instruct "confirmed-7" heuristic
The leak floor is an **image-level, model-independent** property, so I measured it directly on the
actual scoring path rather than assuming the Instruct-7 list:
- **New leaks not in the Instruct-7:** `justext` (58/61 free), `pytz` (232/235 free), `pysondb-v2` —
  these are the biggest Coder corrections and were NOT flagged by the original Coder audit.
- **Instruct-7 members that barely leak on Coder's real scoring path:** `google-images-download`
  (floor 1/30 — mostly genuine 0.50), `aiofiles` (floor 1/211). Their `pip install -e .` clobbers the
  site-packages copy, so on the operative scoring path they are ~genuine for Coder.
- `stamina` is already 0 recorded (no impact); `databases` was already argv-corrected to 0.026 and is
  now additionally leak-zeroed.

## Serving identity (from `fe06947`, unchanged)
`GET :30001/get_model_info → /…/models/Qwen3-Coder-30B-A3B-Instruct`, `qwen3_moe`,
`Qwen3MoeForCausalLM` (pod .147, sglang). Denominator 95 model-valid identical to the headline.

## Repro
- Probe: `scripts/leakfloor_probe.py` (calls the driver's own `run_scoring` with an empty staging dir).
- Analysis: `scripts/analyze_honest.py` (reproduces headline 0.155454 then applies rec−floor).
- Raw per-task floors: `honest_summary.json`; full leak table `leak_table.md`; per-task evidence
  (`base_workspace_listing.txt`, `cmd_*.txt`, `score.json`) for the 10 leaking tasks under `floors/`.
- Driver + headline: `nl2repo_pathA/runs/nl2repo_merged_104/` (run `nl2repo_coder_full104_147`).

**Honest disclosure:** produced by Claude; reused the A+B-confirmed leak mechanism; this is a
credibility recheck of `fe06947`, not a new dual-signed measurement. Numbers are conservative
(strict rec−floor). Net verdict: **Coder headline 0.1555 → honest ≈ 0.143–0.149; the headline was
mostly genuine (small −1.25 pp leak correction), and Coder remains far above Instruct honest 0.0148.**
