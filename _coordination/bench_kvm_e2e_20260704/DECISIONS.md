# tau3 DoD-3 build/transport — DECISIONS (by-85, 2026-07-04)
## GO plan(a): apt→internal debian-proxy mirror + nohup rebuild on swe_dev2
- Judgment: prior rebuild ALIVE not dead (log advanced 387→492s; buildkitd 0.2%CPU = apt network-wait via throttled public-debian proxy). Just impractically slow (~60-90min ×2 imgs + gcc/portaudio).
- Fix: apt source rewrite deb.debian.org/debian → mirrors.i.h.pjlab.org.cn/repository/debian-proxy (200@0.18s, verified); security kept public (small). pip already internal-mirror. Extra=[all] + apt gcc/portaudio19-dev/libportaudio2 (pyaudio needs source build — import chain server.py→tau2→tau2.voice.utils.audio_io→pyaudio).
- Build: setsid nohup bash build_tau3.sh > build_nohup.log (survives maintenance-host kill; build.log tee'd for断点).
- Fragility noted: swe_dev2 = maintenance host AND hosts P0 registry :8555 — restart drops both.
## On build done → FULL CHAIN (55 gate): report NEW digests → apply 55 3 hardening (import probe covers import tau2,fastmcp,tau2.domains.*; test -s /app/task_config.json + sha256 mount match; no public net) → manifest backfill → freeze evidence → preflight 375/375 rerun → push P0 → Pod A re-proof → evidence to disk. Labeling口径: materialized-with-internal-pip-mirror + commit-pinned; NOT offline-build-ready/fully-reproducible.
## Prior digests (pre-[all], WILL CHANGE): main@sha256:74ff8e9e runtime@sha256:f7ce6893. tars images/tau3/*.tar. manifest manifests/images/tau3_full_p0_20260704.yaml (origin f659fd9).

## UPDATE 19:47 — plan(a) apt-rewrite FAILED (over-escaped sed), build stuck; RESUME FIX
- BUG: patch_aptmirror.py wrote `deb\\.debian\\.org` (double-backslash) into the Dockerfile sed → malformed regex → NO rewrite → build still hits http://deb.debian.org (public throttled proxy). Build stuck on cpp-14 (gcc pkg), buildkit 0.2%cpu, log stale.
- debian.sources (python:3.12-slim trixie) deb822 format, 2 stanzas: `URIs: http://deb.debian.org/debian` and `URIs: http://deb.debian.org/debian-security`. File: /etc/apt/sources.list.d/debian.sources.
- CORRECT FIX (single-backslash, security-first to avoid prefix clash): in the Dockerfile RUN, before apt-get update:
    sed -i 's#http://deb.debian.org/debian-security#http://deb.debian.org/debian-security#' ...   # (keep security public — small)
    sed -i -E 's#http://deb\.debian\.org/debian$#http://mirrors.i.h.pjlab.org.cn/repository/debian-proxy#' /etc/apt/sources.list.d/debian.sources
  i.e. ONLY rewrite the main URI (ends at /debian EOL) to debian-proxy; leave -security public. Verified reachable: mirrors.i.h.pjlab.org.cn/repository/debian-proxy/dists/trixie/Release = 200 @0.18s.
- SIMPLEST alt: printf-overwrite debian.sources with 2 stanzas (main=debian-proxy, security=public) — avoids regex.
- STATE: nohup build_tau3.sh running (pid ~1629515, build.log tee'd, build_nohup.log). Extra=[all] + apt gcc/portaudio19-dev/libportaudio2. If host restarts (maintenance), P0 :8555 drops too.
- RESUME: fix apt sed → kill+relaunch nohup build → on done: NEW digests → 55 3-hardening re-proof + full chain (manifest backfill/freeze/preflight 375-375/push/Pod A proof). All prior context in this file + HANDOFF + peer summary + origin f659fd9.

## UPDATE 19:52 — apt-mirror ABANDONED, slow public-apt build running to completion
- Correct-sed also failed to rewrite (build.log 26x deb.debian.org, stuck cpp-14; `$`-anchor not matching deb822 URIs for undiagnosed reason — docker-cache OR trailing-ws OR format). NOT worth more debug at ctx-limit.
- DECISION: apt-mirror is a speedup only; the slow public-apt build STILL yields correct [all]+gcc images. Let it run (~60min), monitor, nohup+tar断点 protect. If maintenance-host restarts mid-build, resume from build_nohup.log.
- Build running: pid~1629789, ctx has pin17e07b1+[all]+gcc/portaudio+pip-internal-mirror(works)+runtime-drop-COPY-task_config. On done -> NEW digests -> full chain (55 3-hardening re-proof etc, see above).
- Open item for resumer if speed needed: debug apt-mirror sed vs /etc/apt/sources.list.d/debian.sources actual bytes (od -c), or printf-overwrite the file.

## UPDATE 20:08 — build died again (maintenance host kills process trees, nohup NOT surviving). ONE-CLICK RERUN
Scripts now on SHARED FS (survive restart): /mnt/.../images/tau3/build_scripts/{build_tau3.sh, patch_all.py}
Paths: IMG=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/tau3 ; CTX=$IMG/build_20260704/ctx ; DS=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench
### ON A STABLE BUILDER (swe_dev2 post-restart, OR swe_dev after `curl -sI --proxy $https_proxy https://github.com` proof):
```
source ~/.bashrc
IMG=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/tau3
CTX=$IMG/build_20260704/ctx
# (only if ctx reset) rm -rf $CTX; cp -r /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench/tau3-airline-0/environment $CTX; python3 $IMG/build_scripts/patch_all.py $CTX/Dockerfile main; python3 $IMG/build_scripts/patch_all.py $CTX/runtime-server/Dockerfile runtime
tmux new-session -d -s tau3build "bash $IMG/build_scripts/build_tau3.sh"   # build_tau3.sh: builds main+runtime (pin17e07b1,[all],gcc/portaudio,pip-internal-mirror), docker save tar+sha256 to $IMG/, tee $IMG/build_20260704/build.log
```
build_tau3.sh uses /usr/bin/docker (bypass repo2env wrapper) + proxy build-args. On success: MAIN_DONE/RUNTIME_DONE/ALL_DONE + tars $IMG/tau3-full-{main,runtime}_20260704.tar (+ .sha256). NOTE: apt/git go public-via-proxy (slow ~60min); apt-mirror speedup unresolved (see UPDATE 19:52). Extra=[all]+gcc REQUIRED (fixes scipy+pyaudio import crash).
### AFTER build: NEW digests -> push P0 100.97.118.137:8555/swe-data-harness/tau3-full-{main,runtime} -> manifest backfill (manifests/images/tau3_full_p0_20260704.yaml) -> freeze/preflight(scripts/tau3_transport_preflight.py)375/375 -> Pod A(env-kvm-15238487-rlgbn) re-proof(scripts/tau3_transport_proof.sh + 55 3-hardening: import tau2/fastmcp/tau2.domains.*, test -s + sha256 mount match, no public net).

## UPDATE 21:15 — build on swe_dev ALSO stalls on apt gcc-14; printf-overwrite apt-mirror READY but unverified
- swe_dev build stalls same as swe_dev2: apt hangs on gcc-14/libgcc-14-dev download (#6 2393s, log stale) via public deb.debian.org — the [all]+gcc extra pulls big gcc pkgs that stall through the proxy.
- FIXED patch_all.py (on SHARED FS build_scripts/patch_all.py): apt step now PRINTF-OVERWRITES /etc/apt/sources.list.d/debian.sources → main URI = http://mirrors.i.h.pjlab.org.cn/repository/debian-proxy (200, fast), security kept public (debian-proxy-security=404). Bulletproof, no regex.
- BUT after re-copy ctx + re-patch + relaunch, build.log STILL shows deb.debian.org at same #6 2393s gcc-14 — SUSPECT DOCKER BUILD CACHE replaying old apt RUN layer (or tee not reset). Ctx Dockerfile confirmed has debian-proxy printf.
- RESUME ACTION (next stable turn): (1) verify printf works: `docker run --rm <FROM python:3.12-slim + printf step> cat /etc/apt/sources.list.d/debian.sources` shows debian-proxy; (2) rebuild with `docker build --no-cache` (build_tau3.sh: add --no-cache to the docker build lines) to bypass stale apt-layer cache; (3) expect fast apt via debian-proxy → MAIN_DONE/RUNTIME_DONE → NEW digests → push P0 → full chain (55 3-hardening re-proof).
- exact debian.sources deb822 (for reference): 2 stanzas, Types: deb / URIs: http://deb.debian.org/{debian, debian-security} / Suites: trixie[-updates|-security] / Components: main / Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp

## UPDATE 21:20 — FIXED. apt on internal mirror, build fast+progressing
- Root cause of prior failures: my inline swe_dev ssh dropped mid-command (flaky conn) so re-patch never ran → old deb.debian.org build kept dying on gcc-14. NOT a Dockerfile problem.
- FIX: relaunch.sh on shared FS (build_scripts/relaunch.sh) run backgrounded via 1 short ssh → executed reliably. Result: tmux=Y, retries=1, apt build.log = 70x debian-proxy vs 4x public, Get:66 @13.5s (was Get:33 @2393s). printf-overwrite debian.sources (main=internal, security=public) + Acquire::Retries=10 both live.
- Monitor bvos27fqh (from dev) watching for ALL_DONE. On done: NEW digests → push P0 → manifest backfill → freeze/preflight375 → Pod A re-proof (55 3-hardening: import tau2/fastmcp/tau2.domains.*, test -s + sha256 mount match, no public net).
- LESSON for resumers: drive swe_dev builds via shared-FS scripts run backgrounded (setsid), NOT long inline ssh (conn flaky). Verify via dev reading shared-FS result files.

## UPDATE 22:00 — IMAGES DONE+FIXED+PUSHED; but preflight BLOCKED by dataset-freeze violation
### GOOD (committed 0c69e60):
- Build fixed: [all] extra + build-essential (gcc+libc6-dev, pyaudio compiled) + apt/pip internal mirror. import tau2/fastmcp/tau2.domains.* = OK (scipy/pyaudio crash GONE).
- P0 push (new digests): main@sha256:3591be51f3901080271eb4a9c1bd9c680fc999ced3c44fc42ccec7d788e81645 runtime@sha256:bf0f3ab41886d31db8f7c93f874d63420c1679733dcce1e4c0663c1c11117fa8. tars main d41e6640 / runtime 4ba76328. base 6da2590a. effective_compose_full_sha d261358d. manifest backfilled + 55#3口径 offline_ready=false.
### BLOCKER — preflight FAIL (dataset freeze violated):
- dataset tree_tar_sha256 CHANGED: manifest-frozen 350576c207e0daa8... → current b171889e... (dataset modified since my freeze).
- 2 EXTRA malformed dirs added: tau3-telecom-0, tau3-banking_knowledge-0 — have task_config.json but NO docker-compose.yaml (incomplete). Domain counts now telecom 115/banking 98 (were 114/97). The 375 REAL tasks intact; only these 2 spurious added.
- preflight (fail-closed, 55) correctly FAILS: task_config_present=375/377 (the 2 spurious missing per its discovery).
### DECISION NEEDED (not fixing dataset unilaterally):
- (a) remove the 2 spurious -0 dirs (they're malformed artifacts, not in frozen 375) → re-verify 375 → re-pin freeze tree_tar → preflight PASS → Pod A re-proof. OR
- (b) preflight validates against frozen taskid_list (375) not glob-all-dirs (excludes spurious by definition).
- Recommend (a)+(b): remove artifacts AND harden preflight to the taskid_list. Then re-proof (55 3-hardening) with REAL tasks (telecom-task-*, banking-task-*, NOT -0).

## UPDATE 22:20 — quarantine DONE (orchestrator a-improved). 2 spurious dirs were MALFORMED
- PROVENANCE: tau3-telecom-0 (mtime 18:33:28) + tau3-banking_knowledge-0 (mtime 18:33:41), owner root:root, ~3.8h old (NOT active/recent → safe to move). ROOT: in both, `task_config.json` is a DIRECTORY not a file (drwxr-xr-x), + no docker-compose.yaml → malformed WIP artifacts. Full ls-laR in images/tau3/quarantine_20260704/PROVENANCE.txt.
- ACTION: mv (reversible) both → images/tau3/quarantine_20260704/ (OUTSIDE dataset tree). dataset_dirs_now=375, quarantined=2. Restore = mv back if ever needed.
- NEXT: re-pin freeze tree_tar (375) → harden preflight to frozen taskid_list → preflight PASS → confirm P0 digests → Pod A re-proof.

## UPDATE 22:35 — DoD-③ COMPLETE ✅ (commit 623eeab)
- Pod A (env-kvm-15238487-rlgbn) transport-proof PASS 4/4 domains, FAIL=0. Per task: P0 by-digest pull + TASKCFG_SHA_MATCH (mounted /app/task_config.json sha256==source) + SIDECAR_8000_UP + IMPORT_TAU2_FASTMCP_DOMAINS_OK (55#1, scipy/pyaudio fix confirmed in-container) + MAIN_TO_SIDECAR_LINK_OK + NO_PUBLIC_NET_CONFIRMED (55#3). Real tasks 1/domain (quarantined -0 excluded).
- FULL CHAIN done: build([all]+build-essential) → P0 push (main@3591be51 runtime@bf0f3ab4, confirmed 200 by-digest) → manifest backfill+status=full_transport_proven → freeze RESTORED (350576c2) + quarantine 2 malformed dirs → preflight hardened(frozen taskid_list ef22ab27)+PASS 375/375 → Pod A re-proof PASS 4/4. Commits: 0c69e60, 9be6e20, 623eeab. Evidence reports/tau3_transport_proof_20260704.log.

## 2026-07-04 23:00 CST — surface:55 adversarial review of tau3 DoD-③

Verdict: PASS. I tried to refute the DoD-③ claim and found no blocking issue in transport proof, dataset freeze, preflight hardening, or manifest status. Scope note: local checked-out repo HEAD was `5719bfb` and is not an ancestor of `623eeab`; however `623eeab` exists and is contained by `origin/main`, so this review is anchored to the committed objects and shared artifacts rather than the local working tree HEAD.

Evidence:
- P0 by-digest manifest probes from Pod A returned HTTP 200 with matching Docker-Content-Digest for both required images: `tau3-full-main@sha256:3591be51f3901080271eb4a9c1bd9c680fc999ced3c44fc42ccec7d788e81645` and `tau3-full-runtime@sha256:bf0f3ab41886d31db8f7c93f874d63420c1679733dcce1e4c0663c1c11117fa8`.
- `manifests/images/tau3_full_p0_20260704.yaml` at commit `623eeab` is machine-readable and records `status: full_transport_proven_pod_a_4domains`, the two P0 digest refs, fallback tar sha256 values, `task_count: 375`, domain split `50/114/114/97`, frozen taskid hash `ef22ab2741b57b0fd84ed452366d63a132de58ab19b12c36376cf7eb584c9dc0`, freeze tree hash `350576c207e0daa8deee21a1754af1908f1df08efaf75027f39ab849844b8763`, and effective compose mount hash `b3c8700bea384d34e27657a8482e1f5e370c652a86ced8789186349d141e8052`.
- 55#3 wording is preserved: image rows still carry `dockerfile_offline_ready: false` and notes that build still depends on live apt/git/transitive deps. The manifest therefore proves transport, not full offline execution readiness.
- `scripts/tau3_transport_preflight.py` at `623eeab` hard-codes the frozen taskid sha and count, checks 375/375 task configs, generates the effective compose with `./runtime-server/task_config.json:/app/task_config.json:ro`, and fail-closes on count/hash/mount/config mismatches. Direct py_compile and live preflight on the shared dataset returned rc=0 with `PREFLIGHT: PASS (375/375 frozen-taskid + task_config + uniform effective compose w/ mount)`.
- Shared dataset live recomputation matches the manifest: `375` tau3 task directories, taskid hash `ef22ab27...`, tree tar hash `350576c2...`, domain counts `airline=50`, `retail=114`, `telecom=114`, `banking_knowledge=97`.
- Quarantine is real and reversible at `images/tau3/quarantine_20260704/`, with `PROVENANCE.txt` plus two malformed WIP dirs (`tau3-banking_knowledge-0`, `tau3-telecom-0`). Both had `task_config.json` as a directory and no compose file; excluding them from the frozen 375 is justified.
- Parsed `reports/tau3_transport_proof_20260704.log` from both commit and shared image proof root: exactly 4 task lines, all include `TASKCFG_SHA_MATCH`, `SIDECAR_8000_UP`, `IMPORT_TAU2_FASTMCP_DOMAINS_OK`, `MAIN_TO_SIDECAR_LINK_OK`, and `NO_PUBLIC_NET_CONFIRMED`, with final `PASS=4/4 FAIL=0`.
- Independent Pod A rerun on `tau3-airline-0` reproduced the proof: digest pulls/inspect matched the two expected sha256 refs, mounted `/app/task_config.json` sha matched source (`c891fa12...`), sidecar port 8000 came up, import probe succeeded for tau2/fastmcp/domain modules, main-to-sidecar link succeeded, and public network probe failed with DNS temporary failure as expected. Follow-up check showed no leftover proof containers or networks.

Non-blocking observations:
- The import probe emits LiteLLM model-cost-map warning/noise before falling back to local backup; because the no-public-net check is explicit and the import succeeds, this is not a blocker.
- Local repo checkout lag (`5719bfb` vs `623eeab`) can confuse future reviewers; prefer `git show 623eeab:<path>` or update local checkout before follow-up reviews.

Decision: tau3 spec/transport stage is closed as `spec-closed/execution-blocked`: DoD-③ transport proof passes, while full offline execution remains gated by later runner/full-eval acceptance and the manifest's intentional `offline_ready=false` build note.

## CLOSURE 2026-07-04 — tau3 DoD-③ OFFICIALLY CLOSED (dual-sign)
- **85 (delivery):** full chain build→P0 push→manifest→freeze-restore+quarantine→preflight-harden(375/375)→Pod A transport-proof PASS 4/4. Commits 0c69e60, 9be6e20, 623eeab, 3adbfe3 pushed origin/main. Evidence reports/tau3_transport_proof_20260704.log.
- **55 (review PASS):** independent Pod A re-run of airline-0 fully reproduced. Verdict PASS.
- **口径:** spec-closed / execution-blocked (dockerfile_offline_ready=false retained — materialized w/ internal mirrors + commit-pinned, NOT offline-build-ready).
- **Next:** 85 role → TB2.1 canary REVIEW seat (55 executes, 85 reviews; cross-family adversarial maintained).

---
## 2026-07-04 20:1x CST — surface:86 — 三 bench 官方榜 × 中转站对照 + 选型
**报告**: `bench/reports/official_leaderboard_vs_relay_20260704.md`（源=官方 JSON/HTML,非三方聚合）
- **中转站** `OPENAI_BASE_URL=8.130.49.170/v1` = 10 模型;agent 相关 6:gpt-5.2/5.3-codex/5.3-codex-spark/5.4/5.4-mini/5.5（key 未落盘）。
- **干净可复现锚只有 2 个**:① SWE-bench Verified bash-only(mini) **gpt-5.2-high=72.8%/500 pass@1**（=我们口径,首选验 harness）;② Terminal-Bench 2.1 terminus-2 **gpt-5.5=78.2%/89×5**。
- **选型建议**:P0 先打 gpt-5.2-high→72.8% 作 harness 合格证;P1 gpt-5.5+terminus-2→78.2%;RepoZero 无 GPT 官方锚只能当新点。100 并发安全(并发不入官方口径,前证零压分)。
- **口径修正/警示**:①TB2.1=**5 attempts 非×3**(发射器须改);②SWE-V 榜冻结~2026-02→5.3/5.4/5.5 不在榜;③三方站 "GPT-5.5 82.6%/Opus4.8 88.6%/Fable5 95%" 官方 0 命中**严禁引**;④RepoZero 官方**400 案非 188**、无 LLM judge;⑤**gpt-5.4-mini 三榜全无官方锚**→full500 不可直接对榜(佐证 70%=django 虚高)。
- TB2.0(勿混):GPT-5.3-Codex 64.7/GPT-5.2 54.0/**Qwen3-Coder-480B 23.9✓锚吻合**。

## 2026-07-04 23:54 CST — surface:55 — TB2.1 oracle closing canary on Pod A

Verdict: PARTIAL / FAIL-CLOSED. I did not modify the canonical map `repo/reports/scores/tb21_full89_oracle_infra_map_r5_final_20260703.json`. The direct shared-runner path was invalid for this canary because it preheated images successfully but then used runtime `put_archive` into read-only `/tests`, producing 0/8 unknown-agent style failures; this is not counted as task evidence. The privileged batched runner path was then used.

Execution evidence:
- Pod A: `env-kvm-15238487-rlgbn`, `DOCKER_HOST=unix:///var/run/docker.sock`, Docker `26.1.3`, storage driver `fuse-overlayfs`, data root `/docker-data-15238487`.
- Correct runner: `.worktrees/tb21-image-fixes-r3/scripts/run_terminal_bench_2_1_full89_batched_privileged_offline.sh`, dataset `shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703`, oracle agent, `TB2_OFFLINE_TEST_BOOTSTRAP=1`, bind payload preflight enabled.
- Invalid direct-run log: `repo/_coordination/20260625_harbor_bench/logs/tb21_oracle_canary8_poda_privileged_c4_20260704t15221783178570z.log`; preheat was healthy (`present=89 missing=0 errors=0 pulled=7 retagged=240 tar_verified=89`) but runtime copy hit read-only `/tests`.
- Privileged 8-row attempt log: `repo/_coordination/20260625_harbor_bench/logs/tb21_oracle_canary8_poda_privileged_runner_c4_20260704t15311783179105z.log`.
- Privileged 8-row bind preflight JSON: `runs/terminal_bench_2_1_oracle_canary/tb21_oracle_canary8_poda_privileged_runner_c4_20260704t15311783179105z/tb21_bind_payload_preflight_tb21_oracle_canary8_poda_privileged_runner_c4_20260704t15311783179105z.json`, counts `ok=84 blocked=5 errors=5 tasks=89`.
- R7-aware privileged 3-row run log: `repo/_coordination/20260625_harbor_bench/logs/tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z.log`.
- R7-aware 3-row image refs were explicit by digest and retagged to compose refs: `git-multibranch` closure-r7 `@sha256:c2d41265...`, `reshard-c4-data` closure-r7 `@sha256:0577dc62...`, `video-processing` closure-r6 `@sha256:d0b64a1e...`.
- R7-aware 3-row gate passed before execution: bind payload preflight `ok=3 blocked=0 errors=0`, runtime closure static gate `closed tasks=3 open=0`, preheat `present=3 missing=0 errors=0 pulled=0 retagged=12 tar_verified=3`.
- R7-aware 3-row artifact: `shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/results.json`.
- Strict summary: `runs/terminal_bench_2_1_oracle_canary/tb21_batched_oracle_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/batch_01_of_01/tb21_strict_summary.json`, counts `total=3 resolved=0 unresolved=3 infra_fail=0 missing_artifact=0 timeout=0 token_sum.input=0 token_sum.output=0`.

Per-task canary outcome:

| task | resolved | attribution | evidence path |
|---|---:|---|---|
| git-multibranch | false | Ran under privileged stack with oracle token=0. Not Docker EOF. Test failed at SSH git clone with `fatal: protocol error: bad line length character: Welc`, then `project-test` directory missing. This is the known git-webserver/git-multibranch service/protocol regression, not a rootless transport failure. | `shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/git-multibranch/git-multibranch.1-of-1.tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/sessions/tests.log` |
| make-doom-for-mips | not run | Fail-closed before execution: oracle payload `solution.sh` is an absolute symlink into the r5 dataset, rejected as `oracle_payload_solution_symlink`; no task score claimed. | `runs/terminal_bench_2_1_oracle_canary/tb21_oracle_canary8_poda_privileged_runner_c4_20260704t15311783179105z/tb21_bind_payload_preflight_tb21_oracle_canary8_poda_privileged_runner_c4_20260704t15311783179105z.json` |
| pytorch-model-recovery | not run | Fail-closed before execution: oracle payload `solution.sh` is an absolute symlink into the r5 dataset, rejected as `oracle_payload_solution_symlink`; no task score claimed. | same preflight JSON as above |
| reshard-c4-data | false | Ran under privileged stack with oracle token=0. Not Docker EOF. Pre-baked C4 data loaded, but `/app/compress.py` failed with `ModuleNotFoundError: No module named 'tqdm'`; image/runtime dependency closure is still incomplete for this r7-aware canary path. | `shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/reshard-c4-data/reshard-c4-data.1-of-1.tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/sessions/tests.log` |
| sam-cell-seg | not run | Fail-closed before execution: oracle payload `solution.sh` is an absolute symlink into the r5 dataset, rejected as `oracle_payload_solution_symlink`; no task score claimed. | same preflight JSON as above |
| schemelike-metacircular-eval | not run | Fail-closed before execution: oracle payload `solution.sh` is an absolute symlink into the r5 dataset, rejected as `oracle_payload_solution_symlink`; no task score claimed. | same preflight JSON as above |
| train-fasttext | not run | Fail-closed before execution: oracle payload `solution.sh` is an absolute symlink into the r5 dataset, rejected as `oracle_payload_solution_symlink`; no task score claimed. | same preflight JSON as above |
| video-processing | false | Ran under privileged stack with oracle token=0. Not Docker EOF. Pytest collection failed immediately because `/tests/test_outputs.py` imports `toml` and the runtime image lacks that module: `ModuleNotFoundError: No module named 'toml'`; image/verifier closure is incomplete. | `shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/video-processing/video-processing.1-of-1.tb21_full89_batched_batch_01_of_01_oracle_c3_tb21_oracle_canary3_poda_privileged_runner_c3_20260704t15461783179960z/sessions/tests.log` |

Decision:
- The privileged KVM stack removed the old rootless `docker_api_eof_before_injection` class for the 3 runnable tasks: agent/test logs and results artifacts exist, with no timeout, missing artifact, or infra-fail counter.
- This canary does **not** recover the 8 old EOF tasks as-is. Five are currently blocked by r7 payload packaging symlinks, and three expose real task/image closure regressions.
- Next minimal actions before counting any of these toward oracle canonical recovery: materialize non-symlink oracle payloads for the five blocked tasks; add/verify `tqdm` closure for `reshard-c4-data`; add/verify `toml` verifier/runtime closure for `video-processing`; fix/verify the git-multibranch SSH/git service protocol path. Then rerun the same privileged runner and keep the canonical map unchanged until reviewer 85 accepts the evidence.
