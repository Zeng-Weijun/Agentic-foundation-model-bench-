# NL2RepoBench x Qwen3-30B-A3B-Instruct-2507 (Path A, qwen-code native) — Independent Blind Review B (cross-family)
## REVISION 2 — supersedes the initial signoff in this same commit history after codex-pro's full independent audit completed

**Reviewer:** Claude (Sonnet 5), primary; codex-pro (gpt-5.6-sol, reasoning=ultra), independent parallel SSH cross-check, ~36 min real runtime, fully completed
**Date:** 2026-07-14
**Run under review:** `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs/full104_instruct_20260713T223930Z`
**Claim under review:** `macro_mean_success_rate = 4.03%` (raw, 97/104 scored, `total_passed=402/24158`)

## VERDICT: FAKE (as a claim of model capability)

Both independent reviewers (Claude primary, codex-pro cross-check) converge, with zero factual contradiction, on: the top-level arithmetic is real and exactly reproducible (`sum(rows[*].success_rate)/97 = 0.04028456701030928`, matches `aggregate.json` exactly) — **but the number is FAKE as a claim that "Qwen3-30B-A3B-Instruct-2507 achieved 4.03% on official NL2RepoBench."** Reasons, in order of severity:

1. The **only "fully_solved" (1.0) task in the entire run is 100% fake** (`stamina` — real upstream package graded via an image-layer leak; the agent's own install failed and it wrote zero implementation code).
2. The **2nd-highest score (`databases`, 0.922) is also 100% fake** (same class of image leak, independently reproduced via live re-execution by both reviewers).
3. At least **5 more nonzero rows contain wholly or partly implementation-independent credit** (`tsfresh`, `autorccar`, `aiofiles`, `python-pytest-cases`, `google-images-download`, 4/5 of `pandarallel`) — codex-pro traced each to its exact passing test and showed the pass does not exercise agent-written code.
4. **94 of the 97 scored tasks terminated abnormally** (60 via a ~483s client-side API-timeout mid-run, 34 via the outer 2400s hard wall-clock kill — disjoint sets; only `deslib`, `graphneuralnetwork`, `structlog` finished normally). This is a client retry/concurrency-vs-serving-latency mismatch in the evaluation stack itself, not deliberate model behavior, but it means the reported number is a **survivor statistic from a mostly-broken evaluation run**, not a clean capability measurement.
5. **7/104 tasks are silently missing** from the denominator with non-uniform, not-all-innocuous causes (see below) — including one (`synthetic`) that is a genuine model-caused failure a fail-closed protocol should have scored as zero, and two (`pyquery`, `pytest-cov`) that show real, substantial partial model work (26 and 49 assistant turns) lost to a driver crash, with unknowable counterfactual outcome.

**Bottom line: 4.03% is neither a valid upper bound nor a valid lower bound on Qwen3-30B-A3B-Instruct-2507's true NL2RepoBench capability.** Known leakage inflates it (corrected floor after removing every independently-proven false-positive: **1.46%**); known infra/timeout failures suppress an unknown, unquantifiable amount in the other direction. A clean number requires a fail-closed rerun with fixed image contamination, fixed telemetry, and a concurrency/timeout budget matched to the serving endpoint's actual latency.

---

## BLOCKER-1: `databases` (142/154 = 92.2%) — image-layer leak, precise mechanism

- `databases_agent_20260713T231911Z/summary.json`: `agent.workspace_files=2`, `agent.stream.assistant_turns=1`, `agent.stream.tool_calls=0`, `agent.removed_package_files=[]`, `agent.pytest_results={passed:142,failed:0,errors:0,total:154,success_rate:0.922078}` (lines 31,34-36,45,62,66 in the raw file).
- `agent/qwen.stdout.jsonl`: exactly 3 events (system/assistant/result); the sole assistant text is `"[API Error: Request timeout after 483s...]"`. Zero tool calls, zero files written. `agent/workspace_listing.txt` (post-agent) = only `/workspace` and `/workspace/start.md`.
- `agent/cmd_0.txt:12,16`: pip log shows `Found existing installation: databases 0.9.0` being uninstalled, then `Successfully installed databases-0.0.1` (agent's empty editable install), followed by `cmd_1.txt`: `142 passed, 12 skipped in 5.04s`.
- **Precise root-cause mechanism (codex-pro, via direct docker image-layer inspection of `nl2repo-databases.tar`)**: the image tar contains **two copies** of the real upstream implementation — one under `/workspace/databases/**` in an early layer, one under `/usr/local/lib/python3.11/site-packages/databases/**` (with `databases-0.9.0.dist-info`) in a later layer — and a final layer containing `/workspace/.wh..wh..opq` (an opaque whiteout) that hides the early-layer `/workspace/databases` source in the normal merged view. Testing the exact harness path (`docker cp agent_staging/. container:/workspace` with only `start.md` in staging, then `pip install -e .`) reproducibly resurrects the hidden lower-layer `/workspace/databases` source through the `fuse-overlayfs` merge, and `pip install -e .` binds that real, resurrected implementation to the dummy `0.0.1` project metadata — this is the actual scored source, not (only) the global site-packages copy, which genuinely does get uninstalled and would fail to import on its own. **Correction to my own initial hypothesis**: my original claim (site-packages copy survives uninstall and gets imported directly) was directionally right about "leak" but wrong about which physical copy is the scored source; codex-pro's layer-level reproduction is the more precise, better-evidenced mechanism and supersedes mine.
- **Independently reproduced three separate times**: (1) me, from logs; (2) codex-pro, full live re-execution of the exact grading path (byte-identical `142 passed, 12 skipped`); (3) codex-pro again, isolating the causal path with/without the harness overlay to pin the exact mechanism.
- Same leak independently present in the sibling Coder run's calibration docs (`nl2repo_merged_104/README.md`, `calibration.md`): Coder's `databases` row was corrected from 142/154 down to **4/154** (not fully zeroed — a small residual of genuinely non-leaked passes) — confirms the leak is a property of the benchmark's docker image, reproducible regardless of which model is served.
- `databases` must be zeroed for any capability estimate.

## BLOCKER-2: `stamina` (129/129 = 100%, the only "fully_solved" task) — image-layer leak, agent's own install failed

- `agent/cmd_0.txt:2,17,69,80`: the agent's own `pip install -e .` **failed** (`rc=1`, hatchling: "no directory that matches the name of your project (stamina)"). No agent code was ever installed.
- `agent/cmd_1.txt:6,23`: pytest nonetheless reports `stamina: 24.2.0` (pytest's version banner for the real upstream package) and `129 passed, 2 skipped in 0.19s`.
- Full-transcript audit (both reviewers independently read the complete `agent/qwen.stdout.jsonl`, not just event counts): the agent's entire tool-call history (9 tool_use / 8 tool_result events, confirmed by both reviewers) was `todo_write` → `mkdir -p src/stamina/instrumentation` → **seven** `write_file`/`edit` calls, **all seven targeting only `/workspace/pyproject.toml`**, repeatedly hitting token-limit errors. Zero `.py` implementation files were ever written before the 2400.1s wall-clock kill (`summary.json: agent.timed_out=true`).
- **Live docker proof** (Claude, independent of codex-pro): booted a container from the **pristine, untouched** `nl2repo-stamina.tar` image (no agent, no overlay at all) and directly confirmed `stamina.__version__ == '24.2.0'` at `/usr/local/lib/python3.11/site-packages/stamina/__init__.py`, with a full module tree (`_core.py`, `_config.py`, `instrumentation/`). The pristine image's `/workspace` also already contains a **stale `.pytest_cache/v/cache/nodeids`**, direct evidence pytest was run against the real reference implementation at image-build time and the artifact was never cleaned before distribution. Codex-pro independently confirmed the same via the retained tar's `stamina-24.2.0.dist-info` and its `direct_url.json` pointing at the image builder's own `/project`.
- `summary.json: agent.stream.tool_calls=0` is confirmed (both reviewers) to be a parser/instrumentation defect that never correctly counts nested tool blocks — it is not evidence the model took no action. The model did act; none of its actions produced any scoreable code.
- `aggregate.json: fully_solved=1` (the `stamina` row) is wholly spurious. **After correction, zero tasks are genuinely fully solved.**
- `stamina` must be zeroed for any capability estimate.

## BLOCKER-3: `tsfresh` (10/317 = 3.15%) — different mechanism (test-design leak, not image leak)

- Same 3-event/483s-API-timeout/empty-workspace signature as `databases`.
- **Falsified my own initial hypothesis**: a live pristine-image check (both reviewers, independently) shows `import tsfresh` genuinely raises `ModuleNotFoundError` in the untouched base image — `tsfresh` is NOT pre-installed. `agent/cmd_1.txt:45,54,63,72,81` confirms all package-dependent test files fail collection with the same error.
- The 10 passes are entirely in `tests/units/feature_selection/test_fdr_control.py`, which imports only `numpy, pandas, pytest, statsmodels.stats.multitest` — it **never imports `tsfresh`** and directly tests `statsmodels` across 10 parametrized cases. This is a test-suite/denominator design bug (implementation-independent tests bundled into the "total" count), not an image leak — but the practical effect is identical: 10/317 credit is not attributable to the agent.
- Secondary finding (codex-pro): `summary.json` reports `errors=48` but the raw pytest output only shows 24 actual collection errors — the harness's result-parser appears to double-count textual error markers per collection failure. A MINOR analyzer bug independent of the leak.
- `tsfresh` must be zeroed for any capability estimate.

## BLOCKER-4: 5 more nonzero rows contain wholly/partly implementation-independent credit (codex-pro, with exact citations; not independently re-verified by me from scratch, but methodology fully consistent with the 3 I did verify)

| Task | Raw | Finding | Corrected |
|---|---:|---|---:|
| `autorccar` | 6/13=0.4615 | All 6 passes test mock classes defined and used entirely within the test files themselves (`test/stream_server_test.py`, `test/ultrasonic_server_test.py`); import no agent code | 0/13 |
| `aiofiles` | 1/211=0.0047 | Sole pass (`test_simple.py::test_serve_small_bin_file_sync`) is documented as testing a generic sync-server concept and imports no `aiofiles`; all real-package imports fail | 0/211 |
| `python-pytest-cases` | 21/1372=0.0153 | All 21 passes are standalone pytest/stdlib issue-reproduction snippets that never import `pytest_cases`; the explicit plugin-presence test fails; 274 package-dependent files fail import; task also `timed_out=true` | 0/1372 |
| `google-images-download` | 1/30=0.0333 | Sole pass (`tests/test_sample.py`) is a literal unconditional `assert True` | 0/30 |
| `pandarallel` | 5/217=0.0230 | 4 of 5 passes are `AttributeError` cases that pass only because `DataFrame.parallel_apply` is absent (attribute-lookup failure coincidentally matches expected exception); only `test_memory_fs_root_environment_variable` genuinely imports and exercises agent-created `pandarallel.core` | 1/217 |

Codex-pro explicitly did **not** find sufficient evidence to zero `retrying` (14/23), `pysondb-v2` (57/96), `fuzzywuzzy` (14/71), or `pytestify` (2/122) — in each, installation/import genuinely reaches agent-written files. I independently spot-checked `retrying` myself (clean install log, no "Found existing installation" line, `removed_package_files` correctly populated, real 30-turn transcript) and confirm it is legitimate.

## MAJOR-1: 94/97 scored tasks terminated abnormally (codex-pro, full census — not a 2-3 example spot check)

- 60/97 scored tasks end in a ~483/484s client-side API-timeout event mid-run.
- 34/97 scored tasks hit the outer 2400s hard wall-clock kill (`timed_out=true`).
- These sets are disjoint → **94/97 (97%) of everything the headline number is computed over terminated abnormally.** Only `deslib`, `graphneuralnetwork`, `structlog` reached a normal terminal condition.
- Root cause (codex-pro, via live serving-side inspection — see below): the qwen-code CLI client uses a ~120s per-request timeout with 3 retries (≈483s total), while up to 8 tasks ran concurrently against a single sglang endpoint; this is a client retry-policy/concurrency-vs-serving-latency mismatch in the evaluation stack, not evidence the model "chose" to submit empty workspaces.
- This creates a real, unquantifiable **downward** bias (legitimate model capability likely being suppressed for many of the 94) that partially offsets the leak-driven **upward** bias — both directions are real and neither can be precisely sized from this run alone.

## MAJOR-2: `agent.stream.tool_calls` telemetry is broken across the whole run, not just the 3 spot-checked tasks

Codex-pro parsed nested `message.content` structures directly in all 97 `qwen.stdout.jsonl` transcripts: **74/97 scored tasks show real tool use** (write_file/edit/run_shell_command/etc.) despite **100% of summaries reporting `tool_calls=0`**. Confirmed examples beyond `stamina`: `autorccar` (multiple writes+shell), `retrying` (11 writes), `fuzzywuzzy` (8 writes + 8 edits). This field must never be used as evidence of model inaction — only the 3-event/API-timeout-shaped tasks (`databases`, `tsfresh`, `cerberus`, and ~22 similar) are confirmed genuinely inactive by direct transcript inspection, not by this counter.

## MAJOR-3: 7/104 tasks missing from the denominator — causes are NOT uniform, and the aggregator is fail-open (not fail-closed)

Confirmed by direct filesystem enumeration: `more-Itertools`, `pyquery`, `pytest-cov`, `pythonprojecttemplate`, `pytorch-grad-cam`, `pytz`, `synthetic`.

| Task | Cause | Classification |
|---|---|---|
| `more-Itertools` | `logs/more-Itertools.log`: `KeyError: 'tar'` in `ensure_image()` | Pre-agent manifest/transport failure |
| `pytorch-grad-cam` | `logs/pytorch-grad-cam.log`: `KeyError: 'ghcr'` before task execution | Pre-agent manifest/image failure |
| `pythonprojecttemplate`, `pytz` | `OSError: [Errno 122] Disk quota exceeded` during scoring | Host storage failure |
| `pyquery` | `agent/qwen.stderr.txt`: `[ROLLOUT_TIMEOUT 2400s]`; `stream_analysis.json`: 39 events, **26 real assistant turns** before crash at driver line 618 | **Real partial work lost to a crash — counterfactual unknown, not a clean "zero"** |
| `pytest-cov` | Same shape: `[ROLLOUT_TIMEOUT 2400s]`; **49 real assistant turns** before crash | **Real partial work lost to a crash — counterfactual unknown** |
| `synthetic` | Agent itself ran `mkdir -p /workspace/{...,pyproject.toml,...}` (brace-expansion mistake, creating `pyproject.toml` as a directory); this breaks the harness's `docker cp` overlay: `cannot overwrite non-directory "/workspace/pyproject.toml" with directory "/workspace"` (`nl2repo_qwencode_driver_instruct.py:501`) | **Genuine model-caused failure; a fail-closed protocol should score this as 0, not silently drop it** |

If all 7 were mechanically inserted as 0: raw macro over 104 = 3.76%. This is denominator sensitivity only, not a fair estimate — `pyquery`/`pytest-cov` need an honest rerun rather than either a 0 or exclusion.

## Serving identity (independently confirmed, two methods, converging)

- **Claude**: direct out-of-band `curl http://100.100.104.147:30000/v1/models` from my own SSH session: `{"id":"Qwen/Qwen3-30B-A3B-Instruct-2507","owned_by":"sglang","max_model_len":262144}`. Matches self-reported `summary.json` and the harness's own live `container_probe.txt` capture.
- **Codex-pro** (stronger evidence, and correctly avoided a redundant network call on an `internet:false`-policy host): inspected the live serving process directly — `python -m sglang.launch_server --model-path .../Qwen3-30B-A3B-Instruct-2507 --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 --tp-size 2 --port 30000 --context-length 262144 --tool-call-parser qwen`, running continuously from July 11 through the July 13-14 eval window, with `/tmp/sgl_instruct.log` recording 912 POST requests from the KVM source address, all HTTP 200, no OOM/restart/traceback during the run. This is process-level + request-log evidence, stronger than a single self-reported `/v1/models` response (which does not itself guarantee `request.model` matches loaded weights).
- **Correction**: the serving engine is **SGLang, not vLLM** — any "vLLM" framing elsewhere should be corrected.
- Confirmed: **Qwen/Qwen3-30B-A3B-Instruct-2507 via SGLang**, `max_model_len=262144`. No evidence of wrong-model routing.

## Arithmetic verification (REPRO — both reviewers, exact match)

- `sum(rows[*].success_rate)/97 = 0.04028456701030928` = reported `macro_mean_success_rate` exactly; `total_passed=402/24158` exact. **The headline number was not typed independently of the underlying rows — the failure is in score provenance/evaluation validity, not elementary arithmetic.**
- Corrected macro, databases+tsfresh+stamina zeroed (both reviewers independently, matching to 15 decimal places): **`0.020144113402061858` = 2.01%**.
- Strictest corrected macro (codex-pro, +5 more implementation-independent rows): **`0.014645670103092783` = 1.46%**; corrected micro = 88/24158 = **0.36%**.
- If the 7 crashed/missing tasks are folded in as 0 (104 denominator): raw = 3.76%, strictest-corrected = 1.37% (not recommended as a capability estimate — 6 of 7 need an honest rerun rather than a mechanical zero).

## Comparison against NL2RepoBench x Coder

Located the actual calibration docs for the Coder run (`nl2repo_pathA/runs/nl2repo_merged_104/{README.md,calibration.md,TRACE.md}`, per codex-pro): **15.55%** (95 model-valid, credibility-adjusted), **14.62%** (101 valid-scored), **14.20%** (conservative, full-104 denominator); its own `databases` leak was corrected from 142/154 down to **4/154** (not fully zeroed — some residual genuine passes), and its infra failures were explicitly calibrated/disclosed. This review finds no basis to overturn that separately double-signed Coder conclusion.

However, `15.55% vs 4.03%` (or vs the corrected `2.01%`/`1.46%`) is **not an apples-to-apples comparison** as currently evidenced: the Instruct run has a far higher abnormal-termination rate (94/97 vs. the Coder run's presumably-lower, though not independently re-verified here, rate) and more identified leaks. The direction (Coder > Instruct) is plausible and consistent with each model's general reputation, but the magnitude of the gap is not reliably estimable from these two artifacts as they stand.

## Codex-pro cross-check: full disclosure

`ps aux | grep gpt-5.6-sol` at task start showed 30+ concurrent instances under the single OAuth account. I launched exactly one additional instance (`zsh -i -c 'codex-pro exec --dangerously-bypass-approvals-and-sandbox - < codex_brief_nl2repo_instruct_B.txt'`, pid 18994) and gave it a generous waiting window. **It completed successfully after ~36 minutes of continuous, real, verifiable SSH work** (confirmed via live process monitoring and a growing, substantive output log). It independently re-executed the `databases` grading pipeline from scratch (byte-identical result), inspected raw docker image layers to find a more precise leak mechanism than my own initial hypothesis, independently confirmed the `stamina` leak via the retained tar's dist-info metadata, audited every other nonzero row in the run (finding 5 more implementation-independent rows I had not personally checked), did a full 97-task census of abnormal terminations and tool-call telemetry reliability, and independently confirmed serving identity via live process inspection. **Zero contradictions were found between the two independent audits at the level of facts** — the only disagreement was the top-line REAL/FAKE label, which I have revised in this document to match codex-pro's better-supported "FAKE (as a capability claim)" framing after reviewing its complete, fully-cited reasoning. Full raw log (~10,200 lines) preserved at the review scratch path for anyone wanting the complete transcript.

## Final honest numbers

| Metric | Value |
|---|---|
| Raw macro (as claimed, 97 scored) | **4.03%** (0.04028456701030928) — arithmetic is real; claim of capability is FAKE |
| Corrected macro (databases+stamina+tsfresh -> 0, 97 denom) | **2.01%** (0.020144113402061858) — matched independently by both reviewers to 15 decimals |
| Strictest corrected macro (+5 more rows, 97 denom) | **1.46%** (0.014645670103092783) |
| Micro, raw / corrected(3) / strictest | 1.66% / 0.50% / 0.36% |
| Scored-task abnormal-termination rate | **94/97 (97%)** |
| Tool-call telemetry reliability | Broken globally: 74/97 show real tool use despite universal `tool_calls=0` |
| Serving identity | Confirmed: Qwen/Qwen3-30B-A3B-Instruct-2507 via **SGLang** (not vLLM), tp-size 2, max_model_len=262144 |
| "Fully solved" (1.0) task count | **0 genuine** (reported 1, `stamina`, is 100% image-leak) |
| Missing-task denominator | 97/104 scored; 2 of the 7 missing (`pyquery`,`pytest-cov`) had substantial real partial work lost to a crash, not clean zeros |

