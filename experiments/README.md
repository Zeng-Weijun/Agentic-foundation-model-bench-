# `experiments/` — the artifacts behind each quoted score

> **Status: HISTORICAL ARTIFACT INDEX.** Bundles below may contain signed, reviewed, or unsigned historical evidence. Appearance in this index does not make a result current; consult the explicit per-run status notice, and do not quote a score as current unless it satisfies the relay-backed `gpt-5.5` + `medium` publication contract.

One directory per run. Everything here is either the exact file that ran, or a hash by which the file
that ran can be checked.

## What each run directory holds

| File | What it is |
|---|---|
| `launch_full500.sh` | the script that ran, verbatim — not a reconstruction |
| `runner_config.json` | the resolved runtime configuration |
| `ledger_summary.json` | counts + `sha256(results.jsonl)` |
| `serving/get_model_info_{before,after}.json` | which weights answered, captured at both ends of the run |
| `serving/get_server_info_{before,after}.json` | 402 server arguments; `api_key`/`admin_api_key` redacted **before** they touched disk |
| `SHA256SUMS` | digests of the log, the launch env, the serving captures, and `results.jsonl` |
| `traces/trace_index.tsv` | `instance_id → sha256 → bytes` for every agent trace |
| `traces/sample_*.stdout.jsonl` | one representative trace, truncated |
| `signoff_A.md`, `signoff_B.md` | two adversarial audits, written blind to each other |

## Traces are not in this repo

They are 347 MB for a single run. `traces/trace_index.tsv` gives a `sha256` per instance; the traces
live on shared storage under the run root recorded in the run card. **The index is the contract**: if
a trace on disk does not hash to its row, the score in this repo is not the score that run produced.

## `serving/` is missing from one run, and that is the point

`swev_qwen3_coder_qwencode_20260710/` has no `serving/` directory. That run executed **before**
`serving_config` became a mandatory field (§0, field 11), so nothing captured the serving stack while
it was running.

Its model identity was established afterwards, from the live process — `PID 673`,
`--model-path .../Qwen3-Coder-30B-A3B-Instruct --tool-call-parser qwen3_coder`, started
`2026-07-09T08:24 UTC`, spanning the whole run window — and from `/get_model_info` on the endpoint it
used. That is good evidence. It is also evidence that happened to survive: had the server been
restarted before anyone thought to look, nothing on disk would have said which weights produced
`48.4%`.

The run that came a few hours later, `swev_instruct2507_qwencode_20260710/`, captures it four ways at
both ends. **The gap between those two directories is the whole argument for field 11.**

## Reading the numbers

Each `ledger_summary.json` reports `rows`, not the benchmark size. They differ:

```
Coder     rows 496   resolved 240      →  242/500 = 48.4%
Instruct  rows 498   resolved 107      →  108/500 = 21.6%
```

Instances whose tests finished and then hit a container-cleanup race are dropped from
`results.jsonl` entirely rather than recorded as unresolved
(`full500_qwencode_orchestrator_v21.py:912-921` calls `preserve_failure` and `append_event`, never
`append_score`). Three of the six dropped across these two runs were **genuinely resolved**, recovered
from their `report.json`.

**Never divide by `rows`.** The denominator is the dataset. `240/496 = 48.39%` is a correct-looking
number attached to the wrong denominator, and it sits 0.01 pt from the honest `242/500 = 48.4%` —
which is why nothing in the pipeline objects to it.

## Serving

`serving/sglang_launch_20260710.sh` is the launch command for both endpoints, captured verbatim from
`ps -eo args`. Read its header before pointing anything at those ports: **sglang does not validate the
`model` field.** Ask the port serving Instruct-2507 for the Coder model and it returns `200`, runs
Instruct-2507, and echoes the Coder name back to you. Only `model_path` from `/get_model_info`
identifies the weights.
