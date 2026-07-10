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

No `.orig`, no `.bak`. The original content is gone from that directory. It is recoverable by comparison,
not by proof:

| | `sha256` | bytes | `ignore_removed` | run start | rows dropped to the 404 race |
|---|---|---:|---:|---|---:|
| SWE-V × Coder | `dca24b59d3a4…` | 532 | **0** | `2026-07-09 16:05:54Z` | 4 |
| SWE-V × Instruct-2507 | `dca24b59d3a4…` | 532 | **0** | `2026-07-09 18:32:39Z` | 2 |
| Multilingual × Coder | `81cb668d25ce…` | 839 | 3 | `2026-07-10 08:39:16Z` | **3** |

Two contemporaneous runs, never edited afterwards, carry the same 532-byte wrapper with no monkeypatch,
and both were bitten by the same race. The Multilingual Coder run was bitten too. The inference is that
it also ran the 532-byte version and was overwritten afterwards.

**`RECOVERED_BY_COMPARISON`, not `PROVEN`.** Both files are committed here. The pre-patch version is
what the evidence says ran; the post-patch version is what is on disk.

## What this run's numbers still mean

The score is unaffected: `57/274` is computed from `results.jsonl` and the per-instance harness reports,
neither of which the wrapper touches. What is affected is the claim of *provenance* — and one real
inconsistency inside a single run:

> The 271 rows that landed normally were evaluated **without** `ignore_removed`.
> The 3 rows repaired afterwards were evaluated **with** it.
> One run, two evaluation environments. It must be declared, and it now is.

## The rule

Never edit a file inside a run directory. Not to fix a bug, not after the run, not ever. Fix the source
and start a new run. Pin the sha256 of every executed script at launch, and re-verify it at teardown; a
mismatch is a finding, not a formality.

This repository already carries two artifacts destroyed the same way: the runner behind the canonical
`70.8%`, untracked and overwritten and unrecoverable; and the `terminus-2` runner, edited two days after
the score it is compared against was measured. Both were somebody else's, some other week. This one is
ours, tonight, and it was found only because someone read an mtime.
