# TB2.1 x Qwen3-Coder x terminus-2 (official harness) — clean rerun summary

- **Run**: `tb21_coder_t2_c32_0711211754`, 2026-07-12 on KVM Pod B (`env-kvm-57740737-bzw56`).
- **Score**: **resolved = 10 / 89**, accuracy = **mean_pass_at_1 = 0.11235955 (11.24%)**.
- **infra_fail = 0** — ran to natural completion (`tb_rc=0`, `runner_rc=0`).
- **Status**: batched-runner `attempt=complete -> run=finalized`.
- **Serving**: Qwen3-Coder-30B-A3B-Instruct @ `100.100.104.147:30001` (sglang 0.5.13, tp2, seed 484925000), IDENTITY_OK before+after.
- **Harness**: terminal-bench **0.2.18**, agent **terminus-2**, dataset **terminal-bench-2.1-yaml-full89-r7-final-20260703** (89 tasks), concurrency 32, attempts 1, temperature 0.0, timeout 7200s.

## Counts (from the run's own strict summary)

| metric | value | note |
|---|---:|---|
| total | 89 | full TB2.1 |
| clean_pass / resolved | 10 | infra_fail=0 => clean_pass == resolved |
| infra_fail | 0 | natural completion; **key clean signal** |
| external_network_marker | 12 | expected offline-attempt markers (see calibration.md) — NOT contamination |
| parse_error | 1 | `headless-terminal` ("No short test summary info found") -> counted unresolved |
| timeout / missing_artifact / cleanup_timeout_warning | 0 / 0 / 0 | |
| unresolved | 78 (batched) / 79 (tb-native folds parse_error) | |
| token_sum | input 32,807,115 / output 592,970 | |

## Resolved task ids (10)

`build-pmars`, `build-pov-ray`, `cancel-async-tasks`, `extract-elf`, `git-leak-recovery`,
`modernize-scientific-stack`, `polyglot-rust-c`, `portfolio-optimization`, `prove-plus-comm`, `pypi-server`

See `calibration.md` for caliber/anchors, `repro_closure.md` for exact repro, `verdict/` for per-task judgments.
