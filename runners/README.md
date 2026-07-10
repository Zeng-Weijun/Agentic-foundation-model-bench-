# `runners/` — an archive, not an execution path

Every file here was **untracked** when it was copied in. Not ignored — untracked, in a directory that
is not a git repository at all:

```
$ git -C /data/nips/bench rev-parse
fatal: not a git repository
$ git ls-files paper_reading/bench | wc -l
0
```

Thirty-seven `run_*.sh`, the `configs/` that pin every model's serving parameters, `profiles/`,
`lib/`, and `tools_repozero_codex_full.py` — the only copy of it anywhere on disk. A single overwrite
and none of them could be recovered, because there is no object to recover them from.

That is not hypothetical. **The runner that produced this repository's canonical Terminal-Bench 2.1
score of 70.8% died exactly this way**: untracked, overwritten by a later patch, no git object, gone.
The score survives in `docs/EXPERIMENTS.md`. The thing that produced it does not. See §6 C1.

## Do not run these

Copying a script is not copying its behaviour. Several of these anchor their paths with
`Path(__file__).resolve().parents[N]` or derive `$REPO_ROOT` from their own location. Executed from
here, they resolve to different directories, silently pick up different inputs, and — in the case
already documented in §5.9 — flip a quality gate's verdict from `closed` to `open` without an error.

**The execution copy stays on shared storage.** These are archive copies. `SHA256SUMS` is what makes
them useful: hash the file on shared storage and compare. If it differs, the thing that ran is not the
thing recorded here, and you have found a drift before it becomes a mystery.

```
shasum -a 256 /data/nips/bench/run_tau3_bench.sh
grep run_tau3_bench.sh SHA256SUMS
```

## What is here

| Path | What |
|---|---|
| `bench_control/run_*.sh` | 37 runners, including the six for benches not yet reproduced: `run_deepswe.sh`, `run_nl2repo.sh`, `run_tau3_bench.sh`, `run_repozero_py2js.sh`, `run_programbench_metadata_smoke.sh`, `run_mcp_atlas_metadata_smoke.sh` |
| `bench_control/configs/code_models/*.yaml` | per-model serving + scaffold pins. `qwen3_coder_30b_a3b_instruct_qwen_code.yaml` records `--context-length 262144`, `--tool-call-parser qwen3_coder`, `--tp-size 2`, and `previous_stable_context_length: 65536` |
| `bench_control/profiles/*.env` | endpoint/model profiles |
| `bench_control/lib/`, `model.env.example` | shared shell helpers, env template |
| `repozero/tools_repozero_codex_full.py` | the only copy on disk, `mtime 2026-05-20` |

No secrets: scanned by value (not by key name) on both the source host and locally before commit —
`sk-*`, bearer tokens, JWTs, HF tokens, and assigned `api_key=` literals. 60 files, 0 findings. The
`api_key` values that do appear are `EMPTY` (self-hosted sglang does not authenticate) or shell
variable references.

## The rule this exists to enforce

A score is not reproducible because someone wrote it down. It is reproducible because the script that
produced it can be found, and can be shown to be the script that produced it. Field 10 of §0
(`script_digests`) exists because that was not true here, and this directory is the first payment
against that debt.
