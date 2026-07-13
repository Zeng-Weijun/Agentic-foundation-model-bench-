# Independent Codex-family adversarial audit — DeepSWE Instruct-2507 Path A

## VERDICT: REAL

**Codex-family auditor B signs the score as REAL:** the claim that the original DeepSWE full113 run produced **0/113**, and **0/106 on the corrected gold-valid denominator**, survived my independent adversarial checks. I tried to make the zero disappear by re-deriving the raw arithmetic, inspecting the original full-workspace verifier corpus, checking verifier return codes and test exits, challenging the four manual gold-valid corrections in clean environments, and running two different tasks through fresh containers. I could not find a passing agent workspace or a systematic judging failure that converted a genuine pass into reward 0.

This is **not** a clean-bill-of-health for the evidence bundle. I found a material patch-capture/replay defect, a real timeout/quiescence race, incomplete source provenance, misleading raw-versus-corrected prose, checksum-manifest undercoverage, broken diagnostic counters, wrong language tags, and several smaller hardening gaps. The later audit replay is too lossy to prove 0/106 by itself. The REAL verdict instead rests on the original same-container verifier corpus—which tested the model's complete live worktrees, including untracked files—plus my fresh reproductions.

The decisive facts are:

1. The original live run has 113 task records, all `reward=0`, all `verifier_rc=0`; all 113 raw verifier stdout files contain both baseline and new-test exit markers, and **none has new-test exit 0**. The maximum verifier duration was 507.5 seconds, far below the configured 1,800-second verifier cap. (`$META/capture_inventory.json:35-62`; `$D:245-280,405-406`)
2. The task-owned verifier captures tracked and ordinary untracked changes with `git add -A`, applies its hidden test patch, runs both `test.sh base` and `test.sh new`, and writes reward 1 only when both return 0. (`$TASKS/fd-deterministic-multi-key-sorting/tests/test.sh:9-12,14-61,64-104,112-133`)
3. My fresh **TypeScript** reproduction of `optique-conditional-option-dependencies`, which is different from Claude's two tasks and is not in the bundle's curated `verdict/samples/`, produced gold reward 1 and agent reward 0 in distinct clean containers. The agent failed a real TypeScript build with `Expected ',' but found '{'` at `src/primitives.ts:665:17`; this was not an infrastructure failure. (`$XOPT/codex_repro_summary.json:3-44`; `$XOPT/gold/verifier.stdout.txt:4054-4213`; `$XOPT/agent/verifier.stdout.txt:1-32`; `$XOPT/agent/verifier.stderr.txt:2-10,26-34`)
4. A second fresh **Rust** reproduction of `fd-deterministic-multi-key-sorting` likewise produced gold reward 1 and agent reward 0. Gold ran 106 baseline tests and 47 new tests with zero failures; the agent generated malformed Rust and failed compilation. (`$XFD/codex_repro_summary.json:3-44`; `$XFD/gold/verifier.stdout.txt:12-176`; `$XFD/agent/verifier.stdout.txt:1-13`; `$XFD/agent/verifier.stderr.txt:68-180`)
5. I freshly reran all four manually promoted gold-valid tasks with proxy variables explicitly unset. The three HTTPX gold patches passed while their agent patches failed; `testem-per-launcher-reports` passed gold twice and failed agent three times. Thus the manual correction does not launder an agent success into the denominator. (`$XCLEAN/clean_correction_summary.json:2-42,51-89,98-136,145-238`)

I therefore explicitly reject **FAKE** under the definition in the brief. I found no evidence that the zero is an artifact of a systematically broken scoring pipeline. I did find defects serious enough that the same evidence methodology should not be reused without repair.

---

## Identity and methodology disclosure

This document is the independent OpenAI Codex-family pass requested as auditor B. It was produced by the genuine Codex-family agent in this session, not by Claude. I treated the supplied “CLAUDE'S CLAIMS” only as hypotheses to attack. I used independent Codex-family static, reducer, and critic lanes in parallel, but the final verdict and all fresh-container actions reported here are my responsibility. No Claude agent performed my shell checks or wrote this report.

The local Mac was used only as the control plane. Every project inspection, Docker action, test execution, hash check, and fresh reproduction ran over the exact supplied SSH endpoint. Every remote invocation had a remote `/bin/timeout`; the two longer fresh reproductions were launched from local `tmux`. I did not modify the audited Git worktree or bundle. My only remote writes were isolated audit outputs beneath `$BM/tmp/codex_auditor_b_*`; every `codex-b-*` Docker container was removed at the end.

Path abbreviations used in citations:

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
$META   = $XFD
```

The evidence-bundle worktree was clean at exact HEAD `6c23a02d9fd7cbfdb3d18fe65e7beb12cbd1573d`; the commit contains 68 files, all below `$B`. This proves current bundle scope, not historical execution-source identity. (Raw Git output is reproduced below; `$B/commit_msg.txt:1-9`; `$B/TRACE.md:4-11`)

---

## Disposition of Claude's 13 claims

| # | Disposition | Independent finding |
|---:|---|---|
| 1 | **CONFIRMED, but qualified** | The sealed audit `results.jsonl` has 113 unique rows, with `agent_reward=0` on 46 and `null` on 67; it never contains 1. (`$B/results.jsonl:1-113`; `$META/capture_inventory.json:2-10`) The more probative original live corpus has reward 0 on all 113 and verifier RC 0 on all 113. (`$META/capture_inventory.json:54-62`) Qualification: the sealed file is a lossy replay ledger, not complete per-task ground truth for the 67 null rows; the original full-workspace verifier corpus is the stronger evidence. |
| 2 | **REFUTED AS LITERALLY WORDED; CORRECTED CONCLUSION CONFIRMED** | Raw `results.jsonl` contains only **102** gold ones and **11** gold zeros. Within the corrected 106-ID set, raw gold is 102 ones plus 4 zeros, not 106 ones. (`$META/capture_inventory.json:6-27`) The four raw-zero overrides are `httpx-deterministic-cookie-store`, `httpx-multipart-response-parsing`, `httpx-streaming-json-iteration`, and `testem-per-launcher-reports`. (`$B/results.jsonl:38,40-41,99`; `$B/denom_assert.txt:15-24`) I independently closed that gap: with proxies unset, all four gold patches passed, while all four agent patches failed; testem was repeated 2/2 gold passes and 0/3 agent passes. (`$XCLEAN/clean_correction_summary.json:2-42,51-89,98-136,145-238`) The corrected conclusion is therefore 102 raw gold passes + 4 justified overrides = 106 corrected-valid tasks, with no agent reward 1. The remaining 7 corrected-broken IDs all have raw gold 0. (`$B/gold_validation/gold_broken_ids.txt:2-8`; `$B/denom_assert.txt:25-32`) |
| 3 | **CONFIRMED mechanically** | After removing comments and extracting the ID column, the Instruct and Coder valid-ID streams are byte-identical, each 106 lines, with SHA-256 `c28ddd1d08d89863738e5811d691094ba33361d3e5f2092c5de6839527ecef3f`; `diff` returned 0. (`$B/gold_validation/gold_valid_ids.txt:3-108`; Coder bundle `gold_validation/gold_valid_ids.txt:3-108`) This is consistency evidence, not proof that the Instruct correction was independently generated; the prose says it reused Coder's correction. (`$B/AUDIT_NOTES.md:10-16`) |
| 4 | **CURRENT CODE CONFIRMED; COMPLETE PARITY CLAIM QUALIFIED/REFUTED** | Gold and replay use the same `git apply --whitespace=nowarn` form and the same `run_verifier()` in distinct fresh containers. (`$D:245-280,381-389`; `$O:207-220,244-302`) However, their payload provenance is not equivalent: gold gets the complete curated solution patch, while replay gets `prediction.patch.diff`, which is produced by `git diff <base_ref>` and omits untracked files. (`$D:301-332`; `$O:273-282`) Thus command/scorer parity is true, but semantic patch parity is false for many tasks. |
| 5 | **CLAUDE'S EXACT TWO RERUNS NOT REPEATED; REQUIREMENT REPLACED WITH TWO INDEPENDENT TASKS** | I intentionally did not treat Claude's dateutil/etree stdout as established by me. Instead I freshly reran `optique-conditional-option-dependencies` (TypeScript, outside curated samples) and `fd-deterministic-multi-key-sorting` (Rust), with forced tar SHA recomputation and `docker load`, separate clean gold/agent containers, clean pre-state, real task tests, and raw failure inspection. Both reproduced gold 1 / agent 0. (`$XOPT/codex_repro_summary.json:3-44`; `$XFD/codex_repro_summary.json:3-44`) I therefore cannot independently sign the exact AttributeError/Go-error details of Claude's two selected tasks, but my different-task checks support the same global conclusion. |
| 6 | **CONFIRMED** | `VENV_PREFIX` activates `/opt/venv` when present and is prepended to the verifier command. (`$D:57-63,245-260`) My clean HTTPX reproductions executed real Python verification and returned normal verifier RC 0 rather than `No module named pytest`; gold passed and agent failed on code/test grounds. (`$XCLEAN/clean_correction_summary.json:2-42,51-89,98-136`) I did not rerun Claude's dateutil task specifically. |
| 7 | **CONFIRMED AND MORE STRONGLY RETESTED** | `container_env()` injects `100.100.0.0/16` and the serving host into both `NO_PROXY` variants for every `dexec`. (`$D:179-201,215-223`) The raw-to-corrected split is documented as 102/11 to 106/7. (`$B/summary.json:24-42`; `$B/denom_assert.txt:15-24`) I did not merely reconcile language counts: I ran fresh clean-environment gold and agent checks for all four overrides. Every gold passed; every agent failed. (`$XCLEAN/clean_correction_summary.json:2-238`) The by-language delta reconciles mechanically under the declared tags, but several declared language tags are themselves wrong; see new defect F. |
| 8 | **CONFIRMED LIVE, point-in-time** | My live probe returned `model_path=.../Qwen3-30B-A3B-Instruct-2507` on port 30000 and `model_path=.../Qwen3-Coder-30B-A3B-Instruct` on port 30001. Historical bundle probes identify the same Instruct path before and after the agent run. (`$B/serving/agent_run_get_model_info_before.json:1`; `$B/serving/agent_run_get_model_info_after.json:1`; `$B/summary.json:76-84`) A current endpoint probe cannot by itself prove historical identity, so the stored per-task commands/probes remain part of the chain. |
| 9 | **66/66 CHECK CONFIRMED; “EVERY FILE SEALED” REFUTED** | `sha256sum -c SHA256SUMS` printed 66 `OK` lines and exited 0. (`$B/SHA256SUMS:1-66`) The bundle has 68 Git-tracked files; entries missing from the manifest are `SHA256SUMS` itself and substantive `commit_msg.txt`. Thus `$B/TRACE.md:11` and `$B/README.md:26` overclaim “every file.” The clean exact Git commit still protects `commit_msg.txt`, so this is a checksum-manifest coverage defect, not evidence of score tampering. |
| 10 | **CONFIRMED NARROWLY; HISTORICAL-SOURCE INFERENCE REJECTED** | `git show` reports 68 changed files and an independent path-prefix check found zero outside `$B`. The worktree is clean at exact HEAD. This commit could not directly change the external driver/orchestrator. But those sources live under `$BM/deepswe_pathA`, outside any Git repository and outside `SHA256SUMS`; the commit therefore does not prove which source bytes executed historically. (`$B/TRACE.md:4-9`; `$B/SHA256SUMS:1-66`; current `$D:1-482`; current `$O:1-490`) |
| 11 | **CONFIRMED ONLY AS PRESENT-DISK INVENTORY** | The current run-root inventory contains exactly `full113_instruct_20260713T103633Z`, `audit_full113_instruct_20260713T144617Z`, `smoke_instruct_20260713T103311Z`, and `reverify_testem_20260713T150553Z`. The selected roots are also recorded in `$B/summary.json:7-8`. This cannot prove that a discarded directory was never deleted or renamed; it only confirms what is present now. |
| 12 | **CONFIRMED AND EXPANDED** | `calibration.md` says “1 of 106,” but corrected-valid audit counts are 51 nonempty captured patches and 42 successfully applied patches. (`$B/calibration.md:8-12`; `$META/capture_inventory.json:16-22`) More importantly, 45 corrected-valid live worktrees had untracked files, including 19 with only untracked changes; the statement that edits “ARE captured” is false. (`$META/capture_inventory.json:28-29`; `$B/summary.json:71-75`) The reward zero remains supported by the original full-workspace verification, not the prose count. |
| 13 | **CONFIRMED** | On my independently chosen `fd` task, the raw stream contains 96 JSON events, 31 nested `tool_use` blocks, and 31 nested `tool_result` blocks, while stored `stream_analysis.json` says 0/0. (`$L/fd-deterministic-multi-key-sorting/agent/qwen.stdout.jsonl:1-96`; `$L/fd-deterministic-multi-key-sorting/agent/stream_analysis.json:1-10`) The bug is caused by checking top-level types and only the first 200 JSON characters. (`$D:349-377`) `classify()` uses reward, JSON-event count, and tracked-patch nonemptiness, not the tool counters. (`$O:77-97`) This counter bug is diagnostic-only, although `patch_nonempty` has a separate material untracked-file bug. |

---

## Fresh reproduction A — independent TypeScript task outside curated samples

### Selection and procedure

I selected `optique-conditional-option-dependencies`, not either Claude task and not any task under `$B/verdict/samples/`. The sealed audit row records a nonempty, successfully applied agent patch and agent reward 0; the original live post-agent status contains a tracked modification to `packages/core/src/primitives.ts`, with no model-created untracked source file, so the saved replay payload is complete for the agent edit in this task. (`$B/results.jsonl:68`; `$L/optique-conditional-option-dependencies/agent/post_agent_git_status.txt:1`; `$L/optique-conditional-option-dependencies/agent/prediction.patch.diff:1-256`)

The bounded remote job did the following:

1. Loaded the manifest row, recomputed the fallback tar SHA-256, required it to match, and forced `docker load -i` without removing the cached tag.
2. Created a new gold container and a different new agent container from the loaded image.
3. In each container, recorded Git HEAD/status and confirmed `/logs/verifier/reward.txt` was missing before application.
4. Applied `solution/solution.patch` in the gold container and the captured `prediction.patch.diff` in the agent container with `git apply --whitespace=nowarn`.
5. Called the driver's task-owned verifier and retained raw stdout/stderr/result files.
6. Removed both containers; a final `docker ps -a --filter name=codex-b-` returned no rows.

The manifest and recomputed tar digest were both `f5d2e780151bf9663a8c75a0ece4da9060f5eef25dae7140d0d7e1821c5c78c7`. The summary itself has SHA-256 `1018b788badc20219a52548e4cd265a24231b650ff2217372979cfc8250d5298`. (`$XOPT/codex_repro_summary.json:3-5`)

### Raw result output

```text
IMAGE_SHA256
manifest   f5d2e780151bf9663a8c75a0ece4da9060f5eef25dae7140d0d7e1821c5c78c7
recomputed f5d2e780151bf9663a8c75a0ece4da9060f5eef25dae7140d0d7e1821c5c78c7
match      true

GOLD
container 0dac99aedb2a43d77a6de112395e663e100f180bf96a9ff3739caa6c28f047d7
created   2026-07-13T16:13:02.078533056Z
pre       HEAD=14bbe4efc7ded67932771b9ca18d9d637bb4cf27; STATUS empty; REWARD_PRE=MISSING
apply     rc=0, APPLIED_OK=true
verifier  rc=0, reward_raw=1, reward=1, seconds=4.9
tests     baseline exit=0; 36/36 new tests passed; new exit=0

AGENT
container da9a4f6b93efa0721ddb2fd78924290f8b3987ac629cb00557dd18b290ea8eff
created   2026-07-13T16:13:09.133742915Z
pre       HEAD=14bbe4efc7ded67932771b9ca18d9d637bb4cf27; STATUS empty; REWARD_PRE=MISSING
apply     rc=0, APPLIED_OK=true
verifier  rc=0, reward_raw=0, reward=0, seconds=3.2
tests     baseline exit=1; new exit=1
```

These fields are preserved verbatim in `$XOPT/codex_repro_summary.json:8-40`, `$XOPT/gold/verifier.result.json:2-6`, and `$XOPT/agent/verifier.result.json:2-6`.

The raw agent failure was a real model-authored parse error, twice encountered because both baseline and new modes build the same broken source:

```text
[PARSE_ERROR] Error: Expected `,` but found `{`
  --> src/primitives.ts:665:17
665 |                 {eOptionName(context.buffer[0])}
    |                 ^ `,` expected
```

The corresponding raw evidence is at `$XOPT/agent/verifier.stderr.txt:2-10,26-34`; the verifier's normal control flow and exit markers are at `$XOPT/agent/verifier.stdout.txt:1-32`. This is not a missing tool, Docker crash, missing dependency, test timeout, hidden reward-file problem, or proxy-dependent assertion. Gold's raw output shows a genuine full build and 2,497 baseline passes plus 36/36 new passes. (`$XOPT/gold/verifier.stdout.txt:4046-4054,4204-4213`)

### Reproduction command shape

The long job ran from local `tmux`, with the exact endpoint and a remote cap:

```bash
ssh -o ConnectTimeout=30 -o BatchMode=yes -o StrictHostKeyChecking=no -CAXY \
  env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn \
  'timeout 900 python3 - \
    /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/deepswe_qwencode_driver_instruct.py \
    optique-conditional-option-dependencies \
    /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/deepswe_pathA/runs/full113_instruct_20260713T103633Z \
    /mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/tmp/codex_auditor_b_optique_20260713T161500Z' \
  < remote_fresh_repro.py
```

The small stdin script imported `$D`, independently recomputed and checked the tar hash, forced `docker load`, created distinct containers, checked their pre-state, and called `apply_solution()` / `run_verifier()` plus an equivalent agent `git apply`. The complete retained artifacts, rather than terminal truncation, are the cited record.

---

## Fresh reproduction B — independent Rust corroboration

I also reran `fd-deterministic-multi-key-sorting`, which is different from both Claude tasks. This task happens to be one of the bundle's curated samples, so I treat it as corroboration rather than my primary independent sample. I nevertheless forced a fresh tar SHA computation and `docker load`, used two distinct new containers, and read the complete raw compiler output myself.

The manifest and recomputed tar digest were both `ab65807cab66ee7cd40111b7d5a8413984b09cfcb4dad57a7c12e6b2575bc18c`. Gold and agent began at the same clean HEAD with empty status and missing reward file. Gold and agent container IDs and creation timestamps are distinct. (`$XFD/codex_repro_summary.json:3-16,25-40`)

```text
GOLD:  apply_rc=0; verifier_rc=0; reward=1; 26.5s
       baseline: 106 passed, 0 failed, exit 0
       new:       47 passed, 0 failed, exit 0

AGENT: apply_rc=0; verifier_rc=0; reward=0; 24.1s
       baseline exit 101; new exit 101
```

The raw records are `$XFD/gold/verifier.result.json:2-6`, `$XFD/agent/verifier.result.json:2-6`, `$XFD/gold/verifier.stdout.txt:12-176`, and `$XFD/agent/verifier.stdout.txt:1-13`.

Representative model-authored compiler errors were:

```text
src/cli.rs:53:5       expected identifier, found keyword `enum`
src/walk.rs:509:38   expected identifier, found reserved keyword `gen`
src/main.rs:68:27    malformed eprintln!([fd error]: ...)
src/walk.rs:503      unresolved crate `rand`
src/walk.rs:326      undeclared type `SortField`
```

The complete excerpts are at `$XFD/agent/verifier.stderr.txt:68-180`. They are ordinary Rust parse/name/dependency errors, not infrastructure failures. The representative task wrapper confirms `/app` as the working directory, full-worktree capture, hidden-test application, and reward-1 only on dual zero exits. (`$TASKS/fd-deterministic-multi-key-sorting/tests/test.sh:9-12,14-61,64-104,112-133`)

---

## Independent challenge to the four corrected gold-valid tasks

Claude's claim 2 was the riskiest arithmetic statement because the raw bundle does **not** contain 106 gold ones. It contains 102, then promotes four raw failures. Merely changing the denominator while leaving agent tests under a polluted environment would be asymmetric and potentially score-laundering. I therefore reran both gold and agent for all four with this command prefix before the task verifier:

```text
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY NO_PROXY no_proxy ALL_PROXY all_proxy;
[ -f /opt/venv/bin/activate ] && {
  export VIRTUAL_ENV=/opt/venv;
  export PATH="/opt/venv/bin:$PATH";
};
```

That exact prefix is recorded at `$XCLEAN/clean_correction_summary.json:2`.

| Task | Fresh clean gold | Fresh clean agent | Independent outcome |
|---|---:|---:|---|
| `httpx-deterministic-cookie-store` | 1, RC 0 | 0, RC 0 | Gold override valid; agent has an unterminated Python string / syntax failure. (`$XCLEAN/clean_correction_summary.json:4-42`; `$XCLEAN/httpx-deterministic-cookie-store/agent_1/verifier.stderr.txt:2-31`) |
| `httpx-multipart-response-parsing` | 1, RC 0 | 0, RC 0 | Gold override valid; agent ends with 122 failures and 11 errors, not a proxy-only failure. (`$XCLEAN/clean_correction_summary.json:51-89`; `$XCLEAN/httpx-multipart-response-parsing/agent_1/verifier.stdout.txt:9631-9632`) |
| `httpx-streaming-json-iteration` | 1, RC 0 | 0, RC 0 | Gold override valid; agent has `async for` outside an async function. (`$XCLEAN/clean_correction_summary.json:98-136`; `$XCLEAN/httpx-streaming-json-iteration/agent_1/verifier.stderr.txt:1-30`) |
| `testem-per-launcher-reports` | 1 twice, RC 0 | 0 three times, RC 0 | The flake correction reproduced 2/2 for gold; the agent reproduced 0/3 with genuine launcher/report-state TypeErrors and assertions. (`$XCLEAN/clean_correction_summary.json:145-238`; `$XCLEAN/testem-per-launcher-reports/agent_1/verifier.stdout.txt:1-1787`) |

Raw summary output:

```text
httpx-deterministic-cookie-store: gold [1]; agent [0]
httpx-multipart-response-parsing:  gold [1]; agent [0]
httpx-streaming-json-iteration:    gold [1]; agent [0]
testem-per-launcher-reports:       gold [1,1]; agent [0,0,0]
all verifier_rc = 0
all fresh pre-states: clean HEAD, REWARD_PRE=MISSING
```

The summary has SHA-256 `d3f561f25e336ceb5e31b91d43399de7b4056820821bd10c7933313435757519`. These reruns independently support the corrected 106/7 split and show that none of the four corrections hides an Instruct success. They also expose documentation drift: `$B/AUDIT_NOTES.md:10-16` says “4 httpx/happy-dom,” whereas this Instruct bundle actually promotes three HTTPX tasks plus testem; `$B/denom_assert.txt:19-24` contains the accurate Instruct list.

---

## Raw arithmetic, verifier integrity, and provenance checks

### Sealed audit reducer

My independent reducer over `$B/results.jsonl:1-113` and the corrected ID files produced:

```text
audit rows                     113 (unique IDs: 113)
audit agent_reward              46 x 0, 67 x null, 0 x 1
raw gold_reward                102 x 1, 11 x 0
corrected valid IDs            106
corrected-valid raw gold       102 x 1, 4 x 0
corrected-valid agent reward    42 x 0, 64 x null, 0 x 1
corrected broken IDs             7 (all raw gold 0)
valid patch nonempty            51
valid patch applied             42
```

The machine-readable audit capture is `$META/capture_inventory.json:2-29`; its SHA-256 is `99e19019bc03f18fd7481d40c8fbcd31b37907a50411f140ef490107da7547b7`.

### Original full-workspace corpus—the strongest score evidence

The later replay is not the authority I rely on. The original run called `run_agent()` and then `run_verifier()` in the **same container**, removing the container only afterward. (`$O:222-242`) Therefore the verifier saw tracked edits, untracked files, and any other live filesystem state that existed at the scoring cutoff.

The original corpus independently reduces to:

```text
live reward                   {0: 113}
live verifier_rc              {0: 113}
verifier stdout marker files       113
baseline exits                0:63, 1:38, 2:6, 4:3, 43:1, 101:2
new-test exits                1:90, 2:11, 4:3, 25:1, 54:1, 79:1, 90:1, 101:5
both baseline and new zero           0
max verifier seconds              507.5
per-task result/summary mismatches     0
```

These figures are recorded at `$META/capture_inventory.json:35-62`. In particular, **new-test exit 0 does not occur at all**, so none of the 113 agent workspaces passed its new tests—even on rows where the baseline also failed.

The external structured live ledger is not itself listed in the bundle's checksum manifest. However, its 113 per-task result records agree with the raw per-task verifier artifacts, and the SHA-covered copy `$B/agent_run_orchestrator.log:5-118` independently records all 113 `DONE` rows with reward 0 and verifier RC 0. Model probes are at the beginning and end of that log, and the final zero report follows at `$B/agent_run_orchestrator.log:119-121`. This is a stronger chain than trusting `$B/summary.json` alone.

### Verifier return codes, timeouts, working directory, and stale reward

For this run, all 113 original agent verifiers, all 113 raw gold verifiers, and all 46 executed audit agent re-verifiers returned RC 0. (`$META/capture_inventory.json:54-62`; `$B/results.jsonl:1-113`) Audit maxima were 427.2 seconds for gold and 249.2 seconds for replayed agent patches; original maximum was 507.5 seconds, all well below the configured 1,800-second verifier timeout. (`$B/results.jsonl:1-113`; `$META/capture_inventory.json:61`; `$D:405-406`)

`subprocess.TimeoutExpired` is not converted to reward 0 by `run_verifier`; it propagates to the orchestrator's exception path, which writes `infra_error`. (`$D:89-90,245-280`; `$O:304-340`) I found no verifier timeout masquerading as a score failure.

Every `docker exec` specifies `-w /app`, and `start_container()` creates a fresh container with no `/app` host bind mount. (`$D:204-223`) Gold and replay use separately created containers. (`$O:244-302`) `run_verifier()` does not explicitly delete an old reward file, which is a latent hardening gap, but the audited orchestration invokes it once per fresh container; both my fresh reproductions independently recorded `REWARD_PRE=MISSING`. (`$XOPT/codex_repro_summary.json:16,33`; `$XFD/codex_repro_summary.json:16,33`)

### Valid-set identity

Independent raw command/output:

```text
DIFF_RC=0
c28ddd1d08d89863738e5811d691094ba33361d3e5f2092c5de6839527ecef3f  instruct ID stream
c28ddd1d08d89863738e5811d691094ba33361d3e5f2092c5de6839527ecef3f  coder ID stream
```

The cited source ranges are `$B/gold_validation/gold_valid_ids.txt:3-108` and the sibling Coder bundle's `gold_validation/gold_valid_ids.txt:3-108`.

### SHA manifest and Git scope

`sha256sum -c` returned 66/66 OK and exit 0. The raw tail was:

```text
./verdict/samples/typescript__cliffy-config-file-parsing/gold/verifier.stdout.txt: OK
CHECK_RC=0
ENTRY_COUNT=66
```

The entire entry list is `$B/SHA256SUMS:1-66`. Independent coverage comparison returned:

```text
tracked_bundle_files 68
checksum_entries     66
tracked_not_in_sha   ['SHA256SUMS', 'commit_msg.txt']
sha_not_tracked      []
```

The corresponding Git check returned:

```text
HEAD=6c23a02d9fd7cbfdb3d18fe65e7beb12cbd1573d
STATUS_BEGIN
STATUS_END
FILE_COUNT=68
OUTSIDE_COUNT=0
68 files changed, 8094 insertions(+)
```

This validates current commit scope but refutes `$B/TRACE.md:11` and `$B/README.md:26` as literal checksum-coverage statements.

### Serving identity

My live point-in-time output was:

```text
PORT30000
model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-30B-A3B-Instruct-2507
model_type=qwen3_moe
architectures=[Qwen3MoeForCausalLM]

PORT30001
model_path=/mnt/shared-storage-user/mineru2-shared/zengweijun/models/Qwen3-Coder-30B-A3B-Instruct
model_type=qwen3_moe
architectures=[Qwen3MoeForCausalLM]
```

The historical stored Instruct identity is at `$B/serving/agent_run_get_model_info_before.json:1` and `$B/serving/agent_run_get_model_info_after.json:1`; the command/model binding is summarized at `$B/summary.json:76-84`.

### Present-disk run inventory

```text
audit_full113_instruct_20260713T144617Z
full113_instruct_20260713T103633Z
reverify_testem_20260713T150553Z
smoke_instruct_20260713T103311Z
```

This agrees with `$B/summary.json:7-8` and `$B/denom_assert.txt:22-24`, but it is not evidence that deletion never occurred.

---

## New bugs and evidence defects found

### A. MAJOR evidence defect: captured agent patches omit untracked files

The driver snapshots the candidate with:

```python
git -c core.fileMode=false diff --binary <base_ref>
git status --short --untracked-files=all
```

It saves only `diff.stdout` as `prediction.patch.diff`. (`$D:301-332`) Plain `git diff <base_ref>` excludes untracked files. The status artifact records those paths, but the replay patch does not contain them.

Measured impact across the original live run:

```text
tasks with untracked files                  48 / 113
untracked-only tasks                        19 / 113
mixed tracked + untracked tasks             29 / 113
corrected-valid tasks with untracked files  45 / 106
corrected-valid untracked-only tasks         19 / 106
```

The aggregate counts are at `$META/capture_inventory.json:28-29,445-446,499-747`. Every one of those 48 live workspaces nevertheless has original reward 0; representative entries explicitly pair `live_reward: 0` with the omitted files. (`$META/capture_inventory.json:63-443,500-747`)

The corrected-valid replay accounting is therefore:

```text
106 corrected-valid tasks
  42 saved tracked patches applied and were reverified -> reward 0
   9 nonempty saved tracked patches failed to apply    -> reward null
  55 saved tracked patches were empty                  -> reward null
       of these, 19 actually had untracked model files
       only 36 were clean by tracked-diff + untracked-status evidence
```

The 51/nonempty and 42/applied counts are at `$META/capture_inventory.json:16-22`; 45 valid-with-untracked and 19 valid-untracked-only are at lines 28-29. Thus `$B/summary.json:71-75` is materially misleading when it labels all 64 nulls “no applicable patch,” and `$B/calibration.md:8-12` is false both in count and in saying edits are captured.

The task verifier already has the correct capture mechanism: it soft-resets to the model base, runs `git add -A -- .`, and writes `git diff --cached --binary` to `/logs/artifacts/model.patch`, including untracked files. (`$TASKS/fd-deterministic-multi-key-sorting/tests/test.sh:14-61`) But the driver retains only the first 4,000 bytes of that full artifact and then destroys the container. (`$D:269-271`; `$O:229-231`) The obvious repair is to copy the complete artifact out and use it for audit replay.

An untracked-only example makes the defect concrete. `wazero-multi-module-snapshots` has:

```text
?? experimental/snapshot/snapshot.go
```

at `$L/wazero-multi-module-snapshots/agent/post_agent_git_status.txt:1`, while its saved `prediction.patch.diff` is empty and the audit row records null at `$B/results.jsonl:104`. The original same-container verifier did see the new file, returned reward 0/RC 0, and reported the substantive compile error `package gzip is not in std`. (`$L/wazero-multi-module-snapshots/agent/verifier.result.json:2-6`; `$L/wazero-multi-module-snapshots/agent/verifier.stdout.txt:9-20`; `$L/wazero-multi-module-snapshots/agent/verifier.stderr.txt:1-2`)

**Impact on verdict:** material to replay fidelity, patch/no-patch diagnosis, and evidence closure; **not evidence of a hidden pass**, because the original verifier executed in the complete live worktree and every original new-test exit was nonzero. (`$O:222-242`; `$META/capture_inventory.json:35-62`)

### B. MAJOR runtime hardening defect: timeout does not quiesce the in-container agent

The driver catches `subprocess.TimeoutExpired`, records agent RC `-100`, and then immediately runs Git diff/status and the verifier. It does not issue an in-container kill, inspect remaining processes, or wait for quiescence. (`$D:314-332`; `$O:222-231`)

Five original rollouts hit the 2,400-second agent timeout:

```text
httpx-deterministic-cookie-store
ipython-session-bundle-replay
langchain-request-coalescing
participle-grammar-conflict-analysis
scc-bounded-memory-spilling
```

Their structured facts are at `$META/capture_inventory.json:447-499`. All five were subsequently verified with live reward 0; three have stable replay reward 0, while the two untracked-only cases have replay null but real original failures. (`$META/capture_inventory.json:447-499`; `$L/ipython-session-bundle-replay/agent/verifier.stdout.txt:22-53`; `$L/participle-grammar-conflict-analysis/agent/verifier.stdout.txt:9-18`)

I tested the platform semantics in a disposable container using the same Python `subprocess.run(..., timeout=...)` around `docker exec`. One second after timeout, and after another two-second wait, the in-container shell remained alive:

```text
timeout_raised=true
PID=7
PROCESS_ALIVE=yes
DONE=no
7  0  Ss  bash -c ... sleep 30 ...
docker_rm rc=0
```

The retained probe is `$META/docker_exec_timeout_probe.json:1-22`, SHA-256 `678cb27ddf83b2167494a4f68a993a417d6b8de57dacee01b659f7de00ea2016`. This proves the underlying `docker exec` timeout mode can leave the in-container process alive. It does **not** prove that the actual Qwen process survived in all five historical tasks; there is no historical `docker top` capture, kill log, or quiescence probe, and Qwen may behave differently on a broken output channel. I therefore classify the actual five-task race as a demonstrated risk, not a demonstrated score corruption.

The diagnostic status is also wrong: `classify()` never consults `ag["timed_out"]`, so the five timeouts are labeled ordinary `unsolved` or `unsolved_no_patch` rather than the advertised rollout-timeout status. (`$O:77-97,222-240`; `$META/capture_inventory.json:447-499`)

**Impact on verdict:** a serious reproducibility/race flaw, but no affirmative hidden pass. Three timeout patches stably replay to 0; the two omitted untracked-only workspaces fail real tests at the scoring cutoff. This must be fixed before reuse by explicitly terminating the in-container agent process group and polling for quiescence before snapshot or verification.

### C. MAJOR provenance gap: historical driver/orchestrator source is not sealed

The active `$BM/deepswe_pathA` directory is not a Git repository. The current files have hashes:

```text
0b73a18b841d139ba8a263617e5d524db76554a6b3d04faa48deb33252f3c054  deepswe_qwencode_driver_instruct.py
91a63c03157d8d148bc6a7e59d71df43c70797ec33d0ad6762d2b8bee2ab9247  deepswe_full113_orchestrator_instruct.py
```

Their current mtimes are 2026-07-13 18:31:33 +08, about five minutes before the agent launch recorded in the sealed log. (`$B/agent_run_orchestrator.log:1-5`; current `$D:1-482`; current `$O:1-490`) This chronology makes the current bytes plausible as the executed source, but no bundle file records these hashes, and neither source appears in `$B/SHA256SUMS:1-66`. `$B/TRACE.md:4-5` names the scripts without cryptographically binding them.

**Impact on verdict:** historical-source provenance is incomplete. It does not create affirmative evidence of tampering, and fresh reproductions using the current source agree with the raw score. Claim 10 must nevertheless remain narrow: commit `6c23a02` only proves the evidence commit did not edit verifier code inside that Git repo; it does not seal external execution code.

### D. Raw-versus-corrected semantics are misleading

The raw orchestrator computes valid rows strictly as `gold_reward == 1`, which yields 102/11. (`$O:430-451`; `$B/results.jsonl:1-113`) Later bundle-generation prose applies four external corrections to report 106/7. (`$B/summary.json:24-42`; `$B/denom_assert.txt:15-24`)

Consequently:

- `$B/README.md:5-8,29` and `$B/calibration.md:13` are false if read as claims about the raw `gold_reward` field.
- Four corrected-valid rows retain raw status `task_broken_gold_fail`. (`$B/results.jsonl:38,40-41,99`)
- `$B/AUDIT_NOTES.md:10-16` contains a stale copied “httpx/happy-dom” description; `$B/denom_assert.txt:19-24` contains the actual three-HTTPX-plus-testem correction.

My clean reruns validate the corrected result, so this is a schema/documentation defect rather than a numerator defect. The bundle should carry explicit `gold_reward_raw`, `gold_reward_corrected`, `correction_reason`, and corrected status fields in its primary structured rows.

### E. Ten nonempty patches are silently converted to null replay results

Across all 113 tasks, the original run saved 56 nonempty tracked patches, but only 46 applied during audit. Across the corrected-valid set, 51 were nonempty and only 42 applied. (`$META/capture_inventory.json:16-22`; `$B/results.jsonl:1-113`) Therefore ten nonempty patches failed atomic replay, nine of them corrected-valid.

The audit helper ignores the `docker cp` return code and returns only a boolean based on `APPLIED_OK`, not the actual `git apply` RC. (`$O:213-220`) Atomic `git apply` prevents a partially applied patch from being verified, which is good, but the resulting nulls are mislabeled as no applicable patch in `$B/summary.json:71-75`.

**Impact on verdict:** another replay-fidelity defect. The original complete workspaces for all ten had reward 0/RC 0, so no passing result is hidden in the observed run. (`$META/capture_inventory.json:35-62`)

### F. Language tags are wrong on at least four tasks

Spot-checking result tags against solution-patch file extensions found:

| Task | Stored tag | Patch language evidence |
|---|---|---|
| `httpx-deterministic-cookie-store` | TypeScript | Python `.py` files (`$B/results.jsonl:38`; `$TASKS/httpx-deterministic-cookie-store/solution/solution.patch:1-656`) |
| `prometheus-transactional-reload-status` | TypeScript | Go `.go` files (`$B/results.jsonl:85`; `$TASKS/prometheus-transactional-reload-status/solution/solution.patch:1-1228`) |
| `katex-multicolumn-array-spans` | JavaScript | TypeScript `.ts` files (`$B/results.jsonl:47`; `$TASKS/katex-multicolumn-array-spans/solution/solution.patch:1-713`) |
| `koota-entity-snapshot-rollback` | Python | TypeScript `.ts` files (`$B/results.jsonl:53`; `$TASKS/koota-entity-snapshot-rollback/solution/solution.patch:1-117`) |

**Impact on verdict:** aggregate 0/113 and 0/106 are unchanged, but `$B/by_lang.md:1-10` and `$B/summary.json:44-69` are not semantically reliable until task metadata is corrected. This also limits the evidentiary value of mechanically reconciling the raw-to-corrected “by language” deltas.

### G. Diagnostic tool-call counts are globally implausible and wrong

For the fresh Rust task's stored stream:

```text
JSON_EVENTS_PARSED 96
NESTED_TOOL_USE    31
NESTED_TOOL_RESULT 31
tool names: glob=1, read_file=12, grep_search=1, todo_write=1, edit=10, write_file=6
stored tool_calls  0
stored tool_results 0
```

The raw/stored sources are `$L/fd-deterministic-multi-key-sorting/agent/qwen.stdout.jsonl:1-96` and `$L/fd-deterministic-multi-key-sorting/agent/stream_analysis.json:1-10`. The parser bug is at `$D:349-377`; classification independence is at `$O:77-97`.

**Impact on verdict:** no direct reward impact. It invalidates interaction diagnostics and should be repaired by recursively parsing `message.content[]` for `tool_use` and `tool_result`.

### H. `verifier_rc` is a latent classifier hole

`classify()` reads `vrc` but checks `reward == 1` before using it, and in practice never gates a parseable reward on `verifier_rc == 0`. (`$O:77-97`) A future task script could write reward 1 and then exit nonzero, yet be classified resolved.

This latent path did not fire here: every executed live, gold, and replay verifier had RC 0. (`$META/capture_inventory.json:54-62`; `$B/results.jsonl:1-113`; `$XOPT/codex_repro_summary.json:17-22,34-39`; `$XFD/codex_repro_summary.json:17-22,34-39`) It does not affect this verdict, but score classification should require both `reward == 1` and `verifier_rc == 0`.

### I. Documentation and checksum defects

Confirmed documentation defects include:

- `calibration.md` says one captured patch; the corrected-valid counts are 51 nonempty / 42 applied, and 70 corrected-valid tasks had either tracked or untracked changes. (`$B/calibration.md:8-12`; `$META/capture_inventory.json:16-29`)
- `summary.json` calls 64 null rows “no applicable patch,” although 9 had nonempty apply failures and 19 of the empty saved patches had untracked-only edits. (`$B/summary.json:71-75`; `$META/capture_inventory.json:16-29`)
- `TRACE.md` and README say checksums cover every file, but `commit_msg.txt` is omitted. (`$B/TRACE.md:11`; `$B/README.md:26`; `$B/SHA256SUMS:1-66`)
- `AUDIT_NOTES.md` has the wrong fourth correction task. (`$B/AUDIT_NOTES.md:10-16`; `$B/denom_assert.txt:19-24`)

None changes the observed reward records; all should be corrected before publication or reuse.

---

## Why the defects do not flip the verdict to FAKE

The replay defect is the closest candidate for a fake zero, because it prevents faithful fresh re-evaluation of many candidate workspaces. It does not overturn this particular score for five independent reasons:

1. **The original score path did not replay a patch.** It ran the task verifier directly in the same container after the agent, before container removal. (`$O:222-242`)
2. **The task wrapper captured and tested the complete live worktree.** Its Step 0 uses `git add -A` and the tests execute against `/app`; untracked source files were therefore visible to compilation/tests. (`$TASKS/fd-deterministic-multi-key-sorting/tests/test.sh:9-61,112-133`)
3. **All 113 live verifier executions completed normally.** Every verifier RC is 0, every raw stdout has baseline and new-test markers, and no new-test exit is 0. (`$META/capture_inventory.json:35-62`)
4. **The sealed log independently records the original outcome.** It contains all 113 unique completion rows, all reward 0 and RC 0. (`$B/agent_run_orchestrator.log:5-118`)
5. **Fresh external checks agree.** Two different tasks in two languages reproduce gold 1 / agent 0, and all four corrected-valid overrides reproduce clean gold pass / agent fail. (`$XOPT/codex_repro_summary.json:3-44`; `$XFD/codex_repro_summary.json:3-44`; `$XCLEAN/clean_correction_summary.json:2-238`)

The timeout race and unsealed source prevent me from calling the historical process perfectly reproducible. They do not supply affirmative evidence that any agent workspace passed. The five timeout tasks have live reward 0/RC 0; three stably replay 0, and the two untracked-only cases have direct substantive failures at the enforced cutoff. (`$META/capture_inventory.json:447-499`; `$L/ipython-session-bundle-replay/agent/verifier.stdout.txt:22-53`; `$L/participle-grammar-conflict-analysis/agent/verifier.stdout.txt:9-18`)

Accordingly, the most precise defensible headline is:

> **Original live rewards: 0/113. Corrected-valid score: 0/106, where raw gold validation was 102/113 and four raw failures were independently justified as corrected-valid. REAL, with material replay, timeout, provenance, metadata, and documentation defects.**

---

## What I explicitly could not verify

1. I did not repeat Claude's exact dateutil and etree tasks, so I do not independently attest to the exact stdout/error details claimed for those two. I satisfied the independent-rerun requirement with TypeScript `optique` and Rust `fd` instead.
2. I did not fresh-rerun all 113 tasks. My full-corpus conclusions come from independent reducers and raw artifact joins; fresh execution covered two ordinary valid tasks plus all four corrected-valid overrides.
3. The current `$D` and `$O` bytes are not cryptographically bound to launch time. Their mtimes precede the run and fresh behavior agrees, but the historical exact-source claim remains unprovable from this bundle.
4. The present-disk run inventory cannot rule out a directory that was deleted or renamed before this audit.
5. The serving endpoint probe is current point-in-time evidence. Historical identity is supported by stored before/after and per-task artifacts, but no external hardware attestation is present.
6. My disposable timeout probe proves a surviving in-container-process mode for timed-out `docker exec`; it does not prove that the historical Qwen process actually survived in each of the five timed-out tasks.
7. My remote audit outputs under `$BM/tmp/codex_auditor_b_*` are independent artifacts, not part of commit `6c23a02` or its `SHA256SUMS`. I report their hashes above so later reviewers can detect changes, but they are not retroactively part of the sealed bundle.

---

## Required remediation before this evidence method is reused

1. Copy the complete task-generated `/logs/artifacts/model.patch` out of every live container; do not save only a 4,000-byte head and do not rely on tracked-only `git diff`.
2. Record the pristine image worktree state before generation and construct a replay patch relative to that state, including new files; validate patch round-trip before destroying the live container.
3. On agent timeout, explicitly terminate the in-container process group, verify quiescence with `docker top`/PID polling, then snapshot and test. Classify timeouts explicitly.
4. Seal exact driver, orchestrator, launch scripts, configuration, and their hashes at launch and teardown. Store them in the evidence commit.
5. Gate resolved status on `reward == 1 AND verifier_rc == 0`; delete any stale reward/artifact before verifier execution.
6. Make raw and corrected gold fields explicit in primary structured results and include correction provenance/reason per task.
7. Check `docker cp` and `git apply` return codes, record actual RC/stderr, and distinguish empty patch from nonempty apply failure.
8. Fix nested stream-event parsing, patch/no-patch diagnostics, language metadata, calibration prose, correction prose, and SHA-manifest coverage.

---

## Final Codex-family signature

**CODEX VERDICT: REAL.** I tried to falsify the score and could not. The zero is supported by complete original same-container verification and independent fresh failures, not by the later lossy replay alone. No BLOCKER demonstrating a systematically fake judge was found. The replay/capture and timeout defects are material and must be disclosed alongside the signature.

*Independent reviewer: OpenAI Codex-family agent, auditor B; local Mac control plane, bounded SSH/Docker execution on the supplied KVM host; 2026-07-13.*
