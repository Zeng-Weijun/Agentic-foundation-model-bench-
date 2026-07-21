# GPT Relay Score Purge — 2026-07-21

## Scope

This record removes locally produced GPT/relay score publications for exactly
these benchmark families:

- DeepSWE
- SWE-bench Multilingual
- NL2Repo
- RepoZero
- SWE-bench Verified

The purge is independent of whether an old result was signed, dual-signed,
called canonical, or described as a failed/partial run. No old score value is
carried forward in this record.

Excluded from the purge:

- Qwen-native scores, traces, scripts, YAML, and stamp/certificate files remain;
  mixed Qwen prose is retained but its local GPT comparator scores are redacted;
- all Terminal-Bench result artifacts;
- public leaderboard and paper anchors;
- generic GPT runner, profile, model, and dry-run configuration;
- gold, oracle, transport, image, and no-model evidence;
- raw traces on shared storage, which remain private debugging evidence and are
  not current score publications.

## Base revision

The correction was prepared from:

`11d95d595f0ccec014ff1d9a4617e1b7f4eacb99`

## Deleted tracked result publications

The object IDs below identify the exact pre-delete Git blobs without repeating
their score contents.

| Path | Pre-delete blob |
|---|---|
| `reports/scores/repozero_gpt55_optionb_188_v2_20260706.results.jsonl` | `df3f9dba3f5aef7ba5b59a4b076f3d5134008063` |
| `reports/scores/repozero_gpt55_optionb_188_v2_20260706.scores.json` | `535a306913deb9a0988268e19dbe8aaedc87f4aa` |
| `reports/scores/repozero_gpt55_optionb_188_v2_20260706.summary.json` | `c28c22eff92d56c638997b9ca2e774a127ef852a` |
| `reports/scores/repozero_v2_final_20260706.md` | `0c60a6950926427c249fc2dd70d68e114619a9e9` |
| `reports/scores/swemultilingual_gpt55_dual_number_20260707.md` | `c144f5dd07e317f24b99332ca6e1ff70e9458a0e` |
| `reports/scores/swev_v2.1_final_score_20260705.md` | `4657ed3fd2199fd8ff0bb94976ef7d67d0b77d71` |
| `reports/full500_midrun_audit_20260704.md` | `d52dc6a2bd7ae395e71e4d2c3d4173a5bc73e48c` |
| `_coordination/20260625_harbor_bench/reports/swev_full500_monitor_surface51_20260703.md` | `bcf84b560f083b9daf4b9e859a7beb2f14ba73ad` |

NL2Repo had no tracked local GPT score/result publication in the audited tree.
DeepSWE had no standalone score file; its former local GPT counters and outcome
excerpt were removed from mixed landscape/parser documents.

## Mixed publication surfaces redacted

The following mixed files retain non-GPT, Qwen, Terminal-Bench, public-anchor,
or infrastructure content while no longer publishing the five-target local GPT
scores:

- `_coordination/20260625_harbor_bench/BENCH_STATUS.md`
- `_coordination/20260625_harbor_bench/lanes/hunt-runner-results.md`
- `_coordination/bench_kvm_e2e_20260704/DECISIONS.md`
- `docs/EXPERIMENTS.md`
- `experiments/runs/sweml_coder_full300_147/calibration.md`
- `experiments/runs/sweml_instruct2507_full300_147/calibration.md`
- `experiments/sweml_coder_qwencode_20260710/signoff/CERT_A_MULTILINGUAL.md`
- `experiments/sweml_coder_qwencode_20260710/signoff/CERT_B_MULTILINGUAL.md`
- `experiments/sweml_instruct2507_qwencode_20260710/signoff/CERT_A_MULTILINGUAL.md`
- `experiments/sweml_instruct2507_qwencode_20260710/signoff/CERT_B_MULTILINGUAL.md`
- `reports/agentic_bench_landscape_20260625.md`
- `reports/agentic_bench_matrix_20260625.csv`
- `reports/all_bench_offline_gap_matrix_20260625.md`
- `reports/daily_digest_20260703.md`
- `reports/next_result_parser_contract_20260625.md`
- `reports/pending_adapter_inventory_20260625.md`
- `reports/progress/CAMPAIGN_20260704_bench_kvm_e2e.md`
- `reports/repozero_official_protocol_launch_spec_20260704.md`
- `reports/repozero_suite_execute_preflight_smoke_20260625.md`
- `reports/scores/QWEN3_CODER_30BA3B_CANONICAL_20260706.md`

## Qwen preservation guard and narrow exceptions

These tree IDs were captured from the base revision as audit baselines:

| Path | Base tree |
|---|---|
| `experiments/runs/deepswe_coder_pathA_147` | `cc91dd5bb5c84fff23dabaf4ae2e68d6c89826c8` |
| `experiments/runs/nl2repo_coder_full104_147` | `b7259bfd993bc091ec9c218fa48562496b15a84a` |
| `experiments/runs/repozero_coder_full400_147` | `3a764c4d9ac0289d68ca9b5ad9ace9757c6f19a8` |
| `experiments/runs/sweml_coder_full300_147` | `803f9a590bfad192caac59303b8ef9b5d73e89f5` |
| `experiments/runs/sweml_instruct2507_full300_147` | `353031ee643e6e727b35d97b98f9b735cfb21c52` |
| `experiments/runs/swev_coder_full500_v5_147` | `765b5df4a08ed75a3fb06a8492375e436566e80d` |

Only the two named Multilingual `calibration.md` files inside these six trees
were changed, and only to remove local GPT comparator prose. The four named
Multilingual certificate files and the Qwen canonical score card were retained
in place with their Qwen scores and verdicts intact; only their local GPT
comparator rows or values were redacted. All other files under the six core
Qwen trees remain byte-identical to the base revision.

## Publication rule after purge

The current formal local GPT score count for the five target benchmark families
is zero. A future score may be published only from a new formal run that satisfies
the repository's then-current evidence and sealing contract. This commit does not
rewrite Git history; it removes the score publications from the current tree and
leaves the deletion itself auditable.
