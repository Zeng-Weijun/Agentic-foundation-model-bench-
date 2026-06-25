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
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "agentic_bench.suite.v1"
FORBIDDEN_HOSTS = {"swe_dev", "swe-dev"}
HOST_KEYS = {"controller_host", "remote_host", "execution_host", "worker_host", "default_worker_host"}
SECRET_KEYS = {"api_key", "openai_api_key", "secret", "token", "password"}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "manifests" / "suite.example.yaml"
EXECUTABLE_ADAPTER_STATES = {"wired", "wired_legacy"}


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


def _redact_env(env: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        lowered = key.lower()
        secretish = (
            lowered in {"api_key", "openai_api_key", "token", "secret", "password"}
            or lowered.endswith("_api_key")
            or lowered.endswith("_token")
            or lowered.endswith("_secret")
            or lowered.endswith("_password")
        )
        if secretish:
            if value.startswith("${") and value.endswith("}"):
                redacted[key] = value
            else:
                redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


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
    return ["ssh", *[str(item) for item in ssh_options], worker_host, "bash -lc " + shlex.quote(remote_body)]


def _render_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


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
    execution_kind = str(suite.get("execution_kind", execution.get("kind", "ssh_worker")))
    ssh_options = _require_list(worker.get("ssh_options", []), "worker.ssh_options")
    worker_env = _worker_runtime_env(worker)
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
            command_argv = ["bash", "-lc", remote]
        else:
            raise ConfigError(f"suite.execution_kind must be ssh_worker or local, got {execution_kind!r}")
        notes: list[str] = []
        if adapter_status not in EXECUTABLE_ADAPTER_STATES:
            notes.append(f"adapter {adapter!r} not wired; dry-run records the intended command only")
        if network_policy != "online_allowed":
            notes.append("worker must consume pre-staged assets; no public internet actions are allowed")
        runs.append(
            {
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
        "suite_concurrency": int(max_concurrency or suite.get("concurrency", 1)),
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
    print("")
    for run in plan["runs"]:
        print(f"- {run['bench_id']} [{run['adapter_status']}]")
        print(f"  model: {run['model']['profile_id']} ({run['model']['name']})")
        print(f"  worker_host: {run['worker_host']}")
        print(f"  network_policy: {run['network_policy']}")
        print(f"  docker_host: {run.get('docker_host', '')}")
        print(f"  command_preview: {run['command_preview']}")
        for note in run["notes"]:
            print(f"  note: {note}")


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


def _run_one(run: dict[str, Any], output_root: Path) -> dict[str, Any]:
    bench_id = str(run["bench_id"])
    log_path = output_root / "logs" / f"{bench_id}.log"
    status_path = output_root / "status" / f"{bench_id}.status"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"START {bench_id} {started_at}\n")
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
            result = future.result()
            results.append(result)
            if result["exit_code"] != 0:
                status = 1
            print(f"{result['bench_id']}\t{result['status']}\t{result['log_path']}")
    summary = {"suite_id": plan["suite_id"], "status": status, "results": results}
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        config = load_suite_config(args.suite_yaml)
        only = set(filter(None, [item.strip() for item in args.only.split(",")])) if args.only else None
        plan = build_run_plan(
            config,
            suite_path=args.suite_yaml,
            dry_run=args.dry_run,
            smoke=args.smoke,
            only=only,
            model_profile_override=args.model_profile,
            max_concurrency=args.max_concurrency,
        )
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    if args.emit_plan:
        _write_plan(plan, args.emit_plan)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _print_human(plan)

    if not args.dry_run:
        return _execute_plan(plan, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
