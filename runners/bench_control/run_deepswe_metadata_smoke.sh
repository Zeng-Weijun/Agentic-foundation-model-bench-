#!/usr/bin/env bash
set -euo pipefail

DEEPSWE_ROOT="${DEEPSWE_ROOT:-/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe}"
BENCH_RUN_DIR="${BENCH_RUN_DIR:-${RUN_DIR:-/tmp/deepswe_metadata_smoke}}"
DEEPSWE_EXPECTED_TASKS="${DEEPSWE_EXPECTED_TASKS:-}"
DEEPSWE_SAMPLE_LIMIT="${DEEPSWE_SAMPLE_LIMIT:-5}"
DEEPSWE_METADATA_ONLY="${DEEPSWE_METADATA_ONLY:-1}"

mkdir -p "$BENCH_RUN_DIR"
export DEEPSWE_ROOT BENCH_RUN_DIR DEEPSWE_EXPECTED_TASKS DEEPSWE_SAMPLE_LIMIT DEEPSWE_METADATA_ONLY

python3 - <<'PY'
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def toml_string(text: str, key: str) -> str:
    pattern = re.compile(r"(?m)^\s*" + re.escape(key) + r"\s*=\s*\"([^\"]*)\"\s*$")
    match = pattern.search(text)
    return match.group(1) if match else ""


def git_commit(root: Path) -> str:
    if not (root / ".git").exists():
        return ""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def path_state(path: Path) -> dict:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "executable": os.access(path, os.X_OK) if path.exists() else False,
        "sha256": file_sha256(path),
    }


root = Path(os.environ["DEEPSWE_ROOT"]).expanduser()
run_dir = Path(os.environ["BENCH_RUN_DIR"]).expanduser()
run_dir.mkdir(parents=True, exist_ok=True)
expected_raw = os.environ.get("DEEPSWE_EXPECTED_TASKS", "").strip()
sample_limit = int(os.environ.get("DEEPSWE_SAMPLE_LIMIT", "5") or "5")
dry_run = env_bool("DRY_RUN", True)
metadata_only = env_bool("DEEPSWE_METADATA_ONLY", True)

tasks_dir = root / "tasks"
errors = []
if not root.exists():
    errors.append(f"missing_deepswe_root:{root}")
if not tasks_dir.exists():
    errors.append(f"missing_tasks_dir:{tasks_dir}")

task_files = []
if tasks_dir.exists():
    candidates = set(tasks_dir.glob("*/task.toml"))
    candidates.update(tasks_dir.glob("*/*/task.toml"))
    task_files = sorted(path for path in candidates if path.is_file())

expected_count = None
if expected_raw:
    try:
        expected_count = int(expected_raw)
    except ValueError:
        errors.append(f"invalid_expected_task_count:{expected_raw}")
if expected_count is not None and len(task_files) != expected_count:
    errors.append(f"task_count_mismatch:expected={expected_count}:actual={len(task_files)}")

sample_tasks = []
sample_task_ids = []
docker_image_refs = []
language_counts = {}
category_counts = {}
missing_required_files = []
for task_file in task_files:
    text = read_text(task_file)
    task_id = toml_string(text, "task_id") or task_file.parent.name
    task_name = toml_string(text, "name")
    repository_url = toml_string(text, "repository_url")
    docker_image = toml_string(text, "docker_image")
    language = toml_string(text, "language")
    category = toml_string(text, "category")
    language_counts[language or "unknown"] = language_counts.get(language or "unknown", 0) + 1
    category_counts[category or "unknown"] = category_counts.get(category or "unknown", 0) + 1
    if docker_image and docker_image not in docker_image_refs:
        docker_image_refs.append(docker_image)
    required = {
        "instruction_md": task_file.parent / "instruction.md",
        "environment_dockerfile": task_file.parent / "environment" / "Dockerfile",
        "tests": task_file.parent / "tests",
        "solution": task_file.parent / "solution",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        missing_required_files.append({"task_id": task_id, "missing": missing, "task_path": rel(task_file.parent, root)})
    if len(sample_tasks) < sample_limit:
        sample_task_ids.append(task_id)
        sample_tasks.append(
            {
                "task_id": task_id,
                "task_name": task_name,
                "relative_path": rel(task_file.parent, root),
                "task_toml": rel(task_file, root),
                "repository_url": repository_url,
                "docker_image": docker_image,
                "language": language,
                "category": category,
                "has_instruction_md": required["instruction_md"].is_file(),
                "has_environment_dockerfile": required["environment_dockerfile"].is_file(),
                "has_tests_dir": required["tests"].is_dir(),
                "has_solution_dir": required["solution"].is_dir(),
            }
        )

repo_root = Path.cwd()
legacy_bench = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench")
shared_bench = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench")
pier_candidates = []
for raw in [
    shutil.which("pier") or "",
    str(legacy_bench / ".official_mini_swe_agent" / "pier-venv" / "bin" / "pier"),
    "/data/tmp/deepswe-pier-venv/bin/pier",
    "/root/.local/bin/pier",
]:
    if raw and raw not in [item["path"] for item in pier_candidates]:
        pier_candidates.append(path_state(Path(raw)))

runner_paths = {
    "metadata_wrapper": path_state(repo_root / "run_deepswe_metadata_smoke.sh"),
    "legacy_runner": path_state(legacy_bench / "run_deepswe.sh"),
    "legacy_smoke_launcher": path_state(legacy_bench / "run_gpt54mini_deepswe_smoke.sh"),
    "shared_runner": path_state(shared_bench / "shared" / "runners" / "run_deepswe.sh"),
    "projectized_agent": path_state(shared_bench / "deepswe" / "deepswe-agent"),
    "source_checkout": path_state(shared_bench / "deepswe" / "source"),
    "pier_candidates": pier_candidates,
}

full_run_blockers = []
if not docker_image_refs:
    full_run_blockers.append("no_task_docker_image_refs_found")
else:
    full_run_blockers.append("task_image_refs_not_digest_pinned_or_preloaded")
if not pier_candidates or not any(item["exists"] for item in pier_candidates):
    full_run_blockers.append("pier_runtime_not_present_on_this_host")
full_run_blockers.extend(
    [
        "rootless_worker_image_cache_not_proven_for_deepswe_task_images",
        "container_to_model_relay_not_proven_for_deepswe",
    ]
)

result = {
    "schema_version": "agentic_bench.deepswe_metadata_smoke.v1",
    "status": "fail" if errors else "pass",
    "mode": "metadata_smoke",
    "dry_run": dry_run,
    "metadata_only": metadata_only,
    "requires_model_call": False,
    "requires_docker_execute": False,
    "network_downloads_performed": False,
    "docker_actions_performed": False,
    "deepswe_root": str(root),
    "deepswe_root_exists": root.exists(),
    "git_commit": git_commit(root),
    "tasks_dir": str(tasks_dir),
    "tasks_dir_exists": tasks_dir.exists(),
    "expected_task_count": expected_count,
    "task_count": len(task_files),
    "sample_task_ids": sample_task_ids,
    "sample_tasks": sample_tasks,
    "docker_image_refs": docker_image_refs,
    "unique_docker_image_count": len(docker_image_refs),
    "language_counts": dict(sorted(language_counts.items())),
    "category_counts": dict(sorted(category_counts.items())),
    "missing_required_files_count": len(missing_required_files),
    "missing_required_files_sample": missing_required_files[:sample_limit],
    "runner_paths": runner_paths,
    "full_run_blockers": full_run_blockers,
    "errors": errors,
}

json_path = run_dir / "deepswe_metadata_smoke.json"
json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"DEEPSWE_METADATA_STATUS={result['status']}")
print(f"DEEPSWE_ROOT={root}")
print(f"DEEPSWE_TASK_COUNT={len(task_files)}")
print(f"DEEPSWE_UNIQUE_DOCKER_IMAGES={len(docker_image_refs)}")
print(f"DEEPSWE_METADATA_JSON={json_path}")
if errors:
    print("DEEPSWE_METADATA_ERRORS=" + ";".join(errors), file=sys.stderr)
sys.exit(2 if errors else 0)
PY
