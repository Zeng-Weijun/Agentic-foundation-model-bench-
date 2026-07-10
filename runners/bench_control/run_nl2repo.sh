#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_nl2repo.sh [--execute|--dry-run]

Metadata-only NL2Repo smoke. It validates the staged NL2RepoBench test_files
snapshot and writes a JSON summary. It intentionally does not run OpenHands,
Docker, package installation, or model/API calls.

Environment:
  NL2REPO_SMOKE_MODE      metadata (default)
  NL2REPO_ROOT            NL2RepoBench source root
  NL2REPO_EXPECTED_TASKS  expected task directory count, 0 disables check
  NL2REPO_EXPECTED_TESTS  expected declared test count, 0 disables check
  BENCH_RUN_DIR           output directory for nl2repo_metadata_summary.json
  DRY_RUN                 1 prints preflight only
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 2
}

shell_quote() {
  printf "%q" "$1"
}

print_export() {
  local name="$1"
  local value="$2"
  printf "export %s=" "$name"
  shell_quote "$value"
  printf "\n"
}

mode="${NL2REPO_SMOKE_MODE:-metadata}"
dry_run="${DRY_RUN:-0}"
shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
nl2repo_root="${NL2REPO_ROOT:-$nips_root/bench/sources/NL2RepoBench}"
run_root="${BENCH_OUTPUT_ROOT:-$nips_root/agentic-foundation-model-bench/runs/nl2repo_metadata_smoke}"
run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/$run_tag}"
summary_path="$bench_run_dir/nl2repo_metadata_summary.json"
expected_tasks="${NL2REPO_EXPECTED_TASKS:-104}"
expected_tests="${NL2REPO_EXPECTED_TESTS:-25640}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      dry_run=0
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --metadata)
      mode=metadata
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ "$mode" == "metadata" ]] || die "unsupported NL2REPO_SMOKE_MODE=$mode; only metadata is wired offline"
command -v python3 >/dev/null 2>&1 || die "python3 is required"


echo "NL2Repo metadata smoke wrapper"
echo "mode=$mode"
echo "dry_run=$dry_run"
echo "nl2repo_root=$nl2repo_root"
echo "summary_path=$summary_path"
echo "expected_tasks=$expected_tasks"
echo "expected_tests=$expected_tests"
echo

print_export NL2REPO_SMOKE_MODE "$mode"
print_export NL2REPO_ROOT "$nl2repo_root"
print_export BENCH_RUN_DIR "$bench_run_dir"
print_export NL2REPO_EXPECTED_TASKS "$expected_tasks"
print_export NL2REPO_EXPECTED_TESTS "$expected_tests"
echo

if [[ "$dry_run" == "1" ]]; then
  echo "Preflight observations:"
  for path in "$nl2repo_root" "$nl2repo_root/test_files" "$nl2repo_root/config.json"; do
    if [[ -e "$path" ]]; then
      echo "  ok: $path"
    else
      echo "  missing: $path"
    fi
  done
  exit 0
fi


mkdir -p "$bench_run_dir"

python3 - "$nl2repo_root" "$summary_path" "$expected_tasks" "$expected_tests" <<'PYCODE'
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

root = pathlib.Path(sys.argv[1]).expanduser().resolve()
summary_path = pathlib.Path(sys.argv[2]).expanduser().resolve()
expected_tasks = int(sys.argv[3] or "0")
expected_tests = int(sys.argv[4] or "0")
required_names = ["start.md", "test_case_count.txt", "test_commands.json", "test_files.json"]
errors = []
warnings = []

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validation report needs exact file path.
        errors.append({"path": str(path), "error": f"json_parse_failed: {exc}"})
        return None

def git_head(path):
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""

test_files = root / "test_files"
config_path = root / "config.json"
task_summaries = []
missing_required = []
invalid_counts = []
empty_commands = []
empty_test_file_lists = []
declared_test_count = 0

if not root.exists():
    errors.append({"path": str(root), "error": "nl2repo_root_missing"})
    task_dirs = []
elif not test_files.is_dir():
    errors.append({"path": str(test_files), "error": "test_files_dir_missing"})
    task_dirs = []
else:
    task_dirs = sorted(path for path in test_files.iterdir() if path.is_dir())

for task_dir in task_dirs:
    task_id = task_dir.name
    missing = [name for name in required_names if not (task_dir / name).is_file()]
    if missing:
        missing_required.append({"task_id": task_id, "missing": missing})
        continue

    count_path = task_dir / "test_case_count.txt"
    try:
        count = int(count_path.read_text(encoding="utf-8").strip())
        if count < 0:
            raise ValueError("negative count")
    except Exception as exc:  # noqa: BLE001
        invalid_counts.append({"task_id": task_id, "path": str(count_path), "error": str(exc)})
        count = 0
    declared_test_count += count

    commands = read_json(task_dir / "test_commands.json")
    test_files_list = read_json(task_dir / "test_files.json")
    if isinstance(commands, list) and not commands:
        empty_commands.append(task_id)
    if isinstance(test_files_list, list) and not test_files_list:
        empty_test_file_lists.append(task_id)

    task_summaries.append(
        {
            "task_id": task_id,
            "declared_test_count": count,
            "command_count": len(commands) if isinstance(commands, list) else None,
            "test_file_entry_count": len(test_files_list) if isinstance(test_files_list, list) else None,
            "start_md_bytes": (task_dir / "start.md").stat().st_size,
        }
    )

if missing_required:
    errors.append({"error": "missing_required_task_files", "items": missing_required[:20], "count": len(missing_required)})
if invalid_counts:
    errors.append({"error": "invalid_test_case_count", "items": invalid_counts[:20], "count": len(invalid_counts)})
if empty_commands:
    errors.append({"error": "empty_test_commands", "items": empty_commands[:20], "count": len(empty_commands)})
if empty_test_file_lists:
    errors.append({"error": "empty_test_files", "items": empty_test_file_lists[:20], "count": len(empty_test_file_lists)})

if expected_tasks and len(task_dirs) != expected_tasks:
    errors.append({"error": "task_count_mismatch", "expected": expected_tasks, "actual": len(task_dirs)})
if expected_tests and declared_test_count != expected_tests:
    errors.append({"error": "declared_test_count_mismatch", "expected": expected_tests, "actual": declared_test_count})

config_names = []
if config_path.is_file():
    config = read_json(config_path)
    if isinstance(config, dict):
        for profile in config.get("startPro", []):
            if isinstance(profile, dict):
                config_names.extend(str(name) for name in profile.get("proNameList", []) if name is not None)
else:
    warnings.append({"warning": "config_json_missing", "path": str(config_path)})

task_names = [path.name for path in task_dirs]
config_set = set(config_names)
task_set = set(task_names)
config_missing_task_dirs = sorted(config_set - task_set)
task_dirs_missing_from_config = sorted(task_set - config_set)
if config_missing_task_dirs or task_dirs_missing_from_config:
    warnings.append(
        {
            "warning": "config_task_name_mismatch",
            "config_missing_task_dirs": config_missing_task_dirs,
            "task_dirs_missing_from_config": task_dirs_missing_from_config,
        }
    )

summary = {
    "schema_version": "agentic_bench.nl2repo_metadata_smoke.v1",
    "bench": "NL2Repo",
    "mode": "metadata",
    "status": "passed" if not errors else "failed",
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "nl2repo_root": str(root),
    "source_git_head": git_head(root),
    "test_files_dir": str(test_files),
    "required_file_names": required_names,
    "task_count": len(task_dirs),
    "expected_task_count": expected_tasks,
    "declared_test_count": declared_test_count,
    "expected_declared_test_count": expected_tests,
    "config_task_count": len(config_names),
    "config_missing_task_dirs": config_missing_task_dirs,
    "task_dirs_missing_from_config": task_dirs_missing_from_config,
    "first_task_ids": task_names[:10],
    "task_summaries_sample": task_summaries[:5],
    "errors": errors,
    "warnings": warnings,
    "offline_contract": {
        "runs_docker": False,
        "runs_model_api": False,
        "runs_openhands": False,
        "downloads_assets": False,
    },
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"status={summary['status']}")
print(f"task_count={summary['task_count']}")
print(f"declared_test_count={summary['declared_test_count']}")
print(f"summary={summary_path}")
if warnings:
    print(f"warnings={len(warnings)}")
if errors:
    print(f"errors={len(errors)}", file=sys.stderr)
sys.exit(0 if not errors else 2)
PYCODE
