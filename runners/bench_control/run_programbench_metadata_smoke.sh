#!/usr/bin/env bash
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 2; }

mode="${PROGRAMBENCH_SMOKE_MODE:-metadata}"
dry_run="${DRY_RUN:-0}"
shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
program_root="${PROGRAMBENCH_ROOT:-$nips_root/bench/sources/ProgramBench}"
tasks_dir="${PROGRAMBENCH_TASKS_DIR:-$program_root/src/programbench/data/tasks}"
smoke_instance="${PROGRAMBENCH_SMOKE_INSTANCE:-abishekvashok__cmatrix.5c082c6}"
expected_tasks="${PROGRAMBENCH_EXPECTED_TASKS:-201}"
expected_branches="${PROGRAMBENCH_EXPECTED_BRANCHES:-14}"
expected_tests="${PROGRAMBENCH_EXPECTED_TESTS:-769}"
expected_ignored_tests="${PROGRAMBENCH_EXPECTED_IGNORED_TESTS:-263}"
run_root="${BENCH_OUTPUT_ROOT:-$nips_root/agentic-foundation-model-bench/runs/programbench_metadata_smoke}"
run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/$run_tag}"
summary_path="$bench_run_dir/programbench_metadata_summary.json"

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

[[ "$mode" == "metadata" ]] || die "unsupported PROGRAMBENCH_SMOKE_MODE=$mode"
command -v python3 >/dev/null 2>&1 || die "python3 is required"

echo "ProgramBench metadata smoke wrapper"
echo "mode=$mode dry_run=$dry_run"
echo "program_root=$program_root"
echo "tasks_dir=$tasks_dir"
echo "smoke_instance=$smoke_instance"
echo "summary_path=$summary_path"

if [[ "$dry_run" == "1" ]]; then
  for path in "$program_root" "$tasks_dir" "$tasks_dir/$smoke_instance/task.yaml" "$tasks_dir/$smoke_instance/tests.json"; do
    [[ -e "$path" ]] && echo "  ok: $path" || echo "  missing: $path"
  done
  exit 0
fi


mkdir -p "$bench_run_dir"

python3 - "$program_root" "$tasks_dir" "$smoke_instance" "$expected_tasks" "$expected_branches" "$expected_tests" "$expected_ignored_tests" "$summary_path" <<'PYCODE'
import json
import pathlib
import sys
from datetime import datetime, timezone

program_root = pathlib.Path(sys.argv[1]).resolve()
tasks_dir = pathlib.Path(sys.argv[2]).resolve()
smoke_instance = sys.argv[3]
expected_tasks = int(sys.argv[4] or "0")
expected_branches = int(sys.argv[5] or "0")
expected_tests = int(sys.argv[6] or "0")
expected_ignored = int(sys.argv[7] or "0")
summary_path = pathlib.Path(sys.argv[8]).resolve()
errors = []
warnings = []

task_dirs = sorted(p for p in tasks_dir.iterdir() if p.is_dir()) if tasks_dir.is_dir() else []
if not program_root.is_dir():
    errors.append({"path": str(program_root), "error": "program_root_missing"})
if not tasks_dir.is_dir():
    errors.append({"path": str(tasks_dir), "error": "tasks_dir_missing"})
if expected_tasks and len(task_dirs) != expected_tasks:
    errors.append({"error": "task_count_mismatch", "expected": expected_tasks, "actual": len(task_dirs)})
missing_task_files = []
for task_dir in task_dirs:
    missing = [name for name in ("task.yaml", "tests.json") if not (task_dir / name).is_file()]
    if missing:
        missing_task_files.append({"task_id": task_dir.name, "missing": missing})
if missing_task_files:
    errors.append({"error": "missing_task_files", "count": len(missing_task_files), "items": missing_task_files[:20]})
smoke_dir = tasks_dir / smoke_instance
if not smoke_dir.is_dir():
    errors.append({"error": "smoke_instance_missing", "instance": smoke_instance})
tests = {}
if (smoke_dir / "tests.json").is_file():
    try:
        tests = json.loads((smoke_dir / "tests.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append({"path": str(smoke_dir / "tests.json"), "error": f"json_parse_failed: {exc}"})
branches = tests.get("branches", {}) if isinstance(tests, dict) else {}
branch_count = len(branches)
active_branch_count = sum(1 for item in branches.values() if not item.get("ignored"))
total_tests = sum(len(item.get("tests", [])) for item in branches.values())
total_ignored = sum(len(item.get("ignored_tests", [])) for item in branches.values())
if expected_branches and branch_count != expected_branches:
    errors.append({"error": "branch_count_mismatch", "expected": expected_branches, "actual": branch_count})
if expected_tests and total_tests != expected_tests:
    errors.append({"error": "test_count_mismatch", "expected": expected_tests, "actual": total_tests})
if expected_ignored and total_ignored != expected_ignored:
    errors.append({"error": "ignored_test_count_mismatch", "expected": expected_ignored, "actual": total_ignored})
summary = {
    "schema_version": "agentic_bench.programbench_metadata_smoke.v1",
    "bench": "ProgramBench",
    "mode": "metadata",
    "status": "passed" if not errors else "failed",
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "program_root": str(program_root),
    "tasks_dir": str(tasks_dir),
    "task_count": len(task_dirs),
    "expected_task_count": expected_tasks,
    "smoke_instance": smoke_instance,
    "branch_count": branch_count,
    "active_branch_count": active_branch_count,
    "total_tests_listed": total_tests,
    "total_ignored_tests": total_ignored,
    "offline_contract": {"runs_docker": False, "runs_model_api": False, "downloads_assets": False},
    "errors": errors,
    "warnings": warnings,
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"status={summary['status']}")
print(f"task_count={summary['task_count']}")
print(f"smoke_instance={summary['smoke_instance']}")
print(f"branch_count={summary['branch_count']} tests={summary['total_tests_listed']} ignored={summary['total_ignored_tests']}")
print(f"summary={summary_path}")
sys.exit(0 if not errors else 2)
PYCODE
