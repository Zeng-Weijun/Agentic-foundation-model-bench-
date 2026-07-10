# `tb21_harness/` — the scripts the official Terminal-Bench 2.1 runs depend on, most of which were not in git

## How this was found

An engineer relaunching TB2.1 × Qwen3-Coder × `terminus-2` watched it die in four minutes, `rc=2`,
before `tb` ever started: zero tasks, zero containers, no run root, nothing polluted.

Three things looked like the cause. All three were wrong:

| Looked guilty | Actually |
|---|---|
| `bench=terminal_bench_2_1_qwen_code` | `bench_common`'s default label — canonical prints the same line |
| `num_tasks=1` | the `NUM_TASKS` default — canonical too. The real selector is `TB_TASK_IDS` |
| `missing_artifact=1` | a consequence, not a cause |

The cause was one line. The runner derives `$REPO_ROOT` from its own location — the `tb21-image-fixes-r3`
worktree — and uses it to invoke `scripts/repair_tb21_full89_runtime_closure.py`. That file exists in
exactly one place on disk: the *main* worktree. `python3` exits `2`, `set -e` kills the chain before
`tb` runs.

## What is not under version control

Four of the scripts a canonical TB2.1 run passes through are untracked. `PROVENANCE.tsv` records path,
UTC mtime, `sha256`, git status, and whether each predates canonical's `tb` invocation at
`2026-07-05 15:55:10Z`.

```
stage_tb21_official_qwen_launcher.sh        UNTRACKED   15:51:06Z   4 minutes before canonical's tb
run_terminal_bench_2_1.sh (shared)          UNTRACKED   06-30
repair_tb21_full89_runtime_closure.py       UNTRACKED   07-02
run_terminal_bench_2_1_full89_batched...sh  UNTRACKED   07-07 15:46:48Z   ← after canonical
```

The last one is the only file in the `terminus-2` chain that changed after the score it is compared
against was measured. `bench_common` (06-03), the shared runner (06-30), `repair` (07-02), the `tb` CLI
`0.2.18` (07-02) and the stage launcher (07-05 15:51Z) all predate it.

## Three corrections to an earlier version of this file

**It said three untracked scripts. There are four.** `stage_tb21_official_qwen_launcher.sh` is itself
untracked, `sha a9d0434b…`, written four minutes before the run it launched.

**It said `nips2026/bench/run_terminal_bench_2_1.sh` and the `swe/bench/shared` file "share a name and
have different content — no way to tell from a log which one ran."** That was wrong twice. The first is
five lines:

```bash
#!/usr/bin/env bash
set -euo pipefail
export TB_AGENT="${TB_AGENT:-terminus-2}"
export TB_EXTRA_ARGS="${TB_EXTRA_ARGS:---no-rebuild}"
exec /mnt/.../swe/bench/shared/runners/run_terminal_bench_2_1.sh "$@"
```

It is a forwarder, not a rival version. The diff is `@@ -1,148 +1,5 @@`. Nothing in the repository
references it, and this run calls the shared runner directly — established from `TB21_RUNNER` being
unset in the live environment and from the r3 runner hardcoding the absolute path at line 595.

**And the real gotcha is the opposite of what was claimed.** Because the forwarder ends in `exec`, it
replaces itself with the shared runner: `/proc/<pid>/cmdline` shows the same thing whether the shared
runner was called directly or reached through the wrapper. *The process table cannot distinguish them.*
The environment can. Read `TB21_RUNNER`, not `ps`.

## The drift is real, bounded, and neutralised at every point where it could be observed

One file changed after canonical. That is a genuine reproducibility defect and it stays recorded. But
the three places it could have altered the measurement were each checked, and each came back identical:

**The command.** Canonical's `command.sh` and today's, tokenized and diffed field by field: the 89
task-ids match in **set and in order**; `--agent-kwarg temperature=0.0`, `--no-rebuild`, all three
timeouts, and `--dataset-path` are token-identical. Exactly one non-task flag differs: `api_base`.

**The dataset.** The frozen `r7` dataset has had no file modified since `2026-07-04 05:26Z`. Canonical
ran on 07-05, today's run on 07-10. Byte-identical.

**The repair step.** Today's run sets `TB2_RUNTIME_CLOSURE_REPAIR=""` and skips it. That is not an
argument that skipping is safe — it is empirically what canonical did, because canonical *ran* repair
and repair did nothing:

```
evidence/tb21_full89_runtime_closure_repair_20260705_155424.json
  generated_at_utc  2026-07-05T15:54:24Z    (46 seconds before canonical's tb)
  execute           true
  changes           []
```

`compose`, `run_tests`, `solution`, `test_outputs` — zero changed. Running the repair and skipping it
produce the same dataset. Skipping it also avoids rewriting a frozen shared dataset in place, which
`--execute` would do.

**So the caveat is narrower than it first appeared.** The runner drifted; every observable consequence
of that drift was checked and found to be nil. What remains genuinely unrecoverable is not the harness
at all — it is the **serving instance**. The host that produced canonical (`100.103.228.120:30000`) is
dead, and no artifact of that run recorded its sglang version, `tp_size`, attention backend, or
`mem_fraction_static`. §0 field 11 exists because of that, not because of these scripts.

## Do not run these

They derive `$REPO_ROOT` from `$0`. Run from here, they resolve to this directory and reach for scripts
that are not beside them — which is precisely the bug described at the top, reproduced. The execution
copies stay where they are. These are for recovering what ran, and for detecting when the thing on disk
stops being it:

```
shasum -a 256 <source_path from PROVENANCE.tsv>
```

## Also here

`tb21_qwencode_agent.py` — the host-bridge agent (`QwenCodeTb21BridgeAgent`), 243 lines. Not the
official harness; it runs `qwen` on the host and reaches into the task container with `docker exec`. It
exists because Terminal-Bench's own `installed_agents/qwen_code` cannot run offline: its setup script
wants `apt-get`, GitHub, `nvm`, and `npm`. Retained for the provenance of the `16.85%` / `13.48%` /
`14.61%` bridge measurements, which are contrast points and not leaderboard numbers. The bridge has
since been abandoned in favour of running `qwen` inside the task container.

Scanned by value before commit — `sk-*`, bearer tokens, JWTs, HF tokens, assigned `api_key=` literals.
Zero findings.
