# Agentic SWE / Tool Bench Landscape

Date: 2026-06-25

Status: working draft. This file is meant to be expanded with more live traces and run artifacts, not treated as the final paper text.

## Scope

This note organizes the benchmark family we are discussing for agentic software engineering and tool-use evaluation:

- SWE-bench Verified and SWE-bench Multilingual
- Monthly-SWEBench
- Terminal-Bench 2.1
- Terminal-X, including DeepTerminalBench, EvoCode-Bench, and RoadmapBench
- MCP-Atlas
- Tool Decathlon / Toolathlon
- tau3-bench / tau3-Banking
- ProgramBench
- RepoZero
- NL2Repo
- DeepSWE

The key objective is to separate four things that are easy to mix together:

1. What the task actually asks the agent to do.
2. What harness/verifier decides success.
3. What strong closed-source models score under the published benchmark setup.
4. What our local Qwen3-Coder-30B-A3B-Instruct runs show under our own SGLang + scaffold setup.

## Important Naming / Score Caveats

- "Qwen3-Coder-Next" in the public technical report is an 80A3 model. Our local run is `qwen3-coder-30b-a3b-instruct`, with 30.5B total parameters and 3.3B activated parameters. Do not write these as the same model.
- Our local Qwen run that has a complete SWE-bench Verified score is Qwen3-Coder-30B-A3B-Instruct + SGLang + Qwen Code. The score is `245/500 = 49.0%`.
- Public benchmark leaderboards move. The scores below are source-backed snapshot numbers from pages checked on 2026-06-25, but they should be refreshed before a camera-ready claim.
- For benchmark rows where we do not have a local Qwen3-30B-A3B full run, this note says "no local full score yet" rather than extrapolating from another model or scaffold.

## Local Evidence We Can Cite

### Local Qwen3-Coder-30B-A3B-Instruct setup

Source: `configs/code_models/qwen3_coder_30b_a3b_instruct_qwen_code.yaml`

- Model name: `qwen3-coder-30b-a3b-instruct`
- Model path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct`
- Serving endpoint: `http://100.103.11.77:8503/v1`
- Serving host: `worker_rkn9p`
- Serving runtime: SGLang `0.5.10.post1`
- Context profile: native 262k context, max output 64k
- Launch shape: `python -m sglang.launch_server ... --tp-size 2 --context-length 262144 --tool-call-parser qwen3_coder`
- Agent scaffold: Qwen Code `0.15.6`
- Headless command shape: `qwen --channel CI -p '<prompt>' --yolo --auth-type openai --openai-base-url ... --model qwen3-coder-30b-a3b-instruct --output-format stream-json`
- SWE-bench subset: `paper_n500`
- Prior max session turns in this config: `80`

### Local Qwen SWE-bench Verified result

Source: `reports/qwen3_coder_swebench_qwen_code_retry_cases_20260529.md`

- Model: `qwen3-coder-30b-a3b-instruct`
- Serving: SGLang on `worker_rkn9p`, `http://100.103.11.77:8503/v1`
- Agent: Qwen Code `0.15.6`
- Raw full run: `245/500 = 49.0%`
- Summary: `completed=486`, `errors=1`, `empty_patch=14`
- Corrected score after selective retry: `245/500 = 49.0%`
- Retry contribution: `0` newly resolved cases

### Agent matrix

Source: `configs/code_models/swebench_agents/qwen3_coder_30b_a3b_instruct_agent_matrix.yaml`

- `qwen_code`: full run completed, raw/corrected `245/500 = 49.0%`
- `swe_agent`: configured, prompt policy is SWE-agent template config, no wrapper prompt injection
- `openhands`: configured, OpenHands official SWE-bench selector `mode=swe -> swe_default.j2`
- `mini_swe_agent`: installed/help verified, prompt policy official `swebench.yaml`; overlay changes model and budget
- Artifact contract:
  - Qwen Code traces: `qwen_native_outputs/<run_name>/instances/<instance_id>/`
  - SWE-agent traces: `sweagent_output/`
  - OpenHands traces: `openhands_output/`
  - mini-swe-agent traces: `mini_swe_agent_outputs/<instance_id>/`

## One-Page Benchmark Matrix

| Benchmark | Task shape | Harness / verifier | Strong closed-source score snapshot | Qwen / local status |
|---|---|---|---|---|
| SWE-bench Verified | Real GitHub issue to patch in existing repo | Dockerized repo eval, `% Resolved`; Verified has 500 human-filtered instances | Vals snapshot: Claude Fable 5 95.0%, Claude Opus 4.8 88.6%, GPT 5.5 82.6% | Public Qwen3-Coder-Next 80A3: about 70.6-71.3 depending scaffold. Local Qwen3-Coder-30B-A3B + Qwen Code: `245/500 = 49.0%` |
| SWE-bench Multilingual | Repo-level bug fixing across multiple languages | Same broad issue-to-patch family; 300 tasks across 9 languages | Need refresh for exact frontier leaderboard before citing | Public Qwen3-Coder-Next 80A3 report: about 56.2-64.3 depending scaffold |
| Monthly-SWEBench | Monthly fresh PR-derived tasks, more feature/change coverage | Dual-phase fail-to-pass verification plus instruction-test alignment | Month-specific; do not use one static global score without naming the release | No local Qwen full score yet |
| Terminal-Bench 2.1 | Terminal tasks: build, train, configure, debug, security, data processing | Harbor / Docker terminal environment; pass@1, usually all pytests must pass | Snorkel snapshot: Codex CLI + GPT-5.5 83.4%, Claude Code + Claude 5 Fable 83.1%, Terminus 2 + Fable 80.4% | Public Qwen3-Coder-Next 80A3 on Terminal-Bench 2.0: 25.8-36.2 depending scaffold. No local 30B full score yet |
| Terminal-X | Terminal depth/evolution: DeepTerminalBench, EvoCode, RoadmapBench | Harbor Terminus-2 fixed harness, Docker terminal, file editing, code execution | Published blog gives per-task/model maps; cite exact table only after extracting target split | No local Qwen full score yet |
| MCP-Atlas | MCP tool-use tasks with noisy tool menus and cross-server orchestration | Real MCP servers in Docker, controlled tool exposure, claim-level LLM judge, pass if coverage >= 0.75 | Scale snapshot: top pass rate 83.6%; GPT-5.5 75.3%, GPT-5.4 70.6%, GPT-5.4-mini 56.7 | No local Qwen full score yet |
| Tool Decathlon / Toolathlon | Long-horizon multi-application tool execution | 32 apps, 604 tools, 108 tasks, dedicated eval scripts | Paper abstract: best Claude-4.5-Sonnet 38.6%; top open-weight DeepSeek-V3.2-Exp 20.1% | No local Qwen full score yet |
| tau3-bench / tau3-Banking | Customer-support tasks requiring policy retrieval plus backend tool calls | Simulated user-agent interaction; success by backend database state, not conversation quality | Artificial Analysis snapshot: GPT-5.5 xhigh 31.3%, Sonnet 4.6 adaptive max 30.5%, GPT-5.4 xhigh 30.3%; abstract says high-budget frontier around 25.5 pass^1 | Local tau3 Harbor adapter inventory exists, but no Qwen3-30B tau3 full score in inspected evidence |
| ProgramBench | Rebuild a program from compiled binary plus docs | Agent gets executable/docs, no source/tests; hidden behavioral tests check reconstructed program | Paper conclusion: no model fully resolves any task; partial progress only | No local Qwen full score yet |
| RepoZero | Generate a repository from scratch by reimplementing APIs | Black-box output equivalence, cross-language constraints, sandboxed eval | Paper: strongest agents limited, about 30%-55%; conclusion says advanced scaffolds around 40% | Local README has RepoZero Py2JS wrapper and historical smoke support; no Qwen3-30B full score in inspected evidence |
| NL2Repo | Generate a complete installable Python repo from NL requirements and empty workspace | Upstream pytest suites; long-horizon repo generation | Paper: Claude Sonnet 4.5 about 39.6 pass / 40.2 avg score; all agents struggle | No local Qwen3-30B full score; paper failure modes are relevant to Qwen attribution |
| DeepSWE | Original long-horizon engineering tasks across real repos | mini-swe-agent consistency harness, behavior verifiers | 2026-06-24 leaderboard: Claude Fable 5 70%, GPT-5.5 67%, Claude Opus 4.8 59%, GPT-5.4 52% | Local GPT-5.4-mini + mini-swe-agent run is incomplete/invalid as a full score: 11 completed trials, all reward 0, mostly timeouts |

## Detailed Benchmark Notes

### SWE-bench Verified / Multilingual

Task shape:

- The agent receives a real issue from a real repository.
- The repository is checked out at the base commit.
- The agent must inspect files, edit code, optionally run tests, and produce a patch.
- The score is not based on natural-language explanation. The patch must pass the benchmark harness.

Harness:

- SWE-bench Verified is a 500-instance human-filtered subset.
- SWE-bench Multilingual is 300 tasks across 9 programming languages.
- The entry metric is `% Resolved`.
- Source: https://www.swebench.com/

Published score anchors:

- Vals SWE-bench Verified snapshot, updated 2026-06-17:
  - Claude Fable 5: 95.00%
  - Claude Opus 4.8: 88.60%
  - GPT 5.5: 82.60%
  - Claude Opus 4.7: 82.00%
  - Gemini 3.5 Flash: 78.80%
- Source: https://www.vals.ai/benchmarks/swebench

Qwen anchors:

- Public Qwen3-Coder-Next technical report:
  - SWE-bench Verified, Qwen3-Coder-Next 80A3:
    - SWE-Agent: 70.6
    - MiniSWE-Agent: 71.1
    - OpenHands: 71.3
  - SWE-bench Multilingual, Qwen3-Coder-Next 80A3:
    - SWE-Agent: 62.8
    - MiniSWE-Agent: 56.2
    - OpenHands: 64.3
- Source: https://arxiv.org/html/2603.00729v1

Local Qwen3-30B-A3B anchor:

- Qwen3-Coder-30B-A3B-Instruct + SGLang + Qwen Code:
  - `245/500 = 49.0%`
  - `completed=486`
  - `errors=1`
  - `empty_patch=14`
  - selective retry added `0` newly resolved cases

Concrete local trace example:

- Instance: `astropy__astropy-14365`
- Run root inspected on `swe_dev`:
  - `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/aci_evolve/experiments/qwen_native_verified_paper_n500_20260503_030617/instances/astropy__astropy-14365`
- Initial prompt shape:
  - "You are using Qwen Code to solve SWE-bench Verified instance astropy__astropy-14365."
  - Repo already checked out at `/testbed`.
  - Inspect code, make minimal source changes, run focused checks when useful.
  - Do not modify benchmark tests.
  - Remove temporary reproduction/debug files.
  - Stop when complete.
- Issue:
  - `ascii.qdp` assumes QDP commands are uppercase.
  - The expected case is lowercase `read serr 1 2`.
- Qwen Code system init:
  - cwd: `/testbed`
  - model: `qwen3-coder-30b-a3b-instruct`
  - permission: `yolo`
  - Qwen Code version: `0.15.6`
  - tools include `glob`, `read_file`, `grep_search`, `edit`, `write_file`, `run_shell_command`, `todo_write`, `task_stop`, `web_fetch`
- Agent behavior:
  - It found `astropy/io/ascii/qdp.py`.
  - It changed regex handling and compiled with `re.IGNORECASE`.
  - It produced a 1435-byte patch.
  - It returned code 0.
  - The verifier still marked `completed=false`, `resolved=false`.
- Failure observation:
  - The agent ran a lowercase `TERR` check and saw `IndexError`.
  - It then reasoned that the `TERR` failure was a separate issue and treated the main issue as fixed.
  - This is a useful concrete example of local self-verification bias: the agent can locate the right file and implement a plausible patch, but it fails to bind observed failures back to the benchmark objective.

Low-score attribution for SWE-bench:

- Model/scaffold mismatch: public Qwen3-Coder-Next 80A3 numbers should not be used as our 30B-A3B result.
- Patch correctness, not syntax, is the main bottleneck. The model can often find the right file but still produce an unresolved patch.
- Empty patch and timeout/session interaction are real score losses. Local full run had 14 empty patches.
- Verification discipline is weak. The trace above shows the model dismissing a test failure after observing it.
- Scaffold and prompt policy matter. Qwen Code, SWE-agent, OpenHands, and mini-swe-agent are not equivalent.

### Monthly-SWEBench

Task shape:

- Monthly fresh tasks derived from newly merged PRs.
- More emphasis on real change requests, feature additions, and interface extension than only historical bug repair.
- Intended to reduce static benchmark overfitting and memorization.

Harness / curation:

- Raw PRs are filtered through merged-to-default, test-change, complexity, quality-gate, fail-to-pass, and alignment stages.
- About 100 verified tasks are released each month.
- Tasks come from fresh PRs and fresh repositories not part of previous releases.
- The page describes direct instruction-test alignment review and trajectory review to distinguish real difficulty from ambiguous/under-specified instructions.
- Source: https://unipat.ai/benchmarks/MonthlySWEBench

How to describe it:

- "Monthly-SWEBench is a living SWE benchmark: instead of a fixed historical 500-task set, it continually releases fresh verified PR-derived tasks."
- "For our paper, it is useful as an anti-contamination and feature-change benchmark."

Score status:

- Do not cite one global score unless we select a specific monthly release.
- No local Qwen3-30B-A3B full result inspected yet.

Trace fields to collect:

- Month/release id.
- PR source and repo.
- Initial task instruction.
- Agent scaffold and system prompt.
- Failing tests before patch and passing tests after patch.
- Whether the task is bug fix, feature addition, interface extension, or refactor.
- Any instruction-test alignment notes.

### Terminal-Bench 2.1

Task shape:

- The agent works inside a terminal environment.
- Tasks include building Linux/QEMU artifacts, configuring services, cracking an archive password, generating TLS certs, resharding data, or training a model under size/accuracy constraints.
- The user-facing instruction is operational, not just "fix this issue".

Harness:

- Terminal-Bench is a Harbor-native benchmark family for terminal agents.
- Terminal-Bench 2.1 is a revision of 2.0 that fixes 28 of 89 tasks and adds continuous validation.
- Terminal-Bench 2.1 changes include external dependency fixes, resource-budget fixes, and instruction/test mismatch fixes.
- Source: https://www.tbench.ai/
- Source: https://snorkel.ai/leaderboard/terminal-bench-2-1/

Published score anchors:

- Snorkel Terminal-Bench 2.1 snapshot:
  - Codex CLI + GPT-5.5: 83.4% +/- 2.2
  - Claude Code + Claude 5 Fable: 83.1% +/- 2.0
  - Terminus 2 + Claude 5 Fable: 80.4% +/- 2.3
  - Claude Code + Claude Opus 4.8: 78.9% +/- 2.5
  - Terminus 2 + GPT-5.5: 78.2% +/- 2.4
- Vals methodology page says models are benchmarked with the Terminus 2 harness, results are pass@1, and a task gets credit only if all provided pytests pass.
- Source: https://www.vals.ai/benchmarks/terminal-bench-2-1

Qwen anchors:

- Public Qwen3-Coder-Next technical report is for Terminal-Bench 2.0, not 2.1:
  - Qwen3-Coder-Next 80A3:
    - Terminus2-xml: 34.2
    - Terminus2-json: 36.2
    - ClaudeCode: 30.9
    - QwenCode: 25.8
- Source: https://arxiv.org/html/2603.00729v1

Local status:

- The local Qwen suite config includes `terminal_bench_2_0` under both smoke and full benchmark lists.
- No local Qwen3-Coder-30B-A3B full Terminal-Bench score was found in the inspected evidence.

Trace fields to collect:

- Exact task id, category, and instruction.
- Container image and resource budget.
- Agent scaffold: Terminus 2, Codex CLI, Claude Code, Qwen Code, etc.
- System prompt and terminal command policy.
- Command trace, file edits, generated artifacts.
- Test command and pytest/verifier output.
- Whether failure is environment/setup, command planning, dependency resolution, runtime timeout, or wrong final artifact.

Likely Qwen failure modes:

- Long command chains and terminal state tracking.
- Recovering from build/test errors.
- Resource/time budget management.
- Tool-call format and JSON/schema fragility under interactive harnesses.
- Premature success declarations after a partial local check.

### Terminal-X

Task shape:

- Terminal-X is not one flat benchmark. It introduces a family:
  - DeepTerminalBench: deep single terminal tasks.
  - EvoCode-Bench: multi-turn code evolution tasks.
  - RoadmapBench: roadmap/version upgrade tasks.
- Examples from the blog include:
  - Rust scheduler optimization with cluster state JSON and exact output requirements.
  - Go deterministic data pipeline.
  - PyG 2.4 to 2.5 style API/behavior upgrade.
  - Fiber 2.49 to 2.50 style Go middleware/context upgrade.

Harness:

- The blog says evaluation uses Harbor Terminus-2, with terminal access, file editing, and code execution inside Docker.
- It also emphasizes fixed high-performing scaffolding to reduce scaffold as a confounder.
- Source: https://unipat.ai/blog/TerminalX

Dataset sizes from the blog:

- DeepTerminalBench: 50 tasks.
- EvoCode-Bench: 26 multi-turn tasks.
- RoadmapBench: 115 tasks.

How to use it in our narrative:

- Terminal-X is the right benchmark family when we want to argue about depth, iteration, and evolution, rather than one-shot issue repair.
- It is a better proxy than SWE-bench for "can the agent keep moving in a terminal over many steps, under realistic feedback".

Local status:

- No local Qwen3-30B-A3B full Terminal-X score inspected yet.

Trace fields to collect:

- Which sub-benchmark: DeepTerminalBench, EvoCode-Bench, or RoadmapBench.
- Phase/round structure.
- Initial instruction and hidden verifier.
- Agent command/file trace.
- Whether the task requires algorithmic optimization, API surface reconstruction, compatibility preservation, or multi-round update.
- Pass/fail per phase if weighted scoring is used.

### MCP-Atlas

Task shape:

- The model receives a task that cannot be solved from memory alone.
- It must discover the right tools from a noisy MCP tool menu, call them with correct parameters and types, recover from errors, and synthesize outputs into a final answer.
- Example task shape: retrieve a paper abstract through one tool/server, query an internal advertising database through another, calculate or compare results, then answer with all required claims.

Harness:

- 1000 human-authored tasks: 500 public, 500 private.
- 36 MCP servers and 220 tools.
- Each task typically needs 3-6 tool calls.
- Each task exposes 10-25 tools, with 3-7 required tools and 5-10 distractors.
- Tasks run against real MCP servers in Docker, with trace logging.
- Scoring decomposes the ground truth into claims; pass if coverage is at least 0.75.
- Source: https://labs.scale.com/leaderboard/mcp_atlas

Published score anchors:

- Snapshot from the Scale page:
  - Gemini 3.5 Flash high: 83.60 +/- 2.30
  - Claude Fable 5: 83.30 +/- 2.25
  - Claude Opus 4.8 max: 82.20 +/- 2.40
  - GPT-5.5 xhigh: 75.30 +/- 2.70
  - GPT-5.4 xhigh: 70.60 +/- 2.80
  - GPT-5.4-mini xhigh: 56.70

Failure analysis from source:

- Tool usage failures dominate: wrong tool selection, incorrect parameters, schema violations, sequencing mistakes.
- Task understanding failures include premature stopping and missing subgoals.
- Response quality failures include wrong final synthesis after otherwise useful intermediate tool calls.

Local status:

- No local Qwen3-30B-A3B MCP-Atlas score inspected yet.

Trace fields to collect:

- Tool list exposed to model, including distractors.
- User prompt.
- System prompt / tool-use policy.
- Full MCP call sequence: tool name, arguments, result, error.
- Final answer and claim-level judge output.
- Whether failure was no tool call, wrong tool, wrong parameter, missed branch, or final synthesis.

### Tool Decathlon / Toolathlon

Task shape:

- Long-horizon task execution across many real software applications.
- Examples in the abstract: coordinating email/calendar/files, monitoring a BigQuery production database, generating anomaly reports following an SOP.
- Applications include everyday tools such as Google Calendar and Notion, plus professional tools such as WooCommerce, Kubernetes, and BigQuery.

Harness:

- 32 software applications.
- 604 tools.
- 108 manually sourced or crafted tasks.
- Around 20 turns on average.
- Dedicated evaluation scripts strictly verify task success.
- Source: https://openreview.net/forum?id=z53s5p0qhf

Published score anchors:

- Best model in the abstract: Claude-4.5-Sonnet at 38.6% success rate.
- Top open-weight model in the abstract: DeepSeek-V3.2-Exp at 20.1%.

How to use it in our narrative:

- This is a useful counterweight to SWE-bench saturation claims.
- It shows that long-horizon multi-application tool use remains low-score even for frontier models.

Local status:

- No local Qwen3-30B-A3B full score inspected yet.

Trace fields to collect:

- Applications and tools exposed.
- Initial environment state.
- SOP or workflow constraints.
- Tool-call sequence and intermediate state changes.
- Final state verification script output.
- Distinguish tool discovery errors from state-management errors.

### tau3-bench / tau3-Banking

Task shape:

- Customer-service agent tasks where the model must retrieve and apply policy, interact with a simulated user, and call backend tools to change account/order/state.
- tau3-Banking examples:
  - Recommend the best cash-back card for Sarah Bosch, surface Rho-Bank+ benefit, and have the user invoke the correct application tool.
  - Investigate Amara Okonkwo's cash-back dispute, file four disputes, unlock a transaction-rewards update tool, and correct each reward total.
  - Open Yumi Tanaka's business checking and savings accounts while respecting active/expired promotions.

Harness:

- The tau3-bench source lineage uses the Sierra upstream repository for simulated customer-service agents.
- Domains specify policy, tools, tasks, and optionally user tools.
- Available domains include airline, retail, telecom, and banking_knowledge.
- tau3-Banking / tau-Knowledge requires navigating about 700 policy documents, about 195K tokens, 21 product categories, and 97 tasks.
- Outcomes are graded by backend database state, not by conversational quality.
- Source: https://github.com/sierra-research/tau2-bench
- Source: https://artificialanalysis.ai/evaluations/tau3-banking

Published score anchors:

- Artificial Analysis snapshot:
  - GPT-5.5 xhigh: 31.3%
  - Claude Sonnet 4.6 adaptive max effort: 30.5%
  - GPT-5.4 xhigh: 30.3%
- The abstract says even frontier models with high reasoning budgets achieve only about 25.5% pass^1, and failures come from retrieval and policy reasoning.

Local status:

- The bench README now treats tau3-bench as the tau-family target; legacy tau-family smoke evidence is de-scoped from the active bench list.
- No local Qwen3-30B-A3B tau3 full score inspected yet.

Trace fields to collect:

- Domain, task id, user simulator model, agent model.
- Full conversation transcript.
- Policy/knowledge retrieval trace.
- Agent tool calls and user tool calls.
- Backend DB before/after state.
- Reward basis and action correctness.
- Whether failure is retrieval, policy interpretation, user-coordination, or tool-state update.

### ProgramBench

Task shape:

- The agent gets a compiled program and documentation.
- Source code and tests are stripped away.
- The agent must write a new source code implementation plus compile script that reproduces the original behavior.
- It can choose language, build system, architecture, abstractions, and algorithms.

Harness:

- The benchmark generates hidden behavioral tests by probing the original program with varied inputs and turning observed behavior into assertions.
- Candidate reconstructions are implementation-agnostic: they pass if behavior matches, even if the internals differ.
- Source: https://arxiv.org/html/2605.03546v1

Published score anchor:

- The paper conclusion says existing models struggle substantially and none fully resolve any task.

How to use it in our narrative:

- ProgramBench is an extreme clean-room software construction benchmark.
- It is not comparable to SWE-bench Verified by raw percent because the task is fundamentally from-scratch reconstruction rather than local patching.

Local status:

- No local Qwen3-30B-A3B full score inspected yet.

Trace fields to collect:

- Binary/program name and documentation.
- Allowed probing commands.
- Agent architecture decisions.
- Generated source tree and compile script.
- Hidden behavioral test summary.
- Partial-progress metrics, not just full resolved.

### RepoZero

Task shape:

- Generate an entire repository from scratch.
- The agent receives API specifications and must reimplement behavior equivalent to the original repository.
- The design uses repository reproduction rather than open-ended app generation.

Harness:

- Fully automated, execution-based verification.
- Strict black-box validation via output equivalence.
- Cross-language constraints and sandboxed evaluation mitigate leakage and shortcut solutions.
- Paper describes two primary subsets, C2Rust and Py2JS, encompassing 600 test files.
- Source: https://arxiv.org/html/2605.07122v1

Published score anchors:

- The abstract says strongest LLM agents achieve limited pass rates, about 30%-55%.
- The conclusion says advanced scaffolds achieve only moderate success, approximately 40%, and self-verification is important.

Local status:

- Local README has a RepoZero Py2JS wrapper:
  - smoke example: `REPOZERO_MODE=smoke REPOZERO_CASES="base58/test1.py bencoder/test1.py bech32/test1.py fractions/test1.py" ./run_repozero_py2js.sh`
  - full example: `REPOZERO_MODE=full REPOZERO_WORKERS=4 REPOZERO_CODEX_ATTEMPTS=3 ./run_repozero_py2js.sh`
- README notes the remote runner default:
  - `repozero_eval/RepoZero/tools_repozero_codex_full.py`
- No local Qwen3-30B-A3B full score inspected yet.

Trace fields to collect:

- Subset: C2Rust, Py2JS, or other.
- API/spec prompt.
- Generated repository tree.
- Agent-generated tests, if any.
- Official black-box output-equivalence tests.
- Whether failures are API surface mismatch, language/runtime errors, missing edge cases, or architectural incompleteness.

### NL2Repo

Task shape:

- The agent starts with a single natural-language requirements document and an empty workspace.
- It must design architecture, manage dependencies, implement multi-module logic, package the project, and produce a fully installable Python library.

Harness:

- 104 tasks across 9 categories of Python libraries.
- Strictly verifiable with upstream pytest suites.
- Source: https://arxiv.org/html/2512.12730v2

Published score anchors:

- The paper reports that long-horizon repository generation remains hard.
- Claude Sonnet 4.5:
  - document-only overall average score about 40.2 in Table 8;
  - conclusion says about 39.6% pass rate.
- The conclusion identifies two critical failure modes:
  - overconfidence of thinking models causing early termination;
  - collaborative bias of models like GPT-5 that fail to proceed autonomously.

How to use it in our narrative:

- NL2Repo is a direct benchmark for "from a spec, build a package" rather than "patch an existing bug."
- It is important for long-horizon planning and cross-file consistency claims.

Local status:

- No local Qwen3-30B-A3B full score inspected yet.

Trace fields to collect:

- Requirements document.
- Generated architecture plan.
- Dependency and packaging decisions.
- Tool/command trace over hundreds of steps.
- Final repository tree.
- Upstream pytest result.
- Non-finish vs early-stop classification.

### DeepSWE

Task shape:

- Original long-horizon engineering tasks across real repositories.
- Prompts are behavior-focused and require repository exploration, architecture understanding, implementation, and verification.

Harness:

- DeepSWE leaderboard says all models run on mini-swe-agent for consistency.
- 113 tasks.
- 91 repos.
- 5 languages.
- Verifiers are hand-written to test behavior rather than implementation details.
- Source: https://deepswe.datacurve.ai/

Published score anchors:

- 2026-06-24 v1.1 leaderboard snapshot:
  - Claude Fable 5 max: 70% +/- 4
  - GPT-5.5 xhigh: 67% +/- 6
  - Claude Opus 4.8 max: 59% +/- 2
  - GPT-5.4 xhigh: 52% +/- 2
  - GLM-5.2 max: 44% +/- 2
  - Gemini 3.5 Flash medium: 37% +/- 2
  - Kimi K2.7 Code: 31% +/- 1
  - Claude Sonnet 4.6 high: 30% +/- 4
  - Gemini 3.1 Pro high: 12% +/- 2

Local GPT + mini-swe-agent trace:

- Run root:
  - `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/runs/deepswe/gpt-5.4-mini_official-mswea-xh_20260615_141320_official_mswea_xh_full`
- Job config:
  - agent: `mini-swe-agent`
  - model: `openai/gpt-5.4-mini`
  - reasoning effort: `xhigh`
  - n concurrent trials: `10`
  - dataset path: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe/tasks`
- This is not a valid full benchmark score:
  - `n_completed_trials=11`
  - `n_errored_trials=11`
  - `n_running_trials=10`
  - `n_pending_trials=92`
  - all 11 completed trial rewards were `0.0`
  - exceptions: 10 `AgentTimeoutError`, 1 `NonZeroAgentExitCodeError`
  - markers: `bad_gateway=9`, `context_window=1`, `response_incomplete=1`, `max_output_tokens=1`
  - cost at stop: about `$46.55`
- One inspected task:
  - `datacurve/clack-async-autocomplete-options`
  - agent: mini-swe-agent `2.4.1`
  - model: `gpt-5.4-mini`
  - result: reward `0.0`
  - exception: `AgentTimeoutError` after 5400 seconds
  - n agent steps: 35
  - peak context tokens: 89560
  - prompt asks to add async search-as-you-type support to Clack's AutocompletePrompt, including thenable detection, first-fetch reuse, AbortSignal handling, loading state, stale-result suppression, cache, stale-while-revalidate, debounce, retries, fallback options, loadingMinDuration, and minSearchLength behavior.
- mini-swe-agent system prompt / workflow shape:
  - system: "You are a helpful assistant that can interact with a computer."
  - instance template begins with "Please solve this issue: {{task}}"
  - workflow: analyze codebase, create reproduction script, edit code, verify fix, test edge cases, submit with `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
  - each response must include reasoning text and at least one bash tool call.

How to use it:

- Do not cite the local GPT-5.4-mini run as a model score.
- Do cite it as an example of the failure modes that long-horizon harnesses expose: timeout, gateway/relay instability, context pressure, huge token use, and failure to reach a clean submit.

Local Qwen status:

- No local Qwen3-30B-A3B DeepSWE full score inspected yet.

## Cross-Benchmark Failure Taxonomy

This taxonomy is useful for explaining why a model that looks decent on SWE-bench can collapse on terminal/tool/repo-generation benchmarks.

### 1. Patch-local correctness failure

Typical in SWE-bench:

- Agent locates the right file.
- Agent edits plausible lines.
- Local test or self-written reproduction appears to pass.
- Official verifier still fails.

Concrete local example:

- `astropy__astropy-14365`: Qwen Code saw a related `TERR` failure but dismissed it as separate, then produced an unresolved patch.

### 2. Empty patch / no submit

Typical in SWE-bench and mini-swe-agent style loops:

- Agent explores for many turns.
- Agent exits cleanly or times out.
- No tracked source diff is produced.
- Score is zero regardless of how much reasoning happened.

Concrete local evidence:

- Qwen full run had 14 empty patches.
- Selective retry produced zero newly resolved cases.

### 3. Terminal execution drift

Typical in Terminal-Bench / Terminal-X / DeepSWE:

- Agent loses track of cwd, environment, generated files, or installed dependencies.
- Build commands and tests become slow or flaky.
- Agent spends time on setup rather than the core task.
- Resource limits or timeouts dominate.

### 4. Tool discovery / schema failure

Typical in MCP-Atlas and Toolathlon:

- No tool called when tools are required.
- Correct tool but wrong parameter shape.
- Wrong tool sequence.
- Failure to recover from tool errors.
- Correct intermediate results but wrong final synthesis.

### 5. Policy retrieval / state transition failure

Typical in tau3:

- Agent retrieves the wrong policy document.
- Agent applies expired or irrelevant policy.
- Agent speaks plausibly but does not update backend state correctly.
- User-tool and agent-tool coordination is missed.

### 6. Repository-level planning failure

Typical in RepoZero, NL2Repo, ProgramBench:

- Agent creates a partial architecture that cannot support all required behavior.
- Cross-file interfaces drift.
- Packaging/dependency choices are inconsistent.
- Agent terminates early or waits for user guidance.
- Self-generated tests are too weak to expose missing behavior.

## Recommended Trace Contract For Our Runs

For every benchmark run we want to cite, collect the following fields into a small manifest next to the raw trace:

```yaml
bench:
  name:
  version_or_release:
  task_id:
  task_category:
  source_url_or_dataset_path:

model:
  public_name:
  exact_served_name:
  endpoint:
  provider_or_serving_runtime:
  temperature:
  max_context_tokens:
  max_output_tokens:
  reasoning_effort:

agent:
  scaffold:
  scaffold_version:
  system_prompt_path_or_hash:
  user_prompt_path_or_hash:
  tool_schema_path_or_hash:
  budget:
    wall_time_s:
    max_turns:
    max_steps:
    cost_limit:

harness:
  verifier_command:
  container_or_env:
  metric:
  pass_condition:

observations:
  final_status:
  score_or_reward:
  exception_type:
  patch_bytes:
  empty_patch:
  n_steps:
  input_tokens:
  output_tokens:
  cost_usd:
  failure_category:
  short_failure_note:

artifacts:
  raw_trace_path:
  prompt_path:
  patch_path:
  verifier_log_path:
  result_json_path:
```

## Recommended Paper Wording

The benchmark suite should be described as follows:

> We evaluate agentic coding and tool-use capability across benchmarks that require executable, environment-grounded success rather than isolated code generation. SWE-bench Verified and SWE-bench Multilingual test issue-to-patch repair in existing repositories; Monthly-SWEBench refreshes that setup with newly merged PRs and explicit instruction-test alignment review; Terminal-Bench 2.1 and Terminal-X move the agent into long-running terminal environments for build, configuration, optimization, and multi-round evolution tasks; MCP-Atlas, Tool Decathlon, and tau3-bench stress real tool discovery, multi-application workflows, and policy-grounded state changes; ProgramBench, RepoZero, NL2Repo, and DeepSWE extend the setting to clean-room reconstruction, from-scratch repository generation, and long-horizon engineering tasks. These benchmarks expose different failure modes: patch-local mistakes, empty submissions, terminal state drift, tool-schema errors, policy retrieval failures, and cross-file planning breakdowns. Strong closed-source models can exceed 80-90% on mature patch-style SWE-bench leaderboards, but the same model families often fall to 20-70% on terminal, tool, and long-horizon repository tasks, with some clean-room reconstruction settings remaining near unsolved.

For the Qwen result, keep the statement precise:

> Our local `Qwen3-Coder-30B-A3B-Instruct` run uses SGLang serving and Qwen Code as the agent scaffold. On SWE-bench Verified, the completed full run scores `245/500 = 49.0%`, with `486` completed instances, `1` error, and `14` empty patches. This should not be conflated with the public Qwen3-Coder-Next 80A3 technical-report result, which reports roughly 70-71% on SWE-bench Verified under SWE-agent, MiniSWE-Agent, and OpenHands. The local trace evidence suggests the main gap is not syntax-level code generation but verifier-grounded agency: the model can often locate the relevant file and produce a plausible patch, yet it may ignore contradictory test evidence, stop early, or fail to submit a valid diff.

## Immediate Follow-Up Work

1. For every benchmark row above, create one `runs/<bench>/<model>/<task>/trace_manifest.yaml` in the contract shape above.
2. Refresh current public leaderboard scores immediately before using them in a final paper/table.
3. Run or locate local Qwen3-Coder-30B-A3B full scores for:
   - Terminal-Bench 2.1 or 2.0, whichever is actually reproducible in our harness.
   - DeepSWE with mini-swe-agent, if compute and relay stability allow.
   - RepoZero Py2JS full, since the local wrapper already exists.
   - tau3-Banking only if the tau3 harness and API/user simulator setup are pinned.
4. Promote `astropy__astropy-14365` as the first detailed Qwen trace case study.
5. Add at least one closed-model successful trace for comparison, ideally GPT-5.5 or Claude Fable 5 on the same benchmark family, so the trace comparison is behavioral rather than only score-based.

## Source Links

- SWE-bench official leaderboard and definitions: https://www.swebench.com/
- Vals SWE-bench Verified leaderboard: https://www.vals.ai/benchmarks/swebench
- Qwen3-Coder-Next technical report: https://arxiv.org/html/2603.00729v1
- Monthly-SWEBench: https://unipat.ai/benchmarks/MonthlySWEBench
- Terminal-Bench site: https://www.tbench.ai/
- Terminal-Bench 2.1 Snorkel leaderboard: https://snorkel.ai/leaderboard/terminal-bench-2-1/
- Terminal-Bench 2.1 Vals methodology: https://www.vals.ai/benchmarks/terminal-bench-2-1
- Terminal-X blog: https://unipat.ai/blog/TerminalX
- MCP-Atlas leaderboard: https://labs.scale.com/leaderboard/mcp_atlas
- Tool Decathlon / Toolathlon OpenReview: https://openreview.net/forum?id=z53s5p0qhf
- tau3 upstream source repository: https://github.com/sierra-research/tau2-bench
- tau3-Banking Artificial Analysis: https://artificialanalysis.ai/evaluations/tau3-banking
- ProgramBench paper: https://arxiv.org/html/2605.03546v1
- RepoZero paper: https://arxiv.org/html/2605.07122v1
- NL2Repo paper: https://arxiv.org/html/2512.12730v2
- DeepSWE leaderboard: https://deepswe.datacurve.ai/
