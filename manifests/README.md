# Manifests

This directory will hold lightweight, reviewable metadata for datasets, harnesses, models, and run artifacts.

Do not store large datasets, model weights, Docker images, or raw benchmark traces in GitHub. Store pointers, versions, hashes, and smoke status here; keep heavy artifacts on shared storage.

Files:

- `bench_registry.yaml` - P0 Harbor/OCI registry contract and image-manifest index.
- `datasets.example.yaml` - example dataset manifest.
- `harnesses.example.yaml` - example harness/runtime manifest.
- `models.example.yaml` - example model/serving manifest.
- `suite.example.yaml` - dry-run-first suite config for the one-key launcher draft.
- `runs.schema.json` - draft schema for normalized run manifests.
- `images/*.yaml` - per-bench Docker/OCI image readiness manifests.

`suite.example.yaml` is intentionally secret-free. Model profiles reference environment variable names such as `OPENAI_API_KEY` and `SGLANG_OPENAI_BASE_URL`; they do not store API key values.

Registry/image manifests are lightweight pointers only. Docker tars, datasets,
and traces stay on shared storage under
`/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`.
