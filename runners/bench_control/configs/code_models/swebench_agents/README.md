# SWE-bench Agent Scaffolds

This directory keeps the SWE-bench Verified agent-scaffold configs together for the same served model:

- `scaffold_versions.yaml`: source of truth for checked GitHub tags, clean checkouts, installed runtimes, and whether a pin has passed smoke.
- `qwen3_coder_30b_a3b_instruct_swe_agent.yaml`: SWE-agent 1.1.0 scaffold.
- `qwen3_coder_30b_a3b_instruct_openhands.yaml`: OpenHands 0.54.0 CodeActAgent scaffold.
- `qwen3_coder_30b_a3b_instruct_mini_swe_agent.yaml`: mini-SWE-agent 2.3.0 scaffold, installed in an isolated venv under `shared_bench/agent_scaffolds`.
- `mini_swe_agent_swebench_qwen3_coder_30b_a3b.yaml`: mini-SWE-agent config overlay passed after the built-in `swebench.yaml`.
- Existing Qwen Code config remains at `../qwen3_coder_30b_a3b_instruct_swebench_qwen_code.yaml` because earlier result paths already reference it.

Version pinning notes:

- Qwen Code existing SWE-bench results use `@qwen-code/qwen-code==0.15.6`. A separate `0.16.2` npm root is installed as a new-run candidate, but old scores should not be reinterpreted with it.
- SWE-agent existing runtime reports `1.1.0` but comes from a dirty post-`v1.1.0` branch. Clean `v1.1.0` source is cloned; switch only after env smoke.
- OpenHands existing runtime imports `0.54.0`. Clean `0.54.0` source is cloned for current-harness reproduction, and clean `1.7.0` source is cloned as a latest-stable candidate.
- mini-SWE-agent `v2.3.0` is cloned and installed; its help command is verified, but full SWE-bench model smoke still needs to run.

Artifact contract for every run:

- The suite runner writes `config.snapshot.yaml` under the suite root.
- Each benchmark run writes its generated native config next to the logs.
- `artifact_manifest.json` points to the preserved config, command, logs, predictions, and agent trace root.
- SWE-agent traces live in the SWE-agent `trajectories` output directory and are symlinked back into the bench run dir.
- OpenHands traces live in its `output.jsonl` directory and are symlinked back into the bench run dir.
- mini-SWE-agent writes per-instance trajectory JSON files under its output directory.
