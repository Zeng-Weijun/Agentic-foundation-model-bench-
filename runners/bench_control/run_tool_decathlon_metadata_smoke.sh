#!/usr/bin/env bash
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 2; }

mode="${TOOL_DECATHLON_SMOKE_MODE:-metadata}"
dry_run="${DRY_RUN:-0}"
shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
tool_root="${TOOL_DECATHLON_ROOT:-$nips_root/bench/sources/Toolathlon}"
tasks_dir="${TOOL_DECATHLON_TASKS_DIR:-$tool_root/tasks/finalpool}"
smoke_task="${TOOL_DECATHLON_SMOKE_TASK:-paper-checker}"
expected_tasks="${TOOL_DECATHLON_EXPECTED_TASKS:-108}"
run_root="${BENCH_OUTPUT_ROOT:-$nips_root/agentic-foundation-model-bench/runs/tool_decathlon_metadata_smoke}"
run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/$run_tag}"
summary_path="$bench_run_dir/tool_decathlon_metadata_summary.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) dry_run=0; shift ;;
    --dry-run) dry_run=1; shift ;;
    --metadata) mode=metadata; shift ;;
    -h|--help)
      sed -n '1,40p' "$0"
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "$mode" == "metadata" ]] || die "unsupported TOOL_DECATHLON_SMOKE_MODE=$mode"
command -v python3 >/dev/null 2>&1 || die "python3 is required"

echo "Tool-Decathlon metadata smoke wrapper"
echo "mode=$mode dry_run=$dry_run"
echo "tool_root=$tool_root"
echo "tasks_dir=$tasks_dir"
echo "smoke_task=$smoke_task"
echo "summary_path=$summary_path"

if [[ "$dry_run" == "1" ]]; then
  for path in "$tool_root" "$tasks_dir" "$tasks_dir/$smoke_task/task_config.json"; do
    [[ -e "$path" ]] && echo "  ok: $path" || echo "  missing: $path"
  done
  exit 0
fi


mkdir -p "$bench_run_dir"

python3 - "$tool_root" "$tasks_dir" "$smoke_task" "$expected_tasks" "$summary_path" <<'PYCODE'
import json
import pathlib
import sys
import tarfile
from datetime import datetime, timezone

tool_root = pathlib.Path(sys.argv[1]).resolve()
tasks_dir = pathlib.Path(sys.argv[2]).resolve()
smoke_task = sys.argv[3]
expected_tasks = int(sys.argv[4] or "0")
summary_path = pathlib.Path(sys.argv[5]).resolve()
required = ["task_config.json", "docs/task.md", "docs/agent_system_prompt.md", "preprocess/main.py", "evaluation/main.py", "initial_workspace/files.tar.gz", "groundtruth_workspace/files.tar.gz"]
errors = []
warnings = []

def tar_member_count(path):
    try:
        with tarfile.open(path, "r:gz") as tf:
            return len(tf.getmembers())
    except Exception as exc:  # noqa: BLE001
        errors.append({"path": str(path), "error": f"tar_read_failed: {exc}"})
        return 0

task_dirs = sorted(p for p in tasks_dir.iterdir() if p.is_dir()) if tasks_dir.is_dir() else []
if not tool_root.is_dir():
    errors.append({"path": str(tool_root), "error": "tool_root_missing"})
if not tasks_dir.is_dir():
    errors.append({"path": str(tasks_dir), "error": "tasks_dir_missing"})
if expected_tasks and len(task_dirs) != expected_tasks:
    errors.append({"error": "task_count_mismatch", "expected": expected_tasks, "actual": len(task_dirs)})
smoke_dir = tasks_dir / smoke_task
missing = [name for name in required if not (smoke_dir / name).is_file()]
if missing:
    errors.append({"error": "smoke_required_files_missing", "task": smoke_task, "missing": missing})
config = None
cfg_path = smoke_dir / "task_config.json"
if cfg_path.is_file():
    try:
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append({"path": str(cfg_path), "error": f"json_parse_failed: {exc}"})
initial_members = tar_member_count(smoke_dir / "initial_workspace/files.tar.gz") if not missing else 0
groundtruth_members = tar_member_count(smoke_dir / "groundtruth_workspace/files.tar.gz") if not missing else 0
summary = {
    "schema_version": "agentic_bench.tool_decathlon_metadata_smoke.v1",
    "bench": "Tool-Decathlon",
    "mode": "metadata",
    "status": "passed" if not errors else "failed",
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "tool_root": str(tool_root),
    "tasks_dir": str(tasks_dir),
    "task_count": len(task_dirs),
    "expected_task_count": expected_tasks,
    "smoke_task": smoke_task,
    "needed_mcp_servers": (config or {}).get("needed_mcp_servers", []),
    "needed_local_tools": (config or {}).get("needed_local_tools", []),
    "initial_workspace_members": initial_members,
    "groundtruth_workspace_members": groundtruth_members,
    "offline_contract": {"runs_docker": False, "runs_model_api": False, "downloads_assets": False},
    "errors": errors,
    "warnings": warnings,
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"status={summary['status']}")
print(f"task_count={summary['task_count']}")
print(f"smoke_task={summary['smoke_task']}")
print(f"summary={summary_path}")
sys.exit(0 if not errors else 2)
PYCODE
