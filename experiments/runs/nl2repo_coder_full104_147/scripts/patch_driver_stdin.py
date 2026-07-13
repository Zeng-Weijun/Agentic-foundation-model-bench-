#!/usr/bin/env python3
"""Patch nl2repo_qwencode_driver.py: deliver the agent prompt via STDIN instead of
`-p "$(cat ...)"`. The old form put the entire (up to 393KB) start.md-inlined prompt
into a single argv element, which exceeds Linux MAX_ARG_STRLEN (131072 B) for the 18
tasks whose start.md >= ~128KB -> `/usr/bin/env: Argument list too long` -> qwen never
launches -> turns=0, empty workspace -> FALSE score (0 for most; a false-POSITIVE for
'databases' where the base image leaks the package). qwen reads the prompt from stdin
(its own `-p` help: "Appended to input on stdin"); this is byte-identical prompt content,
only the delivery channel changes. Verified: `... qwen ... < prompt.txt` -> real stream-json.

Idempotent; backs up original; refuses unless exactly one match of each anchor is found.
"""
import shutil, sys
from pathlib import Path

DRV = Path(sys.argv[1] if len(sys.argv) > 1 else
           "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/nl2repo_pathA/nl2repo_qwencode_driver.py")

OLD1 = '''        'qwen --channel CI -p "$(cat /tmp/nl2repo_prompt.txt)" '\n'''
NEW1 = '''        'qwen --channel CI '\n'''
# faithful: prompt now arrives on stdin (see build_prompt / prompt.txt already cp'd to container)

OLD2 = '''        f"--model {shlex.quote(model)} --output-format stream-json {turns_flag}"\n'''
NEW2 = '''        f"--model {shlex.quote(model)} --output-format stream-json {turns_flag} "\n        "< /tmp/nl2repo_prompt.txt"\n'''

src = DRV.read_text()
if "< /tmp/nl2repo_prompt.txt" in src and "-p \"$(cat /tmp/nl2repo_prompt.txt)\"" not in src:
    print("[patch] already applied (idempotent) — no change"); sys.exit(0)

for name, old in (("OLD1", OLD1), ("OLD2", OLD2)):
    n = src.count(old)
    if n != 1:
        print(f"[patch] ABORT: anchor {name} found {n} times (expected 1). Driver changed; not patching."); sys.exit(2)

bak = DRV.with_suffix(".py.bak.argv")
if not bak.exists():
    shutil.copy2(DRV, bak); print(f"[patch] backup -> {bak}")

src = src.replace(OLD1, NEW1).replace(OLD2, NEW2)
DRV.write_text(src)
# verify
assert "< /tmp/nl2repo_prompt.txt" in src and '-p "$(cat /tmp/nl2repo_prompt.txt)"' not in src, "verify failed"
import py_compile; py_compile.compile(str(DRV), doraise=True)
print("[patch] applied + py_compile OK: prompt now delivered via stdin (no argv overflow)")
