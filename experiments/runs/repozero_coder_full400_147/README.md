# RepoZero Py2JS full400 x Qwen3-Coder-30B-A3B-Instruct x qwen-code (Path A) -- v6 evidence bundle

**Result: 98 / 400 = 24.5% all_pass.** (RepoZero Py2JS OFFICIAL 400, single base
image `repoarena-new`; agent = `qwen-code` native CLI driving `:30001` Coder; judge = RepoZero
official `eval_case`, oracle-executable stdout vs generated `node .mjs` stdout, all samples must match.)

## One-line reading
Same official judge for every case: **agent `.mjs` stdout must equal the oracle across all
testcase samples**; that holds for **98 / 400** cases. Denominator is **400, not shrunk** --
the 4 judge-step crash cases were re-judged serving-free and confirmed **genuine fails (0/4 recovered)**.

## Anchor (band only)
RepoZero arXiv anchor **54.70% +- 2.55 = Mini-SWE-Agent + Claude-4.6-Sonnet**. This run swaps
**both** the scaffold (qwen-code) **and** the model (open 30B Coder), so it is a NEW measurement
with no official cell -- 54.70% is a coarse sanity band, **not** an aligned comparison. See `calibration.md`.

## Contents
- `results.jsonl` -- 400 per-case rows (all_pass, reward, passed/total, entry_exists, agent_rc, turns, seconds). RAW run record.
- `summary.json` -- run aggregate (cases_total=400, cases_all_pass=98, all_pass_rate=0.2450, cases_judged=396) + sorted results.
- `denom_assert.txt` -- denominator integrity (400, unique, 98+302=400, 396 judged + 4 crash=400) + the re-judge proof.
- `rejudge_missing4.json` -- serving-free re-judge of the 4 crash cases -> 0/4 recovered passes (genuine fails).
- `by_lang.md` -- per-library all_pass breakdown.
- `calibration.md` -- what 24.5% means, denominator integrity, crash-case proof, anchor caveat, harness caveat.
- `serving/` -- serving identity (`:30001` Coder): `get_model_info_after.json`, `get_server_info_after.json`, `v1_models_after.json`, `chat_probe_after.json`, `repoarena_image_inspect.json`, `identity_summary.md`.
- `repro_closure.json` -- image ref + Id + tar sha256, rz_root, scaffold, judge rule, serving identity, eval_timeout.
- `verdict/per_task_verdict.tsv` -- 400-row condensed verdict table (+ note column flags the 4 re-judged crash cases).
- `verdict/samples/` -- 5 worked examples (pass / partial-fail / clean-fail / re-judged / oracle-timeout) with the qwen `:30001` trajectory, the generated `.mjs`, and the official `judge.result.json` (oracle-vs-node diff) -- independently re-judgeable.
- `verdict_pack.tar.gz` -- packed copy of `verdict/` (portable evidence archive).
- `scripts/` -- orchestrator, driver (contains the official `eval_case` judge), and the re-judge script.
- `launch.sh`, `launch.console.log` -- exact launcher (serving preflight = before-identity gate) + full progress log.
- `TRACE.md` -- where the full 400-case recordings live + how to independently re-judge.
- `SHA256SUMS` -- checksums of every file above.
