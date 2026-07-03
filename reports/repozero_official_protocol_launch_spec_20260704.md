# RepoZero official-protocol run — pre-launch spec (by-85, 2026-07-04)

**Purpose:** pre-launch spec for the RepoZero **official-protocol** run (official Mini-SWE-Agent scaffold + pass@1 single + official 5s per-case timeout + gpt-5.4-mini via dev relay 18540). Line = "官方协议 + 无锚存档" (official leaderboard has no GPT models → run their protocol, archive as no-anchor). **This is a read-only spec — NO run/model call was executed; no Pod A/B runtime touched.** Official repo pinned `@39308b1` (`/mnt/.../nips2026/repozero_eval/RepoZero`).

---

## ① Official Mini-SWE-Agent runner + config (verified from source @39308b1)

**Solver runner:** `run_py2js/run_all_loop_mini_openai.py` (OpenAI-provider, loop mode; there is also an `_anthropic` variant — use the OpenAI one for relay).
**Evaluator:** `evaluate/eval_py2js_mini.py`.

Config is **hardcoded module globals + main() locals — NO argparse.** Exact lines to override:

| param | source (file:line) | default | set to | note |
|---|---|---|---|---|
| model | `run_all_loop_mini_openai.py:9` `model_name` | `"deepseek-v3.1-250821"` | `"gpt-5.4-mini"` | hardcoded — must edit |
| api_base | `:10` `api_base = os.environ.get("QIANFAN_API_URL", ...)` | qianfan | env `QIANFAN_API_URL=http://100.96.122.22:18540/v1` | reads this env; no edit needed |
| provider | `:11` | `"openai"` | keep | ok |
| concurrency | `:12` `num_processes` | `10` | **8–16** | hardcoded — edit |
| **attempts (pass@1)** | `main():` `max_retries` | **`2`** | **`1`** | ⚠ default 2 = loop retries; **official pass@1 SINGLE ⇒ must set 1** |
| mini bin | `:14` `MINI_BIN=os.environ.get("MINI_SWE_AGENT_BIN","mini")` | `mini` | env or PATH | needs mini-swe-agent installed |
| agent per-call timeout | `run_mini_swe_agent()` `subprocess.run(..., timeout=30)` | 30s | keep | agent-side, distinct from eval 5s |

**Mini invocation (line ~52):** `mini --model openai/{model_name} -y --exit-immediately …` — reads `OPENAI_API_KEY` + base-url from env/mini config.
**Eval (`eval_py2js_mini.py`):** runs `python <py>` and `node <js>` each with **`timeout=5`** (lines 22/26 — the official 5s per-case), compares cleaned output → `all_pass`. `NODE_BIN` env (default `node`). Output `.mjs` under `Py2JS/output_loop_mini/{model}_retry{max_retries}/`.
**Prompt contract (baked in runner):** JS must be **pure ESM, Node.js, ZERO external npm deps** (lines ~107/114) → no `npm install` needed for eval.

---

## ② Running it on a KVM pod — requirements + gaps

| need | status on dev/pod | action |
|---|---|---|
| `node` | ✅ dev has `v20.20.0` (`/usr/local/bin/node`) | confirm on target host |
| `python3` | ✅ | ok |
| **`mini` (mini-swe-agent CLI)** | ❌ **NOT installed on dev** (`mini: command not found`) | **`pip install mini-swe-agent`; offline ⇒ stage the wheel** to shared FS + install (no PyPI on pods) |
| **relay 18540 reachability** | ⚠ **relay is DEV-ONLY per policy** (Tailscale API relay; workers/pods forbidden) | **critical preflight** — the solver's model calls need `100.96.122.22:18540`. If the target KVM pod cannot reach it, **run the solver on `dev`** (relay-reachable), or tunnel pod→dev. The prior codex rescue used `--base-url http://100.96.122.22:18540/v1` from pg89q — verify that path still holds for the pod, else host the solver on dev. |
| repozero docker image (`ghcr.io/jessezzzzz/repoarena-new`, staged tar in `.../images/repozero/`) | present | **likely NOT needed for the official protocol** — the official eval runs `node`/`python` **locally** (no docker sandbox in `eval_py2js_mini.py`). Confirm whether `mini-swe-agent`'s env is `local` vs a docker sandbox (`mini` default = local subprocess). If local, **no docker needed** (unlike our codex line). |
| dataset | ✅ `Py2JS/dataset` present (446 `.py` files) | ok |

**Bottom line:** the official protocol is much lighter than our codex-in-docker line — it needs `node` + `python3` + `mini-swe-agent` + relay access, **not** the repozero docker image. The only real gaps are **(a) install mini-swe-agent (offline wheel)** and **(b) relay reachability from the run host** (default to running the solver on dev).

---

## ③ 73-timeout residual extraction — command + shared-FS rebuild path

⚠ pg89q `/tmp/rz_pilot/*` caches evaporated (tmpfs, lost on pod restart) — but the **rerun `results.jsonl` is on shared FS** (persistent):
```
RES=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero/Py2JS/output_codex/gpt-5.4-mini_repozero_full_rerun_ratelimited_pg89q_20260702/results.jsonl
```
242 rows. Fields include `case, all_pass, codex_returncode, codex_timeout, entry, …`. **Extract the timeout residuals (run on dev, read-only):**
```bash
python3 -c "import json,os
rows=[json.loads(l) for l in open(os.environ['RES'])]
to=[r['case'] for r in rows if r.get('codex_timeout')]
print(len(to)); print(' '.join(to))"
```
(Field is `codex_timeout` (bool); equivalently `codex_returncode==124` @2400s wall.) **✅ VERIFIED on shared FS (read-only): total=242, `codex_timeout`=73 == `codex_returncode==124`=73 — matches REPOZERO_LANE_HANDOFF §6 exactly.** The command above is correct and runs on dev against the shared-FS jsonl (no pg89q dependency).

**Note on scope:** the 73 are **our codex-line** residuals (c=25 latency casualties, NOT genuine fails). The **official-protocol run is a fresh independent full-400** with mini-swe-agent — the 73 list is useful only if piloting/comparing on that subset; do not conflate the two lines (official-protocol archive vs our internal 260/400 codex number). **Rebuild the strict-scope caches on shared FS** (not pg89q /tmp): re-derive over the ORIGINAL run `summary.json` — genuine-excluded = `all_pass==False AND codex_returncode==0 AND NOT codex_timeout` (per §5); persist to `.../repozero_eval/scope/` on shared FS.

---

## ④ Launch command draft + preflight checklist

**Preflight (all must pass before launch):**
1. ⚠ **Relay health + reachability from the run host**: `curl -s http://100.96.122.22:18540/v1/models` (or a 1-token chat completion) → HTTP 200 + model list includes `gpt-5.4-mini`. (Relay is dev-only — if running on a KVM pod, this is the #1 blocker; default to running the solver on **dev**.)
2. **`ulimit -n 65535`** (lesson: high-concurrency mini-swe + node subprocesses exhaust the default 1024 fd limit → spurious failures).
3. `mini --version` succeeds (mini-swe-agent installed; offline wheel staged).
4. `node --version` (≥18) + `python3 --version` present.
5. Source keys: `source /data/nips/shared_bench/api_config.env` → `OPENAI_API_KEY` set (relay key).
6. Runner edits applied: `model_name="gpt-5.4-mini"` (:9), `num_processes=8` (:12), `max_retries=1` (main — **pass@1**).
7. Output dir writable on shared FS; dataset present (446 files).
8. Confirm mini-swe-agent env = local (no docker) OR docker socket ready if sandboxed.

**Launch draft (solver on dev, relay-reachable):**
```bash
cd /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/repozero_eval/RepoZero
source ~/.bashrc; source /data/nips/shared_bench/api_config.env      # OPENAI_API_KEY
export QIANFAN_API_URL=http://100.96.122.22:18540/v1                 # api_base override
export MINI_SWE_AGENT_BIN=mini NODE_BIN=node
ulimit -n 65535
# (edit run_all_loop_mini_openai.py: model_name, num_processes=8, main max_retries=1)
python3 run_py2js/run_all_loop_mini_openai.py            # → .mjs into output_loop_mini/gpt-5.4-mini_retry1/
# then eval (5s/case):
python3 evaluate/eval_py2js_mini.py <results.jsonl> <dataset_root> gpt-5.4-mini <results_dir>
```
**Concurrency rec:** **c=8** to start (safe; the codex line proved c=25 → latency casualties, c=8 stable), scale to **c=12–16** only if relay p50 latency stays flat. Watch relay 5xx / per-call latency; back off on rising latency (not throttle).
**Runtime estimate:** ~400 cases × (solver + 5s eval), pass@1 single, c=8 → order of a few hours (solver-bound; refine after a 10-case smoke).

---

## Red lines held
Pure read-only pre-research. **No run / no model call executed.** No Pod A/B runtime touched (full89 running Pod A c=89). No runner files edited (edits above are for the launch operator to apply). All source facts verified from `@39308b1` + shared-FS artifacts.
