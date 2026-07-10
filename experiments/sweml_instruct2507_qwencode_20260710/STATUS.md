# sweml_instruct2507_qwencode_20260710 — status

**score**: 8.03% (22/274)
**sign-off**: one endorsement; second audit in flight
**evidence gap**: serving_identity_after = UNVERIFIABLE (sglang shut down 14 min after last row)
**plan**: WILL RE-RUN: capture after-identity before serving teardown

Per the user's instruction (2026-07-11), runs with an evidence gap are **re-run clean under verdict
rules v5**, not patched after the fact — because evidence assembled after a run is exactly the kind of
after-the-fact artifact this project spent a night learning to distrust (see
`experiments/eval_wrap_integrity_20260710/`). What is committed here is what was captured cleanly at
run time; what is missing is named, not reconstructed. The authoritative numbers stay in
`docs/EXPERIMENTS.md` with status `pending`/`valid-with-caveat` until the clean re-run lands.
