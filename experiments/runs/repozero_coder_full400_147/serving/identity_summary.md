# Serving identity -- the model that produced these rollouts

The RepoZero agent phase drove **`:30001`** (base_url `http://100.100.104.147:30001/v1`,
recorded in `summary.json` and `launch.console.log`). Probed identity (post-run):

| field | value |
|---|---|
| served_model_name | `Qwen/Qwen3-Coder-30B-A3B-Instruct` |
| model_path | `/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct` |
| model_type | `qwen3_moe` |
| architectures | `['Qwen3MoeForCausalLM']` |
| is_generation | `True` |
| sglang version | `0.5.13` |

**Live chat probe** (`serving/chat_probe_after.json`): request model
`Qwen/Qwen3-Coder-30B-A3B-Instruct` -> response `model="Qwen/Qwen3-Coder-30B-A3B-Instruct"`,
content=`"pong"`.

- **Before**: `launch.sh` preflight hard-gated the run -- it `curl`ed `{base}/models`
  and aborted unless the served list contained `Qwen3-Coder` (see `launch.console.log`
  `[preflight][OK] ... serving Coder`). So the run provably started against Coder.
- **After**: the get_model_info / get_server_info / chat probes above (this bundle) confirm
  the SAME weights (`.../models/Qwen3-Coder-30B-A3B-Instruct`, qwen3_moe) are still served.
- The orchestrator did not snapshot a separate before/after JSON per case; identity is
  established by the preflight gate (before) + these probes (after). Raw probes:
  `get_model_info_after.json`, `get_server_info_after.json`, `v1_models_after.json`, `chat_probe_after.json`.
