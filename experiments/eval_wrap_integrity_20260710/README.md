# The file in the run directory is not the file that ran

`sweml_coder_qwencode0162_clean274_20260710t083916z` started at `08:39:16Z`. Its first container-cleanup
race — `make_run_report → containers.list → inspect → 404` — dropped a row at `08:57:20Z`, its second at
`09:53:29Z`, a third somewhere between.

The `eval_wrap.py` sitting in that run's directory has an mtime of **`10:27:03Z`**.

It was edited in place, ninety minutes after the first failure it was written to prevent, inside the
directory of a run that had already produced most of its results. The edit added a monkeypatch:

```python
_sweml_container_list = ContainerCollection.list
def _sweml_list_ignore_removed(self, *args, **kwargs):
    kwargs['ignore_removed'] = True
    return _sweml_container_list(self, *args, **kwargs)
ContainerCollection.list = _sweml_list_ignore_removed
```

The patch is correct. Its placement is not.

## The sha256 was the disguise

After the edit, the Coder run's `eval_wrap.py` and the Instruct run's — a *different* run, launched two
hours later — hash identically to `81cb668d25cecce85f0c…`. An auditor comparing the two runs would
conclude they used the same evaluation wrapper and be unable to explain why one lost three rows and the
other lost none.

**Two runs whose artifacts agree, whose executions did not.** A matching hash is evidence that two
*files* are the same. It is evidence about the *runs* only if neither file was touched after its run.

## Recovering what actually ran

No `.orig`, no `.bak`, no launch-time pin, no snapshot. **Status: `ORIGINAL_LOST`.**

The engineer who owns that run reviewed a first draft of this note, which claimed the pre-patch content
was "recovered by comparison," and rejected the promotion. It is a **recovery candidate**, not a
recovered file. The distinction is the whole subject of this directory.

The candidate, and its witnesses:

| | `sha256` | bytes | `ignore_removed` | when | rows dropped to the 404 race |
|---|---|---:|---:|---|---:|
| Multilingual **canary**, same lane | `dca24b59d3a4…` | 532 | **0** | `2026-07-10 08:07Z` — 32 min before launch | — |
| SWE-V × Coder | `dca24b59d3a4…` | 532 | **0** | `2026-07-09 16:05:54Z` | 4 |
| SWE-V × Instruct-2507 | `dca24b59d3a4…` | 532 | **0** | `2026-07-09 18:32:39Z` | 2 |
| **Multilingual × Coder**, as found on disk | `81cb668d25ce…` | 839 | 3 | mtime `2026-07-10 10:27:03Z` | **3** |

Three runs, none edited afterwards, carry the same 532-byte wrapper with no monkeypatch. The closest is
that run's own canary, thirty-two minutes before its launch. Two of the three were bitten by the race,
as the full run was.

**None of that proves what the full run loaded at `08:39:16Z`.** A witness standing thirty-two minutes
away is a better witness than one standing a day away. Neither was in the room. The candidate is
committed here beside the file that overwrote it; the run's own status carries `ORIGINAL_LOST`, and the
superseded hash freeze is retained rather than deleted.

## What this run's numbers still mean

The score is unaffected: `57/274` is computed from `results.jsonl` and the per-instance harness reports,
neither of which the wrapper touches. What is affected is the claim of *provenance* — and one real
inconsistency inside a single run:

> The 271 rows that landed normally were evaluated **without** `ignore_removed`.
> The 3 rows repaired afterwards were evaluated **with** it.
> One run, two evaluation environments. It must be declared, and it now is.

## The rule, and it is already in force

The `Multilingual × Instruct-2507` run, launched two hours later, pins its wrapper at launch:

```json
// provenance/EVAL_WRAP_LAUNCH_PIN.json
{ "sha256": "81cb668d…", "mtime": "2026-07-10T10:37:13.033571Z", "size": 839, "guard": true }
```

Re-verified at teardown. **A mismatch invalidates the run.** That run genuinely uses `ignore_removed`
throughout, and can say so with a hash taken before a single task started.

The Coder run cannot. Its final status now carries `MIXED_EVAL_ENVIRONMENTS_DISCLOSED`: its 271 main
rows were evaluated **without** the guard, and the 3 rows repaired afterwards **with** it. Which means
the two Multilingual runs — `Coder` and `Instruct-2507`, the pair anyone would want to compare — did
not share an evaluation environment, and only one of them can prove which environment it had.

Never edit a file inside a run directory. Not to fix a bug, not after the run, not ever. Fix the source
and start a new run. Pin the sha256 of every executed script at launch, and re-verify it at teardown; a
mismatch is a finding, not a formality.

This repository already carries two artifacts destroyed the same way: the runner behind the canonical
`70.8%`, untracked and overwritten and unrecoverable; and the `terminus-2` runner, edited two days after
the score it is compared against was measured. Both were somebody else's, some other week. This one is
ours, tonight, and it was found only because someone read an mtime.
