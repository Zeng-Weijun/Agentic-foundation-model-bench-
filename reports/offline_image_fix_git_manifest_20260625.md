# Offline Image Fix-Git Manifest Report - 2026-06-25

## Scope

Added an exact one-task Terminal-Bench 2.1 offline image manifest for the `fix-git` smoke target:

- Manifest: `manifests/offline_images.tb21_fix_git.yaml`
- Required tag: `tb2-offline/fix-git:20260425`
- Shared tar: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar`

No loader code, README files, suite launcher files, or broad offline manifests were changed.

## Manifest Contract

The manifest contains exactly one image entry:

```text
id: terminal_bench_2_1_fix_git_smoke
bench: terminal-bench-2.1
task_id: fix-git
required_images:
  - tb2-offline/fix-git:20260425
source_path:
  - /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
```

Worker metadata preserved in the manifest:

```text
worker_id: worker-j9jjd
worker_host: ws-4d5210c60d64c583-worker-j9jjd.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn
worker_hostname: zwj2-64rlk-3469265-worker-0
docker_host: unix:///tmp/rl/run/docker.sock
docker_root_dir: /tmp/rl/data
rootless: true
worker_network_policy: offline_or_internal_only
mutation_policy: no docker load in this lane
```

## Worker Precheck

Ran on `worker-j9jjd`; no `swe_dev` host was used.

```bash
top=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
tar=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
test -d "$top"
test -f "$tar"
DOCKER_HOST=unix:///tmp/rl/run/docker.sock docker image inspect tb2-offline/fix-git:20260425
```

Observed:

```text
host=zwj2-64rlk-3469265-worker-0
repo_exists=yes
repo_git=no
loader_exists=no
checker_exists=no
tar_exists=yes
-rw------- 1 root root 332M Jun  3 02:24 /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
tag_present=no
```

The top-level shared asset directory was not the repo checkout. The actual shared checkout with the loader was:

```text
/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo
```

## Loader Check

Copied only `manifests/offline_images.tb21_fix_git.yaml` into the worker shared checkout, then ran check mode only:

```bash
DOCKER_HOST=unix:///tmp/rl/run/docker.sock scripts/load_offline_images.sh \
  --manifest manifests/offline_images.tb21_fix_git.yaml \
  --asset-root /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench \
  --check \
  --json
```

Exact output summary:

```json
{
  "asset_root": "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench",
  "counts": {
    "errors": 0,
    "loaded": 0,
    "missing": 1,
    "present": 0,
    "skipped": 0,
    "tar_missing": 0
  },
  "docker_host": "unix:///tmp/rl/run/docker.sock",
  "entries": [
    {
      "bench": "terminal-bench-2.1",
      "expected_tags": [
        "tb2-offline/fix-git:20260425"
      ],
      "id": "terminal_bench_2_1_fix_git_smoke",
      "loaded_tars": [],
      "missing_tags": [
        "tb2-offline/fix-git:20260425"
      ],
      "status": "missing",
      "tar_paths": [
        "/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar"
      ],
      "unresolved_sources": []
    }
  ],
  "manifest": "manifests/offline_images.tb21_fix_git.yaml",
  "mode": "check"
}
CHECK_RC=1
```

Interpretation:

- The loader checked exactly one entry.
- The missing tag is the exact requested tag: `tb2-offline/fix-git:20260425`.
- The tar is resolved and present: `tar_missing=0`.
- There are no placeholder rows such as `tb2-offline/<task>:20260425`.
- No image was loaded: `loaded=0`, and no `--load` command was run.

## Local Verification

Manifest parser assertion:

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path
root = Path.cwd()
module_path = root / 'scripts' / 'check_offline_images_manifest.py'
spec = importlib.util.spec_from_file_location('checker', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
manifest = root / 'manifests' / 'offline_images.tb21_fix_git.yaml'
config = module.load_yaml(manifest)
entries = module.manifest_entries(config)
assert len(entries) == 1, entries
entry = entries[0]
assert entry['id'] == 'terminal_bench_2_1_fix_git_smoke', entry
assert entry['expected_tags'] == ['tb2-offline/fix-git:20260425'], entry
assert entry['source_paths'] == ['/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar'], entry
print('manifest_parse=ok')
print('entry_count=1')
print('expected_tag=tb2-offline/fix-git:20260425')
print('source_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar')
PY
```

Output:

```text
manifest_parse=ok
entry_count=1
expected_tag=tb2-offline/fix-git:20260425
source_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/terminalbench2.1/prebuilt-images/20260425/fix-git.tar
```

Loader unit regression:

```bash
python3 -m unittest scripts/test_offline_images_manifest.py
```

Output:

```text
..
----------------------------------------------------------------------
Ran 2 tests in 1.262s

OK
```

Whitespace check:

```bash
git diff --check -- manifests/offline_images.tb21_fix_git.yaml reports/offline_image_fix_git_manifest_20260625.md
```

Output: exit code 0, no output.

## Remaining Blocker

The image is still not loaded in worker rootless Docker. That is intentionally left to the Terminal-Bench image-debug lane; this manifest lane only produced and validated the exact one-task check manifest.
