#!/usr/bin/env python3
"""NL2Repo Path A driver (native qwen-code-in-container).

Evaluates NL2RepoBench (M-A-P) tasks with the SAME native qwen-code mechanism
used by the DeepSWE Path A driver (deepswe_qwencode_driver.py), but adapted to
NL2Repo's 0-to-1 "generate a whole repo from a natural-language spec" task and
its OFFICIAL scoring (a faithful port of NL2RepoBench openhands/post_processor.py).

WHY NL2Repo differs from SWE-bench / DeepSWE (verified against the upstream src):
  - Task = generate a COMPLETE runnable repository FROM SCRATCH given only
    start.md (a natural-language spec). NOT a patch over an existing repo.
  - The base task image
        ghcr.io/multimodal-art-projection/nl2repobench/<task>:1.0
    is a CLEANROOM: /workspace holds the ground-truth tests/ + pyproject.toml +
    requirements-test.txt, but NO reference source (import <pkg> ->
    ModuleNotFoundError). The model must supply the implementation source.
  - Official scoring (openhands/post_processor.py -> post_process_task):
      1. remove_package_files(): strip setup.py / pyproject.toml / setup.cfg /
         requirements*.txt / tox.ini / pytest.ini / poetry.lock / Pipfile* /
         environment.yml / conda-env.yaml / MANIFEST.in from the model workspace.
      2. remove_test_files(): strip the ground-truth paths listed in
         test_files.json (e.g. ["tests"]) from the model workspace.
      3. Build FROM the base image + `COPY workspace /workspace` so the base's
         pyproject.toml + tests SURVIVE and the model only supplies source.
      4. Run test_commands.json (e.g. ["pip install -e .", "pytest ... tests"]).
      5. analyze_pytest_results(): regex "(N) passed/failed/error"; total =
         test_case_count.txt; success_rate = min(passed/total, 1); the per-task
         score = passed count.

Because the base image /workspace LEAKS the expected API via tests/, the AGENT
must NOT see it. The agent runs in the base image with /workspace WIPED to an
empty dir holding only start.md (clean Python 3.12 env: no deps, no tests, no
reference). This matches upstream OpenHands giving the model a clean runtime +
start.md and the instruction "According to the start.md in the workspace,
implement the entire project ...".

The offline scoring container replicates the upstream `COPY workspace /workspace`
via `docker cp <staged>/. <container>:/workspace` (staged = model workspace with
package + test files stripped), runs --network none with the offline wheelhouse
mounted (PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheelhouse) so `pip install -e .`
resolves build backends (flit_core / hatchling / poetry-core / ...) offline.

Modes:
  load  : sha256-verify tar, docker load, ensure ghcr ref present.
  meta  : print task metadata (prompt bytes, test count, commands, test files).
  gold  : grader sanity -- overlay the REFERENCE source (from the gold wheel) and
          score. Proves the offline `pip install -e .` + pytest path reaches a
          high pass rate. Needs NO serving.
  agent : wipe workspace -> native qwen-code (direct to serving) generates the
          repo -> official scoring on the model's output (real pass rate).
  smoke : gold then agent for one task (default).

Additive + self-contained. Independent container names + run dir; only ever
`docker rm -f` / `docker rmi` its OWN nl2repo-pathA resources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# ----------------------------- constants -----------------------------

QWEN_MOUNT = "/opt/qwen-native/.npm-root"
QWEN_PATH_PREFIX = f'export PATH="{QWEN_MOUNT}/node_modules/node/bin:{QWEN_MOUNT}/node_modules/.bin:$PATH"; '

_SHARE = "/mnt/shared-storage-user/mineru2-shared/zengweijun"
DEFAULT_QWEN_ROOT = f"{_SHARE}/nips2026/shared_bench/qwen_native_swebench/.npm-root"
DEFAULT_SRC = f"{_SHARE}/nips2026/bench/sources/NL2RepoBench"
DEFAULT_IMG_DIR = f"{_SHARE}/nips2026/agentic-foundation-model-bench/images/nl2repo"
DEFAULT_MANIFEST = f"{DEFAULT_IMG_DIR}/nl2repo_transport_manifest.jsonl"
DEFAULT_WHEELHOUSE = f"{DEFAULT_IMG_DIR}/wheelhouse"
DEFAULT_GOLD = f"{DEFAULT_IMG_DIR}/gold"
DEFAULT_RUN_ROOT = f"{_SHARE}/nips2026/agentic-foundation-model-bench/nl2repo_pathA/runs"
DEFAULT_BASE_URL = "http://100.100.104.147:30001/v1"
DEFAULT_MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
WORKDIR = "/workspace"

# openhands/post_processor.py :: remove_package_files
PACKAGE_FILES = {
    "setup.py", "pyproject.toml", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "requirements-test.txt", "tox.ini", "pytest.ini",
    "poetry.lock", "Pipfile", "Pipfile.lock", "environment.yml",
    "conda-env.yaml", "manifest.in", "MANIFEST.in",
}

# upstream openhands_app.py :: command (-t ...)
UPSTREAM_INSTRUCTION = (
    "According to the start.md in the workspace, implement the entire project as "
    "per the requirements specified in the document, ensuring that the final "
    "product can be directly run in the current directory. The running "
    "requirements should comply with the <API Usage Guide> section of the "
    "document. Please complete this task step by step."
)


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(*parts: object) -> None:
    print("[nl2repo-pathA]", *parts, flush=True)


def docker_env() -> dict:
    env = dict(os.environ)
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    env.setdefault("DOCKER_HOST", os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock"))
    return env


def run(args: list[str], *, env: dict, timeout: int | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=env, text=True, capture_output=True, timeout=timeout, check=check)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_row(manifest: Path, task: str) -> dict:
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("task") == task:
            return row
    raise RuntimeError(f"task {task!r} not in manifest {manifest}")


# ----------------------------- task metadata -----------------------------

def read_task_meta(src_root: Path, task: str) -> dict:
    """Mirror test_data_service.read_all_test_data() for a single task dir."""
    tdir = src_root / "test_files" / task
    if not tdir.is_dir():
        raise RuntimeError(f"task dir not found: {tdir}")
    start_md = tdir / "start.md"
    count_txt = tdir / "test_case_count.txt"
    commands_json = tdir / "test_commands.json"
    files_json = tdir / "test_files.json"
    for p in (start_md, count_txt, commands_json, files_json):
        if not p.is_file():
            raise RuntimeError(f"missing required task file: {p}")
    test_case_count = int(count_txt.read_text(encoding="utf-8").strip())
    test_shell = json.loads(commands_json.read_text(encoding="utf-8"))
    py_test_file_list = json.loads(files_json.read_text(encoding="utf-8"))
    return {
        "task": task,
        "task_dir": str(tdir),
        "start_md": str(start_md),
        "start_md_bytes": start_md.stat().st_size,
        "test_case_count": test_case_count,
        "test_shell": test_shell,
        "py_test_file_list": py_test_file_list,
    }


# ----------------------------- image (tar -> load) -----------------------------

def ensure_image(row: dict, env: dict, verify_sha: bool = True) -> dict:
    """docker load the transported tar (loads directly as row['ghcr'])."""
    target_ref = row["ghcr"]
    info: dict = {"target_ref": target_ref}
    if run(["docker", "image", "inspect", target_ref], env=env).returncode == 0:
        info["status"] = "already_present"
        return info

    tar = Path(row["tar"])
    if not tar.exists():
        raise RuntimeError(f"transport tar missing: {tar}")
    want_sha = row.get("tar_sha256", "")
    if verify_sha and want_sha:
        t0 = time.time()
        got = sha256_file(tar)
        info["recomputed_sha256"] = got
        info["sha256_seconds"] = round(time.time() - t0, 1)
        if got != want_sha:
            raise RuntimeError(f"tar sha256 mismatch: {got} != {want_sha}")
        info["sha256_verified"] = True

    load = run(["docker", "load", "-i", str(tar)], env=env, timeout=1800)
    if load.returncode != 0:
        raise RuntimeError(f"docker load failed: {(load.stderr or load.stdout)[-500:]}")
    info["load_stdout"] = (load.stdout or "").strip()
    if run(["docker", "image", "inspect", target_ref], env=env).returncode != 0:
        # fall back to retag if the tar loaded under a different ref
        m = re.search(r"Loaded image(?: ID)?:\s*(\S+)", load.stdout or "")
        loaded_ref = m.group(1) if m else ""
        if not loaded_ref:
            raise RuntimeError(f"could not parse loaded ref from: {load.stdout!r}")
        if run(["docker", "tag", loaded_ref, target_ref], env=env).returncode != 0:
            raise RuntimeError(f"retag {loaded_ref}->{target_ref} failed")
        info["retagged_from"] = loaded_ref
    info["status"] = "loaded"
    return info


# ----------------------------- container plumbing -----------------------------

def container_env(base_url: str, model: str) -> dict[str, str]:
    base_host = base_url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    no_proxy_parts = [
        os.environ.get("NO_PROXY", ""),
        "127.0.0.1", "localhost", "::1",
        "10.0.0.0/8", "100.96.0.0/12", "100.100.0.0/16",
        ".pjlab.org.cn", base_host,
    ]
    no_proxy = ",".join(dict.fromkeys(x for part in no_proxy_parts for x in part.split(",") if x))
    return {
        "PATH": f"{QWEN_MOUNT}/node_modules/node/bin:{QWEN_MOUNT}/node_modules/.bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "EMPTY"),
        "OPENAI_MODEL": model,
        "QWEN_DEFAULT_AUTH_TYPE": "openai",
        "QWEN_TELEMETRY_ENABLED": "false",
        "QWEN_TELEMETRY_TARGET": "local",
        "QWEN_CODE_UNATTENDED_RETRY": "0",
        "QWEN_CODE_AUTO_ACCEPT": "true",
        "PAGER": "cat", "MANPAGER": "cat", "LESS": "-R", "TQDM_DISABLE": "1",
        "NO_PROXY": no_proxy, "no_proxy": no_proxy,
    }


def start_agent_container(name: str, image: str, base_url: str, model: str, qwen_root: str, env: dict) -> None:
    """Agent container: default (bridge) network so qwen can reach the serving."""
    run(["docker", "rm", "-f", name], env=env)
    args = ["docker", "run", "-d", "--pull=never", "--name", name, "-w", WORKDIR, "-u", "root"]
    for k, v in container_env(base_url, model).items():
        args.extend(["-e", f"{k}={v}"])
    args.extend(["-v", f"{qwen_root}:{QWEN_MOUNT}:ro", image, "tail", "-f", "/dev/null"])
    r = run(args, env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"agent docker run failed: {(r.stderr or r.stdout)[-500:]}")


def start_score_container(name: str, image: str, wheelhouse: str, env: dict, network: str) -> None:
    """Scoring container: --network none (default) + offline wheelhouse mount."""
    run(["docker", "rm", "-f", name], env=env)
    args = ["docker", "run", "-d", "--name", name, f"--network={network}", "-w", WORKDIR, "-u", "root"]
    for k, v in {
        "PIP_NO_INDEX": "1" if network == "none" else "0",
        "PIP_FIND_LINKS": "/wheelhouse",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONPATH": WORKDIR,
        "PYTHONDONTWRITEBYTECODE": "1",
        "TQDM_DISABLE": "1", "PAGER": "cat",
    }.items():
        args.extend(["-e", f"{k}={v}"])
    if wheelhouse:
        args.extend(["-v", f"{wheelhouse}:/wheelhouse:ro"])
    args.extend([image, "tail", "-f", "/dev/null"])
    r = run(args, env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"score docker run failed: {(r.stderr or r.stdout)[-500:]}")


def dexec(name: str, command: str, env: dict, extra_env: dict[str, str], timeout: int,
          workdir: str = WORKDIR, login: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "exec", "-w", workdir, "-u", "root"]
    for k, v in extra_env.items():
        cmd.extend(["-e", f"{k}={v}"])
    cmd.extend([name, "bash", "-lc" if login else "-c", command])
    return run(cmd, env=env, timeout=timeout)


# ----------------------------- agent (native qwen-code -> serving) -----------------------------

def build_prompt(start_md_text: str) -> str:
    """The model receives start.md (already in /workspace) + the upstream instruction."""
    parts = [
        UPSTREAM_INSTRUCTION,
        "",
        f"The working directory is {WORKDIR}. The natural-language specification is "
        f"in {WORKDIR}/start.md (also inlined below). Create the complete project "
        f"source files directly under {WORKDIR} so that the described package is "
        f"importable and runnable from {WORKDIR}. Do not write test files; the "
        f"grader supplies its own tests.",
        "",
        "<start.md>",
        start_md_text,
        "</start.md>",
        "",
    ]
    return "\n".join(parts).strip() + "\n"


def prepare_agent_workspace(name: str, start_md_host: Path, env: dict) -> None:
    """Wipe /workspace (removes the base image's tests/ + pyproject.toml so the
    agent cannot see the expected API) and seed it with start.md only."""
    ce = container_env(DEFAULT_BASE_URL, DEFAULT_MODEL)
    dexec(name, "rm -rf /workspace && mkdir -p /workspace", env, ce, 120)
    cp = run(["docker", "cp", str(start_md_host), f"{name}:/workspace/start.md"], env=env, timeout=120)
    if cp.returncode != 0:
        raise RuntimeError(f"start.md cp failed: {(cp.stderr or cp.stdout)[-300:]}")


def analyse_stream(stdout: str) -> dict:
    events, assistants, tool_calls, tool_results, errors = 0, 0, 0, 0, 0
    sample: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        events += 1
        t = str(obj.get("type", ""))
        low = json.dumps(obj)[:200].lower()
        if t in ("assistant", "message") or obj.get("role") == "assistant":
            assistants += 1
        if "tool_call" in low or t in ("tool_call", "tool_use") or obj.get("tool"):
            tool_calls += 1
        if "tool_result" in low or t in ("tool_result", "tool"):
            tool_results += 1
        if "error" in t.lower():
            errors += 1
        if len(sample) < 6:
            sample.append(t or obj.get("role", "?"))
    return {
        "json_events": events, "assistant_turns": assistants,
        "tool_calls": tool_calls, "tool_results": tool_results,
        "error_events": errors, "first_event_types": sample,
        "has_real_interaction": events > 1 and (assistants > 0 or tool_calls > 0),
    }


def run_agent(name: str, meta: dict, out_dir: Path, env: dict, base_url: str, model: str,
              turns: int, rollout_timeout: int) -> dict:
    start_md_text = Path(meta["start_md"]).read_text(encoding="utf-8", errors="replace")
    prompt = build_prompt(start_md_text)
    (out_dir / "prompt.txt").write_text(prompt)
    ce = container_env(base_url, model)

    # prove container -> serving path (independent of qwen), same shell conditions
    probe = dexec(name, QWEN_PATH_PREFIX + "node --version; echo '---'; command -v qwen; qwen --version; echo '---'; "
                        f"curl -s --noproxy '*' --max-time 12 {shlex.quote(base_url.rsplit('/v1', 1)[0])}/v1/models | head -c 400 || echo CURL_FAIL",
                  env, ce, 60)
    (out_dir / "container_probe.txt").write_text((probe.stdout or "") + "\n[stderr]\n" + (probe.stderr or ""))

    cp = run(["docker", "cp", str(out_dir / "prompt.txt"), f"{name}:/tmp/nl2repo_prompt.txt"], env=env, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError(f"prompt cp failed: {(cp.stderr or cp.stdout)[-300:]}")

    turns_flag = f"--max-session-turns {turns}" if turns and turns > 0 else ""
    qcmd = QWEN_PATH_PREFIX + (
        "env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY "
        'qwen --channel CI '
        f"--yolo --auth-type openai --openai-base-url {shlex.quote(base_url)} "
        '--openai-api-key "$OPENAI_API_KEY" '
        f"--model {shlex.quote(model)} --output-format stream-json {turns_flag} "
        "< /tmp/nl2repo_prompt.txt"
    ).strip()
    (out_dir / "qwen_command.txt").write_text(qcmd + "\n")

    t0 = time.time()
    timed_out = False
    try:
        proc = dexec(name, qcmd, env, ce, rollout_timeout)
        rc, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out, rc = True, -100
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = (exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")) + f"\n[ROLLOUT_TIMEOUT {rollout_timeout}s]\n"
    dur = round(time.time() - t0, 1)
    (out_dir / "qwen.stdout.jsonl").write_text(stdout, errors="replace")
    (out_dir / "qwen.stderr.txt").write_text(stderr, errors="replace")

    listing = dexec(name, "find /workspace -maxdepth 3 -not -path '*/.git/*' | head -200", env, ce, 60)
    (out_dir / "workspace_listing.txt").write_text(listing.stdout or "")
    turns_info = analyse_stream(stdout)
    (out_dir / "stream_analysis.json").write_text(json.dumps(turns_info, indent=2) + "\n")

    return {
        "agent_rc": rc, "agent_seconds": dur, "timed_out": timed_out,
        "workspace_files": len([x for x in (listing.stdout or "").splitlines() if x.strip()]),
        "stream": turns_info,
    }


# ----------------------------- scoring (official post_processor port) -----------------------------

def stage_workspace_from_container(name: str, staging: Path, env: dict) -> None:
    """docker cp the model's /workspace out to a host staging dir."""
    if staging.exists():
        shutil.rmtree(staging)
    staging.parent.mkdir(parents=True, exist_ok=True)
    cp = run(["docker", "cp", f"{name}:/workspace/.", str(staging)], env=env, timeout=300)
    if cp.returncode != 0:
        raise RuntimeError(f"workspace cp-out failed: {(cp.stderr or cp.stdout)[-300:]}")


def stage_workspace_from_gold(gold_dir: Path, task: str, staging: Path) -> dict:
    """Unzip the reference wheel -> host staging dir (the reference source)."""
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    wheels = sorted((gold_dir / task).glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"no gold wheel for {task} under {gold_dir/task}")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as zf:
        zf.extractall(staging)
    return {"gold_wheel": str(wheel), "extracted": [p.name for p in sorted(staging.iterdir())]}


def strip_workspace(staging: Path, py_test_file_list: list[str]) -> dict:
    """post_processor.remove_package_files + remove_test_files on the staged dir.

    Also removes *.dist-info / *.egg-info build artefacts: with PYTHONPATH=/workspace
    (upstream Dockerfile), a stray dist-info makes `pip install -e .` treat /workspace
    as a site dir, "find existing installation", and UNINSTALL it -- deleting the very
    source .py files it should install. A model source repo never ships these; the
    reference wheel does, so strip them so gold reflects a real source overlay.
    """
    removed_pkg, removed_test, removed_meta = [], [], []
    for meta_dir in list(staging.glob("*.dist-info")) + list(staging.rglob("*.egg-info")):
        try:
            shutil.rmtree(meta_dir)
            removed_meta.append(meta_dir.name)
        except Exception:
            pass
    for root, _dirs, files in os.walk(staging):
        for fn in files:
            if fn in PACKAGE_FILES:
                p = Path(root) / fn
                try:
                    p.unlink()
                    removed_pkg.append(str(p.relative_to(staging)))
                except Exception:
                    pass
    for entry in py_test_file_list:
        target = staging / entry
        try:
            if target.is_dir():
                shutil.rmtree(target)
                removed_test.append(entry + "/")
            elif target.exists():
                target.unlink()
                removed_test.append(entry)
        except Exception:
            pass
    return {"removed_package_files": removed_pkg, "removed_test_files": removed_test,
            "removed_metadata_dirs": removed_meta}


def analyze_pytest(command_results: list[dict], total: int) -> dict:
    passed = failed = errors = 0
    for res in command_results:
        if "pytest" not in res["command"].lower():
            continue
        for line in res["output"].split("\n"):
            m = re.search(r"(\d+) passed", line)
            if m:
                passed += int(m.group(1))
            m = re.search(r"(\d+) failed", line)
            if m:
                failed += int(m.group(1))
            m = re.search(r"(\d+) error", line)
            if m:
                errors += int(m.group(1))
    success_rate = min(passed / total, 1.0) if total > 0 else 0.0
    return {"passed": passed, "failed": failed, "errors": errors, "total": total,
            "success_rate": round(success_rate, 6)}


def run_scoring(image: str, cname: str, staging: Path, meta: dict, out_dir: Path, env: dict,
                wheelhouse: str, network: str, cmd_timeout: int, keep_image: bool) -> dict:
    """Faithful port of post_processor.post_process_task (docker-cp overlay variant).

    Overlay `staging` (model source, package + test files already stripped) onto a
    FRESH base image /workspace (which restores pyproject.toml + tests), then run
    test_commands and parse pytest counts.
    """
    score_env = {"PIP_NO_INDEX": "1" if network == "none" else "0", "PIP_FIND_LINKS": "/wheelhouse",
                 "PYTHONPATH": WORKDIR, "PYTHONDONTWRITEBYTECODE": "1", "TQDM_DISABLE": "1", "PAGER": "cat"}
    start_score_container(cname, image, wheelhouse, env, network)
    try:
        # snapshot the pristine base /workspace (evidence: base supplies tests + pyproject)
        base_ls = dexec(cname, "find /workspace -maxdepth 2 | sort", env, score_env, 60)
        (out_dir / "base_workspace_listing.txt").write_text(base_ls.stdout or "")

        # overlay: docker cp staged/. -> /workspace (base's tests/pyproject survive)
        cp = run(["docker", "cp", f"{str(staging)}/.", f"{cname}:/workspace"], env=env, timeout=300)
        if cp.returncode != 0:
            raise RuntimeError(f"overlay cp failed: {(cp.stderr or cp.stdout)[-300:]}")
        merged_ls = dexec(cname, "find /workspace -maxdepth 2 -not -path '*/.git/*' | sort | head -200", env, score_env, 60)
        (out_dir / "merged_workspace_listing.txt").write_text(merged_ls.stdout or "")

        command_results = []
        for i, command in enumerate(meta["test_shell"]):
            t0 = time.time()
            proc = dexec(cname, command, env, score_env, cmd_timeout)
            out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
            command_results.append({"command": command, "exit_code": proc.returncode,
                                    "seconds": round(time.time() - t0, 1), "output": out})
            (out_dir / f"cmd_{i}.txt").write_text(f"$ {command}\n[rc={proc.returncode}]\n{out}", errors="replace")

        pytest_results = analyze_pytest(command_results, meta["test_case_count"])
        result = {
            "network": network,
            "test_shell": meta["test_shell"],
            "command_exit_codes": [c["exit_code"] for c in command_results],
            "command_seconds": [c["seconds"] for c in command_results],
            "pytest_results": pytest_results,
            "score": pytest_results["passed"],
            "success_rate": pytest_results["success_rate"],
        }
        (out_dir / "score.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        run(["docker", "rm", "-f", cname], env=env)
        if not keep_image:
            run(["docker", "rmi", image], env=env)


# ----------------------------- main -----------------------------

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="NL2Repo Path A driver (native qwen-code-in-container)")
    p.add_argument("--task", required=True)
    p.add_argument("--mode", choices=("load", "meta", "gold", "agent", "smoke"), default="smoke")
    p.add_argument("--src-root", default=DEFAULT_SRC)
    p.add_argument("--img-dir", default=DEFAULT_IMG_DIR)
    p.add_argument("--manifest", default=DEFAULT_MANIFEST)
    p.add_argument("--wheelhouse", default=DEFAULT_WHEELHOUSE)
    p.add_argument("--gold", default=DEFAULT_GOLD)
    p.add_argument("--qwen-root", default=DEFAULT_QWEN_ROOT)
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    p.add_argument("--max-session-turns", type=int, default=40)
    p.add_argument("--rollout-timeout", type=int, default=2400)
    p.add_argument("--cmd-timeout", type=int, default=1800)
    p.add_argument("--score-network", choices=("none", "bridge"), default="none",
                   help="scoring container network; 'none' = offline (default), 'bridge' = allow PyPI fallback")
    p.add_argument("--no-verify-sha", action="store_true")
    p.add_argument("--keep-image", action="store_true", help="do not docker rmi the task image after scoring")
    args = p.parse_args(argv)

    env = docker_env()
    src_root = Path(args.src_root)
    meta = read_task_meta(src_root, args.task)
    manifest = Path(args.manifest)
    row = load_manifest_row(manifest, args.task)

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_root = Path(args.run_root) / f"{args.task}_{args.mode}_{ts}"
    run_root.mkdir(parents=True, exist_ok=True)
    log("RUN_ROOT", run_root)
    log("TASK", args.task, "| ghcr", row["ghcr"], "| tests", meta["test_case_count"],
        "| commands", meta["test_shell"], "| strip", meta["py_test_file_list"])

    summary: dict = {"task": args.task, "mode": args.mode, "ghcr": row["ghcr"],
                     "base_url": args.base_url, "model": args.model,
                     "test_case_count": meta["test_case_count"], "test_shell": meta["test_shell"],
                     "py_test_file_list": meta["py_test_file_list"], "start_md_bytes": meta["start_md_bytes"],
                     "score_network": args.score_network, "run_root": str(run_root), "ts": ts}

    if args.mode == "meta":
        (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        log("META", json.dumps(summary, indent=2))
        return 0

    # image (needed for load / gold / agent / smoke)
    img_info = ensure_image(row, env, verify_sha=not args.no_verify_sha)
    summary["image"] = img_info
    log("IMAGE", img_info.get("status"), "sha_ok=", img_info.get("sha256_verified"))
    if args.mode == "load":
        (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        log("DONE (load only)")
        return 0

    cbase = f"nl2repo-pathA-{args.task}-{ts}".replace("_", "-")[:120]

    # gold grader sanity (no serving) -- overlay reference source, expect high pass
    if args.mode in ("gold", "smoke"):
        gold_dir = run_root / "gold"
        gold_dir.mkdir(parents=True, exist_ok=True)
        staging = run_root / "gold_staging"
        ginfo = stage_workspace_from_gold(Path(args.gold), args.task, staging)
        sinfo = strip_workspace(staging, meta["py_test_file_list"])
        (gold_dir / "stage_info.json").write_text(json.dumps({**ginfo, **sinfo}, indent=2) + "\n")
        score = run_scoring(row["ghcr"], (cbase + "-goldscore")[:120], staging, meta, gold_dir, env,
                            args.wheelhouse, args.score_network, args.cmd_timeout,
                            keep_image=(args.mode == "smoke") or args.keep_image)
        summary["gold"] = {**ginfo, **sinfo, **score}
        log("GOLD", "passed=", score["pytest_results"]["passed"], "/", score["pytest_results"]["total"],
            "failed=", score["pytest_results"]["failed"], "errors=", score["pytest_results"]["errors"],
            "success_rate=", score["success_rate"])

    # agent path (native qwen-code -> serving) -- real model output, real score
    if args.mode in ("agent", "smoke"):
        ag_dir = run_root / "agent"
        ag_dir.mkdir(parents=True, exist_ok=True)
        cagent = (cbase + "-agent")[:120]
        try:
            start_agent_container(cagent, row["ghcr"], args.base_url, args.model, args.qwen_root, env)
            prepare_agent_workspace(cagent, Path(meta["start_md"]), env)
            ag = run_agent(cagent, meta, ag_dir, env, args.base_url, args.model,
                           args.max_session_turns, args.rollout_timeout)
            staging = run_root / "agent_staging"
            stage_workspace_from_container(cagent, staging, env)
        finally:
            run(["docker", "rm", "-f", cagent], env=env)
        sinfo = strip_workspace(staging, meta["py_test_file_list"])
        (ag_dir / "stage_info.json").write_text(json.dumps(sinfo, indent=2) + "\n")
        score = run_scoring(row["ghcr"], (cbase + "-agentscore")[:120], staging, meta, ag_dir, env,
                            args.wheelhouse, args.score_network, args.cmd_timeout, keep_image=args.keep_image)
        summary["agent"] = {**ag, **sinfo, **score}
        log("AGENT", "workspace_files=", ag.get("workspace_files"),
            "assistant_turns=", ag.get("stream", {}).get("assistant_turns"),
            "tool_calls=", ag.get("stream", {}).get("tool_calls"),
            "| passed=", score["pytest_results"]["passed"], "/", score["pytest_results"]["total"],
            "success_rate=", score["success_rate"])

    (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log("SUMMARY", json.dumps(summary, indent=2))
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
