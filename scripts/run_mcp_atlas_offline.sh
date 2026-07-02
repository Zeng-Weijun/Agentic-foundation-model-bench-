#!/usr/bin/env bash
set -euo pipefail

MODE="${MCP_ATLAS_MODE:-smoke}"
TASK_LIMIT="${MCP_ATLAS_TASK_LIMIT:-5}"
SERVER_PROFILE="${MCP_ATLAS_SERVER_PROFILE:-local_replay_smoke}"
DATASET="${MCP_ATLAS_DATASET:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/datasets/ScaleAI-MCP-Atlas/MCP-Atlas.parquet}"
OUTPUT_DIR="${MCP_ATLAS_OUTPUT_DIR:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/runs/mcp_atlas_smoke_$(date -u +%Y%m%dT%H%M%SZ)}"
IMAGE_MANIFEST="${MCP_ATLAS_IMAGE_MANIFEST:-manifests/images/mcp_atlas.yaml}"
AGENT_MODEL="${MCP_ATLAS_AGENT_MODEL:-${MODEL:-}}"
JUDGE_MODEL="${MCP_ATLAS_JUDGE_MODEL:-${EVAL_LLM_MODEL:-}}"
AGENT_BASE_URL="${MCP_ATLAS_AGENT_BASE_URL:-${LLM_BASE_URL:-${OPENAI_BASE_URL:-}}}"
JUDGE_BASE_URL="${MCP_ATLAS_JUDGE_BASE_URL:-${EVAL_LLM_BASE_URL:-${OPENAI_BASE_URL:-}}}"
DOCKER_HOST_VALUE="${DOCKER_HOST:-}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/run_mcp_atlas_offline.sh [--dry-run] [--mode smoke|full500] [--task-limit N] [--server-profile local_replay_smoke]

Fail-closed MCP-Atlas local/replay smoke runner skeleton. The smoke profile is
for <=5 tasks and is not a full500 claim. Agent and judge model paths are
separate and must route through an approved relay. Non-dry-run is disabled until
runtime image transport, dataset snapshot, replay fixtures, runner env, and
strict parser proof exist.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --mode)
      MODE="${2:?missing value for --mode}"
      shift 2
      ;;
    --task-limit)
      TASK_LIMIT="${2:?missing value for --task-limit}"
      shift 2
      ;;
    --server-profile)
      SERVER_PROFILE="${2:?missing value for --server-profile}"
      shift 2
      ;;
    --dataset)
      DATASET="${2:?missing value for --dataset}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

case "$MODE" in
  smoke|full500) ;;
  *) echo "unsupported MCP-Atlas mode: $MODE" >&2; exit 64 ;;
esac
if ! [[ "$TASK_LIMIT" =~ ^[0-9]+$ ]] || [[ "$TASK_LIMIT" -lt 1 ]]; then
  echo "MCP_ATLAS_TASK_LIMIT must be a positive integer" >&2
  exit 64
fi
if [[ "$MODE" == "smoke" && "$TASK_LIMIT" -gt 5 ]]; then
  echo "MCP-Atlas smoke task limit must be <=5" >&2
  exit 64
fi

case "$SERVER_PROFILE" in
  local_replay_smoke)
    ENABLED_SERVERS=(calculator filesystem memory git mcp-code-executor)
    EXTERNAL_SERVICE_PROFILE="replay"
    ;;
  *)
    ENABLED_SERVERS=()
    EXTERNAL_SERVICE_PROFILE="unknown"
    ;;
esac

DATASET_EXISTS=0
VFS_DOCKER_HOST=0
if [[ -f "$DATASET" ]]; then DATASET_EXISTS=1; fi
if [[ "$DOCKER_HOST_VALUE" == unix:///tmp/rl-vfs/run/docker-shim.sock ]]; then VFS_DOCKER_HOST=1; fi
SELECTED_TASK_IDS=(replay_calculator_claim_001 replay_filesystem_claim_002 replay_memory_claim_003 replay_git_claim_004 replay_code_claim_005)
SELECTED_TASK_IDS=("${SELECTED_TASK_IDS[@]:0:$TASK_LIMIT}")
FULL_BLOCKERS=(full500_external_service_closure_missing runtime_image_transport_missing dataset_snapshot_missing completion_eval_runner_env_missing replay_fixture_coverage_missing)

if [[ "$DRY_RUN" == "1" ]]; then
  python3 - <<'MCP_ATLAS_RUNNER_JSON' "$MODE" "$TASK_LIMIT" "$SERVER_PROFILE" "$EXTERNAL_SERVICE_PROFILE" "$DATASET" "$DATASET_EXISTS" "$OUTPUT_DIR" "$IMAGE_MANIFEST" "$AGENT_MODEL" "$JUDGE_MODEL" "$AGENT_BASE_URL" "$JUDGE_BASE_URL" "$DOCKER_HOST_VALUE" "$VFS_DOCKER_HOST" "${ENABLED_SERVERS[*]}" "${FULL_BLOCKERS[*]}" "${SELECTED_TASK_IDS[*]}"
import json, sys
(mode, task_limit, server_profile, external_service_profile, dataset, dataset_exists,
 output_dir, image_manifest, agent_model, judge_model, agent_base_url, judge_base_url,
 docker_host, vfs_docker_host, enabled_servers, full_blockers, selected_task_ids) = sys.argv[1:]
servers = [s for s in enabled_servers.split() if s]
blockers = [s for s in full_blockers.split() if s]
task_ids = [s for s in selected_task_ids.split() if s]
print(json.dumps({
    "status": "dry_run",
    "bench_id": "mcp_atlas",
    "mode": mode,
    "task_limit": int(task_limit),
    "selected_task_ids": task_ids,
    "server_profile": server_profile,
    "external_service_profile": external_service_profile,
    "enabled_servers": servers,
    "dataset": dataset,
    "dataset_exists": dataset_exists == "1",
    "output_dir": output_dir,
    "image_manifest": image_manifest,
    "agent_model": agent_model,
    "judge_model": judge_model,
    "agent_base_url": agent_base_url,
    "judge_base_url": judge_base_url,
    "docker_host": docker_host,
    "vfs_docker_host": vfs_docker_host == "1",
    "full_score_valid": False,
    "planned_agent_environment_command": ["docker", "run", "--network", "none", "--env", "ENABLED_SERVERS=" + ",".join(servers), "mcp-atlas-agent-environment"],
    "planned_completion_command": ["python", "services/mcp_eval/run.py", "--dataset", dataset, "--task-limit", task_limit, "--server-profile", server_profile],
    "planned_judge_command": ["python", "services/mcp_eval/mcp_evals_scores.py", "--input", output_dir + "/completion", "--threshold", "0.75"],
    "full_blockers": blockers,
    "fail_closed_until": [
        "HF parquet snapshot and sha256/row_count proof exist",
        "runtime image has P0 digest proof or verified fallback tar sha",
        "completion/eval runner image or wheelhouse is offline-ready",
        "local/replay fixtures cover selected smoke task tools",
        "agent and judge relay env are configured without writing secrets",
        "strict parser validates coverage and model-call accounting",
    ],
}, sort_keys=True))
MCP_ATLAS_RUNNER_JSON
  exit 0
fi

cat >&2 <<'EOF'
MCP-Atlas offline runner skeleton is fail-closed for non-dry-run execution.
TODO before enabling: snapshot HF parquet, stage runtime image transport,
materialize local/replay fixtures for <=5 smoke tasks, package completion/eval
env, verify agent+judge relay routing, and run strict parser proof.
EOF
exit 78
