# Sign-off — RepoZero × Qwen3-30B-A3B-Instruct-2507 (Path A, full 400) — Blind Reviewer B (cross-family)

**Reviewer identity:** Claude (Sonnet 5) general-purpose agent, acting as independent blind reviewer
**B**, cross-checked with a real `codex-pro` (gpt-5.6-sol, reasoning=ultra) second opinion. Honest
labeling: I am not the run author. Reviewer A (Claude, separate session) audited the same run in
parallel; I read A's signoff only AFTER completing my own independent recompute/rejudge/crash-probe
work, to check convergence, not to copy conclusions.

**Date:** 2026-07-14. **Mandate:** assume 51/400=12.75% is FAKE, attempt every falsification; declare
REAL only if it survives.

## Final verdict: **REAL** — with a MAJOR methodology caveat (matches Reviewer A almost exactly)

- As measured by the run's own actual judge (node 20, 10s/sample): **51/400 = 12.75%**. Genuine,
  unmanipulated output of a real, completed, non-resumed 400-case run. Not fabricated.
- Strict official-runtime rejudge (image-native node 18): **46/400 = 11.50%** (−1.25pp; 5 cases flip).
- Additionally strict 5s timeout (vs the 10s the run used) on top of node 18: an estimated further
  **44/400 ≈ 11.0%** (2 more genuine, non-overlapping flips), not exhaustively re-verified in
  combination by anyone across both reviews.
- 51/400 also has at least 1 undercounted case (`rsa/test5.py`, a judge-crash currently scored fail,
  recovers to a genuine 20/20 pass) partially offsetting in the other direction.
- Net: the honest range for "what this model can actually do on RepoZero Py2JS full-400 via this
  agent harness" is **≈11–13%**, not a single precise point estimate. 12.75% is real but is the
  *loosest* number in that range, not the central one.

## What I did (own independent work, before reading Reviewer A)

1. **Recompute from raw `results.jsonl`** (not `summary.json` aggregates): 400 rows, 400 unique
   cases, 0 duplicates, `all_pass==True` count = 51, `reward==1` count = 51, the two sets are
   identical, no `reward` values outside `{0,1}`. 51/400 = 0.1275 exact.
   `results.jsonl` (400 lines) ↔ `summary.json`'s embedded `results` array: 0 mismatches (own script,
   independent of Reviewer A's and codex's equivalent checks). File mtimes for both are within 0.01s
   of each other (`results.jsonl` / `summary.json` in run dir).
2. **Denominator assertion**: parsed `RepoZero/run_py2js_docker/run_all_docker.py`'s `valid_ids`
   literal (400 entries) via `ast.literal_eval` — set-equal to the run's 400 cases, 0 diff either
   direction. See `verdict/denom_assert.txt`.
3. **Independent re-judge, 5 cases** (`scripts/reviewerB_rejudge.py`), reusing the driver's own
   `start_container()`+`eval_case()` (source-read first, confirmed no leniency: both `oracle_rc==0`
   AND `js_rc==0` required, normalized-line **exact** equality, `all_pass = passed==total and
   total>0`) against the **already-generated `.mjs` on disk** — no serving/agent re-run needed,
   fully deterministic:
   - `boltons/test1.py` (60/60), `base58/test3.py` (57/57), `bidict/test12.py` (60/60): all
     re-judged **PASS**, matches committed.
   - `base58/test1.py` (4/60), `bidict/test19.py` (57/60): re-judged **FAIL**, matches committed.
     Raw evidence: `base58/test1.py` oracle stdout `b'3mJr7AoUCHxNqd'` vs agent stdout
     `b'3mJr7AoUCPu5dR'` (wrong base58 encoding — genuine bug). `bidict/test19.py`: oracle and agent
     produce the SAME key/value pairs but in **different dict order** — the judge is order-sensitive
     and correctly rejects it. This proves the judge discriminates real differences, isn't lenient.
   5/5 exact match with committed verdicts.
4. **Judge source read**: `repozero_qwencode_driver.py:354-396` (`eval_case`) and RepoZero's own
   `evaluate/eval_py2js_docker.py:46-71` (upstream reference). No LLM in the loop, no hardcoded
   reward, no substring/partial matching, no swallowed exceptions that turn a failure into a pass.
5. **8 judge-crash cases** (`results.jsonl` rows with an `error` key, "no summary.json",
   `driver_rc=1`, `cases_judged=392` not 400 — exactly `rsa/{test2,test5,test10,test11,test17,test18}`
   + `mpmath/test18` + `base58/test13`, matching the brief's known-issue list exactly). Root cause:
   `eval_case()`'s per-sample loop (`repozero_qwencode_driver.py:379-389`) does NOT catch
   `subprocess.TimeoutExpired` from `dexec_plain`; one slow sample crashes the WHOLE case's judging,
   and the orchestrator (`repozero_full400_orchestrator.py:82-83`) then synthesizes
   `all_pass=false, reward=0` — i.e. **crashes are scored as fails, which can only make 51 an
   UNDERcount, never inflate it.** I spot-checked 2 of the 8 by re-running with per-sample
   timeout-tolerant recovery (own script `reviewerB_recover_crashes.py`):
   - `rsa/test5.py`: recovers to **TRUE all_pass=True, 20/20, 0 timeouts** — the original crash was a
     transient contention artifact during the 6-worker parallel run, not a real failure. This one
     case is a genuine hidden pass currently miscounted as a fail.
   - `mpmath/test18.py`: recovers to **TRUE all_pass=False, 0/60**, with 13 genuine per-sample
     timeouts AND, on the samples that did complete, systematic precision mismatches (oracle uses
     ~30-digit arbitrary-precision output via `mpmath`; the JS translation uses native doubles,
     ~16-digit precision) — a real algorithmic bug, not recoverable to a pass at any timeout.
6. **Model identity**: `curl :30000/v1/models` → `Qwen/Qwen3-30B-A3B-Instruct-2507`;
   `curl :30000/get_model_info` → `model_path=.../Qwen3-30B-A3B-Instruct-2507`; `:30001/v1/models` →
   `Qwen/Qwen3-Coder-30B-A3B-Instruct` (the sibling Coder run's port). Cross-checked against the
   ACTUAL per-case rollout trace `cases/boltons-test1/agent/qwen.stdout.jsonl` (`"model":
   "Qwen/Qwen3-30B-A3B-Instruct-2507"` in both the `init` event and every `assistant` message) and
   `qwen_command.txt` (`--model Qwen/Qwen3-30B-A3B-Instruct-2507 --openai-base-url
   http://100.100.104.147:30000/v1`). `summary.json`'s `scope` field says "...x Coder" — confirmed
   this is a **hardcoded literal string** at `repozero_full400_orchestrator.py:108`
   (`"scope": "RepoZero_Py2JS_official_400 x qwen-code(native, in-container) x Coder"`), NOT derived
   from `args.model`; the sibling Coder run's own `summary.json` has the *identical* literal string
   (correctly, in that case) — proof this is a stale copy-paste label, not a targeted mislabel of
   THIS run. Cosmetic MINOR, not a model-identity problem.
7. **10s-vs-5s eval-timeout sensitivity** (own full check, restricted to the 51 committed passes —
   the only cases that CAN flip when tightening the timeout, per the repo's own precedent
   methodology already validated on the sibling Coder run): re-judged all 51 at 5s in parallel, found
   4 phase-1 flips, then serially re-verified each flip at both 5s and 10s (contention-free) to
   separate genuine timeout cost from parallel-worker contention artifacts:
   - **2 genuine flips** (`deepdiff/test1.py`, `networkx/test1.py`): fail serially at 5s, pass
     serially at 10s — a real >5s-per-sample cost, would fail under the official 5s harness.
   - **2 contention artifacts** (`networkx/test2.py`, `networkx/test3.py`): fail in the 6-way
     parallel phase-1 5s pass, but PASS when re-verified serially at 5s with no CPU contention — kept
     as pass.
   - Implied strict-5s headline (timeout dimension only): **49/400 = 12.25%** (own full
     spot-check restricted to the 51 passes; consistent with the sibling Coder run's own precedent:
     98/400→95/400, a similarly small ~0.75pp effect).
8. **Node18-vs-Node20 MAJOR finding — independently found the SAME issue Reviewer A found, before
   reading A's signoff**, then re-verified against A's specific case list: `container_env()`
   (`repozero_qwencode_driver.py:249`) sets the container's baked-in `PATH` to
   `{qwen_mount}/node_modules/node/bin:...` FIRST, so a bare `node` inside ANY `docker exec` into a
   container started via `start_container()` — including the JUDGE's own `eval_case()` calls —
   resolves to the qwen-mounted **node v20.20.2**, not the image's native **node v18.19.1**
   (confirmed via `docker run --rm <image> node --version` = v18.19.1, no override). This directly
   contradicts the driver's own docstring claim at line 41 ("Eval always uses the IMAGE's native
   node... for scoring fidelity"). I independently reproduced **all 5 of the 5** cases Reviewer A
   flagged (`base58/test3.py`, `base58/test6.py`, `bencoder/test3.py`, `bidict/test3.py`,
   `bidict/test5.py`) by forcing `/usr/bin/node` (confirmed = image-native v18.19.1) — **5/5 exact
   match**, every one flips from committed PASS (node20) to FAIL under strict node18
   (`SyntaxError: Named export 'x' not found` — the model's `.mjs` does
   `import { name } from './helper.js'` where `helper.js` is a plain `.js` file without
   `"type":"module"`; node 20's newer ESM/CJS auto-detection accepts this, node 18 rejects it — a
   genuine, 100%-reproducible module-resolution difference, not a flaky timing artifact). I also
   spot-checked 2 DIFFERENT, unflagged passing cases (`boltons/test4.py`, `bencoder/test8.py`) as a
   negative control — both remain PASS under node 18, confirming the effect is localized to this
   specific import pattern, not a blanket node18 incompatibility. **Strict-node18 headline: 51−5 =
   46/400 = 11.50%, matching Reviewer A's number exactly.**

## Severity-graded findings

- **BLOCKER:** none. The 51/400=12.75% headline is not fabricated: raw-row recompute, denominator
  set-equality, judge source semantics, 5/5 independent re-judge match, and full-provenance timing
  checks all hold up.
- **MAJOR — judge runs node 20, not the image's official node 18** (`repozero_qwencode_driver.py:239-249,
  381-382` vs. docstring line 41's contrary claim). 5 of 51 passes (`base58/test3.py`,
  `base58/test6.py`, `bencoder/test3.py`, `bidict/test3.py`, `bidict/test5.py`) are node-version
  artifacts that fail under the image's actual native runtime. Independently confirmed 5/5 by two
  reviewers (A and B) using two different scripts. Strict headline: 46/400=11.50%.
- **MAJOR — eval timeout is 10s, not RepoZero's own hardcoded 5s** (`repozero_qwencode_driver.py:381-383`,
  default `--eval-timeout 10` at line 548 of the orchestrator vs. `RepoZero/evaluate/eval_py2js_docker.py`
  lines 52,59 `timeout=5`). Own full spot-check of the 51 passes: 2 genuine flips
  (`deepdiff/test1.py`, `networkx/test1.py`), implied strict-5s headline 49/400=12.25%. Effect
  magnitude matches the sibling Coder run's own precedent (98→95/400, ~0.75pp), i.e. small but real
  and directionally consistent across both model runs (not cherry-picked).
- **MINOR — crash-handling conflates infra-crash with algorithmic fail.** `eval_case()` doesn't catch
  per-sample `subprocess.TimeoutExpired`; a single slow sample crashes the whole case, recorded as a
  clean fail. Effect is conservative on net (can only lower 51, not inflate it), but at least 1 case
  (`rsa/test5.py`) is a hidden genuine pass (20/20) currently miscounted as a fail — the reported
  51/400 is very slightly an UNDERcount on this axis, partially offsetting the node18/5s overcounts.
- **MINOR — `summary.json`'s `scope` field says "...x Coder"**: confirmed hardcoded literal at
  `repozero_full400_orchestrator.py:108`, present identically in the sibling Coder run's own
  `summary.json`. Every authoritative signal (`model` field, launch args, rollout trace, serving
  `/v1/models` + `/get_model_info`) independently and unanimously says Instruct-2507. Cosmetic only.
- **REPRO:** headline reproduced from raw `results.jsonl` independent of `summary.json`; denominator
  set-equality against the official `valid_ids` literal; 5/5 case re-judge match (3 pass + 2 fail,
  including a raw oracle-vs-agent stdout side-by-side); 2/8 crash-cases individually recovered and
  classified (1 hidden pass, 1 genuine fail); 5/5 independent node18-flip reproduction; 51-case-wide
  5s-timeout sensitivity sweep with contention-controlled serial re-verification; model identity
  cross-checked via serving endpoints + rollout trace on 2 different cases; run provenance (worker
  count, wall-clock/per-case-seconds ratio, launch.log sequential progress, artifact mtime spread)
  all internally consistent with a genuine, non-resumed, non-doctored 400-case run.

## Reasonableness

12.75% (Instruct-2507, general-purpose model) vs. the sibling Coder run's 24.5% (Qwen3-Coder-30B,
code-specialized, same harness/image/judge) is a plausible ~2x gap for a demanding agentic
Python→JS translation benchmark — consistent with the expected ordering
Claude-4.6-Sonnet-anchor(54.7%) > Coder-30B(24.5%) > Instruct-30B(12.75%), i.e. frontier closed model
> code-specialized open model > general-purpose open model of the same parameter count. Not a
suspiciously round or out-of-band number.

## codex-pro second opinion — disclosed honestly

I dispatched a real local `codex-pro` (`zsh -i -c 'codex-pro exec --dangerously-bypass-approvals-and-sandbox
- < brief'`, model `gpt-5.6-sol`, `reasoning.effort=ultra`), single instance, ran to completion (not
killed, not timed out — process exited cleanly on its own after ~29 minutes,
`session id: 019f5db2-472c-7903-a6db-0261a5b2514a`). At launch time `ps aux | grep gpt-5.6-sol`
showed **12 already-running** `gpt-5.6-sol` sessions (mostly idle `resume`/interactive panes from
other work, not necessarily concurrent active requests) — above this task's own "give it a
reasonable window" threshold of 6, so I gave it a long runway rather than fail closed. ~60% of its
wall-clock time was spent reading unrelated project skill/workflow documentation
(`WORKFLOW.md`, `cc-dev-tools` SKILL.md, cmux adversarial-agent docs) triggered by its own "codex"
skill's onboarding protocol before it ever touched `results.jsonl` — a real inefficiency of the
environment's auto-skill-triggering, not a sign of the run being stuck. Once it reached the actual
task it did substantive, genuinely independent work: recomputed 400/51/392-judged exactly matching
mine; cross-checked ALL 400 rows against BOTH `run_root/summary.json` AND
`run_root/agent/judge.result.json` (a check I had not done at that granularity) with **0
mismatches**; re-implemented the oracle-vs-`.mjs` docker-exec comparison FROM SCRATCH (not reusing
the driver module) on 3 different cases than mine (`rsa/test16.py`, `networkx/test1.py`,
`canonicaljson/test20.py`), matching committed verdicts; independently found and flagged the SAME
node18/node20 MAJOR issue (though its own 5-case spot-check happened to miss the specific flip cases
and it correctly caveated non-exhaustiveness); confirmed model identity via the underlying sglang
serving log's real inference timestamps during the run window, not just `/v1/models`. Its own
verdict: **REAL** — "51/400 is the genuine recorded score of this custom 10-second/Node-20 Path-A
run; the stronger characterization as a deterministic, blind, official-runtime score is false" — this
matches my own conclusion almost word for word, reached independently. **My verdict above is based on
my own reproduced evidence (recompute, 5-case rejudge, 2 crash-case recoveries, 5-case node18
reproduction, 51-case 5s-timeout sweep, denominator assertion), not on trusting codex's output**;
codex served as a corroborating, genuinely independent second signal that converged on the same
number and the same caveat.

## Evidence bundle (this branch)

`results.jsonl`, `summary.json`, `launch.log`, `serving/` (fresh `/v1/models` + `get_model_info` for
both :30000 and :30001), `scripts/` (my 6 independent scripts + the driver/orchestrator source I
read), `verdict/` (`denom_assert.txt`, `node18_flip_evidence_B.txt`, and 3 JSON result files:
`reviewerB_rejudge5.json`, `reviewerB_crash_recovery.json`, `reviewerB_5s_check.json`).

— Reviewer B (Claude Sonnet 5, cross-checked with codex-pro gpt-5.6-sol ultra)
