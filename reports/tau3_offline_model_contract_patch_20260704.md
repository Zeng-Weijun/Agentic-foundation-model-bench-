# tau3 — offline + model-contract patch (by-85, 2026-07-04) — closes 55's HIGH 1-4

Spec-level patch (no build/push/launch) answering `reports/tau3_recon_adversarial_review_by55_20260704.md`. Read-only facts verified against the actual dataset/Dockerfiles. **STATUS: spec-closed / execution-blocked — build + P0 push + transport-proof await lead GO.** (Terminology corrected throughout: **375-task** dataset served by a **2-image** contract — the earlier "375-image" phrasing is a misnomer, retired.)

## HIGH 1 — machine-readable P0 manifest ✅
Was a markdown placeholder → now `manifests/images/tau3_full_p0_20260704.yaml` (schema `agentic_bench.image_manifest.v1`, 2-image contract, structure FROZEN, digest/sha fields `PENDING` until build). `status: draft_spec_closed_execution_blocked`; `transport.digest_rows/fallback_rows = 0`; **enable_gate (55 re-review fix — the earlier `--require-offline-transport --verify-fallback` was stale, rc=2/unknown-flag): `python3 scripts/check_offline_images_manifest.py --manifest manifests/images/tau3_full_p0_20260704.yaml --check` (current dry-run check mode) must PASS before any suite/full enable.** `worker_target: rjob_privileged` (not rootless-vfs; MEDIUM-2). Existing smoke manifests (`tau3_bench.yaml`, `tau3_oracle_direct_smoke.yaml`) stay smoke-only; do NOT flip full until the gate is green.

## HIGH 3 — dataset pin = complete reproducibility contract ✅
- **Deterministic full-tree snapshot proof (COMPUTED, read-only):**
  `tree_tar_sha256 = 350576c207e0daa8deee21a1754af1908f1df08efaf75027f39ab849844b8763`
  method: `cd <parent>; tar --sort=name --mtime="2026-01-01 00:00:00" --owner=0 --group=0 --numeric-owner -cf - tau3-bench | sha256sum` (deterministic: sorted names + fixed mtime/owner). Recorded in the manifest `dataset.tree_tar_sha256`.
- **`uv.lock` disposition:** the adapter tree is dirty on `uv.lock` (+ `.venv/.lock`). These are **adapter-build artifacts, NOT dataset inputs** — the generated dataset is already frozen by `{taskid_list_sha256, compose_sha256, tree_tar_sha256}`, which do not depend on the adapter venv. ⇒ **explicitly excluded** from the repro contract (`manifest.source.adapter_dirty_ignored: [uv.lock, .venv/.lock]`); adapter pinned by `adapter_commit 387625f`. (If a fully-clean adapter proof is later wanted: `git -C <adapter> stash` the lockfiles or add them to the adapter's `.gitignore` — cosmetic only, does not change the dataset.)

## HIGH 2 — Dockerfile offline-ization (both main + runtime-server) — TB2.1 vendor/内网 pattern
Both `environment/Dockerfile` and `environment/runtime-server/Dockerfile` currently do: `FROM python:3.12-slim` (untagged digest) → `apt-get update && install git` (public) → `git clone --depth=1 <github>` (**unpinned, moving HEAD**) → `pip install <root>[knowledge]` (+ `fastmcp>=3.0` for runtime, public PyPI). **Offline conversion (mirror the TB2.1/repo2env offline-bake):**
1. **Pin base by digest:** `FROM python:3.12-slim@sha256:<BASE_DIGEST>` — resolve the digest once from the internal registry and bake it (no floating tag).
2. **Vendor the upstream source @ the pin commit (replaces the clone):** on a net builder, `git clone <repo> && git -C tau2-bench checkout 17e07b1da2bbc0cadfddeea36412686e0604127b && git -C tau2-bench archive --format=tar 17e07b1 -o tau2-bench-17e07b1.tar`; stage `tau2-bench-17e07b1.tar` on shared FS; in the Dockerfile **`COPY tau2-bench-17e07b1.tar /opt/ && tar -xf ...`** instead of `git clone` → **deterministic, commit-pinned, no network.** (Removes the "moving HEAD" defect + the `TAU2_BENCH_COMMIT` checkout 55 flagged as missing.)
3. **apt via internal mirror:** bake `/etc/apt/apt.conf.d/` + sources.list to `mirrors.i.h.pjlab.org.cn` (jammy/noble) + the `apt-proxy.conf` that survives sudo — same pattern as the TB2.1 regression/offline work. (git is only needed for archive at bake time; the runtime image can drop it.)
4. **pip via internal mirror + staged wheels:** bake `/etc/pip.conf` → `mirrors.i.h.pjlab.org.cn/repository/pypi-*`; pre-stage the `[knowledge]` extras + `fastmcp>=3.0` (+ `rank-bm25` for banking) as wheels; `pip install --no-index --find-links <staged>` for full offline. Bake `HF_HUB_OFFLINE=1` if any HF asset is pulled.
5. **Result:** both images build with zero public network, pinned to 17e07b1 + fixed base digest → reproducible. Set `manifest.images[*].dockerfile_offline_ready: true` only after this lands.
> These are Dockerfile edits to be applied on the **build worktree** at build-execution (NOT now); the pristine dataset Dockerfiles stay untouched until then.

## HIGH 4 — explicit 3-LLM relay contract (replaces the `gpt-5.2` defaults)
The dataset defaults (`task.toml` `TAU2_USER_MODEL=gpt-5.2`, `TAU2_NL_ASSERTIONS_MODEL=gpt-5.2`, `TAU2_USER_REASONING_EFFORT=low`; `docker-compose.yaml` env passthrough) are placeholders — scores are NOT comparable unless all three roles are pinned. **tau3 run contract (freeze per run, inject via compose/task env, do NOT rely on defaults):**
| role | env var | value (pin per run) | notes |
|---|---|---|---|
| **agent** | `--agent-llm` / Harbor `tau3_llm_agent` model | **`gpt-5.4-mini`** (model under test; Qwen model-id in Phase 2) | reasoning_effort + temperature pinned; **match the anchor 口径** — board-comparable run uses provider-default effort (see `tb21_official_anchor_check_20260704.md`), not xhigh |
| **user-sim** | `TAU2_USER_MODEL` + `TAU2_USER_REASONING_EFFORT` | **`gpt-5.4-mini`**, effort **`low`** — FIXED across all agent runs | drives the dialogue; affects score — hard-pinned (no default) |
| **judge** | `TAU2_NL_ASSERTIONS_MODEL` | **`gpt-5.4`** — FIXED (stronger than agent → avoids self-grading when agent=gpt-5.4-mini) | NL-assertion scorer — hard-pinned (no default) |
| all roles | `OPENAI_BASE_URL` | **`http://100.96.122.22:18540/v1`** — single pod-facing relay URL, no default (distinct from P0 image registry `100.97.118.137:8555`) | `OPENAI_API_KEY` from `/data/nips/shared_bench/api_config.env` |

Additional contract requirements (55's HIGH-4):
- **Real per-role completion health check** — a 1-token chat/completions to the relay **for each of agent/user-sim/judge** (not just `/v1/models`), with `--noproxy` (relay lesson). Fail-closed if any role errors.
- **Usage parsing by role** — separate agent vs user-sim vs judge token classes in the run report; **oracle-gold MUST show nonzero user-sim + judge tokens** (oracle is NOT 0-token here — recon §7).
- **Temperature/seed** pinned per role; record all three model IDs + efforts + temps in the run manifest so any tau3 score is reproducible + comparable.
- **Roll-out:** 4-domain canary (airline/retail/telecom/banking, 1 task each) at conservative concurrency; measure relay saturation (3× call classes × tasks) before scaling.

## MEDIUM notes (folded in)
- **M1** — compose still has `build:` → after images are built+pushed, switch the task `docker-compose.yaml` to `image: <P0 digest>` (or Harbor prebuilt transport) so no runtime build. Tracked as `manifest.transport.compose_runtime_build: true`.
- **M2** — target = rjob privileged (`DOCKER_HOST=unix:///var/run/docker.sock`, `ulimit -n 65535`), not the retiring rootless-vfs worker. In the manifest `worker_target`.
- **M3** — P0 capacity fine for the **2 images**; "375-image" misnomer corrected → **375 TASKS served by a 2-IMAGE contract** (empirically proven). transport-proof = 4-domain compose-up (DoD-3).

## Closure checklist for 55's re-review
- [x] HIGH-1 machine-readable manifest at `manifests/images/tau3_full_p0_20260704.yaml` (structure frozen, PENDING digests, enable-gate + rjob target)
- [x] HIGH-3 deterministic `tree_tar_sha256 = 350576c2…4b8763` recorded + `uv.lock` explicitly excluded (adapter-build artifact)
- [x] HIGH-2 Dockerfile offline plan (base-digest pin + vendor tau2-bench@17e07b1 tar + internal apt/pip + staged wheels) — spec; apply on build worktree at build-execution
- [x] HIGH-4 explicit 3-LLM contract (agent/user-sim/judge pinned, per-role health check, per-role usage parsing, oracle nonzero user+judge)
- [ ] (build-execution) materialize digests/shas → gate green → then enable — NOT done (no build per instruction)

**Refs:** `manifests/images/tau3_full_p0_20260704.yaml`; `reports/tau3_{recon,dataset_pin_freeze}_20260704.md`; `reports/tau3_recon_adversarial_review_by55_20260704.md`; `reports/tb21_official_anchor_check_20260704.md` (effort 口径); `MIGRATION_RUNBOOK_RJOB_20260703.md` (TB2.1 offline-bake patterns).
