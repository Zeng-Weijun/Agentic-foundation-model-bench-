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
