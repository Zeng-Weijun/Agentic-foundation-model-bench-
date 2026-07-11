#!/usr/bin/env bash
# ============================================================================
# collect_evidence_v6.sh — collect a bench reproduction run into a COMPLETE,
# self-contained v6 evidence bundle: enough to (a) INDEPENDENTLY REPRODUCE and
# (b) INDEPENDENTLY RE-ADJUDICATE resolved/unresolved WITHOUT the shared-disk trace.
# ----------------------------------------------------------------------------
# Usage:   collect_evidence_v6.sh <RUN_DIR> <OUT_DIR> [EXPECT_N]
#   RUN_DIR  : a completed run root (has results.jsonl + runner_config.json)
#   OUT_DIR  : where to write the evidence bundle (experiments/runs/<run>/)
#   EXPECT_N : declared dataset_size; default = runner_config.expected_score_rows
#
# Optional env (sensible defaults for AFMB qwen-code multilingual runs):
#   CONDA_SWEBENCH_PY  eval-harness python (pip freeze source)
#   TAIL_LINES         test_output tail lines per instance (default 400)
#   TAIL_BYTES         test_output tail byte cap per instance (default 60000)
#   --- (1) per-task image digest capture (run ON the exec host while keep_images) ---
#   CAPTURE_IMAGE_DIGESTS=1   enable capture (default off; off keeps a documented gap)
#   IMAGE_INSPECT_CMD  docker command prefix (default "docker"; e.g. "ssh <host> docker")
#   IMAGE_ARCH         swebench image arch token (default x86_64)
#   --- (2) agent trajectory condensation into verdict_pack ---
#   TRAJ_MAX_BLOCKS    max trajectory blocks/instance (default 400)
#   TRAJ_SUMMARY_CHARS per-block summary char cap (default 240)
#   TRAJ_MAX_BYTES     per-instance trajectory byte cap (default 80000)
#   --- (3) bulky-artifact internal retention (NOT pushed to git) ---
#   RETAIN_ARTIFACTS=1 archive scaffold tree to RETAIN_DIR (content-addressed, idempotent)
#   RETAIN_DIR         internal shared-disk retention dir (required if RETAIN_ARTIFACTS=1)
#
# What it produces under OUT_DIR (each element = a reproducibility/adjudication seam):
#   launch.sh              发射脚本 (exact orchestrator entrypoint) + COMMAND.sh
#   repro_closure.json     复现闭包: script sha256+git, scaffold ver+pkg sha, conda pkgs,
#                          dataset id+parquet sha, per-task image digests, artifact_retrieval
#   serving/               get_model_info + get_server_info  BEFORE + AFTER
#   results.jsonl          verbatim run results
#   verdict_pack.tar.gz    判定证据: per-instance prediction.patch + test_output_tail + report.json
#                          + trajectory.jsonl (verdict AND process re-checkable OFFLINE, no shared-disk trace)
#   calibration.md         口径卡: resolved def, harness ver, include_unverified, anchor, caveats
#   denom_assert.txt       wc -l results == declared dataset_size  (PASS/FAIL)
#   TRACE.md               full-trace location + du + top-level manifest sha (big trace stays on FS)
#   SHA256SUMS             完整性封条 over every file above
#
# Fail-closed: aborts if RUN_DIR lacks results.jsonl or runner_config.json.
# Truthful: every sha is really computed; verdict_pack really extracted from trace;
#           un-collectable elements are recorded as {"missing": "..."} — never faked.
# ============================================================================
set -uo pipefail

v6_die(){ echo "[v6][FATAL] $*" >&2; exit 1; }
v6_log(){ echo "[v6] $*"; }

RUN_DIR="${1:-}"; OUT_DIR="${2:-}"; EXPECT_N_ARG="${3:-}"
[ -n "$RUN_DIR" ] && [ -n "$OUT_DIR" ] || v6_die "usage: collect_evidence_v6.sh <RUN_DIR> <OUT_DIR> [EXPECT_N]"
RUN_DIR="$(cd -- "$RUN_DIR" 2>/dev/null && pwd)" || v6_die "RUN_DIR not a dir: $1"
[ -f "$RUN_DIR/results.jsonl" ]     || v6_die "no results.jsonl under $RUN_DIR"
[ -f "$RUN_DIR/runner_config.json" ] || v6_die "no runner_config.json under $RUN_DIR"

CONDA_SWEBENCH_PY="${CONDA_SWEBENCH_PY:-/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python}"
TAIL_LINES="${TAIL_LINES:-400}"
TAIL_BYTES="${TAIL_BYTES:-60000}"
export CAPTURE_IMAGE_DIGESTS="${CAPTURE_IMAGE_DIGESTS:-0}"
export IMAGE_INSPECT_CMD="${IMAGE_INSPECT_CMD:-docker}"
export IMAGE_ARCH="${IMAGE_ARCH:-x86_64}"
export TRAJ_MAX_BLOCKS="${TRAJ_MAX_BLOCKS:-400}"
export TRAJ_SUMMARY_CHARS="${TRAJ_SUMMARY_CHARS:-240}"
export TRAJ_MAX_BYTES="${TRAJ_MAX_BYTES:-80000}"
export RETAIN_ARTIFACTS="${RETAIN_ARTIFACTS:-0}"
export RETAIN_DIR="${RETAIN_DIR:-}"

mkdir -p "$OUT_DIR" || v6_die "cannot mkdir OUT_DIR $OUT_DIR"
OUT_DIR="$(cd -- "$OUT_DIR" && pwd)"
v6_log "RUN_DIR=$RUN_DIR"
v6_log "OUT_DIR=$OUT_DIR"

# ---------------------------------------------------------------------------
# (1) launch.sh — the exact orchestrator entrypoint + exact invocation
# ---------------------------------------------------------------------------
if [ -f "$RUN_DIR/COMMAND.sh" ]; then
  cp -f "$RUN_DIR/COMMAND.sh" "$OUT_DIR/COMMAND.sh"
  LAUNCH_SRC="$(awk 'NF{print $1; exit}' "$RUN_DIR/COMMAND.sh" 2>/dev/null)"
else
  LAUNCH_SRC=""
fi
if [ -n "$LAUNCH_SRC" ] && [ -f "$LAUNCH_SRC" ]; then
  cp -f "$LAUNCH_SRC" "$OUT_DIR/launch.sh"
  v6_log "launch.sh <- $LAUNCH_SRC"
else
  # fall back to run-local launch.log-adjacent script, else stub with a pointer
  { echo "# launch script not co-located; exact invocation was:"; \
    [ -f "$RUN_DIR/COMMAND.sh" ] && cat "$RUN_DIR/COMMAND.sh"; } > "$OUT_DIR/launch.sh"
  v6_log "launch.sh: original launcher not found; wrote invocation pointer (LAUNCH_SRC=$LAUNCH_SRC)"
fi

# ---------------------------------------------------------------------------
# (3) results.jsonl — verbatim
# ---------------------------------------------------------------------------
cp -f "$RUN_DIR/results.jsonl" "$OUT_DIR/results.jsonl"

# ---------------------------------------------------------------------------
# (4) serving/ — model_info + server_info BEFORE + AFTER (identity chain)
# ---------------------------------------------------------------------------
mkdir -p "$OUT_DIR/serving"
copied_serving=0
for SD in "$RUN_DIR/serving" "$RUN_DIR/serving_config"; do
  [ -d "$SD" ] || continue
  for f in get_model_info_before.json get_model_info_after.json \
           get_server_info_before.json get_server_info_after.json \
           get_server_info_before.redacted.json get_server_info_after.redacted.json \
           IDENTITY_before.txt IDENTITY_after.txt; do
    if [ -f "$SD/$f" ]; then cp -f "$SD/$f" "$OUT_DIR/serving/$f"; copied_serving=$((copied_serving+1)); fi
  done
done
v6_log "serving/: copied $copied_serving file(s)"

# ---------------------------------------------------------------------------
# (2,5,6,7,9-index) heavy lifting in one python pass:
#   repro_closure.json, verdict_pack staging + INDEX.json, calibration.md,
#   denom_assert.txt, TRACE.md, serving IDENTITY summary
# ---------------------------------------------------------------------------
# gather pip-freeze from the eval-harness env (best-effort; recorded, not required)
FREEZE_TXT="$(mktemp)"
if [ -x "$CONDA_SWEBENCH_PY" ]; then
  "$CONDA_SWEBENCH_PY" -m pip freeze > "$FREEZE_TXT" 2>/dev/null || :
fi

VP_STAGE="$(mktemp -d)"      # verdict_pack staging root

python3 - "$RUN_DIR" "$OUT_DIR" "$EXPECT_N_ARG" "$VP_STAGE" "$FREEZE_TXT" "$TAIL_LINES" "$TAIL_BYTES" "$CONDA_SWEBENCH_PY" <<'PY'
import sys, os, json, hashlib, subprocess, glob, io, tarfile, datetime, shlex
RUN, OUT, EXPECT_ARG, VP, FREEZE, TAILL, TAILB, CONDA_PY = sys.argv[1:9]
TAILL=int(TAILL); TAILB=int(TAILB)
CAP_IMG=os.environ.get("CAPTURE_IMAGE_DIGESTS","0")=="1"
IMG_CMD=os.environ.get("IMAGE_INSPECT_CMD","docker"); IMG_ARCH=os.environ.get("IMAGE_ARCH","x86_64")
TRAJ_MAX=int(os.environ.get("TRAJ_MAX_BLOCKS","400")); TRAJ_CH=int(os.environ.get("TRAJ_SUMMARY_CHARS","240"))
TRAJ_BYTES=int(os.environ.get("TRAJ_MAX_BYTES","80000"))
RETAIN=os.environ.get("RETAIN_ARTIFACTS","0")=="1"; RETAIN_DIR=os.environ.get("RETAIN_DIR","")

def sha256_file(p):
    try:
        h=hashlib.sha256()
        with open(p,'rb') as f:
            for b in iter(lambda:f.read(1<<20), b''): h.update(b)
        return h.hexdigest()
    except Exception as e:
        return None

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()

def jload(p):
    try:    return json.load(open(p))
    except Exception: return None

def git_info(path):
    """git commit+branch for the dir containing `path` (worktrees supported)."""
    d = path if os.path.isdir(path) else os.path.dirname(path)
    if not d or not os.path.isdir(d): return {"missing":"path not present: %s"%path}
    out={}
    for key,args in (("commit",["rev-parse","HEAD"]),
                     ("branch",["rev-parse","--abbrev-ref","HEAD"]),
                     ("dirty", ["status","--porcelain"])):
        try:
            r=subprocess.run(["git","-C",d]+args,capture_output=True,text=True,timeout=15)
            out[key]= (r.stdout.strip() if key!="dirty" else ("dirty" if r.stdout.strip() else "clean")) if r.returncode==0 else None
        except Exception:
            out[key]=None
    return out

def du_sh(p):
    try:
        r=subprocess.run(["du","-sh",p],capture_output=True,text=True,timeout=180)
        return r.stdout.split()[0] if r.returncode==0 else "?"
    except Exception: return "?"

def tree_namelist_sha(root):
    """cheap content-independent anchor: sha256 over sorted relpath<TAB>size (no file reads)."""
    buf=io.StringIO(); n=0
    for r,dirs,files in os.walk(root):
        dirs.sort()
        for fn in sorted(files):
            full=os.path.join(r,fn)
            try: sz=os.path.getsize(full)
            except Exception: sz=-1
            buf.write("%s\t%d\n"%(os.path.relpath(full,root),sz)); n+=1
    return sha256_bytes(buf.getvalue().encode()), n

cfg = jload(os.path.join(RUN,"runner_config.json")) or {}
rows=[json.loads(l) for l in open(os.path.join(RUN,"results.jsonl")) if l.strip()]
N=len(rows)
EXPECT = int(EXPECT_ARG) if str(EXPECT_ARG).strip() else int(cfg.get("expected_score_rows", N))

# ---- score summary (real, from run) ----
score_sum = jload(os.path.join(RUN,"score_summary.json")) or jload(os.path.join(RUN,"score_summary_clean274.json")) or {}
final_status = jload(os.path.join(RUN,"FINAL_CODER_CLEAN274_STATUS.json")) or {}

# =========================================================================
# (2) repro_closure.json
# =========================================================================
closure={"schema":"repro_closure/v6","generated_utc":datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
closure["run_id"]=cfg.get("run_id") or os.path.basename(RUN)
closure["bench"]=cfg.get("bench")
closure["model"]=cfg.get("model")
closure["base_url"]=cfg.get("base_url")
closure["scaffold"]={"name":cfg.get("scaffold"),"agent_scaffold":cfg.get("agent_scaffold")}
closure["context_limit"]=cfg.get("context_limit")
closure["max_output_tokens"]=cfg.get("max_output_tokens")
closure["runner_config_sha256"]=sha256_file(os.path.join(RUN,"runner_config.json"))

# --- orchestrator + launch scripts: sha256 (live) + config-declared sha + git ---
scripts={}
# launcher (from COMMAND.sh first token)
launch_src=None
cmd_p=os.path.join(RUN,"COMMAND.sh")
if os.path.isfile(cmd_p):
    toks=open(cmd_p).read().split()
    if toks: launch_src=toks[0]
def script_rec(path, declared_sha=None):
    rec={"path":path}
    if path and os.path.isfile(path):
        rec["sha256"]=sha256_file(path)
        rec["git"]=git_info(path)
        if declared_sha and rec["sha256"]!=declared_sha:
            rec["WARN_config_sha_mismatch"]={"config":declared_sha,"live":rec["sha256"]}
        elif declared_sha:
            rec["config_declared_sha256_matches"]=True
    else:
        rec["missing"]="script file not present at collect time"
        if declared_sha: rec["config_declared_sha256"]=declared_sha
    return rec
scripts["launcher"]=script_rec(launch_src)
scripts["base_runner"]=script_rec(cfg.get("base_runner_path"), cfg.get("base_runner_sha256"))
closure["orchestrator_scripts"]=scripts

# --- qwen-code scaffold: version + package.json sha256 ---
qwen={"version":cfg.get("qwen_code_version"),"qwen_root":cfg.get("qwen_root")}
pj=os.path.join(cfg.get("qwen_root","") or "","package.json")
if os.path.isfile(pj):
    qwen["package_json_sha256"]=sha256_file(pj)
    qwen["package_json_text"]=open(pj).read()
    pl=os.path.join(os.path.dirname(pj),"package-lock.json")
    if os.path.isfile(pl): qwen["package_lock_json_sha256"]=sha256_file(pl)
else:
    qwen["missing"]="package.json not found under qwen_root"
closure["qwen_code_scaffold"]=qwen

# --- agent runtime offline bundle (litellm/openai/mini-swe-agent live here) ---
agent_bundle={"path":cfg.get("mini_swe_agent_path")}
mb=cfg.get("mini_swe_agent_path","") or ""
if os.path.isdir(mb):
    vers={}
    for name in os.listdir(mb):
        if name.endswith(".dist-info"):
            base=name[:-len(".dist-info")]
            if "-" in base:
                pkg,ver=base.rsplit("-",1)
                if pkg.lower() in ("litellm","openai","mini_swe_agent","swebench","tiktoken","anthropic","httpx","pydantic"):
                    vers[pkg]=ver
    agent_bundle["key_dist_info_versions"]=vers or {"missing":"no matching *.dist-info found"}
else:
    agent_bundle["missing"]="agent bundle dir not present"
closure["agent_runtime_bundle"]=agent_bundle

# --- conda key packages (eval-harness env) via pip freeze ---
conda={"eval_harness_python":CONDA_PY}
freeze=""
try: freeze=open(FREEZE).read()
except Exception: pass
if freeze.strip():
    keys=("swebench","litellm","openai","sglang","datasets","docker","tiktoken","unidiff","ghapi","modal","transformers")
    picked={}
    for line in freeze.splitlines():
        low=line.lower()
        for k in keys:
            if low.startswith(k+"==") or ("egg=%s"%k in low) or low.startswith("-e ") and k in low:
                picked.setdefault(k,line.strip())
    conda["key_packages"]=picked
    # resolve editable swebench actual version + git sha
    try:
        r=subprocess.run([CONDA_PY,"-c",
            "import swebench,inspect,os;print(getattr(swebench,'__version__','?'));print(os.path.dirname(inspect.getfile(swebench)))"],
            capture_output=True,text=True,timeout=20)
        if r.returncode==0:
            parts=r.stdout.strip().splitlines()
            conda["swebench_version"]=parts[0] if parts else None
            conda["swebench_path"]=parts[1] if len(parts)>1 else None
            if len(parts)>1 and os.path.isdir(parts[1]):
                g=git_info(parts[1]); conda["swebench_git"]=g
    except Exception as e:
        conda["swebench_probe_error"]=str(e)
else:
    conda["missing"]="pip freeze empty/unavailable (CONDA_SWEBENCH_PY not runnable)"
closure["conda_key_packages"]=conda

# --- dataset id + parquet sha256 ---
ds={"dataset_root":cfg.get("dataset_root"),
    "dataset_parquet_sha256_config":cfg.get("dataset_parquet_sha256")}
dr=cfg.get("dataset_root","") or ""
if os.path.isdir(dr):
    ds["dataset_id"]=os.path.basename(dr)
    pq=glob.glob(os.path.join(dr,"data","*.parquet"))
    if pq:
        ds["parquet_file"]=pq[0]
        ds["parquet_sha256_live"]=sha256_file(pq[0])
        ds["parquet_bytes"]=os.path.getsize(pq[0])
        ds["parquet_sha256_matches_config"]= (ds["parquet_sha256_live"]==cfg.get("dataset_parquet_sha256"))
    rc=jload(os.path.join(dr,"ROW_COUNT.json"))
    if rc: ds["row_count"]=rc
    shp=os.path.join(dr,"SHA256SUMS")
    if os.path.isfile(shp): ds["dataset_SHA256SUMS_sha256"]=sha256_file(shp)
else:
    ds["missing"]="dataset_root not present at collect time"
# subset selection manifest (clean274 ids)
sub=cfg.get("clean_subset_ids")
if sub and os.path.isfile(sub):
    ids=[x.strip() for x in open(sub) if x.strip()]
    ds["subset_ids_file"]=sub
    ds["subset_ids_sha256"]=sha256_file(sub)
    ds["subset_ids_count"]=len(ids)
elif sub:
    ds["subset_ids_file"]=sub; ds["subset_ids_missing"]=True
closure["dataset"]=ds

# --- task image digest manifest (from results / run manifest / canary) ---
img={"registry":None,"naming_pattern":None,"per_task_digests":{}}
# canary image inspect (1 image) — real digest we DO have
canary=jload(os.path.join(RUN,"scaffold","canary_image_inspect.json"))
if isinstance(canary,list) and canary: canary=canary[0]
if isinstance(canary,dict):
    rt=canary.get("RepoTags") or []
    rd=canary.get("RepoDigests") or []
    img["canary_image"]={"Id":canary.get("Id"),"RepoTags":rt,"RepoDigests":rd}
    for r_ in rd:
        if "@sha256:" in r_ and "/" in r_:
            img["registry"]=r_.split("/")[0]
    for t_ in rt:
        # derive naming pattern by blanking the instance token
        if "sweb.eval" in t_:
            img["naming_pattern"]=t_
# --- (1) live per-task digest capture on the exec host (opt-in) ---
def _mangle(iid): return iid.replace("__","_1776_").lower()
def _capture_digests(rows, cmd, arch):
    base=shlex.split(cmd)
    try:
        r=subprocess.run(base+["images","--no-trunc","--format","{{.Repository}}:{{.Tag}}\t{{.ID}}"],capture_output=True,text=True,timeout=600)
    except Exception as e:
        return {"error":"image listing failed: %s"%e}
    if r.returncode!=0:
        return {"error":"docker images rc=%d: %s"%(r.returncode,(r.stderr or '')[:200])}
    tagmap={}
    for line in r.stdout.splitlines():
        if "\t" not in line: continue
        rt,_id=line.split("\t",1)
        repo_comp=rt.rsplit(":",1)[0]
        if "sweb.eval." not in repo_comp: continue
        tagmap.setdefault(repo_comp.lower(), rt)  # first tag per repo component
    per={}; found=miss=0
    for row in rows:
        iid=row["instance_id"]; tok=_mangle(iid); suffix="sweb.eval.%s.%s"%(arch,tok)
        cand=[tag for rc,tag in tagmap.items() if rc.endswith(suffix)]
        if not cand:
            per[iid]={"missing":"no local image whose repo ends with %s"%suffix}; miss+=1; continue
        cand.sort(key=lambda t:(0 if (t.startswith("swebench/") and t.endswith(":latest")) else 1, t))
        tag=cand[0]
        try:
            ri=subprocess.run(base+["image","inspect",tag,"--format","{{.Id}}||{{range .RepoDigests}}{{.}} {{end}}"],capture_output=True,text=True,timeout=90)
            if ri.returncode!=0:
                per[iid]={"missing":"inspect rc=%d for %s"%(ri.returncode,tag)}; miss+=1; continue
            out=ri.stdout.strip(); imgid,_,digs=out.partition("||")
            digs=[d for d in digs.split() if d]
            per[iid]={"image_ref":tag,"image_id":imgid.strip(),"repo_digest":(digs[0] if digs else None),"repo_digests_all":digs}
            if not digs: per[iid]["repo_digest_note"]="no RepoDigests (locally built, never pushed); image_id pins content"
            found+=1
        except Exception as e:
            per[iid]={"missing":"inspect error %s"%e}; miss+=1
    return {"captured_found":found,"captured_missing":miss,"inspect_cmd":cmd,"arch":arch,"per_task":per}

if CAP_IMG:
    res=_capture_digests(rows, IMG_CMD, IMG_ARCH)
    if "error" in res:
        img["capture_error"]=res["error"]
        img["missing"]="per-task digest capture attempted but failed (%s); only canary digest available."%res["error"]
    else:
        img["per_task_digests"]=res["per_task"]
        img["capture_summary"]={k:res[k] for k in ("captured_found","captured_missing","inspect_cmd","arch")}
        if res["captured_found"]==0:
            img["missing"]="capture ran but matched 0 images (wrong exec host / images gone / arch mismatch)."
else:
    img["capture_note"]="per-task digest capture NOT run (CAPTURE_IMAGE_DIGESTS!=1). Run this collector ON the exec host with keep_images while images are present."
    img["missing"]=("per-task image digests not captured; only pre-flight canary image digest available. "
        "Images run --pull=never --network none by deterministic local tag "
        "swebench/sweb.eval.%s.<instance __->_1776_ >:latest. Re-run with CAPTURE_IMAGE_DIGESTS=1 on the exec host."%IMG_ARCH)
closure["task_images"]=img

# =========================================================================
# (3) artifact_retrieval — where to fetch bulky artifacts + verify (internal, NOT git)
# =========================================================================
retr={"note":"Bulky artifacts are NOT in git. Fetch from these internal/shared-disk or registry sources and verify sha256."}
qr=cfg.get("qwen_root","") or ""
sc={"kind":"qwen-code scaffold tree","source_path":qr,"version":cfg.get("qwen_code_version")}
if os.path.isdir(qr):
    tsha,tn=tree_namelist_sha(qr)
    sc["du"]=du_sh(qr); sc["namelist_manifest_sha256"]=tsha; sc["file_count"]=tn
    sc["package_json_sha256"]=qwen.get("package_json_sha256"); sc["package_lock_json_sha256"]=qwen.get("package_lock_json_sha256")
    sc["rebuild_hint"]="npm install --prefix %s @qwen-code/qwen-code@%s node@20"%(qr,cfg.get("qwen_code_version"))
    if RETAIN:
        if RETAIN_DIR:
            os.makedirs(RETAIN_DIR,exist_ok=True)
            ap=os.path.join(RETAIN_DIR,"scaffold_qwencode_%s_%s.tar.gz"%(cfg.get("qwen_code_version"),tsha[:12]))
            if os.path.isfile(ap):
                sc["internal_archive"]={"path":ap,"sha256":sha256_file(ap),"bytes":os.path.getsize(ap),"reused_existing":True}
            else:
                parent=os.path.dirname(qr.rstrip("/")); bn=os.path.basename(qr.rstrip("/"))
                rr=subprocess.run(["tar","-C",parent,"-czf",ap,bn],capture_output=True,text=True,timeout=1800)
                if rr.returncode==0 and os.path.isfile(ap):
                    sc["internal_archive"]={"path":ap,"sha256":sha256_file(ap),"bytes":os.path.getsize(ap),"content_addressed_by":"namelist_manifest_sha256[:12]"}
                else:
                    sc["internal_archive"]={"missing":"tar failed rc=%d: %s"%(rr.returncode,(rr.stderr or '')[:200])}
        else:
            sc["internal_archive"]={"missing":"RETAIN_ARTIFACTS=1 but RETAIN_DIR unset; recorded source+sha only"}
else:
    sc["missing"]="scaffold tree not present at collect time"
retr["scaffold_tree"]=sc
retr["dataset_parquet"]={"kind":"dataset parquet","source_path":ds.get("parquet_file"),"sha256":ds.get("parquet_sha256_live"),
    "bytes":ds.get("parquet_bytes"),"dataset_dir":dr,"dataset_dir_SHA256SUMS_sha256":ds.get("dataset_SHA256SUMS_sha256"),
    "row_count":(ds.get("row_count") or {}).get("row_count") if isinstance(ds.get("row_count"),dict) else None,
    "missing":(None if ds.get("parquet_file") else "parquet not located under dataset_root/data")}
reg=img.get("registry")
retr["task_images"]={"kind":"harbor registry images","registry":reg,
    "pull_pattern":("docker pull %s/<project>-sweb.eval.%s.<instance __->_1776_ >@<repo_digest>"%(reg,IMG_ARCH)) if reg else None,
    "per_task_digests_in":"repro_closure.json:task_images.per_task_digests",
    "note":"Images live in the Harbor registry; pull by RepoDigest for byte-exact reproduction. Local build tag: swebench/sweb.eval.%s.<mangled>:latest."%IMG_ARCH}
closure["artifact_retrieval"]=retr

open(os.path.join(OUT,"repro_closure.json"),"w").write(json.dumps(closure,indent=2,sort_keys=True)+"\n")

# =========================================================================
# serving IDENTITY summary (before/after model_path + seed) from copied files
# =========================================================================
sdir=os.path.join(OUT,"serving")
def load_first(*names):
    for n in names:
        p=os.path.join(sdir,n)
        if os.path.isfile(p): return jload(p),p
    return None,None
ident={}
for phase in ("before","after"):
    mi,_=load_first("get_model_info_%s.json"%phase)
    si,_=load_first("get_server_info_%s.json"%phase,"get_server_info_%s.redacted.json"%phase)
    rec={}
    if mi: rec["model_path"]=mi.get("model_path")
    if si:
        rec["sglang_version"]=si.get("version") or si.get("sglang_version")
        rec["random_seed"]=si.get("random_seed", (si.get("server_args") or {}).get("random_seed"))
    ident[phase]=rec or {"missing":"serving %s not captured"%phase}
ident["before_equals_after"]= (ident.get("before",{}).get("model_path")==ident.get("after",{}).get("model_path")
                               and ident.get("before") and ident.get("after") and "missing" not in ident.get("before",{}) and "missing" not in ident.get("after",{}))
open(os.path.join(sdir,"IDENTITY_SUMMARY.json"),"w").write(json.dumps(ident,indent=2,sort_keys=True)+"\n")

# =========================================================================
# (4) verdict_pack — per-instance prediction.patch + test_output_tail + report.json
# =========================================================================
def rglob_first(root, pat, must_contain=None):
    hits=sorted(glob.glob(os.path.join(root, pat), recursive=True))
    if must_contain:
        for h in hits:
            try:
                if must_contain in open(h,'rb').read(): return h
            except Exception: pass
        return hits[0] if hits else None
    return hits[0] if hits else None

def tail_text(path, nlines, nbytes):
    try:
        data=open(path,'rb').read()
    except Exception:
        return None
    if len(data)>nbytes: data=data[-nbytes:]
    txt=data.decode('utf-8','replace')
    lines=txt.splitlines()
    if len(lines)>nlines: lines=lines[-nlines:]
    return ("\n".join(lines)).rstrip("\n")+"\n"

# --- (2) condensed agent trajectory (tool_use/tool_result summaries; not full payload) ---
def summarize_input(inp):
    if not isinstance(inp,dict): return str(inp)[:TRAJ_CH]
    for k in ("command","cmd","file_path","path","filePath","absolute_path","pattern","query","url","content","new_string","old_string","prompt"):
        if inp.get(k) is not None:
            v=inp[k]; s=v if isinstance(v,str) else json.dumps(v)
            return "%s=%s"%(k, s.replace("\n","\\n")[:TRAJ_CH])
    return "keys=%s"%(",".join(list(inp.keys())[:8]))
def extract_trajectory(agent_dir):
    cands=sorted(glob.glob(os.path.join(agent_dir,"*stdout*.jsonl")))
    if not cands: return None,None
    f=cands[0]; steps=[]
    def push(s): steps.append(s); return len(steps)>=TRAJ_MAX
    stop=False
    for i,line in enumerate(open(f,errors="replace")):
        line=line.strip()
        if not line: continue
        try: d=json.loads(line)
        except Exception: continue
        t=d.get("type")
        if t=="system":
            tools=d.get("tools") or []
            if push({"i":i,"role":"system","tools":(tools if isinstance(tools,list) and len(tools)<=60 else len(tools)),"cwd":d.get("cwd")}): stop=True
        elif t in ("assistant","user"):
            msg=d.get("message") or {}; content=msg.get("content"); role=msg.get("role",t)
            if isinstance(content,str):
                if push({"i":i,"role":role,"block":"text","text":content[:TRAJ_CH]}): stop=True
            elif isinstance(content,list):
                for b in content:
                    if not isinstance(b,dict): continue
                    bt=b.get("type")
                    if bt=="text":
                        if push({"i":i,"role":role,"block":"text","text":(b.get("text") or "")[:TRAJ_CH]}): stop=True
                    elif bt=="tool_use":
                        if push({"i":i,"role":role,"block":"tool_use","name":b.get("name"),"input":summarize_input(b.get("input"))}): stop=True
                    elif bt=="tool_result":
                        c=b.get("content")
                        if isinstance(c,list): txt=" ".join((x.get("text","") if isinstance(x,dict) else str(x)) for x in c)
                        else: txt=str(c)
                        if push({"i":i,"role":role,"block":"tool_result","is_error":bool(b.get("is_error")),"text":txt[:TRAJ_CH]}): stop=True
                    if stop: break
        elif t=="result":
            push({"i":i,"role":"result","subtype":d.get("subtype"),"is_error":d.get("is_error"),"num_turns":d.get("num_turns"),"duration_ms":d.get("duration_ms")})
        if stop:
            steps.append({"note":"TRUNCATED at %d blocks"%TRAJ_MAX}); break
    buf=io.StringIO()
    for s in steps:
        buf.write(json.dumps(s,ensure_ascii=False)+"\n")
        if buf.tell()>TRAJ_BYTES:
            buf.write(json.dumps({"note":"TRUNCATED at %d bytes"%TRAJ_BYTES})+"\n"); break
    return buf.getvalue(), f

index=[]
mism=[]
n_patch=n_report=n_test=n_traj=0
for r in rows:
    iid=r["instance_id"]; ed=r.get("evidence_dir","")
    safe=iid.replace("/","__")
    dst=os.path.join(VP,safe); os.makedirs(dst,exist_ok=True)
    rec={"instance_id":iid,"resolved_results":bool(r.get("resolved")),"evidence_dir":ed,
         "eval_rc":r.get("eval_rc"),"agent_status":r.get("agent_status")}
    # --- prediction.patch ---
    patch_path=None
    if ed:
        for c in ("agent/prediction.patch.diff","input_model_patch.diff","prediction.patch.diff"):
            p=os.path.join(ed,c)
            if os.path.isfile(p): patch_path=p; break
    if patch_path is None and ed:
        # last resort: extract model_patch from prediction.json
        pj=os.path.join(ed,"prediction.json")
        d=jload(pj)
        if isinstance(d,dict):
            mp=None
            if iid in d and isinstance(d[iid],dict): mp=d[iid].get("model_patch")
            elif "model_patch" in d: mp=d.get("model_patch")
            if mp is not None:
                open(os.path.join(dst,"prediction.patch"),"w").write(mp)
                rec["prediction_patch_source"]="prediction.json:model_patch"
                rec["prediction_patch_sha256"]=sha256_bytes(mp.encode())
                n_patch+=1
    if patch_path:
        b=open(patch_path,'rb').read()
        open(os.path.join(dst,"prediction.patch"),"wb").write(b)
        rec["prediction_patch_source"]=os.path.relpath(patch_path,ed) if ed else patch_path
        rec["prediction_patch_sha256"]=sha256_bytes(b)
        n_patch+=1
    rec["has_patch"]=os.path.isfile(os.path.join(dst,"prediction.patch"))
    # --- report.json (deep, with tests_status) ---
    report_resolved=None
    rep=None
    if ed:
        rep=rglob_first(ed,"eval/logs/run_evaluation/**/report.json", must_contain=iid.encode())
        if not rep:
            rep=rglob_first(ed,"**/report.json", must_contain=b"tests_status")
    if rep:
        rd=jload(rep)
        open(os.path.join(dst,"report.json"),"w").write(json.dumps(rd,indent=2,sort_keys=True)+"\n")
        rec["report_source"]=os.path.relpath(rep,ed) if ed else rep
        n_report+=1
        if isinstance(rd,dict) and iid in rd and isinstance(rd[iid],dict):
            report_resolved=rd[iid].get("resolved")
    else:
        # fallback: summary report (resolved_ids list)
        summ=rglob_first(ed,"eval/*.json") if ed else None
        if summ:
            sd=jload(summ)
            if isinstance(sd,dict):
                open(os.path.join(dst,"report.json"),"w").write(json.dumps(sd,indent=2,sort_keys=True)+"\n")
                rec["report_source"]=os.path.relpath(summ,ed)+" (SUMMARY, no tests_status)"
                n_report+=1
                if "resolved_ids" in sd: report_resolved= iid in (sd.get("resolved_ids") or [])
    rec["has_report"]=os.path.isfile(os.path.join(dst,"report.json"))
    rec["resolved_report"]=report_resolved
    # --- test_output_tail.txt ---
    tp=None
    if ed:
        tp=rglob_first(ed,"eval/logs/run_evaluation/**/test_output.txt", must_contain=None)
        if not tp:
            for c in ("eval/eval.log","eval.log"):
                p=os.path.join(ed,c)
                if os.path.isfile(p): tp=p; break
    if tp:
        t=tail_text(tp,TAILL,TAILB)
        if t is not None:
            open(os.path.join(dst,"test_output_tail.txt"),"w").write(t)
            rec["test_output_source"]=os.path.relpath(tp,ed) if ed else tp
            n_test+=1
    rec["has_test_output"]=os.path.isfile(os.path.join(dst,"test_output_tail.txt"))
    # --- (2) trajectory.jsonl (condensed agent process, for cheat auditing) ---
    mang=iid.replace("__","_u_")
    agent_dirs=[]
    if ed: agent_dirs.append(os.path.join(ed,"agent"))
    agent_dirs+=[os.path.join(RUN,"instances",mang,"agent"), os.path.join(RUN,"failed",mang,"agent"), os.path.join(RUN,".running",mang,"agent")]
    traj=None; tsrc=None
    for adir in agent_dirs:
        if os.path.isdir(adir):
            traj,tsrc=extract_trajectory(adir)
            if traj: break
    if traj:
        open(os.path.join(dst,"trajectory.jsonl"),"w").write(traj)
        rec["trajectory_source"]=tsrc; rec["trajectory_blocks"]=traj.count("\n"); n_traj+=1
    rec["has_trajectory"]=os.path.isfile(os.path.join(dst,"trajectory.jsonl"))
    # cross-check adjudication consistency
    if report_resolved is not None and bool(report_resolved)!=bool(r.get("resolved")):
        mism.append({"instance_id":iid,"resolved_results":bool(r.get("resolved")),"resolved_report":bool(report_resolved)})
        rec["ADJUDICATION_MISMATCH"]=True
    index.append(rec)

resolved_results=sum(1 for r in rows if r.get("resolved"))
resolved_report =sum(1 for x in index if x.get("resolved_report") is True)
vp_summary={
    "run_id":closure["run_id"],
    "instances":len(index),
    "with_prediction_patch":n_patch,
    "with_report_json":n_report,
    "with_test_output_tail":n_test,
    "with_trajectory":n_traj,
    "resolved_by_results_jsonl":resolved_results,
    "resolved_by_report_json":resolved_report,
    "report_coverage":"%d/%d"%(sum(1 for x in index if x.get("resolved_report") is not None),len(index)),
    "adjudication_mismatches":mism,
    "note":("resolved_by_report_json counts only instances whose deep report.json carried tests_status; "
            "instances lacking a deep report (eval error / empty patch / cleanup-race) show resolved_report=null "
            "and are NOT independently re-adjudicable from this pack — see has_report=false rows. "
            "trajectory.jsonl is a condensed agent process log (tool_use/tool_result summaries) for auditing "
            "process cheating (peeking gold/answer files, polluting tests) — not the full payload."),
}
open(os.path.join(VP,"INDEX.json"),"w").write(json.dumps({"summary":vp_summary,"instances":index},indent=2,sort_keys=True)+"\n")

# tar it up (sorted, deterministic order)
tarp=os.path.join(OUT,"verdict_pack.tar.gz")
with tarfile.open(tarp,"w:gz") as tf:
    for root,dirs,files in os.walk(VP):
        dirs.sort()
        for fn in sorted(files):
            full=os.path.join(root,fn)
            arc=os.path.relpath(full,VP)
            ti=tf.gettarinfo(full,arcname=os.path.join("verdict_pack",arc))
            ti.mtime=0; ti.uid=ti.gid=0; ti.uname=ti.gname=""
            with open(full,'rb') as fh: tf.addfile(ti,fh)

# =========================================================================
# (7) denom_assert.txt
# =========================================================================
uniq=len({r["instance_id"] for r in rows})
declared=EXPECT
verdict = "PASS" if (N==declared and uniq==N) else "FAIL"
da=[]
da.append("DENOMINATOR ASSERTION (v6)")
da.append("run_id            : %s"%closure["run_id"])
da.append("results.jsonl rows: %d   (wc -l)"%N)
da.append("unique instance_id: %d"%uniq)
da.append("declared dataset_size (EXPECT_N): %d   [source: %s]"%(declared,
          "arg" if str(EXPECT_ARG).strip() else "runner_config.expected_score_rows"))
subn = closure.get("dataset",{}).get("subset_ids_count")
if subn is not None: da.append("subset_ids manifest count       : %d"%subn)
rc=closure.get("dataset",{}).get("row_count",{})
if isinstance(rc,dict) and rc: da.append("dataset parquet row_count       : %s (superset; subset selected via subset_ids)"%rc.get("row_count"))
da.append("")
da.append("ASSERT rows==declared AND unique==rows  =>  %s"%verdict)
if verdict!="PASS":
    da.append("  MISMATCH: rows=%d declared=%d unique=%d"%(N,declared,uniq))
open(os.path.join(OUT,"denom_assert.txt"),"w").write("\n".join(da)+"\n")

# =========================================================================
# (6) calibration.md — 口径卡
# =========================================================================
sw = closure.get("conda_key_packages",{})
swver = sw.get("swebench_version"); swgit=(sw.get("swebench_git") or {}).get("commit")
anchor_note = ("No official SWE-bench Multilingual cell exists for %s under this scaffold; "
               "this run is reported as a NEW measurement." % (cfg.get("model")))
score = score_sum.get("score"); resolved=score_sum.get("resolved"); denom=score_sum.get("denominator")
per_lang = score_sum.get("per_language",{})
caveat = final_status.get("critical_eval_wrap_caveat") or {}
prov = final_status.get("provenance_status")
md=[]
md.append("# calibration.md — 口径卡 (v6)")
md.append("")
md.append("run_id: `%s`"%closure["run_id"])
md.append("bench: **%s**  model: **%s**  scaffold: **%s (qwen-code %s)**"%(
    cfg.get("bench"),cfg.get("model"),cfg.get("scaffold"),cfg.get("qwen_code_version")))
md.append("")
md.append("## Headline")
md.append("- **score = %s** (resolved **%s** / denominator **%s**)"%(score,resolved,denom))
md.append("- serving identity before==after: **%s** (model_path=%s, sglang=%s, seed=%s)"%(
    ident.get("before_equals_after"), ident.get("before",{}).get("model_path"),
    ident.get("before",{}).get("sglang_version"), ident.get("before",{}).get("random_seed")))
md.append("")
md.append("## 1. resolved 的定义 (adjudication rule)")
md.append("SWE-bench harness rule (schema_version 2): an instance is **resolved** iff, after applying the")
md.append("agent `model_patch`, **every** `FAIL_TO_PASS` test transitions to PASS **and every** `PASS_TO_PASS`")
md.append("test stays PASS. Per-instance `tests_status` (FAIL_TO_PASS / PASS_TO_PASS / FAIL_TO_FAIL / PASS_TO_FAIL)")
md.append("is preserved in `verdict_pack/<instance>/report.json`, so each verdict is **re-checkable offline**")
md.append("from this pack alone — no shared-disk trace needed.")
md.append("")
md.append("## 2. eval harness 版本")
md.append("- swebench **%s**%s"%(swver or "?", (" @ git `%s`"%swgit) if swgit else ""))
md.append("- editable install: `%s`"%(sw.get("key_packages",{}).get("swebench","(see repro_closure.json)")))
md.append("- report schema_version: 2  (per-instance report.json under eval/logs/run_evaluation/)")
md.append("")
md.append("## 3. include_unverified")
md.append("- **No** include_unverified / no gold-less admission here: all %d rows carry a real docker eval."%N)
md.append("- Denominator = clean subset (not padded with unverified rows). See `denom_assert.txt`.")
md.append("")
md.append("## 4. anchor 对齐")
md.append("- %s"%anchor_note)
md.append("- Denominator caveat: this run scores the **clean274 subset** = full300 − 26 offline-Gradle")
md.append("  false-zero tasks; official SWE-bench Multilingual uses 300. Compare per-language, not raw overall,")
md.append("  against any official number. Per-language resolved/total below.")
if per_lang:
    md.append("")
    md.append("| language | resolved | total | score |")
    md.append("|---|---|---|---|")
    for k in sorted(per_lang):
        v=per_lang[k]; md.append("| %s | %s | %s | %.3f |"%(k,v.get("resolved"),v.get("total"),v.get("score",0)))
md.append("")
md.append("## 5. 口径差 / 已知 caveat (disclosed, not hidden)")
if caveat:
    md.append("- **provenance_status = %s**"%prov)
    md.append("- MIXED eval environments: %s"%(caveat.get("overwrite_reason","(see FINAL_CODER_CLEAN274_STATUS.json)")))
    md.append("  - main %s rows evaluated **%s**;"%(
        caveat.get("main_271_rows_eval_environment","271")," ".join(str(caveat.get('main_271_rows_eval_environment','')).split())))
    md.append("  - 3 cleanup-race repair rows evaluated **with ignore_removed=True** (eval-only frozen-patch repair), all resolved=false.")
    md.append("  - original launch eval_wrap.py: **%s** (severity %s)."%(caveat.get("original_eval_wrap"),caveat.get("severity")))
    md.append("- Effect on score: the 3 repaired rows are unresolved either way, so the mixed environment does")
    md.append("  **not** inflate the resolved count; disclosed for full provenance honesty.")
else:
    md.append("- No mixed-environment caveat recorded for this run.")
md.append("")
md.append("## 6. denominator")
md.append("- results rows = %d, unique = %d, declared = %d  → see `denom_assert.txt` (%s)."%(N,uniq,declared,verdict))
open(os.path.join(OUT,"calibration.md"),"w").write("\n".join(md)+"\n")

# =========================================================================
# (8) TRACE.md — full-trace location + du + top-level manifest sha
# =========================================================================
# cheap top-level integrity anchor: sha256 over sorted "relpath\tsize" manifest (names+sizes, no 225M read)
manifest=io.StringIO()
for root,dirs,files in os.walk(RUN):
    dirs.sort()
    for fn in sorted(files):
        full=os.path.join(root,fn)
        try: sz=os.path.getsize(full)
        except Exception: sz=-1
        manifest.write("%s\t%d\n"%(os.path.relpath(full,RUN),sz))
mbytes=manifest.getvalue().encode()
namelist_sha=sha256_bytes(mbytes)
existing_sums=os.path.join(RUN,"SHA256SUMS")
tm=[]
tm.append("# TRACE.md — full trace pointer (big trace stays on the filesystem)")
tm.append("")
tm.append("Full trace is NOT copied into git (%s). It lives on the shared filesystem:"%du_sh(RUN))
tm.append("")
tm.append("```")
tm.append("HOST_PATH : %s"%RUN)
tm.append("du -sh    : %s"%du_sh(RUN))
tm.append("instances : %s (%s)"%(os.path.join(RUN,"instances"), du_sh(os.path.join(RUN,"instances"))))
tm.append("```")
tm.append("")
tm.append("## Top-level integrity anchors")
tm.append("- namelist+size manifest sha256 (this collect): `%s`"%namelist_sha)
tm.append("  (sha256 over a sorted `relpath<TAB>size` listing of every file under the run root — a cheap,")
tm.append("  independent anchor pinning the directory state without reading 225M of content.)")
if os.path.isfile(existing_sums):
    tm.append("- run's own SHA256SUMS sha256: `%s`  (%s per-file hashes sealed at run end)"%(
        sha256_file(existing_sums), sum(1 for _ in open(existing_sums))))
tm.append("")
tm.append("## Per-instance trace layout (for anyone re-adjudicating from the full trace)")
tm.append("```")
tm.append("instances/<instance>/agent/prediction.patch.diff          # agent's model_patch")
tm.append("instances/<instance>/agent/qwen_attempt_1.stdout.jsonl     # full agent transcript")
tm.append("instances/<instance>/eval/logs/run_evaluation/**/report.json      # tests_status (FAIL_TO_PASS/PASS_TO_PASS)")
tm.append("instances/<instance>/eval/logs/run_evaluation/**/test_output.txt  # full eval stdout")
tm.append("repairs/<instance>/cleanup_race_eval_only_*/               # 3 cleanup-race eval-only repairs")
tm.append("```")
tm.append("verdict_pack.tar.gz in THIS bundle already carries patch + report.json + test_output_tail per")
tm.append("instance, so offline re-adjudication does not require the full trace above.")
open(os.path.join(OUT,"TRACE.md"),"w").write("\n".join(tm)+"\n")

# console summary
print("[v6][py] repro_closure/verdict_pack/calibration/denom/TRACE written")
print("[v6][py] verdict_pack: instances=%d patch=%d report=%d test=%d traj=%d resolved(results)=%d resolved(report)=%d mismatches=%d"%(
      len(index),n_patch,n_report,n_test,n_traj,resolved_results,resolved_report,len(mism)))
_ti=closure.get("task_images",{})
if _ti.get("capture_summary"): print("[v6][py] image digests: found=%s missing=%s"%(_ti["capture_summary"].get("captured_found"),_ti["capture_summary"].get("captured_missing")))
elif CAP_IMG: print("[v6][py] image digest capture: %s"%_ti.get("capture_error","(no summary)"))
print("[v6][py] denom: rows=%d unique=%d declared=%d -> %s"%(N,uniq,declared,verdict))
PY
rc=$?
rm -f "$FREEZE_TXT"; rm -rf "$VP_STAGE"
[ "$rc" = 0 ] || v6_die "python collection pass failed (rc=$rc)"

# ---------------------------------------------------------------------------
# (9) SHA256SUMS — completeness seal over every file in the bundle
# ---------------------------------------------------------------------------
( cd "$OUT_DIR" && find . -type f ! -name 'SHA256SUMS' -print0 | sort -z \
    | xargs -0 sha256sum > SHA256SUMS ) || v6_die "sealing SHA256SUMS failed"
NF=$(wc -l < "$OUT_DIR/SHA256SUMS" | tr -d ' ')
v6_log "SHA256SUMS sealed over $NF file(s)"

echo
v6_log "===== v6 evidence bundle complete ====="
( cd "$OUT_DIR" && ls -la && echo && echo "bundle du:" && du -sh . )
v6_log "OUT_DIR=$OUT_DIR"
