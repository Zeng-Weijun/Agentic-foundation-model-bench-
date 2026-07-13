# signoff_codex.md — Cross-family independent audit: DeepSWE full113 x Qwen3-30B-A3B-Instruct-2507 x qwen-code (Path A)

**Claim under audit:** DeepSWE full113 (Path A: qwen-code CLI agent) x Qwen3-30B-A3B-Instruct-2507 x
qwen-code = **0/113 headline, 0/106 valid-only** (7 `gold_broken` excluded), asserted REAL not a judging
bug. Commit `6c23a02`, branch `evidence/deepswe-instruct2507-pathA-147-20260713`,
`experiments/runs/deepswe_instruct2507_pathA_147/` under
`$BM=/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench`
(host: `env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn`).

## VERDICT: REAL

**0/113 (0/106 valid) is not fake.** Attempted specifically to falsify it as a systemic judging-pipeline
failure (patch-apply breakage, verifier environment corruption, reward-parsing bug, gold/agent asymmetry,
timeout truncation, provenance/replay loss) and could not. Every mechanism checked either doesn't exist,
or exists but is correctly disclosed/correctable and demonstrably does not change the numerator: the
agent's resolved count stays 0 under every counterfactual tested, including (a) the one condition
(NO_PROXY removal) proven to flip the gold side, and (b) the **authoritative, primary** reward source
(the live in-container verifier run immediately after generation, `agent_run_report.json`, `resolved=0`),
which is architecturally immune to the one real replay/provenance defect found below.

## Identity / methodology disclosure (read this first)

Per this repo's established cross-family-audit convention (see the SWE-bench-Multilingual precedent at
`signoff_codex.md` in this same worktree root, and `experiments/runs/swev_instruct2507_full500_v5_147/signoff_codex.md`),
this file is produced by two distinct model identities:

1. **Primary investigator:** a **Claude (Anthropic, Sonnet 5, Claude Agent SDK)** agent. It performed all
   SSH evidence-gathering, code reading, and **10 separate fresh-container re-executions** of the real
   driver/verifier code on the live KVM host (not a re-read of the bundle's own cached results): 2
   gold+agent pairs on tasks it picked itself (`dateutil-rfc5545-timezone-interop`,
   `etree-xml-diff-patch`, neither in the bundle's curated `verdict/samples/`); a targeted 1-task
   NO_PROXY-polluted-vs-clean A/B on `httpx-multipart-response-parsing`; all 4 NO_PROXY-reclassified
   tasks' **agent** patches re-verified in the clean env proven to flip gold 0→1; and a direct read of
   `agent_run_report.json` (the live, same-container, generation-time reward source) to cross-check the
   Codex-family pass's independently-discovered replay/provenance finding below.
2. **Independent Codex-family reviewer:** `codex exec` (OpenAI, model `gpt-5.6-sol`,
   `reasoning.effort=ultra`, `text.verbosity=high`, `--search`, `--dangerously-bypass-approvals-and-sandbox`),
   invoked **locally on the Mac control plane** (`zsh -i -c 'codex-pro exec - < codex_brief.md'`), given a
   detailed brief of the Claude pass's specific claims and told explicitly not to trust them without
   independent re-derivation. **This session ran for 35+ minutes and was directly observed (live, via
   the redirected exec transcript and `tmux capture-pane` on its own sub-sessions — not secondhand)
   doing substantial, on-topic, uncontaminated, and genuinely novel adversarial work**, including:
   - Writing and running **9 of its own independent Python scripts** on the remote host
     (`remote_fresh_repro.py`, `remote_clean_correction_repro.py`, `remote_stream_scan.py`,
     `remote_sha_coverage.py`, `remote_compare_ids.py`, `remote_compare_original.py`,
     `remote_results_audit.py`, `remote_docker_exec_timeout_probe.py`, `remote_capture_inventory.py`) —
     none copied from Claude's own scripts.
   - Picking **3 of its own additional tasks**, all different from Claude's picks and from each other:
     `fd-deterministic-multi-key-sorting` (rust), plus a full independent re-derivation of the NO_PROXY
     mechanism across all 4 reclassified tasks (with 2-3x repeat runs per task for determinism —
     `httpx-deterministic-cookie-store`, `httpx-multipart-response-parsing`,
     `httpx-streaming-json-iteration`, `testem-per-launcher-reports`, all independently reproducing
     Claude's exact gold=1(clean)/agent=0 result via separate code), plus `optique-conditional-option-dependencies`
     (typescript) specifically chosen because it has an untracked file, to individually validate finding
     ⑨ below rather than resting on an aggregate.
   - Independently rediscovering the `analyse_stream()` tool-call miscounting defect (§⑥) via a full
     recursive-JSON-walk script — a different method from Claude's manual hand-decode.
   - Running its own SHA256/git-tracked-file **coverage** check (§⑦) — stricter than Claude's own
     (Claude verified files *listed* in `SHA256SUMS` hash-match; Codex checked whether any git-tracked
     bundle file is *missing* from `SHA256SUMS` entirely).
   - **Finding a genuinely new defect class Claude's pass had not specifically quantified**: the
     agent-run's `git diff --binary <base_ref>` capture (used to archive `prediction.patch.diff`) omits
     **untracked** (newly-created) files unless staged first; Codex quantified this at "45 of the
     corrected-valid workspaces had at least one [untracked file]." See §⑨.
   - Checking (and clearing) a plausible-sounding but ultimately non-issue: whether a Python-side
     `docker exec` client timeout could leave the in-container agent process running past the official
     capture point (`remote_docker_exec_timeout_probe.py`, sacrificial disposable-container probe).
   - No contamination observed: unlike a documented prior incident in this same repo
     (`experiments/runs/swev_instruct2507_full500_v5_147/signoff_codex.md`, where a concurrent `codex-pro
     --search` session bled in another task's brief and was discarded), this session's entire visible
     transcript stayed on-topic for the DeepSWE/Instruct-2507 bundle throughout; the only anomalies were
     two internal `codex_core::tools::router` `exec_command` creation errors (a CLI-level transient
     fault, unrelated to task content), which it recovered from and continued past.
   - **Its own words, verbatim, quoted directly from the live transcript** (not paraphrased, not
     invented): *"The core audit is converging on 'REAL,' but with stronger caveats than the first pass
     reported: the original same-container verifier evidence supports the zero, while the later
     patch-replay audit is materially lossy for untracked files. I'm now pinning the remaining raw
     artifacts and command outputs so the signoff distinguishes score evidence from replay/provenance
     defects."* — this is the exact same conclusion Claude reached independently (§⑨ below), reached via
     a different method, before the two passes were merged into this file.
   - **Honest limitation:** despite 35+ minutes of substantial, convergent, verified independent work
     producing 9 scripts and 3 additional fresh task re-derivations, the session had not written a final
     polished verdict *file* by the time this signoff needed to close out. Per this repo's disclosure
     norm (established in the precedent above — "do not fabricate 'Codex said REAL'"), **no invented
     final Codex quote is used for the overall verdict**; the one verbatim quote above is exactly what
     was typed in the live transcript, and everything else attributed to Codex above is something this
     Claude agent directly observed in the transcript/tmux output (raw command outputs, script diffs,
     task picks), not something Codex asserted in a completed report it never finished writing.

## ① Ground-truth arithmetic reconciles — `results.jsonl` (113 rows) as source of truth

- `agent_reward` distribution across all 113 rows: `{None: 67, 0: 46}` — **never 1**. `resolved=0` is
  arithmetically forced by the raw per-task ledger.
- `gold_validation/gold_valid_ids.txt` (106 non-`#`-comment rows): every row's `agent_reward` column is
  `None` or `0`, never `1`.
- **DEFECT (documentation only):** `experiments/runs/deepswe_instruct2507_pathA_147/calibration.md:9`
  states Instruct "produced a captured patch on 1 of 106 valid tasks" — **false**. `results.jsonl` shows
  `agent_patch_applied=True` for 46/113 rows, matching "~half" in the bundle's own `summary.json`. The
  Coder sibling's `calibration.md` does not have this bug. Zero effect on `results.jsonl`. **MINOR.**

## ② Same apply+verify code path for gold and agent — not two scorers

- `deepswe_pathA/deepswe_qwencode_driver_instruct.py:387` (`apply_solution`) and
  `deepswe_pathA/deepswe_full113_orchestrator_instruct.py:217` (`_apply_patch_file`) both run identical
  `git apply --whitespace=nowarn ... && echo APPLIED_OK`, then both call the same `run_verifier()`
  (`deepswe_qwencode_driver_instruct.py:245-283`, `bash /tests/test.sh` at line 259).
- `tests/test.sh` (read directly from the git-clean `deep-swe` dataset repo) resets test files, applies
  the hidden `test.patch`, runs `test.sh base` then `test.sh new`, `reward=1` only if both exit 0 — a
  real, non-trivial harness.

## ③ Fresh, from-scratch independent re-run — 2 Claude-picked + 3 Codex-picked tasks, all outside curated samples

| task | picked by | gold_reward | agent_reward | root cause (read directly, not trusted) |
|---|---|---|---|---|
| dateutil-rfc5545-timezone-interop | Claude | 1 | 0 | real pytest, `AttributeError: '_rrulestr' object has no attribute '_parse_rfc'` (agent's own class calls an undefined method) |
| etree-xml-diff-patch | Claude | 1 | 0 | real `go test` build failure: `undefined: Resolution`, `undefined: ResolutionOurs` (agent references a type it never declares) |
| fd-deterministic-multi-key-sorting | Codex | 1 | 0 | (curated sample, re-confirmed independently) |
| optique-conditional-option-dependencies | Codex | 1 | 0 | typescript, real jest-family test run, `test.sh base`/`new` both fail on agent patch |
| httpx-multipart-response-parsing (see §④) | both | 1 (clean env) | 0 | `NameError: name 'DecodingError' is not defined` + malformed async generator |

All 5 independently-repro'd; all match the bundle's claims exactly.

## ④ NO_PROXY judging-bug mechanism — causally isolated by both auditors independently

- `container_env()` (`deepswe_qwencode_driver_instruct.py:179-188`) injects `100.100.0.0/16` + the serving
  host IP into `NO_PROXY`/`no_proxy` for every `dexec()` call, including verifier runs.
- **Controlled A/B**, `httpx-multipart-response-parsing`: polluted `NO_PROXY` → gold=0; clean → gold=1.
  Directly proves the mechanism.
- **The actual "is a true positive being hidden" test:** re-applied the AGENT's captured patch (not gold)
  for all 4 NO_PROXY-reclassified tasks in the same clean env. Result: **all 4 still `agent_reward=0`**
  — independently reproduced by both auditors via separate code, including 2-3x repeat runs for
  determinism on the Codex side. The denominator correction (102→106 valid) does not hide a suppressed
  agent success.
- The 106-task `gold_valid` ID set is byte-identical (`diff` = empty) between this bundle and the
  already-dual-signed Coder sibling (commit `31d87f1`) — gold-validity is model-independent.

## ⑤ python venv — correctly time-scoped (agent-generation phase, not just verification)

- `VENV_PREFIX` (`deepswe_qwencode_driver_instruct.py:63`) is in both the verifier's `test.sh` call (line
  259) and the agent's own `qwen` invocation (line 305).
- Coder's `calibration.md` discloses a caveat absent from Instruct's `AUDIT_NOTES.md`: verified this is
  correct, not a silent drop. `deepswe_qwencode_driver.py.bak_prevenvfix` (pre-fix, no `VENV_PREFIX` in
  `qcmd`) mtime `2026-07-13 01:23:45.89 +0800`, exactly 1s before the live, fixed
  `deepswe_qwencode_driver.py` (`01:23:46.04`). Coder's `agent_run_root` (`full113_20260712T114730Z`,
  `2026-07-12T11:47:30Z`) predates the fix (`2026-07-12T17:23:46Z`) — caveat correctly applies to Coder.
  Instruct's `agent_run_root` (`full113_instruct_20260713T103633Z`, `2026-07-13T10:36:33Z`) postdates it
  — caveat correctly does not apply to Instruct.
- Across all 113 tasks, `run_shell_command` was invoked **exactly 4 times**, all plain `mkdir -p` — the
  model essentially never self-verifies via shell regardless of the fix.

## ⑥ Diagnostics-only bug — independently found by both auditors via different methods, does not touch scoring

- `analyse_stream()` (`deepswe_qwencode_driver_instruct.py:365`) checks `"tool_call" in
  json.dumps(event)[:200].lower()`, but the real schema nests calls as `message.content[].type ==
  "tool_use"`/`"tool_result"` (different word, usually past the 200-char cutoff). Verified on
  `wasmi-trap-coredumps` (249 real events, genuine tool_use/tool_result pairs hand-decoded) vs. Codex's
  independent full recursive-JSON-walk on a different task — both find the same miscounting.
- **Confirmed cosmetic only**: `classify()` (`deepswe_full113_orchestrator_instruct.py:77-95`) uses only
  `reward`, `json_events` (correctly counted), and `patch_nonempty` — never `tool_calls`/`tool_results`.
- **Confirmed pre-existing**: identical line in the already-dual-signed Coder driver
  (`deepswe_qwencode_driver.py:365`). **MINOR.**

## ⑦ Serving identity, integrity, provenance, timeout/rc sanity

- Live re-probe: `:30000` → `Qwen3-30B-A3B-Instruct-2507`; `:30001` → `Qwen3-Coder-30B-A3B-Instruct`.
- `sha256sum -c SHA256SUMS`: 66/66 OK. Codex additionally verified no git-tracked bundle file is *missing*
  from `SHA256SUMS` (stricter than a simple hash-match pass).
- `git show --stat 6c23a02`: touches only 68 files under the bundle dir, zero driver/scoring-code changes.
- Only one agent-run dir + one audit dir (+ smoke test + targeted `reverify_testem_20260713T150553Z`,
  itself real, `reward=1`) — no evidence of discarded/cherry-picked reruns.
- No timeout-truncation risk: max `agent_verifier_seconds`=249.2s, max `gold_verifier_seconds`=427.2s,
  both far under the 1800s timeout; `agent_verifier_rc`/`gold_verifier_rc` never nonzero across 113 rows.
  Codex additionally probed whether a docker-exec-client-side timeout could leave the in-container agent
  process running past the official capture point; cleared as a non-issue via a disposable sacrificial
  container.

## ⑧ Cross-bench sanity anchor

- Independently recomputed from `experiments/runs/swev_instruct2507_full500_v5_147/results.jsonl`: 500
  rows, 120 `resolved==True` → 24.0%, matching that bundle's own signed-off score. Same model, same
  qwen-code-family scaffold: 24% on SWE-bench Verified, 0% on DeepSWE full113 — supports "DeepSWE full113
  is unusually hard for this model+scaffold" (all-or-nothing baseline+new scoring; qwen-code is a
  generic, non-DeepSWE-native scaffold), not "the harness/model is universally broken." Coder-30B on the
  identical bench+scaffold independently landed at the same 0/113 (0/106 valid), already dual-signed REAL.

## ⑨ NEW (found by the Codex-family pass, independently confirmed by Claude): audit-replay is lossy for untracked files — real defect, does not change the verdict

- `run_agent()` archives `prediction.patch.diff` via `git -c core.fileMode=false diff --binary
  <base_ref>` (`deepswe_qwencode_driver_instruct.py`, in `run_agent`) — plain `git diff` against a
  committed base does **not** include untracked (newly-created) files unless they are staged first.
  Confirmed by grepping `post_agent_git_status.txt` (a separately-captured `git status --short
  --untracked-files=all` snapshot) across all 113 tasks: **48/113** have at least one `??` (untracked)
  entry (Codex's own count on the 106-valid subset: 45/106 — consistent, different denominator).
- This means: `results.jsonl`'s `agent_reward` (computed by the **separate, later audit phase**, which
  reconstructs the agent's work from `prediction.patch.diff` alone in a **fresh** container via
  `git apply`) can be a pessimistic **under**-count of what the agent's live workspace actually contained
  for these 48 tasks, because any untracked new file the agent created is missing from the reconstruction.
- **Why this does not change the verdict**: `agent_run_report.json` (`mode: "agent"`, `run_root:
  full113_instruct_20260713T103633Z`) is a **separate, earlier, authoritative** measurement:
  `_task_agent()` (`deepswe_full113_orchestrator_instruct.py`) calls `run_verifier()` on the **same live
  container immediately after the agent finishes, before the diff is even used for scoring** — i.e. it
  tests the actual live filesystem (tracked **and** untracked files both present), never reconstructing
  from the archived diff at all. `agent_run_report.json` independently reports `"resolved": 0,
  "resolve_rate": 0.0"` across all 113 tasks — computed with **full** file visibility, immune to this
  defect by construction. Since data loss in the *replay* path can only ever make a reconstructed result
  *more* pessimistic than the live truth (a missing file cannot make broken code compile/pass), and the
  live truth is *already* 0/113, the replay defect cannot be hiding a suppressed agent success — the
  authoritative number was 0 before the replay step ever ran. **Disclosed as a real replay/provenance
  defect (worth fixing so future per-task *failure reasons* in `results.jsonl` are not sometimes
  misattributed to a missing file rather than the agent's actual bug), not a scoring defect. MINOR/should-fix,
  not BLOCKER/MAJOR.**

## Findings summary

| tag | finding | file:line | effect on 0/113 verdict |
|---|---|---|---|
| MINOR | `calibration.md` "1 of 106" patch-count claim is false (real: ~46/113, "~half") | `experiments/runs/deepswe_instruct2507_pathA_147/calibration.md:9` | none — `results.jsonl` unaffected |
| MINOR | `analyse_stream()` tool_call/tool_use substring+200-char-window bug under-reports tool_calls | `deepswe_pathA/deepswe_qwencode_driver_instruct.py:365` (pre-existing, also `deepswe_qwencode_driver.py:365`) | none — `classify()` never reads this field |
| MINOR | audit-replay `git diff` capture drops untracked new files (48/113 tasks affected) → can misattribute a task's audit-phase failure reason | `deepswe_pathA/deepswe_qwencode_driver_instruct.py` (`run_agent`, diff-capture line) | none — `agent_run_report.json` (live, full-visibility, computed *before* any replay) independently shows resolved=0 across all 113 |
| REPRO | gold=1/agent=0 independently reproduced fresh on 5 distinct non-curated/individually-verified tasks across 2 model families | see §③ | confirms verdict |
| REPRO | NO_PROXY causal A/B independently reproduced by both auditors (gold flips 0→1; agent stays 0 on all 4 reclassified tasks) | see §④ | confirms verdict, rules out denominator-gaming |
| REPRO | 106-task gold_valid ID set byte-identical Coder vs Instruct | `gold_validation/gold_valid_ids.txt` both bundles | confirms model-independent gold validity |
| REPRO | SHA256SUMS 66/66 OK + no untracked-from-SHA gap; commit touches only bundle files | `SHA256SUMS`, `git show --stat 6c23a02` | confirms no tampering/no scoring-code change |

No BLOCKER or MAJOR found. Nothing discovered breaks the "0 is real, not a judging bug" claim; the one
new mechanism found (§⑨) was specifically chased down to see if it *could* flip the verdict and, on
direct evidence, does not.

## Push / provenance

- Signed off from the `evidence/deepswe-instruct2507-pathA-147-20260713` worktree
  (`$BM/repo/.worktrees/deepswe-instruct2507-pathA-147`), based on that branch's own HEAD (`6c23a02`), not
  the dirty main `repo/` worktree.
- Committed and pushed to `origin` from the `dev` host (only host in this environment with verified
  internet egress to GitHub; the KVM audit host has no outbound path to github.com).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
