#!/usr/bin/env python3
"""Registry-aware image manifest checker for offline agentic bench workers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, NamedTuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "manifests" / "bench_registry.yaml"
DEFAULT_ASSET_ROOT = Path(
    "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench"
)
DEFAULT_DOCKER_HOST = "unix:///tmp/rl/run/docker.sock"
INTERNAL_REGISTRY_PREFIXES = ("100.97.118.137:8555/",)


try:
    from scripts.check_offline_images_manifest import load_yaml as _load_yaml
except ModuleNotFoundError:  # pragma: no cover - used when executed from scripts/
    from check_offline_images_manifest import load_yaml as _load_yaml  # type: ignore


class ImageManifestError(ValueError):
    """Raised when registry/image manifest input is invalid."""


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[list[str], dict[str, str]], CommandResult]


def _run(argv: list[str], env: dict[str, str]) -> CommandResult:
    proc = subprocess.run(argv, text=True, capture_output=True, check=False, env=env)
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def _load(path: Path) -> Any:
    try:
        return _load_yaml(path)
    except Exception as exc:  # noqa: BLE001 - convert checker parser errors into this CLI's domain.
        raise ImageManifestError(str(exc)) from exc


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ImageManifestError(f"{name} must be a mapping")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ImageManifestError(f"{name} must be a list")
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(*values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in _as_list(value):
            if item is None:
                continue
            text = str(item).strip()
            if text:
                result.append(text)
    return list(dict.fromkeys(result))


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_asset_path(path_text: str, manifest_path: Path, asset_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    asset_candidate = asset_root / path
    manifest_candidate = manifest_path.parent / path
    if asset_candidate.exists() or not manifest_candidate.exists():
        return asset_candidate
    return manifest_candidate


def _resolve_manifest_path(path_text: str, registry_path: Path, asset_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    registry_candidate = registry_path.parent / path
    if registry_candidate.exists():
        return registry_candidate
    return asset_root / path


def _digest_from_sha_file(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ImageManifestError(f"could not read sha256 file {path}: {exc}") from exc
    if not content:
        raise ImageManifestError(f"empty sha256 file {path}")
    return content.split()[0]


def image_entries(config: Any) -> tuple[str, list[dict[str, Any]]]:
    config_map = _require_mapping(config, "image manifest root")
    images = _require_list(config_map.get("images"), "images")
    bench_id = str(config_map.get("bench_id") or config_map.get("bench") or "")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(images, start=1):
        raw_map = _require_mapping(raw, f"images[{index}]")
        local_refs = _string_list(
            raw_map.get("local_ref"),
            raw_map.get("local_refs"),
            raw_map.get("required_images"),
            raw_map.get("expected_tags"),
        )
        image_refs = _string_list(raw_map.get("image_ref"), raw_map.get("image_refs"), raw_map.get("registry_ref"))
        fallback_tars = _string_list(raw_map.get("fallback_tar"), raw_map.get("fallback_tars"), raw_map.get("tar_paths"))
        entries.append(
            {
                "id": str(raw_map.get("id") or f"image_{index}"),
                "role": raw_map.get("role", ""),
                "required": _bool(raw_map.get("required"), default=True),
                "local_refs": local_refs,
                "image_refs": image_refs,
                "inspect_refs": local_refs or image_refs,
                "fallback_tars": fallback_tars,
                "fallback_tar_sha256": raw_map.get("fallback_tar_sha256"),
                "fallback_tar_sha256_path": raw_map.get("fallback_tar_sha256_path"),
                "smoke": raw_map.get("smoke", {}),
                "raw": raw_map,
            }
        )
    return bench_id, entries


def _fallback_status(entry: dict[str, Any], manifest_path: Path, asset_root: Path) -> dict[str, Any]:
    fallback = {
        "tar_paths": [],
        "present_paths": [],
        "missing_paths": [],
        "sha256": "",
        "sha256_status": "not_configured",
    }
    for tar_text in entry["fallback_tars"]:
        tar_path = _resolve_asset_path(tar_text, manifest_path, asset_root)
        fallback["tar_paths"].append(str(tar_path))
        if tar_path.is_file():
            fallback["present_paths"].append(str(tar_path))
        else:
            fallback["missing_paths"].append(str(tar_path))
    sha_value = entry.get("fallback_tar_sha256")
    sha_path_value = entry.get("fallback_tar_sha256_path")
    if not sha_value and sha_path_value:
        sha_path = _resolve_asset_path(str(sha_path_value), manifest_path, asset_root)
        if sha_path.is_file():
            sha_value = _digest_from_sha_file(sha_path)
    if sha_value:
        fallback["sha256"] = str(sha_value)
        if not fallback["present_paths"]:
            fallback["sha256_status"] = "tar_missing"
        else:
            actual = _sha256(Path(fallback["present_paths"][0]))
            fallback["sha256_actual"] = actual
            fallback["sha256_status"] = "match" if actual == str(sha_value) else "mismatch"
    return fallback


def _docker_inspect(refs: list[str], env: dict[str, str], runner: Runner) -> tuple[bool, str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for ref in refs:
        result = runner(["docker", "image", "inspect", ref], env)
        attempt = {"ref": ref, "returncode": result.returncode}
        if result.returncode != 0:
            attempt["stderr"] = result.stderr.strip()
        attempts.append(attempt)
        if result.returncode == 0:
            return True, ref, attempts
    return False, "", attempts


def _is_internal_ref(ref: str) -> bool:
    return ref.startswith(INTERNAL_REGISTRY_PREFIXES)


def _docker_load(tar_path: str, env: dict[str, str], runner: Runner) -> CommandResult:
    return runner(["docker", "load", "-i", tar_path], env)


def _docker_pull(ref: str, env: dict[str, str], runner: Runner) -> CommandResult:
    return runner(["docker", "pull", ref], env)


def docker_cache_inventory(
    *,
    prefixes: list[str] | None = None,
    docker_host: str = DEFAULT_DOCKER_HOST,
    runner: Runner = _run,
    base_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = dict(base_env or os.environ)
    env["DOCKER_HOST"] = docker_host
    selected_prefixes = [prefix for prefix in (prefixes or []) if prefix]
    result = runner(["docker", "image", "ls", "--format", "{{json .}}"], env)
    if result.returncode != 0:
        raise ImageManifestError(result.stderr.strip() or "docker image ls failed")

    images: list[dict[str, str]] = []
    for line_number, line in enumerate(result.stdout.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ImageManifestError(f"docker image ls returned invalid json on line {line_number}: {exc}") from exc
        repository = str(row.get("Repository") or "").strip()
        tag = str(row.get("Tag") or "").strip()
        if not repository or repository == "<none>" or tag == "<none>":
            continue
        ref = f"{repository}:{tag}" if tag else repository
        if selected_prefixes and not any(repository.startswith(prefix) or ref.startswith(prefix) for prefix in selected_prefixes):
            continue
        digest = str(row.get("Digest") or "").strip()
        images.append(
            {
                "repository": repository,
                "tag": tag,
                "ref": ref,
                "image_id": str(row.get("ID") or "").strip(),
                "digest": "" if digest == "<none>" else digest,
                "size": str(row.get("Size") or "").strip(),
            }
        )

    images.sort(key=lambda image: image["ref"])
    return {
        "schema_version": "agentic_bench.docker_cache_inventory.v1",
        "docker_host": docker_host,
        "prefixes": selected_prefixes,
        "counts": {"images": len(images), "prefixes": len(selected_prefixes)},
        "images": images,
    }


def _smoke_command(entry: dict[str, Any], image_ref: str) -> list[str] | None:
    smoke = entry.get("smoke") or {}
    if not isinstance(smoke, dict):
        return None
    command = smoke.get("command")
    if not command:
        return None
    network = str(smoke.get("network", "none"))
    if isinstance(command, list):
        command_parts = [str(item) for item in command]
    else:
        command_parts = ["/bin/sh", "-lc", str(command)]
    return ["docker", "run", "--rm", "--network", network, image_ref, *command_parts]


def check_image_manifest(
    manifest_path: str | Path,
    *,
    asset_root: str | Path = DEFAULT_ASSET_ROOT,
    docker_host: str = DEFAULT_DOCKER_HOST,
    runner: Runner = _run,
    skip_docker: bool = False,
    allow_pull: bool = False,
    load_fallback: bool = False,
    run_smoke: bool = False,
    fail_on_optional_missing: bool = False,
    base_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    manifest = Path(manifest_path)
    asset_root_path = Path(asset_root)
    bench_id, entries = image_entries(_load(manifest))
    env = dict(base_env or os.environ)
    env["DOCKER_HOST"] = docker_host
    counts = {
        "present": 0,
        "missing": 0,
        "unchecked": 0,
        "errors": 0,
        "tar_verified": 0,
        "tar_missing": 0,
        "tar_mismatch": 0,
        "loaded": 0,
        "pulled": 0,
        "smoke_passed": 0,
        "optional_missing": 0,
    }
    results: list[dict[str, Any]] = []

    for entry in entries:
        fallback = _fallback_status(entry, manifest, asset_root_path)
        if fallback["sha256_status"] == "match":
            counts["tar_verified"] += 1
        elif fallback["sha256_status"] == "mismatch":
            counts["tar_mismatch"] += 1
        elif fallback["missing_paths"]:
            counts["tar_missing"] += 1

        result = {
            "id": entry["id"],
            "role": entry["role"],
            "required": entry["required"],
            "local_refs": entry["local_refs"],
            "image_refs": entry["image_refs"],
            "inspect_attempts": [],
            "fallback": fallback,
            "status": "",
        }

        if skip_docker:
            counts["unchecked"] += 1
            result["status"] = "unchecked"
            results.append(result)
            continue

        present, present_ref, attempts = _docker_inspect(entry["inspect_refs"], env, runner)
        result["inspect_attempts"] = attempts
        if not present and allow_pull and entry["image_refs"]:
            pull_ref = entry["image_refs"][0]
            if not _is_internal_ref(pull_ref):
                result["pull_status"] = "refused_non_internal_registry"
            else:
                pull_result = _docker_pull(pull_ref, env, runner)
                result["pull_status"] = "pulled" if pull_result.returncode == 0 else "failed"
                if pull_result.returncode == 0:
                    counts["pulled"] += 1
                    present, present_ref, attempts = _docker_inspect([pull_ref], env, runner)
                    result["inspect_attempts"].extend(attempts)
                else:
                    result["pull_stderr"] = pull_result.stderr.strip()

        if not present and load_fallback and fallback["present_paths"] and fallback["sha256_status"] in {"match", "not_configured"}:
            load_result = _docker_load(str(fallback["present_paths"][0]), env, runner)
            result["load_status"] = "loaded" if load_result.returncode == 0 else "failed"
            if load_result.returncode == 0:
                counts["loaded"] += 1
                present, present_ref, attempts = _docker_inspect(entry["inspect_refs"], env, runner)
                result["inspect_attempts"].extend(attempts)
            else:
                result["load_stderr"] = load_result.stderr.strip()

        if present:
            counts["present"] += 1
            result["status"] = "present"
            result["present_ref"] = present_ref
            smoke_argv = _smoke_command(entry, present_ref)
            if run_smoke and smoke_argv:
                smoke_result = runner(smoke_argv, env)
                result["smoke_status"] = "passed" if smoke_result.returncode == 0 else "failed"
                if smoke_result.returncode == 0:
                    counts["smoke_passed"] += 1
                else:
                    counts["errors"] += 1
                    result["smoke_stderr"] = smoke_result.stderr.strip()
            results.append(result)
            continue

        if entry["required"]:
            counts["missing"] += 1
            result["status"] = "missing"
        else:
            counts["unchecked"] += 1
            counts["optional_missing"] += 1
            result["status"] = "optional_missing"
        results.append(result)

    return {
        "schema_version": "agentic_bench.image_check.v1",
        "manifest": str(manifest),
        "bench_id": bench_id,
        "asset_root": str(asset_root_path),
        "docker_host": docker_host,
        "mode": {
            "skip_docker": skip_docker,
            "allow_pull": allow_pull,
            "load_fallback": load_fallback,
            "run_smoke": run_smoke,
            "fail_on_optional_missing": fail_on_optional_missing,
        },
        "counts": counts,
        "images": results,
    }


def registry_manifest_entries(config: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config_map = _require_mapping(config, "registry manifest root")
    registry = _require_mapping(config_map.get("registry", {}), "registry")
    manifests = _require_list(config_map.get("image_manifests"), "image_manifests")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(manifests, start=1):
        raw_map = _require_mapping(raw, f"image_manifests[{index}]")
        path = raw_map.get("path")
        if not path:
            raise ImageManifestError(f"image_manifests[{index}] requires path")
        entries.append({"id": str(raw_map.get("id") or f"manifest_{index}"), "path": str(path), "raw": raw_map})
    return registry, entries


def validate_registry(registry_path: str | Path, *, asset_root: str | Path = DEFAULT_ASSET_ROOT) -> dict[str, Any]:
    registry_manifest = Path(registry_path)
    asset_root_path = Path(asset_root)
    registry, entries = registry_manifest_entries(_load(registry_manifest))
    counts = {"manifests": 0, "images": 0, "required_images": 0, "missing_manifests": 0}
    manifests: list[dict[str, Any]] = []
    for entry in entries:
        path = _resolve_manifest_path(entry["path"], registry_manifest, asset_root_path)
        if not path.is_file():
            counts["missing_manifests"] += 1
            manifests.append({"id": entry["id"], "path": str(path), "status": "missing"})
            continue
        bench_id, images = image_entries(_load(path))
        counts["manifests"] += 1
        counts["images"] += len(images)
        counts["required_images"] += sum(1 for image in images if image["required"])
        manifests.append(
            {
                "id": entry["id"],
                "path": str(path),
                "status": "ok",
                "bench_id": bench_id,
                "images": [
                    {
                        "id": image["id"],
                        "required": image["required"],
                        "local_refs": image["local_refs"],
                        "image_refs": image["image_refs"],
                        "fallback_tars": image["fallback_tars"],
                    }
                    for image in images
                ],
            }
        )
    return {
        "schema_version": "agentic_bench.registry_validation.v1",
        "registry": registry,
        "registry_manifest": str(registry_manifest),
        "asset_root": str(asset_root_path),
        "counts": counts,
        "manifests": manifests,
    }


def _print_check(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print(f"Manifest: {summary['manifest']}")
    print(f"Bench: {summary['bench_id']}")
    print(f"Docker host: {summary['docker_host']}")
    print(
        "Summary: "
        f"present={counts['present']} "
        f"missing={counts['missing']} "
        f"unchecked={counts['unchecked']} "
        f"tar_verified={counts['tar_verified']} "
        f"tar_missing={counts['tar_missing']} "
        f"errors={counts['errors']}"
    )
    for image in summary["images"]:
        print(f"- {image['id']}: {image['status']}")
        if image.get("present_ref"):
            print(f"  present_ref: {image['present_ref']}")
        if image["fallback"]["tar_paths"]:
            print(f"  fallback_tars: {', '.join(image['fallback']['tar_paths'])}")


def _print_registry(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print(f"Registry manifest: {summary['registry_manifest']}")
    print(f"Registry: {summary['registry'].get('domain', summary['registry'].get('url', ''))}")
    print(
        "Summary: "
        f"manifests={counts['manifests']} "
        f"images={counts['images']} "
        f"required_images={counts['required_images']} "
        f"missing_manifests={counts['missing_manifests']}"
    )
    for manifest in summary["manifests"]:
        print(f"- {manifest['id']}: {manifest['status']} {manifest['path']}")


def _print_inventory(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print(f"Docker host: {summary['docker_host']}")
    print(f"Prefixes: {', '.join(summary['prefixes']) if summary['prefixes'] else '(all)'}")
    print(f"Summary: images={counts['images']}")
    for image in summary["images"]:
        size = f" {image['size']}" if image.get("size") else ""
        print(f"- {image['ref']}{size}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate registry and referenced image manifests")
    validate.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    validate.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    validate.add_argument("--json", action="store_true")

    list_cmd = subparsers.add_parser("list", help="list registry image manifests")
    list_cmd.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    list_cmd.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    list_cmd.add_argument("--json", action="store_true")

    check = subparsers.add_parser("check", help="check a bench image manifest against local Docker cache")
    check.add_argument("--image-manifest", type=Path, required=True)
    check.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    check.add_argument("--docker-host", default=os.environ.get("DOCKER_HOST", DEFAULT_DOCKER_HOST))
    check.add_argument("--skip-docker", action="store_true", help="validate manifest/tar metadata without Docker")
    check.add_argument("--pull", action="store_true", help="pull internal registry digest refs when missing")
    check.add_argument("--load-fallback", action="store_true", help="docker load verified fallback tar when missing")
    check.add_argument("--run-smoke", action="store_true", help="run image smoke commands after image is present")
    check.add_argument("--fail-on-optional-missing", action="store_true", help="return nonzero when optional image rows have no available refs/cache")
    check.add_argument("--json", action="store_true")

    inventory = subparsers.add_parser("inventory-cache", help="inventory local Docker cache images by repository/tag prefix")
    inventory.add_argument("--prefix", action="append", dest="prefixes", default=[], help="repository/tag prefix to include; repeatable")
    inventory.add_argument("--docker-host", default=os.environ.get("DOCKER_HOST", DEFAULT_DOCKER_HOST))
    inventory.add_argument("--output", type=Path, help="write inventory JSON to this path")
    inventory.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command in {"validate", "list"}:
            summary = validate_registry(args.registry, asset_root=args.asset_root)
            if args.json:
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                _print_registry(summary)
            return 1 if summary["counts"]["missing_manifests"] else 0
        if args.command == "inventory-cache":
            summary = docker_cache_inventory(prefixes=args.prefixes, docker_host=args.docker_host)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if args.json:
                print(json.dumps(summary, indent=2, sort_keys=True))
            else:
                _print_inventory(summary)
            return 0
        summary = check_image_manifest(
            args.image_manifest,
            asset_root=args.asset_root,
            docker_host=args.docker_host,
            skip_docker=args.skip_docker,
            allow_pull=args.pull,
            load_fallback=args.load_fallback,
            run_smoke=args.run_smoke,
            fail_on_optional_missing=args.fail_on_optional_missing,
        )
    except ImageManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        _print_check(summary)
    counts = summary["counts"]
    if counts["errors"] or counts["tar_mismatch"]:
        return 2
    if counts["missing"] or counts["tar_missing"]:
        return 1
    if args.fail_on_optional_missing and counts.get("optional_missing", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
