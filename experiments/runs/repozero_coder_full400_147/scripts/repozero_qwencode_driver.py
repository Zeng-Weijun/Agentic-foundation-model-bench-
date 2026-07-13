#!/usr/bin/env python3
"""RepoZero Path A driver (native qwen-code-in-container).

Drives RepoZero **Py2JS** official-400 cases with the SAME native
qwen-code-in-container mechanism used by the DeepSWE Path A driver
(deepswe_qwencode_driver.py) / SWE-V full500 orchestrator, and scores with
RepoZero's OWN official comparison (oracle python-executable stdout vs the
generated JavaScript stdout, normalized-line equality across all testcase
samples -> per-case `all_pass`; aggregate all_pass_rate = the 54.70% anchor
metric).

RepoZero is NOT a repo-patch benchmark. A "case" is `lib/testN.py`: translate
the Python module to a single pure-ESM Node.js `.mjs` and match the oracle's
stdout for every hidden testcase sample. The `repoarena-new` image is the
runtime+scoring sandbox (node 18 + the compiled oracle executables), NOT a
per-task repo image.

Mirrors DeepSWE Path A (proven plumbing):
  - `docker run -d --pull=never ... -v <qwen_npm_root>:/opt/qwen-native/.npm-root:ro
     <image> tail -f /dev/null`  (qwen installed tree mounted read-only)
  - qwen runs NATIVELY inside the container and talks to SERVING directly:
        qwen --channel CI -p "<prompt>" --yolo --auth-type openai \
             --openai-base-url <SERVING> --openai-api-key "$OPENAI_API_KEY" \
             --model <MODEL> --output-format stream-json --max-session-turns N
    -> no host bridge, no tool restriction (--yolo), direct to SERVING.

Adapted from tools_repozero_codex_full.py (RepoZero specifics):
  - case source: run_py2js_docker/run_all_docker.py `valid_ids` (official 400).
  - per-case container mounts dataset lib dir ro + a host output dir rw.
  - white-box examples: run the compiled oracle for up to N sample arg-sets.
  - scoring (eval_case): for every testcase sample, run oracle executable and
    `node <entry>.mjs` inside the container and compare normalized stdout lines;
    all_pass = every sample matches (>0 samples). This is RepoZero's real judge.

KEY DIFFERENCE vs codex runner: the codex line ran codex ON THE HOST with
`--network none` on the container (agent could not reach the net). Here qwen
runs INSIDE the container and MUST reach SERVING, so the container uses the
default bridge (NO --network none). Anti-cheat (no npm install of the real lib)
is preserved by the offline pod environment + the prompt contract, not by
--network none.

AUDIT CORRECTION (A+B review, 2026-07-13): the eval judge does NOT use the
image's native node. `start_container` sets the container PATH to the mounted
qwen tree (see `container_env`: PATH="<QWEN_MOUNT>/node_modules/node/bin:..."),
and `dexec_plain` runs `docker exec` WITHOUT overriding PATH, so the eval's
`node <entry>.mjs` resolves to the mounted qwen node **v20.20.2 (OpenSSL 3.0.19)**,
NOT the image's native node **v18.19.1 (OpenSSL 3.0.13)**. The full-400 run and
its official 5s re-judge both scored on qwen node v20 (consistent within the run).
The node seam is immaterial to the headline: re-scoring the 10 crypto/RSA cases
under image node-18 leaves 9/10 unchanged; only rsa/test11 flips (a legacy SHA-1
digest name node18 rejects but node20 accepts) -> worst case 97/400 = 24.25%
(a 0.25pp node seam). See AUDIT_NOTES.md.

Modes:
  load    : ensure repoarena-new image present (docker load offline from the
            shared tar, retag to canonical ref), no container.
  grader  : start container, drop a KNOWN-GOOD reference .mjs (e.g. a prior
            all_pass output) into the output pkg dir, run the judge -> expect
            all_pass=1. Proves the grader is REAL and needs NO serving. Also
            runs a broken (empty) .mjs -> expect all_pass=0 to show it
            discriminates.
  agent   : start container, run qwen-code (direct to SERVING) -> collect the
            generated .mjs -> run the judge -> real all_pass reward.
  smoke   : grader (if --reference-mjs given) + agent for one case (default).

This file is additive and self-contained. It does not import or modify any
running orchestrator, and it uses independent container names + run dir.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

QWEN_MOUNT = "/opt/qwen-native/.npm-root"
# Defensive: if the image's /etc/profile resets PATH (login shell), re-prepend
# the mounted qwen/node bins so `qwen` resolves. Only used for the qwen agent.
QWEN_PATH_PREFIX = f'export PATH="{QWEN_MOUNT}/node_modules/node/bin:{QWEN_MOUNT}/node_modules/.bin:$PATH"; '

DEFAULT_QWEN_ROOT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/qwen_native_swebench/.npm-root"
DEFAULT_RZ_ROOT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero"
DEFAULT_SHARED_TAR = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar"
# canonical ref the codex runner + eval expect; retag the loaded image to this.
DEFAULT_IMAGE = "ghcr.io/jessezzzzz/repoarena-new:latest"
DEFAULT_BASE_URL = "http://100.100.104.147:30001/v1"
DEFAULT_MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
DEFAULT_RUNS_ROOT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs"

CONTAINER_DATASET = "/workspace/dataset"
CONTAINER_OUTPUT = "/workspace/output"

# Forbidden-shortcut hints (from tools_repozero_codex_full.py) — keep the agent
# from importing an external equivalent of the target library.
PYTHON_TO_JS_HINTS = {
    "base58": "Uint8Array / Buffer only; implement Base58 manually",
    "bech32": "Uint8Array / DataView only; implement Bech32 manually",
    "bencoder": "Uint8Array / Buffer only; implement bencode manually",
    "rlp": "Uint8Array / Buffer only; implement Recursive Length Prefix manually",
    "canonicaljson": "JSON.stringify and custom deterministic sorting only",
    "bidict": "Map only; implement bidirectional mapping manually",
    "bitarray": "Uint8Array / BigInt / bitwise operators only",
    "bitstring": "Buffer / Uint8Array / DataView only",
    "construct": "DataView / ArrayBuffer only; implement parsing manually",
    "ecdsa": "node:crypto only; implement glue manually",
    "rsa": "node:crypto only; implement RSA behavior manually",
    "jose": "node:crypto only; implement JOSE/JWT behavior manually",
    "pbkdf2": "node:crypto pbkdf2/pbkdf2Sync only",
    "pyaes": "Uint8Array / Buffer only; implement AES behavior manually",
    "fractions": "BigInt / Number only; implement rational arithmetic manually",
    "mpmath": "BigInt / Number only; implement math behavior manually",
    "moneyed": "Intl.NumberFormat / BigInt only",
    "idna": "node:punycode / URL built-ins only",
    "markdown": "RegExp / string processing only; implement markdown behavior manually",
    "sqlparse": "RegExp / string processing only; implement SQL tokenization manually",
    "yaml": "RegExp / string processing only; implement YAML behavior manually",
    "boltons": "standard JS collections only; implement utility behavior manually",
    "deepdiff": "standard JS objects/arrays only; implement diff behavior manually",
    "furl": "URL and URLSearchParams built-ins only",
    "jsonschema": "standard JS only; implement validator behavior manually",
    "networkx": "Map / Set / Array only; implement graph algorithms manually",
    "schedule": "Date / timers not required; implement schedule formatting manually",
    "whoosh": "RegExp / string processing only; implement search/parser behavior manually",
}


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(*parts: object) -> None:
    print("[repozero-pathA]", *parts, flush=True)


def docker_env() -> dict:
    env = dict(os.environ)
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(k, None)
    env.setdefault("DOCKER_HOST", os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock"))
    return env


def run(argv: list[str], *, env: dict, timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, env=env, text=True, capture_output=True, timeout=timeout)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def args_from_params(params: dict) -> list[str]:
    args: list[str] = []
    for key, value in params.items():
        args.extend([f"--{key}", str(value)])
    return args


def normalized_lines(text: str) -> list[str]:
    return ["".join(line.split()) for line in text.strip().splitlines() if line.strip()]


# ----------------------------- case source -----------------------------

def parse_official_cases(rz_root: Path) -> list[str]:
    """official 400 valid_ids from run_py2js_docker/run_all_docker.py."""
    script = rz_root / "run_py2js_docker" / "run_all_docker.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    values: dict = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"valid_ids", "excluded_ids"}:
                values[target.id] = ast.literal_eval(node.value)
    return list(values["valid_ids"])


def load_jsonl_cases(jsonl_path: Path, case: str) -> list[dict]:
    rows = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("filename") == case:
                obj.pop("filename", None)
                rows.append(obj)
    return rows


# ----------------------------- image -----------------------------

def ensure_image(image_ref: str, shared_tar: str, env: dict, verify_sha: bool = True) -> dict:
    """docker load repoarena-new from the offline shared tar; retag to image_ref."""
    info: dict = {"image_ref": image_ref}
    if run(["docker", "image", "inspect", image_ref], env=env).returncode == 0:
        info["status"] = "already_present"
        return info

    tar = Path(shared_tar)
    if not tar.exists():
        raise RuntimeError(f"shared tar missing: {tar}  (transport to Harbor also available)")
    sidecar = Path(str(tar) + ".sha256")
    if sidecar.exists():
        info["sidecar_sha256"] = sidecar.read_text().strip().split()[0]
    if verify_sha and sidecar.exists():
        t0 = time.time()
        got = sha256_file(tar)
        info["recomputed_sha256"] = got
        info["sha256_seconds"] = round(time.time() - t0, 1)
        if got != info["sidecar_sha256"]:
            raise RuntimeError(f"tar sha256 mismatch: {got} != {info['sidecar_sha256']}")
        info["sha256_verified"] = True

    load = run(["docker", "load", "-i", str(tar)], env=env, timeout=1800)
    if load.returncode != 0:
        raise RuntimeError(f"docker load failed: {(load.stderr or load.stdout)[-500:]}")
    info["load_stdout"] = (load.stdout or "").strip()
    m = re.search(r"Loaded image(?: ID)?:\s*(\S+)", load.stdout or "")
    loaded_ref = m.group(1) if m else ""
    info["loaded_ref"] = loaded_ref

    if run(["docker", "image", "inspect", image_ref], env=env).returncode == 0:
        info["status"] = "loaded_ref_is_target"
        return info
    if not loaded_ref:
        raise RuntimeError(f"could not parse loaded ref from: {load.stdout!r}")
    if run(["docker", "tag", loaded_ref, image_ref], env=env).returncode != 0:
        raise RuntimeError("retag failed")
    if run(["docker", "image", "inspect", image_ref], env=env).returncode != 0:
        raise RuntimeError(f"image ref missing after retag: {image_ref}")
    info["status"] = "loaded_and_retagged"
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


def start_container(name: str, image: str, dataset_dir: Path, output_root: Path,
                    qwen_root: str, base_url: str, model: str, env: dict) -> None:
    run(["docker", "rm", "-f", name], env=env)
    # default bridge network (NO --network none) so in-container qwen reaches SERVING.
    args = ["docker", "run", "-d", "--pull=never", "--name", name, "-u", "root", "-w", CONTAINER_OUTPUT]
    for k, v in container_env(base_url, model).items():
        args.extend(["-e", f"{k}={v}"])
    args.extend([
        "-v", f"{dataset_dir}:{CONTAINER_DATASET}:ro",
        "-v", f"{output_root}:{CONTAINER_OUTPUT}:rw",
        "-v", f"{qwen_root}:{QWEN_MOUNT}:ro",
        image, "tail", "-f", "/dev/null",
    ])
    r = run(args, env=env, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"docker run failed: {(r.stderr or r.stdout)[-500:]}")


def dexec_plain(name: str, argv: list[str], env: dict, timeout: int, workdir: str | None = None) -> subprocess.CompletedProcess:
    """Exec with the container's default env (no per-exec -e overrides) — for oracle + eval + probes.
    NOTE (audit correction): because start_container set the container PATH to the mounted qwen
    tree, `node` here resolves to the mounted qwen node v20.20.2, NOT the image's native node
    v18.19.1. See the module docstring + AUDIT_NOTES.md (node seam, immaterial to the headline)."""
    cmd = ["docker", "exec"]
    if workdir:
        cmd.extend(["-w", workdir])
    cmd.extend([name] + argv)
    return run(cmd, env=env, timeout=timeout)


def dexec_qwen(name: str, command: str, env: dict, base_url: str, model: str, timeout: int,
               workdir: str = CONTAINER_OUTPUT, login: bool = False) -> subprocess.CompletedProcess:
    """Exec with the qwen container_env injected — for the qwen agent + qwen probes."""
    cmd = ["docker", "exec", "-w", workdir, "-u", "root"]
    for k, v in container_env(base_url, model).items():
        cmd.extend(["-e", f"{k}={v}"])
    cmd.extend([name, "bash", "-lc" if login else "-c", command])
    return run(cmd, env=env, timeout=timeout)


# ----------------------------- prompt -----------------------------

def build_prompt(case: str, py_source: str, exe_name: str, whitebox: list[dict],
                 container_pkg_dir: str, entry_name: str, hint: str) -> str:
    # AUDIT NOTE: the line below tells the agent "native Node.js 18 is on PATH".
    # That label is inaccurate — start_container puts the mounted qwen node v20.20.2
    # first on PATH, so the agent (and the eval) actually run node v20, not v18.
    # Left verbatim to match the frozen run prompts; the node seam is immaterial
    # (0.25pp). See the module docstring + AUDIT_NOTES.md.
    return f"""You are running one RepoZero Py2JS benchmark case natively with qwen-code.

Case: {case}

Python source (this is the reference behavior you must reproduce):
```python
{py_source}
```

Oracle executable (already inside this container):
{CONTAINER_DATASET}/{exe_name}
Run it to inspect reference behavior, e.g.:
  {CONTAINER_DATASET}/{exe_name} --arg value

White-box examples from the hidden test distribution (oracle outputs):
```json
{json.dumps(whitebox, ensure_ascii=False, indent=2)}
```

Task:
- Reimplement the behavior in pure JavaScript for Node.js as ES Modules.
- Write all generated files under exactly this directory (your current working dir):
  {container_pkg_dir}
- The entry point MUST be exactly:
  {container_pkg_dir}/{entry_name}
- Use `.mjs` files, `import` / `export`, and full `.mjs` extensions in local imports.
- Parse CLI arguments from `process.argv` so `node {entry_name} --arg value` matches the oracle executable.
- Match stdout semantics and formatting. Newline/space differences are normalized away, but token content and line count must match.
- Use NO npm packages and do NOT use CommonJS (`require`/`module.exports`).
- Do NOT call Python, the oracle executable, or any wrapper from the final JavaScript implementation.
- Do NOT import or mention an external equivalent of this library. Forbidden shortcut hint: {hint}.
- You may run the oracle executable ({CONTAINER_DATASET}/{exe_name}) during development to inspect behavior.
- You may run `node {entry_name} --arg value` to test your implementation (native Node.js 18 is on PATH).

Finish only after {entry_name} exists in {container_pkg_dir} and you have tested at least the white-box examples.
"""


# ----------------------------- judge (RepoZero official comparison) -----------------------------

def build_whitebox(name: str, exe_name: str, samples: list[dict], env: dict, limit: int = 4) -> list[dict]:
    examples = []
    for params in samples[:limit]:
        args = args_from_params(params)
        r = dexec_plain(name, [f"{CONTAINER_DATASET}/{exe_name}"] + args, env, timeout=10)
        examples.append({"args": args, "returncode": r.returncode,
                         "stdout": r.stdout or "", "stderr": (r.stderr or "")[:500]})
    return examples


def eval_case(name: str, rz_root: Path, case: str, out_dir: Path, env: dict, eval_timeout: int = 10) -> dict:
    """RepoZero official judge: oracle-executable stdout vs generated-JS stdout,
    normalized-line equality across EVERY testcase sample -> per-case all_pass."""
    lib, filename = case.split("/")
    stem = filename[:-3] if filename.endswith(".py") else filename
    exe_name = stem + "_executable"
    entry_name = stem + ".mjs"
    pkg_name = stem + "_pkg"
    container_pkg_dir = f"{CONTAINER_OUTPUT}/packages/{lib}/{pkg_name}"

    testcase_file = rz_root / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    samples = load_jsonl_cases(testcase_file, case)

    # entry existence checked inside the container (bind-mounted output)
    exists = dexec_plain(name, ["test", "-f", f"{container_pkg_dir}/{entry_name}"], env, timeout=30).returncode == 0
    if not exists:
        result = {"case": case, "entry": f"{container_pkg_dir}/{entry_name}", "passed": 0,
                  "total": len(samples), "all_pass": False,
                  "fail_examples": [{"error": "missing generated entry file"}],
                  "reward": 0, "reward_source": "RepoZero eval_case (oracle vs node, normalized lines)"}
        (out_dir / "judge.result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result

    passed = 0
    details: list[dict] = []
    for params in samples:
        args = args_from_params(params)
        py = dexec_plain(name, [f"{CONTAINER_DATASET}/{exe_name}"] + args, env, timeout=eval_timeout)
        js = dexec_plain(name, ["node", entry_name] + args, env, timeout=eval_timeout, workdir=container_pkg_dir)
        ok = py.returncode == 0 and js.returncode == 0 and normalized_lines(py.stdout or "") == normalized_lines(js.stdout or "")
        if ok:
            passed += 1
        elif len(details) < 5:
            details.append({"args": args, "oracle_rc": py.returncode, "js_rc": js.returncode,
                            "oracle_stdout": (py.stdout or "")[:400], "js_stdout": (js.stdout or "")[:400],
                            "js_stderr": (js.stderr or "")[:400]})
    all_pass = passed == len(samples) and len(samples) > 0
    result = {"case": case, "entry": f"{container_pkg_dir}/{entry_name}",
              "passed": passed, "total": len(samples), "all_pass": all_pass,
              "reward": int(all_pass), "reward_source": "RepoZero eval_case (oracle vs node, normalized lines)",
              "fail_examples": details}
    (out_dir / "judge.result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


# ----------------------------- agent (native qwen-code -> serving) -----------------------------

def case_paths(case: str):
    lib, filename = case.split("/")
    stem = filename[:-3] if filename.endswith(".py") else filename
    return lib, filename, stem, stem + "_pkg", stem + ".mjs", stem + "_executable"


def run_agent(name: str, rz_root: Path, case: str, host_output_root: Path, out_dir: Path,
              env: dict, base_url: str, model: str, turns: int, rollout_timeout: int) -> dict:
    lib, filename, stem, pkg_name, entry_name, exe_name = case_paths(case)
    container_pkg_dir = f"{CONTAINER_OUTPUT}/packages/{lib}/{pkg_name}"
    host_pkg_dir = host_output_root / "packages" / lib / pkg_name
    host_pkg_dir.mkdir(parents=True, exist_ok=True)  # bind-mounted -> visible in container

    py_source = (rz_root / "Py2JS" / "dataset" / case).read_text(encoding="utf-8")
    testcase_file = rz_root / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    samples = load_jsonl_cases(testcase_file, case)
    whitebox = build_whitebox(name, exe_name, samples, env, limit=4)
    (out_dir / "whitebox.json").write_text(json.dumps(whitebox, ensure_ascii=False, indent=2) + "\n")

    hint = PYTHON_TO_JS_HINTS.get(lib, "Node built-ins only; implement behavior manually")
    prompt = build_prompt(case, py_source, exe_name, whitebox, container_pkg_dir, entry_name, hint)
    (out_dir / "prompt.txt").write_text(prompt)

    # probe: prove container -> serving path directly (independent of qwen), same shell as agent.
    probe = dexec_qwen(name, QWEN_PATH_PREFIX + "node --version; echo '---'; command -v qwen; qwen --version; echo '---'; "
                             f"curl -s --noproxy '*' --max-time 12 {shlex.quote(base_url)}/models | head -c 400 || echo CURL_FAIL",
                       env, base_url, model, 60)
    (out_dir / "container_probe.txt").write_text((probe.stdout or "") + "\n[stderr]\n" + (probe.stderr or ""))

    cp = run(["docker", "cp", str(out_dir / "prompt.txt"), f"{name}:/tmp/qwen_rz_prompt.txt"], env=env, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError(f"prompt cp failed: {(cp.stderr or cp.stdout)[-300:]}")

    turns_flag = f"--max-session-turns {turns}" if turns and turns > 0 else ""
    qcmd = QWEN_PATH_PREFIX + (
        "env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY "
        'qwen --channel CI -p "$(cat /tmp/qwen_rz_prompt.txt)" '
        f"--yolo --auth-type openai --openai-base-url {shlex.quote(base_url)} "
        '--openai-api-key "$OPENAI_API_KEY" '
        f"--model {shlex.quote(model)} --output-format stream-json {turns_flag}"
    ).strip()
    (out_dir / "qwen_command.txt").write_text(qcmd + "\n")

    t0 = time.time()
    timed_out = False
    try:
        proc = dexec_qwen(name, qcmd, env, base_url, model, rollout_timeout, workdir=container_pkg_dir)
        rc, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out, rc = True, -100
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", "replace")
        stderr = (exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", "replace")) + f"\n[ROLLOUT_TIMEOUT {rollout_timeout}s]\n"
    dur = round(time.time() - t0, 1)
    (out_dir / "qwen.stdout.jsonl").write_text(stdout, errors="replace")
    (out_dir / "qwen.stderr.txt").write_text(stderr, errors="replace")

    # collect generated files (the RepoZero analog of a diff)
    listing = dexec_plain(name, ["sh", "-c", f"ls -la {container_pkg_dir} 2>/dev/null"], env, timeout=30)
    (out_dir / "generated_ls.txt").write_text(listing.stdout or "")
    entry_exists = dexec_plain(name, ["test", "-f", f"{container_pkg_dir}/{entry_name}"], env, timeout=30).returncode == 0
    entry_bytes = 0
    if (host_pkg_dir / entry_name).exists():
        entry_bytes = (host_pkg_dir / entry_name).stat().st_size

    turns_info = analyse_stream(stdout)
    (out_dir / "stream_analysis.json").write_text(json.dumps(turns_info, indent=2) + "\n")

    return {"agent_rc": rc, "agent_seconds": dur, "timed_out": timed_out,
            "entry_exists": entry_exists, "entry_bytes": entry_bytes,
            "stream": turns_info}


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
    return {"json_events": events, "assistant_turns": assistants, "tool_calls": tool_calls,
            "tool_results": tool_results, "error_events": errors, "first_event_types": sample,
            "has_real_interaction": events > 1 and (assistants > 0 or tool_calls > 0)}


# ----------------------------- grader realness (reference .mjs -> expect all_pass=1) -----------------------------

def run_grader(name: str, rz_root: Path, case: str, host_output_root: Path, out_dir: Path,
               env: dict, reference_mjs: Path, eval_timeout: int) -> dict:
    lib, filename, stem, pkg_name, entry_name, exe_name = case_paths(case)
    host_pkg_dir = host_output_root / "packages" / lib / pkg_name
    host_pkg_dir.mkdir(parents=True, exist_ok=True)

    # positive: known-good reference -> expect all_pass=1
    shutil.copyfile(reference_mjs, host_pkg_dir / entry_name)
    pos = eval_case(name, rz_root, case, out_dir, env, eval_timeout)
    (out_dir / "grader_positive.json").write_text(json.dumps(pos, indent=2) + "\n")

    # negative: broken (empty) mjs -> expect all_pass=0 (proves discrimination)
    (host_pkg_dir / entry_name).write_text("// intentionally empty — should FAIL the judge\n")
    neg_dir = out_dir / "_neg"
    neg_dir.mkdir(exist_ok=True)
    neg = eval_case(name, rz_root, case, neg_dir, env, eval_timeout)
    (out_dir / "grader_negative.json").write_text(json.dumps(neg, indent=2) + "\n")

    # restore reference so a following agent run starts clean is unnecessary (agent uses fresh pkg dir),
    # but leave the reference in place as evidence
    shutil.copyfile(reference_mjs, host_pkg_dir / entry_name)

    return {"reference_mjs": str(reference_mjs),
            "positive_all_pass": pos.get("all_pass"), "positive_passed": pos.get("passed"), "positive_total": pos.get("total"),
            "negative_all_pass": neg.get("all_pass"),
            "grader_is_real": bool(pos.get("all_pass")) and not bool(neg.get("all_pass"))}


# ----------------------------- main -----------------------------

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="RepoZero Path A driver (native qwen-code-in-container)")
    p.add_argument("--case", help="single case, e.g. base58/test1.py")
    p.add_argument("--mode", choices=("load", "grader", "agent", "smoke"), default="smoke")
    p.add_argument("--rz-root", default=DEFAULT_RZ_ROOT)
    p.add_argument("--image", default=DEFAULT_IMAGE)
    p.add_argument("--shared-tar", default=DEFAULT_SHARED_TAR)
    p.add_argument("--qwen-root", default=DEFAULT_QWEN_ROOT)
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--run-root", default=None)
    p.add_argument("--reference-mjs", default=None, help="known-good .mjs for grader-realness (grader/smoke)")
    p.add_argument("--max-session-turns", type=int, default=30)
    p.add_argument("--rollout-timeout", type=int, default=1500)
    p.add_argument("--eval-timeout", type=int, default=10,
                   help="per-sample oracle/node timeout. THIS RUN USED 10s; RepoZero OFFICIAL is 5s "
                        "(evaluate/eval_py2js_docker.py lines 52 & 59). 10s is 2x looser and can only "
                        "admit passes the official 5s would reject, so 98/400 is an UPPER bound. The "
                        "official-5s re-judge of all 400 .mjs is in rejudge_official5s.json / AUDIT_NOTES.md.")
    p.add_argument("--no-verify-sha", action="store_true")
    p.add_argument("--keep-container", action="store_true")
    args = p.parse_args(argv)

    env = docker_env()
    rz_root = Path(args.rz_root)

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    tag = (args.case or "load").replace("/", "-").replace(".py", "")
    run_root = Path(args.run_root or f"{DEFAULT_RUNS_ROOT}/{tag}_{ts}")
    run_root.mkdir(parents=True, exist_ok=True)
    host_output_root = run_root / "workspace_output"
    host_output_root.mkdir(parents=True, exist_ok=True)
    log("RUN_ROOT", run_root)

    summary: dict = {"mode": args.mode, "case": args.case, "image": args.image,
                     "base_url": args.base_url, "model": args.model,
                     "run_root": str(run_root), "ts": ts}

    # 1) image
    img_info = ensure_image(args.image, args.shared_tar, env, verify_sha=not args.no_verify_sha)
    summary["image_info"] = img_info
    log("IMAGE", img_info.get("status"), "sha_ok=", img_info.get("sha256_verified"))
    if args.mode == "load":
        (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        log("DONE (load only)")
        return 0

    if not args.case:
        raise SystemExit("--case required for mode != load")
    lib = args.case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    if not dataset_dir.exists():
        raise SystemExit(f"dataset lib dir not found: {dataset_dir}")

    cname = f"repozero-pathA-{tag}-{ts}"[:120]

    # 2) grader realness (needs NO serving)
    if args.mode in ("grader", "smoke") and args.reference_mjs:
        gdir = run_root / "grader"
        gdir.mkdir(parents=True, exist_ok=True)
        try:
            start_container(cname + "-g", args.image, dataset_dir, host_output_root, args.qwen_root, args.base_url, args.model, env)
            g = run_grader(cname + "-g", rz_root, args.case, host_output_root, gdir, env, Path(args.reference_mjs), args.eval_timeout)
            summary["grader"] = g
            log("GRADER", "positive_all_pass=", g.get("positive_all_pass"),
                "negative_all_pass=", g.get("negative_all_pass"), "grader_is_real=", g.get("grader_is_real"))
        finally:
            if not args.keep_container:
                run(["docker", "rm", "-f", cname + "-g"], env=env)
    elif args.mode == "grader":
        raise SystemExit("grader mode requires --reference-mjs")

    # 3) agent path (native qwen-code -> serving)
    if args.mode in ("agent", "smoke"):
        adir = run_root / "agent"
        adir.mkdir(parents=True, exist_ok=True)
        # fresh output pkg dir for the agent (do not let a reference .mjs leak in)
        lib_, _, _, pkg_name_, _, _ = case_paths(args.case)
        agent_pkg = host_output_root / "packages" / lib_ / pkg_name_
        if agent_pkg.exists():
            shutil.rmtree(agent_pkg)
        try:
            start_container(cname + "-a", args.image, dataset_dir, host_output_root, args.qwen_root, args.base_url, args.model, env)
            ag = run_agent(cname + "-a", rz_root, args.case, host_output_root, adir, env,
                           args.base_url, args.model, args.max_session_turns, args.rollout_timeout)
            judge = eval_case(cname + "-a", rz_root, args.case, adir, env, args.eval_timeout)
            summary["agent"] = {**ag, **judge}
            log("AGENT", "entry_exists=", ag.get("entry_exists"),
                "assistant_turns=", ag.get("stream", {}).get("assistant_turns"),
                "tool_calls=", ag.get("stream", {}).get("tool_calls"),
                "reward=", judge.get("reward"), "passed=", judge.get("passed"), "/", judge.get("total"))
        finally:
            if not args.keep_container:
                run(["docker", "rm", "-f", cname + "-a"], env=env)

    (run_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log("SUMMARY", json.dumps(summary, indent=2))
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
