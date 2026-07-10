#!/usr/bin/env bash
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 2; }

mode="${MCP_ATLAS_SMOKE_MODE:-metadata}"
dry_run="${DRY_RUN:-0}"
shared_root="${SHARED_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun}"
nips_root="${NIPS_ROOT:-$shared_root/nips2026}"
mcp_root="${MCP_ATLAS_ROOT:-$nips_root/bench/sources/mcp-atlas}"
sample_tasks="${MCP_ATLAS_SAMPLE_TASKS:-$mcp_root/services/mcp_eval/sample_tasks.csv}"
server_template="${MCP_ATLAS_SERVER_TEMPLATE:-$mcp_root/services/agent-environment/src/agent_environment/mcp_server_template.json}"
mcp_client="${MCP_ATLAS_MCP_CLIENT:-$mcp_root/services/agent-environment/src/agent_environment/mcp_client.py}"
dataset_path="${MCP_ATLAS_HF_DATASET_PATH:-$nips_root/bench/datasets/ScaleAI-MCP-Atlas/MCP-Atlas.parquet}"
expected_commit="${MCP_ATLAS_EXPECTED_COMMIT:-b290e672645791fea0bcb23e2c0f4fec50715cca}"
expected_sample_tasks="${MCP_ATLAS_EXPECTED_SAMPLE_TASKS:-10}"
expected_servers="${MCP_ATLAS_EXPECTED_SERVERS:-36}"
expected_default_servers="${MCP_ATLAS_EXPECTED_DEFAULT_SERVERS:-20}"
require_hf_dataset="${MCP_ATLAS_REQUIRE_HF_DATASET:-0}"
run_root="${BENCH_OUTPUT_ROOT:-$nips_root/agentic-foundation-model-bench/runs/mcp_atlas_metadata_smoke}"
run_tag="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
bench_run_dir="${BENCH_RUN_DIR:-$run_root/$run_tag}"
summary_path="$bench_run_dir/mcp_atlas_metadata_summary.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute) dry_run=0; shift ;;
    --dry-run) dry_run=1; shift ;;
    --metadata) mode=metadata; shift ;;
    -h|--help)
      sed -n '1,52p' "$0"
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "$mode" == "metadata" ]] || die "unsupported MCP_ATLAS_SMOKE_MODE=$mode"
command -v python3 >/dev/null 2>&1 || die "python3 is required"

echo "MCP-Atlas metadata smoke wrapper"
echo "mode=$mode dry_run=$dry_run"
echo "mcp_root=$mcp_root"
echo "sample_tasks=$sample_tasks"
echo "server_template=$server_template"
echo "mcp_client=$mcp_client"
echo "dataset_path=$dataset_path"
echo "summary_path=$summary_path"

if [[ "$dry_run" == "1" ]]; then
  for path in "$mcp_root" "$sample_tasks" "$server_template" "$mcp_client"; do
    [[ -e "$path" ]] && echo "  ok: $path" || echo "  missing: $path"
  done
  [[ -e "$dataset_path" ]] && echo "  ok: $dataset_path" || echo "  optional-missing: $dataset_path"
  exit 0
fi

mkdir -p "$bench_run_dir"

python3 - "$mcp_root" "$sample_tasks" "$server_template" "$mcp_client" "$dataset_path" "$expected_commit" "$expected_sample_tasks" "$expected_servers" "$expected_default_servers" "$require_hf_dataset" "$summary_path" <<'PYCODE'
import ast
import csv
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

mcp_root = pathlib.Path(sys.argv[1]).resolve()
sample_tasks = pathlib.Path(sys.argv[2]).resolve()
server_template = pathlib.Path(sys.argv[3]).resolve()
mcp_client = pathlib.Path(sys.argv[4]).resolve()
dataset_path = pathlib.Path(sys.argv[5]).resolve()
expected_commit = sys.argv[6]
expected_sample_tasks = int(sys.argv[7] or "0")
expected_servers = int(sys.argv[8] or "0")
expected_default_servers = int(sys.argv[9] or "0")
require_hf_dataset = sys.argv[10].lower() in {"1", "true", "yes", "on"}
summary_path = pathlib.Path(sys.argv[11]).resolve()
errors = []
warnings = []


def error(kind, **fields):
    item = {"error": kind}
    item.update(fields)
    errors.append(item)


def warning(kind, **fields):
    item = {"warning": kind}
    item.update(fields)
    warnings.append(item)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        error("json_parse_failed", path=str(path), detail=str(exc))
        return {}


def git_head(path):
    try:
        proc = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True, check=False, timeout=5)
    except Exception as exc:
        warning("git_head_unavailable", detail=str(exc))
        return ""
    if proc.returncode != 0:
        warning("git_head_unavailable", detail=proc.stderr.strip())
        return ""
    return proc.stdout.strip()


def default_servers(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        error("mcp_client_parse_failed", path=str(path), detail=str(exc))
        return []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "DEFAULT_SERVERS" for target in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                return [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
    error("default_servers_not_found", path=str(path))
    return []

for label, path in [("mcp_root", mcp_root), ("sample_tasks", sample_tasks), ("server_template", server_template), ("mcp_client", mcp_client)]:
    if not path.exists():
        error("required_path_missing", label=label, path=str(path))

commit = git_head(mcp_root) if mcp_root.exists() else ""
if expected_commit and commit and commit != expected_commit:
    error("commit_mismatch", expected=expected_commit, actual=commit)

rows = []
required_fields = {"TASK", "ENABLED_TOOLS", "PROMPT", "TRAJECTORY", "GTFA_CLAIMS"}
if sample_tasks.is_file():
    try:
        with sample_tasks.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            if fields != required_fields:
                error("sample_tasks_header_mismatch", missing=sorted(required_fields - fields), extra=sorted(fields - required_fields))
            rows = list(reader)
    except Exception as exc:
        error("sample_tasks_read_failed", path=str(sample_tasks), detail=str(exc))
if expected_sample_tasks and len(rows) != expected_sample_tasks:
    error("sample_task_count_mismatch", expected=expected_sample_tasks, actual=len(rows))

template = load_json(server_template) if server_template.is_file() else {}
servers = template.get("mcpServers", {}) if isinstance(template, dict) else {}
server_names = sorted(servers) if isinstance(servers, dict) else []
if expected_servers and len(server_names) != expected_servers:
    error("server_count_mismatch", expected=expected_servers, actual=len(server_names))

default = default_servers(mcp_client) if mcp_client.is_file() else []
if expected_default_servers and len(default) != expected_default_servers:
    error("default_server_count_mismatch", expected=expected_default_servers, actual=len(default))
missing_defaults = sorted(set(default) - set(server_names))
if missing_defaults:
    error("default_servers_missing_from_template", missing=missing_defaults)

task_ids = []
unique_tools = set()
json_field_errors = 0
for row in rows:
    task_id = row.get("TASK", "")
    task_ids.append(task_id)
    for field in ("ENABLED_TOOLS", "TRAJECTORY", "GTFA_CLAIMS"):
        try:
            value = json.loads(row.get(field, "[]"))
        except Exception as exc:
            json_field_errors += 1
            error("csv_json_field_parse_failed", task_id=task_id, field=field, detail=str(exc))
            continue
        if field == "ENABLED_TOOLS" and isinstance(value, list):
            unique_tools.update(str(item) for item in value)
if not dataset_path.is_file():
    if require_hf_dataset:
        error("hf_dataset_parquet_missing", path=str(dataset_path))
    else:
        warning("hf_dataset_parquet_missing", path=str(dataset_path))

summary = {
    "schema_version": "agentic_bench.mcp_atlas_metadata_smoke.v1",
    "bench": "MCP-Atlas",
    "mode": "metadata",
    "status": "passed" if not errors else "failed",
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mcp_root": str(mcp_root),
    "git_commit": commit,
    "expected_commit": expected_commit,
    "sample_tasks_csv": str(sample_tasks),
    "sample_task_count": len(rows),
    "expected_sample_task_count": expected_sample_tasks,
    "sample_task_ids": task_ids,
    "unique_enabled_tools": len(unique_tools),
    "server_template": str(server_template),
    "server_count": len(server_names),
    "expected_server_count": expected_servers,
    "default_server_count": len(default),
    "expected_default_server_count": expected_default_servers,
    "hf_dataset_path": str(dataset_path),
    "hf_dataset_present": dataset_path.is_file(),
    "offline_contract": {"runs_docker": False, "runs_model_api": False, "downloads_assets": False},
    "errors": errors,
    "warnings": warnings,
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"status={summary['status']}")
print(f"sample_task_count={summary['sample_task_count']}")
print(f"server_count={summary['server_count']} default_server_count={summary['default_server_count']}")
print(f"hf_dataset_present={summary['hf_dataset_present']}")
print(f"summary={summary_path}")
sys.exit(0 if not errors else 2)
PYCODE
