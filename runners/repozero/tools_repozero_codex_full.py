#!/usr/bin/env python3
import argparse
import ast
import concurrent.futures
import json
import os
import pathlib
import re
import shutil
import subprocess
import threading
import time


DEFAULT_IMAGE = "ghcr.io/jessezzzzz/repoarena-new:latest"
DEFAULT_RUN_NAME = "gpt-5.4_xhigh_full"
TRANSIENT_CODEX_ERRORS = (
    "503 Service Unavailable",
    "502 Bad Gateway",
    "504 Gateway Timeout",
    "Service temporarily unavailable",
    "temporarily unavailable",
    "Rate limit",
    "rate_limit",
    "429",
    "ECONNRESET",
    "ETIMEDOUT",
)


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
    "mpmath": "BigInt / Number only; implement math behavior manually",
    "networkx": "Map / Set / Array only; implement graph algorithms manually",
    "schedule": "Date / timers not required; implement schedule formatting manually",
    "whoosh": "RegExp / string processing only; implement search/parser behavior manually",
}


def run_cmd(cmd, timeout=10, cwd=None, env=None):
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"


def load_jsonl_cases(jsonl_path, filename):
    rows = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("filename") == filename:
                obj.pop("filename", None)
                rows.append(obj)
    return rows


def args_from_params(params):
    args = []
    for key, value in params.items():
        args.extend([f"--{key}", str(value)])
    return args


def normalized_lines(text):
    return ["".join(line.split()) for line in text.strip().splitlines() if line.strip()]


def parse_official_cases(repo_root, include_excluded=True):
    script = repo_root / "run_py2js_docker" / "run_all_docker.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"valid_ids", "excluded_ids"}:
                values[target.id] = ast.literal_eval(node.value)
    cases = list(values["valid_ids"])
    excluded = set(values.get("excluded_ids", []))
    if not include_excluded:
        cases = [case for case in cases if case.split("/")[0] not in excluded]
    return cases


def parse_dataset_cases(repo_root):
    cases = []
    dataset = repo_root / "Py2JS" / "dataset"
    for path in sorted(dataset.glob("*/*.py")):
        cases.append(str(path.relative_to(dataset)))
    return cases


def safe_container_suffix(case):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", case.replace("/", "-"))


def start_case_container(repo_root, output_root, case, docker_image):
    lib, _ = case.split("/")
    dataset_dir = repo_root / "Py2JS" / "dataset" / lib
    name = f"repozero-codex-{os.getpid()}-{time.time_ns()}-{safe_container_suffix(case)}"
    rc, out, err = run_cmd(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "none",
            "-v",
            f"{dataset_dir}:/workspace/dataset:ro",
            "-v",
            f"{output_root}:/workspace/output:rw",
            docker_image,
            "tail",
            "-f",
            "/dev/null",
        ],
        timeout=45,
    )
    if rc != 0:
        raise RuntimeError(f"failed to start container for {case}: {err or out}")
    return name


def stop_container(name):
    subprocess.run(
        ["docker", "rm", "-f", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def run_oracle(container_name, executable_name, args, timeout=10):
    return run_cmd(
        ["docker", "exec", container_name, f"/workspace/dataset/{executable_name}"] + args,
        timeout=timeout,
    )


def run_js(container_name, container_pkg_dir, entry_name, args, timeout=10):
    return run_cmd(
        ["docker", "exec", "-w", container_pkg_dir, container_name, "node", entry_name] + args,
        timeout=timeout,
    )


def ensure_node_wrapper(output_root, docker_image):
    bin_dir = output_root / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    node_path = bin_dir / "node"
    script = f"""#!/usr/bin/env bash
set -euo pipefail
host_root="${{REPOZERO_NODE_HOST_ROOT:?missing REPOZERO_NODE_HOST_ROOT}}"
container_root="/workspace/output"
case_dir="${{PWD#$host_root}}"
case_dir="${{case_dir#/}}"
if [[ -z "$case_dir" || "$case_dir" == "$PWD" ]]; then
  workdir="$container_root"
else
  workdir="$container_root/$case_dir"
fi
exec docker run --rm --network none -v "$host_root:$container_root:rw" -w "$workdir" {docker_image} node "$@"
"""
    node_path.write_text(script, encoding="utf-8")
    node_path.chmod(0o755)
    return bin_dir


def build_whitebox(container_name, executable_name, samples, limit=4):
    examples = []
    for params in samples[:limit]:
        args = args_from_params(params)
        rc, out, err = run_oracle(container_name, executable_name, args, timeout=10)
        examples.append({"args": args, "returncode": rc, "stdout": out, "stderr": err})
    return examples


def build_prompt(repo_root, output_root, case, output_dir, whitebox, docker_image):
    lib, filename = case.split("/")
    py_path = repo_root / "Py2JS" / "dataset" / case
    exe_name = py_path.stem + "_executable"
    source = py_path.read_text(encoding="utf-8")
    entry_name = filename.replace(".py", ".mjs")
    hint = PYTHON_TO_JS_HINTS.get(lib, "Node built-ins only; implement behavior manually")
    container_output_dir = f"/workspace/output/packages/{lib}/{filename.replace('.py', '_pkg')}"
    return f"""You are running one RepoZero Py2JS benchmark case with OpenAI Codex.

Source Python file:
{py_path}

Python source:
```python
{source}
```

Oracle executable:
{py_path.with_name(exe_name)}

Oracle inspection command template:
docker run --rm --network none -v {py_path.parent}:/workspace/dataset:ro {docker_image} /workspace/dataset/{exe_name} --arg value

White-box examples from the hidden test distribution:
```json
{json.dumps(whitebox, ensure_ascii=False, indent=2)}
```

Task:
- Reimplement the behavior in pure JavaScript for Node.js as ES Modules.
- Write all generated files under exactly this directory:
  {output_dir}
- The entry point must be:
  {output_dir / entry_name}
- Use `.mjs` files, `import` / `export`, and include full `.mjs` extensions in local imports.
- Parse CLI arguments from `process.argv` so `node {entry_name} --arg value` matches the oracle executable.
- Match stdout semantics and formatting. Newline/space differences matter.
- Use no npm packages and do not use CommonJS.
- Do not call Python, the oracle executable, or any generated wrapper from the final JavaScript implementation.
- Do not import or mention external equivalents for this library. Forbidden shortcut hint: {hint}.
- You may run the oracle executable through the Docker command template during development to inspect behavior.
- You may run `node` to test your generated implementation. In this environment `node` is a wrapper for Node.js 18 in the RepoZero Docker image.
- Container output path equivalent:
  {container_output_dir}

Finish only after the entry file exists and you have tested at least the white-box examples.
"""


def create_testfile_wrapper(output_root, case):
    lib, filename = case.split("/")
    entry_name = filename.replace(".py", ".mjs")
    pkg_name = filename.replace(".py", "_pkg")
    src_entry = output_root / "packages" / lib / pkg_name / entry_name
    testfile = output_root / "testfiles" / lib / entry_name
    testfile.parent.mkdir(parents=True, exist_ok=True)
    if src_entry.exists():
        testfile.write_text(f"import '../../packages/{lib}/{pkg_name}/{entry_name}';\n", encoding="utf-8")
    return testfile


def eval_case(repo_root, output_root, case, container_name):
    lib, filename = case.split("/")
    testcase_file = repo_root / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    samples = load_jsonl_cases(testcase_file, case)
    py_path = repo_root / "Py2JS" / "dataset" / case
    executable_name = py_path.stem + "_executable"
    entry_name = filename.replace(".py", ".mjs")
    pkg_name = filename.replace(".py", "_pkg")
    entry = output_root / "packages" / lib / pkg_name / entry_name
    container_pkg_dir = f"/workspace/output/packages/{lib}/{pkg_name}"

    passed = 0
    details = []
    if not entry.exists():
        return {
            "case": case,
            "entry": str(entry),
            "passed": 0,
            "total": len(samples),
            "all_pass": False,
            "fail_examples": [{"error": "missing generated entry file"}],
        }

    for params in samples:
        args = args_from_params(params)
        py_rc, py_out, py_err = run_oracle(container_name, executable_name, args, timeout=10)
        js_rc, js_out, js_err = run_js(container_name, container_pkg_dir, entry_name, args, timeout=10)
        ok = py_rc == 0 and js_rc == 0 and normalized_lines(py_out) == normalized_lines(js_out)
        if ok:
            passed += 1
        elif len(details) < 5:
            details.append(
                {
                    "args": args,
                    "oracle_rc": py_rc,
                    "js_rc": js_rc,
                    "oracle_stdout": py_out[:500],
                    "oracle_stderr": py_err[:500],
                    "js_stdout": js_out[:500],
                    "js_stderr": js_err[:500],
                }
            )
    return {
        "case": case,
        "entry": str(entry),
        "testfile_wrapper": str(create_testfile_wrapper(output_root, case)),
        "passed": passed,
        "total": len(samples),
        "all_pass": passed == len(samples) and len(samples) > 0,
        "fail_examples": details,
    }


def log_has_transient_error(log_path):
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return any(pattern in text for pattern in TRANSIENT_CODEX_ERRORS)


def clean_attempt_outputs(output_dir):
    for child in output_dir.iterdir():
        if child.name == "prompt.txt":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def run_case(repo_root, output_root, model, base_url, effort, docker_image, case, timeout_s, codex_attempts):
    start = time.time()
    lib, filename = case.split("/")
    pkg_name = filename.replace(".py", "_pkg")
    output_dir = output_root / "packages" / lib / pkg_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    py_path = repo_root / "Py2JS" / "dataset" / case
    testcase_file = repo_root / "Py2JS" / "testcases_60" / f"testcase_{lib}.jsonl"
    if not py_path.exists() or not py_path.with_name(py_path.stem + "_executable").exists():
        return {
            "case": case,
            "error": "missing dataset source or executable",
            "all_pass": False,
            "seconds": round(time.time() - start, 2),
        }
    if not testcase_file.exists():
        return {
            "case": case,
            "error": "missing testcase jsonl",
            "all_pass": False,
            "seconds": round(time.time() - start, 2),
        }

    container = start_case_container(repo_root, output_root, case, docker_image)
    log_path = output_dir / "codex.log"
    prompt_path = output_dir / "prompt.txt"
    try:
        samples = load_jsonl_cases(testcase_file, case)
        whitebox = build_whitebox(container, py_path.stem + "_executable", samples, limit=4)
        prompt = build_prompt(repo_root, output_root, case, output_dir, whitebox, docker_image)
        prompt_path.write_text(prompt, encoding="utf-8")

        host_codex = shutil.which("codex")
        host_node = shutil.which("node")
        if not host_codex or not host_node:
            raise RuntimeError("codex or node not found on PATH")

        env = os.environ.copy()
        env["PATH"] = f"{output_root / '.bin'}:{env.get('PATH', '')}"
        env["REPOZERO_NODE_HOST_ROOT"] = str(output_root)
        if "PACKYAPI_KEY" not in env and "OPENAI_API_KEY" in env:
            env["PACKYAPI_KEY"] = env["OPENAI_API_KEY"]

        cmd = [
            host_node,
            host_codex,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "-m",
            model,
            "-c",
            'model_provider="packyapi"',
            "-c",
            f'model_providers.packyapi.base_url="{base_url}"',
            "-c",
            'model_providers.packyapi.env_key="PACKYAPI_KEY"',
            "-c",
            'model_providers.packyapi.wire_api="responses"',
            "-c",
            f'model_reasoning_effort="{effort}"',
            "-C",
            str(output_dir),
            prompt,
        ]
        timed_out = False
        attempts_used = 0
        retry_reason = None
        for attempt in range(1, max(1, codex_attempts) + 1):
            attempts_used = attempt
            timed_out = False
            if attempt > 1:
                clean_attempt_outputs(output_dir)
                time.sleep(min(60, 10 * (attempt - 1)))
            attempt_log_path = output_dir / f"codex_attempt_{attempt}.log"
            with open(attempt_log_path, "w", encoding="utf-8") as log:
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(output_dir),
                        env=env,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=timeout_s,
                    )
                    codex_rc = proc.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    codex_rc = 124
            shutil.copyfile(attempt_log_path, log_path)
            retry_reason = None
            if codex_rc == 0 or attempt >= max(1, codex_attempts):
                break
            if timed_out:
                retry_reason = "timeout"
            elif log_has_transient_error(attempt_log_path):
                retry_reason = "transient_api_error"
            if not retry_reason:
                break

        result = eval_case(repo_root, output_root, case, container)
        result.update(
            {
                "codex_returncode": codex_rc,
                "codex_timeout": timed_out,
                "codex_attempts": attempts_used,
                "codex_retry_reason": retry_reason,
                "seconds": round(time.time() - start, 2),
                "log": str(log_path),
                "prompt": str(prompt_path),
                "output_dir": str(output_dir),
            }
        )
        (output_dir / "case_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result
    finally:
        stop_container(container)


def summarize(args, started, output_root, results):
    completed = [r for r in results if not r.get("skipped")]
    summary = {
        "model": args.model,
        "effort": args.effort,
        "base_url": args.base_url,
        "workers": args.workers,
        "docker_image": args.docker_image,
        "run_name": args.run_name,
        "elapsed_seconds": round(time.time() - started, 2),
        "cases_total": len(results),
        "cases_all_pass": sum(1 for r in results if r.get("all_pass")),
        "tests_passed": sum(int(r.get("passed", 0)) for r in results),
        "tests_total": sum(int(r.get("total", 0)) for r in results),
        "results": sorted(results, key=lambda r: r.get("case", "")),
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def load_completed(results_jsonl):
    completed = {}
    if not results_jsonl.exists():
        return completed
    with open(results_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("case"):
                completed[obj["case"]] = obj
    return completed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--effort", default="xhigh")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-s", type=int, default=2400)
    parser.add_argument("--codex-attempts", type=int, default=3)
    parser.add_argument("--docker-image", default=DEFAULT_IMAGE)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--case-source", choices=["official", "dataset"], default="official")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cases", nargs="*", default=None)
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo_root).resolve()
    output_root = repo_root / "Py2JS" / "output_codex" / args.run_name
    output_root.mkdir(parents=True, exist_ok=True)
    ensure_node_wrapper(output_root, args.docker_image)

    if args.cases:
        cases = args.cases
    elif args.case_source == "official":
        cases = parse_official_cases(repo_root, include_excluded=args.include_excluded)
    else:
        cases = parse_dataset_cases(repo_root)

    results_jsonl = output_root / "results.jsonl"
    completed = load_completed(results_jsonl) if args.resume else {}
    lock = threading.Lock()
    started = time.time()
    results = []

    pending = []
    for case in cases:
        if case in completed:
            obj = dict(completed[case])
            obj["skipped"] = True
            results.append(obj)
        else:
            pending.append(case)

    print(
        json.dumps(
            {
                "event": "start",
                "run_name": args.run_name,
                "model": args.model,
                "effort": args.effort,
                "workers": args.workers,
                "cases": len(cases),
                "pending": len(pending),
                "resume_completed": len(results),
                "output_root": str(output_root),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(
                run_case,
                repo_root,
                output_root,
                args.model,
                args.base_url,
                args.effort,
                args.docker_image,
                case,
                args.timeout_s,
                args.codex_attempts,
            ): case
            for case in pending
        }
        for fut in concurrent.futures.as_completed(futs):
            case = futs[fut]
            try:
                res = fut.result()
            except Exception as exc:
                res = {"case": case, "error": repr(exc), "all_pass": False}
            with lock:
                results.append(res)
                with open(results_jsonl, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
                summary = summarize(args, started, output_root, results)
            print(json.dumps(res, ensure_ascii=False), flush=True)
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "done": len(results),
                        "total": len(cases),
                        "cases_all_pass": summary["cases_all_pass"],
                        "tests_passed": summary["tests_passed"],
                        "tests_total": summary["tests_total"],
                        "elapsed_seconds": summary["elapsed_seconds"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    summary = summarize(args, started, output_root, results)
    print("SUMMARY", output_root / "summary.json")
    print("ALL_PASS_CASES", summary["cases_all_pass"], "/", summary["cases_total"])
    print("TESTS", summary["tests_passed"], "/", summary["tests_total"])


if __name__ == "__main__":
    main()
