#!/usr/bin/env python3
"""Scan the 51 all_pass cases: which have an entry .mjs that imports a `.js`
sibling with ESM export syntax (node-20 auto-detect dependent; would fail under
the RepoZero image's official node 18)."""
import json, re
from pathlib import Path
RZ = Path("/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/runs/instruct2507_full400_20260713T151209Z")
OUT = "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repozero_pathA/reviewerA_scanjs.txt"
buf=[]
def w(*a): buf.append(" ".join(str(x) for x in a))
rows=[json.loads(l) for l in open(RZ/"results.jsonl") if l.strip()]
allpass=[r["case"] for r in rows if r.get("all_pass")]
imp_js=re.compile(r"""(?:import|from)\s+['"][^'"]*\.js['"]""")
dep=[]; robust=[]; nofiles=[]
for case in sorted(allpass):
    lib,fn=case.split("/"); stem=fn[:-3]
    pkg=RZ/"cases"/f"{lib}-{stem}"/"workspace_output"/"packages"/lib/f"{stem}_pkg"
    if not pkg.exists():
        nofiles.append(case); continue
    mjs=sorted(pkg.glob("*.mjs")); js=sorted(pkg.glob("*.js"))
    entry=pkg/f"{stem}.mjs"
    # does ANY .mjs in the pkg import a .js file?
    imports_js=False; detail=[]
    for m in mjs:
        txt=m.read_text(errors="ignore")
        hits=imp_js.findall(txt)
        if hits:
            imports_js=True; detail.append(f"{m.name}->{hits[:3]}")
    tag=f"{case}: mjs={[m.name for m in mjs]} js={[j.name for j in js]}"
    if imports_js:
        dep.append(case); w("NODE20-DEP", tag, "||", "; ".join(detail))
    else:
        robust.append(case)
w("\n=== SUMMARY ===")
w("total all_pass            :", len(allpass))
w("node20-dependent (.js import):", len(dep), "->", dep)
w("robust (mjs-only/single)  :", len(robust))
w("pkg missing               :", len(nofiles), nofiles)
w("\nStrict-node18 upper-bound flip = up to", len(dep), "cases")
w("=> strict-node18 headline in [", f"{(len(allpass)-len(dep))}/400={(len(allpass)-len(dep))/400*100:.2f}%", ",", f"{len(allpass)}/400={len(allpass)/400*100:.2f}%", "]")
Path(OUT).write_text("\n".join(buf)+"\n")
print("SCANJS_DONE dep=",len(dep))
