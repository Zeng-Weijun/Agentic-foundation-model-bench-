# Bench Image Manifests

These manifests are the bench-local P0 Harbor/OCI contract used before a worker
starts a Docker-based benchmark.

The runner order is:

1. Verify worker rootless Docker and registry CA state.
2. Inspect the exact local tag or digest in the worker Docker cache.
3. Pull a digest-pinned image from `100.97.118.137:8555` only when the manifest
   uses that internal registry and the runner was explicitly asked to pull.
4. If pull is unavailable, verify the fallback tar checksum and load it.
5. Run the configured `docker run --rm --network none` smoke before marking the
   image ready.

Current worker-j9jjd note: the shell can reach the registry and cached digest
smokes pass, but the active rootless Docker daemon has shown `network is
unreachable` for fresh registry pulls. Treat cached image readiness and registry
pull readiness as separate states until the daemon is restarted under the synced
rootless guard.

## Generated Cache Manifests

Two generated audit manifests currently materialize swe_dev cache state with image identity fields:

- `terminal_bench_2_1_swe_dev_cache.yaml`: 89 `tb2-offline/*:20260425` rows from swe_dev Docker cache. It records full source image IDs and marks which rows have shared tar fallback coverage under `terminalbench2.1/prebuilt-images/20260425`.
- `swebench_verified_django10097.yaml`: two required rows for the SWE-bench `django__django-10097` promotion probe: the official eval base and the exact `swerex-prebuilt` wrapper. This manifest is expected to pass on swe_dev and fail with `identity_mismatch` on the current worker until the official base is staged correctly.

Generated cache manifests are audit/promotion inputs. Do not treat them as P0-ready until every required row either has a digest-pinned registry ref or a verified fallback tar sha256.
