# tau3-bench — dataset-pin freeze + 375-image P0 manifest DRAFT (by-85, 2026-07-04)

Pure docs/manifest — **no image build/push, no launch, no model call.** Freezes the tau3 dataset pin and drafts the P0 image-transport manifest so the enable line can start fail-closed (charter DoD). Extends `reports/tau3_recon_20260704.md`. Digests/shas that require a build are marked `PENDING_BUILD` (to be filled at build-execution, not now).

## 1. Dataset pin — FROZEN

| field | value |
|---|---|
| upstream repo | `github.com/sierra-research/tau2-bench` |
| upstream ref | `dev/tau3` (≈ `v1.0.0`) |
| **upstream commit** | **`17e07b1da2bbc0cadfddeea36412686e0604127b`** |
| Harbor adapter path | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/adapters/tau3-bench` |
| **adapter commit** | **`387625f`** |
| generated dataset path | `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-atlas/harbor/datasets/tau3-bench` |
| **task count** | **375** (verified: `find -maxdepth1 -type d` = 375) |
| domain split | airline=50, retail=114, telecom=114, banking_knowledge=97 (verified) |
| **task-id list sha256** | **`ef22ab2741b57b0fd84ed452366d63a132de58ab19b12c36376cf7eb584c9dc0`** (`ls DS \| sort \| sha256sum`) |
| per-task required files | `task.toml`, `instruction.md`, `environment/docker-compose.yaml`, `environment/Dockerfile`, `environment/runtime-server/Dockerfile`, `solution/`, `tests/` (verified present on sample) |
| env/docker-compose.yaml | **all 375 identical**, sha256 `e1aa85bb70ab83120e8e863036ea6bb41b600a35a0e5d8b65fce6d0b5a05f1c1` |

**Freeze status: FROZEN at the pin above.** Immutable anchors = {upstream commit, adapter commit, task-count 375, domain split, task-id-list sha256, compose sha256}. Any change to these = a new pin (must re-freeze + re-manifest). **TODO at freeze-execution (needs a run on the host with the dataset):** compute the full per-file tree hash (or a `tar --sort=name` tar+sha256) of the 375-task tree and record it here; today's anchors (task-id list + compose sha) already detect id-set or compose drift.

## 2. Image contract — 2-image (justified)
Empirical finding (read-only, this run): across all 375 tasks the **`environment/docker-compose.yaml` is byte-identical (1 unique hash)**, the **main `environment/Dockerfile` is 1 unique**, and the **`environment/runtime-server/Dockerfile` is 1 unique**. The only per-task variation is the DATA (task.toml/instruction/solution/tests + domain DB). Therefore **two images cover all 375 tasks** — the per-domain (8-image) option from the feasibility draft is NOT needed. compose declares the MCP sidecar via `build: context: ./runtime-server`.

## 3. 375-image P0 manifest — DRAFT (not built/pushed)
```yaml
schema_version: agentic_bench.image_manifest.v1
bench_id: tau3_bench
status: draft_pending_build_and_transport      # NOT built, NOT pushed
source:
  repo: github.com/sierra-research/tau2-bench
  ref: dev/tau3
  commit: 17e07b1da2bbc0cadfddeea36412686e0604127b
  adapter_path: /mnt/.../swe/bench/swe-atlas/harbor/adapters/tau3-bench
  adapter_commit: 387625f
  dataset_taskid_list_sha256: ef22ab2741b57b0fd84ed452366d63a132de58ab19b12c36376cf7eb584c9dc0
contract_basis: >-
  all 375 tasks share identical env/docker-compose.yaml (sha256 e1aa85bb...) + main Dockerfile (1 unique)
  + runtime-server Dockerfile (1 unique) => 2-image contract covers all 375; task data mounted at runtime.
images:
  - id: tau3_full_main
    role: harbor_task_main_runtime
    required: true
    build_context: <task>/environment          # Dockerfile identical across 375
    image_ref: 100.97.118.137:8555/swe-data-harness/tau3-full-main@sha256:<DIGEST_PENDING_BUILD>
    fallback_tar: /mnt/shared-storage-user/.../images/tau3/tau3-full-main_<STAMP>.tar
    fallback_tar_sha256: <PENDING_BUILD>
  - id: tau3_full_runtime
    role: tau3_runtime_mcp_sidecar
    required: true
    build_context: <task>/environment/runtime-server   # compose build: context ./runtime-server; identical across 375
    image_ref: 100.97.118.137:8555/swe-data-harness/tau3-full-runtime@sha256:<DIGEST_PENDING_BUILD>
    fallback_tar: /mnt/shared-storage-user/.../images/tau3/tau3-full-runtime_<STAMP>.tar
    fallback_tar_sha256: <PENDING_BUILD>
```

## 4. Build+transport procedure to materialize the manifest (SPEC — do NOT run now)
On a net-enabled builder (swe_dev/swe_dev2), NOT on a KVM pod:
1. **Offline-provision the Dockerfiles first** — the main + runtime-server Dockerfiles contain `apt-get`/`git clone`/`pip install` (per feasibility §2); bake internal-mirror pip.conf + apt proxy + vendored git sources so the built images are offline-self-contained (reuse the TB2.1/repo2env offline-bake patterns). Bake `rank-bm25` into the runtime image (banking retrieval).
2. **Build** `tau3-full-main` (context `<task>/environment`) and `tau3-full-runtime` (context `<task>/environment/runtime-server`) once each.
3. **Push by-digest** to P0 `100.97.118.137:8555/swe-data-harness/tau3-full-{main,runtime}` (insecure-registry, self-signed CA — same as TB2.1); record the returned `@sha256:` digests.
4. **Export fallback tars** to `/mnt/.../images/tau3/tau3-full-{main,runtime}_<STAMP>.tar` + record `sha256`.
5. **Fill** the 4 `PENDING_BUILD` fields; flip `status: full_transport_materialized_pending_worker_preflight`.
6. **Transport-proof** on a KVM pod (Pod A/B): P0 by-digest pull for both images + `--network none` compose-up of ≥1 task per domain (4 tasks) → prove the main↔MCP-sidecar link works under fuse-overlayfs (the new-vs-TB2.1 multi-container risk from recon §6). This is the DoD ③ P0-transport gate.

## 5. Freeze/manifest checklist (state for the enable line)
- [x] dataset pin frozen (commit + adapter + counts + task-id sha256 + compose sha256)
- [x] image contract determined = **2-image** (empirical, all-375-identical)
- [x] P0 manifest drafted (schema v1, 2 images, PENDING_BUILD placeholders)
- [ ] full tree-hash / dataset tar+sha (freeze-execution)
- [ ] images built + offline-provisioned (build-execution, net builder)
- [ ] P0 push by-digest + fallback tars + shas filled
- [ ] transport-proof on KVM pod (4-domain compose-up, sidecar link) = DoD ③
- [ ] then: 3-LLM relay preflight + oracle-gold + per-domain canary (recon §9) before any full run

**References:** `reports/tau3_recon_20260704.md` (§4 3-LLM, §6 KVM, §7 oracle-not-free, §9 DoD, §11/§11b anchors); `reports/tau3_offline_feasibility_20260702.md` (§2 offline decomposition, §3 enable contract); TB2.1 P0/offline-bake patterns in `MIGRATION_RUNBOOK_RJOB_20260703.md`.
