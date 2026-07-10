#!/usr/bin/env python3
"""Terminal-Bench custom agent that drives QwenCode through a Docker exec bridge."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.terminal.tmux_session import TmuxSession

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "qwen_tb21_bridge.py"
QWEN_ROOT_DEFAULT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/.npm-root"
MODEL_DEFAULT = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
BASE_URL_DEFAULT = "http://100.103.228.120:30000/v1"
EXCLUDED_HOST_TOOLS = [
    "Shell",
    "ShellTool",
    "Bash",
    "run_shell_command",
    "WriteFile",
    "write_file",
    "Edit",
    "edit",
    "ReadFile",
    "read_file",
    "ListDirectory",
    "list_directory",
    "GrepSearch",
    "grep_search",
    "Glob",
    "glob",
    "TodoWrite",
    "todo_write",
    "Skill",
    "skill",
    "Agent",
    "agent",
    "WebFetch",
    "web_fetch",
]


class QwenCodeTb21BridgeAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "qwen-code-host-bridge"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_name = str(kwargs.get("model_name") or os.environ.get("TB21_QWENCODE_MODEL") or os.environ.get("OPENAI_MODEL") or MODEL_DEFAULT)
        self.base_url = str(kwargs.get("base_url") or os.environ.get("TB21_QWENCODE_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or BASE_URL_DEFAULT)
        self.qwen_root = str(kwargs.get("qwen_root") or os.environ.get("TB21_QWENCODE_QWEN_ROOT") or os.environ.get("SWEV_QWEN_ROOT") or QWEN_ROOT_DEFAULT)
        self.qwen_code_version = str(kwargs.get("qwen_code_version") or os.environ.get("TB21_QWENCODE_VERSION") or os.environ.get("SWEV_QWEN_CODE_VERSION") or "0.15.6")
        self.max_session_turns = int(kwargs.get("max_session_turns") or os.environ.get("TB21_QWENCODE_MAX_SESSION_TURNS") or os.environ.get("SWEV_QWEN_MAX_SESSION_TURNS") or -1)
        self.max_output_tokens = int(kwargs.get("max_output_tokens") or os.environ.get("TB21_QWENCODE_MAX_OUTPUT_TOKENS") or os.environ.get("SWEV_MAX_OUTPUT_TOKENS") or 65536)
        self.rollout_timeout_sec = int(kwargs.get("rollout_timeout_sec") or os.environ.get("TB21_QWENCODE_ROLLOUT_TIMEOUT_SEC") or os.environ.get("SWEV_ROLLOUT_TIMEOUT") or 7200)
        self.container_workdir = str(kwargs.get("container_workdir") or os.environ.get("TB21_QWENCODE_CONTAINER_WORKDIR") or "/app")
        self.container_user = str(kwargs.get("container_user") or os.environ.get("TB21_QWENCODE_CONTAINER_USER") or "root")

    @property
    def version(self) -> str:
        return self.qwen_code_version

    def _qwen_bin_dir(self) -> str:
        return f"{self.qwen_root}/node_modules/.bin"

    def _node_bin_dir(self) -> str:
        return f"{self.qwen_root}/node_modules/node/bin"

    def _no_proxy(self) -> str:
        base_host = urlparse(self.base_url).hostname or ""
        parts = [
            os.environ.get("NO_PROXY", ""),
            os.environ.get("no_proxy", ""),
            "127.0.0.1",
            "localhost",
            "::1",
            "10.0.0.0/8",
            "100.96.0.0/12",
            "100.103.0.0/16",
            ".pjlab.org.cn",
            base_host,
        ]
        seen: dict[str, None] = {}
        for part in parts:
            for item in part.split(","):
                item = item.strip()
                if item:
                    seen[item] = None
        return ",".join(seen.keys())

    def _build_qwen_env(self, container_name: str, log_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self._node_bin_dir()}:{self._qwen_bin_dir()}:" + env.get("PATH", ""),
                "OPENAI_BASE_URL": self.base_url,
                "OPENAI_API_BASE": self.base_url,
                "OPENAI_API_KEY": env.get("OPENAI_API_KEY", env.get("API_KEY", "EMPTY")),
                "OPENAI_MODEL": self.model_name,
                "QWEN_DEFAULT_AUTH_TYPE": "openai",
                "QWEN_TELEMETRY_ENABLED": "false",
                "QWEN_TELEMETRY_TARGET": "local",
                "QWEN_CODE_UNATTENDED_RETRY": "0",
                "QWEN_CODE_AUTO_ACCEPT": "true",
                "QWEN_CODE_MAX_OUTPUT_TOKENS": str(self.max_output_tokens),
                "TB21_QWENCODE_CONTAINER_NAME": container_name,
                "TB21_QWENCODE_CONTAINER_WORKDIR": self.container_workdir,
                "TB21_QWENCODE_CONTAINER_USER": self.container_user,
                "TB21_QWENCODE_LOG_DIR": str(log_dir),
                "NO_PROXY": self._no_proxy(),
                "no_proxy": self._no_proxy(),
                "PAGER": "cat",
                "MANPAGER": "cat",
                "LESS": "-R",
            }
        )
        return env

    def _write_qwen_settings(self, workdir: Path) -> Path:
        settings_dir = workdir / ".qwen"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings = {
            "tools": {
                "approvalMode": "yolo",
                "discoveryCommand": f"python3 {shlex.quote(str(BRIDGE))} discover",
                "callCommand": str(BRIDGE),
                "exclude": EXCLUDED_HOST_TOOLS,
                "useRipgrep": False,
            },
            "telemetry": {"enabled": False, "target": "local"},
            "context": {
                "fileFiltering": {
                    "enableRecursiveFileSearch": False,
                    "enableFuzzySearch": False,
                }
            },
        }
        path = settings_dir / "settings.json"
        path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _build_prompt(self, instruction: str) -> str:
        rendered = self._render_instruction(instruction)
        return (
            "You are QwenCode running as a command-line agent for a Terminal-Bench 2.1 task.\n"
            "You are NOT running inside the benchmark container. The only valid way to interact with the task is the custom tool run_tb_command, which executes commands inside the live task container.\n"
            "Do not use host shell, host file editing, npm installs, apt installs outside the task, or any public network download.\n"
            "Use run_tb_command to inspect files, edit files, run builds/tests, and verify. Non-zero exit_code from run_tb_command is feedback; continue debugging when useful.\n"
            "When you believe the task is complete, stop after a concise final answer.\n\n"
            "Task instruction:\n"
            f"{rendered}\n"
        )

    def _build_qwen_command(self, prompt: str) -> list[str]:
        cmd = [
            "qwen",
            "--channel",
            "CI",
            "--yolo",
            "--auth-type",
            "openai",
            "--openai-base-url",
            self.base_url,
            "--model",
            self.model_name,
            "--output-format",
            "stream-json",
            "--allowed-tools",
            "run_tb_command",
        ]
        for tool in EXCLUDED_HOST_TOOLS:
            cmd.extend(["--exclude-tools", tool])
        cmd.extend(["--max-session-turns", str(self.max_session_turns)])
        cmd.extend(["--prompt", prompt])
        return cmd

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        container_name = getattr(session.container, "name", "") or getattr(session.container, "id", "")
        if not container_name:
            raise RuntimeError("QwenCode TB2.1 bridge cannot determine task container name")
        log_dir = Path(logging_dir or tempfile.mkdtemp(prefix="tb21-qwencode-logs-"))
        log_dir.mkdir(parents=True, exist_ok=True)
        workdir = log_dir / "qwen_workdir"
        home = log_dir / "qwen_home"
        workdir.mkdir(parents=True, exist_ok=True)
        home.mkdir(parents=True, exist_ok=True)
        self._write_qwen_settings(workdir)
        prompt = self._build_prompt(instruction)
        (log_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        cmd = self._build_qwen_command(prompt)
        redacted_cmd = ["$OPENAI_API_KEY" if part == os.environ.get("OPENAI_API_KEY") else part for part in cmd]
        (log_dir / "qwen_command.json").write_text(json.dumps(redacted_cmd, indent=2) + "\n", encoding="utf-8")
        env = self._build_qwen_env(container_name, log_dir)
        env["HOME"] = str(home)
        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=workdir,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.rollout_timeout_sec,
            )
            (log_dir / "qwen_stdout.jsonl").write_text(proc.stdout or "", encoding="utf-8", errors="replace")
            (log_dir / "qwen_stderr.txt").write_text(proc.stderr or "", encoding="utf-8", errors="replace")
            (log_dir / "qwen_exit.json").write_text(
                json.dumps(
                    {
                        "returncode": proc.returncode,
                        "elapsed_sec": round(time.time() - start, 3),
                        "container": container_name,
                        "model": self.model_name,
                        "base_url": self.base_url,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            failure = FailureMode.NONE if proc.returncode == 0 else FailureMode.UNKNOWN_AGENT_ERROR
            return AgentResult(total_input_tokens=0, total_output_tokens=0, failure_mode=failure)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
            (log_dir / "qwen_stdout.jsonl").write_text(stdout, encoding="utf-8", errors="replace")
            (log_dir / "qwen_stderr.txt").write_text(stderr + f"\n[qwen-tb21-agent] timeout after {self.rollout_timeout_sec}s\n", encoding="utf-8", errors="replace")
            return AgentResult(total_input_tokens=0, total_output_tokens=0, failure_mode=FailureMode.AGENT_TIMEOUT)
