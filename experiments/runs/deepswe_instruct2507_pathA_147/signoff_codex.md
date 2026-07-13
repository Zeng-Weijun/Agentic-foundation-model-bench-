# signoff_codex.md — Cross-family independent audit: DeepSWE full113 x Qwen3-30B-A3B-Instruct-2507 x qwen-code (Path A)

**Claim under audit:** DeepSWE full113 (Path A: qwen-code CLI agent) x Qwen3-30B-A3B-Instruct-2507 x
qwen-code = **0/113 headline, 0/106 valid-only** (7 `gold_broken` excluded), asserted REAL not a judging
bug. Commit `6c23a02`, branch `evidence/deepswe-instruct2507-pathA-147-20260713`,
`experiments/runs/deepswe_instruct2507_pathA_147/` under
`$BM=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`
(host: `env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`).

## VERDICT: REAL

**0/113 (0/106 valid) is not fake — but this is not a clean bill of health for the evidence bundle's
replay methodology.** Two independent model families both tried hard to falsify the score as a
systemic judging-pipeline artifact and both failed. Both independently found the *same* real
replay/provenance defect (audit-phase reconstruction from `git diff` drops untracked new files) and
both independently proved, via the same underlying mechanism (the original live in-container
verification, which is architecturally immune to that defect), that it cannot be hiding a suppressed
agent success. The Codex-family pass additionally found further genuine defects (timeout/quiescence
race, unsealed historical driver source, wrong per-task language tags, a latent `verifier_rc`
classifier hole) that raise the bar this evidence-collection methodology must clear before reuse, but
none of them supply *affirmative* evidence that any of the 113 agent workspaces actually passed.

> **Most precise defensible headline (Codex-family phrasing, endorsed after independent Claude
> cross-check): "Original live rewards: 0/113. Corrected-valid score: 0/106, where raw gold validation
> was 102/113 and four raw failures were independently justified as corrected-valid. REAL, with
> material replay, timeout, provenance, metadata, and documentation defects."**

## Identity / methodology disclosure

Per this repo's established cross-family-audit convention (see the SWE-bench-Multilingual precedent at
`signoff_codex.md` in this same worktree root, and `experiments/runs/swev_instruct2507_full500_v5_147/signoff_codex.md`),
this file is produced by two distinct model identities, kept attributable throughout:

1. **Primary/first investigator: Claude (Anthropic, Sonnet 5, Claude Agent SDK).** Performed the initial
   SSH evidence-gathering, code reading, and independent fresh-container re-executions (2 tasks it picked
   itself — `dateutil-rfc5545-timezone-interop`, `etree-xml-diff-patch` — plus a targeted NO_PROXY
   polluted-vs-clean A/B and all-4-reclassified-task agent re-verification in the clean env), then
   drafted a first version of this signoff from a *partial, directly-observed* read of the Codex-family
   session (which was still running). **That intermediate draft has since been superseded by this file**,
   written after the Codex-family session finished and produced its own complete report.
2. **Independent Codex-family reviewer: `codex exec`** (OpenAI, model `gpt-5.6-sol`,
   `reasoning.effort=ultra`, `text.verbosity=high`, `--search`, `--dangerously-bypass-approvals-and-sandbox`),
   invoked locally on the Mac control plane (`zsh -i -c 'codex-pro exec - < codex_brief.md'`), given a
   detailed brief of the Claude pass's specific claims and told explicitly not to trust them. **This
   session ran ~40 minutes**, writing **9 of its own independent Python scripts**
   (`remote_fresh_repro.py`, `remote_clean_correction_repro.py`, `remote_stream_scan.py`,
   `remote_sha_coverage.py`, `remote_compare_ids.py`, `remote_compare_original.py`,
   `remote_results_audit.py`, `remote_docker_exec_timeout_probe.py`, `remote_capture_inventory.py`),
   picking its own additional/different fresh tasks
   (`optique-conditional-option-dependencies` TypeScript, `fd-deterministic-multi-key-sorting` Rust, plus
   its own full independent re-derivation of the NO_PROXY mechanism across all 4 reclassified tasks with
   2-3x repeat runs), and producing a **complete, self-contained final report**
   (`codex_pro_findings.md`, ~545 lines, its own explicit verdict "CODEX VERDICT: REAL", quoted and
   incorporated below). No contamination was observed (unlike a documented prior incident in this same
   repo at `experiments/runs/swev_instruct2507_full500_v5_147/signoff_codex.md`, where a concurrent
   `codex-pro --search` session bled in another task's brief and had to be discarded); the only anomalies
   were two internal `codex_core::tools::router` `exec_command` creation errors (CLI-level transient
   faults, unrelated to task content), which it recovered from.

Everything below marked **[Codex]** is drawn directly from the Codex-family agent's own completed report
and its own cited raw evidence paths (`$META`, `$XOPT`, `$XFD`, `$XCLEAN` — path abbreviations it defined
itself, reproduced in its own words in §Codex path key below); it is not paraphrased into a Claude
summary and re-presented as if Claude had verified it independently, except where explicitly marked
**[Claude, independently confirmed]**. Both signatures are genuine; neither agent is impersonating the
other.

### Codex path key (as defined by the Codex-family agent itself)

```text
$BM     = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench
$WT     = $BM/repo/.worktrees/deepswe-instruct2507-pathA-147
$B      = $WT/experiments/runs/deepswe_instruct2507_pathA_147
$L      = $BM/deepswe_pathA/runs/full113_instruct_20260713T103633Z
$A      = $BM/deepswe_pathA/runs/audit_full113_instruct_20260713T144617Z
$D      = $BM/deepswe_pathA/deepswe_qwencode_driver_instruct.py
$O      = $BM/deepswe_pathA/deepswe_full113_orchestrator_instruct.py
$TASKS  = /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/bench/deep-swe/tasks
$XOPT   = $BM/tmp/codex_auditor_b_optique_20260713T161500Z
$XFD    = $BM/tmp/codex_auditor_b_fd_20260713T155032Z
$XCLEAN = $BM/tmp/codex_auditor_b_clean4_20260713T155354Z
$META   = $XFD   (capture_inventory.json lives here)
```

---

## ① Ground-truth arithmetic reconciles

- **[Claude]** `results.jsonl` (113 rows): `agent_reward` distribution `{None: 67, 0: 46}` — never 1.
- **[Codex]** Independent reducer over `$B/results.jsonl:1-113` confirms the same 46/67/0 split, plus:
  raw `gold_reward` is **102 x 1, 11 x 0** (not 106 x 1 as a literal reading of `gold_valid_ids.txt`'s own
  header comment might suggest); within the corrected 106-ID set, raw gold is 102 ones + 4 zeros. The
  four raw-zero-but-corrected-valid tasks are `httpx-deterministic-cookie-store`,
  `httpx-multipart-response-parsing`, `httpx-streaming-json-iteration`, `testem-per-launcher-reports`.
- **DEFECT (documentation, immaterial to score):** `calibration.md:9`'s "1 of 106 valid tasks" captured a
  patch is false both in count and in framing. **[Codex, more precise]**: corrected-valid counts are
  **51 nonempty captured patches, 42 successfully applied**; the Coder sibling's `calibration.md` does not
  have this bug. Zero effect on `results.jsonl` itself. **MINOR.**

## ② Same apply+verify code path for gold and agent — command parity confirmed, payload parity refuted

- **[Claude]** `apply_solution()` (`$D:387`) and `_apply_patch_file()` (`$O:217`) both run identical
  `git apply --whitespace=nowarn ... && echo APPLIED_OK`, both call the same `run_verifier()` (`$D:245-283`).
- **[Codex, qualifies claim 4]**: command/scorer parity is true, but **payload provenance is not
  equivalent** — gold gets the complete curated `solution.patch`, while the agent replay gets
  `prediction.patch.diff`, produced by `git diff <base_ref>` (`$D:301-332`), which **omits untracked
  files**. This is the root cause of finding ⑨ below.
- `tests/test.sh` (git-clean `deep-swe` dataset repo) resets test files, applies the hidden `test.patch`,
  runs `test.sh base` then `test.sh new`, reward=1 only if both exit 0.

## ③ Fresh, from-scratch independent re-runs — 2 Claude-picked + 2 Codex-picked tasks, all outside curated samples (plus 1 curated-sample corroboration)

| task | lang | picked by | gold | agent | root cause (read directly) |
|---|---|---|---|---|---|
| dateutil-rfc5545-timezone-interop | python | Claude | 1 | 0 | `AttributeError: '_rrulestr' object has no attribute '_parse_rfc'` |
| etree-xml-diff-patch | go | Claude | 1 | 0 | `undefined: Resolution`, `undefined: ResolutionOurs` — agent references a type it never declares |
| optique-conditional-option-dependencies | typescript | **[Codex]** | 1 | 0 | real build error `Expected ',' but found '{'` at `src/primitives.ts:665:17`; gold: full build, 2497 baseline + 36/36 new passes (`$XOPT/gold/verifier.stdout.txt:4046-4054,4204-4213`) |
| fd-deterministic-multi-key-sorting | rust | **[Codex]** (also in curated samples — treated as corroboration) | 1 | 0 | malformed Rust, multiple real compile errors (`expected identifier, found keyword 'enum'`, `unresolved crate 'rand'`, `undeclared type 'SortField'`) (`$XFD/agent/verifier.stderr.txt:68-180`) |

All 4 (5 counting the httpx/testem set in §④) independently re-derived from scratch — SHA-256-verified
fresh `docker load`, distinct fresh gold/agent containers, clean pre-state (`REWARD_PRE=MISSING`
confirmed before verification) — and all match the bundle's claims exactly.

## ④ NO_PROXY judging-bug mechanism — causally isolated and quantified by both auditors independently

- **[Claude]** `container_env()` (`$D:179-188`) injects `100.100.0.0/16` + serving host IP into
  `NO_PROXY`/`no_proxy` for every `dexec()` call. Controlled A/B on `httpx-multipart-response-parsing`:
  polluted → gold=0; clean → gold=1.
- **[Codex, full 4-task re-derivation with repeats]**: reran all four gold+agent pairs with
  `unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY NO_PROXY no_proxy ALL_PROXY all_proxy` prefixed:

  | task | clean gold | clean agent | note |
  |---|---|---|---|
  | httpx-deterministic-cookie-store | 1 | 0 | agent: unterminated Python string / syntax failure |
  | httpx-multipart-response-parsing | 1 | 0 | agent: 122 failures + 11 errors, not proxy-only |
  | httpx-streaming-json-iteration | 1 | 0 | agent: `async for` outside an async function |
  | testem-per-launcher-reports | 1, 1 (2/2) | 0, 0, 0 (0/3) | flake-corrected gold stable; agent has genuine launcher/report-state TypeErrors |

  All `verifier_rc=0`. **The denominator correction does not launder an agent success into the
  numerator — independently confirmed twice, by two different scripts, on all four tasks, with repeat
  runs for determinism.**
- Documentation drift found **[Codex]**: `AUDIT_NOTES.md:10-16` says "4 httpx/happy-dom" (copied from the
  Coder bundle's own correction description), but this Instruct bundle actually promotes **three** httpx
  tasks plus `testem-per-launcher-reports`; `denom_assert.txt:19-24` has the accurate list. **MINOR.**
- The 106-task `gold_valid` ID set is byte-identical (SHA-256 `c28ddd1d08...` both sides, confirmed by
  both auditors independently) between this bundle and the already-dual-signed Coder sibling (`31d87f1`).

## ⑤ python venv — correctly time-scoped

- `VENV_PREFIX` (`$D:63`) is in both the verifier's `test.sh` call and the agent's own `qwen` invocation.
- **[Claude]** Verified via file-mtime forensics that Coder's caveat (venv-handicap during agent
  *generation*) genuinely predates a fix landed at `2026-07-12T17:23:46Z` (`deepswe_qwencode_driver.py.bak_prevenvfix`
  vs. the live, fixed file, mtimes 1 second apart), and Instruct's `agent_run_root`
  (`2026-07-13T10:36:33Z`) postdates that fix — so Instruct's `AUDIT_NOTES.md` correctly omits a caveat
  that no longer applies, rather than silently dropping a live one.
- Across all 113 tasks, `run_shell_command` was invoked exactly 4 times, all plain `mkdir -p` — the model
  essentially never self-verifies via shell regardless of venv availability.

## ⑥ Diagnostics-only bug — independently found by both auditors via different methods, does not touch scoring

- **[Claude]** `analyse_stream()` (`$D:365`) checks `"tool_call" in json.dumps(event)[:200].lower()`, but
  the real schema nests calls as `message.content[].type == "tool_use"`/`"tool_result"`, usually past the
  200-char cutoff. Hand-decoded `wasmi-trap-coredumps` (249 real events, genuine tool_use/tool_result
  pairs) vs. `stream_analysis.json`'s `tool_calls: 0`.
- **[Codex, independent method + exact numbers]**: on its own picked `fd-deterministic-multi-key-sorting`,
  a full recursive-JSON-walk found `JSON_EVENTS_PARSED=96, NESTED_TOOL_USE=31, NESTED_TOOL_RESULT=31`
  against stored `tool_calls=0, tool_results=0` — same bug, independently rediscovered.
- **Confirmed cosmetic only by both**: `classify()` (`$O:77-97`) uses only `reward`, `json_events`
  (correctly counted), and `patch_nonempty` — never `tool_calls`/`tool_results`.
- Confirmed pre-existing in the already-dual-signed Coder driver too. **MINOR.**

## ⑦ Serving identity, integrity, provenance, timeout/rc sanity

- Live re-probe (both auditors, independently, same result): `:30000` → `Qwen3-30B-A3B-Instruct-2507`;
  `:30001` → `Qwen3-Coder-30B-A3B-Instruct`.
- `sha256sum -c SHA256SUMS`: 66/66 OK both auditors. **[Codex, stricter coverage check]**: the bundle has
  **68** git-tracked files but only **66** checksum entries — `SHA256SUMS` itself and `commit_msg.txt` are
  git-tracked but not self-checksummed, so `TRACE.md:11`/`README.md:26`'s "every file sealed" claim
  overclaims. `commit_msg.txt` is still protected by the exact clean git commit itself, so this is a
  checksum-manifest coverage gap, not evidence of tampering. **MINOR.**
- `git show --stat 6c23a02`: 68 files, all under the bundle dir, 0 outside — confirmed by both auditors
  independently (Claude via `git show --stat`; Codex via an independent path-prefix check).
- No timeout-truncation risk on any *verifier* run: max `agent_verifier_seconds`=249.2s (audit-replay) /
  507.5s (**[Codex]**, original live corpus), both far under the 1800s verifier cap;
  `agent_verifier_rc`/`gold_verifier_rc` never nonzero across all 113 rows in either the audit-replay set
  or **[Codex]** the original 113 live verifier executions.

## ⑧ Cross-bench sanity anchor

- **[Claude]** Independently recomputed from `swev_instruct2507_full500_v5_147/results.jsonl`: 500 rows,
  120 resolved → 24.0%, matching that bundle's own signed-off score. Same model, same qwen-code-family
  scaffold: 24% on SWE-bench Verified, 0% on DeepSWE full113 — DeepSWE full113 is unusually hard for this
  model+scaffold (all-or-nothing baseline+new scoring), not evidence of a universally broken harness.
  Coder-30B on the identical bench+scaffold independently landed at the same 0/113, already dual-signed
  REAL.

## ⑨ Audit-replay drops untracked files — real, quantified, MAJOR as a methodology defect, does NOT flip the verdict

- **[Claude, first found]** and **[Codex, independently found + far more precisely quantified]**: the
  agent-run's `git -c core.fileMode=false diff --binary <base_ref>` capture (`$D`, in `run_agent`) omits
  untracked (newly-created) files. **[Codex]** exact breakdown:
  `tasks with untracked files: 48/113` (Claude's own independent count: 48/113, matching exactly);
  `untracked-only tasks: 19/113` (the *entire* agent contribution for these 19 is invisible to a
  diff-based reconstruction); `mixed tracked+untracked: 29/113`; within the 106 corrected-valid set,
  `45/106` have untracked files, `19/106` are untracked-only.
- **[Codex]** Concrete example: `wazero-multi-module-snapshots` has `?? experimental/snapshot/snapshot.go`
  in its live `post_agent_git_status.txt`, an **empty** saved `prediction.patch.diff`, and a `null` row in
  `results.jsonl:104` — yet the *original* same-container verifier saw the new file and reported a real
  compile error (`package gzip is not in std`).
- **Why this does not change the verdict — independently proven by both auditors via the same underlying
  argument**:
  - **[Claude]**: `agent_run_report.json` (`mode: "agent"`, computed by `_task_agent()`'s `run_verifier()`
    call on the *same live container*, before any diff is used for scoring) independently reports
    `"resolved": 0, "resolve_rate": 0.0` across all 113 tasks with full (tracked+untracked) file
    visibility — architecturally immune to the replay defect.
  - **[Codex, exhaustive]**: reduced the *complete* original 113-task live corpus directly (not just the
    aggregate report): `live reward = {0: 113}`, `live verifier_rc = {0: 113}`, all 113 raw verifier
    stdout files have both baseline/new-test exit markers, and **new-test exit 0 occurs zero times across
    all 113** — cross-checked against the SHA-covered `agent_run_orchestrator.log`, which independently
    records all 113 `DONE` rows with reward 0, RC 0. Every one of the 48 untracked-affected live
    workspaces individually still shows `live_reward: 0`.
  - Since data loss in the replay path can only make a reconstructed result *more* pessimistic than the
    live truth (a missing file cannot make broken code compile/pass), and the live truth is already 0/113
    with full visibility, the replay defect cannot be hiding a suppressed success.
- **Severity: this is a real, MAJOR defect in the evidence-collection/replay methodology** (it means
  `results.jsonl`'s per-task *failure attribution* — "no applicable patch" vs. "patch fails verifier" —
  is unreliable for up to 48 tasks, and any *future* run relying on audit-replay alone, without also
  checking the original live corpus, could not by itself prove a 0 is real). **It does not change this
  specific verdict (0/113 REAL)** because the authoritative, replay-independent live measurement already
  establishes it. Recommended fix **[Codex]**: copy the complete `/logs/artifacts/model.patch` (which the
  task's own `test.sh` already builds via `git add -A` + `git diff --cached --binary`, including
  untracked files) out of the container instead of relying on the driver's own separate, incomplete
  `git diff <base_ref>` capture.

## ⑩ Additional defects found only by the Codex-family pass

- **Timeout/quiescence race (MAJOR as a reproducibility/hardening defect):** `run_agent()`'s
  `subprocess.TimeoutExpired` handler does not kill the in-container agent process before capture/scoring
  proceeds. **[Codex]** directly probed this on a disposable container using the same
  `subprocess.run(..., timeout=...)` around `docker exec` mechanism: one second after the client-side
  timeout fired, the in-container shell process was still alive (`PROCESS_ALIVE=yes`). 5 original
  rollouts hit the 2400s agent timeout (`httpx-deterministic-cookie-store`,
  `ipython-session-bundle-replay`, `langchain-request-coalescing`,
  `participle-grammar-conflict-analysis`, `scc-bounded-memory-spilling`); all 5 have live reward 0/RC 0
  (3 stably replay to 0; the 2 untracked-only cases have real substantive failures visible at the
  original scoring cutoff, per §⑨'s live-corpus argument). Codex explicitly and correctly characterizes
  this as "a demonstrated risk, not a demonstrated score corruption" — it could not prove the actual
  historical Qwen process for these 5 specific tasks survived past the timeout, only that the platform
  mechanism *can* allow it. Also: `classify()` never consults `ag["timed_out"]`, so these 5 are
  mislabeled ordinary `unsolved`/`unsolved_no_patch` rather than a distinct timeout status — a
  diagnostic-only sub-issue.
- **Historical driver/orchestrator source is not sealed (MAJOR as a provenance-methodology defect):**
  `$BM/deepswe_pathA` is not a git repository; `deepswe_qwencode_driver_instruct.py` and
  `deepswe_full113_orchestrator_instruct.py`'s current hashes are not recorded anywhere in the sealed
  bundle or `SHA256SUMS`. Their mtimes (`2026-07-13 18:31:33 +08`) precede the agent-run launch by ~5
  minutes, which is *consistent with* these being the executed bytes, but this is not cryptographically
  proven. Fresh reproductions using the current source agree with the raw score, so this does not
  constitute affirmative evidence of tampering — but it is a real gap that should be closed (seal driver
  hashes into the evidence commit at launch time) before this methodology is relied on for a
  higher-stakes claim.
- **Wrong per-task language tags on at least 4 tasks (MINOR — does not affect the aggregate, does affect
  by-language breakdown reliability):** `httpx-deterministic-cookie-store` tagged "typescript" but its
  solution patch touches only `.py` files; `prometheus-transactional-reload-status` tagged "typescript"
  but is Go; `katex-multicolumn-array-spans` tagged "javascript" but is TypeScript;
  `koota-entity-snapshot-rollback` tagged "python" but is TypeScript. `by_lang.md` and `summary.json`'s
  per-language breakdown should not be trusted at face value until corrected; the aggregate 0/113 /
  0/106 is unaffected.
- **Latent `verifier_rc` classifier hole (MINOR — did not fire in this run):** `classify()`
  (`$O:77-97`) branches on `reward == 1`/`reward == 0` without also requiring `verifier_rc == 0`, so a
  hypothetical future task script that writes `reward=1` to the file and then exits nonzero would still
  be classified `resolved`. Did not matter here: every one of the 113 original, 113 raw-gold, and 46
  executed audit-replay verifier runs returned `verifier_rc=0`.
- **Ten nonempty saved patches silently null out on replay (folds into §⑨'s root cause):** 56 tasks had
  nonempty tracked (git-diff-visible) saved patches in the original run, but only 46 apply cleanly during
  audit replay (51/42 within the corrected-valid subset) — the missing 10 fail atomic `git apply` and are
  mislabeled "no applicable patch" in `summary.json` rather than "patch failed to apply." All ten's
  *original* live workspaces still show reward 0.

## Findings summary

| tag | finding | file:line | effect on 0/113 verdict |
|---|---|---|---|
| MINOR | `calibration.md` "1 of 106" patch-count claim false (real: 51 nonempty / 42 applied of 106) | `experiments/runs/deepswe_instruct2507_pathA_147/calibration.md:9` | none — `results.jsonl` unaffected |
| MINOR | `analyse_stream()` tool_call/tool_use substring+200-char-window bug under-reports tool_calls | `deepswe_pathA/deepswe_qwencode_driver_instruct.py:365` (pre-existing, also in Coder driver) | none — `classify()` never reads this field |
| MINOR | `AUDIT_NOTES.md` copied the wrong 4th-correction description from the Coder bundle | `experiments/runs/deepswe_instruct2507_pathA_147/AUDIT_NOTES.md:10-16` | none — `denom_assert.txt` has the accurate list |
| MINOR | `SHA256SUMS` covers 66/68 git-tracked bundle files (excludes itself + `commit_msg.txt`) | `experiments/runs/deepswe_instruct2507_pathA_147/SHA256SUMS` | none — git commit itself protects the 2 missing files |
| MINOR | 4 tasks have wrong `lang` metadata tags | `results.jsonl` rows 38, 47, 53, 85 | none on aggregate; by-language tables unreliable until fixed |
| MINOR | latent `verifier_rc` not required alongside `reward==1` in `classify()` | `deepswe_pathA/deepswe_full113_orchestrator_instruct.py:77-97` | none observed — every verifier_rc in this run is 0 |
| **MAJOR (methodology, not verdict)** | audit-replay `git diff` capture drops untracked new files (48/113 tasks, 19/113 untracked-only) → unreliable per-task failure attribution for future reuse | `deepswe_pathA/deepswe_qwencode_driver_instruct.py` (`run_agent`, diff-capture) | none on THIS verdict — original live in-container verifier (full file visibility, computed before any replay) independently shows resolved=0 across all 113, cross-checked task-by-task for the affected 48 |
| **MAJOR (methodology, not verdict)** | agent-timeout handling does not kill/quiesce the in-container process before scoring (demonstrated race, not demonstrated corruption) | `deepswe_pathA/deepswe_qwencode_driver_instruct.py` (`run_agent`, `TimeoutExpired` handler) | none observed — all 5 affected tasks independently show live reward=0/RC=0 |
| **MAJOR (methodology, not verdict)** | historical driver/orchestrator source bytes are not cryptographically sealed (not a git repo, hashes not in `SHA256SUMS`) | `deepswe_pathA/` (not a git repo) | none observed — fresh reproduction with current source agrees with the raw score |
| REPRO | gold=1/agent=0 independently reproduced fresh on 4 non-curated + 1 curated-corroboration tasks across 2 model families, 4 languages | see §③ | confirms verdict |
| REPRO | NO_PROXY causal mechanism independently reproduced twice (by both auditors, separate code, with repeats) on all 4 reclassified tasks | see §④ | confirms verdict, rules out denominator-gaming |
| REPRO | 106-task gold_valid ID set byte-identical Coder vs Instruct (SHA-256 match confirmed by both auditors) | `gold_validation/gold_valid_ids.txt` both bundles | confirms model-independent gold validity |
| REPRO | original 113-task live corpus independently reduced by Codex: reward={0:113}, verifier_rc={0:113}, new-test-exit-0 count = 0 | `agent_run_orchestrator.log`, per-task `verifier.result.json`/`.stdout.txt` | direct, exhaustive confirmation of the verdict, not dependent on the lossy replay at all |

**No BLOCKER found by either auditor.** Three genuine MAJOR-severity defects were found in the
evidence-collection *methodology* (replay data loss, timeout race, unsealed historical source) — these
matter and should be fixed before this harness is trusted for a less-scrutinized future claim — but none
of them supply affirmative evidence that any of the 113 agent workspaces passed; the original,
replay-independent live verification (immune to all three by construction) already and exhaustively
shows 0/113.

## Required remediation before this evidence-collection method is reused (Codex-family recommendation, endorsed)

1. Copy the complete task-generated `/logs/artifacts/model.patch` (already built by the task's own
   `test.sh` via `git add -A`) out of the container instead of a separate, lossy `git diff <base_ref>`.
2. On agent timeout, explicitly terminate the in-container process group and verify quiescence
   (`docker top`/PID polling) before snapshot/verification; classify timeouts as a distinct status.
3. Seal exact driver/orchestrator/launch-script bytes and hashes into the evidence commit at launch time.
4. Gate `resolved` on `reward == 1 AND verifier_rc == 0`, not `reward == 1` alone.
5. Record actual `git apply`/`docker cp` return codes; distinguish "empty patch" from "nonempty patch,
   apply failed" in per-task status.
6. Fix nested stream-event tool-call parsing, per-task language metadata, and calibration/correction
   prose to match the underlying structured data.

## Push / provenance

- Signed off from the `evidence/deepswe-instruct2507-pathA-147-20260713` worktree
  (`$BM/repo/.worktrees/deepswe-instruct2507-pathA-147`), based on that branch's own HEAD (`6c23a02`),
  not the dirty main `repo/` worktree.
- Committed and pushed to `origin` from the `dev` host (only host in this environment with verified
  internet egress to GitHub; the KVM audit host has no outbound path to github.com). This file supersedes
  an earlier, more provisional version of itself pushed in commit `3533a65` before the Codex-family
  session had finished; that commit's content is preserved in git history for transparency.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
