# sweml_coder_qwencode_20260710 — status

**score**: 20.80% (57/274)
**sign-off**: one endorsement; second audit in flight
**evidence gap**: ★eval_wrap ORIGINAL_LOST — 271 main rows' wrapper overwritten in-run at 10:27:03Z; MIXED_EVAL_ENVIRONMENTS
**plan**: WILL RE-RUN: single eval env, launch pin, no in-run file edits

Per the user's instruction (2026-07-11), runs with an evidence gap are **re-run clean under verdict
rules v5**, not patched after the fact — because evidence assembled after a run is exactly the kind of
after-the-fact artifact this project spent a night learning to distrust (see
`experiments/eval_wrap_integrity_20260710/`). What is committed here is what was captured cleanly at
run time; what is missing is named, not reconstructed. The authoritative numbers stay in
`docs/EXPERIMENTS.md` with status `pending`/`valid-with-caveat` until the clean re-run lands.
