# RepoZero official-protocol run — pre-launch spec (Pod B, by-85, 2026-07-04)

**Purpose:** pre-launch spec for the RepoZero **official-protocol** run (official Mini-SWE-Agent scaffold + pass@1 single + official 5s per-case timeout + gpt-5.4-mini via bench relay 18540). Line = "官方协议 + 无锚存档" (official leaderboard has no GPT models → run their protocol, archive as no-anchor). **Read-only spec — NO run/model call executed; no Pod A/B runtime touched (full89 running Pod A c=89, full500 running Pod B).** Official repo pinned `@39308b1` (`/mnt/.../nips2026/repozero_eval/RepoZero`).

**★ Run host = Pod B `env-kvm-57740737-bzw56`** (NOT dev). Correction: bench relay **18540 (100.96.122.22, dev tmux) is the POD-FACING relay** — pods hit it directly (Pod A's 89 containers + Pod B c=50 are using it now; 86 verified pod→18540 = 200). It is **not** the old SkillForge Tailscale dev-only relay. dev (8C/16G) hosts the relay body and must not carry the solver load. **Launch timing = AFTER full89 收官** — relay budget is 149/150 now (too full); after full89 finishes, ~50 (full500) + 8 (this) is comfortable. **Launch order awaits lead.**

---

## ① Official Mini-SWE-Agent runner + config (verified from source @39308b1)

**Solver:** `run_py2js/run_all_loop_mini_openai.py` (OpenAI provider; `_anthropic` variant also exists — use OpenAI for relay). **Evaluator:** `evaluate/eval_py2js_mini.py`. Config = **hardcoded module globals + main() locals — NO argparse.** Exact overrides:

| param | source (file:line) | default | set to | note |
|---|---|---|---|---|
| model | `run_all_loop_mini_openai.py:9` `model_name` | `"deepseek-v3.1-250821"` | `"gpt-5.4-mini"` | hardcoded — must edit |
| api_base | `:10` `os.environ.get("QIANFAN_API_URL", …)` | qianfan | env `QIANFAN_API_URL=http://100.96.122.22:18540/v1` | reads env; no edit |
| provider | `:11` | `"openai"` | keep | ok |
| concurrency | `:12` `num_processes` | `10` | **8** (start) | hardcoded — edit |
| **attempts (pass@1)** | `main()` `max_retries` | **`2`** | **`1`** | ⚠ default 2 = loop retries; **official pass@1 SINGLE ⇒ set 1** |
| mini bin | `:14` `MINI_SWE_AGENT_BIN` | `mini` | PATH after offline install | see ② |
| agent per-call timeout | `run_mini_swe_agent()` `subprocess.run(..., timeout=30)` | 30s | keep | agent-side, ≠ eval 5s |

**Mini invocation (~:52):** `mini --model openai/{model_name} -y --exit-immediately …` — reads `OPENAI_API_KEY` + base-url from env/mini config.
**Eval:** `python <py>` and `node <js>` each `timeout=5` (lines 22/26 = official 5s per-case), compare cleaned output → `all_pass`. `NODE_BIN` env. Output `.mjs` under `Py2JS/output_loop_mini/{model}_retry{max_retries}/`.
**Prompt contract (baked in):** JS = pure ESM, Node.js, **ZERO external npm deps** (~:107/114) → no `npm install`.

---

## ② Pod B run requirements — probed + staged (prep DONE)

| need | Pod B status (probed) | action |
|---|---|---|
| `python3` | ✅ `/bin/python3` = **3.10.12**, pip 25.1 | ok — wheels below target cp310 |
| `node` | ✅ `/usr/local/bin/node` = **v16.14.0** | present. ⚠ node 16 is EOL; the eval JS is basic zero-dep ESM (`.mjs`) so v16 should run it — **preflight: smoke one `node <case>.mjs`**; if it errors on newer syntax, stage node 20 (dev has v20.20.0) to shared FS + set `NODE_BIN`. |
| **mini-swe-agent** | staged ✅ (was NOT installed on any pod) | **✅ DONE — pip-downloaded on dev to shared FS:** `mini_swe_agent-2.4.4` + 76 deps = **77 wheels, 0 sdists** (litellm-1.90.3, openai-2.44.0, tiktoken-0.11.0 cp310, pydantic-2.13.4, …). Path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/wheels/mini_swe_agent/` (manifest: `../mini_swe_agent_wheels_manifest_20260704.txt`). **Offline install on Pod B:** `python3 -m pip install --no-index --find-links /mnt/.../repozero_eval/wheels/mini_swe_agent mini-swe-agent` → puts `mini` on PATH. |
| relay 18540 | ✅ pod-reachable (86 verified pod→200; pods using it now) | preflight curl (below) |
| repozero docker image (`repoarena-new`) | staged tar exists | **NOT needed for official protocol** — eval runs `node`/`python` locally (no docker sandbox in `eval_py2js_mini.py`); confirm mini-swe-agent env = local subprocess (default) not docker. |
| dataset | ✅ `Py2JS/dataset` (446 `.py`) | ok |

**Bottom line:** Pod B is ready except (a) `pip install` the staged wheels (offline, 1 cmd) and (b) a one-case node-16 smoke. No dev load, no docker image, no network on the pod.

---

## ③ 73-timeout residual extraction — command VERIFIED + shared-FS path

⚠ pg89q `/tmp/rz_pilot/*` evaporated (tmpfs) — but the rerun `results.jsonl` is on **shared FS** (persistent):
```
RES=<former-local-gpt-result-root-removed-from-current-publication>
```
242 rows; fields `case, all_pass, codex_returncode, codex_timeout, entry, …`. **Extract (run on dev, read-only):**
```bash
python3 -c "import json,os
rows=[json.loads(l) for l in open(os.environ['RES'])]
to=[r['case'] for r in rows if r.get('codex_timeout')]
print(len(to)); print(' '.join(to))"
```
**✅ VERIFIED on shared FS: total=242, `codex_timeout`=73 == `codex_returncode==124`=73 — matches REPOZERO_LANE_HANDOFF §6 exactly.** No pg89q dependency.
**Scope note:** the former internal codex-line result and its subset counts were removed from the current publication tree on 2026-07-21. The official-protocol run was planned as an independent full benchmark; do not recover a local GPT score from this pre-launch spec.

---

## ④ Pod B launch command draft + preflight checklist

**Preflight (on Pod B, all must pass before launch):**
1. **Relay health + reachability**: `curl -s http://100.96.122.22:18540/v1/models` → 200 + list includes `gpt-5.4-mini`; **check relay budget < cap** (after full89 收官: ~50 full500 + 8 here vs 150).
2. **`ulimit -n 65535`** (lesson: high-concurrency mini + node subprocesses exhaust default 1024 fd → spurious fails).
3. **Offline-install mini-swe-agent** from staged wheels → `mini --version` succeeds.
4. `node --version` (v16.14.0 present) + **smoke `node <a_case>.mjs`** to confirm v16 runs the ESM; else stage node 20 + `NODE_BIN`.
5. `source /data/nips/shared_bench/api_config.env` → `OPENAI_API_KEY` (relay key) set; `python3 -V` = 3.10.
6. Runner edits applied: `model_name="gpt-5.4-mini"` (:9), `num_processes=8` (:12), `max_retries=1` (main — **pass@1**).
7. Output dir writable on shared FS; dataset present (446).

**Launch draft (on Pod B, AFTER full89 收官 + lead GO):**
```bash
ssh env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero
python3 -m pip install --no-index --find-links /mnt/.../repozero_eval/wheels/mini_swe_agent mini-swe-agent   # offline
source /data/nips/shared_bench/api_config.env                        # OPENAI_API_KEY
export QIANFAN_API_URL=http://100.96.122.22:18540/v1                 # api_base override
export MINI_SWE_AGENT_BIN=mini NODE_BIN=node
ulimit -n 65535
# edit run_all_loop_mini_openai.py: model_name="gpt-5.4-mini", num_processes=8, main max_retries=1
python3 run_py2js/run_all_loop_mini_openai.py            # → .mjs into output_loop_mini/gpt-5.4-mini_retry1/
python3 evaluate/eval_py2js_mini.py <results.jsonl> <dataset_root> gpt-5.4-mini <results_dir>   # 5s/case eval
```
**Concurrency:** **c=8 start** (codex line proved c=25 → latency casualties; c=8 stable), scale c=12–16 only if relay p50 stays flat AND budget headroom holds. Watch relay 5xx / per-call latency; back off on rising latency.
**Runtime:** ~400 cases × (solver + 5s eval), pass@1, c=8 → order of hours (solver-bound); refine after a 10-case smoke.

---

## Red lines held
Pure read-only spec + offline prep only. **No run / no model call executed.** No Pod A/B runtime touched. `pip download` ran on **dev** (has net, authorized). Node probe on Pod B was read-only. Runner edits above are for the launch operator (not applied). **Launch order awaits lead.**

## §7 — STATUS: PAUSED @ Gate4 (lead decision D, 2026-07-04)

**Decision (lead):** PAUSE the official-protocol run. The former codex-line aggregate is not retained as a primary/current number. **0 official full runs launched.**

### Gate outcomes
- ✅ **Gate1** — pin `39308b1` pristine + worktree `rz_run_wt_20260704` + clean runner diff (below).
- ✅ **Gate2** — preflight: relay `:18540` has `gpt-5.4-mini`; venv mini **2.4.4** offline-installed (77 wheels); `ulimit→65535`; node v16.14.0.
- ✅ **Gate3** — xhigh reaches API: direct probe `reasoning_tokens=79`; adapted-runner end-to-end **`reasoning_tokens=114/148/328`** (evidence: `repozero_eval/gate3_e2e/{e2e.log,traj.json}`). mini 2.4.4 forwards `model_kwargs`→`litellm.completion` — no param-drop.
- ❌ **Gate4** — BLOCKER: stock mini 2.4.4 ↔ gpt-5.4-mini scaffold incompatibility → 0 output (details below).

### ★ Root finding — official-benchmark reproducibility gap (UPSTREAM-ARCHIVE, not-fix per charter)
The official runner `run_py2js/run_all_loop_mini_openai.py` @39308b1 invokes `mini --custom-llm-provider litellm --api-base X -t <file>` — flags present in **NEITHER stock mini 1.17.5 (latest v1) NOR 2.4.4 (latest v2)**; the repo has **no vendored mini + no version pin**. RepoZero therefore depends on an **unidentifiable mini fork** whose CLI + agent-format + output-parser differ from any published mini-swe-agent. Compounding it, stock 2.4.4's scaffolds are incompatible with gpt-5.4-mini's (reasoning-model) output:
- `mini.yaml` (tool-calling) → `No tool calls found in the response` → 0 output;
- `mini_textbased.yaml` (correct bash-in-``` format) → gpt-5.4-mini responses repeatedly fail the strict "exactly ONE bash code block" parser → `Format error` loop → timeout(124), 0 output (the smoke's 8× "succeeded" were empty — no `.mjs`).

Faithful reproduction is **not achievable offline without the exact fork**. Per the offline-E2E charter this is a **reproducibility gap in the official RepoZero benchmark itself → archived upstream-not-fix**. No local GPT aggregate from the former codex harness is current or publishable.

### Resume start point (if this line is ever resumed) — all preserved, DO NOT DELETE
- worktree (pin pristine + adapted runner): `repozero_eval/rz_run_wt_20260704/`
- offline mini wheels: `repozero_eval/wheels/mini_swe_agent/` (mini-swe-agent 2.4.4 + 76 deps = 77 wheels, 0 sdists)
- venv: `repozero_eval/rz_venv/` ; xhigh evidence: `repozero_eval/gate3_e2e/`
- **stock-2.4.4 adaptation diff (bug-for-bug audit record):**
  ```
  + import shlex ; + from minisweagent.run.mini import DEFAULT_CONFIG_FILE
    model_name  : "deepseek-v3.1-250821" -> "gpt-5.4-mini"
    num_processes: 10 -> 8
    max_retries : 2 -> 1   (pass@1)
    mini invocation:
      -  -t {prompt_file!r} --custom-llm-provider litellm --api-base {api_base}
      +  -t {shlex.quote(prompt)} -c {DEFAULT_CONFIG_FILE}
         -c model.model_kwargs.api_base={api_base} -c model.model_kwargs.reasoning_effort=xhigh
    + env at launch: MSWEA_CONFIGURED=1, MINI_SWE_AGENT_BIN=<venv>/bin/mini, dataset symlink into worktree
    + RZ_SMOKE_N env-gated smoke limit (inert for full run)
  ```
- **Unresolved for resume:** the Gate4 model↔scaffold format incompatibility — needs the exact fork mini, OR a parser/prompt tune (accepting deviation), OR a format-compliant model. If resumed, also verify node v16 vs the eval (or stage node20) and the 5s-eval strict chain.
