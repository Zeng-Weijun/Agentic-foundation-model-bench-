#!/usr/bin/env python3
"""Check or preload offline Docker image tar files from a manifest."""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "offline_images.example.yaml"
DEFAULT_ASSET_ROOT = Path(
    "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench"
)
DEFAULT_DOCKER_HOST = "unix:///tmp/rl/run/docker.sock"


class ManifestError(ValueError):
    """Raised when the offline image manifest cannot be interpreted."""


def _strip_inline_comment(raw: str) -> str:
    quote: str | None = None
    escaped = False
    for idx, char in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "#" and (idx == 0 or raw[idx - 1].isspace()):
            return raw[:idx].rstrip()
    return raw.rstrip()


def _split_unquoted(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    quote: str | None = None
    escaped = False
    start = 0
    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == delimiter:
            parts.append(text[start:idx].strip())
            start = idx + 1
    parts.append(text[start:].strip())
    return parts


def _split_key_value(text: str, lineno: int) -> tuple[str, str | None]:
    quote: str | None = None
    escaped = False
    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == ":":
            key = text[:idx].strip()
            value = text[idx + 1 :].strip()
            if not key:
                raise ManifestError(f"line {lineno}: empty YAML key")
            return key, value if value else None
    raise ManifestError(f"line {lineno}: expected 'key: value'")


def _looks_like_mapping_item(text: str) -> bool:
    quote: str | None = None
    escaped = False
    for idx, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == ":":
            return idx == len(text) - 1 or text[idx + 1].isspace()
    return False


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value[0], value[-1]) in {("'", "'"), ('"', '"')}:
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_unquoted(inner, ",")]
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?\d+\.\d+", value):
        return float(value)
    return value


def _prepare_yaml_lines(text: str) -> list[tuple[int, str, int]]:
    lines: list[tuple[int, str, int]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise ManifestError(f"line {lineno}: tabs are not supported for indentation")
        stripped = _strip_inline_comment(raw.strip())
        if stripped:
            lines.append((indent, stripped, lineno))
    return lines


def _parse_mapping(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line_indent, text, lineno = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ManifestError(f"line {lineno}: unexpected indentation")
        if text.startswith("- "):
            break
        key, value = _split_key_value(text, lineno)
        index += 1
        if value is None:
            if index < len(lines) and lines[index][0] > indent:
                child, index = _parse_block(lines, index, lines[index][0])
                result[key] = child
            else:
                result[key] = {}
        else:
            result[key] = _parse_scalar(value)
    return result, index


def _parse_sequence(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line_indent, text, lineno = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ManifestError(f"line {lineno}: unexpected sequence indentation")
        if not text.startswith("- "):
            break
        item_text = text[2:].strip()
        index += 1
        if not item_text:
            if index < len(lines) and lines[index][0] > indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
            result.append(item)
            continue
        if _looks_like_mapping_item(item_text):
            key, value = _split_key_value(item_text, lineno)
            item_map: dict[str, Any] = {}
            if value is None:
                if index < len(lines) and lines[index][0] > indent:
                    child, index = _parse_block(lines, index, lines[index][0])
                    item_map[key] = child
                else:
                    item_map[key] = {}
            else:
                item_map[key] = _parse_scalar(value)
            if index < len(lines) and lines[index][0] > indent:
                continuation, index = _parse_mapping(lines, index, lines[index][0])
                item_map.update(continuation)
            result.append(item_map)
        else:
            result.append(_parse_scalar(item_text))
    return result, index


def _parse_block(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    line_indent, text, lineno = lines[index]
    if line_indent != indent:
        raise ManifestError(f"line {lineno}: expected indentation {indent}, got {line_indent}")
    if text.startswith("- "):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def load_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        lines = _prepare_yaml_lines(text)
        if not lines:
            return {}
        parsed, index = _parse_block(lines, 0, lines[0][0])
        if index != len(lines):
            lineno = lines[index][2]
            raise ManifestError(f"line {lineno}: could not parse trailing YAML content")
        return parsed
    return yaml.safe_load(text)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(value: Any) -> list[str]:
    result: list[str] = []
    for item in _as_list(value):
        if item is None:
            continue
        if isinstance(item, (str, int, float)):
            result.append(str(item))
    return result


def _looks_like_placeholder(path_text: str) -> bool:
    lowered = path_text.lower()
    return lowered.startswith("no_") or lowered.startswith("missing_") or " no_" in lowered


def _resolve_path(path_text: str, manifest_dir: Path, asset_root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    asset_path = asset_root / path
    if asset_path.exists() or any(char in path_text for char in "*?["):
        return asset_path
    return manifest_dir / path


def _paths_from_jsonl(path: Path, asset_root: Path) -> list[Path]:
    tar_paths: list[Path] = []
    keys = ("tar", "tar_path", "image_tar", "path", "file", "archive", "archive_path")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return tar_paths
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        for key in keys:
            value = record.get(key)
            if isinstance(value, str) and value.endswith(".tar"):
                candidate = Path(value)
                if not candidate.is_absolute():
                    candidate = (path.parent / candidate) if (path.parent / candidate).exists() else asset_root / candidate
                tar_paths.append(candidate)
    return tar_paths


def resolve_tar_paths(source_paths: list[str], manifest_path: Path, asset_root: Path) -> tuple[list[Path], list[str]]:
    tars: list[Path] = []
    unresolved: list[str] = []
    manifest_dir = manifest_path.parent
    for source in source_paths:
        if _looks_like_placeholder(source):
            unresolved.append(source)
            continue
        resolved = _resolve_path(source, manifest_dir, asset_root)
        if any(char in str(resolved) for char in "*?["):
            matches = sorted(Path(match) for match in glob.glob(str(resolved)))
            tar_matches = [match for match in matches if match.is_file() and match.name.endswith(".tar")]
            if tar_matches:
                tars.extend(tar_matches)
            else:
                unresolved.append(source)
            continue
        if resolved.is_file() and resolved.name.endswith(".jsonl"):
            jsonl_tars = [path for path in _paths_from_jsonl(resolved, asset_root) if path.is_file()]
            if jsonl_tars:
                tars.extend(jsonl_tars)
            else:
                unresolved.append(source)
            continue
        if resolved.is_file() and resolved.name.endswith(".tar"):
            tars.append(resolved)
        else:
            unresolved.append(source)
    unique_tars = list(dict.fromkeys(tars))
    return unique_tars, unresolved


def manifest_entries(config: Any) -> list[dict[str, Any]]:
    if not isinstance(config, dict):
        raise ManifestError("manifest root must be a mapping")
    images = config.get("images")
    if not isinstance(images, list):
        raise ManifestError("manifest must contain an images list")
    entries: list[dict[str, Any]] = []
    for index, raw in enumerate(images, start=1):
        if not isinstance(raw, dict):
            continue
        expected = (
            _string_list(raw.get("expected_tags"))
            or _string_list(raw.get("required_images"))
            or _string_list(raw.get("tags"))
        )
        source_paths = (
            _string_list(raw.get("source_path"))
            or _string_list(raw.get("source_paths"))
            or _string_list(raw.get("tar_paths"))
            or _string_list(raw.get("image_tars"))
        )
        entries.append(
            {
                "id": str(raw.get("id") or raw.get("bench") or f"image_{index}"),
                "bench": raw.get("bench"),
                "expected_tags": expected,
                "source_paths": source_paths,
            }
        )
    return entries


def list_docker_tags(env: dict[str, str]) -> set[str]:
    proc = subprocess.run(
        ["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise ManifestError(proc.stderr.strip() or "docker image ls failed")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip() and "<none>" not in line}


def missing_patterns(expected_tags: list[str], local_tags: set[str]) -> list[str]:
    missing: list[str] = []
    for pattern in expected_tags:
        if any(char in pattern for char in "*?["):
            if not any(fnmatch.fnmatchcase(tag, pattern) for tag in local_tags):
                missing.append(pattern)
        elif pattern not in local_tags:
            missing.append(pattern)
    return missing


def docker_load(tar_path: Path, env: dict[str, str]) -> str:
    proc = subprocess.run(
        ["docker", "load", "-i", str(tar_path)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise ManifestError(proc.stderr.strip() or f"docker load failed for {tar_path}")
    return proc.stdout.strip()


def evaluate(
    manifest_path: Path,
    asset_root: Path,
    docker_host: str,
    mode: str,
    base_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = load_yaml(manifest_path)
    env = dict(base_env or os.environ)
    env["DOCKER_HOST"] = docker_host
    local_tags = list_docker_tags(env)
    entries: list[dict[str, Any]] = []
    counts = {"present": 0, "missing": 0, "loaded": 0, "skipped": 0, "tar_missing": 0, "errors": 0}

    for entry in manifest_entries(config):
        tars, unresolved_sources = resolve_tar_paths(entry["source_paths"], manifest_path, asset_root)
        missing_tags = missing_patterns(entry["expected_tags"], local_tags)
        result = {
            "id": entry["id"],
            "bench": entry["bench"],
            "expected_tags": entry["expected_tags"],
            "missing_tags": missing_tags,
            "tar_paths": [str(path) for path in tars],
            "unresolved_sources": unresolved_sources,
            "loaded_tars": [],
            "status": "",
        }
        if not missing_tags:
            counts["present"] += 1
            counts["skipped"] += 1
            result["status"] = "present"
            entries.append(result)
            continue
        if not tars:
            counts["missing"] += 1
            counts["tar_missing"] += 1
            result["status"] = "missing_no_tar"
            entries.append(result)
            continue
        if mode == "check":
            counts["missing"] += 1
            result["status"] = "missing"
            entries.append(result)
            continue
        try:
            for tar_path in tars:
                docker_load(tar_path, env)
                result["loaded_tars"].append(str(tar_path))
            counts["loaded"] += 1
            result["status"] = "loaded"
        except ManifestError as exc:
            counts["errors"] += 1
            counts["missing"] += 1
            result["status"] = "load_failed"
            result["error"] = str(exc)
        entries.append(result)

    return {
        "manifest": str(manifest_path),
        "asset_root": str(asset_root),
        "docker_host": docker_host,
        "mode": mode,
        "counts": counts,
        "entries": entries,
    }


def print_text_summary(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print(f"Manifest: {summary['manifest']}")
    print(f"Asset root: {summary['asset_root']}")
    print(f"Docker host: {summary['docker_host']}")
    print(f"Mode: {summary['mode']}")
    print(
        "Summary: "
        f"present={counts['present']} "
        f"missing={counts['missing']} "
        f"loaded={counts['loaded']} "
        f"skipped={counts['skipped']} "
        f"tar_missing={counts['tar_missing']} "
        f"errors={counts['errors']}"
    )
    for entry in summary["entries"]:
        print(f"- {entry['id']}: {entry['status']}")
        if entry["missing_tags"]:
            print(f"  missing_tags: {', '.join(entry['missing_tags'])}")
        if entry["loaded_tars"]:
            print(f"  loaded_tars: {', '.join(entry['loaded_tars'])}")
        if entry["unresolved_sources"]:
            print(f"  unresolved_sources: {', '.join(entry['unresolved_sources'])}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--docker-host", default=os.environ.get("DOCKER_HOST", DEFAULT_DOCKER_HOST))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", "--dry-run", dest="mode", action="store_const", const="check")
    mode.add_argument("--load", dest="mode", action="store_const", const="load")
    parser.set_defaults(mode="check")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        summary = evaluate(
            manifest_path=args.manifest,
            asset_root=args.asset_root,
            docker_host=args.docker_host,
            mode=args.mode,
        )
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_text_summary(summary)
    counts = summary["counts"]
    if counts["errors"]:
        return 2
    if args.mode == "check" and (counts["missing"] or counts["tar_missing"]):
        return 1
    if args.mode == "load" and (counts["missing"] or counts["tar_missing"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
