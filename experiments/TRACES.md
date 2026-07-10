# Agent traces

The full agent trace of every instance in the completed runs is committed here.

| Run | Traces | Compressed | `sha256` of the tarball |
|---|---:|---:|---|
| `swev_qwen3_coder_qwencode_20260710` | 496 | 9.6 MB | `agent_traces.tar.gz.sha256` |
| `swev_instruct2507_qwencode_20260710` | 498 | 6.4 MB | `agent_traces.tar.gz.sha256` |

143 MB of `stream-json` uncompressed. Every tool call the agent made, every tool result it
received, every message, for all 994 instances.

## Verifying a trace against the score

`trace_index.tsv` hashes each trace **uncompressed**, per instance:

```bash
tar xzf agent_traces.tar.gz
shasum -a 256 ./django_u_django-11276/agent/qwen_attempt_1.stdout.jsonl
grep django_u_django-11276 trace_index.tsv
```

If a trace does not hash to its row, the score in this repository is not the score that run
produced. That is the whole point of committing them.

## Reading a trace

Tool activity is **not** in a top-level `tool_calls` field. `qwen-code` nests it inside
`message.content[]` blocks typed `tool_use` and `tool_result`:

```python
import json
for line in open("qwen_attempt_1.stdout.jsonl"):
    rec = json.loads(line)
    for block in (rec.get("message") or {}).get("content") or []:
        if block.get("type") in ("tool_use", "tool_result"):
            print(block["type"], block.get("name"))
```

Counting `tool_calls` at the top level returns zero for every trace here. An audit that did so
concluded the model had emitted no tool calls at all, and came within one step of striking a
correct baseline off the table. See `docs/EXPERIMENTS.md` §5.13.

## Secrets

Scanned by value, decompressed, across all 994 traces and 143 MB: `sk-*`, three-segment JWTs,
bearer tokens, HF tokens, and assigned `api_key=` literals. Zero findings.

A first pass reported two JWT hits. Both were `eyJ0ZXN0aW5nIjo0Mn0`, which is base64 for
`{"testing":42}` — a literal in a Flask test file. `eyJ` is not a token marker; it is base64 for
`{"`. The pattern was tightened to require the three dot-separated segments a JWT actually has.
A substring heuristic is not evidence, which is the same lesson §5.7 records about
`external_network_marker`.

## Not committed

`instances/` also holds eval logs, patches, and harness reports — 372 MB per run. Those are on
shared storage. The traces are what a reader needs to check that the agent did the work the score
claims it did.
