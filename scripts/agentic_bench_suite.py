#!/usr/bin/env python3
"""Dry-run-first suite planner for agentic benchmark YAML configs."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "agentic_bench.suite.v1"
FORBIDDEN_HOSTS = {"swe_dev", "swe-dev"}
HOST_KEYS = {"controller_host", "remote_host", "execution_host", "worker_host", "default_worker_host"}
SECRET_KEYS = {"api_key", "openai_api_key", "secret", "token", "password"}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "manifests" / "suite.example.yaml"
EXECUTABLE_ADAPTER_STATES = {"wired", "wired_legacy"}

READINESS_TARGETS = [
    {
        "target_id": "swebench_verified_multi",
        "label": "SWE-bench Verified multi",
        "aliases": ["swebench_verified_multi", "swe_bench_verified_multi", "swebench_verified", "swe_bench_verified", "swe-bench-verified"],
    },
    {
        "target_id": "terminal_bench_2_1",
        "label": "Terminal Bench 2.1",
        "aliases": ["terminal_bench_2_1", "terminal bench 2.1", "terminal-bench-2.1", "tb2", "tb2_1"],
    },
    {"target_id": "mcp_atlas", "label": "MCP-Atlas", "aliases": ["mcp_atlas", "mcp-atlas", "mcp atlas"]},
    {
        "target_id": "tool_decathlon",
        "label": "Tool-Decathlon",
        "aliases": ["tool_decathlon", "tool-decathlon", "tool decathlon"],
    },
    {"target_id": "tau3_bench", "label": "tau3-bench", "aliases": ["tau3_bench", "tau3-bench", "tau3 bench"]},
    {"target_id": "programbench", "label": "programbench", "aliases": ["programbench", "program_bench"]},
    {"target_id": "repozero", "label": "RepoZero", "aliases": ["repozero", "repozero_py2js", "repozero py2js"]},
    {"target_id": "nl2repo", "label": "NL2Repo", "aliases": ["nl2repo", "nl2_repo"]},
    {"target_id": "deepswe", "label": "DeepSWE", "aliases": ["deepswe", "deep_swe"]},
]


class ConfigError(ValueError):
    """Raised when a suite YAML file violates the launcher contract."""


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
                raise ConfigError(f"line {lineno}: empty YAML key")
            return key, value if value else None
    raise ConfigError(f"line {lineno}: expected 'key: value'")


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
            raise ConfigError(f"line {lineno}: tabs are not supported for indentation")
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
            raise ConfigError(f"line {lineno}: unexpected indentation")
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
            raise ConfigError(f"line {lineno}: unexpected sequence indentation")
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
        if ":" in item_text:
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
        raise ConfigError(f"line {lineno}: expected indentation {indent}, got {line_indent}")
    if text.startswith("- "):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        lines = _prepare_yaml_lines(text)
        if not lines:
            return {}
        parsed, index = _parse_block(lines, 0, lines[0][0])
        if index != len(lines):
            lineno = lines[index][2]
            raise ConfigError(f"line {lineno}: could not parse trailing YAML content")
        return parsed
    return yaml.safe_load(text)


def _walk_config(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            child_path = path + (key_text,)
            if lowered in HOST_KEYS and isinstance(child, str) and child in FORBIDDEN_HOSTS:
                dotted = ".".join(child_path)
                raise ConfigError(f"{dotted} must not use {child!r}; this repo contract targets controller_host=dev")
            if (
                lowered in SECRET_KEYS
                or lowered.endswith("_secret")
                or lowered.endswith("_token")
                or lowered.endswith("_password")
            ):
                if (
                    child not in {"", None, "EMPTY"}
                    and not (isinstance(child, str) and (child.startswith("$") or child.startswith("env:")))
                ):
                    dotted = ".".join(child_path)
                    raise ConfigError(f"{dotted} must not contain a real secret; use an *_env field")
            _walk_config(child, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _walk_config(child, path + (str(idx),))


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be a list")
    return value


def _index_by_id(items: list[Any], name: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_map = _require_mapping(item, name)
        item_id = item_map.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ConfigError(f"{name} entries require a non-empty string id")
        if item_id in result:
            raise ConfigError(f"{name} contains duplicate id {item_id!r}")
        result[item_id] = item_map
    return result


def _model_profiles_map(value: Any) -> dict[str, dict[str, Any]]:
    if isinstance(value, list):
        return _index_by_id(value, "model_profiles")
    if isinstance(value, dict):
        result: dict[str, dict[str, Any]] = {}
        for profile_id, profile in value.items():
            profile_map = _require_mapping(profile, f"model_profiles.{profile_id}")
            copied = dict(profile_map)
            copied.setdefault("id", str(profile_id))
            result[str(profile_id)] = copied
        if not result:
            raise ConfigError("model_profiles must not be empty")
        return result
    raise ConfigError("model_profiles must be a list or mapping")


def _bench_list(config: dict[str, Any]) -> list[Any]:
    benches = config.get("benches")
    if benches is None:
        benches = config.get("benchmarks")
    return _require_list(benches, "benches or benchmarks")


def _validate_config(config: Any) -> dict[str, Any]:
    config_map = _require_mapping(config, "suite config")
    if config_map.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"schema_version must be {SCHEMA_VERSION!r}")
    suite = _require_mapping(config_map.get("suite"), "suite")
    controller_host = suite.get("controller_host", "dev")
    if controller_host != "dev":
        raise ConfigError("suite.controller_host must be dev for this repository contract")
    _model_profiles_map(config_map.get("model_profiles"))
    _index_by_id(_bench_list(config_map), "benches or benchmarks")
    _walk_config(config_map)
    return config_map


def load_suite_config(path: str | Path) -> dict[str, Any]:
    suite_path = Path(path)
    if not suite_path.exists():
        raise ConfigError(f"suite YAML not found: {suite_path}")
    data = _load_yaml(suite_path.read_text(encoding="utf-8"))
    return _validate_config(data)


def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.-")
    return cleaned or "unnamed"


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _model_env_state(profile: dict[str, Any]) -> dict[str, Any]:
    api_key_env = profile.get("api_key_env")
    api_key_value = profile.get("OPENAI_API_KEY")
    if isinstance(api_key_value, str) and api_key_value.startswith("env:"):
        api_key_env = api_key_value.split(":", 1)[1]
    base_url_env = profile.get("base_url_env")
    model_name = profile.get("model_name", profile.get("MODEL_NAME", profile["id"]))
    endpoint = profile.get("base_url", profile.get("OPENAI_BASE_URL"))
    if not endpoint and base_url_env:
        endpoint = f"${{{base_url_env}}}"
    provider = profile.get("provider", "")
    if not provider:
        profile_text = f"{profile['id']} {model_name} {endpoint}".lower()
        if "sglang" in profile_text or "qwen" in profile_text:
            provider = "sglang"
        elif endpoint:
            provider = "openai_compatible_relay"
    api_key_policy = profile.get("api_key_policy")
    if not api_key_policy:
        api_key_policy = "empty_allowed" if api_key_value == "EMPTY" else "env_only"
    required_env = []
    if isinstance(api_key_env, str) and api_key_env:
        required_env.append(api_key_env)
    if isinstance(base_url_env, str) and base_url_env and not profile.get("base_url"):
        required_env.append(base_url_env)
    return {
        "profile_id": profile["id"],
        "name": model_name,
        "provider": provider,
        "endpoint": endpoint or "",
        "base_url_env": base_url_env or "",
        "api_key_env": api_key_env or "",
        "api_key_policy": api_key_policy,
        "api_key_set": bool(api_key_env and os.environ.get(str(api_key_env))),
        "required_env": required_env,
    }


def _model_runtime_env(profile: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    model_name = profile.get("model_name", profile.get("MODEL_NAME"))
    if model_name:
        env["MODEL_NAME"] = str(model_name)
        env.setdefault("OPENAI_MODEL", str(model_name))
    litellm_model = profile.get("litellm_model", profile.get("LITELLM_MODEL"))
    if litellm_model:
        env["LITELLM_MODEL"] = str(litellm_model)
    elif model_name:
        env["LITELLM_MODEL"] = "openai/" + str(model_name)
    base_url = profile.get("base_url", profile.get("OPENAI_BASE_URL"))
    if base_url:
        env["OPENAI_BASE_URL"] = str(base_url)
        env["BASE_URL"] = str(base_url)
    elif profile.get("base_url_env"):
        ref = str(profile["base_url_env"])
        env["OPENAI_BASE_URL"] = "${" + ref + "}"
        env["BASE_URL"] = "${" + ref + "}"
    api_key_value = profile.get("OPENAI_API_KEY")
    if isinstance(api_key_value, str) and api_key_value.startswith("env:"):
        env["OPENAI_API_KEY"] = "${" + api_key_value.split(":", 1)[1] + "}"
    elif api_key_value == "EMPTY":
        env["OPENAI_API_KEY"] = "EMPTY"
    elif profile.get("api_key_env"):
        env["OPENAI_API_KEY"] = "${" + str(profile["api_key_env"]) + "}"
    reasoning_effort = profile.get("reasoning_effort", profile.get("OPENAI_REASONING_EFFORT"))
    if reasoning_effort is not None:
        env["OPENAI_REASONING_EFFORT"] = str(reasoning_effort or "")
        env["REASONING_EFFORT"] = str(reasoning_effort or "")
    temperature = profile.get("temperature", profile.get("TEMPERATURE"))
    if temperature is not None:
        env["TEMPERATURE"] = str(temperature)
    max_tokens = profile.get("max_tokens", profile.get("MAX_TOKENS"))
    if max_tokens is not None:
        env["MAX_TOKENS"] = str(max_tokens)
    max_input_tokens = profile.get("max_input_tokens", profile.get("MAX_INPUT_TOKENS"))
    if max_input_tokens is not None:
        env["MAX_INPUT_TOKENS"] = str(max_input_tokens)
    legacy_profile = profile.get("bench_model_profile", profile.get("BENCH_MODEL_PROFILE"))
    if legacy_profile:
        env["BENCH_MODEL_PROFILE"] = str(legacy_profile)
    return env


def _worker_runtime_env(worker: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    if worker.get("docker_host"):
        env["DOCKER_HOST"] = str(worker["docker_host"])
    if worker.get("tmp_root"):
        env["TMPDIR"] = str(worker["tmp_root"])
    if _bool(worker.get("offline"), default=True):
        env["BENCH_OFFLINE"] = "1"
    if isinstance(worker.get("env"), dict):
        for key, value in worker["env"].items():
            if value is not None:
                env[str(key)] = str(value)
    return env


def _bench_runtime_env(bench: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    if isinstance(bench.get("env"), dict):
        for key, value in bench["env"].items():
            if value is not None:
                env[str(key)] = str(value)
    params = bench.get("params", {})
    if isinstance(params, dict):
        for key, value in params.items():
            if value is None:
                continue
            key_text = str(key)
            if key_text.upper() == key_text and re.fullmatch(r"[A-Z_][A-Z0-9_]*", key_text):
                env[key_text] = str(value)
            else:
                env_key = "BENCH_PARAM_" + re.sub(r"[^A-Za-z0-9]+", "_", key_text).upper().strip("_")
                env[env_key] = str(value)
    return env


def _secretish_key(key: Any) -> bool:
    lowered = str(key).lower()
    return (
        lowered in {"api_key", "openai_api_key", "token", "secret", "password"}
        or lowered.endswith("_api_key")
        or lowered.endswith("_token")
        or lowered.endswith("_secret")
        or lowered.endswith("_password")
    )


_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?P<eq>=)(?P<quote>[\"']?)(?P<value>[^\"'\s;]+)(?P=quote)"
)


def _redact_secret_text(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if not _secretish_key(key):
            return match.group(0)
        raw_value = match.group("value")
        if raw_value.startswith("${") and raw_value.endswith("}"):
            return match.group(0)
        quote = match.group("quote")
        return f"{key}{match.group('eq')}{quote}<redacted>{quote}"

    return _SECRET_ASSIGNMENT_RE.sub(replace, value)


def _redact_env(env: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        if _secretish_key(key):
            if value.startswith("${") and value.endswith("}"):
                redacted[key] = value
            else:
                redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def _redact_secret_values(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            str(child_key): _redact_secret_values(child_value, str(child_key))
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_secret_values(item, key) for item in value]
    if isinstance(value, str):
        if _secretish_key(key):
            if value.startswith("${") and value.endswith("}"):
                return value
            return "<redacted>"
        return _redact_secret_text(value)
    if _secretish_key(key):
        return "<redacted>"
    return value


def _shell_exports(env: dict[str, str]) -> str:
    lines = []
    for key, value in sorted(env.items()):
        if value.startswith("${") and value.endswith("}"):
            lines.append(f"export {key}=\"{value}\"")
        else:
            lines.append(f"export {key}={shlex.quote(value)}")
    return "\n".join(lines)


def _source_env_files(paths: list[Any]) -> str:
    lines = []
    for raw_path in paths:
        path = str(raw_path)
        if path.startswith("~/"):
            shell_path = "${HOME}/" + path[2:]
        else:
            shell_path = shlex.quote(path)
        lines.append(f"[ -f {shell_path} ] && source {shell_path} || true")
    return "\n".join(lines)


def _remote_body(*, bench_root: str, source_env_files: list[Any], runtime_env: dict[str, str], adapter_script: str) -> str:
    script = adapter_script
    if script.startswith("/"):
        run_line = f"exec {shlex.quote(script)}"
    else:
        run_line = f"exec ./{shlex.quote(script)}"
    return "\n".join(
        part
        for part in [
            "set -euo pipefail",
            _source_env_files(source_env_files),
            _shell_exports(runtime_env),
            f"mkdir -p {shlex.quote(runtime_env.get('BENCH_RUN_DIR', '/tmp/agentic-bench-run'))}",
            f"cd {shlex.quote(bench_root)}",
            run_line,
        ]
        if part
    )


def _ssh_command(worker_host: str, ssh_options: list[Any], remote_body: str) -> list[str]:
    return ["ssh", *[str(item) for item in ssh_options], worker_host, "bash -c " + shlex.quote(remote_body)]


def _render_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _image_manifest_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _positive_int(value: Any, *, default: int, field: str) -> int:
    if value is None or value == "":
        return max(1, int(default))
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field} must be a positive integer") from exc
    if parsed < 1:
        raise ConfigError(f"{field} must be a positive integer")
    return parsed


def _optional_positive_int(value: Any, *, field: str) -> int | None:
    if value is None or value == "":
        return None
    return _positive_int(value, default=1, field=field)


def _image_preflight_concurrency(image_config: dict[str, Any], suite_concurrency: int) -> int:
    configured = image_config.get(
        "max_concurrency",
        image_config.get("transport_concurrency", image_config.get("concurrency")),
    )
    default = min(max(1, int(suite_concurrency)), 4)
    return _positive_int(configured, default=default, field="image_preflight.max_concurrency")


def _default_project_root_for_suite(suite_path: str | Path) -> Path:
    parent = Path(suite_path).expanduser().resolve().parent
    if parent.name == "manifests":
        return parent.parent
    return parent


def _resolve_suite_relative_path(value: Any, *, suite_path: str | Path, default: Path) -> str:
    if value is None or value == "":
        path = default
    else:
        path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = Path(suite_path).expanduser().resolve().parent / path
    return str(path.resolve())


def _image_preflight_bool(bench_map: dict[str, Any], image_config: dict[str, Any], bench_key: str, config_key: str) -> bool:
    return _bool(bench_map.get(bench_key, image_config.get(config_key)), default=False)


def _image_preflight_for_bench(
    *,
    bench_map: dict[str, Any],
    image_config: dict[str, Any],
    worker: dict[str, Any],
    bench_root: str,
    worker_host: str,
    ssh_options: list[Any],
    execution_kind: str,
    suite_path: str | Path,
) -> dict[str, Any] | None:
    manifests = _image_manifest_values(bench_map.get("image_manifest") or bench_map.get("image_manifests"))
    if not manifests:
        return None
    policy = str(bench_map.get("image_policy", image_config.get("default_policy", "required")))
    required = policy not in {"optional", "none", "disabled", "skip"}
    project_root = _resolve_suite_relative_path(
        bench_map.get("image_project_root", image_config.get("project_root")),
        suite_path=suite_path,
        default=_default_project_root_for_suite(suite_path),
    )
    asset_root = str(
        bench_map.get(
            "image_asset_root",
            image_config.get(
                "asset_root",
                "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench",
            ),
        )
    )
    docker_host = str(bench_map.get("docker_host", image_config.get("docker_host", worker.get("docker_host", ""))))
    preflight_env = _worker_runtime_env(worker)
    if docker_host:
        preflight_env["DOCKER_HOST"] = docker_host
    allow_pull = _image_preflight_bool(bench_map, image_config, "image_pull", "pull")
    load_fallback = _image_preflight_bool(bench_map, image_config, "image_load_fallback", "load_fallback")
    run_smoke = _image_preflight_bool(bench_map, image_config, "image_run_smoke", "run_smoke")
    fail_on_optional_missing = _bool(
        bench_map.get("image_fail_on_optional_missing", image_config.get("fail_on_optional_missing")),
        default=not required,
    )
    commands: list[dict[str, Any]] = []
    for manifest in manifests:
        check_argv = [
            "python3",
            "scripts/agentic_bench_images.py",
            "check",
            "--image-manifest",
            manifest,
            "--asset-root",
            asset_root,
        ]
        if docker_host:
            check_argv.extend(["--docker-host", docker_host])
        if allow_pull:
            check_argv.append("--pull")
        if load_fallback:
            check_argv.append("--load-fallback")
        if run_smoke:
            check_argv.append("--run-smoke")
        if fail_on_optional_missing and not required:
            check_argv.append("--fail-on-optional-missing")
        if _bool(image_config.get("json"), default=True):
            check_argv.append("--json")
        remote_body = "\n".join(
            part
            for part in [
                "set -euo pipefail",
                _shell_exports(preflight_env),
                f"cd {shlex.quote(project_root)}",
                "exec " + _render_command(check_argv),
            ]
            if part
        )
        if execution_kind == "ssh_worker":
            command_argv = _ssh_command(worker_host, ssh_options, remote_body)
        elif execution_kind == "local":
            command_argv = ["bash", "-c", remote_body]
        else:
            command_argv = check_argv
        commands.append(
            {
                "manifest": manifest,
                "check_argv": check_argv,
                "check_command": _render_command(check_argv),
                "command_argv": command_argv,
                "command": _render_command(command_argv),
                "environment": _redact_env(preflight_env),
            }
        )
    return {
        "schema_version": "agentic_bench.image_preflight.v1",
        "policy": policy,
        "required": required,
        "project_root": project_root,
        "asset_root": asset_root,
        "docker_host": docker_host,
        "environment": _redact_env(preflight_env),
        "allow_pull": allow_pull,
        "load_fallback": load_fallback,
        "run_smoke": run_smoke,
        "fail_on_optional_missing": fail_on_optional_missing,
        "manifest": manifests[0],
        "manifests": manifests,
        "command_argv": commands[0]["command_argv"],
        "command": commands[0]["command"],
        "commands": commands,
    }



def _readiness_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _readiness_target_specs(target_benches: list[str] | None) -> list[dict[str, Any]]:
    known: dict[str, dict[str, Any]] = {}
    for target in READINESS_TARGETS:
        aliases = {_readiness_key(target["target_id"]), _readiness_key(target["label"])}
        aliases.update(_readiness_key(alias) for alias in target.get("aliases", []))
        spec = {"target_id": target["target_id"], "label": target["label"], "aliases": aliases}
        for alias in aliases:
            known[alias] = spec
    if not target_benches:
        return [known[_readiness_key(target["target_id"])] for target in READINESS_TARGETS]
    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in target_benches:
        key = _readiness_key(raw)
        spec = known.get(key, {"target_id": key, "label": str(raw), "aliases": {key}})
        if spec["target_id"] not in seen:
            specs.append(spec)
            seen.add(spec["target_id"])
    return specs


def _bench_readiness_keys(bench: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("id", "benchmark", "adapter"):
        value = bench.get(field)
        if value:
            keys.add(_readiness_key(value))
    for manifest in _image_manifest_values(bench.get("image_manifest") or bench.get("image_manifests")):
        manifest_path = Path(manifest)
        keys.add(_readiness_key(manifest_path.stem))
        keys.add(_readiness_key(str(manifest_path.with_suffix(""))))
    return keys


def _bench_readiness_role(bench: dict[str, Any]) -> str:
    role = str(bench.get("readiness_role", "")).strip().lower()
    if role:
        return role
    bench_id = _readiness_key(bench.get("id", ""))
    adapter = _readiness_key(bench.get("adapter", ""))
    if bench_id.endswith("_image_smoke") or adapter.endswith("_image_smoke"):
        return "image_smoke"
    return "full"


def _bench_specific_readiness_blockers(bench: dict[str, Any], image_config: dict[str, Any]) -> list[str]:
    if _bench_readiness_role(bench) != "full":
        return []
    if "tau3_bench" not in _bench_readiness_keys(bench):
        return []
    params = bench.get("params") or {}
    if not isinstance(params, dict):
        params = {}
    blockers: list[str] = []
    tau3_mode = str(params.get("TAU3_MODE", "")).strip().lower()
    if tau3_mode != "full":
        blockers.append("tau3_full_smoke_mode")
    tau3_limit = str(params.get("TAU3_LIMIT", "")).strip()
    if tau3_limit != "0":
        if tau3_limit:
            blockers.append("tau3_full_limit_set")
        blockers.append("tau3_full_limit_not_disabled")
    image_policy = str(bench.get("image_policy", image_config.get("default_policy", "required"))).strip().lower()
    if image_policy != "required":
        blockers.append("tau3_full_image_policy_not_required")
    return blockers


def _suite_concurrency_settings(config: dict[str, Any], *, max_concurrency: int | None = None) -> tuple[int, int | None]:
    suite = _require_mapping(config.get("suite", {}), "suite")
    suite_concurrency = _positive_int(
        max_concurrency if max_concurrency is not None else suite.get("concurrency", 1),
        default=1,
        field="suite.concurrency",
    )
    proxy_concurrency_ceiling = _optional_positive_int(
        suite.get("proxy_concurrency_ceiling"),
        field="suite.proxy_concurrency_ceiling",
    )
    if proxy_concurrency_ceiling is not None and suite_concurrency > proxy_concurrency_ceiling:
        raise ConfigError(
            f"suite_concurrency {suite_concurrency} exceeds suite.proxy_concurrency_ceiling {proxy_concurrency_ceiling}"
        )
    return suite_concurrency, proxy_concurrency_ceiling


def _resolve_readiness_manifest_path(manifest: str, *, project_root: str | Path) -> Path:
    path = Path(manifest).expanduser()
    if path.is_absolute():
        return path
    return (Path(project_root) / path).resolve()


def _readiness_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _image_has_offline_transport(image: dict[str, Any]) -> bool:
    image_refs = _readiness_list(image.get("image_ref")) + _readiness_list(image.get("image_refs"))
    digest_refs = _readiness_list(image.get("source_repo_digest")) + _readiness_list(image.get("source_repo_digests"))
    has_digest_ref = any("@sha256:" in ref for ref in image_refs + digest_refs)
    has_fallback_sha = bool(image.get("fallback_tar") and image.get("fallback_tar_sha256"))
    return has_digest_ref or has_fallback_sha


def _static_image_manifest_readiness(manifest: str, *, project_root: str | Path) -> dict[str, Any]:
    path = _resolve_readiness_manifest_path(manifest, project_root=project_root)
    result: dict[str, Any] = {
        "manifest": manifest,
        "path": str(path),
        "status": "missing_manifest",
        "blockers": ["image_manifest_missing"],
        "counts": {
            "images": 0,
            "required_images": 0,
            "required_with_offline_transport": 0,
            "required_without_offline_transport": 0,
            "optional_placeholders": 0,
        },
        "required_without_offline_transport_images": [],
    }
    if not path.is_file():
        return result
    data = _require_mapping(_load_yaml(path.read_text(encoding="utf-8")), f"image manifest {manifest}")
    images = _require_list(data.get("images", []), f"image manifest {manifest}.images")
    blockers: list[str] = []
    counts = dict(result["counts"])
    counts["images"] = len(images)
    for raw_image in images:
        image = _require_mapping(raw_image, f"image manifest {manifest}.images")
        image_id = str(image.get("id") or "")
        required = _bool(image.get("required"), default=True)
        transport_text = " ".join(
            str(image.get(key, ""))
            for key in ("image_transport", "registry_status", "fallback_transport", "offline_blocker")
        ).lower()
        if required:
            counts["required_images"] += 1
            if _image_has_offline_transport(image):
                counts["required_with_offline_transport"] += 1
            else:
                counts["required_without_offline_transport"] += 1
                result["required_without_offline_transport_images"].append(
                    {
                        "id": image_id,
                        "role": image.get("role", ""),
                        "local_refs": _readiness_list(image.get("local_ref"))
                        + _readiness_list(image.get("local_refs")),
                        "image_transport": image.get("image_transport", ""),
                        "fallback_transport": image.get("fallback_transport", ""),
                        "offline_blocker": image.get("offline_blocker", ""),
                    }
                )
        elif any(token in transport_text for token in ("todo", "missing", "pending", "none")):
            counts["optional_placeholders"] += 1
    if counts["required_without_offline_transport"]:
        blockers.append("required_image_transport_missing")
    manifest_status = str(data.get("status", "")).lower()
    known_blockers = data.get("known_blockers") or []
    manifest_unmaterialized = (
        counts["required_images"] == 0
        and (counts["optional_placeholders"] or known_blockers or any(token in manifest_status for token in ("missing", "pending", "todo")))
    )
    if manifest_unmaterialized:
        blockers.append("image_manifest_not_materialized")
    result.update(
        {
            "status": "blocked" if blockers else "ready",
            "bench_id": data.get("bench_id", ""),
            "manifest_status": data.get("status", ""),
            "blockers": blockers,
            "counts": counts,
        }
    )
    return result


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _bench_readiness_entry(
    bench: dict[str, Any],
    *,
    suite_path: str | Path,
    image_config: dict[str, Any],
) -> dict[str, Any]:
    bench_id = str(bench.get("id", ""))
    enabled = _bool(bench.get("enabled"), default=True)
    adapter_status = str(bench.get("adapter_status", "todo"))
    adapter_ready = adapter_status in EXECUTABLE_ADAPTER_STATES
    image_manifests = _image_manifest_values(bench.get("image_manifest") or bench.get("image_manifests"))
    project_root = _resolve_suite_relative_path(
        bench.get("image_project_root", image_config.get("project_root")),
        suite_path=suite_path,
        default=_default_project_root_for_suite(suite_path),
    )
    image_reports = [
        _static_image_manifest_readiness(manifest, project_root=project_root) for manifest in image_manifests
    ]
    image_blockers = _unique_preserve_order(
        [blocker for report in image_reports for blocker in report.get("blockers", [])]
    )
    bench_blockers = _bench_specific_readiness_blockers(bench, image_config)
    blockers: list[str] = []
    if not enabled:
        blockers.append("suite_entry_disabled")
    if not adapter_ready:
        blockers.append("adapter_not_wired")
    blockers.extend(image_blockers)
    blockers.extend(bench_blockers)
    return {
        "bench_id": bench_id,
        "benchmark": bench.get("benchmark", bench_id),
        "adapter": bench.get("adapter", ""),
        "readiness_role": _bench_readiness_role(bench),
        "enabled": enabled,
        "adapter_status": adapter_status,
        "adapter_ready": adapter_ready,
        "image_manifests": image_reports,
        "blockers": _unique_preserve_order(blockers),
        "ready": enabled and adapter_ready and not image_blockers and not bench_blockers,
    }


def build_readiness_report(
    config: dict[str, Any],
    *,
    suite_path: str | Path,
    target_benches: list[str] | None = None,
) -> dict[str, Any]:
    targets = _readiness_target_specs(target_benches)
    image_config = _require_mapping(config.get("image_preflight", {}), "image_preflight")
    benches = [_require_mapping(bench, "benches") for bench in _bench_list(config)]
    target_results: list[dict[str, Any]] = []
    counts = {"ready": 0, "blocked": 0, "missing": 0, "total": 0}
    for target in targets:
        aliases = set(target["aliases"])
        matched = [bench for bench in benches if _bench_readiness_keys(bench) & aliases]
        entry_reports = [
            _bench_readiness_entry(bench, suite_path=suite_path, image_config=image_config)
            for bench in matched
        ]
        full_entry_reports = [entry for entry in entry_reports if entry.get("readiness_role") == "full"]
        aggregation_entries = full_entry_reports if full_entry_reports else entry_reports
        enabled_entries = [entry for entry in aggregation_entries if entry["enabled"]]
        wired_entries = [entry for entry in enabled_entries if entry["adapter_ready"]]
        ready_entries = [entry for entry in aggregation_entries if entry["ready"]]
        all_ready_entries = [entry for entry in entry_reports if entry["ready"]]
        blockers: list[str] = []
        if not matched:
            status = "missing"
            blockers.append("missing_suite_entry")
        elif not aggregation_entries:
            status = "blocked"
            blockers.append("no_full_readiness_entry")
        elif ready_entries:
            status = "ready"
        else:
            status = "blocked"
            if not enabled_entries:
                blockers.append("no_enabled_suite_entry")
            if enabled_entries and not wired_entries:
                blockers.append("no_enabled_wired_adapter")
            blockers.extend(blocker for entry in aggregation_entries for blocker in entry["blockers"])
        blockers = _unique_preserve_order(blockers)
        counts[status] += 1
        target_results.append(
            {
                "target_id": target["target_id"],
                "label": target["label"],
                "status": status,
                "blockers": blockers,
                "entry_count": len(entry_reports),
                "aggregation_entry_count": len(aggregation_entries),
                "enabled_entry_count": len(enabled_entries),
                "wired_entry_count": len(wired_entries),
                "ready_entry_count": len(all_ready_entries),
                "aggregation_ready_entry_count": len(ready_entries),
                "entries": entry_reports,
            }
        )
    counts["total"] = len(target_results)
    suite = _require_mapping(config.get("suite", {}), "suite")
    return {
        "schema_version": "agentic_bench.readiness_report.v1",
        "suite_id": suite.get("id", suite.get("id_prefix", "")),
        "suite_path": str(Path(suite_path)),
        "created_at": _utc_now(),
        "counts": counts,
        "targets": target_results,
    }

def _command_preview(
    *,
    adapter_script: str,
    suite_id: str,
    run_id: str,
    mode: str,
    model_profile: str,
    worker_host: str,
    network_policy: str,
    params: dict[str, Any],
    runtime_env: dict[str, str] | None = None,
    dry_run: bool,
) -> str:
    env = {
        "DRY_RUN": "1" if dry_run else "0",
        "BENCH_SUITE_ID": suite_id,
        "BENCH_RUN_ID": run_id,
        "BENCH_MODE": mode,
        "BENCH_MODEL_PROFILE": model_profile,
        "BENCH_WORKER_HOST": worker_host,
        "BENCH_NETWORK_POLICY": network_policy,
    }
    if network_policy != "online_allowed":
        env["BENCH_OFFLINE"] = "1"
    if runtime_env:
        env.update(runtime_env)
    for key, value in sorted(params.items()):
        key_text = str(key)
        if key_text.upper() == key_text and re.fullmatch(r"[A-Z_][A-Z0-9_]*", key_text):
            env[key_text] = str(value)
        else:
            env_key = "BENCH_PARAM_" + re.sub(r"[^A-Za-z0-9]+", "_", key_text).upper().strip("_")
            env[env_key] = str(value)
    assignments = [f"{key}={shlex.quote(value)}" for key, value in env.items()]
    return " ".join(assignments + [shlex.quote(adapter_script)])


def build_run_plan(
    config: dict[str, Any],
    *,
    suite_path: str | Path,
    dry_run: bool = True,
    smoke: bool = False,
    only: set[str] | None = None,
    model_profile_override: str | None = None,
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    suite = _require_mapping(config["suite"], "suite")
    worker = _require_mapping(config.get("worker", {}), "worker")
    execution = _require_mapping(config.get("execution", {}), "execution")
    suite_id = str(suite.get("id", suite.get("id_prefix", "")))
    if not suite_id:
        raise ConfigError("suite requires id or id_prefix")
    mode = "smoke" if smoke else str(suite.get("mode", "smoke"))
    suite_policy = _require_mapping(suite.get("offline_policy", {}), "suite.offline_policy")
    network_policy_default = str(suite_policy.get("network_policy", "offline_or_internal_only"))
    if worker.get("network_policy"):
        network_policy_default = str(worker["network_policy"])
    rootless_default = _bool(suite_policy.get("rootless_required", worker.get("rootless")), default=True)
    default_worker = str(suite.get("default_worker_host", worker.get("host", "worker")))
    model_profiles = _model_profiles_map(config["model_profiles"])
    benches = _bench_list(config)
    suite_path = Path(suite_path)
    created_at = _utc_now()
    source_env_files = _require_list(suite.get("source_env_files", []), "suite.source_env_files")
    bench_root = str(suite.get("bench_root", "/data/nips/bench"))
    run_root = str(suite.get("run_root", suite.get("output_root", "/tmp/agentic-foundation-model-bench/runs")))
    image_preflight_config = _require_mapping(config.get("image_preflight", {}), "image_preflight")
    execution_kind = str(suite.get("execution_kind", execution.get("kind", "ssh_worker")))
    ssh_options = _require_list(worker.get("ssh_options", []), "worker.ssh_options")
    worker_env = _worker_runtime_env(worker)
    suite_concurrency, proxy_concurrency_ceiling = _suite_concurrency_settings(
        config,
        max_concurrency=max_concurrency,
    )
    image_preflight_concurrency = _image_preflight_concurrency(image_preflight_config, suite_concurrency)
    runs: list[dict[str, Any]] = []

    for bench in benches:
        bench_map = _require_mapping(bench, "benches")
        bench_id = str(bench_map["id"])
        if only and bench_id not in only:
            continue
        if not _bool(bench_map.get("enabled"), default=True):
            continue
        profile_id = str(
            model_profile_override
            or bench_map.get("model_profile")
            or suite.get("default_model_profile")
            or config.get("active_model", "")
        )
        if profile_id not in model_profiles:
            raise ConfigError(f"bench {bench_id!r} references unknown model_profile {profile_id!r}")
        worker_host = str(bench_map.get("worker_host", default_worker))
        execution_host = str(bench_map.get("execution_host", worker_host))
        remote_host = str(bench_map.get("remote_host", suite.get("controller_host", "dev")))
        bench_policy = bench_map.get("offline_policy", {})
        if bench_policy == "inherit" or bench_policy is None:
            bench_policy = {}
        bench_policy = _require_mapping(bench_policy, f"benches.{bench_id}.offline_policy")
        network_policy = str(bench_policy.get("network_policy", network_policy_default))
        rootless_required = _bool(bench_policy.get("rootless_required"), default=rootless_default)
        params = bench_map.get("params")
        if params is None:
            env_by_mode = _require_mapping(bench_map.get("env_by_mode", {}), f"benches.{bench_id}.env_by_mode")
            params = env_by_mode.get(mode, {})
        params = _require_mapping(params, f"benches.{bench_id}.params")
        adapter = str(bench_map.get("adapter", bench_map.get("benchmark", bench_id)))
        adapter_script = str(bench_map.get("adapter_script", bench_map.get("script", f"shared/runners/run_{adapter}.sh")))
        adapter_path = (ROOT / adapter_script).resolve() if not adapter_script.startswith("/") else Path(adapter_script)
        adapter_status = str(bench_map.get("adapter_status", "todo"))
        run_id = _slug(f"{suite_id}__{bench_id}__{profile_id}")
        run_dir = str(Path(run_root) / suite_id / bench_id)
        runtime_env = {
            "BENCH_SUITE_ID": suite_id,
            "BENCH_RUN_ID": run_id,
            "BENCH_MODE": mode,
            "BENCH_MODEL_PROFILE": profile_id,
            "BENCH_WORKER_HOST": worker_host,
            "BENCH_NETWORK_POLICY": network_policy,
            "BENCH_RUN_DIR": run_dir,
            "RUN_TAG": suite_id,
        }
        if network_policy != "online_allowed":
            runtime_env["BENCH_OFFLINE"] = "1"
        runtime_env.update(_model_runtime_env(model_profiles[profile_id]))
        runtime_env.update(worker_env)
        bench_runtime_source = dict(bench_map)
        bench_runtime_source["params"] = params
        runtime_env.update(_bench_runtime_env(bench_runtime_source))
        remote = _remote_body(
            bench_root=bench_root,
            source_env_files=source_env_files,
            runtime_env=runtime_env,
            adapter_script=adapter_script,
        )
        if execution_kind == "ssh_worker":
            command_argv = _ssh_command(worker_host, ssh_options, remote)
        elif execution_kind == "local":
            command_argv = ["bash", "-c", remote]
        else:
            raise ConfigError(f"suite.execution_kind must be ssh_worker or local, got {execution_kind!r}")
        notes: list[str] = []
        if adapter_status not in EXECUTABLE_ADAPTER_STATES:
            notes.append(f"adapter {adapter!r} not wired; dry-run records the intended command only")
        if network_policy != "online_allowed":
            notes.append("worker must consume pre-staged assets; no public internet actions are allowed")
        image_preflight = _image_preflight_for_bench(
            bench_map=bench_map,
            image_config=image_preflight_config,
            worker=worker,
            bench_root=bench_root,
            worker_host=worker_host,
            ssh_options=ssh_options,
            execution_kind=execution_kind,
            suite_path=suite_path,
        )
        if image_preflight and image_preflight["required"]:
            notes.append("image preflight required before adapter execution")
        run_manifest = {
            "schema_version": "agentic_bench.run_manifest.v1",
            "run_id": run_id,
            "suite_id": suite_id,
            "bench": bench_map.get("benchmark", bench_id),
            "bench_id": bench_id,
            "mode": mode,
            "controller_host": suite.get("controller_host", "dev"),
            "remote_host": remote_host,
            "execution_host": execution_host,
            "worker_host": worker_host,
            "worker_id": bench_map.get("worker_id", worker.get("id", "")),
            "network_policy": network_policy,
            "worker_network": network_policy,
            "rootless_required": rootless_required,
            "rootless": worker.get("rootless", None),
            "container_engine": worker.get("container_engine", ""),
            "docker_host": worker.get("docker_host", ""),
            "tmp_root": worker.get("tmp_root", ""),
            "run_root": run_root,
            "run_dir": run_dir,
            "bench_root": bench_root,
            "script_path": adapter_script,
            "script_sha256": _sha256_file(adapter_path),
            "created_at": created_at,
            "status": "planned",
            "adapter": adapter,
            "adapter_status": adapter_status,
            "model": _model_env_state(model_profiles[profile_id]),
            "runtime_env": _redact_env(runtime_env),
            "concurrency": int(bench_map.get("concurrency", 1)),
            "params": params,
            "command_preview": _command_preview(
                adapter_script=adapter_script,
                suite_id=suite_id,
                run_id=run_id,
                mode=mode,
                model_profile=profile_id,
                worker_host=worker_host,
                network_policy=network_policy,
                params=params,
                runtime_env=_redact_env(runtime_env),
                dry_run=dry_run,
            ),
            "command_argv": command_argv,
            "command": _render_command(command_argv),
            "notes": notes,
        }
        if image_preflight:
            run_manifest["image_preflight"] = image_preflight
        runs.append(
            run_manifest
        )

    return {
        "schema_version": "agentic_bench.suite_plan.v1",
        "suite_id": suite_id,
        "suite_path": str(suite_path),
        "suite_sha256": _sha256_file(suite_path),
        "created_at": created_at,
        "dry_run": dry_run,
        "mode": mode,
        "controller_host": suite.get("controller_host", "dev"),
        "suite_concurrency": suite_concurrency,
        "proxy_concurrency_ceiling": proxy_concurrency_ceiling,
        "image_preflight_concurrency": image_preflight_concurrency,
        "run_root": run_root,
        "bench_root": bench_root,
        "execution_kind": execution_kind,
        "worker": {
            "id": worker.get("id", ""),
            "host": worker.get("host", ""),
            "rootless": worker.get("rootless", None),
            "container_engine": worker.get("container_engine", ""),
            "docker_host": worker.get("docker_host", ""),
            "tmp_root": worker.get("tmp_root", ""),
            "network_policy": worker.get("network_policy", network_policy_default),
            "ssh_dispatch_path": worker.get("ssh_dispatch_path", ""),
        },
        "offline_policy": suite_policy,
        "runs": runs,
    }


def _print_human(plan: dict[str, Any]) -> None:
    print(f"suite: {plan['suite_id']}")
    print(f"mode: {plan['mode']}")
    print(f"controller_host: {plan['controller_host']}")
    print(f"dry_run: {str(plan['dry_run']).lower()}")
    print(f"suite_concurrency: {plan['suite_concurrency']}")
    if plan.get("proxy_concurrency_ceiling") is not None:
        print(f"proxy_concurrency_ceiling: {plan['proxy_concurrency_ceiling']}")
    print(f"image_preflight_concurrency: {plan.get('image_preflight_concurrency', min(int(plan.get('suite_concurrency', 1)), 4))}")
    print("")
    for run in plan["runs"]:
        print(f"- {run['bench_id']} [{run['adapter_status']}]")
        print(f"  model: {run['model']['profile_id']} ({run['model']['name']})")
        print(f"  worker_host: {run['worker_host']}")
        print(f"  network_policy: {run['network_policy']}")
        print(f"  docker_host: {run.get('docker_host', '')}")
        if run.get("image_preflight"):
            print(f"  image_preflight: {run['image_preflight']['command']}")
        print(f"  command_preview: {run['command_preview']}")
        for note in run["notes"]:
            print(f"  note: {note}")



def _print_readiness_report(report: dict[str, Any]) -> None:
    counts = report["counts"]
    print(f"suite: {report.get('suite_id', '')}")
    print(
        "readiness: "
        f"ready={counts['ready']} "
        f"blocked={counts['blocked']} "
        f"missing={counts['missing']} "
        f"total={counts['total']}"
    )
    print("")
    for target in report["targets"]:
        print(f"- {target['target_id']} [{target['status']}]")
        print(f"  label: {target['label']}")
        print(f"  entries: {target['entry_count']} enabled={target['enabled_entry_count']} wired={target['wired_entry_count']} ready={target['ready_entry_count']}")
        for blocker in target["blockers"]:
            print(f"  blocker: {blocker}")

def _write_plan(plan: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _local_output_root(plan: dict[str, Any], output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir).expanduser()
    run_root = Path(str(plan.get("run_root") or "/tmp/agentic-foundation-model-bench/runs")).expanduser()
    if run_root.is_absolute() and run_root.parent.exists():
        return run_root / str(plan["suite_id"]) / "_controller"
    return Path("/tmp/agentic-foundation-model-bench/runs") / str(plan["suite_id"]) / "_controller"


SSH_OPTIONS_WITH_VALUE = {
    "-b",
    "-c",
    "-D",
    "-E",
    "-F",
    "-I",
    "-i",
    "-J",
    "-L",
    "-l",
    "-m",
    "-O",
    "-o",
    "-p",
    "-Q",
    "-R",
    "-S",
    "-W",
    "-w",
}


LOCAL_DISPATCH_FORBIDDEN_SSH_OPTION_PREFIXES = ("-D", "-F", "-J", "-L", "-R", "-W")
LOCAL_DISPATCH_ALLOWED_SSH_O_OPTIONS = ("batchmode=", "connecttimeout=")

FORBIDDEN_DISPATCH_HOST_KEYS = {"dev", "swe_dev", "swe_dev2", "swe_dev_2", "zwj", "zwj3_image"}
FORBIDDEN_DISPATCH_HOST_FRAGMENTS = ("zwj3-image", "group-ailab-mineruinfra", "group-ailab-sciversealign")


def _load_json_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path).expanduser()
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"could not read dispatch plan {plan_path}: {exc}") from exc
    return _require_mapping(payload, "dispatch plan")


def _ssh_target_from_argv(argv: Any) -> str:
    if not isinstance(argv, list) or not argv or str(argv[0]) != "ssh":
        return ""
    index = 1
    while index < len(argv):
        part = str(argv[index])
        if part == "--":
            index += 1
            break
        if part.startswith("-") and part != "-":
            if part in SSH_OPTIONS_WITH_VALUE:
                index += 2
            else:
                index += 1
            continue
        return part
    if index < len(argv):
        return str(argv[index])
    return ""


def _safe_local_dispatch_o_option(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(LOCAL_DISPATCH_ALLOWED_SSH_O_OPTIONS)


def _validate_local_dispatch_ssh_options(command_argv: Any, *, context: str) -> None:
    if not isinstance(command_argv, list):
        return
    index = 1
    while index < len(command_argv):
        part = str(command_argv[index])
        if part == "--":
            return
        if not part.startswith("-") or part == "-":
            return
        if part.startswith(LOCAL_DISPATCH_FORBIDDEN_SSH_OPTION_PREFIXES):
            raise ConfigError(f"{context} uses ssh option {part!r}, which is not allowed for local dispatch")
        if part == "-o":
            if index + 1 >= len(command_argv):
                raise ConfigError(f"{context} has ssh -o without a value")
            option_value = str(command_argv[index + 1])
            if not _safe_local_dispatch_o_option(option_value):
                raise ConfigError(f"{context} uses ssh -o {option_value!r}, which is not allowed for local dispatch")
            index += 2
            continue
        if part.startswith("-o"):
            option_value = part[2:]
            if not _safe_local_dispatch_o_option(option_value):
                raise ConfigError(f"{context} uses ssh option {part!r}, which is not allowed for local dispatch")
            index += 1
            continue
        if part in SSH_OPTIONS_WITH_VALUE:
            index += 2
        else:
            index += 1


def _forbidden_dispatch_host(value: str) -> bool:
    key = _readiness_key(value)
    lowered = str(value).lower()
    return key in FORBIDDEN_DISPATCH_HOST_KEYS or any(fragment in lowered for fragment in FORBIDDEN_DISPATCH_HOST_FRAGMENTS)


def _validate_local_dispatch_ssh_command(command_argv: Any, *, context: str) -> str:
    _validate_local_dispatch_ssh_options(command_argv, context=context)
    target = _ssh_target_from_argv(command_argv)
    if not target:
        raise ConfigError(f"{context} must be a direct worker ssh command_argv")
    if _forbidden_dispatch_host(target):
        raise ConfigError(f"{context} must target a worker directly; got {target!r}, not dev")
    return target


def _validate_local_dispatch_plan(plan: dict[str, Any], *, dispatch_host: str, allow_dev_dispatch: bool) -> None:
    if plan.get("schema_version") != "agentic_bench.suite_plan.v1":
        raise ConfigError("dispatch plan must have schema_version 'agentic_bench.suite_plan.v1'")
    if not allow_dev_dispatch and _forbidden_dispatch_host(dispatch_host):
        raise ConfigError("local dispatch must be started from the Mac/control plane, not dev")
    if str(plan.get("execution_kind", "ssh_worker")) != "ssh_worker":
        raise ConfigError("local dispatch requires an ssh_worker suite plan")
    runs = _require_list(plan.get("runs"), "dispatch plan.runs")
    for run_index, raw_run in enumerate(runs, start=1):
        run = _require_mapping(raw_run, f"dispatch plan.runs[{run_index}]")
        bench_id = str(run.get("bench_id") or f"run_{run_index}")
        worker_host = str(run.get("worker_host") or "")
        target = _validate_local_dispatch_ssh_command(run.get("command_argv"), context=f"run {bench_id}")
        if worker_host and target != worker_host:
            raise ConfigError(f"run {bench_id} command_argv target {target!r} does not match worker_host {worker_host!r}")
        preflight = run.get("image_preflight")
        if isinstance(preflight, dict):
            for command_index, command in enumerate(preflight.get("commands", []), start=1):
                command_map = _require_mapping(command, f"run {bench_id}.image_preflight.commands[{command_index}]")
                preflight_target = _validate_local_dispatch_ssh_command(
                    command_map.get("command_argv"),
                    context=f"run {bench_id}.image_preflight.commands[{command_index}]",
                )
                if worker_host and preflight_target != worker_host:
                    raise ConfigError(
                        f"run {bench_id}.image_preflight.commands[{command_index}] target {preflight_target!r} "
                        f"does not match worker_host {worker_host!r}"
                    )


def dispatch_plan_from_local_controller(
    plan: dict[str, Any],
    output_dir: str | None,
    *,
    dispatch_host_label: str = "",
    allow_dev_dispatch: bool = False,
) -> int:
    configured_dispatch_host = dispatch_host_label or os.environ.get("AGENTIC_BENCH_LOCAL_DISPATCH_HOST")
    if not configured_dispatch_host and not allow_dev_dispatch:
        raise ConfigError("local dispatch requires an explicit --local-dispatch-host or AGENTIC_BENCH_LOCAL_DISPATCH_HOST")
    dispatch_host = configured_dispatch_host or socket.gethostname()
    dispatch_plan = _redact_secret_values(plan)
    _validate_local_dispatch_plan(dispatch_plan, dispatch_host=dispatch_host, allow_dev_dispatch=allow_dev_dispatch)
    source_controller_host = dispatch_plan.get("controller_host")
    if source_controller_host and str(source_controller_host) != dispatch_host:
        dispatch_plan["source_plan_controller_host"] = source_controller_host
    dispatch_plan["controller_host"] = dispatch_host
    dispatch_plan["dispatch"] = {
        "schema_version": "agentic_bench.local_dispatch.v1",
        "mode": "local_controller",
        "host": dispatch_host,
        "created_at": _utc_now(),
        "requires_direct_worker_ssh": True,
    }
    dispatch_plan["dry_run"] = False
    return _execute_plan(dispatch_plan, output_dir)


def _run_one(run: dict[str, Any], output_root: Path) -> dict[str, Any]:
    bench_id = str(run["bench_id"])
    log_path = output_root / "logs" / f"{bench_id}.log"
    status_path = output_root / "status" / f"{bench_id}.status"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"START {bench_id} {started_at}\n")
        adapter_status = str(run.get("adapter_status", "wired_legacy"))
        if adapter_status not in EXECUTABLE_ADAPTER_STATES:
            ended_at = _utc_now()
            status = "fail:adapter_not_wired"
            handle.write(f"adapter_status {adapter_status} is not executable; use --image-preflight-only for image-only checks\n")
            status_path.write_text(status + "\n", encoding="utf-8")
            return {
                "bench_id": bench_id,
                "status": status,
                "exit_code": 2,
                "started_at": started_at,
                "ended_at": ended_at,
                "log_path": str(log_path),
            }
        preflight = run.get("image_preflight")
        if isinstance(preflight, dict) and preflight.get("required"):
            for command in preflight.get("commands", []):
                handle.write("[image_preflight] " + str(command.get("command", "")) + "\n")
                handle.flush()
                preflight_proc = subprocess.run(
                    command["command_argv"],
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                if preflight_proc.returncode != 0:
                    ended_at = _utc_now()
                    status = f"fail:image_preflight:{preflight_proc.returncode}"
                    status_path.write_text(status + "\n", encoding="utf-8")
                    return {
                        "bench_id": bench_id,
                        "status": status,
                        "exit_code": preflight_proc.returncode,
                        "started_at": started_at,
                        "ended_at": ended_at,
                        "log_path": str(log_path),
                    }
        handle.write(str(run["command"]) + "\n\n")
        handle.flush()
        proc = subprocess.run(run["command_argv"], stdout=handle, stderr=subprocess.STDOUT, check=False)
    ended_at = _utc_now()
    status = "pass" if proc.returncode == 0 else f"fail:{proc.returncode}"
    status_path.write_text(status + "\n", encoding="utf-8")
    return {
        "bench_id": bench_id,
        "status": status,
        "exit_code": proc.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "log_path": str(log_path),
    }


def _cached_preflight_command_returncode(
    command: dict[str, Any],
    handle: Any,
    *,
    command_cache: dict[tuple[str, ...], concurrent.futures.Future[int]] | None,
    command_cache_lock: threading.Lock | None,
) -> int:
    if command_cache is None or command_cache_lock is None:
        proc = subprocess.run(command["command_argv"], stdout=handle, stderr=subprocess.STDOUT, check=False)
        return proc.returncode

    key = tuple(str(part) for part in command["command_argv"])
    owner = False
    with command_cache_lock:
        future = command_cache.get(key)
        if future is None:
            future = concurrent.futures.Future()
            command_cache[key] = future
            owner = True

    if owner:
        try:
            proc = subprocess.run(command["command_argv"], stdout=handle, stderr=subprocess.STDOUT, check=False)
        except BaseException as exc:  # pragma: no cover - preserves waiter behavior on unexpected launcher errors.
            future.set_exception(exc)
            raise
        future.set_result(proc.returncode)
        return proc.returncode

    returncode = future.result()
    handle.write("[image_preflight_cached] " + str(command.get("command", "")) + f" rc={returncode}\n")
    handle.flush()
    return returncode


def _run_image_preflight_one(
    run: dict[str, Any],
    output_root: Path,
    *,
    include_optional: bool,
    fail_on_optional: bool,
    command_cache: dict[tuple[str, ...], concurrent.futures.Future[int]] | None = None,
    command_cache_lock: threading.Lock | None = None,
) -> dict[str, Any]:
    bench_id = str(run["bench_id"])
    preflight = run.get("image_preflight")
    log_path = output_root / "logs" / f"{bench_id}.image_preflight.log"
    status_path = output_root / "status" / f"{bench_id}.image_preflight.status"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()

    result: dict[str, Any] = {
        "bench_id": bench_id,
        "required": False,
        "policy": "none",
        "status": "skipped_no_preflight",
        "exit_code": 0,
        "fatal": False,
        "started_at": started_at,
        "ended_at": started_at,
        "log_path": str(log_path),
    }
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"START image_preflight {bench_id} {started_at}\n")
        if not isinstance(preflight, dict) or not preflight.get("commands"):
            handle.write("no image_preflight commands configured\n")
            status_path.write_text(result["status"] + "\n", encoding="utf-8")
            return result

        required = _bool(preflight.get("required"), default=False)
        policy = str(preflight.get("policy", "required" if required else "optional"))
        result["required"] = required
        result["policy"] = policy
        if not required and not include_optional:
            result["status"] = "skipped_optional"
            ended_at = _utc_now()
            result["ended_at"] = ended_at
            handle.write(f"skipped optional image preflight policy={policy}\n")
            status_path.write_text(result["status"] + "\n", encoding="utf-8")
            return result

        for command in preflight.get("commands", []):
            handle.write("[image_preflight] " + str(command.get("command", "")) + "\n")
            handle.flush()
            returncode = _cached_preflight_command_returncode(
                command,
                handle,
                command_cache=command_cache,
                command_cache_lock=command_cache_lock,
            )
            if returncode != 0:
                ended_at = _utc_now()
                if required:
                    status = f"fail:{returncode}"
                    fatal = True
                else:
                    status = f"optional_fail:{returncode}"
                    fatal = fail_on_optional
                result.update(
                    {
                        "status": status,
                        "exit_code": returncode,
                        "fatal": fatal,
                        "ended_at": ended_at,
                    }
                )
                status_path.write_text(status + "\n", encoding="utf-8")
                return result

    ended_at = _utc_now()
    result.update({"status": "pass", "exit_code": 0, "fatal": False, "ended_at": ended_at})
    status_path.write_text("pass\n", encoding="utf-8")
    return result


def _execute_image_preflights(
    plan: dict[str, Any],
    output_dir: str | None,
    *,
    include_optional: bool = False,
    fail_on_optional: bool = False,
) -> int:
    output_root = _local_output_root(plan, output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_plan(plan, output_root / "run_manifest.json")
    results: list[dict[str, Any]] = []
    suite_workers = max(1, int(plan.get("suite_concurrency", 1)))
    max_workers = max(1, int(plan.get("image_preflight_concurrency", min(suite_workers, 4))))
    command_cache: dict[tuple[str, ...], concurrent.futures.Future[int]] = {}
    command_cache_lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(
                _run_image_preflight_one,
                run,
                output_root,
                include_optional=include_optional,
                fail_on_optional=fail_on_optional,
                command_cache=command_cache,
                command_cache_lock=command_cache_lock,
            ): run
            for run in plan["runs"]
        }
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            results.append(result)
            print(f"{result['bench_id']}\t{result['status']}\t{result['log_path']}")

    order = {str(run["bench_id"]): idx for idx, run in enumerate(plan["runs"])}
    results.sort(key=lambda item: order.get(str(item["bench_id"]), len(order)))
    counts = {
        "pass": 0,
        "fail": 0,
        "optional_fail": 0,
        "skipped_optional": 0,
        "skipped_no_preflight": 0,
    }
    for result in results:
        status = str(result["status"])
        if status == "pass":
            counts["pass"] += 1
        elif status.startswith("optional_fail:"):
            counts["optional_fail"] += 1
        elif status.startswith("fail:"):
            counts["fail"] += 1
        elif status == "skipped_optional":
            counts["skipped_optional"] += 1
        elif status == "skipped_no_preflight":
            counts["skipped_no_preflight"] += 1
    status = 1 if any(_bool(result.get("fatal"), default=False) for result in results) else 0
    summary = {
        "schema_version": "agentic_bench.image_preflight_summary.v1",
        "suite_id": plan["suite_id"],
        "status": status,
        "include_optional": include_optional,
        "fail_on_optional": fail_on_optional,
        "image_preflight_concurrency": max_workers,
        "image_preflight_unique_commands": len(command_cache),
        "counts": counts,
        "results": results,
    }
    _write_plan(summary, output_root / "image_preflight_summary.json")
    return status


def _read_text_if_present(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _run_dir_candidates(run: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    for raw in (run.get("run_dir"), _require_mapping(run.get("runtime_env", {}), "runtime_env").get("BENCH_RUN_DIR")):
        if raw:
            path = Path(str(raw)).expanduser()
            if path not in candidates:
                candidates.append(path)
    return candidates


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _tau3_benchmark_result(run: dict[str, Any]) -> dict[str, Any] | None:
    summary_path: Path | None = None
    summary: dict[str, Any] | None = None
    for run_dir in _run_dir_candidates(run):
        candidate = run_dir / "tau3_result_summary.json"
        loaded = _load_json_file(candidate)
        if loaded is not None:
            summary_path = candidate
            summary = loaded
            break
    if summary_path is None or summary is None:
        return None

    status_text = str(summary.get("status", "")).strip().lower()
    verifier_status = str(summary.get("verifier_status", "")).strip().lower()
    reward = summary.get("reward")
    pass_statuses = {"pass", "passed", "success", "succeeded"}
    passed = status_text in pass_statuses or (not status_text and verifier_status == "passed")
    n_total_trials = _safe_int(summary.get("n_total_trials"))
    n_errors = _safe_int(summary.get("n_errors"))
    successful_eval_trials = _safe_int(summary.get("successful_eval_trials"))
    exception_stats = summary.get("exception_stats")
    if not isinstance(exception_stats, dict):
        exception_stats = {}
    safe_exception_stats = {str(key): _safe_int(value) for key, value in sorted(exception_stats.items())[:8]}
    safe_exception_stats = {key: value for key, value in safe_exception_stats.items() if value is not None}

    result: dict[str, Any] = {
        "parser_status": "parsed",
        "status": "pass" if passed else "fail",
        "metric": "reward" if reward is not None else "native_summary",
        "passed": passed,
        "score_claim_valid": bool(passed and reward is not None),
        "failure_category": "" if passed else "tau3_native_error",
        "short_failure_note": str(summary.get("short_failure_note") or status_text or "tau3 native summary did not pass")[:240],
        "tau3_status": status_text,
        "verifier_status": verifier_status,
    }
    if reward is not None:
        result["reward"] = reward
    if n_total_trials is not None:
        result["n_total_trials"] = n_total_trials
    if n_errors is not None:
        result["n_errors"] = n_errors
    if successful_eval_trials is not None:
        result["successful_eval_trials"] = successful_eval_trials
    if safe_exception_stats:
        result["exception_stats"] = safe_exception_stats

    native_artifacts: list[dict[str, str]] = [
        {
            "role": "tau3_result_summary",
            "path": str(summary_path),
            "status": "parsed",
            "read_policy": "allowlist_json",
        }
    ]
    artifact_manifest = summary_path.parent / "artifact_manifest.json"
    if artifact_manifest.is_file():
        native_artifacts.append(
            {
                "role": "artifact_manifest",
                "path": str(artifact_manifest),
                "status": "referenced_not_read",
                "read_policy": "pointer_only",
            }
        )
    result["_source"] = {"native_artifacts": native_artifacts}
    return result


def _repozero_benchmark_result(log_text: str) -> dict[str, Any] | None:
    all_pass_match = re.search(r"ALL_PASS_CASES\s+(\d+)\s*/\s*(\d+)", log_text)
    tests_match = re.search(r"TESTS\s+(\d+)\s*/\s*(\d+)", log_text)
    if not all_pass_match and not tests_match:
        return None
    tasks_passed = int(all_pass_match.group(1)) if all_pass_match else 0
    tasks_total = int(all_pass_match.group(2)) if all_pass_match else 0
    tests_passed = int(tests_match.group(1)) if tests_match else 0
    tests_total = int(tests_match.group(2)) if tests_match else 0
    passed = bool(tasks_total and tasks_passed == tasks_total and (not tests_total or tests_passed == tests_total))
    failure_note = ""
    failure_match = re.search(r"fail_example[:=]\s*(.+)", log_text)
    if failure_match:
        failure_note = failure_match.group(1).strip()
    elif not passed:
        failure_note = "RepoZero selected case did not pass native tests."
    return {
        "parser_status": "parsed",
        "status": "pass" if passed else "fail",
        "metric": "tests_passed",
        "passed": passed,
        "tasks_passed": tasks_passed,
        "tasks_total": tasks_total,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "score_claim_valid": False,
        "failure_category": "" if passed else "agent_generation_failed",
        "short_failure_note": failure_note,
    }


def _benchmark_result_for_run(run: dict[str, Any], execution_result: dict[str, Any]) -> dict[str, Any]:
    execution_status = "pass" if execution_result.get("exit_code") == 0 else "fail"
    adapter = str(run.get("adapter", run.get("bench", run.get("bench_id", "")))).lower()
    bench_id = str(run.get("bench_id", "")).lower()
    if "tau3" in adapter or "tau3" in bench_id:
        parsed = _tau3_benchmark_result(run)
        if parsed:
            return parsed
    if execution_status != "pass":
        return {
            "parser_status": "not_run",
            "status": "infra_error",
            "metric": "adapter_exit_code",
            "passed": False,
            "score_claim_valid": False,
            "failure_category": "adapter_crash",
            "short_failure_note": f"adapter exited {execution_result.get('exit_code')}",
        }
    log_text = _read_text_if_present(str(execution_result.get("log_path", "")))
    if "repozero" in adapter or "repozero" in bench_id:
        parsed = _repozero_benchmark_result(log_text)
        if parsed:
            return parsed
    return {
        "parser_status": "no_parser",
        "status": "unknown",
        "metric": "none",
        "passed": False,
        "score_claim_valid": False,
        "failure_category": "native_artifact_missing",
        "short_failure_note": "no benchmark result parser is configured for this adapter",
    }


def _attach_benchmark_result(run: dict[str, Any], execution_result: dict[str, Any], output_root: Path) -> dict[str, Any]:
    execution_status = "pass" if execution_result.get("exit_code") == 0 else "fail"
    benchmark_result = _benchmark_result_for_run(run, execution_result)
    source = benchmark_result.pop("_source", None)
    result_doc = {
        "schema_version": "agentic_bench.result.v1",
        "suite_id": run.get("suite_id", ""),
        "run_id": run.get("run_id", ""),
        "bench_id": run.get("bench_id", ""),
        "bench": run.get("bench", ""),
        "adapter": run.get("adapter", ""),
        "execution": {
            "status": execution_status,
            "adapter_status": execution_result.get("status", ""),
            "exit_code": execution_result.get("exit_code"),
            "log_path": execution_result.get("log_path", ""),
            "started_at": execution_result.get("started_at", ""),
            "ended_at": execution_result.get("ended_at", ""),
        },
        "benchmark_result": benchmark_result,
    }
    if source:
        result_doc["source"] = source
    bench_id = _slug(str(run.get("bench_id", "unnamed")))
    result_path = output_root / "results" / f"{bench_id}.result.json"
    _write_plan(result_doc, result_path)
    enriched = dict(execution_result)
    enriched.update(
        {
            "execution_status": execution_status,
            "benchmark_status": benchmark_result["status"],
            "score_claim_valid": _bool(benchmark_result.get("score_claim_valid"), default=False),
            "result_path": str(result_path),
        }
    )
    if benchmark_result.get("failure_category"):
        enriched["failure_category"] = benchmark_result["failure_category"]
    return enriched


def _execute_plan(plan: dict[str, Any], output_dir: str | None) -> int:
    unwired = [run["bench_id"] for run in plan["runs"] if run["adapter_status"] not in EXECUTABLE_ADAPTER_STATES]
    if unwired:
        print("refusing --execute because adapters are not wired: " + ", ".join(unwired), file=sys.stderr)
        return 2
    output_root = _local_output_root(plan, output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_plan(plan, output_root / "run_manifest.json")
    status = 0
    results: list[dict[str, Any]] = []
    max_workers = max(1, int(plan.get("suite_concurrency", 1)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {pool.submit(_run_one, run, output_root): run for run in plan["runs"]}
        for future in concurrent.futures.as_completed(future_map):
            run = future_map[future]
            result = _attach_benchmark_result(run, future.result(), output_root)
            results.append(result)
            if result["exit_code"] != 0:
                status = 1
            print(f"{result['bench_id']}\t{result['status']}\t{result['log_path']}")
    order = {str(run["bench_id"]): idx for idx, run in enumerate(plan["runs"])}
    results.sort(key=lambda item: order.get(str(item["bench_id"]), len(order)))
    summary = {"suite_id": plan["suite_id"], "status": status, "results": results}
    if plan.get("dispatch"):
        summary["dispatch"] = plan["dispatch"]
    _write_plan(summary, output_root / "summary.json")
    return status


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a dry-run-first plan from an agentic bench suite YAML.")
    parser.add_argument("suite_yaml", nargs="?", default=str(DEFAULT_SUITE), help="suite YAML path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="dry_run", action="store_true", help="plan only; do not execute adapters")
    mode.add_argument("--execute", dest="dry_run", action="store_false", help="reserved for wired adapters")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--smoke", action="store_true", help="force smoke mode in the generated plan")
    parser.add_argument("--only", help="comma-separated bench ids to include")
    parser.add_argument("--model-profile", help="override the active model profile for all included benches")
    parser.add_argument("--max-concurrency", type=int, help="override suite concurrency")
    parser.add_argument("--json", action="store_true", help="print the full JSON plan")
    parser.add_argument("--emit-plan", help="write the JSON plan to this path")
    parser.add_argument("--output-dir", help="local/controller output dir for --execute logs and manifests")
    parser.add_argument("--readiness", action="store_true", help="emit a static all-bench readiness report and fail if any selected target is blocked or missing")
    parser.add_argument("--target-benches", help="comma-separated readiness target names; defaults to the tracked agentic bench set")
    parser.add_argument("--image-preflight-only", action="store_true", help="run image preflight commands only; never launch adapters")
    parser.add_argument("--include-optional-image-preflight", action="store_true", help="include optional image preflights in --image-preflight-only")
    parser.add_argument("--fail-on-optional-image-preflight", action="store_true", help="make optional image preflight failures fatal when included")
    parser.add_argument("--dispatch-plan", help="execute a dry-run JSON suite plan from the local control plane using its direct worker ssh command_argv values")
    parser.add_argument("--local-dispatch-host", default="", help="operator-visible local control-plane host label for --dispatch-plan artifacts")
    parser.add_argument("--allow-dev-dispatch", action="store_true", help="override the fail-closed guard that prevents running --dispatch-plan on dev")
    parser.add_argument("--allow-empty-plan", action="store_true", help="allow filters that select zero runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.dispatch_plan:
            plan = _load_json_plan(args.dispatch_plan)
            return dispatch_plan_from_local_controller(
                plan,
                args.output_dir,
                dispatch_host_label=args.local_dispatch_host,
                allow_dev_dispatch=args.allow_dev_dispatch,
            )
        config = load_suite_config(args.suite_yaml)
        if args.readiness:
            _suite_concurrency_settings(config, max_concurrency=args.max_concurrency)
            target_benches = _unique_preserve_order(
                [item.strip() for item in args.target_benches.split(",") if item.strip()]
            ) if args.target_benches else None
            report = build_readiness_report(config, suite_path=args.suite_yaml, target_benches=target_benches)
            if args.emit_plan:
                _write_plan(report, args.emit_plan)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                _print_readiness_report(report)
            return 0 if report["counts"]["blocked"] == 0 and report["counts"]["missing"] == 0 else 1
        only = set(filter(None, [item.strip() for item in args.only.split(",")])) if args.only else None
        plan = build_run_plan(
            config,
            suite_path=args.suite_yaml,
            dry_run=args.dry_run and not args.image_preflight_only,
            smoke=args.smoke,
            only=only,
            model_profile_override=args.model_profile,
            max_concurrency=args.max_concurrency,
        )
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    if not plan["runs"] and not args.allow_empty_plan:
        if args.only:
            print(f"no runs selected for --only {args.only}", file=sys.stderr)
            return 2
        if args.image_preflight_only:
            print("no runs selected for image preflight", file=sys.stderr)
            return 2

    if args.emit_plan:
        _write_plan(plan, args.emit_plan)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _print_human(plan)

    if args.image_preflight_only:
        return _execute_image_preflights(
            plan,
            args.output_dir,
            include_optional=args.include_optional_image_preflight,
            fail_on_optional=args.fail_on_optional_image_preflight,
        )
    if not args.dry_run:
        return _execute_plan(plan, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
