# `tb21_harness/` — the six files the official Terminal-Bench 2.1 runs depend on, none of which were in git

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

Canonical never hit this. It could not have: the runner it used no longer exists.

```
canonical run                     2026-07-05 15:55
r3 runner's mtime on disk today   2026-07-07 23:46      ← changed, two days later
```

## What that means

**The canonical `9/89 = 10.1%` cannot be reproduced from git.** The official harness reaches outside
the repository for three things, and every one of them was untracked when this directory was created:

```
run_terminal_bench_2_1_full89_batched_privileged_offline.sh   r3 worktree    UNTRACKED   mtime 07-07 23:46
run_terminal_bench_2_1_qwencode_batched_privileged_offline.sh r3 worktree    UNTRACKED   mtime 07-06 15:51
repair_tb21_full89_runtime_closure.py                         main worktree  UNTRACKED   mtime 07-02 12:13
run_terminal_bench_2_1.sh                                     swe/bench/shared           mtime 06-30 13:17
```

A fifth file, `nips2026/bench/run_terminal_bench_2_1.sh`, shares a name with the fourth and has
different content (`9ec75caa…` vs `3dcd4a1d…`). Two files, one name, no way to tell from a log which
one ran.

This is the second confirmed instance of the same failure in this repository. The first destroyed the
runner behind the canonical `70.8%` — untracked, overwritten, no git object, unrecoverable (§6 C1).
This one did not destroy anything, only because someone tried to run it and it failed loudly. Had the
`repair` script happened to exist in both worktrees, the run would have completed and produced a
number, and nobody would have learned that its runner had been edited after the score it is compared
against was measured.

**Any claim that a TB2.1 run used "the same configuration as canonical" must first pin these files by
hash.** `PROVENANCE.tsv` records the source path, mtime, `sha256`, and git status of each, as of the
moment they were copied.

## Do not run these

They derive `$REPO_ROOT` from `$0`. Run from here, they resolve to this directory and reach for
scripts that are not beside them — which is precisely the bug documented above, reproduced. The
execution copies stay where they are. These are for recovering what ran, and for detecting when the
thing on disk stops being it:

```
shasum -a 256 <source_path from PROVENANCE.tsv>
```

## Also here

`tb21_qwencode_agent.py` — the host-bridge agent (`QwenCodeTb21BridgeAgent`), 243 lines. Not the
official harness; it runs `qwen` on the host and reaches into the task container with `docker exec`.
It exists because Terminal-Bench's own `installed_agents/qwen_code` cannot run offline: its setup
script wants `apt-get`, GitHub, `nvm`, and `npm`. Kept for provenance of the `16.85%` and `13.48%` /
`14.61%` bridge measurements, which are contrast points and not leaderboard numbers.

Scanned by value before commit — `sk-*`, bearer tokens, JWTs, HF tokens, assigned `api_key=` literals.
7 files, 0 findings.
