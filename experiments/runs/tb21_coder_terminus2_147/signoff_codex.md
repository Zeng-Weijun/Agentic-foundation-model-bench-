# Codex-family independent audit signoff — TB2.1 x Qwen3-Coder x terminus-2

**Auditor identity:** OpenAI Codex CLI 0.144.1, model `gpt-5.6-sol` (reasoning effort `ultra`
for the orchestrating pass, `xhigh` for the pinned interactive audit session it drove),
`--dangerously-bypass-approvals-and-sandbox`, invoked locally on the operator's Mac (session
ids `019f5b15-d8bb-7f91-9a61-024b36243992` orchestrator and `019f5b17…` pinned auditor;
recovered via `~/.codex/sessions/2026/07/13/rollout-*.jsonl` after a local tmux pane was lost
mid-session — see "Process note" below). This is a genuine OpenAI/Codex-family model, distinct
from the Claude family that authored both prior commits on this path (see Finding 5).

**Date:** 2026-07-13. **Claim under audit:** Terminal-Bench 2.1 (89 tasks) x
Qwen3-Coder-30B-A3B-Instruct x official `terminus-2` harness = **10/89 = 11.24%**, run_id
`tb21_coder_t2_c32_0711211754`, bundle `experiments/runs/tb21_coder_terminus2_147/`
(commits `39bf63a`, `ac80ef8`).

**Rule applied:** try to prove FAKE; if it cannot be disproven after real, hands-on
verification, mark REAL.

## Verdict: REAL

Could not falsify after independent, ground-truth, read-only verification directly on
KVM Pod B (`env-kvm-57740737-bzw56`) and a live probe of the serving endpoint. Every
check below was executed by this session's own shell tool calls (not copied from the
Claude-side pass), and several were run against files the Claude-side pass had not touched.

## Findings (each with the exact command output this session captured)

**1. Denominator = 89, not shrunk.** Independently recomputed, not read from any
pre-aggregated summary:
```
raw_task_subdirs=89
tsv_total_lines=90  tsv_data_rows=89
dataset_compose_files=89  compose_network_mode_none=89  compose_network_mode_non_none_or_missing=0
summary_resolved_len=10  summary_unresolved_len=79  summary_list_sum=89
per_task_results_files=89
```
All 89 `docker-compose.yaml` files in the exact dataset used
(`terminal-bench-2.1-yaml-full89-r7-final-20260703/`) carry `network_mode: none`; zero
exceptions.

**2. Resolved count recomputed directly from the 89 raw per-task `results.json` files**
(ground truth on shared disk, not the vendored bundle copy):
```
per_task_results_files=89
resolved_ids_from_raw_grep:
build-pmars, build-pov-ray, cancel-async-tasks, extract-elf, git-leak-recovery,
modernize-scientific-stack, polyglot-rust-c, portfolio-optimization, prove-plus-comm, pypi-server
resolved_count_from_raw_grep=10
```
Exact match to the bundle's claimed `resolved_ids`. The recount also surfaces, rather than
hides, the one non-boolean row: `headless-terminal` is `null`/`parse_error` (tb could not find
a short test summary), so the full accounting is **10 true + 78 false + 1 null = 89** — matches
`calibration.md`'s own disclosure of `parse_error=1`.

**3. Three resolved tasks spot-checked, deliberately different from the ones the Claude-side
pass already checked** (`build-pmars`, `pypi-server`, `prove-plus-comm`, `git-leak-recovery`):
`build-pov-ray`, `cancel-async-tasks`, `extract-elf`. For each: raw per-task `results.json`
confirms `is_resolved: true`; the `parser_results` test names were diffed against the real
upstream `tests/*.py` `def test_...` names in
`.../shared_bench/terminal-bench-2.1/tasks/<task_id>/tests/` and matched exactly; each task's
`agent-logs/episode-N/debug.json` shows a genuine, distinct `litellm_call_id` and
`"api_base": "http://100.100.104.147:30001/v1/"`, e.g.
`build-pov-ray` -> `litellm_call_id: 9751c806-b824-4ee7-8669-918947a47e9b`,
`cancel-async-tasks` -> `6faf4147-670a-42e4-a324-7392800b1171`,
`extract-elf` -> `befa29a2-91e7-4df1-a0a1-bbe39898c1c8` (three different UUIDs, consistent with
three distinct live API calls, not replayed/copied data).

**4. Serving identity — programmatic live-vs-bundle diff, not eyeballing.** Live-curled
`/get_model_info` and `/get_server_info` on `http://100.100.104.147:30001` right now and
diffed field-by-field against the bundle's `serving/get_model_info_before.json`,
`get_model_info_after.json`, and `get_server_info_after.json`:
```
model_full_equal_before_live True  after_live True  before_after True
server_selected_equal True   (server_selected_diffs = {})
```
model_path, tokenizer_path, served_model_name, random_seed (484925000), version (0.5.13),
tp_size (2), tool_call_parser, context_length, mem_fraction_static, max_total_num_tokens,
and max_prefill_tokens are byte-identical across the before capture, the after capture, and
a fresh probe taken independently by this session two days later. This is the strongest
practical proof available on this stack (model/response `model` strings are not trusted here;
weights+endpoint are).

**5. infra_fail scoring — verified as real code, and independently corroborated against the
actual invalidated prior run's own artifacts (not just the narrative in `calibration.md`).**
Read `tb21_strict_batch_summary.py` directly: `infra_fail` is stamped per-row from a single
*batch-level* `tb_rc` value (`infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not
in (0, None))`), so a nonzero batch exit code poisons every row regardless of individual
pass/fail. Then went further than tracing the code: pulled the actual persisted artifacts of
the **07-10 run** this story is about (`tb21_coder_t2_c32_0710064916`):
```
tb.exit_status: tb_rc=143
tb21_strict_summary.json: infra_fail=89, resolved=12, total=89, accuracy=0.1348314606741573
```
This is hard, on-disk, official-scorer-output confirmation — not just plausible code logic —
that the invalidated run really did SIGTERM (`tb_rc=143`) and really did carry a real
`resolved=12` signal underneath the batch-level `infra_fail=89` contamination, exactly as
`calibration.md` states. A third run, `tb21_coder_t2_c32_0711203259` (2026-07-11, ~1h before
the final clean run), was also found with a nonzero `tb_rc=126` and an incomplete/partial
artifact set — consistent with a normal, human pattern of iterating toward a clean run rather
than a single convenient number picked from nowhere. The final run
(`tb21_coder_t2_c32_0711211754`) is the only one of the four found with `tb_rc=0`.
10/89 = 0.11235955... = 11.24%, recomputed independently and matches.

## Finding on the existing "dual-sign" framing (flagged regardless of the verdict above)

`git show -s --format=fuller` on both commits that ever touched this path:
- `39bf63a`: Author/Committer `Zeng-Weijun <zeng_wjccnu@163.com>`, trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- `ac80ef8`: Author/Committer `Zeng-Weijun <DorcasMilleriop@therapist.net>` (a **different**
  local git identity than the first commit), trailer **also**
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

`ac80ef8`'s own message claims "Both blind auditors independently verdict REAL" — but the only
AI-authorship evidence available on both commits points to the same model family (Claude),
even though the two passes ran under different local git identities. That does not itself make
the underlying 10/89 number false (this session independently re-derived it from raw ground
truth above, with zero reliance on either prior commit's aggregate claims), but the "2
independent blind auditors" wording overstates cross-family diversity. This signoff is the
first artifact on this path with verifiable non-Claude (OpenAI Codex) authorship, closing that
specific gap.

## Process note (transparency on how this file was finalized)

This session's pinned interactive Codex CLI audit (tmux pane `codex-6226ff`) executed all of
the SSH commands and comparisons cited above directly and produced the findings verbatim as
quoted. Mid-session, after the analytical work above was already complete and logged, the local
tmux pane hosting that interactive session was lost to an environment/tooling issue unrelated
to the audited evidence (a pane-lifecycle glitch in the local orchestration harness, not a
finding about the KVM host, the bundle, or the model). The orchestrating Codex process
recovered the pane's own findings from its on-disk session transcript
(`~/.codex/sessions/2026/07/13/rollout-*.jsonl`) rather than re-deriving them, and this file
transcribes those recovered, verbatim findings plus completes the mechanical
write/commit/push step. No claim in this document was invented or inferred beyond what the
quoted command outputs show; anything not directly observed (e.g. a from-scratch review of all
89 raw per-task directories rather than the 3+1 sampled here) is explicitly out of scope, per
the brief's own "spot-check, don't re-run everything" instruction.
