# CERT_B — TB2.1 × Qwen3-Coder-30B × terminus-2 — Evidence-Chain / Reproducibility Audit

**Signer role:** Second signer (independent). I did **not** read `CERT_A_TB21_TERMINUS2.md`.
**Question I answer:** *Not* "is this an official reproduction" (that is signer A). Mine is:
**"If this machine disappears tomorrow, is what survives on GitHub enough for a stranger to re-run this and prove the score was not tampered with?"** My job was to *find gaps*, not confirm completeness.

**Audit window:** 2026-07-10 ~09:05→09:20 UTC. **The run FINALIZED during my audit** (markers `full.rc`/`full.done`/`tb.exit_status`/`artifact_manifest.json` all written 09:15 UTC / 17:15 local). Read-only throughout; no file/process/service touched.

---

## 0. Run finalization status (read this before the score)

| item | value | source |
|---|---|---|
| run finished? | **YES** (all 89 tasks eval'd, results written) | `full_run.out`: "Running tasks (89/89, Accuracy 13.48%)" → "Results written to …/results.json" |
| process exit | **`tb_rc=143` (128+15 = SIGTERM)** — hit during docker **cleanup**, AFTER results.json was written (`cleanup_helper=skipped`, `runner_failed rc=143`) | `full.rc`, `.../batch_01_of_01/tb.exit_status`, `full_run.out` |
| run's OWN strict gate | **`status=blocked`, `ready=False`, `clean_pass=0`, `infra_fail=89`, `external_network_marker=12`, `timeout=2`** | `tb21_strict_summary.json` |
| static closure gate | `status=closed`, `ready=true`, `closed=89 / open=0` on the r7 dataset | `gate/gate.json` (schema `tb21.runtime_closure_static_gate.v1`) |

⇒ The **12/89 score is fully computed and internally consistent**, but the run's own strict summary flags the whole batch `blocked / infra_fail=89` and the process was SIGTERM'd. Any repro package **must carry this status**, or a stranger will mistake 13.48% for a clean official number. (Clean-vs-official is signer A's call; I only record that the run self-reports "blocked".)

---

## 1. Thirteen-field evidence table

Status = does the evidence **exist** (PRESENT/PARTIAL/MISSING). **Durability tag** in each cell: `[pod-only-untracked]`, `[git-ignored]`, or `[rescued-uncommitted]` — because the audit question is durability, not mere existence.

| # | 字段 | 状态 | 绝对路径 (host: env-kvm-…rlgbn pod) | 能证明什么 / caveat |
|---|---|---|---|---|
| 1 | run_id | **PRESENT** | `…/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c32_tb21_coder_t2_c32_0710064916_attempt1_medium_c32/run_metadata.json` (`run_id`, `uuid=ea134590-…`); `…/logs/tb21_coder_terminus2_20260710/full.run_id` = `tb21_coder_t2_c32_0710064916` | Identity pinned & consistent across TB-native + launcher. `[git-ignored]` (TB run_root) |
| 2 | bench + dataset 快照名 | **PRESENT** | `run_metadata.dataset_path` = `…/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703`; also `run.env.summary` (`tb_dataset_name=terminal-bench/terminal-bench-2-1`), `command.sh --dataset-path`, `run.log:4742` (docker-compose reads it), `gate/summary.json dataset_dir` | Snapshot name pinned 4 ways + used at runtime + closure-gated 89/89. (`dataset_name/version` fields in run_metadata are `null`; path is authoritative.) |
| 3 | model | **PRESENT** | `run_metadata.model_name=openai/Qwen/Qwen3-Coder-30B-A3B-Instruct`; serving `get_model_info*.json model_path=/mnt/.../models/Qwen3-Coder-30B-A3B-Instruct`; every `agent-logs/episode-*/debug.json model=Qwen/Qwen3-Coder-30B-A3B-Instruct`; identity-after `endswith_Coder=True` | Model pinned to a local weights dir + verified before & after. `[pod-only]` for serving/identity |
| 4 | harness + 版本 | **PRESENT** | `agent_name=terminus-2`; `run_metadata.commit_hash=1a6ffa9674b571da0ed040c470cb40c4d85f9b9b`; tb binary `…/shared_bench/terminal-bench/.venv/bin/tb`; repo origin `github.com/harbor-framework/terminal-bench.git` | terminus-2 @ TB commit 1a6ffa96. Upstream commit is public/reproducible; the **wrapper layer (4 scripts) is the user's untracked add-on** — see #10 |
| 5 | reasoning_effort / 采样参数 | **PRESENT** | `command.sh` → `--agent-kwarg temperature=0.0`; `run.env.summary` → `reasoning_effort=` (**EMPTY**); `debug.json optional_params.temperature=0.0`, `extra_body` empty | **Sampling = greedy temperature=0.0.** ⚠️ The `medium` in the run_id is a **cosmetic label, not a model param** (reasoning_effort is unset; server `sampling_defaults=model`). top_p/top_k not pinned client-side — rely on sglang model defaults + `random_seed=598954308` |
| 6 | attempts / concurrency | **PRESENT** | `run_metadata` `n_attempts=1`, `n_concurrent_trials=32`; `command.sh --n-concurrent 32`; launcher `--attempts all --concurrency 32` | Consistent 1×32 |
| 7 | score (resolved/total) | **PRESENT** (see §0) | `results.json` `n_resolved=12 n_unresolved=77 accuracy=0.1348314606741573`; `run_metadata.accuracy` same + `dataset_size=89`; `tb21_strict_summary.json score={12,89,0.1348}` | **12/89 = 0.13483146** exact. **Denominator = 89** confirmed (12+77 = 89 = dataset_size = strict.total). No live-run 12/85 artifact — run is finalized. **BUT strict gate = blocked (§0)** |
| 8 | results / sha256 | **PARTIAL** | `results.json` PRESENT (I computed `sha256=fcb8be96441d7cc14448dda91823af706d8a3976ef7ed6714b2b8cf0a37fbc5e`; run_metadata `50391421…`; run.log `d9efa5da…`) | Results exist, but **NO sha256 was stored with the run.** `artifact_manifest.json` is a **path index with zero hashes.** The only integrity hash in existence is the one *I* just computed → tampering is **not** detectable from stored artifacts. `[git-ignored]` |
| 9 | agent trace + 指针/哈希 | **PARTIAL** | per task: `…/<task>/…/agent-logs/episode-N/{debug.json,prompt.txt,response.txt}`, `sessions/{agent.cast,agent.log,tests.cast,tests.log,verifier/{ctrf.json,reward.txt}}`, `commands.txt`, `panes/`. Pointer: launcher `…/batch_01_of_01/tb_run_output` symlink → run_root; `artifact_manifest.json` | Rich per-turn trace (**8559 debug.json / 8559 prompt / 8555 response**; **NOT last-only** — see pit 4). `debug.json` embeds api_base+temperature+model+response+latency. **No trace hash stored; whole tree `[git-ignored]`** |
| 10 | script_digests | **PARTIAL** | run self-record: **none** (`full_run.sh` runs no `sha256sum`; no digest file in any run dir). Separate rescue: local `…/paper_reading/bench/runners/tb21_harness/PROVENANCE.tsv` + `runners/SHA256SUMS` | Rescue digests **match run-time** for `stage_tb21_official_qwen_launcher.sh` (`a9d0434b`✓) and `run_terminal_bench_2_1.sh` (`3dcd4a1d`✓) — but **MISS the driver `full_run.sh` (`5c9cc132`), `identity_capture.py` (`0caa9a76`), `leakscan.py` (`9dc98543`)**. The run itself proves **nothing** about which script version it used. `[rescued-uncommitted]` |
| 11 | serving_config | **PRESENT** | `…/logs/tb21_coder_terminus2_20260710/serving_run/get_{model,server}_info_{before,after}.json` (before 14:49, after 17:15) + `serving/…_before.json` | **Full sglang config, before & after.** v0.5.13, `tp_size=2`, `dtype=auto`, `mem_fraction_static=0.85`, `attention_backend=fa3`, `chunked_prefill=8192`, `schedule_policy=fcfs`, `random_seed=598954308`, `context_length=262144`, `max_total_num_tokens=1946895`, `quantization=None`. **`api_key`/`admin_api_key`/`ssl_keyfile_password` all `null`.** `[pod-only-untracked]` — host 100.100.104.140 is ephemeral; these files are the ONLY config record |
| 12 | relay_upstream | **PRESENT** | `full_run.sh` header "Direct sglang :30001 (**no relay**)"; `base_url=http://100.100.104.140:30001/v1` in `full_run.sh`, `command.sh --agent-kwarg api_base`, `run.env.summary`, every `debug.json api_base` | **No relay — model served DIRECTLY by sglang** at 100.100.104.140:30001. The launcher flag `--relay-url` is a misnomer. Endpoint pinned 4 ways |
| 13 | llm_health | **PRESENT** | `identity_capture.py` before+after → `full_run.out`: `[after] IDENTITY_OK`, `endswith_Coder=True`, `value_scan_leaks=0`; `serving/stress32_before.txt`; per-turn `debug.json llm_api_duration_ms` + `response_headers{server:uvicorn,http 200}`; `tb21_strict_summary token_sum{input:31,751,137 output:615,764}` | Identity **matches before & after** (no mid-run model swap); real latency + 31.7M input tokens = genuine load. `[pod-only-untracked]` |

**Tally: PRESENT = 10 · PARTIAL = 3 (#8 sha256, #9 trace-hash/archival, #10 script_digests) · MISSING = 0.**
Every field's *evidence exists on the pod*. The failure mode is **durability**, quantified next.

---

## 2. Six-pit verdicts

1. **script_digests recorded WITH the run?** → **NO.** `full_run.sh` never hashes its scripts; `artifact_manifest.json` carries no hashes; no digest file in any run dir. A *separate, later* rescue (`PROVENANCE.tsv`, mtime Jul-10 15:19) hashed the repo-side scripts (2 match run-time) but **omitted the driver `full_run.sh` + `identity_capture.py` + `leakscan.py`**. "GitHub has an archive" ≠ "the run recorded what it used" — **confirmed distinct, and both are incomplete.**
2. **serving snapshot before/after + keys redacted?** → **YES, both, clean.** `get_{model,server}_info_{before,after}.json` present. Independent **value-scan: sk-=0, bearer=0, jwt=0**; `api_key`/`admin_api_key`/`ssl_keyfile_password` = `null` (server runs auth-less). The harness's own `leakscan.py` logged `value_scan_leaks=0`. No key by name or by value. (My scanner's 67 "secret-named" hits were false positives on sglang params containing "token"/"secret" — all ints/bools/null.)
3. **full command line + dataset snapshot on disk?** → **YES.** `…/batch_01_of_01/command.sh` = complete `tb run …` with all 89 `--task-id`, `--dataset-path …r7-final-20260703`, `--agent-kwarg api_base=… temperature=0.0`; `run.env.summary` mirrors it. Driver `full_run.sh` also persisted (pod-only). Live `/proc` cmdline matched.
4. **trace debug.json count / volume / overwrite?** → **8559** `debug.json` (+8559 prompt, +8555 response). ★ **For THIS run the overwrite concern does NOT hold**: episodes are **distinct `episode-N` dirs** (sam-cell-seg=32, regex-chess=21, adaptive=15), each with its own debug/prompt/response ⇒ **full per-turn trace, NOT last-episode-only.** `.cast`=178, `agent.log`=89. **Volume: run_root = 12 GB.** gzip: **.cast = 8.0 MB (fits GitHub)**; **debug+prompt+response = 316 MB** (prompt re-embeds full history each turn ⇒ needs LFS/release; do **not** confuse with the 12 GB full tree).
5. **accuracy denominator?** → **89, confirmed.** `results.json accuracy=0.1348314606741573 = 12/89`; `n_resolved+n_unresolved = 12+77 = 89 = run_metadata.dataset_size = strict.total`. Run finalized ⇒ no `12/85`-style live artifact.
6. **reproducibility gap (specific)?** → see §3. The gap is **not** missing evidence; it is that **~all of it is pod-only / git-ignored / uncommitted**, and the one rescue omits the driver and every run-instance artifact.

---

## 3. Reproducibility-gap table — "if this machine dies tomorrow, GitHub is missing…"

Durability reality: TB run_root is **git-ignored** (`terminal-bench/.gitignore:182 runs`); the launcher repo (`github.com/Zeng-Weijun/Agentic-foundation-model-bench-.git`, HEAD `7c50ae8` Jul-5) has **every** Jul-10 artifact `UNTRACKED(not-ignored)`; the local rescue `…/paper_reading/bench/runners/` is **`?? untracked`** and `git remote -v` returned **empty** (no push target observed). So "已抢救进 GitHub" is, as verified here, **staged in a working tree, not committed, no remote** — and partial.

| 缺什么 (from durable/GitHub) | 路径 (pod, unless noted) | 体积 | 为什么必须有 | 能进 GitHub? |
|---|---|---|---|---|
| **`full_run.sh` driver** (env `TB21_ENABLE_KVM_DEVICE=0`, `TB2_RUNTIME_CLOSURE_REPAIR=""`, NO_PROXY, dataset-assert, serving-capture) `sha 5c9cc132` | `…/logs/tb21_coder_terminus2_20260710/full_run.sh` — untracked; **NOT in rescue** | 5.7 KB | Top-level orchestration that *defines* the exact run; without it the env/flags are unknown | **Yes** (tiny) |
| `identity_capture.py` `0caa9a76` + `leakscan.py` `9dc98543` | same dir — untracked; **NOT in rescue** | ~4 KB | Reproduce the identity/leak gating that blessed the serving | **Yes** |
| **serving snapshots** `get_{model,server}_info_{before,after}.json` | `…/serving_run/`, `…/serving/` — untracked; **NOT in rescue** | ~120 KB | **Only** record of the sglang config (host 100.100.104.140 is ephemeral) | **Yes** |
| `command.sh` + `run.env.summary` + `artifact_manifest.json` + `tb21_strict_summary.json` + `gate/{gate.json,matrix.jsonl,summary.json}` | `…/runs/terminal_bench_2_1_official_qwen_poda/tb21_coder_t2_c32_0710064916/…/batch_01_of_01/` + `…/gate/` — untracked | ~460 KB | Exact `tb` invocation, effective env, **the `blocked/infra_fail=89` verdict**, closure proof | **Yes** |
| **`results.json` + `run_metadata.json`** (the score) | TB run_root — **git-ignored** | 221 KB | The score itself; must travel **with a stored sha256** | **Yes** |
| stored **sha256 manifest of results.json + the 5 scripts** | **does not exist anywhere** | <5 KB | Without it the 12/89 cannot be proven un-tampered | **Yes — must be created** |
| agent traces | run_root `sessions/*.cast` (8 MB gz) / `agent-logs/**` (316 MB gz) — git-ignored | 8 MB / 316 MB | Auditable per-turn behavior | `.cast`: yes; I/O: LFS/release |
| the rescue itself | `…/paper_reading/bench/runners/` — **`?? untracked`, no remote** | 304 KB | Even the partial script rescue is not yet durable | **Yes — commit + add remote** |

---

## 4. Key-scan result

**No API key exposed anywhere I read or in this report.** All key material redacted **on the pod before reaching my screen** (pushed `/tmp/redact_lines.py`, `/tmp/serving_scan.py`). Independent by-value scan of serving snapshots: `sk-=0 bearer=0 jwt=0`; `api_key`/`admin_api_key`/`ssl_keyfile_password` = `null`. `full_run.sh` key exports and `debug.json api_key`/`api_key_sha256` were redacted. Harness's own `leakscan.py`: `value_scan_leaks=0`.

## 5. Run-time script digests (authoritative, computed by me during audit)

```
full_run.sh                          5c9cc132552f899f9e480fd07e983aa89c45e9aa5f61a90d363dc7c84ad919b9   [driver, NOT rescued]
identity_capture.py                  0caa9a76eb1f53f0d089999277ccefd8a19f645a364f4085ce335b836569aa77   [NOT rescued]
leakscan.py                          9dc98543718d2076a8c3c355aaff221b0d8875d455e59fe706d4977919d0da74   [NOT rescued]
stage_tb21_official_qwen_launcher.sh a9d0434bbfcf80329fa7b20d59ce8f743d488ada1165a8370e05c7e36ba611d7   [rescue MATCHES]
run_terminal_bench_2_1.sh            3dcd4a1d642f90ff940c1f2d79addd8f873f470f2cc5882f796e1dd53f7c79b0   [rescue MATCHES; source /mnt/.../swe/bench is NOT a git repo]
results.json                         fcb8be96441d7cc14448dda91823af706d8a3976ef7ed6714b2b8cf0a37fbc5e   [no stored digest existed before this]
run_metadata.json                    5039142129c33ae247ad728a4748d552e8b9ccc789ef499bb505d878577a001a
```

---

## 6. Verdict

The **on-pod evidence chain is unusually strong** (serving before/after with no leaks, identity gating, closure gate 89/89, full command + env + per-turn traces, self-reported strict status). If the machine *survives*, a diligent stranger could reproduce most of this.

But the audit question is **GitHub durability**, and there it fails:
- TB run_root (score + 12 GB traces) is **git-ignored**; launcher/driver provenance is **100% untracked** (repo HEAD is Jul-5); the local rescue is **uncommitted with no remote**, **omits the driver `full_run.sh` + identity/leak scripts**, and contains **zero run-instance evidence** (no serving, results, health, or traces for `0710064916`);
- **no sha256 of `results.json` was ever stored**, so the 12/89 cannot be proven un-tampered from durable artifacts;
- the run's own **`blocked / infra_fail=89 / rc=143`** status is itself untracked.

> **我是否愿意为「GitHub 上的产物足以让一个陌生人重做这次 run 并验证分数未被篡改」背书? → 不背书 (DO NOT ENDORSE).**

This is a **durability/archival failure, not an evidence-quality failure.** The fix is concrete and small (≈9 MB + LFS for I/O traces): commit the §3 files — driver+identity+leakscan, both serving pairs, command.sh/run.env.summary/manifest/strict/gate, results.json/run_metadata.json, `.cast` sessions — **plus a stored sha256 manifest** — to a repo with a real remote. Until that is done and pushed, the machine is a single point of failure for this run.

*— Second signer, evidence-chain audit, 2026-07-10*
