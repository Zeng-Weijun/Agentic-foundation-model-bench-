# RepoZero × Qwen3-30B-A3B-Instruct-2507 (Path A, full 400) — Blind Reviewer A Calibration

**Reviewer:** Claude (Anthropic) general-purpose agent, independent blind sign-off **A** (honest labeling; not the run author).
**Date:** 2026-07-14 UTC.
**Mandate:** assume the score is FAKE; try every falsification; declare REAL only if it survives.
**Verdict:** **REAL** (headline could not be falsified) — with one MAJOR harness-fidelity caveat (node version, below).

---

## Headline
- **all_pass = 51 / 400 = 12.75%** — RepoZero Py2JS official 400, per-sample eval timeout 10s, judged on the run's own `node` (= mounted qwen **node v20.20.2**; see MAJOR finding).
- Judged-only denominator: 51 / 392 = **13.01%** (392 = 400 − 8 judge-crashes).
- **Strict official RepoZero image node 18: 46 / 400 = 11.50%** (5 all_pass cases rely on node-20 leniency — see MAJOR finding).
- Anchor (context only, NOT an official-cell match): **54.70% ±2.55** Mini-SWE-Agent + Claude-4.6-Sonnet. The orchestrator itself labels this a NEW measurement / ruler+sanity band (different scaffold + model).

## Independent reproduction (reviewer A, did NOT trust summary.json aggregates)
- Recomputed from raw `results.jsonl`: 400 rows, **400 unique cases** (no dup/missing), all_pass==true = **51**, reward==1 = **51**, {all_pass set}=={reward set}, all rewards ∈ {0,1}, 51/400 = 0.1275 EXACT.
- **Denominator set-equality:** run's 400 == official `valid_ids` (400 unique) exactly, 0 diff. `excluded_ids=[pyaes,yaml,idna,markdown]` are **INCLUDED** in the 400 (they score ~0%), i.e. the *harder/conservative* denominator (excluding them → 51/324 = 15.7%).
- **Independent re-judge** (my own harness, official image, oracle-stdout vs node-stdout normalized-line equality) on 12 cases (8 all_pass + 4 fail): **12/12 agree** with results.jsonl once the judging node is matched (see below). Fail cases confirmed fail (bech32/test1 missing entry 0/20; base58/test1 4/60; idna/test1 0/50; yaml/test1 7/60), pass cases confirmed pass (whoosh/schedule/fractions/boltons/networkx/rsa/bidict full).
- Inspected generated `.mjs`: genuine from-scratch reimplementations (e.g. base58 = Bitcoin-alphabet big-int encoder), no oracle call / no external-lib import. 60/60 cannot be whitebox-overfit — the agent sees only 4 whitebox examples but the judge runs up to 60 hidden-arg samples.

## Judge is deterministic (no LLM)
RepoZero official `eval_case` (mirrored in the driver): per hidden testcase sample, run the compiled Python **oracle executable** and `node <entry>.mjs` in-container, compare `normalized_lines(oracle_stdout) == normalized_lines(node_stdout)` with both rc==0; `all_pass = passed==len(samples) and len(samples)>0`; `reward = int(all_pass)`. `normalized_lines` = whitespace-collapsed, blank-line-stripped per-line list. Orchestrator aggregates `sum(all_pass)/400` with no post-hoc edit. No serving involved.

## MAJOR finding — judging node version (harness fidelity)
The Path A judge executes generated JS on the **mounted qwen node v20.20.2** (the container's default PATH prepends `/opt/qwen-native/.npm-root/node_modules/node/bin`), **NOT** the RepoZero image's official **node v18.19.1** (`/usr/bin/node`) — even though the driver docstring claims "Eval always uses the IMAGE's native node for scoring fidelity." Verified in-container: bare `node` → v20.20.2; `/usr/bin/node` → v18.19.1.
Node 20's auto-detect-module accepts a `.mjs` that imports a `.js` helper using ESM `export` syntax; node 18 rejects it (`SyntaxError: Named export not found` / "set type:module or use .mjs"). **5 of the 51 all_pass cases** depend on this leniency, and **all 5 fail under strict node 18** (re-judged, 0 passed each):
`base58/test3, base58/test6, bencoder/test3, bidict/test3, bidict/test5`.
→ run's-node-20 headline **12.75% (51/400)**; strict-official-node-18 headline **11.50% (46/400)**. The 12.75% is REAL as the run's own measurement, but carries **+1.25pp node-version leniency** vs the official RepoZero (node-18) harness. Recommendation: report as node-20 with this caveat, or re-run the judge under `/usr/bin/node` (node 18).

## Scope-label note (MINOR)
`summary.json` `scope` = "...x qwen-code(native, in-container) **x Coder**" is a **stale hardcoded template literal** (`repozero_full400_orchestrator.py:108`, `assemble_docs.py:61`, both written for the earlier Coder run). Actual model = **Qwen3-30B-A3B-Instruct-2507**, triple-confirmed:
1. `summary.json` `model` = `Qwen/Qwen3-30B-A3B-Instruct-2507` (= orchestrator `args.model`).
2. serving `:30000/get_model_info` → `model_path=.../Qwen3-30B-A3B-Instruct-2507`; `/v1/models` id = `Qwen/Qwen3-30B-A3B-Instruct-2507`. (`:30001` is the separate Coder endpoint.)
3. per-case rollout `agent/qwen_command.txt` → `--openai-base-url http://100.100.104.147:30000/v1 --model Qwen/Qwen3-30B-A3B-Instruct-2507`.

## 8 judge-crashes ("no summary.json")
`rsa/test{5,11,18,2,17,10}` + `mpmath/test18` + `base58/test13`. Each is a `subprocess.TimeoutExpired after 10s` on a `docker exec` — oracle side (RSA keygen `--bits 3178/4728/2048` itself >10s) or node side hang — uncaught by eval_case → driver_rc=1 → orchestrator records `error:"no summary.json"`, reward=0. Counted as **fail = conservative** (can only lower the headline). RSA oracle-side timeouts are not cheaply recoverable (the reference itself exceeds 10s). MINOR: eval_case should catch TimeoutExpired and score the sample as a fail rather than crash the case.

## Denominator / state breakdown (recomputed)
- all_pass (reward=1): **51**
- entry_exists==false (no `.mjs` produced): **23**
- agent timed_out==true: **35**
- judge-crash (total==0): **8**
- (remainder = entry present but stdout mismatch)
- 51 all_pass + 349 fail = 400 ✓ ; 392 judged + 8 crash = 400 ✓

## 10s vs 5s timeout
Driver/orchestrator used `--eval-timeout 10` (argparse help notes "official is 5s"). Looser budget → can only help the agent. In my 8 sampled all_pass cases, per-sample max latency was ≤0.96s except **networkx/test1** (one sample 5.07s) which is the only sampled case that would flip true→false at a strict 5s cut. Effect is small (cf. sibling Coder run 24.5%@10s → 23.75%@5s). A full 5s re-judge of all 51 would tighten the exact number.

## By-package all_pass (sanity)
High: whoosh 9/18, schedule 8/17, fractions 6/18 (clean algorithmic reimplementation). Zero/low: crypto/bignum (rsa 1/11, mpmath 0/19, pbkdf2 0/12, pyaes 0/17, bech32 0/17) and yaml 0/19, markdown 0/20, idna 0/20 — technically explicable (arbitrary-precision / digest-sensitive / large-grammar tasks are hard to re-implement in JS). Direction vs Coder (24.5%) is correct: general Instruct < code-specialized Coder.

## Verdict
**REAL.** 51/400 = 12.75% is the genuine, deterministic, independently-reproduced output of the run's judge; identity, denominator, judge logic, and a 12/12 sample of verdicts all check out; the 8 crashes and the included excluded-packages are conservative. **Caveat (MAJOR):** the judge ran on node 20, not the official RepoZero node 18; the strict-official value is **11.50% (46/400)**, a −1.25pp correction from node-version leniency on 5 `.js`-helper cases.
