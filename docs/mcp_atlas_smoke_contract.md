# MCP-Atlas Local/Replay Smoke Contract - 2026-07-02

This contract intentionally defines a local/replay smoke, not a full500 claim. It exists to make MCP-Atlas executable enough to prove the runner, two model-call paths, MCP server allowlist, and strict parser without pretending the public-service server closure is solved.

## Smoke Scope

- Mode: `smoke` only.
- Task limit: <=5 tasks.
- Server profile: `local_replay_smoke`.
- Allowed local/replay servers: `calculator`, `filesystem`, `memory`, `git`, and `mcp-code-executor`.
- External service profile: `replay`; selected smoke tasks must be backed by replay fixtures or local deterministic tool behavior.
- Judge path: LLM judge goes through the approved relay, separate from the agent model path.
- Strict threshold: coverage >= 0.75 per task.

## Why This Is Not Full

This smoke is not a full500 claim. Full MCP-Atlas includes 500 tasks and 36 MCP servers. Many default or official servers imply public service or public API access and cannot run on no-internet workers without mirrors, replay fixtures, local service emulators, or a documented internal proxy contract.

Servers that block full enablement until mirrored or replayed include: `arxiv`, `ddg-search`, `fetch`, `pubmed`, `weather`, `wikipedia`, `open-library`, `osm-mcp-server`, `met-museum`, `exa`, `brave-search`, `alchemy`, `twelvedata`, `national-parks`, `google-maps`, `weather-data`, `airtable`, `google-workspace`, `notion`, `mongodb`, and `slack`.

## Required Smoke Artifacts

1. HF dataset snapshot: `ScaleAI/MCP-Atlas/MCP-Atlas.parquet` copied to shared storage with sha256 and row_count=500 proof.
2. Runtime image transport: `ghcr.io/scaleapi/mcp-atlas:1.2.5` linux/amd64 mirrored to P0 or stored as verified fallback tar+sha.
3. Completion/eval runner env: offline wheelhouse or runner image for `services/mcp_eval` and LiteLLM dependencies.
4. Replay fixture bundle: <=5 selected tasks whose tools are covered by the local/replay server profile.
5. Two relay paths: agent model and judge model must be configured separately and secrets must not be written to artifacts.
6. Parser proof: strict parser must count completion rows, judge rows, tool calls, coverage details, and model call counts.

## Parser Contract

The parser reports `coverage_pass_count`, `coverage_pass_rate`, `coverage_threshold`, `agent_model_call_count`, `judge_model_call_count`, `enabled_servers`, and `full_score_valid`. For smoke mode, `full_score_valid` is always false. A task passes the smoke parser only when completion and judge status are `ok`, tool calls exist, coverage details match GTFA claim count, and coverage >= 0.75.

## Full Enable Blocker List

Full enablement remains blocked until every full500 task has a server closure proof and the runner refuses unknown server profiles, missing image transport, missing replay/mirror data, missing agent relay, missing judge relay, and missing strict parser artifacts.
