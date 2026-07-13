#!/usr/bin/env python3
"""Reviewer B: independently verify codex-pro's MAJOR finding (Node20 vs
Node18 in the judge's PATH) on 2 DIFFERENT passing cases than codex already
checked. Force the oracle+node exec to use /usr/bin/node (image-native
v18.19.1, confirmed via `docker run --rm <image> node --version`) via an
absolute path, instead of the bare `node` that resolves through the
container_env()-overridden PATH to the qwen-mounted v20.20.2.
"""
import importlib.util, json
from pathlib import Path

P = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA")
spec = importlib.util.spec_from_file_location("rz", str(P / "repozero_qwencode_driver.py"))
rz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rz)

RUN = P / "runs" / "instruct2507_full400_20260713T151209Z"
rz_root = Path(rz.DEFAULT_RZ_ROOT)
env = rz.docker_env()

cases = ["base58/test3.py", "bidict/test3.py", "bidict/test5.py"]  # Reviewer-A claims these flip to FAIL under node18 (independent re-check)

baseline = {}
with (RUN / "results.jsonl").open() as f:
    for line in f:
        o = json.loads(line.strip())
        baseline[o["case"]] = o

for case in cases:
    slug = case.replace("/", "-").replace(".py", "")
    run_root = RUN / "cases" / slug
    output_root = run_root / "workspace_output"
    lib = case.split("/")[0]
    dataset_dir = rz_root / "Py2JS" / "dataset" / lib
    name = f"reviewerB-node18-{slug}"
    b = baseline[case]
    print(f"\n=== {case} (baseline all_pass={b.get('all_pass')} passed={b.get('passed')}/{b.get('total')}) ===", flush=True)
    try:
        rz.start_container(name, rz.DEFAULT_IMAGE, dataset_dir, output_root,
                           rz.DEFAULT_QWEN_ROOT, rz.DEFAULT_BASE_URL, rz.DEFAULT_MODEL, env)
        # confirm bare `node` really is v20 in THIS container (sanity)
        bare = rz.dexec_plain(name, ["node", "--version"], env, timeout=10)
        native = rz.dexec_plain(name, ["/usr/bin/node", "--version"], env, timeout=10)
        print("bare `node` -v =", bare.stdout.strip(), " /usr/bin/node -v =", native.stdout.strip())

        lib2, filename = case.split("/")
        stem = filename[:-3]
        entry_name = stem + ".mjs"
        pkg_name = stem + "_pkg"
        container_pkg_dir = f"{rz.CONTAINER_OUTPUT}/packages/{lib2}/{pkg_name}"
        testcase_file = rz_root / "Py2JS" / "testcases_60" / f"testcase_{lib2}.jsonl"
        samples = rz.load_jsonl_cases(testcase_file, case)
        exe_name = stem + "_executable"

        passed_v18 = 0
        for params in samples:
            args = rz.args_from_params(params)
            py = rz.dexec_plain(name, [f"{rz.CONTAINER_DATASET}/{exe_name}"] + args, env, timeout=10)
            js18 = rz.dexec_plain(name, ["/usr/bin/node", entry_name] + args, env, timeout=10, workdir=container_pkg_dir)
            ok = py.returncode == 0 and js18.returncode == 0 and rz.normalized_lines(py.stdout or "") == rz.normalized_lines(js18.stdout or "")
            if ok:
                passed_v18 += 1
        all_pass_v18 = passed_v18 == len(samples) and len(samples) > 0
        print(f"UNDER NODE 18.19.1 (image-native, forced /usr/bin/node): passed={passed_v18}/{len(samples)} all_pass={all_pass_v18}")
        print(f"COMMITTED (node20 via bare PATH): all_pass={b.get('all_pass')} passed={b.get('passed')}/{b.get('total')}")
        print("VERDICT_CHANGED:", all_pass_v18 != b.get("all_pass"))
    finally:
        rz.run(["docker", "rm", "-f", name], env=env)
