# Traces

This directory should contain trace indexes and small public case studies only.

Raw traces can be large and may include model outputs, paths, logs, tool calls, or benchmark data that should remain on shared storage. For each cited raw trace, store a manifest pointer using:

```text
reports/trace_manifest_template.yaml
```

Required trace policy:

- include prompt/system prompt hashes or paths;
- include scaffold and tool schema information;
- include verifier output path;
- include failure category;
- distinguish infra failures from model/agent failures;
- avoid committing secrets, API keys, raw private benchmark data, or large logs.
