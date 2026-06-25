# Manifests

This directory will hold lightweight, reviewable metadata for datasets, harnesses, models, and run artifacts.

Do not store large datasets, model weights, Docker images, or raw benchmark traces in GitHub. Store pointers, versions, hashes, and smoke status here; keep heavy artifacts on shared storage.

Files:

- `datasets.example.yaml` - example dataset manifest.
- `harnesses.example.yaml` - example harness/runtime manifest.
- `models.example.yaml` - example model/serving manifest.
- `suite.example.yaml` - dry-run-first suite config for the one-key launcher draft.
- `runs.schema.json` - draft schema for normalized run manifests.

`suite.example.yaml` is intentionally secret-free. Model profiles reference environment variable names such as `OPENAI_API_KEY` and `SGLANG_OPENAI_BASE_URL`; they do not store API key values.
