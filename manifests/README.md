# Manifests

This directory will hold lightweight, reviewable metadata for datasets, harnesses, models, and run artifacts.

Do not store large datasets, model weights, Docker images, or raw benchmark traces in GitHub. Store pointers, versions, hashes, and smoke status here; keep heavy artifacts on shared storage.

Files:

- `datasets.example.yaml` - example dataset manifest.
- `harnesses.example.yaml` - example harness/runtime manifest.
- `models.example.yaml` - example model/serving manifest.
- `runs.schema.json` - draft schema for normalized run manifests.
