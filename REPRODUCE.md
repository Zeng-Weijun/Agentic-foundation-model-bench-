# REPRODUCE.md — 12 open-weight 30B bench reproductions (turnkey)

This is the one document you follow to reproduce every sealed score in this repo.
Two open-weight models (`Qwen3-Coder-30B-A3B-Instruct`, `Qwen3-30B-A3B-Instruct-2507`)
were run through **6 agentic software benchmarks** with the **same native `qwen-code`
scaffold** and each benchmark's **own official judge**. Every score below is
**dual-signed REAL** (two independent blind audits) with a sealed evidence bundle.

> **Golden rule, read first:** neither the relay nor self-hosted sglang validates
> the request `model` field — both return HTTP 200 while echoing back whatever name
> you sent. A run is attributable to a model **only** by the serving identity
> `(port, /get_model_info model_path, random_seed)`, never by a label in a config,
> a response, or an agent trace. This is why every launcher captures serving
> identity `before` and `after` and aborts on mismatch.

---

## 0. Topology — who runs what

```
  ┌─────────────┐   OpenAI-compatible HTTP (no proxy)   ┌──────────────────────────────┐
  │  KVM pod    │ ────────────────────────────────────▶ │  sglang serving pod .147     │
  │ (bench      │   :30001  Qwen3-Coder-30B-A3B-Instruct │  8×H200, cards 4-7 only      │
  │  executor)  │   :30000  Qwen3-30B-A3B-Instruct-2507  │  sglang 0.5.13, tp2, ctx262k │
  │ Docker +    │ ◀──────────────────────────────────── │                              │
  │ shared FS   │        model output (streamed)         └──────────────────────────────┘
  └─────────────┘
        │  per-case task container (repoarena / SWE-bench / terminus-2 / …)
        │  + native qwen-code inside, judge = each bench's OWN grader (no LLM judge)
        ▼
  evidence bundle  ->  experiments/runs/<line>/   (results.jsonl, summary, calibration, verdict)

  Judge/user-sim benches (τ²/τ³, VitaBench) call a GPT relay for the *environment*;
  that relay is reachable from `dev` ONLY. The 12 lines here use NO relay in scoring.
```

- **Serving pod**: `slime-77777210-q9tqc … .pod` (pod_ip `100.100.104.147`, namespace
  `ailab-sciverseh`). Cards 0-3 belong to a co-tenant — never bind them.
- **Executor**: KVM bench pod (`env-kvm-57740737-bzw56`), Docker + shared FS.
- **Shared FS root** (`$B`): `/mnt/shared-storage-user/mineru2-shared/zengweijun`.

---

## 1. Start serving (prerequisite for all 12)

Run on the serving pod, verbatim from `experiments/serving/sglang_launch_20260711.sh`
(`PATH`/`LD_LIBRARY_PATH` exports are needed or `nvidia-smi` is invisible):

```bash
MODEL_ROOT=/mnt/shared-storage-user/mineru2-shared/zengweijun/models
export PATH=/usr/local/nvidia/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/nvidia/lib64:${LD_LIBRARY_PATH:-}

# Instruct-2507 on cards 4,5 -> :30000
tmux new-session -d -s sgl_instruct \
  "CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-30B-A3B-Instruct-2507 \
     --served-model-name Qwen/Qwen3-30B-A3B-Instruct-2507 \
     --tp-size 2 --host 0.0.0.0 --port 30000 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen --trust-remote-code 2>&1 | tee /tmp/sgl_instruct.log"

# Coder-30B on cards 6,7 -> :30001
tmux new-session -d -s sgl_coder \
  "CUDA_VISIBLE_DEVICES=6,7 python -m sglang.launch_server \
     --model-path $MODEL_ROOT/Qwen3-Coder-30B-A3B-Instruct \
     --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
     --tp-size 2 --host 0.0.0.0 --port 30001 \
     --context-length 262144 --mem-fraction-static 0.85 \
     --tool-call-parser qwen3_coder --trust-remote-code 2>&1 | tee /tmp/sgl_coder.log"
```

**Serving identity fingerprint** (assert this via `GET :<port>/get_model_info` and
`/get_server_info` — captured in `experiments/serving/SERVING_CONFIG_20260711_147.json`):

| Port | Model | `model_path` basename | `random_seed` | `tool_call_parser` | tp | ctx | mem_frac |
|---|---|---|---|---|---|---|---|
| **30001** | Qwen3-Coder-30B-A3B-Instruct | `Qwen3-Coder-30B-A3B-Instruct` | **484925000** | `qwen3_coder` | 2 | 262144 | 0.85 |
| **30000** | Qwen3-30B-A3B-Instruct-2507 | `Qwen3-30B-A3B-Instruct-2507` | **61643818** | `qwen` | 2 | 262144 | 0.85 |

sglang version `0.5.13` on both. Client output cap used by launchers: `65536`
(input+history+output share the 262144 window).

---

## 2. Load offline images

Each Docker-backed bench consumes **pre-staged** image tars from the shared FS
(offline pod = no pulls). Generic check/load:

```bash
scripts/load_offline_images.sh --check      # verify tars vs manifest, no pull
scripts/load_offline_images.sh              # docker load the staged tars
```

Per-bench staging helpers (run once, on an internet host, then load on the pod):

| Bench | Stage helper | Image / dataset |
|---|---|---|
| RepoZero | `scripts/stage_repozero_image.sh --execute` | `ghcr.io/jessezzzzz/repoarena-new:latest` (single base image carries all 400 cases) |
| DeepSWE | `scripts/snapshot_deepswe_dataset.sh` | 113 per-task images |
| NL2Repo | `scripts/snapshot_nl2repo_dataset.sh` | 104 base images + offline wheelhouse |
| Multilingual | `scripts/snapshot_swebench_multilingual_dataset.sh` | 300 instance images (Java/C++ from offline p0) |
| SWE-V | (SWE-bench Verified images, staged on the KVM pod) | 500 instance images |
| TB2.1 | `runners/tb21_harness/…` + `tb2-offline/*` | 89 terminus-2 task images |

---

## 3. The 12 lines — score ↔ command ↔ evidence

Denominators: SWE-V 500, TB2.1 89, Multilingual 300, DeepSWE 113, RepoZero 400,
NL2Repo 104. Model = Coder on `:30001`, Instruct-2507 on `:30000`.

| # | Bench × Model | Port | Turnkey runner | Honest score (caliber) | Evidence bundle | Harness defect |
|--:|---|:--:|---|---|---|:--:|
| 1 | **SWE-V** × Coder | 30001 | `experiments/runs/swev_coder_full500_v5_147/launch.sh` | **46.8%** (234/500) | `swev_coder_full500_v5_147/` | — |
| 2 | **SWE-V** × Instruct | 30000 | `experiments/runs/swev_instruct2507_full500_v5_147/launch.sh` | **24.0%** (120/500) | `swev_instruct2507_full500_v5_147/` | — |
| 3 | **TB2.1** × Coder | 30001 | `experiments/runs/tb21_coder_terminus2_147/launch.sh coder` | **11.24%** (10/89) | `tb21_coder_terminus2_147/` | —¹ |
| 4 | **TB2.1** × Instruct | 30000 | `experiments/runs/tb21_instruct2507_terminus2_147/launch.sh instruct` | **3.37%** (3/89) | `tb21_instruct2507_terminus2_147/` | —¹ |
| 5 | **Multilingual** × Coder | 30001 | `experiments/runs/sweml_coder_full300_147/launch.sh coder` | **23.33%** (70/300, set-e) · raw 24.33% (73/300) | `sweml_coder_full300_147/` | **set-e** |
| 6 | **Multilingual** × Instruct | 30000 | `experiments/runs/sweml_instruct2507_full300_147/launch.sh instruct2507` | **9.33%** (28/300, set-e) · raw 10.67% (32/300) | `sweml_instruct2507_full300_147/` | **set-e** |
| 7 | **DeepSWE** × Coder | 30001 | see §4 (Path A driver) | **0.00%** (0/113; 0/106 valid) | `deepswe_coder_pathA_147/` | — |
| 8 | **DeepSWE** × Instruct | 30000 | §4 with `:30000` / Instruct model | **0.00%** | *not committed — regenerate (REPRO_GAPS)* | — |
| 9 | **RepoZero** × Coder | 30001 | `scripts/run_repozero_offline.sh --execute --mode full` | **24.5%** (98/400, 10s·node20) · official 5s **23.75%** (95/400) · node18 floor 24.25% (97/400) | `repozero_coder_full400_147/` | **eval-timeout + node-seam** |
| 10 | **RepoZero** × Instruct | 30000 | `scripts/run_repozero_offline.sh --execute --mode full` + `:30000` env (§4) | **11.50%** (node18) · 12.75% (node20·10s) | *not committed — regenerate (REPRO_GAPS)* | **eval-timeout + node-seam** |
| 11 | **NL2Repo** × Coder | 30001 | `experiments/runs/nl2repo_coder_full104_147/scripts/full104_launch.sh` | **14.29%** honest (base-image-leak) · raw macro 15.55% (95 model-valid) | `nl2repo_coder_full104_147/` | **base-image-leak** |
| 12 | **NL2Repo** × Instruct | 30000 | `full104_launch.sh` with `:30000` / Instruct model | **1.48%** honest · raw 4.03% (leak) | *not committed — regenerate (REPRO_GAPS)* | **base-image-leak** |

¹ TB2.1's strict gate self-reports `status=blocked` because `ready` demands an oracle
89/89; **every** real model run is "blocked" by that gate. The score `10/89` is
`clean_pass` with `infra_fail=0` and is promoted by the v4 rules (same path that
promoted the gpt-5.5 63/89 anchor). Not a scoring inflation — see the bundle's `launch.sh` NOTES.

**Caliber tags:** `set-e` = SWE-bench-Multilingual honest number after correcting the
C++/Java fail-fast defect (§5); `5s`/`10s` = RepoZero per-sample eval wall; `node18`/`node20`
= RepoZero eval node; `base-image-leak` = NL2Repo number after removing base-image
false-positives. Where "raw" ≠ "honest", the honest number is the one to cite.

---

## 4. Per-line run commands (detail)

All launchers run **on the KVM executor pod**, from a local `tmux` + `ssh` (so an SSH
drop can't kill a multi-hour run). All capture serving identity before/after.

### SWE-bench Verified (500) — lines 1-2
Runner: `scripts/full500_qwencode_orchestrator_v21.py` (qwen-code `0.15.6`, concurrency 15).
```bash
# Coder (line 1) — sealed 234/500 = 46.8%
bash experiments/runs/swev_coder_full500_v5_147/launch.sh
# Instruct (line 2) — sealed 120/500 = 24.0%
bash experiments/runs/swev_instruct2507_full500_v5_147/launch.sh
```
The launch.sh pins `BASE=http://100.100.104.147:3000{1|0}/v1`, asserts `get_model_info`
carries the expected weights, then runs the orchestrator to `results.jsonl` (500 rows).

### Terminal-Bench 2.1 (89) — lines 3-4
Runner: `full_run_147.sh <coder|instruct>` → `stage_tb21_official_qwen_launcher*.sh`
(official **terminus-2** harness, `--concurrency 32 --attempts all --timeout-sec 7200`,
pass@1). r7 frozen dataset, `network_mode: none` per task.
```bash
bash experiments/runs/tb21_coder_terminus2_147/launch.sh    coder     # 10/89 = 11.24%
bash experiments/runs/tb21_instruct2507_terminus2_147/launch.sh instruct  # 3/89 = 3.37%
# Instruct needs the patched launcher copy (accepts Instruct-2507); see the launch.sh header.
```

### SWE-bench Multilingual (300) — lines 5-6
Runner: `launch_full300_qwencode_147.sh <coder|instruct2507>` →
`full300_swemultilingual_qwencode_orchestrator_v21.py` (qwen-code `0.16.2`, `SWEML_CONCURRENCY=8`,
swebench 4.1.0). Guarded — set `FULL300_ALLOW=YES` to actually launch.
```bash
FULL300_ALLOW=YES bash experiments/runs/sweml_coder_full300_147/launch.sh coder        # 73/300 raw -> 70/300 honest (set-e)
FULL300_ALLOW=YES bash experiments/runs/sweml_instruct2507_full300_147/launch.sh instruct2507  # 32/300 raw -> 28/300 honest (set-e)
```

### DeepSWE (113) — lines 7-8
Runner: DeepSWE **Path A** native-qwen-code driver `deepswe_qwencode_driver.py` + orchestrator
(same in-container mechanism as RepoZero). No `launch.sh` is vendored in the bundle; the
generation + audit run roots are pinned in `experiments/runs/deepswe_coder_pathA_147/TRACE.md`:
```
$B/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/full113_20260712T114730Z/<task>/agent/
$B/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/audit_full113_20260712T173528Z/<task>/
```
Result is a **defensible 0**: on 106 valid tasks `gold => reward=1` (judge correct) and the
agent scores 0 on every one (`gold_validation/`). Instruct (line 8) = same runner on `:30000`;
score 0, evidence not committed.

### RepoZero Py2JS (400) — lines 9-10  ← NEW turnkey wrapper `scripts/run_repozero_offline.sh`
Wraps the committed orchestrator+driver
(`experiments/runs/repozero_coder_full400_147/scripts/`). Both judging calibers switch on flags:
```bash
# Coder, committed caliber (10s / qwen node v20) -> 98/400 = 24.50%
scripts/run_repozero_offline.sh --execute --mode full

# RepoZero OFFICIAL 5s caliber -> 95/400 = 23.75%
scripts/run_repozero_offline.sh --execute --mode full --eval-timeout 5

# node18 image-node floor (24.25%) is analytical only -> the script fails closed with a pointer
scripts/run_repozero_offline.sh --execute --eval-node node18

# 4-case smoke (grader-real + agent), no full run:
scripts/run_repozero_offline.sh --execute --mode smoke

# Instruct (line 10) — swap endpoint + model (regenerates the missing bundle):
REPOZERO_BASE_URL=http://100.100.104.147:30000/v1 \
REPOZERO_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507 \
  scripts/run_repozero_offline.sh --execute --mode full
```
Preview any command's exact orchestrator invocation with `--dry-run` (safe anywhere).
Serving-free official 5s re-judge of already-generated `.mjs`:
`experiments/runs/repozero_coder_full400_147/scripts/rejudge_official5s.py`.

### NL2RepoBench (104) — lines 11-12
Runner: `experiments/runs/nl2repo_coder_full104_147/scripts/full104_launch.sh`
(native qwen-code, `--network none` + offline wheelhouse, scoring = faithful port of
NL2RepoBench `openhands/post_processor.py`, concurrency 8, setsid).
```bash
bash experiments/runs/nl2repo_coder_full104_147/scripts/full104_launch.sh    # macro 15.55% raw (95 model-valid) -> 14.29% honest
# Instruct (line 12): same script pointed at :30000 / Instruct model; 4.03% raw -> 1.48% honest.
```
The prompt is delivered via **stdin** (the `argv`-overflow fix); `start.md` ≥ 128 KB blows
`MAX_ARG_STRLEN` if inlined into `-p`. Pre-fix driver kept as `nl2repo_qwencode_driver.py.PREFIX_argv_bug`.

---

## 5. Harness judging-defect clinic (4 disclosed defects)

These are **grader** (not model) issues found by the audits. Each has a switchable /
corrected caliber; the honest score is the corrected one.

| Defect | Bench | Mechanism | Impact | How to switch / correct |
|---|---|---|---|---|
| **set-e** | Multilingual (5,6) | `eval.sh` runs `set -uxo pipefail` but **omits `-e`**, so a C/C++/Java **compile failure doesn't abort** — the test then runs against a **baked pre-compiled stale binary** → false PASS / false resolved. (SWE-V is pure-Python → **zero** such false-positives, which is why SWE-V carries no defect.) | **7 false-positives:** Coder 73→70 (24.33→**23.33%**); Instruct 32→28 (10.67→**9.33%**) | Remove the stale-binary C/C++/Java false-PASS cases (rebuild-hash check); score per official **per-language** cells |
| **eval-timeout** | RepoZero (9,10) | Driver default per-sample wall = 10s, but RepoZero official hardcodes **5s** (`evaluate/eval_py2js_docker.py` L52 & L59); 10s admits passes 5s rejects | Coder 98/400 (10s) → **95/400 = 23.75%** (5s); Instruct 12.75% (10s) → 12.25% (5s) | `run_repozero_offline.sh --eval-timeout 5`, or the serving-free `rejudge_official5s.py` |
| **node-seam** | RepoZero (9,10) | Eval `node <entry>.mjs` resolves to the **mounted qwen node v20.20.2**, not the image's native **v18.19.1** (`start_container` puts qwen first on `PATH`; `dexec_plain` doesn't override); node20 auto-accepts some ESM/exports node18 rejects | Coder **0.25pp** (98→97/400 = 24.25%, only `rsa/test11`); **Instruct 1.25pp** (5 cases, 12.75→**11.50%**; A+B 5/5 exact match) | Documented floor (AUDIT_NOTES §3); `--eval-node node18` is fail-closed (full node18 re-run needs a driver PATH override, not wired) |
| **base-image-leak** | NL2Repo (11,12) | The offline overlay didn't cover the base image's `site-packages`, so some target packages import straight from the base → false-POSITIVE resolves (e.g. `databases` 0.922 with turns=0) | macro 15.55% → **14.29%** honest (Coder); 4.03% → **1.48%** (Instruct) | Isolate base-leak false-positives out of the model-valid denominator (see `calibration.md` / `taxonomy.json`) |

Not in the 4: TB2.1's `status=blocked` gate (§3 footnote 1) is an *inherent oracle-89/89
gate*, not a scoring bug; the DeepSWE `NO_PROXY` pollution was a per-run fix that left the
0 unchanged.

---

## 6. Serving-identity discipline (why the scores are attributable)

sglang does **not** validate the request `model` field — ask `:30000` for the Coder
name and it returns 200 while running Instruct-2507. So identity is pinned three ways,
and every launcher enforces it:

1. **Port** — Coder `:30001`, Instruct `:30000` (physically separate sglang processes).
2. **`/get_model_info` `model_path`** — the on-disk weights directory (captured
   `before` and `after`; launchers `exit 3` on mismatch).
3. **`random_seed`** — `484925000` (Coder) vs `61643818` (Instruct); distinct
   `config.json` inodes prove the two ports are not a relabel of one process.

Never trust the `model` string in a request, a response, or an agent trace. Record the
endpoint identity, not the name.

---

## 7. Turnkey status

Reproducible today from a fresh clone + the serving pod + staged shared-FS assets:
lines 1-7, 9, 11 (all with committed evidence bundles), plus lines 8/10/12 via the same
runner pointed at `:30000` (evidence not yet committed). Open items, unification, and the
13th bench are tracked in **`REPRO_GAPS.md`**.
