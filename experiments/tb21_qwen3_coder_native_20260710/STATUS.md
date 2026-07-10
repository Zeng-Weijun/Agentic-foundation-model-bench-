# tb21_qwen3_coder_native_20260710 — status

**score**: 11.24% (10/89)
**sign-off**: dual-signed CERT_A: all 6 CONFIRMED
**evidence gap**: serving/ not yet packaged (on disk under control/), trace index pending
**plan**: clean evidence complete on disk; will re-pack, and re-run under v5 for a launch-time serving pin

Per the user's instruction (2026-07-11), runs with an evidence gap are **re-run clean under verdict
rules v5**, not patched after the fact — because evidence assembled after a run is exactly the kind of
after-the-fact artifact this project spent a night learning to distrust (see
`experiments/eval_wrap_integrity_20260710/`). What is committed here is what was captured cleanly at
run time; what is missing is named, not reconstructed. The authoritative numbers stay in
`docs/EXPERIMENTS.md` with status `pending`/`valid-with-caveat` until the clean re-run lands.
