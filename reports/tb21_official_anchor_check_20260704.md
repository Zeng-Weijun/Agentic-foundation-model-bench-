# TB2.1 official-anchor check — is our setup reliable for scoring Qwen? (by-85, 2026-07-04, READ-ONLY WebFetch)

Answers the user's "用这套测 Qwen 分数可靠吗". All facts from the official board (tbench.ai) + Artificial Analysis + the Terminal-Lego paper (2606.03461) + Terminus-2 methodology. No launch/model-call.

## ★ ONE-LINE VERDICT
**Our `9/89` (gpt-5.4-mini · xhigh · TB2.1 · privileged-docker) has NO direct same-口径 official anchor** — the board's only OpenAI entry is the flagship **GPT-5.5 at provider-default "medium" effort** (78.2% Terminus-2), not a mini tier and not xhigh. **For a reliable Qwen number, match the official 口径 (Terminus-2, provider-DEFAULT effort, 7200s/task, pass@1×3) and anchor to `Qwen3-Coder-480B = 23.9%` (TB2.0 Terminus-2) — validate the harness first by reproducing a known official point within ±3-5pp.**

## ① TB2.1 official leaderboard (tbench.ai/leaderboard/terminal-bench/2.1) — models × scaffold
Board protocol: **Terminus-2 agent, e2b sandbox, pass@1 averaged over 3 repeats/task.** Terminus-2-filtered entries (6 of 13 shown):
| model | Terminus-2 score |
|---|---|
| Claude 5 Fable | 80.4% ±2.3 |
| **GPT-5.5** (2026-05-01) | **78.2% ±2.4** |
| Claude Opus 4.8 | 74.6% ±2.4 |
| Gemini 3 Pro | 74.4% ±2.6 |
| Gemini 3.1 Pro | 70.3% ±2.9 |
| Claude Opus 4.7 | 66.1% ±2.7 |
Top overall (non-default configs): Claude Opus 4.8 84.6%, **GPT-5.5 (xhigh) 84.3%**, Codex-CLI+GPT-5.5 83.4%. **⚠ Only ONE OpenAI model on the board (GPT-5.5 flagship). NO gpt-5.x-mini tier and NO Qwen model visible** (7 of 13 entries not rendered — a mini/Qwen may be hidden; confirm on the full board).

## ② Official default reasoning effort — ★ the 口径 gap ★
Terminus-2 harness sets **`reasoning_effort = None`, `max_thinking_tokens = None`** → it does **NOT override provider defaults**. For configurable-effort models the board uses the **provider default: "medium" for GPT-5.5**, "high" for Claude Opus 4.7. The `GPT-5.5 (xhigh) 84.3%` line is a *separate explicit-xhigh submission*, distinct from the default-effort 78.2%.
- **⇒ Our truemodel line runs xhigh; the board's baseline runs medium. Not the same 口径.** To compare to a board number we must either (a) match a specific xhigh submission, or (b) re-run at default effort. Our 9/89 (xhigh) is an **internal** number, not board-comparable as-is.

## ③ Qwen (and GPT-mini) anchors — Phase-2 sglang reproduction target
Official Terminus-2 results on **Terminal-Bench 2.0** (from the Terminal-Lego paper 2606.03461 + llm-stats TB2.0 board):
| model | TB2.0 Terminus-2 pass@1 |
|---|---|
| GPT-5 (high) | 42.5% |
| **GPT-5-Mini** | **24.0%** |
| **Qwen3-Coder-480B (A35B)** | **23.9%** |
| GPT-OSS-20B | (low; Terminal-Lego-Qwen3-8B 11.8% "clearly above" it) |
- **★ Qwen reproduction anchor = `Qwen3-Coder-480B = 23.9%` on TB2.0 Terminus-2 (default effort).★** ±3-5pp band ⇒ **~19–29%** is the pass window for "our harness reproduces the official Qwen number."
- ⚠ This is **TB2.0**, not TB2.1. No confirmed official **TB2.1** Qwen number in the visible board (check the hidden 7 entries + the Qwen3-Coder-Next tech report 2603.00729). **For the ±3-5pp criterion, run Qwen on TB2.0 (matched to 23.9%) OR find the TB2.1 Qwen entry — do not cross-compare TB2.0 anchor ↔ TB2.1 run.**
- GPT-5-Mini (24.0%, TB2.0) is the nearest "mini-tier" GPT anchor, but it is GPT-5.5-era, NOT our gpt-5.4-mini, and it's TB2.0 not TB2.1.

## ④ Official per-task time budget (原文)
Terminus-2: **per-task timeout = 2 hours (7,200 s)**; **max episodes = 100** (an episode = model reviews state + plans next terminal actions). Board averages **pass@1 over 3 repeats**. (Note: the Qwen-team TB2.0 eval used a 3h timeout + 32CPU/48GB + temp=1.0/top_p=0.95/top_k=20/max_tokens=80K/256K-ctx, avg 5 runs — a *different* config from the board's 7200s×3; match whichever board you anchor to.)

## Reliability conclusion (for "用这套测 Qwen 分数可靠吗")
**Reliable IF the 口径 is matched, NOT as the current xhigh/TB2.1 line stands:**
1. **Validate the harness first** — reproduce a KNOWN official point at matched 口径: e.g. **GPT-5.5 (medium) on TB2.1 → expect 78.2% ±3-5pp**, or **Qwen3-Coder-480B on TB2.0 → expect 23.9% ±3-5pp**. If we land in-band, the harness is board-comparable.
2. **Then Qwen numbers are reliable** only when run at the SAME matched 口径 (Terminus-2, provider-default effort, 7200s/task, 100 episodes, pass@1×3, sandbox equivalence).
3. **Watch-outs:** (a) our privileged-docker/fuse-overlayfs sandbox ≠ official e2b — prove parity (the same reason TB2.1 oracle needed the mount fixes); (b) effort must be default (medium), not xhigh, to match the baseline board; (c) pin TB2.0-vs-TB2.1 to the anchor you use.
4. Our internal **9/89 xhigh** is fine as an internal signal but **must not be quoted against the official board** (no matching anchor).

**Refs:** tbench.ai/leaderboard/terminal-bench/{2.0,2.1}; artificialanalysis.ai/evaluations/terminalbench-v2-1; Terminal-Lego "What Makes Interaction Trajectories Effective…" arXiv 2606.03461; llm-stats.com/benchmarks/terminal-bench-2; layerlens GPT-5(high) 42.5%. TB2.1 spec: `tb21_canonical_final_verdict_84of89_20260704.md` (our oracle 84/89).
