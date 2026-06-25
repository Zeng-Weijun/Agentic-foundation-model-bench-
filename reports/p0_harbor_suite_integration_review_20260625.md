# P0 Harbor Suite Integration Review - 2026-06-25

## Scope

Review-only lane for the current suite launcher and offline image checker. No code,
manifest, commit, push, remote mutation, image pull, or benchmark run was performed.

Reviewed surfaces:

- `/Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md`, especially `Project-Owned OCI Registry (P0 Harbor)`.
- `scripts/agentic_bench_suite.py`
- `scripts/check_offline_images_manifest.py`
- `manifests/suite.example.yaml`
- Nearby tests, wrappers, and image manifests used only to understand compatibility:
  `scripts/test_agentic_bench_suite.py`, `scripts/test_offline_images_manifest.py`,
  `scripts/load_offline_images.sh`, `manifests/offline_images.example.yaml`,
  `manifests/offline_images.repozero.yaml`, and
  `manifests/offline_images.tb21_fix_git.yaml`.

## Current State

- `WORKFLOW.md` defines the P0 registry as a workspace-local lightweight OCI registry,
  not full Harbor. It requires digest-pinned `image_ref`, optional fallback tar and
  checksum, worker CA refresh, `docker pull`, fallback `docker load`, one
  `docker run --network none` smoke, then `image_ready` before the bench starts.
- `scripts/agentic_bench_suite.py` is dry-run-first. `load_suite_config()` validates
  the suite and secrets, `build_run_plan()` creates run metadata and command strings,
  and `_execute_plan()` runs adapter commands only after rejecting unwired adapters.
  There is no image preflight field or Docker side effect in the suite path today.
- `scripts/check_offline_images_manifest.py` is a legacy tag/tar checker. It reads
  `required_images` or `expected_tags`, compares them against
  `docker image ls --format '{{.Repository}}:{{.Tag}}'`, and optionally runs
  `docker load -i <tar>`. It does not support registry digest refs, CA refresh,
  fallback tar sha validation, `docker pull`, `docker image inspect`, or
  `docker run --network none` readiness smoke.
- `manifests/suite.example.yaml` has worker offline/rootless fields and per-bench
  adapter/model/params, but no per-bench image requirement link. Docker-dependent
  benches and docker-free benches are indistinguishable to the suite planner.
- Existing tests assert dry-run command construction, secret safety, model-profile
  override behavior, and legacy image checker check/load behavior. They do not assert
  exact full JSON shape, so additive optional fields can be introduced if
  absent-by-default behavior is preserved.

## Recommendation

Use a two-layer, additive integration:

1. Keep the suite runner as the orchestrator. It should know that a bench has required
   image assets, emit that requirement in dry-run JSON, and fail closed before adapter
   execution when required image warmup fails.
2. Keep image mechanics in `check_offline_images_manifest.py`. Extend it from
   "tag/tar checker" to "registry-or-fallback image readiness checker" while preserving
   current `--check` and `--load` behavior for existing manifests and tests.

Do not put Docker pull/load/run side effects inside `load_suite_config()`,
`_validate_config()`, `_command_preview()`, or `build_run_plan()` dry-run planning.
Dry-run should remain deterministic and local. The only side-effectful integration
point should be the future `--execute` path, before `_run_one()` starts the adapter.

## Suite Manifest Field

Add one optional per-bench field. Omitted means "no Docker image preflight", which
preserves current dry-run output and behavior for VitaBench and other
docker-free rows.

Suggested field shape:

```yaml
image_preflight:
  required: true
  manifest: manifests/offline_images.repozero.yaml
  image_ids:
    - repozero_py2js_repoarena_runtime
  mode: warmup
  fail_closed: true
```

Field semantics:

- `required`: if true, `--execute` must not start the adapter until all referenced
  image entries report `image_ready`.
- `manifest`: path to an offline image manifest, relative to repo root unless absolute.
- `image_ids`: exact `images[].id` entries to check. This avoids scanning and failing
  unrelated entries in the broad example manifest.
- `mode`: `check` for read-only inventory, `warmup` for the P0 Harbor runner order.
  Dry-run should always render a preview, never warm up.
- `fail_closed`: default true for `required: true`.

Avoid a global suite-level default that applies to every bench. Several enabled rows
are docker-free or have unproven image inventories; a broad default would make
VitaBench or other docker-free rows surprisingly depend on Docker assets.

## Offline Image Manifest Fields

Extend image entries with the fields from `WORKFLOW.md`, while continuing to accept
existing `required_images`, `source_path`, `source_paths`, `tar_paths`, and
`image_tars`.

Suggested image entry:

```yaml
images:
  - bench: repozero/repoarena
    id: repozero_py2js_repoarena_runtime
    env_id: repozero-repoarena-new
    image_transport: registry
    image_ref: 100.97.118.137:8555/swe-data-harness/repozero-repoarena-new@sha256:<digest>
    needs_network: false
    fallback_transport: oci_tar
    fallback_tar: /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/images/repozero/repoarena-new_latest.tar
    fallback_tar_sha256: <sha256>
    smoke_command:
      - /bin/sh
      - -lc
      - python --version 2>/dev/null || python3 --version 2>/dev/null || echo shell-ok
```

Compatibility mapping:

- Existing `required_images` remains the legacy tag/check input.
- Existing `source_path` remains the legacy tar source.
- New `image_ref` is for digest-pinned registry readiness. Require `@sha256:` when
  `image_transport: registry`.
- New `fallback_tar` and `fallback_tar_sha256` are the P0 fallback path. Existing
  `sha256_path` can continue as metadata, but warmup needs an inline expected digest
  or a resolved sha256 file reader.
- `needs_network: false` should mean the benchmark container smoke runs with
  `--network none`; it should not be interpreted as "do not pull from the internal
  project registry during warmup".

## Function-Level Changes

### `scripts/agentic_bench_suite.py`

Recommended minimal functions:

- Add `_normalize_image_preflight(bench, *, bench_id, repo_root) -> dict | None`.
  Validate the optional per-bench `image_preflight` mapping, normalize the manifest
  path, require a non-empty `image_ids` list when `required: true`, and reject a real
  secret under any auth field. Prefer `registry_auth_env` if credentials are ever
  needed.
- Add `_image_preflight_command_preview(preflight, worker, suite_path) -> str`.
  Render a shell-safe preview such as:

  ```bash
  DOCKER_HOST=unix:///tmp/rl/run/docker.sock python3 scripts/check_offline_images_manifest.py --manifest manifests/offline_images.repozero.yaml --only-id repozero_py2js_repoarena_runtime --warmup --json
  ```

- In `build_run_plan()`, call `_normalize_image_preflight()` after `params` and
  adapter fields are known, then attach a compact `run["image_preflight"]` object
  only when the bench declares it. Do not add the key for benches without the field.
- In `_print_human()`, print one short preflight line only when present.
- In `_execute_plan()`, before submitting adapter runs to the thread pool, run a new
  `_run_image_preflights(plan, output_root)` gate. Keep `_run_one()` adapter-only.
  Return a distinct nonzero status, for example `3`, when required image preflight
  fails before any adapter starts.
- Keep `dry_run=True` behavior side-effect-free. If a CLI flag is added, use explicit
  names such as `--image-preflight {off,check,warmup}` or `--skip-image-preflight`;
  do not make `--dry-run` call Docker.

### `scripts/check_offline_images_manifest.py`

Recommended minimal functions:

- Extend `manifest_entries()` to parse legacy fields plus `env_id`,
  `image_transport`, `image_ref`, `needs_network`, `fallback_transport`,
  `fallback_tar`, `fallback_tar_sha256`, `registry_ca_path`, and `smoke_command`.
- Add `--only-id` as a repeatable CLI filter. The suite should never have to evaluate
  every row in `offline_images.example.yaml` just to start one bench.
- Keep current `--check` semantics read-only. It may run `docker image inspect` or
  `docker image ls`, but must not pull, load, copy certs, or run containers.
- Add an explicit `--warmup` mode for the P0 Harbor runner order:
  1. Use `DOCKER_HOST`, defaulting to `unix:///tmp/rl/run/docker.sock`.
  2. Install or verify registry CA only if the manifest/CLI explicitly asks for it.
  3. `docker pull <image_ref>` for digest-pinned internal registry refs.
  4. If pull fails, verify `fallback_tar_sha256`, then `docker load -i <fallback_tar>`.
  5. Resolve the runnable image ref and run one `docker run --rm --network none ...`
     smoke command.
  6. Emit JSON status `image_ready` only after the smoke succeeds.
- Add `docker_image_inspect(ref, env)` instead of relying only on `docker image ls`.
  Digest refs and loaded images can be invisible to the current tag-only comparison.
- Add `sha256_file(path)`, `verify_fallback_tar(path, expected)`, `docker_pull(ref)`,
  and `docker_run_network_none_smoke(ref, smoke_command)`.
- Do not call `docker version` or Docker SDK in the checker. Current worker evidence
  shows simple `docker info`, `docker image ls`, and cached `docker run --network none`
  can work while `/version` and SDK negotiation fail.

## Compatibility Risks

- **Dry-run regression risk:** Adding `image_preflight` unconditionally to every run
  would change JSON consumers and human output. Attach it only for benches that declare
  the field.
- **Unexpected broad execution risk:** A global image preflight against
  `offline_images.example.yaml` would fail many unrelated entries. Always filter by
  `image_ids`.
- **Mutation risk from wrapper defaults:** `scripts/load_offline_images.sh` defaults
  to `--load` when no mode is passed. The suite should call the Python checker with an
  explicit mode, not the shell wrapper without `--check` or `--warmup`.
- **Digest verification gap:** Current `docker image ls` tag comparison cannot prove
  a digest-pinned `image_ref` from the project registry. Harbor/P0 readiness needs
  `docker pull` or `docker image inspect` by digest plus a run smoke.
- **Rootless worker Docker gap:** The worker can run some cached-image commands with
  `--network none`, but `/version` and Python Docker SDK negotiation have known EOF
  failures. Preflight code must stay CLI-based and avoid SDK/version probes.
- **CA installation risk:** Worker CA paths include both Docker certs.d and rootless
  locations. Auto-copying certs during dry-run would be wrong, and auto-copying during
  execute should be explicit, idempotent, and logged.
- **Internal registry versus public internet:** The offline policy forbids public
  pulls, but P0 registry pulls are an approved internal transport. The checker should
  reject non-approved registries for `image_transport: registry` unless explicitly
  allowed by manifest policy.
- **Concurrency risk:** `_execute_plan()` currently uses a thread pool. First-time
  pulls or fallback loads for the same image should be deduped or serialized before
  adapter parallelism begins.
- **Disabled placeholder risk:** `suite.example.yaml` disabled rows are skipped before
  planning. Adding image fields to disabled rows is safe only if the planner continues
  to skip them before validating referenced files that may not exist yet.
- **Secret validation risk:** `_walk_config()` rejects concrete token/secret values.
  Any future registry credential should be represented as `registry_auth_env`, not
  `registry_token: <value>`.

## Test Suggestions

Keep these existing commands green after any implementation:

```bash
python3 -m py_compile scripts/agentic_bench_suite.py scripts/check_offline_images_manifest.py scripts/test_agentic_bench_suite.py scripts/test_offline_images_manifest.py
python3 -m unittest scripts.test_agentic_bench_suite scripts.test_offline_images_manifest
python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --dry-run --json --only vitabench_delivery_one_task_smoke --model-profile dev_proxy_gpt54mini_8130
```

Add focused suite-runner tests:

- A suite fixture with no `image_preflight` keeps existing dry-run fields and does not
  call Docker.
- A bench fixture with `image_preflight.required: true` produces
  `run["image_preflight"]` and a checker command preview while leaving the adapter
  `command_preview` intact.
- A disabled bench with `image_preflight` is skipped and does not require its manifest
  file to exist.
- `--only` with one preflight-enabled bench includes only the requested `image_ids`.
- `--execute` fails before adapter launch when the checker returns nonzero for a
  required preflight, and records the preflight log path.

Add focused image-checker tests with fake `docker`:

- Legacy `--check` and `--load` tests continue to pass unchanged.
- Registry entry in `--check` mode performs no `docker pull`, `docker load`, or
  `docker run`.
- Registry entry in `--warmup` mode calls `docker pull <digest-ref>` then
  `docker run --rm --network none`.
- Pull failure with matching `fallback_tar_sha256` calls `docker load -i` and then
  the `--network none` smoke.
- Pull failure with checksum mismatch exits nonzero and does not call `docker load`.
- Tag-only `image_ref` is rejected when `image_transport: registry`.
- `--only-id` filters out unrelated manifest entries and avoids false failures.

## Minimal Rollout Order

1. Extend `check_offline_images_manifest.py` schema parsing and tests while preserving
   all legacy modes.
2. Add a tiny registry/digest fixture test with fake Docker.
3. Add `image_preflight` support to `agentic_bench_suite.py` in dry-run plan metadata
   only.
4. Link one known Docker bench, preferably RepoZero, to
   `manifests/offline_images.repozero.yaml` with `image_ids` set to
   `[repozero_py2js_repoarena_runtime]`.
5. Add the `--execute` pre-adapter fail-closed gate only after the checker has a
   verified fake-Docker warmup path.
6. Run a live worker warmup smoke manually for one image before enabling broad suite
   execution.

This keeps existing dry-run/test behavior stable while making the Harbor/P0 image
contract explicit enough to fail closed before benchmark adapters consume missing or
wrong Docker environments.
