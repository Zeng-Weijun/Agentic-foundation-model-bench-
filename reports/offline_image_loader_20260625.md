# Offline Image Loader Report - 2026-06-25

## Scope

Added a narrow offline Docker image preload/check helper for worker-side use:

- `scripts/load_offline_images.sh`
- `scripts/check_offline_images_manifest.py`
- `scripts/test_offline_images_manifest.py`

No existing suite launcher, README, or manifest files were modified.

## Default Contract

The shell entrypoint defaults to:

- Manifest: `manifests/offline_images.example.yaml`
- Asset root: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`
- Docker host: `unix:///tmp/rl/run/docker.sock`

The helper uses only the local/shared filesystem and the local `docker` CLI. It does not pull images, call registries, install packages, or contact benchmark/model APIs.

## Worker Commands

Check only:

```bash
scripts/load_offline_images.sh --check
```

Load missing image tars from the default manifest and asset root:

```bash
scripts/load_offline_images.sh
```

Use explicit overrides:

```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock \
  scripts/load_offline_images.sh \
  --manifest manifests/offline_images.example.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --load
```

Machine-readable check output:

```bash
python3 scripts/check_offline_images_manifest.py \
  --manifest manifests/offline_images.example.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --check \
  --json
```

## Behavior

For each manifest image entry, the helper:

1. Lists local image tags with `docker image ls --format '{{.Repository}}:{{.Tag}}'`.
2. Compares the local tags with `expected_tags`, `required_images`, or `tags`.
3. Skips entries whose expected tags are already present.
4. Resolves tar sources from `source_path`, `source_paths`, `tar_paths`, or `image_tars`.
5. In `--check` / `--dry-run` mode, reports missing tags and available tar paths without loading.
6. In `--load` mode, runs `docker load -i <tar>` only for entries with missing expected tags and existing local tar files.
7. Prints a summary with `present`, `missing`, `loaded`, `skipped`, `tar_missing`, and `errors`.

Relative tar paths resolve against `--asset-root` first when present, otherwise against the manifest directory. Globbed `*.tar` sources and simple JSONL tar manifests are supported.

## Local Verification

I could not run real worker rootless Docker from this local session. Verification used local syntax checks plus a fake `docker` CLI to prove command construction, `DOCKER_HOST` defaulting, check-mode non-mutation, and load-mode skip/load behavior.

Commands run locally:

```bash
python3 -m py_compile scripts/check_offline_images_manifest.py scripts/test_offline_images_manifest.py
```

Result: exit code 0, no output.

```bash
python3 -m unittest scripts/test_offline_images_manifest.py
```

Result:

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.759s

OK
```

Wrapper-level default check with a fake local `docker` executable:

```bash
PATH=<fake-docker-bin>:$PATH scripts/load_offline_images.sh --check
```

Result:

```text
rc=1
docker_log=unix:///tmp/rl/run/docker.sock|image ls --format {{.Repository}}:{{.Tag}}
Summary: present=1 missing=5 loaded=0 skipped=1 tar_missing=5 errors=0
```

The nonzero return is expected for check mode because the local Mac does not have the shared worker image tars mounted at the manifest paths. The fake Docker log confirms the default `DOCKER_HOST` and that no `docker load` command ran.

## Remaining Blocker

The helper still needs a live worker smoke check against `DOCKER_HOST=unix:///tmp/rl/run/docker.sock` once the worker session is available. That check should start with `scripts/load_offline_images.sh --check` and only then run `scripts/load_offline_images.sh --load` if the missing tar paths are intentional and present on the shared filesystem.
