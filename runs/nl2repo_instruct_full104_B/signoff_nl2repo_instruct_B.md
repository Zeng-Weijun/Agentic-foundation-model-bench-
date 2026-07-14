# NL2RepoBench x Qwen3-30B-A3B-Instruct-2507 (Path A, qwen-code native) — Independent Blind Review B (cross-family)

**Reviewer:** Claude (Sonnet 5), primary; codex-pro (gpt-5.6-sol, reasoning=ultra) cross-check, independent parallel SSH investigation
**Date:** 2026-07-14
**Run under review:** `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/full104_instruct_20260713T223930Z`
**Claim under review:** `macro_mean_success_rate = 4.03%` (raw, 97/104 scored, `total_passed=402/24158`)

## VERDICT: REAL, with a mandatory, severe correction

The run is genuine (real serving, real qwen-code CLI transcripts including honest failures/timeouts, real Docker grading, arithmetic 100% reproducible from raw logs). It is **not** a fabricated number. However, the raw 4.03% figure is **not an honest measure of model capability**: independent, hard, reproducible evidence (including a live re-execution of the grading pipeline) proves that **the two highest-scoring rows in the entire run — including the only "fully_solved" (1.0) task — are 100% environment/image leaks with zero functional agent contribution.**

**Honest corrected macro (databases + stamina + tsfresh zeroed): `2.01%` (0.020144, vs raw 4.03% — roughly HALF).**
**Stricter correction (also removing 4 more implementation-independent rows found by codex-pro): `1.46%`.**

---

## BLOCKER-1: `databases` (142/154 = 92.2%, 2nd-highest score) is a 100% base-image leak

- `.../databases_agent_20260713T231911Z/summary.json:31,34-36,45,62,66` — agent block: `workspace_files: 2`, `assistant_turns: 1`, `tool_calls: 0`, `tool_results: 0`, `removed_package_files: []`. The agent's ONE turn (`.../databases_agent_20260713T231911Z/agent/qwen.stdout.jsonl`, event 2) is literally the text `"[API Error: Request timeout after 483s...]"` — the agent wrote nothing.
- `.../databases_agent_20260713T231911Z/agent/workspace_listing.txt` (post-agent) = only `/workspace` and `/workspace/start.md`. Zero source files exist anywhere the agent touched.
- **Smoking gun** — `.../databases_agent_20260713T231911Z/agent/cmd_0.txt:12,16`: pip install log reads:
  ```
  Found existing installation: databases 0.9.0
      Uninstalling databases-0.9.0:
        Successfully uninstalled databases-0.9.0
  ...
  Successfully installed databases-0.0.1
  ```
  The **real upstream `databases` PyPI package (by Tom Christie, github.com/encode/databases) is pre-installed in the base docker image's site-packages before the agent ever starts.**
- Grading then reports `142 passed, 12 skipped in 5.04s` (`agent/cmd_1.txt`), testing the real upstream package's own test suite (test_databases.py, test_integration.py, etc.), not agent code.
- **Independently reproduced twice**: (1) by me, reading the byte-for-byte logs above; (2) by codex-pro, which loaded `nl2repo-databases.tar` fresh, copied the run's actual (empty) `agent_staging/` onto a pristine container, and re-ran `pip install -e .` + pytest from scratch — obtaining the **identical** `142 passed, 12 skipped` result and the identical "Found existing installation: databases 0.9.0" line. Codex-pro further confirmed via `pip show databases` inside a pristine container that the installed package's `Author: Tom Christie` metadata matches the real upstream project.
- Root cause located in the harness itself: `nl2repo_pathA/nl2repo_qwencode_driver_instruct.py:422-459` (`strip_workspace()`) only deletes package/metadata files from the **staged agent workspace**; it never touches the scoring container's `site-packages`. Its own docstring (lines 424-429) acknowledges awareness of workspace/site-dir interaction bugs but only guards the opposite failure mode (stray dist-info in `/workspace` causing pip to uninstall the agent's own code). It cannot detect or fix a base image that ships the reference solution pre-installed in `site-packages`.
- Same leak independently reproduced in the sibling `full104_20260713T004127Z` (Coder) run directory: `databases 142/154=0.922078, turns=0` — confirms this is a benchmark image-construction bug, not model- or run-specific.

## BLOCKER-2: `stamina` (129/129 = 100%, the ONLY "fully_solved" task) is also a 100% leak — worse than databases

- `.../stamina_agent_20260714T024842Z/agent/cmd_0.txt:2,17,69,80`: the agent's own `pip install -e .` **failed outright** (`rc=1`): `hatchling.build` error "there is no directory that matches the name of your project (stamina)". **No code from the agent was ever installed.**
- Yet `.../stamina_agent_20260714T024842Z/agent/cmd_1.txt:6,23` (pytest, run immediately after the failed install) shows:
  ```
  Tenacity: 9.1.2
  stamina: 24.2.0
  ...
  129 passed, 2 skipped in 0.19s
  ```
  `stamina: 24.2.0` is pytest's own version banner for the **real, calendar-versioned upstream `stamina` package** (Hynek Schlawack, pypi.org/project/stamina/24.2.0/). 0.19s for 131 tests is consistent with a pre-compiled real package, not code the agent supposedly just wrote.
- Transcript audit (`agent/qwen.stdout.jsonl`, 18 assistant turns): the agent's **entire** tool-call history was `todo_write` → `mkdir -p src/stamina/instrumentation` → **seven** `write_file`/`edit` calls, **all seven targeting only `/workspace/pyproject.toml`** (repeatedly hitting token-limit errors: "I'll split the pyproject.toml file into smaller parts..."). It never wrote a single line of `.py` implementation code before the harness's `summary.json:30` `timed_out: true` (2400.1s wall-clock) killed it.
- `summary.json:35-36` again shows `tool_calls: 0, tool_results: 0` despite the real transcript activity above — this field is **broken harness telemetry** (never populated), not evidence of true inactivity; I confirmed this both for stamina (real activity, wrong counter) and for databases (zero activity, same wrong counter coincidentally reads correctly there).
- **Live docker proof** (Claude, independent of codex-pro): loaded `nl2repo-stamina.tar` fresh, ran a `--network none` container from the **pristine, untouched image** (no agent, no overlay at all) and directly imported the package:
  ```
  VERSION= 24.2.0
  FILE= /usr/local/lib/python3.11/site-packages/stamina/__init__.py
  DIR_LISTING= ['typing.py','py.typed','_config.py','__pycache__','__init__.py','instrumentation','_core.py']
  ```
  The pristine image's `/workspace` **also already contains a stale `.pytest_cache/v/cache/nodeids`** — direct evidence pytest was run against the real reference implementation at image-build time and the cache artifact was never cleaned before the image was published/distributed as the agent-facing task image.
- `summary.json:48` `removed_package_files: ["pyproject.toml"]` shows the harness's strip step ran and found something to remove from `/workspace` — irrelevant, since the leak lives in `site-packages`, not `/workspace`.

## MAJOR-1: `tsfresh` (10/317 = 3.15%) — different mechanism, still not agent capability

- Same "1-turn / 0-tool-call / 483s API timeout" signature as databases (`agent/qwen.stdout.jsonl` identical shape; `workspace_listing.txt` = only `start.md`).
- **This is NOT a site-packages leak** (I falsified my own initial hypothesis here): a live pristine-image check (`docker run --network none ... python3 -c "import tsfresh"`) gives `ModuleNotFoundError: No module named 'tsfresh'` — the real package is genuinely absent from the base image.
- Root cause instead: `agent/cmd_1.txt:45,54,63,72,81` show most test files fail collection with `ModuleNotFoundError: No module named 'tsfresh'` (genuine, expected, given zero agent code) — but the 10 tests that DID pass are entirely in `tests/units/feature_selection/test_fdr_control.py`, which imports only `numpy, pandas, pytest, statsmodels.stats.multitest` — **it does not import `tsfresh` at all**. These are self-contained tests bundled in the "total" denominator that pass regardless of whether the agent writes anything. This is a distinct, real scoring-methodology bug (fixed test counts include implementation-independent tests) rather than an image leak, but the practical effect is the same: 10/317 "passed" credit is not attributable to the model.

## MAJOR-2 (codex-pro's additional finding, independently corroborated by convergent macro arithmetic): 4-5 more nonzero rows are partly/wholly implementation-independent

Codex-pro's independent parallel audit (see cross-check section below) additionally found, by reading each task's passing test content directly:
- `autorccar` (6/13): the 6 passes are self-contained mock tests.
- `aiofiles` (1/211): the 1 pass tests only a generic/environment-level concept.
- `python-pytest-cases` (21/1372): the 21 passes are standalone pytest/stdlib issue-reproduction snippets bundled in the suite, not implementation tests.
- `google-images-download` (1/30): the 1 pass is a literal `assert True`.
- `pandarallel` (5/217): 4 of the 5 passes reward the **absence** of `parallel_apply` (negative/non-registration tests); only 1/5 genuinely depends on agent code.

I did not independently re-verify each of these five myself (time-boxed out of scope for my own SSH budget), but I flag them as MAJOR rather than BLOCKER because I have not personally confirmed them — I only cross-checked that removing them changes the macro in the direction and magnitude codex-pro reports (see arithmetic cross-check below, which matched to high precision on the databases+tsfresh+stamina subset I did verify myself).

## CONFIRMED GENUINE (spot checks — not leaks, methodology worked correctly)

- `cerberus` (0/249): 1-turn/0-tool-call/483s-timeout, identical structural signature to `databases`, but scored 0 — proves the timeout signature by itself does not cause false credit; `databases` is anomalous specifically because of its image content.
- `asteval` (0/227, 18 real turns): agent genuinely wrote `asteval/asteval.py` + `__init__.py`; `pip install -e .` genuinely built a real editable wheel from that code (no "Found existing installation" line); pytest genuinely errored (4 errors). Clean, credible negative result.
- `retrying` (14/23 = 60.9%, 3rd-highest score, 30 turns): clean install log (`Successfully installed retrying-1.3.4.dev0`, no "Found existing installation" line), `removed_package_files: ["setup.py","MANIFEST.in"]` populated correctly by the strip step, genuine multi-turn work, `workspace_files: 11`. Legitimate partial success.

## MINOR-1: 7/104 tasks have no summary.json at all (correctly excluded from the 97-scored denominator, not hidden real scores)

Confirmed by direct filesystem enumeration (104 `*_agent_*` directories total, 97 have `summary.json`): `more-Itertools`, `pyquery`, `pytest-cov`, `pythonprojecttemplate`, `pytorch-grad-cam`, `pytz`, `synthetic`. Root causes (spot-checked, mix of infra and agent-induced harness crashes, all in the scoring/grading phase, not the agent phase — the agent's staged output for pyquery/pytest-cov shows real partial work in `agent_staging/`):
- `pythonprojecttemplate`, `pytz`: `OSError: [Errno 122] Disk quota exceeded` during scoring (`logs/pythonprojecttemplate.log`, `logs/pytz.log`).
- `synthetic`: the agent itself ran `mkdir -p /workspace/{...,pyproject.toml,...}` (brace-expansion mistake, treating `pyproject.toml` as a directory name), which later crashes the harness's `docker cp` overlay step: `RuntimeError: overlay cp failed: ... cannot overwrite non-directory "/workspace/pyproject.toml" with directory "/workspace"` (`nl2repo_qwencode_driver_instruct.py:501`).
- `pyquery`, `pytest-cov`: `agent/qwen.stderr.txt` = `[ROLLOUT_TIMEOUT 2400s]` during the agent phase itself, propagating into a `KeyError: 'ghcr'` in the driver's own exception-logging path (`nl2repo_qwencode_driver_instruct.py:566`) that suppresses a proper summary write.
- `more-Itertools`, `pytorch-grad-cam`: launcher-level `rc=1` crashes (not deep-dived; lower priority given consistent pattern above).
This does not inflate the reported 97-scored macro (there is no hidden nonzero credit here), but it is a genuine 6.7% completeness gap worth disclosing alongside the headline number.

## Arithmetic verification (REPRO)

- Independently recomputed from `aggregate.json` rows on the KVM host: `sum(success_rate)/97 = 0.04028456701030928` = reported `macro_mean_success_rate` exactly. `total_passed=402/24158` exact match. **The raw headline arithmetic is not fabricated.**
- Corrected macro (databases + stamina + tsfresh -> 0): **`0.020144113402061858` = 2.01%** (computed independently by me on the KVM host; independently re-derived by codex-pro via a wholly separate Decimal-arithmetic script, agreeing to 15 decimal places: `db_ts_st_97 0.02014411340206185567010309278350515463918`).
- Codex-pro's stricter correction (also removing autorccar/aiofiles/python-pytest-cases/google-images-download and reducing pandarallel to 1/217): `all_confirmed_stored_97 = 0.01464567...` = **1.46%**, `retained_passed = 88/24158` micro = 0.36%.
- If the 7 crashed/unscored tasks are folded in as zero (104 denominator, a stricter-but-defensible alternative convention): raw = 3.76%, corrected (databases+stamina+tsfresh only) = 1.88%.

## Serving identity (confirmed independently, out-of-band)

Direct `curl http://100.100.104.147:30000/v1/models` from my own SSH session (not relying on any harness-written file):
```
{"object":"list","data":[{"id":"Qwen/Qwen3-30B-A3B-Instruct-2507","object":"model","created":1784008367,"owned_by":"sglang","root":"Qwen/Qwen3-30B-A3B-Instruct-2507","parent":null,"max_model_len":262144}]}
```
Matches self-reported `summary.json` fields and matches the harness's own `container_probe.txt` capture taken live during the `databases` task run. Confirmed: Qwen3-30B-A3B-Instruct-2507 via sglang, `max_model_len=262144`.

## Comparison against NL2RepoBench x Coder (15.55%, cited as already double-signed REAL)

The sibling Coder run directory I located (`full104_20260713T004127Z`) is only a **30/104-scored partial/WIP snapshot** (macro=15.22% on that subset, total_passed=482/8401) — not obviously the complete, final run behind the cited 15.55% figure, so I cannot fully reconcile the exact number from this artifact alone. It does, however, independently reconfirm the identical `databases 142/154=0.922078, 0 turns` leak occurring in the Coder run too, which is the single most load-bearing cross-check available: **the leak is a property of the benchmark's docker images, reproducible identically regardless of which model is served.** Given that, a corrected Instruct-2507 macro of ~2.0% against a Coder macro in the ~12-15% range (also requiring its own databases correction per the brief) is directionally plausible — Instruct-2507 is a materially weaker coder on this benchmark, consistent with its general reputation relative to Qwen3-Coder variants, though I have not independently re-verified the Coder run's own final, complete numbers within this review's scope.

## Codex-pro cross-check status (honest disclosure)

`ps aux | grep gpt-5.6-sol` at task start showed **30+ concurrent gpt-5.6-sol processes** already running under the single OAuth account (well over the 6+ threshold). Per instructions I launched exactly one additional instance (`zsh -i -c 'codex-pro exec --dangerously-bypass-approvals-and-sandbox - < .../codex_brief_nl2repo_instruct_B.txt'`, pid 18994) and gave it a generous waiting window rather than an immediate fallback, since it began producing real, verifiable SSH output almost immediately.

Over **35+ minutes** of continuous, real, verifiable work (confirmed via live `ps -p 18994 -o etime` and a growing, substantive output log at `/private/tmp/claude-501/.../scratchpad/review/codex_pro_output_nl2repo_instruct_B.log`), codex-pro independently:
- Recomputed the same macro/micro arithmetic.
- Independently discovered and loaded the same `nl2repo-databases.tar`, then did a **full live re-execution** of the grading pipeline (fresh container + actual `agent_staging` overlay + `pip install -e .` + pytest) and reproduced the identical `142 passed, 12 skipped` result and the identical "Found existing installation: databases 0.9.0" leak signature.
- Independently confirmed `pip show databases` metadata (`Author: Tom Christie`) matches the real upstream project.
- Read the actual harness driver source (`strip_workspace()`, `run_scoring()`, gold vs. agent mode branches) to locate the structural root cause.
- Independently enumerated the same 7 no-summary tasks and found precise root causes for 4 of them (disk quota, overlay-cp type conflict, rollout timeout + KeyError), matching/extending my own findings.
- Independently audited every other nonzero row and flagged 4-5 additional implementation-independent passes beyond what I was specifically asked to check.
- Independently derived a corrected macro (`0.020144113402061858`) that matches my own to 15 decimal places, via a completely separate Decimal-arithmetic script.

Codex-pro had **not yet emitted its final formatted terminal summary** at the point I finalized this report (still in a "final grading/number-unification" synthesis step per its own status messages), most likely due to the 30+ instance OAuth queue slowing per-turn latency rather than any error or stall (no errors, no retries, no repeated/looping behavior observed in the log — purely real, incremental, convergent SSH work throughout). **Zero contradictions** were observed between codex-pro's partial output and my own independently-reached conclusions at any point; several of its findings (the exact macro match, the `pip show` authorship confirmation, the driver source-code root cause, the 4 additional implementation-independent rows) materially strengthened this report beyond what I had independently found alone. I did not wait for its full completion given: (a) my own evidence base was already complete and self-sufficient for a verdict per the task's explicit requirement that "verdict must be based on your own independently reproduced hard evidence," and (b) the marginal value of further waiting was low given zero disagreement across 35 minutes of real overlap. Its full raw log (several MB) is preserved at the path above for anyone who wants to read its eventual final message.

`ps aux` snapshot at launch time (excerpt, full snapshot captured in review transcript): 30+ lines matching `gpt-5.6-sol`, e.g.:
```
Zhuanz1  78048 ... codex --model gpt-5.6-sol -c reasoning.effort=ultra ... resume 019f4a14-7def-7aa2-98be-3e182066fb70
Zhuanz1  67836 ... codex --model gpt-5.6-sol -c reasoning.effort=ultra ... exec -
Zhuanz1  30952 ... codex --model gpt-5.6-sol -c reasoning.effort=ultra ... resume 019f4aaa-7073-7a53-8394-63d21e462397
... (27+ more)
```

## Final honest numbers

| Metric | Value |
|---|---|
| Raw macro (as claimed, 97 scored) | **4.03%** (0.04028456701030928) — arithmetically real, not fabricated |
| Corrected macro (databases + stamina + tsfresh -> 0, 97 denom) | **2.01%** (0.020144113402061858) |
| Stricter corrected macro (codex-pro, +5 more implementation-independent rows, 97 denom) | **1.46%** (0.01464567...) |
| Raw macro if 7 crashed tasks counted in denom (104) | 3.76% |
| Corrected macro if 7 crashed tasks counted in denom (104) | 1.88% |
| Micro (raw) | 1.66% (402/24158) |
| Micro (corrected, databases+stamina+tsfresh removed) | 0.50% (121/24158) |
| Micro (codex-pro strictest) | 0.36% (88/24158) |
| Serving identity | Confirmed: Qwen/Qwen3-30B-A3B-Instruct-2507 via sglang, max_model_len=262144 |
| "Fully solved" (1.0) task count | **0 genuine** (the reported 1, `stamina`, is a 100% environment leak) |

