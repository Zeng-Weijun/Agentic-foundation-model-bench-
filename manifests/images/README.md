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

- `terminal_bench_2_1_swe_dev_cache.yaml`: 89 `tb2-offline/*:20260425` rows from swe_dev Docker cache. It records full source image IDs and marks which rows have shared tar fallback coverage under `terminalbench2.1/prebuilt-images/20260425`; `protein-assembly` additionally has a P0 digest ref and verified batch fallback tar.
- `swebench_verified_django10097.yaml`: two required rows for the SWE-bench `django__django-10097` promotion probe: the official eval base and the exact `swerex-prebuilt` wrapper. Both rows now have verified fallback tar checksums; worker-j9jjd `--load-fallback --run-smoke` loaded the official base over the prior alias mismatch and passed both image smokes.

Generated cache manifests are audit/promotion inputs. Do not treat them as P0-ready until every required row either has a digest-pinned registry ref or a verified fallback tar sha256.

Use the registry-level static gate when checking a worker-ready policy set:

```bash
python3 scripts/agentic_bench_images.py lint-registry \
  --registry manifests/bench_registry.yaml \
  --asset-root manifests \
  --policy audit_manifest_for_tb2_full_image_warmup \
  --policy required_for_swebench_django10097_promotion_smoke \
  --require-offline-transport \
  --verify-fallback-files
```

`--verify-fallback-files` upgrades the static gate from configured transport metadata to actual fallback tar presence/hash verification. As of the current audit, that TB2 + SWE promotion selection still fails closed only because 38 TB2 rows lack P0 digest refs or verified fallback checksums; the SWE django10097 rows now satisfy the fallback-tar transport gate. P0 digest refs are still preferred for scale, but no longer required for this narrow SWE django fallback smoke.
