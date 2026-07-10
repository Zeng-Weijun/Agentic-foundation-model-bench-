# Experiments — Agentic Foundation Model Bench

> **Living document.** Every finished run is appended here. A score that is not in this
> file did not happen. A score whose evidence cannot be recomputed from disk is not a score.
>
> Last updated: **2026-07-09** · Repo HEAD at write time: `45839f6`

---

## §0 Maintenance contract

When a run finishes, do **all four**:

1. Append one row to the [master table](#2-master-table).
2. Add a run card in [§3](#3-run-cards) carrying the **9 mandatory fields**.
3. If it changes a canonical number, keep the old row with `status: superseded`. Never delete history.
4. If a harness defect surfaced, append it to the [overturn log](#5-overturn-log).

### The 13 mandatory fields

Fields 10–13 were added on 2026-07-09. **Each one exists because its absence caused a specific
failure that same day** — see the "why" column. Do not treat them as bureaucracy.

| # | Field | Rule | Why (the incident that forced it) |
|---|---|---|---|
| 1 | `bench` | Verbatim id from the score artifact | |
| 2 | `model` | Exact served name, not a friendly alias | |
| 3 | `harness` + version | Scaffold **and** pinned version (`mini-swe-agent v2.0.0`) | |
| 4 | `score` | Fraction **and** `resolved/total` | |
| 5 | `run_root` | Absolute path on shared storage | |
| 6 | `results` + `sha256` | Results file and its digest | |
| 7 | `image` | Registry `@sha256:` digest, **or** `ABSENT` + the transport actually used | |
| 8 | `trace_manifest` | Path to a **filled** `reports/trace_manifest_template.yaml` | The template has existed for weeks and **has never once been filled**. §6. |
| 9 | `status` | One of the enum below | |
| **10** | **`script_digests`** | `sha256` of **every** script on the invocation path: launcher, runner, helpers, orchestrator. Not just the entrypoint. | The runner that produced TB2.1's canonical `70.8%` was git-untracked, got overwritten by a later patch, and **is now unrecoverable**. Nobody noticed because nobody had its hash. §6 C1. |
| **11** | **`serving_config`** | Not just `base_url`. Record: served model name, weight path + revision, `tp`, `context-length`, `mem-fraction-static`, `tool-call-parser`, serving-runtime version, GPU indices, **and the full launch command**. | Both Qwen runs recorded only `base_url`. That server is now dead; the replacement is a *different instance*, and from the artifact alone it is impossible to tell whether it was configured identically. |
| **12** | **`relay_upstream`** | Record the upstream the relay proxies to, **separately from the endpoint URL**. | `endpoint = :18540` stayed constant while `upstream` silently moved `176.122…` → `45.78…`. The endpoint field **could not see the change**. That change cost a 2-hour run. §5.11. |
| **13** | **`llm_health`** | Run-level: `total_calls`, `retry_exhausted`, `http_5xx`, `http_429`, `hard_fail_rate`, `token_sum` vs baseline. | The strict gate's `infra_fail` **structurally cannot see LLM-layer failures**. 125 hard failures → `infra_fail = 0` → gate reported clean. §5.12. |

> **On field 10.** `mtime` and `sha256` prove *content* identity, not *behavioural* identity — a script
> can be byte-identical and behave differently from a different directory (§5.9). Record the digest
> **and** the absolute path it ran from.
>
> **On field 13.** Two layers. **Run-level** from `run.log`, counted in two columns (`infra_class`
> vs `content_class`) and never one. **Task-level** from `agent-logs/episode-N/debug.json`, which is
> already on disk: `content_class` errors are always attributable to their task; `infra_class` errors
> only when the error killed the episode, since `debug.json` is overwritten per episode and a failure
> a retry survives leaves nothing behind. An earlier version of this line declared per-task
> attribution *impossible from disk*. It is not, and the file that disproves it was there the whole
> time. §5.12.

### `status` enum

| Value | Meaning |
|---|---|
| `canonical` | Dual-signed, quotable, current best evidence for that cell |
| `superseded` | Was canonical, replaced; kept as history — **do not quote** |
| `blocked` | **Infra failure** (`infra_fail > 0`: missing artifact / fatal timeout / non-zero runner rc) — not a model score |
| `forbidden` | Number is real but measures the harness or the environment, not the model |

### ⚠️ The harness's `blocked` is **not** this table's `blocked`

The strict reducer sets `status="blocked"` whenever `ready == false`, and
`ready` requires **`unresolved == 0`**. A real model never solves every task, so
**every real model run is `blocked` by construction** — including this table's own canonical
baselines. Meanwhile `score = resolved/total` is computed *independently* of `ready`.

> **Read `resolved/total`. Ignore `ready`/`status` from the reducer.**
> A verdict rule that rejects a score *because the harness said `blocked`* rejects every real run.
> This document shipped exactly that rule on 2026-07-09 and had to retract it. See §5.12(c).

### Verdict rules (v4)

Apply in order:

1. **`infra_fail` must be decomposed before it is used.** The harness computes
   `infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not in (0, None))`, which folds a
   task-level outcome in with two genuine infrastructure faults:
   - `missing_artifact` or `tb_rc != 0` → real infrastructure fault → **`blocked`**. Attribute it.
   - `fatal_timeout` → **a task-level result, not an infrastructure fault.** Note it; it does not
     block. The canonical Qwen × terminus-2 run carries `infra_fail=1` purely from `timeout=1`.
     Reading the boolean instead of its terms disqualifies this document's own anchor.
2. `parse_error > 0` → **correctable**. Fix it, and record the correction task-by-task with its
   justification. (The canonical TB2.1 `62 → 63` was exactly this.)
3. **`llm_health` hard failures must be split by layer**, then only one layer counts:
   - `infra_class` — `5xx`, `429`, `connection_error`, `read_timeout`, retry exhaustion against
     the endpoint. **A material rate here → `forbidden`**, because the harness gate is
     structurally blind to it (§5.12a). This — not its `blocked` status — is the only reason the
     2026-07-09 TB2.1 re-measurement (`53/89`) is disqualified.
   - `content_class` — `400 BadRequest`, tokenizer errors, `context_length_exceeded`.
     **Ordinary agent behaviour. Never `forbidden`.** The canonical Qwen run carries six
     `BadRequestError`s, three of them `context_length_exceeded` from a trajectory that grew to
     262,170 tokens against a 262,144-token window. The canonical gpt-5.5 run's single
     `Unknown Error` was `disallowed special token <` — a tokenizer error, not a relay fault, so
     its relay-layer hard-failure count is 0 and not 1.
4. Scaffold/protocol mismatch (e.g. 100% of trajectories rejected by the parser) → **`forbidden`**.
   Establish this from the trace, never from a low score (§5.13).
5. Otherwise → eligible for `canonical`, pending dual review.

Compare a run against **the counts of the run it is being compared to**, not against a threshold
imported from another benchmark.

**Hard rule.** A run that has not passed dual review never enters the quotable column,
no matter how plausible the number looks.

### Evidence rule

The score **must be independently recomputable** from the per-case artifacts on disk.
A number that exists only in a process log is not a number. (Written in blood — see §5.3.)

### ★ Where the truth lives — read this before disputing any score

**`_coordination/<sprint>/DECISIONS.md` is the ledger.** Every reconciliation and every
dual-sign is recorded there. Score artifacts under `reports/scores/` are an *index*, and
the index is incomplete.

> **"grep found nothing" ≠ "it does not exist."**
> Search order is fixed: **① `DECISIONS.md` ledger entries → ② `reports/scores/` → ③ the
> worktrees.** This repo has several worktrees (`tb21-image-fixes-r3`,
> `tb21-gpt55-launcher-s55`, …) and key artifacts are scattered across them.

On 2026-07-09 this document's author asserted that the `Qwen × terminus-2` run did not
exist, on the strength of an exhaustive filename/content grep. It does exist, it was
dual-signed on 2026-07-06, and the ledger said so at line 1480. See §5.7.

---

## §1 Scoring doctrine

### 1.1 The only two reproducible official anchors

| Bench | Official config | Anchor |
|---|---|---|
| SWE-bench Verified | bash-only, `gpt-5.2-high` | **72.8%** |
| Terminal-Bench 2.1 | `terminus-2`, `gpt-5.5`, medium effort | **78.2% ± 2.4** (5-run mean) |

Everything else is an unanchored archive score or a self-baseline.
Third-party aggregator numbers are hallucination-grade and banned.

### 1.2 Forbidden-to-quote list

| Number | Why |
|---|---|
| SWE-V `23.4%` (Qwen × mini) | Scaffold mismatch: 498/498 trajectories rejected for multi-tool-call format. Measures the harness. |
| SWE-V `43.6%` (gpt-5.5, v2) | 211 `docker exit-125` container-start failures recorded as `no_patch`. Labelled `superseded_history_do_not_quote_as_model_score`. |
| TB2.1 raw `62/89` | Scorer false negative on `headless-terminal`; corrected value is 63/89. |
| TB2.1 `64.04%` (KVM run) | Gate returned `ready=false`, `status=blocked`. Not a model score. See §5.6. |
| Multilingual raw `67.0%` | 26 Gradle tasks scored false-zero offline. Its match to the 66.7% anchor is **coincidental cancellation**. Use the 73.4% clean subset. |
| RepoZero `28.2%` / `67.0%`-as-final | `/tmp` inode exhaustion corrupted per-case evidence, twice. |

### 1.3 Failure taxonomy (bug-for-bug compatibility)

Upstream benchmarks have their own bugs. We reproduce them; we do not fix them, because
fixing them makes our numbers incomparable to the leaderboard.

| Class | Test | Action |
|---|---|---|
| `offline-induced` | Official harness passes, ours fails | **Fix it.** Our infra broke it. |
| `upstream-native` | Official harness also fails | **Archive, do not fix.** Attach evidence. |

Ledger identity: `passed + offline_fixed + upstream_archived = total`.

### 1.4 Trace policy

Per `traces/README.md`, raw traces stay on shared storage — they are large and may carry
model outputs, absolute paths, tool calls and secrets. This repo stores a **pointer** per
cited trace, filled from `reports/trace_manifest_template.yaml`, recording prompt/system-prompt
hash, scaffold + tool schema, verifier command and exit code, failure category, and an explicit
**infra-failure vs model-failure** split.

Never commit secrets, API keys, raw private benchmark data, or large logs.

### 1.5 What identifies a model — and what does not

A trace records the `model` string an agent sent. That string is not evidence of which
weights answered. Verified against a live sglang server, 2026-07-10:

```
POST http://<host>:30000/v1/chat/completions
     {"model": "Qwen/Qwen3-Coder-30B-A3B-Instruct", ...}
->   HTTP 200
     {"model": "Qwen/Qwen3-Coder-30B-A3B-Instruct", "content": "OK", ...}

GET  http://<host>:30000/get_model_info
->   {"model_path": ".../Qwen3-30B-A3B-Instruct-2507"}     # a different model entirely
```

sglang does not validate `model`. It echoes it. A run can evaluate the wrong weights from
the first token to the last and produce a trace that looks flawless.

Ports do not identify a model either. `:30000` served `Qwen3-Coder-30B-A3B-Instruct` on the
host that produced the canonical Qwen scores, and serves `Qwen3-30B-A3B-Instruct-2507` on the
host that replaced it.

| Recorded value | Identifies the weights? |
|---|---|
| `model` in the request | no — you chose that string |
| `model` in the response | no — the server echoes it back |
| `base_url` alone | no — same port, different host, different model |
| **`model_path` from `/get_model_info`, fetched from that host:port at run time** | **yes** |

#### The same fault, in a system that shares no code with sglang

The API relay used for every `gpt-5.x` row in this table behaves identically, and worse. Probed
2026-07-10:

```
POST /v1/chat/completions  {"model": "gpt-5.7-doesnotexist", ...}
->  200. The response's `model` field echoes `gpt-5.7-doesnotexist`.
    The response's *content* introduces itself as GPT-5.1.

POST /v1/chat/completions  {"model": "gpt-5.6-sol", ...}
->  200. The content also introduces itself as GPT-5.1.
```

A fabricated model name is served. Two different real names produce a reply claiming the same
identity. **Nothing in the response body distinguishes them.** The only names that fail are `-codex`
variants and the entire `claude` family, which return `400` — so an endpoint that refuses a *valid*
model with a clear error will happily serve an *invented* one without any.

Two systems with nothing in common — a self-hosted inference server and a third-party proxy — fail
the same way: **they accept the name you assert and let you believe it.** The lesson is not about
either implementation. It is that a model identifier travels through a request as data, and data does
not verify itself. Record the endpoint and probe it; never record the name and trust it.

A consequence worth stating plainly, because it is easy to claim otherwise: **cross-family
adversarial review is not possible through this relay.** There is one family behind it. Any pipeline
asserting that a `claude-*` judge reviewed a `gpt-*` generator through this endpoint asserts something
that returned `400` and never ran.

#### ⚠️ Every `gpt-5.x` row in this table carries an undeclared scaffold

The relay is a proxy in front of a **ChatGPT-Codex account**, not the OpenAI API. It says so itself,
in the error it returns for the models it refuses:

```
"The 'claude-opus-4-6-thinking' model is not supported when using [ChatGPT-Codex account]"
```

and in the ~5000 tokens of system prompt that arrive with every request — the figure this table first
recorded as a mysterious `prompt_tokens: 5087` for a two-token message, and mistook for a relay
defect. It is not a defect. It is Codex's system prompt, prepended to every call we made.

So the `gpt-5.5` in these rows is not a bare model. It is a model wrapped in a harness we never chose,
never versioned, and never recorded — and it is being compared against official anchors
(`72.8%` for `gpt-5.2-high` on SWE-V bash-only, `78.2%` for `gpt-5.5` on TB2.1) that were almost
certainly measured through the plain API.

This does not invalidate the rows. It means the comparison to the anchors was never like-for-like,
and nothing in the pipeline said so. `serving_config` (field 11) covers self-hosted endpoints; there
is no equivalent field capturing *what a proxy does to a request on its way through*, and
`relay_upstream` (field 12) records only where it went, not what it became.

The `Qwen` rows are unaffected: they call self-hosted sglang directly, with no relay in the path. That
is now an argument for the self-hosted lane beyond cost — **it is the only lane whose prompt we can
account for.**

**Open, not closed.** The claim that the injected prompt changes benchmark behaviour is plausible and
unmeasured. The experiment that settles it is a paired run of one bench through the relay and through
a bare API key, and this repo has not run it.

Hence field 11 of §0. `serving_config` must be captured **during** the run, from the endpoint
the run actually used, and stored with the run. Not looked up afterwards in a config file that
describes some other host.

Captured example: [`experiments/serving/sglang_launch_20260710.sh`](../experiments/serving/sglang_launch_20260710.sh)
(verbatim `ps -eo args`) and `SERVING_CONFIG_20260710.json` (402 server args per port, secrets
redacted at capture time).

---

## §2 Master table

| Bench | Model | Harness + version | Score | resolved/total | Anchor | Status | Card |
|---|---|---|---|---|---|---|---|
| SWE-bench Verified | `gpt-5.5` (high) | `mini-swe-agent v2.0.0` | **77.2%** | 386/500 | 72.8% (`gpt-5.2-high`) | `canonical` | [3.1](#31-swe-v--gpt-55--mini--772-canonical) |
| SWE-bench Verified | `gpt-5.5` (high) | `mini-swe-agent v2.0.0` | 43.6% | 218/500 | — | `superseded` | [3.2](#32-swe-v--gpt-55--mini--436-superseded) |
| SWE-bench Verified | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | `qwen-code 0.15.6` (native) | **48.6%** | 243/500 | ~51% (vendor self-report) | `canonical` | [3.3](#33-swe-v--qwen--qwen-code--486-canonical) |
| SWE-bench Verified | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | `mini-swe-agent v2.0.0` | 23.4% | 117/500 | — | `forbidden` | [3.4](#34-swe-v--qwen--mini--234-forbidden) |
| Terminal-Bench 2.1 | `gpt-5.5` (medium) | `terminus-2` | **70.8%** | 63/89 | 78.2% ± 2.4 | `canonical` | [3.5](#35-tb21--gpt-55--terminus-2--708-canonical) |
| Terminal-Bench 2.1 | `gpt-5.5` (medium) | `terminus-2` + `/dev/kvm` | 64.04% | 57/89 | — | `blocked` | [3.6](#36-tb21--gpt-55--terminus-2--devkvm--6404-blocked) |
| Terminal-Bench 2.1 | `gpt-5.5` (medium) | `terminus-2` — **re-measurement 2026-07-09** | 59.55% | 53/89 | — | `forbidden`⁵ | [3.12](#312-tb21--gpt-55--terminus-2--5955-re-measurement--forbidden) |
| Terminal-Bench 2.1 | `Qwen/Qwen3-Coder-30B-A3B-Instruct` (medium) | `terminus-2` | **10.1%** | 9/89 | none (no Qwen anchor on TB2.1) | `canonical`¹ | [3.7](#37-tb21--qwen--terminus-2--101-canonical-with-caveat) |
| Terminal-Bench 2.1 | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | `qwen-code 0.15.6` host-bridge | 16.85% | 15/89 | — | contrast² | [3.8](#38-tb21--qwen--qwen-code-bridge--1685-contrast) |
| Terminal-Bench 2.1 (oracle) | — | `terminus-2` | 95.5% | 85/89 | — | infra map³ | [3.9](#39-tb21-oracle-infra-map) |
| RepoZero (188-case **rescue pool**) | `gpt-5.5` | internal codex runner | 67.55% raw / 67.0% strict | 127/188 · 126/188 | 54.70% ± 2.55 — **on 400 cases, not these** | `forbidden`⁸ | [3.10](#310-repozero--gpt-55--6755-raw--670-strict) |
| SWE-bench Multilingual | `gpt-5.5` (high) | `mini-swe-agent v2.0.0` | **73.4%** clean | 201/274 | 66.7% (`gpt-5.2-high`) | `canonical` | [3.11](#311-swe-bench-multilingual--gpt-55--mini--734-clean) |
| SWE-bench Multilingual | `gpt-5.5` (high) | `mini-swe-agent v2.0.0` | 67.0% raw | 201/300 | 66.7% | `forbidden` | [3.11](#311-swe-bench-multilingual--gpt-55--mini--734-clean) |
| SWE-bench Verified | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | `qwen-code 0.15.6` — **re-measurement 2026-07-10** | 48.4% | 242/500 | 48.6% (this table, 2026-07-05) | `reproduced`⁶ | [3.13](#313-swe-v--qwen-coder--qwen-code--484-re-measurement) |
| SWE-bench Verified | `Qwen/Qwen3-30B-A3B-Instruct-2507` | `qwen-code 0.15.6` | 21.6% | 108/500 | ≈25.7% (nebius, base) | `canonical`⁷ | [3.14](#314-swe-v--instruct-2507--qwen-code--216-pending) |

⁶ **`reproduced`** — a new status. Dual-signed and valid, but produced under a serving stack that differs from the row it reproduces, so it is *not* that row's `canonical` and does not replace it. Two auditors worked from the raw artifacts, blind to each other and on different filesystems; one audited the run live at 478 rows, the other after completion at 496. Both were instructed to prove the score fake. Both failed. See §3.13.
⁷ **Dual-signed, and a lower bound.** `no_patch` is 137/498 (27.5%) against 6/496 (1.2%) for Coder on the same bench, harness, serving host and day — a 23× rise. (An earlier version of this footnote said 45×, having compared against the *canonical* Coder run's 3/500 instead of the same-day one. See §3.14.) Two independent censuses of all 137 both put *zero* of them in the parser-failure column: the model calls tools, reads code, edits files, and does not converge. So 21.6% measures the model. But `43/500 = 8.6%` of the benchmark ended at an envelope limit — a 229,376-token context ceiling, a rollout timeout, or a crash — rather than at the model's own judgement, and one further genuine resolve was discarded by the denominator defect. Quote it as *the score under this scaffold configuration*, never as an upper bound on the model. §3.14.

⁸ **Not a RepoZero score, and not comparable to the anchor.** The official figure, `54.70% ± 2.55`, is measured on **400** Py2JS cases — verified from three independent sources that agree verbatim: the paper (`arxiv.org/html/2605.07122v3`), the repo README's 24-library / 400-file table, and the harness itself, whose `valid_ids` has `len == 400`. Its protocol is `mini-swe-agent` + `Claude-4.6-Sonnet`, All-Pass Rate, single-attempt `pass@1`.

Our 188 are not a sample of those 400. An internal note claimed they came from a `filter_cleaned_test_cases.py` subset; **no such script exists anywhere on disk.** `candidate_pool.json` shows what they actually are: `infra_all_pass_false = entry_missing 131 + timeout 49 + nonzero 8` — the cases whose *infrastructure* failed in an earlier `w100` run, collected for a rescue re-run. A pool selected by "previously broke on our side" is structurally biased, and 67.55% answers the question *"how many of the tasks that crashed last time pass now"*, which is not the question RepoZero asks.

To use the anchor, run the official protocol over all 400. The paper's per-difficulty columns do not divide to integers against the repo's `difficulty.json`; quote only the Avg column.

¹ Dual-signed (ledger `DECISIONS.md` L1480 reconciliation 15/15 PASS + surface:85 review PASS). The artifact's own `score_note` says: *"single pass@1 compatibility probe; no official TB2.1 Qwen anchor claimed."* **Do not put it on a leaderboard.**
² Non-official harness (host QwenCode + `docker exec` bridge). A native-scaffold contrast point, not a leaderboard number.
³ Oracle-solution infra pass map, **not a model score**. r6 explicitly states so.
⁴ Reconciled and accepted in the ledger (`DECISIONS.md` L1534). Its score artifact was never filed under `reports/scores/` — an **index gap**, not an evidence gap. Mandatory caveats: 188-case rescue subset (not the official 400), no LLM judge, single attempt.
⁵ The gate reported clean, yet the same run logged **125 retry-exhausted LLM failures** (117–120 × `503`, 5 × `429`) against a relay ingress that had silently changed upstream. The gate is structurally blind to the LLM layer, and the `c=89` single-batch design leaves no control group — the damage cannot be quantified. Disqualified on **epistemic** grounds. **Not** because the harness said `blocked`: it says that for every real run. See §5.12.

---

## §2.1 The result that matters: the interaction-mode gradient

Hold the model fixed (`Qwen3-Coder-30B-A3B-Instruct`) and vary only the harness:

| Interaction mode | Harness | SWE-V | TB2.1 |
|---|---|---:|---:|
| Native multi-tool-call | `qwen-code 0.15.6` | **48.6%** | 16.85% (bridge) |
| Single bash block | `mini-swe-agent v2.0.0` | 23.4% | — |
| Live terminal (tmux) | `terminus-2` | — | **10.1%** |

Same axis, `gpt-5.5`: **77.2%** (mini) vs **70.8%** (terminus-2) — nearly flat.

**Reading.** A 30B model loses ~25 pt moving from its native tool protocol to a bash-only
protocol, and lands at 10.1% on a live terminal. A frontier model barely notices. The
bottleneck **migrates** with interaction complexity:

- at the **bash layer** it is output-format compliance — 498/498 SWE-V trajectories rejected;
- at the **terminal layer** it is screen comprehension and convergence — the 89-task Qwen run
  shows `83 unset / 3 context_length_exceeded / 2 unknown_agent_error / 1 test_timeout`, i.e.
  the agent mostly never converges rather than failing a test.

**Consequences for harness design.** The ROI is in the interaction layer, not the prompt:
screen-state summarisation, environment-constraint pre-announcement, an explicit turn budget
with convergence pressure, and a false-completion guard.

**Consequences for training mix.** Weight the mixture by the *deployed* scaffold. Either teach
the parser to accept multi-call output, or SFT the model to emit single-block bash. Do not
benchmark a model on a protocol it was never trained to speak and call the result a capability.

---

## §3 Run cards

### 3.1 SWE-V · gpt-5.5 × mini · 77.2% `canonical`
- **run_root** `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/v2_full500_c100_gpt55_20260704T211853Z`
- **results** `results.jsonl` · `sha256 fb1bc11f1735c13a1649d94ab93cd5f3bc949b4ad6466ad1f9004cdddc00ccd6`
- model `gpt-5.5` · effort `high` · scaffold `mini-swe-agent v2.0.0` · runner `full500_model_orchestrator_v2_podb.py` (v2.1)
- `resolved 386 / unresolved 114 / unique 500 / duplicates 0 / no_patch_rows 0`
- `freeze_utc 2026-07-05T02:38:21.824493Z`
- v2.1 repair: `stale_rows_removed 212`, `preheat ok=212 errors=0`, overlay includes `--pull=never`
- concurrency `c=100` (**inferred from run_root dirname**; explicit field `ABSENT`) · `timeout_multiplier ABSENT` · `n_attempts ABSENT`
- artifact `reports/scores/swev_full500_gpt55_high_v21_20260705T0220Z.{yaml,json,md}`
- `trace_manifest` **ABSENT**

### 3.2 SWE-V · gpt-5.5 × mini · 43.6% `superseded`
- Same `run_root` as 3.1 · `results.jsonl sha256 a9c184aae704885296c1ac90b1a3906cebb16bb618d9ff37cc88ee8bcefde7e0`
- `resolved 218 / 500` · `infra_error_event_count 16` · `freeze_utc 2026-07-05T00:10:34.479467Z`
- Status verbatim: `superseded_history_do_not_quote_as_model_score`
- Cause: 211 instances hit `docker exit-125` on container start and were recorded as `no_patch`. See §5.1.

### 3.3 SWE-V · Qwen × qwen-code · 48.6% `canonical`
- **run_root** `/mnt/…/agentic-foundation-model-bench/runs/swev_qwencode_v21_20260705T190754Z/full500_c20`
- **results** `results.jsonl` · `sha256 132e8a2610e3be07d7fd72b2aad6f14afe84bffce5e1bc5169d2ba1155bc1aef`
- model `Qwen/Qwen3-Coder-30B-A3B-Instruct` · scaffold `qwencode` `v0.15.6` · effort `ABSENT`
- dataset `princeton-nlp/SWE-bench_Verified test cached c104f840cc67f8b6eec6f759ebc8b2693d585d4a`
- `resolved 243 / 500` · `agent_status_counts {patch: 497, no_patch: 3}` · `attempts 1` · `c=20`
- `base_url http://100.103.228.120:30000/v1` — ⚠️ **this sglang server is DEAD as of 2026-07-09**
- `created_at_utc 2026-07-06T06:59:51Z` (no `freeze_utc`)
- artifact `reports/scores/swev_qwencode_v21_full500_final_20260706.json`

### 3.4 SWE-V · Qwen × mini · 23.4% `forbidden`
- **run_root** `/mnt/…/swe/rootless/reports/swev_full500_model_20260702/v2_1_qwen30ba3b_merged_full500_20260705T092310Z`
- **results** `results_merged.jsonl` · `sha256 7c582634ea95b8349dcf5640252fd7a76543ed03dc52ca0bc9e34cef0bf1794e`
- `resolved 117 / 500` · `infra_events_total 47` · `frozen_at_utc 2026-07-05T09:23:10Z`
- 3 merged shards, `c=50` each · overlay `step_limit 80`, container timeout 180s, model timeout 300s, `run_args ["--rm","--network=none","--pull=never"]`
- **Not filed under `reports/scores/`** — only `score_summary.json` inside the run tree. Index gap.
- Reconciled in ledger: `DECISIONS.md` — surface:86 ACCEPT ✓ (16/16 PASS)
- **Why forbidden**: 498/498 trajectories emitted multi-tool-call format; `mini`'s bash-only parser rejects it. 100% format rejection. This measures the scaffold.

### 3.5 TB2.1 · gpt-5.5 × terminus-2 · 70.8% `canonical`
- **run_id** `tb21_gpt55_official_medium_c89_single_20260704t195417z`
- **run_artifact** `/mnt/…/shared_bench/terminal-bench/runs/tb21_full89_batched_batch_01_of_01_terminus-2_c89_tb21_gpt55_official_medium_c89_single_20260704t195417z_attempt1_medium_c89`
- score **corrected 63/89 = 0.7078651685**; raw reducer `62/89` → **do not quote** (scorer false negative on `headless-terminal`; CTRf 7/7 pass)
- model `gpt-5.5` · scaffold `terminus-2` · effort `medium/default_no_reasoning_effort_arg`
- `c=89` · `timeout_multiplier 1.0` · `timeout_sec 7200` (agent+test) · `attempts 1`
- **KVM: OFF.** `make-doom-for-mips` note reads `qemu timeout=30 / no KVM`.
- gate: `run_rc 0`, `rows 89/89`, `preheat_present 89`, `preheat_tar_verified 89`, `preheat_retagged 248`, `preheat_errors 0`, all transport counters 0
- dataset `…/shared_bench/terminal-bench-2.1-yaml-full89-r7-final-20260703`
- image manifest `.worktrees/tb21-image-fixes-r3/manifests/images/terminal_bench_2_1_full89_p0_closure_r7.yaml` (**178 `@sha256:` refs = 89 unique**, all HEAD-200 against the P0 registry)
- **canonical launcher** `.worktrees/tb21-gpt55-launcher-s55/scripts/stage_tb21_official_gpt55_launcher.sh` — an outer wrapper that *calls* the runner. **Not** either `run_terminal_bench_2_1_*` script.
- review: `DECISIONS.md` 651-675, surface:85 verdict PASS with the mandatory headless-terminal correction
- ⚠️ **The runner that produced this number is unrecoverable.** See §6, C1.
- **Reproduction recipe**: [`experiments/tb21_gpt55/`](../experiments/tb21_gpt55/)

### 3.6 TB2.1 · gpt-5.5 × terminus-2 + `/dev/kvm` · 64.04% `blocked`
- **run_id** `tb21_gpt55_kvm_full89_c89_20260707T164624Z` · same口径 as 3.5 (`c=89`, 7200s, ×1.0, attempts 1)
- native `57/89 = 0.6404494382` · `strict_ready false` · `strict_status blocked`
- `strict_counts {clean_pass 57, external_network_marker 11, infra_fail 1, timeout 1, unresolved 31}`; `token_sum {in 24377067, out 495217}`
- KVM injected into **all 89** task containers via generated compose `devices` (`/dev/kvm:/dev/kvm`)
- diff vs 3.5: `gained 3` (`cancel-async-tasks`, `count-dataset-tokens`, `schemelike-metacircular-eval`), `lost 9` (`build-cython-ext`, `code-from-image`, `compile-compcert`, `db-wal-recovery`, `extract-elf`, `gcode-to-text`, `git-multibranch`, `pytorch-model-recovery`, `torch-tensor-parallelism`)
- ★ `qemu_kvm_related_diff_summary` = `gained 0 / lost 0 / same_resolved 2 / same_unresolved 3`
- an earlier tag `…T161706Z` is **invalid** (launcher omitted the 7200s timeout; agent died at 900s)
- **Verdict**: the −6.74pp is **not attributable to the KVM device**. See §5.6.

### 3.7 TB2.1 · Qwen × terminus-2 · 10.1% `canonical` (with caveat)
- **artifact** `.worktrees/tb21-gpt55-launcher-s55/reports/scores/tb21_qwen_official_medium_c32_stage1_20260705t15481783266492z_medium_c32_scores.{yaml,json,md}`
- model `Qwen/Qwen3-Coder-30B-A3B-Instruct` · scaffold `terminus-2` · effort `medium` · `c=32` · `attempts 1`
- `mean_pass_at_1 0.10112360` = **9/89**; strict partition `clean_pass 9 / unresolved 79 / timeout 1 = 89` (exact)
- served against the **Qwen sglang endpoint** (`:30000`), *not* the gpt relay — confirmed in `command.sh` and `terminal_bench.log`
- failure modes: `83 unset / 3 context_length_exceeded / 2 unknown_agent_error / 1 test_timeout`
- **dual-signed**: `DECISIONS.md` L1480 (surface:86 reconciliation, 15/15 PASS) + surface:85 review PASS
- artifact's own `score_note`: *"single pass@1 compatibility probe; no official TB2.1 Qwen anchor claimed."*
- **Caveat**: TB2.1 has **no official Qwen anchor**. Do not put this on a leaderboard. The nearest reference is TB2.0 `Qwen3-Coder-480B = 23.9%` — different generation, different bench version.

### 3.8 TB2.1 · Qwen × qwen-code bridge · 16.85% `contrast`
- **artifact** `.worktrees/tb21-image-fixes-r3/_coordination/20260625_harbor_bench/reports/scores/tb21_qwencode_native_20260706/summary.{json,md}`
- scaffold `qwen-code-host-bridge` = host QwenCode 0.15.6 + `docker exec` bridge · `c=32` · `attempts 1`
- `raw_accuracy 0.16853932584` = **15/89**
- `strict_counts {clean_pass 15, external_network_marker 2, infra_fail 1, timeout 1, unresolved 73}`
- `status` / `ready` fields **ABSENT** in the summary
- Non-official harness. TTY limitations accepted as a finding, to preserve the native protocol.

### 3.9 TB2.1 oracle infra map
- r5 `tb21_full89_oracle_infra_map_r5_final_20260703.json` — `resolved 79 / 89`, `signoff null`
- r6 `tb21_full89_oracle_infra_map_r6_20260705.json` — `resolved 85 / 89`, signoff `{executor: surface55, reviewer: surface85, review_status: "PASS per orchestrator approval"}`
- r6 note[0] verbatim: *"This is an oracle infra map, not a true-model score."*
- 4 unresolved: `git-multibranch` (protocol), `make-doom-for-mips` (X11), `query-optimize` / `rstan-to-pystan` (pending official baseline)
- ⚠️ A value of `87/89` circulates in project memory; the newest map in this repo is **85/89**. Unreconciled — see §6.

### 3.10 RepoZero · gpt-5.5 · 67.55% raw / 67.0% strict
- runner `tools_repozero_codex_full.py` (internal codex runner) · `c=8` · model `gpt-5.5`
- **raw `all_pass` 127/188 = 0.675531914893617**; **strict 126/188 = 0.6702127659574468**
  (both are metrics of the *same* rejudged run — not two runs)
- strict pass condition: `all_pass==true` AND `codex_returncode==0` AND `codex_timeout==false` AND the generated `.mjs` entry exists
- `category_counts {clean_test_fail 57, strict_pass 126, timeout 5}` · `rescue_all_pass 74 / rescue_cases 128` · `retained_original 60`
- reconciled in ledger: `DECISIONS.md` L1534 — surface:86 ACCEPT ✓
- artifacts `reports/scores/repozero_gpt55_optionb_188_rejudged_20260705.{yaml,json,md}` · `sha256` **ABSENT** · `evidence_consistent` key **ABSENT**
- **Mandatory caveats** (verbatim from the artifact): *"not a 400-case official RepoZero leaderboard score"*; 188-case option-b rescue subset; zero-token rejudge (no LLM judge); single run.
- ⚠️ run_root lives on `swe_dev2` **local disk** — the disk that filled twice. See §5.3.

### 3.11 SWE-bench Multilingual · gpt-5.5 × mini · 73.4% clean
- `runs/swemultilingual_v21_full300_gpt55_high_podb_20260706T233447Z` · `c=50` · single-attempt pass@1
- **clean 201/274 = 73.4%** `canonical` · **raw 201/300 = 67.0%** `forbidden`
- 26 Gradle tasks scored false-zero: `lucene 9 / druid 5 / gson 9 / javaparser 2 / rxjava 1`
- per-language (ours vs official `gpt-5.2-high`): Rust 81.4 (74.4) · JS/TS 79.1 (69.8) · PHP 76.7 (69.8) · C/C++ 75.0 (73.8) · Ruby 70.5 (63.6) · Go 61.9 (52.4)
- cross-language degradation ≈ −5 pt (official: −6.1 pt)
- only a `.md` artifact exists; no `.json`/`.yaml` sibling; dataset path **ABSENT**
- See §5.5 for why the raw number's match to the anchor is a coincidence.

### 3.12 TB2.1 · gpt-5.5 × terminus-2 · 59.55% re-measurement · `forbidden`
**The first run card carrying all 13 mandatory fields.** Also the first one where fields 10–13 were the
difference between a defensible verdict and a fabricated one.

| # | Field | Value |
|---|---|---|
| 1 | `bench` | Terminal-Bench 2.1, 89 tasks |
| 2 | `model` | `gpt-5.5` |
| 3 | `harness` | `terminus-2`, effort `medium` (default; no `reasoning_effort` arg passed) |
| 4 | `score` | **53/89 = 59.55%** (`accuracy = resolved/total`, computed independently of `ready`) |
| 5 | `run_root` | `runs/terminal_bench_2_1_official_gpt55_poda/tb21_gpt55_repro_medium_c89_single_20260709t121819z/medium_c89/attempt_1/…` |
| 6 | `results` + `sha256` | `results.json` under the tb artifact dir · digest recorded in the run report |
| 7 | `image` | `terminal_bench_2_1_full89_p0_closure_r7.yaml` — **89/89 unique `@sha256:` digests**, all HEAD-200 against the P0 registry; `preheat retagged=248` (**byte-identical to canonical**) |
| 8 | `trace_manifest` | **ABSENT** — traces exist (`sessions/{agent.cast,agent.log,tests.log,tests.cast}`) but are not indexed. §6. |
| 9 | `status` | **`forbidden`** (verdict rule v3 §0, clause 3) |
| 10 | `script_digests` | launcher `stage_tb21_official_gpt55_launcher.sh` (s55 worktree) → r3 privileged runner; **12-entry dependency gate green**. ⚠️ runner is git-untracked; the version that produced canonical `70.8%` no longer exists. §6 C1. |
| 11 | `serving_config` | via relay, not sglang — see field 12 |
| 12 | `relay_upstream` | endpoint `http://100.96.122.87:18540/v1` · **upstream `45.78.67.178:2053`** (canonical used `176.122.167.162:2053`; **the endpoint field cannot see this**). ⚠️ Relay injects ~5085 tokens of hidden prompt (`cached_tokens=4864`) and appears to ignore `max_tokens`; whether `reasoning_effort` reaches upstream is **unverifiable** from the response body. |
| 13 | **`llm_health`** | `total_calls 2266` · `retry_exhausted 125` · `http_5xx 117–120` · `http_429 5` · **`hard_fail_rate 5.52%`** · baseline: `0/1215 = 0.00%` |

**Strict counts (this run / canonical):**
`resolved 53/62` · `unresolved 36/26` · `parse_error 0/1` · `infra_fail 0/0` · `timeout 0/0` ·
`external_network_marker 12/10` · `token in 22,043,936 / 24,629,709` · `out 484,360 / 504,006` ·
`status blocked / blocked` (mechanically guaranteed — §5.12c).

**Like-for-like:** canonical's board figure `63/89` = raw `62` + a hand-correction of the
`headless-terminal` scorer false-negative. This run's `headless-terminal` resolved cleanly, needing no
correction. Same-basis delta: **`53 − 63 = −10` tasks = `−11.24 pp`**.

**Declared deviations (5):** relay IP `.22→.87` · `kvm_device_off` (guard against the runner's
`TB21_ENABLE_KVM_DEVICE=1` default) · `run_id_freshness` · `env_seam_repo_root_reset` (F2) ·
cleanup-helper reset. Plus the **relay upstream change**, reinstated as a deviation after a `c=1` probe
was shown insufficient (§5.11).

**Burst timing:** 122/125 failures fell inside `[12:18:28Z, 12:31:08Z]` — the first 12m40s, the c89 ramp
(12:22 → 74 errors at 85 live agents). The remaining **3 occurred with exactly one agent alive**
(13:57–13:59), proving a second, concurrency-independent fault mode. Ramp-limiting explains 97.6%, not 100%.

**Attribution:** exactly **1** of the 125 is attributable — `feal-linear-cryptanalysis`, whose
`agent-logs/episode-N/debug.json` carries the only `Error code: 503` among the run's 1668 such files.
It died `unknown_agent_error` after 99.4 min without reaching its 7200 s ceiling, and appears in the
`lost` set. The other 124 are unattributable — not for lack of data, but because `debug.json` is
overwritten per episode, so a failure a retry survives leaves nothing behind. Corrected classification:
`ATTRIBUTABLE_ONLY_WHEN_THE_EPISODE_DIES`.

> This paragraph previously claimed **3** attributable, argued *by exclusion* from the fact that those
> three landed when one agent was alive. The right task, the wrong count, and an inference standing
> where a file was. See the retraction in §5.12. Note also that `unknown_agent_error` alone proves
> nothing about the relay: two canonical Qwen tasks died that way from a plain 400.

Between-run diff: `gained 3 (real) / lost 13`, of which 8 overlap the KVM round's losses — i.e.
threshold-variance tasks. **No task other than `feal` can be linked to a relay failure.**

**Dual sign-off:** surface:85 (score + attribution) and surface:86 (independent recompute from raw
artifacts + reducer source, *not* a restatement — the two lanes wrote to different filesystems and never
saw each other's reports). 86 **refuted two orchestrator claims**: that `blocked` implies an invalid
score, and that the extra ~1051 calls were pure retries (`8.4 > 8` retry ceiling). Both retractions are
recorded in §5.12.

---

### 3.13 SWE-V · Qwen-Coder × qwen-code · 48.4% re-measurement

| Field | Value |
|---|---|
| `run_id` | `swev_qwencode_full500_surface55_20260709t160554z/full500_c20` |
| `bench` / `dataset` | SWE-bench Verified · `princeton-nlp/SWE-bench_Verified` `test` |
| `model` | `Qwen/Qwen3-Coder-30B-A3B-Instruct` — **verified by `model_path`, not by the `model` field** |
| `harness` | `qwen-code 0.15.6`, `c=20`, `attempts=1`, `reasoning_effort` unset |
| `serving_config` | `:30001` · `tp=2` · `ctx=262144` · `mem_frac=0.85` · `fa3` · `qwen3_coder` · sglang `0.5.13` |
| `relay_upstream` | none — self-hosted sglang |
| `llm_health` | `infra_class = 0` |
| `score` | **242/500 = 48.4%** · conservative `240/500` · **never `240/496`** |
| `results.jsonl` | `132e8a26…` (canonical) / this run recomputed from artifacts |
| `status` | **`reproduced`** — dual-signed |

**Dual review.** Two auditors, each told to prove the score fake and to stamp only on failure. They
never saw each other's report — they were writing to different filesystems, which began as an
orchestration bug and turned out to be the property that made the review independent.

Auditor A audited the run **live**, at 478 rows, and began by verifying `run_id` against
`run_manifest.json` rather than trusting the score — a habit this table earned the hard way, since
`10.11%` appears on two entirely unrelated runs (`gpt-5.4-mini c=89` and `Qwen c=32`, both 9/89) and
the coincidence once fooled its author. Auditor B audited after completion, at 496 rows, and
recomputed `resolved` from the harness's own `resolved_ids` rather than from `eval_rc`.

Auditor A returned `INSUFFICIENT_EVIDENCE` on one line — the exact `ps -o args` match against the
serving process — with this note:

> No discrepancy was found — I simply could not perform the exact process-cmdline comparison the
> brief requested. What is missing: SSH access to the sglang host.

It had discovered that the run host has no GPU at all (`nvidia-smi` empty) and declined to `curl`
the live serving endpoint rather than risk perturbing the run. **That is what the verdict is for.**
Auditor B, which did have a path to the serving host, closed the line independently: `PID 673`,
`--port 30001 --model-path .../Qwen3-Coder-30B-A3B-Instruct --tool-call-parser qwen3_coder`, running
since `2026-07-09T08:24 UTC`, spanning the entire run window.

**Denominator.** `results.jsonl` holds 496 rows, not 500. Four instances finished their tests and were
then dropped: `full500_qwencode_orchestrator_v21.py:912-921` routes `eval_error`/`infra_error` through
`preserve_failure` + `append_event` but **never `append_score`**. The stack top is
`swebench/harness/reporting.py:107 make_run_report → containers.list → docker.errors.NotFound: 404 No
such container` — a cleanup race *after* the tests ran. Recovered from their `report.json`: two are
genuinely resolved (`django__django-11276`, `sympy__sympy-19346`), two are not.

`240/496 = 48.39%` and the honest `242/500 = 48.4%` differ by 0.01 pt. **Had nobody opened those four
`report.json` files, the number would have been right and the denominator wrong, permanently and
invisibly.** The bug under-counts; a bug that over-counted would have been caught by its own
implausibility. This one hides behind a plausible answer.

**Anti-cheat.** 17 resolved instances touched a test file. All 17 are void: the harness runs
`git checkout <base_commit> <testfile>` and re-applies the gold `test_patch` before evaluating
(`instances/django_u_django-13821/eval/.../eval.sh`). Empty patch yet resolved: **0/496**.

**Serving deviation.** The stack differs from the 2026-07-05 canonical (whose host,
`100.103.228.120`, is dead). This is a re-measurement under today's environment, not a strict
reproduction. It is worth stating plainly that **the aggregate landed within one task of canonical
anyway**, while individual trajectories on TB2.1 were shown to diverge deterministically under the
same serving change. Trajectory instability and score instability are not the same quantity.

---

### 3.14 SWE-V · Instruct-2507 × qwen-code · 21.6% `pending`

| Field | Value |
|---|---|
| `run_id` | `swev_instruct2507_qwencode_full500_poda_20260709t183239z` |
| `model` | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| `harness` | `qwen-code 0.15.6`, `c=16`, `attempts=1` |
| `serving_config` | `:30000` · `tp=2` · `ctx=262144` · `mem_frac=0.85` · `fa3` · **`tool_call_parser=qwen`** · sglang `0.5.13` |
| `script_digests` | `SHA256SUMS` + `SHA256SUMS.prelaunch` |
| `runner_rc` | `0`, `finished_utc 2026-07-09T23:39:21Z` (in `logs/runner.rc`, **not** at the run root) |
| `score` | **108/500 = 21.6%** · conservative `107/500` · **never `107/498`** |
| `anchor` | ≈25.7% — nebius's reported figure for this base model |
| `status` | `pending` — audit in flight |

**Model identity, established four ways.** `get_model_info` and `get_server_info`, captured both before
and after the run, all four report `model_path = .../Qwen3-30B-A3B-Instruct-2507`. This is not
ceremony: sglang echoes whatever `model` string you send it (§1.5), so a run pointed at the wrong port
would have produced a flawless-looking trace of the wrong model.

**Denominator, again.** Two instances dropped, same 404 cleanup race, same missing `append_score`.
`django__django-12050` is a **real resolved** — `report.json` gives `FAIL_TO_PASS 1/1`,
`PASS_TO_PASS 10/10`, and its `patch.diff` is 649 bytes. `matplotlib__matplotlib-23299` has no
`report.json` and is counted unresolved. **The defect has now reproduced independently on two runs with
an identical stack top. It is systematic, not incidental.**

#### The number that has to be explained before this row can be quoted

| run | rows | `patch` | `no_patch` | `no_patch` rate | resolved | score |
|---|---:|---:|---:|---:|---:|---:|
| Coder, **2026-07-10** (this comparison) | 496 | 490 | **6** | 1.21% | 240 → 242 | 48.4% |
| Instruct-2507, **2026-07-10** | 498 | 361 | **137** | 27.51% | 107 → 108 | 21.6% |
| *Coder, canonical 2026-07-05* | *500* | *497* | *3* | *0.60%* | *243* | *48.6%* |

Same bench, same harness, same serving host, same day: `no_patch` rises **23×**.

> **Correction.** This table first shipped comparing Instruct-2507's `137` against the *canonical*
> Coder run's `3/500`, yielding "45×", while taking `242` and `48.4%` from the 2026-07-10
> re-measurement — two different runs in one row. The like-for-like figure is **23×**. The direction
> of the finding is unchanged and the conclusion does not depend on the factor; the published number
> was still wrong. Mixing runs is precisely the failure §0's search rule exists to prevent, and the
> author committed it while writing the section that warns about it.

Two readings, and they are not close in consequence:

- **Model.** Instruct-2507 is not coder-tuned. It explores, then stops without producing a diff. Then
  21.6% is a capability figure, sits plausibly beside nebius's 25.7%, and the row is `canonical`.
- **Scaffold.** `:30000` runs `--tool-call-parser qwen`; qwen-code speaks the `qwen3_coder` dialect. If
  a material share of those 137 trajectories emit **zero parsed tool calls**, then 21.6% measures the
  parser and the row is `forbidden`.

A three-task protocol probe (§5.13) already showed tool calls are parsed and executed — `12` `tool_use`
blocks across `3/3` trajectories, running `glob`, `grep_search`, `read_file`, `edit`. That rules out a
*total* mismatch. It does not rule out a partial one, and 3 tasks cannot speak for 137.

#### The census

All 137 classified, not sampled:

| | count | |
|---|---:|---|
| (a) zero tool calls — protocol/parser failure | **0** | the hypothesis this audit existed to test |
| (b) tool calls issued, no diff produced | **94** | |
| (c) rollout or request timeout | 13 | 8 × `ROLLOUT_TIMEOUT after 3000s`, 5 × request-level 483 s |
| (d) crash / API 400 at the context ceiling | 30 | see below |
| (e) voluntary stop | 0 | |
| | **137** | |

Two trajectories *do* contain literally zero tool calls. The auditor traced both to a 483-second
serving timeout on the first request and filed them under (c) rather than (a) — the distinction being
that the parser never got a response to fail on. Even taken as (a), the count is 2/137, and the
scaffold reading dies either way.

So Instruct-2507 calls tools, reads code, edits files. It does not converge. It issues tool calls and
produces no diff 94 times, and talks until it overruns its context 30 times. Coder converges. That is
the 45×.

`eval` genuinely ran: **42,456 individual unit-test executions**. `resolved` is taken from the
harness's `resolved_ids`, not from `eval_rc`. Zero resolved instances have an empty patch; zero touch
a test file. Model identity was re-probed 31 times across the run.

#### The fourth mechanism

`context_length = 262144`; the scaffold passes `max_output_tokens = 65536`. The 400s fire near 228K
input tokens, which matches none of the three obvious ceilings:

```
262144 − 65536 = 196608     no
262144                      no
262138                      no   (sglang's tokenizer-manager path reserves 6)
```

Three candidate ceilings, none of which produces the observed number, means a fourth exists. The
second audit found it:

```
229376 = 262144 − 32768
```

The effective output reservation is **32768 — half the configured 65536**. The evidence is direct
rather than inferential: the largest input the server ever accepted in the whole run is **229,363**
tokens; nothing above 230,000 was accepted; and a **226,271**-token request returned `200 OK`, which
refutes the 196,608 squeeze outright. The client sees `[API Error: 400 status code (no body)]`; the
server raises it at `serving_chat.py:938 create_error_response`.

**And the causal story inverts.** Those 30 tasks did not die because `max_output_tokens` squeezed
their input budget. They died at 229,376 because Instruct-2507 fills a context that Coder, on the same
host against the same ceiling, barely approaches. The configuration contributes the 32K reservation;
the model contributes the other 229K. This is capability, not configuration — and the orchestrator's
suspicion that it was configuration was wrong.

#### Dual review

Both auditors worked from raw artifacts, blind to each other. Both endorse. Their censuses agree
exactly where it matters and differ where judgement enters:

| | auditor A | auditor B |
|---|---:|---:|
| **(a) parser failure** | **0** | **0** |
| (b) tool calls, no diff | 94 | 90 |
| (c) timeout | 13 | 12 |
| (d) crash / 400 | 30 | 31 |
| (e) voluntary stop | 0 | 4 |
| | 137 | 137 |

The load-bearing number — the one the whole audit existed to produce — is the one they agree on. The
rest is where a trajectory that stops after a failed edit could be filed under (b) or (e), and
reasonable auditors put it in different columns. **Two independent censuses that agreed on everything
would have been evidence of collusion or of a shared script, not of truth.**

Both traced the two literally-zero-tool-call trajectories (`pytest-5787`, `pytest-5809`) to the same
place, separately: `peak_input = 0`, `num_turns = 1`, `duration ≈ 483 s`, literal
`Request timeout after 483s`. No response ever arrived, so no parse could fail. `(a) = 0` survives.

#### ⚠️ Caveat: this is a lower bound

`43/500 = 8.6%` of the benchmark ended at an envelope limit — the 229,376-token ceiling, a rollout
timeout, or a crash — rather than at the model's judgement. One further genuine resolve
(`django__django-12050`) was silently discarded by the denominator defect. **21.6% is the score
Instruct-2507 achieves under this scaffold configuration. It is not an upper bound on the model.**

Status `canonical` for this cell, with that caveat attached to the number wherever it is quoted.

---

## §4 Reproducible example

[`experiments/tb21_gpt55/`](../experiments/tb21_gpt55/) reproduces the TB2.1 `canonical` cell (§3.5).

```
experiments/tb21_gpt55/
├── config.yaml   # every parameter, its source file, 4 recorded conflicts, 3 declared deviations
└── run.sh        # --dry-run | --preflight-only | --execute
```

Self-checks that gate it: `bash -n` passes; `yaml.safe_load` passes; `--dry-run` prints 12
fields that match `config.yaml` verbatim; `--preflight-only` runs read-only against Pod A and
**hard-blocks with `exit 24`** when the closure-gate helper is missing rather than silently
downgrading the gate.

### The three declared deviations

1. **`relay_ip`** — `100.96.122.22` → `100.96.122.87`. `dev` was restarted 2026-07-09 ~15:59 and its pod IP moved.
2. **`kvm_device_off`** ★ — today's runner has `export TB21_ENABLE_KVM_DEVICE="${TB21_ENABLE_KVM_DEVICE:-1}"` at line 44, i.e. **KVM defaults ON**. The canonical launcher never set it, and the canonical run was **no-KVM**. Running as-is would silently reproduce the 2026-07-07 `64.04%` instead of `70.8%`. `run.sh` therefore sets it to `0` explicitly and declares it.
3. **`run_id_freshness`** — reusing the canonical `run_id` would overwrite the retained 70.8% artifacts; `run.sh` refuses.

> Because of §6 C1, any execution of this recipe is a **re-measurement under today's
> environment**, not a byte-identical reproduction. Say so when quoting its output.

---

## §5 Overturn log

Seven times a number that looked finished turned out to measure something other than the model.

### 5.1 `docker exit-125` — SWE-V 43.6% was never a model score
211 instances hit `docker exit-125` on container start at `c=100` (the agent outran image
loading) and were recorded as `no_patch`. The agent never ran on them.
**Fix**: per-instance image preflight, `--pull=never`, preheat, and reclassify `125` as `INFRA`.
**Became** **77.2%**.
**Lesson**: when a score is low, check the `no_patch` rate *before* blaming the model.

### 5.2 Scaffold mismatch — SWE-V 23.4% measures the format
498/498 Qwen trajectories emitted multi-tool-call format; `mini`'s bash-only parser rejects it.
The number is real but it is not a capability number. The representative Qwen score is **48.6%**
via the native `qwen-code` scaffold.

### 5.3 `/tmp` inode exhaustion — RepoZero, twice
`/tmp` ran out of **inodes**, not bytes — 26 GB free while `df -ih` showed 100%. 128 cases died
`rc=126 no-space`. During the rejudge the ceiling was hit **again** and the on-disk
`case_result.json` evidence was overwritten.
**Fix**: watch inodes (`df -ih`), dual watermark guard (bytes *and* inodes < 10% → stop), atomic
`case_result` writes, and — the durable fix — an **evidence-consistency assertion in the reducer**:
the final score must be independently recomputable from on-disk per-case artifacts.
**Lesson**: a one-shot disk cleanup gets refilled by the run itself.

### 5.4 Strict gate caught a missing artifact — TB2.1 × Qwen, first round
`artifact_manifest.json` was missing → `status=blocked`, **no fake number emitted**.
After a model or scaffold swap, preflight the whole artifact chain.

### 5.5 Gradle false-zero — Multilingual's accidental anchor match
Inside `--network none`, `gradlew` tries to download `gradle-wrapper.jar` → timeout → tests never
ran → 26 tasks across 5 Java repos scored a **false zero**.
**The trap**: gpt-5.5 actually beat the official anchor by **+7–9 pt in every healthy language**.
The 26 false zeros cancelled that lead almost exactly, landing raw at 67.0% next to the 66.7%
anchor. **The match was a coincidence.**
**Lesson**: always split per-language. An aggregate that lands perfectly on the anchor is a red
flag, not a validation. And offline-ising a bench means proving the **build toolchain** is
self-contained, not merely that the image exists.

### 5.6 `/dev/kvm` did not do what everyone assumed — and its report proves it
The 2026-07-07 run mounted `/dev/kvm` into all 89 containers expecting to recover the qemu-class
tasks. It scored **57/89 (64.04%)**, `−6.74pp` vs baseline. The intuitive story — "KVM broke
something" — is **wrong**, and so was the prior story — "KVM will fix the qemu tasks".

The report's own `qemu_kvm_related_diff_summary` reads `gained 0 / lost 0 / same_resolved 2 /
same_unresolved 3`. Per task:

| qemu/kvm task | baseline | with `/dev/kvm` |
|---|---|---|
| `qemu-alpine-ssh` | pass | pass |
| `qemu-startup` | pass | pass |
| `install-windows-3.11` | fail | fail |
| `make-doom-for-mips` | fail | fail |
| `make-mips-interpreter` | fail | fail |

`gained ∩ qemu = lost ∩ qemu = ∅`. The device changed **nothing** for the only tasks it could
affect. Two qemu tasks already passed *without* KVM; three failed *with* it.

**Attribution**: the delta is entirely non-qemu tasks flipping both ways between two
single-sample runs — i.e. **pass@1 sampling variance**. The artifact itself anticipates this:
`official_reference` states *"one pass@1 sample, so ±4-5pp sampling drift is expected"*, and
`infra_note` records that KVM/launch gates were clean and the failures were *"task-run outcomes,
not Docker transport failures."*

The run stays `blocked` (`ready=false`). Canonical remains **70.8%**.

**Engineering hazard uncovered while writing this**: the runner's line 44 sets
`TB21_ENABLE_KVM_DEVICE` to **1 by default**. The canonical launcher never set it. Anyone
re-running "the canonical recipe" today, unchanged, silently reproduces 64.04% and thinks they
failed to reproduce 70.8%. See §4, deviation 2.

### 5.7 `external_network_marker` is a substring heuristic, not evidence of egress
Source: `.worktrees/tb21-image-fixes-r3/scripts/tb21_strict_batch_summary.py` (L22-31, L123-132).

```python
NETWORK_PATTERNS = ("Temporary failure resolving", "Could not resolve host",
  "Failed to establish a new connection", "Failed to fetch http", "httpproxy-headless",
  "archive.ubuntu.com", "deb.debian.org", "github.com", "/simple/")

def network_markers(text):
    for line in text.splitlines():
        if any(pattern in line for pattern in NETWORK_PATTERNS):   # plain substring, not a regex
            ...
```

It is a **notes annotation only** — it does not gate resolution. Of the 11 marker rows in the
KVM run, **5 also resolved**. Worked examples, all on-disk:

- `sam-cell-seg` (**resolved**): the marker fired on a `torch.load()` `FutureWarning` whose text
  contains `github.com/pytorch/pytorch/blob/main/SECURITY.md#untrusted-models`. No network call.
- `count-dataset-tokens` (**resolved**): a printed `Repository: https://github.com/…` line.
- `fix-git` (**resolved**): a git reflog line `clone: from https://github.com/…`.
- `compile-compcert`, `code-from-image`: markers from `curl: (6) Could not resolve host: github.com`
  and a pip `NewConnectionError` — that is egress **failing**, i.e. **proof the offline isolation
  is working**, the exact opposite of a leak.

**A marker never implied egress.** Any count of markers must not be read as a count of leaks.

### 5.8 The author asserted a run did not exist. It did, and it was dual-signed.
On 2026-07-09 the maintainer of this document concluded that the `Qwen × terminus-2` TB2.1 run
did not exist and that its 10.1% had been mis-attributed from a `gpt-5.4-mini` run — on the
strength of an exhaustive filename/content grep that returned nothing.

Both premises were false:

- The run exists: `.worktrees/tb21-gpt55-launcher-s55/reports/scores/tb21_qwen_official_medium_c32_stage1_…scores.yaml`.
  Its `command.sh` invoked `--model openai/Qwen/Qwen3-Coder-30B-A3B-Instruct` against the Qwen
  sglang endpoint; its `terminal_bench.log` never mentions `gpt-5.4-mini`.
- It was dual-signed on 2026-07-06: `DECISIONS.md` L1480 records surface:86's reconciliation
  (15/15 PASS) and surface:85's review (PASS).
- The coincidence that seeded the error: **two independent terminus-2 runs each scored exactly
  9/89** — `gpt-5.4-mini` (xhigh, c89) and `Qwen3-Coder-30B` (medium, c32) — on task sets that
  overlap in only **1 of 9** resolved tasks.

The same reasoning error had also produced a false claim that RepoZero's 67.55% "has no
artifact"; the ledger records its reconciliation at L1534.

**Root cause**: trusting an agent's "exhaustive grep found nothing" over the ledger, and
searching only one of the repo's worktrees.
**Fix**: the search-order rule in §0. This entry exists so the next maintainer does not repeat it.

### 5.9 Vendoring a script is not vendoring its behaviour
While preparing the §4 recipe we needed `build_tb21_full89_closure_matrix.py`, which exists only
in the main repo, inside a worktree that lacks it. Its mtime (`2026-07-02`) predates the canonical
run (`2026-07-04`), which appeared to prove that copying it would restore the canonical behaviour.

**Copying it broke the gate.** The script anchors one of its inputs to its own location:

```python
DEFAULT_REPO_ROOT    = Path(__file__).resolve().parents[1]                     # line 19
DEFAULT_R2_SUMMARY_DIR = <repo>/_coordination/.../tb21_closure_full89_r2       # line 32
```

That directory holds 31 per-task summaries, and `load_closed_runtime_hf_assets()` **silently
returns `[]`** when it cannot find them. Copy the script into a worktree, and `__file__` moves
with it: two `hf_asset` tasks (`count-dataset-tokens`, `mteb-retrieve`) flip from `closed` to
`open`, the gate returns `ready=false`, and the runner exits `rc=24` before the batch loop.

The diagnosis was settled by a control experiment (read-only, zero containers): the **same script,
same dataset, only the file's location changed** →

| Script location | gate `open` |
|---|---|
| main repo | 0 |
| copied into the worktree | 2 |
| temp dir symlinked to main repo | **0** |

Of the builder's four `__file__`-anchored defaults, three are overridden by explicit runner flags;
`DEFAULT_R2_SUMMARY_DIR` is the only one **anchored to `__file__` and not overridable from the
CLI**, so it is the only one that fires. The sibling `tb21_runtime_closure_static_gate.py` contains
**zero** `__file__` references and copies safely.

**Fix**: symlink, not copy. `Path(__file__).resolve()` follows symlinks, so the anchor returns to
the main repo. Downgrading the gate (`TB21_ALLOW_OPEN_RUNTIME_CLOSURE=1`, or setting it to `0`) was
rejected — it would have turned a real infra defect into a silent, undeclared deviation.

> **Rule.** Before vendoring or relocating any script, grep it for `__file__` / `Path(__file__)`
> and for relative-path defaults. An input that is both `__file__`-anchored and not CLI-overridable
> makes the script **location-dependent**: identical bytes, different behaviour. mtime and sha256
> prove content identity; they prove nothing about runtime behaviour.

This also refines §6 C2: vendoring the reproduction chain into this repo is necessary, but a
straight `cp` is not sufficient. Each component must be audited for location dependence first.

### 5.10 Three implicit couplings, found by trying to re-run one benchmark
Restoring the §4 recipe surfaced three distinct latent defects in the TB2.1 harness. All three
are the same disease — a value silently derived from *where a file sits* or *how a string is
spelled* — but they fail in increasingly nasty ways.

#### (a) `__file__` anchoring — fails immediately (§5.9)
Covered above. `build_tb21_full89_closure_matrix.py` anchors a data directory to its own location.
Fixed by symlink; the gate then reproduced `closed=89 / open=0`, **field-identical to canonical**.

#### (b) `$REPO_ROOT` derivation — fails immediately, three times over
The 2026-07-07 patch changed the runner to derive `REPO_ROOT` from *its own script path*, which
points into a worktree. Three call sites broke:

```bash
# runner L61-62 — has a ${VAR+x} seam, but the default is wrong
if [[ -z "${TB2_RUNTIME_CLOSURE_REPAIR+x}" ]]; then
  export TB2_RUNTIME_CLOSURE_REPAIR="$REPO_ROOT/scripts/repair_tb21_full89_runtime_closure.py"
fi
# runner L53 — unconditional export, not gated at all
export TB_DOCKER_FORCE_CLEANUP_HELPER="${TB_DOCKER_FORCE_CLEANUP_HELPER:-$REPO_ROOT/scripts/cleanup_tb21_worker.sh}"
# runner L590/610 — bare relative path, no seam (gated by TB21_RUN_CLEANUP_HELPER, `|| true`)
```

The first one is fatal: the shared runner calls `python3 "$TB2_RUNTIME_CLOSURE_REPAIR" --execute`
under `set -euo pipefail`, the file is absent in the worktree, and Terminal-Bench is **never
invoked** — `docker ps -aq` returns 0, so there is not even an `exit-125` to point at.

**Fixed by env-seam reset**, not by moving files: the runner already offers `${VAR+x}`, so passing
an explicit path to the main-repo script restores canonical behaviour *and* leaves that script's own
two `__file__` anchors in their original location. (Copying it would have re-created defect (a).)

A sha256 audit of every script the runner touches proved that all the relative-called scripts are
byte-identical across both roots — which collapsed the fix space: "override the env" and "override
`REPO_ROOT`" are behaviourally equivalent, and only the repair path actually differs.

#### (c) Case-sensitive `run_id` — **fails 70 minutes later, after the whole run completes**
```
runner:         lowercases TB21_FULL_TAG, then builds run_root from it
stage launcher: uses the ORIGINAL tag for record_attempt + `touch attempt.done`
```
Supply a `run_id` containing an uppercase character and the two paths diverge. Nothing complains.
All 89 tasks execute. Then, at the very end, the launcher trips `set -e` on the `touch`,
**`finalize_scores` never runs, and the entire 2–3 hour run yields no score.**

The canonical run never hit this **only because its `run_id` happened to be all-lowercase.**

**Fixed** by lowercasing the stamp and adding an assertion `^[a-z0-9_-]+$` on `run_id`, with a
negative test (`--run-id BAD_UPPER_Z` → blocked). Luck became a guarantee.

#### The generalisation
> Implicit couplings that fail **immediately** are cheap: the gate catches them, nothing is wasted.
> Implicit couplings that fail **after the workload completes** are the expensive ones — they burn
> the entire run and produce no evidence. When auditing a harness, hunt for the second kind first:
> look for any value that is derived (lowercased, joined, resolved) on one code path and consumed
> raw on another.

#### What we did about it, permanently
The one-off audit was frozen into a **dependency gate** in `run.sh`, running on both the
`--preflight-only` and `--canary` lanes:

- it resolves **12** scripts the runner and shared-runner reference, under the *effective* env;
- `required` missing → `exit 24`, hard block;
- `latent` missing (currently gated off, e.g. `cleanup_tb21_worker.sh` behind `TB21_RUN_CLEANUP_HELPER=0`)
  → warn, printing the expected path, the variable it derives from, and the current gate value;
- **flip the gate to its enabling value and `latent` auto-promotes to `required`**;
- two negative tests prove it: pointing the repair path at `/nonexistent` → `exit 24`; setting
  `TB21_RUN_CLEANUP_HELPER=1` while the helper is absent → `exit 24`.

### 5.11 A probe that proved the wrong thing
The canonical run's relay pointed upstream at `176.122.167.162:2053`; today's points at
`45.78.67.178:2053`. Both are reached through the same `:18540` endpoint URL, so the
`relay_endpoint` field **cannot see this difference** — it would have shipped as an undeclared
environment change.

Rather than declare an unverified deviation, we A/B-tested the two addresses with an identical
request and got an elegant-looking result:

| field | `176.122…:2053` | `45.78…:2053` |
|---|---|---|
| `model` / `content` / `finish_reason` | `gpt-5.5` / `PING` / `stop` | identical |
| `prompt_tokens` / `completion_tokens` | 5092 / 5 | identical |
| **`prompt_tokens_details.cached_tokens`** | **4864** | **4864** |

`cached_tokens` matching to the digit means both requests hit the **same prompt cache**, and a
prompt cache is per-backend. Conclusion: two ingress IPs, one backend. The difference was
downgraded from a deviation to an `informational` note.

**That conclusion was true and useless.** The probe ran at `c=1`. It established **backend
identity**. It said nothing about **ingress capacity or rate limiting** — and capacity is exactly
what a benchmark at `c=89` consumes.

The full-89 run then produced, in its own `run.log`:

| | canonical (`176.122`, c89) | today (`45.78`, c89) |
|---|---:|---:|
| `ServiceUnavailableError` (503) | **0** | **117** |
| `RateLimitError` (429) | **0** | **5** |
| `Unknown Error in LLM interaction` | 1 | 122 |

Same harness, same concurrency, same ~5k injected system prompt. The only variable was the ingress
IP. All 122 were `tenacity` retry-exhaustion — hard failures reaching the agent, not transient
blips. (The burst was pulse-shaped and had ended by the run's tail; a live 3/3 `HTTP 200 @1.9s`
probe confirmed the endpoint was healthy again.)

**`cached_tokens` is an identity fingerprint. `503`/`429` are throughput phenomena. Identity
equivalence does not imply capacity equivalence.**

The `relay_upstream` entry was reinstated as a **deviation**, worded:
> backend identity verified equivalent (c=1 A/B, matching `cached_tokens`);
> **ingress capacity / rate-limiting unverified at c=89 — and empirically NOT equivalent this run.**

This makes the run's score **not同口径-comparable** to the canonical `63/89`.

> **Rule (superseding the naive version).** When an environment field cannot distinguish two
> configurations, designing a distinguishing probe is necessary but **not sufficient**. The probe
> must exercise the **operating condition the run will actually use**, or it must explicitly state
> which dimension it covers and which it does not. A `c=1` probe cannot vouch for a `c=89` run.
>
> Corollary: name the dimension. "Same backend" ≠ "same latency" ≠ "same throughput ceiling" ≠
> "same rate-limit policy". Each is a separate claim needing separate evidence.

**Note on what is still unknown.** The canonical `5xx=0` is an observation from 2026-07-04. The
relay's capacity may have changed since. So "`176.122` would not 503 today at c89" is *not*
established — it would itself require a controlled test. We record the asymmetry, we do not
extrapolate from it.

### 5.12 The quality gate cannot see the thing that broke the run
A `c=89` re-measurement of TB2.1 hit **125 retry-exhausted LLM failures** (117–120 × `503`, 5 × `429`)
against a relay ingress that had silently changed. The strict gate reported:

```
infra_fail = 0      missing_artifact = 0      timeout = 0      parse_error = 0
```

Everything looked clean. It was not. Reading the reducer source (`tb21_strict_batch_summary.py`)
exposed **three** structural blind spots, each worse than the last.

#### (a) `infra_fail` does not include the LLM layer
```python
infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not in (0, None))   # ~L250
```
125 hard failures at the model-call layer → `infra_fail` stays `0`.

> **Corollary: every historical score in this repo may have been degraded by an invisible LLM-layer
> fault, with no gate ever raising a flag.** And it is not retroactively checkable — those errors live
> only in `run.log`, which is not always retained.

#### (b) `unknown_agent_error` is not `infra_fail` either
One task (`feal-linear-cryptanalysis`) died because its model calls failed outright. In the ledger it is
**indistinguishable from "the model could not solve it."**

#### (c) `ready` requires `unresolved == 0` — so `blocked` means nothing
```python
ready  = bool(total > 0 and clean_pass == total and missing_artifact == 0 and timeout == 0 ...)  # L309
status = "blocked" if (not ready and not allow_oracle_score) else ...                            # L317
```

A real model never clean-passes all 89 tasks. Therefore `unresolved > 0`, therefore `clean_pass < total`,
therefore **`ready` is `False` and `status` is `blocked` for *every* real model run, by construction.**

- The canonical `70.8%` run: `blocked`.
- This `59.55%` run: `blocked`.
- A 3-task canary that happened to pass all 3: `ready=true` — the only way to reach it.

And crucially, **`score` never reads `ready`**: `resolved` (L299), `accuracy = resolved/total` (L318),
and the `score` block (L338) are computed independently.

> **`status=blocked` on a model run carries exactly zero information about score validity.**
> Any rule that rejects a score *because it is blocked* rejects every real run by construction.
> This document's first verdict rule did exactly that — and would have disqualified its own canonical
> baseline. Corrected in §0.

#### What actually disqualifies the number
Not `blocked`. The number is disqualified because **the gate said clean while 125 model calls died**,
and the experiment design cannot quantify the damage:

- `c=89` single-batch ⇒ all 89 tasks sit inside the failure window ⇒ **no control group**;
- most of the 125 failures cannot be tied to a task. Not because the artifacts lack the data, but
  because `debug.json` is **overwritten each episode**: a failure that a retry survives leaves no
  trace. Only a failure that *kills* its episode is still on disk when the run ends.

> **Retraction.** This section previously said per-task attribution was *impossible from disk*, and
> that **3** of the 125 were attributable *by exclusion* (they landed at 13:57–13:59 when one agent
> was alive). Both claims were wrong, and the second was wrong in the more embarrassing direction —
> it was reasoning where evidence was available.
>
> Per-task LLM errors **are** on disk, in `agent-logs/episode-N/debug.json`, which records the HTTP
> error body of every call. Two searches missed it: a `find -maxdepth 4` too shallow to reach it, then
> a grep for the *exception class name* (`ServiceUnavailableError`) in a file that stores the *HTTP
> payload* (`Error code: 503`). Re-scanned with `"Error code: (\d{3})"`:
>
> | run | `debug.json` files | with an error code |
> |---|---:|---|
> | this run | 1668 | **4** → `{503: 1, 404: 3}` |
> | canonical gpt-5.5 | 1214 | **0** — confirms its relay hard-fail truth is 0 |
> | canonical Qwen | 8687 | 5 — **all 400**, i.e. all `content_class` |
>
> The single 503 is `feal-linear-cryptanalysis`. So the exclusion argument reached the right task by
> the wrong route, and the count was 3 when the evidence says **1**. Corrected attribution:
> `ATTRIBUTABLE_ONLY_WHEN_THE_EPISODE_DIES` — 1 of 125.

⇒ Recorded as `forbidden`: *evidence insufficient to quantify, sufficient to disqualify.*
**An epistemic judgement, not a statistical one.** Say which one you are making.

The verdict is unchanged. The argument behind it was defective, and a defective argument for a
correct verdict is still a defect — it would have been reused.

#### A hypothesis that failed arithmetic
This run made 2266 total API calls vs the baseline's 1215, while resolving **fewer** tasks. The tempting
story — "the extra ~1051 calls are the retries behind the 125 hard failures" — **does not survive**:

```
1051 / 125 = 8.4 retries per hard failure
nested retry ceiling = 3 × 3 − 1 = 8
8.4 > 8  ⇒  arithmetically impossible as pure retries
```

Independent recount: ~454 of the extra calls are **additional agent turns** (churn induced by failures),
~597 are **bounded retry/failure overhead**. The `hard_fail_rate = 5.52%` stands; the "doubling is all
retries" narrative does not. *A number that merely looks consistent is not evidence.*

#### The fix (proposed, not yet implemented)
`llm_health` has **two layers**, because the two layers can answer different questions and an earlier
single-layer design conceded ground it did not have to:

```
run-level   (parse run.log)
  total_calls · retry_exhausted · hard_fail_rate · token_sum_vs_baseline
  counted in two columns, never one:
    infra_class    5xx · 429 · connection_error · read_timeout · retry exhaustion
    content_class  400 · tokenizer errors · context_length_exceeded

task-level  (read agent-logs/episode-N/debug.json — already on disk, free)
  llm_error_last_episode
    content_class  always attributable per task
    infra_class    attributable only when the error killed the episode
                   (debug.json is overwritten per episode; survived retries leave nothing)
```

Emitted by a runner-side parser — not the strict reducer, which reads only per-task artifacts, and
not Terminal-Bench itself, which is not ours to change. Exceed an `infra_class` threshold → tag the
score `llm_degraded`. Do not block the run; **taint the number**.

Do not tag on `content_class`. And do not infer a relay fault from `unknown_agent_error`: a task can
die that way from a pure 400. Two canonical Qwen tasks (`tune-mjcf`, `write-compressor`) did exactly
that, reporting `Input length (262143) exceeds the maximum allowed length (262138)` — the same
262,144-token window seen from sglang's tokenizer-manager path, which reserves six tokens. The
canonical Qwen run's `infra_class` count is **0**. Under v4(b) it is not `forbidden`, and it must not
be, because it is this table's own anchor.

**Rule adopted: no re-run happens before `llm_health` lands.** Otherwise the next round is equally blind.

---

### 5.13 The probe was correct. The thing counting its output was not.

`Qwen3-30B-A3B-Instruct-2507` is served with `--tool-call-parser qwen`. `qwen-code 0.15.6` speaks
the `qwen3_coder` tool-call dialect. The predicted failure was a clean one: the server parses no
tool calls, the agent loops without acting, every task scores zero, and every quality gate reports
success — a scaffold/protocol mismatch indistinguishable from "the model is bad at coding".

So a protocol probe was written before the run. It ran three tasks and asked one question:
`tool_calls_emitted_and_parsed > 0`? It reported **zero**, on all three.

The probe specification — written by the orchestrator — said to count top-level `tool_calls` and
`function_call` fields. That is the OpenAI wire format. It is not what the scaffold writes.
qwen-code's `stream-json` nests tool activity inside `message.content[]` blocks typed `tool_use`
and `tool_result`. The counter was looking at a level of the document where the answer never
appears.

Recounted at the right level, the same three trajectories give:

| instance | `tool_use` | `tool_result` | tools actually called |
|---|---:|---:|---|
| `astropy__astropy-14539` | 4 | 4 | `glob`, `read_file`, `glob`, `glob` |
| `django__django-17084` | 4 | 4 | `glob`, `grep_search`, `grep_search`, `read_file` |
| `sympy__sympy-24443` | 4 | 4 | `read_file`, `edit`, `read_file`, `edit` |

`rows_protocol_ok = 3/3`. A direct OpenAI-compatible tool call against the same endpoint returns a
non-empty `tool_calls` array. The protocol works. The hypothesis was wrong, and the probe would
have "confirmed" it.

Had the orchestrator's instruction been followed literally, `0/3` would have been read as
`protocol mismatch → forbidden`, and the only benchmark line in this table with a same-base
training anchor would have been struck before it ran. The engineer running the probe checked what
the zero *meant* before reporting it, found the counter was reading the wrong field, and said so.

Two lessons, and the second is the one that generalises:

- **A negative result from an instrument you have not validated is not a negative result.** Before
  a probe can disconfirm, it must first be shown capable of confirming. A tool-call counter that
  has never seen a *positive* trajectory cannot testify that a trajectory has no tool calls.
- **The layer that reports a metric and the layer that produces it are different layers, and they
  drift.** `tool_calls` is the API's word for it; `content[].type == "tool_use"` is the scaffold's.
  Both are "the tool calls". Only one is where the data lives. Every implicit coupling in §5.10 has
  this shape: a name that survived a layer change while its referent moved.

This is the fourth time in one working session that an instruction from the orchestrating agent was
overturned by the agent executing it — after `blocked` implying an invalid score, after the retry
arithmetic, after `UNRECOVERABLE`. Each was caught the same way: someone declined to report a
number they could not explain.

### 5.14 Three ways to get the denominator wrong, none of which raises an error

Within one night, on one benchmark family, the same quantity was corrupted three different ways.

**By omission.** `full500_qwencode_orchestrator_v21.py:912-921` routes `eval_error` and `infra_error`
through `preserve_failure` and `append_event`, and never calls `append_score`. Instances that finished
their tests and then lost a container-cleanup race disappear from `results.jsonl` rather than being
recorded as unresolved. Six vanished across two runs; three of them were genuinely resolved.

**By reporting.** `results.jsonl` has rows, and the benchmark has a size, and they are not the same
number. `240/496 = 48.39%` and the honest `242/500 = 48.4%` differ by 0.01 pt. The wrong denominator
does not produce a wrong-looking answer. It produces a right-looking one.

**By accretion.** A TB2.1 launch wrote its own preflight summary as JSON into the directory the task
loader globs, and the loader counted it. `dataset_size` became 90. The engineer noticed before any
task ran, stopped the launch, removed only that run's containers, fixed the guard, added eight tests,
and relaunched with `run_metadata` independently confirming `dataset_size=89, task_ids=89, no
pseudo-task`.

The third is the one worth generalising. **An output written beside its input becomes an input.** The
directory was not a directory of tasks; it was a directory of files, and something decided that files
are tasks. Nothing in that chain was wrong on its own.

None of the three raises an exception, fails a gate, or produces an implausible number. The only
defence that caught any of them was someone asking what a number was the denominator *of*, before
dividing by it.

---

---

## §6 Reproducibility gaps (as of 2026-07-09)

An honest list of what a third party could **not** reproduce from this repo today.

### C1 — The canonical TB2.1 runner is gone (HIGH)
`run_terminal_bench_2_1_full89_batched_privileged_offline.sh` is **untracked by git** in the r3
worktree (`git status` shows `??`). Its mtime is `2026-07-07 23:46` — it was **rewritten by the
KVM-passthrough patch**, after the canonical run. **There is no git object for the version that
produced 70.8%, and it cannot be restored.** The r3 HEAD `c42f23c` does not contain the file.

That patch also changed the runner to (a) materialise an effective dataset per tag, (b) rewrite
payload bind paths, and (c) derive `REPO_ROOT` from the runner script path. The effect of (a)–(c)
on a KVM-off run is **unverified**.

⇒ Byte-identical reproduction is impossible. Everything downstream is a **re-measurement**.

### C2 — The whole TB2.1 reproduction chain lives outside git
| Component | Where it lives | Tracked? |
|---|---|---|
| canonical runner | r3 worktree | ✗ (and overwritten) |
| `build_tb21_full89_closure_matrix.py` | main repo only | ✗ (mtime 2026-07-02) |
| `tb21_runtime_closure_static_gate.py` | main repo only | ✗ (mtime 2026-07-01) |
| `stage_tb21_official_gpt55_launcher.sh` (the real launcher) | s55 worktree only | — |
| `tb21_gpt55_official_ledger.py` | s55 worktree only | — |

**This is why the runner could be lost: it was never under version control.** Vendoring this
chain into the repo is the entire purpose of `experiments/`.

### C3 — Everything else
| Gap | Detail |
|---|---|
| Orchestrator not vendored | `full500_model_orchestrator_v2_podb.py` (51 KB) lives in the shared-FS run tree, not this repo. SWE-V full500 cannot be re-run from a clone. |
| Image digest coverage is thin | `bench_registry.yaml` says it outright: `full_benchmark_digest_coverage_is_not_yet_available_for_every_bench`. For SWE-V's 500 images, `p0_digest_pushed = 8`, `p0_registry_digest: null`; the real primary transport is `shared_oci_tar_chunk` (96 fallback tars). TB2.1 is the good case: 89/89 unique digests, all HEAD-200. |
| **Qwen serving is dead** | Both Qwen runs used `base_url http://100.103.228.120:30000/v1`. That sglang server is **down** (probed 2026-07-09). Any Qwen re-measurement necessarily uses a **different serving instance** and must say so. |
| No trace manifests filled | `traces/` holds only its README; `reports/trace_manifest_template.yaml` is an empty template. **No run has a committed trace pointer.** |
| Index gaps | `Qwen × mini 23.4%` and `RepoZero 67.55%` are reconciled in `DECISIONS.md` but were never filed under `reports/scores/`. Evidence exists; the index does not. |
| Multilingual has no machine-readable score | Only a `.md`; no `.json`/`.yaml`; dataset path unrecorded. |
| RepoZero run_root is off shared storage | It lives on `swe_dev2` local disk — the disk that filled twice. |
| Config not first-class | For SWE-V, `c=100` is only inferable from a directory name; `timeout_multiplier` and `n_attempts` are ABSENT in the score artifacts. |
| Oracle count unreconciled | Project memory says `87/89`; the newest map here says `85/89`. |
| `ABSENT` in the TB2.1 recipe | `terminal_bench_version`, `terminus_2_version`, `runner_git_state_at_canonical_time` — recorded nowhere, not invented. |

Closing these is ordinary work, not a footnote.

---

## §7 How this document is built

1. **Ledger first.** Every claim is checked against `DECISIONS.md` before `reports/scores/`.
2. **Adversarial verification.** Load-bearing claims are handed to two independent auditors
   instructed to *refute* them, with access to the same disk and no contact with each other. A
   claim is recorded only if both fail to break it. §5.8 exists because this process caught the
   author's own error before it was published.
3. **`ABSENT`, never invented.** A field with no on-disk source is written `ABSENT`.
4. **Terms over booleans.** Never act on a harness's summary flag without reading how it is
   computed. `ready=false` is mechanically true of every real run; `infra_fail=1` is often just a
   timeout. This rule replaces an earlier "gate over score" rule that this document shipped, and
   which would have disqualified its own baselines. See §5.12(c) and verdict rules v4.
