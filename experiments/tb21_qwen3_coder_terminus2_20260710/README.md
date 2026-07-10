# TB2.1 × Qwen3-Coder-30B × `terminus-2` — 12/89 = 13.48%

This directory exists because an independent auditor, asked whether the artifacts on GitHub were
enough for a stranger to redo this run and prove the score untampered, said **no**. Its finding was
not that the evidence was poor. It was that the evidence lived on one machine, and that machine was a
single point of failure. Everything here was already on disk. None of it was anywhere else.

## The score, and why its exit code is 143

```
run_metadata.json   agent_name terminus-2 · dataset_size 89 · c=32 · attempts=1
                    accuracy 0.1348314606741573 · 06:52:08Z → 08:58:08Z
                    commit_hash 1a6ffa96  (the same commit as canonical)
independent recount 89 unique trials · 12 resolved · 12/89 = 13.48%
failure_mode        unset 79 · context_length_exceeded 7 · test_timeout 2 · agent_timeout 1
full.rc             143
```

`tb run` finished scoring at `08:58:08.646521Z`, wrote `results.json`, released every container — and
then did not exit. 62 threads, 61 of them parked in `futex_wait_queue_me` including the main thread,
zero children, 0.0% CPU, one leftover `ESTAB` socket to the inference endpoint. That is
`threading._shutdown()` joining a non-daemon thread. The work was done.

It was terminated by operator `SIGTERM` at `09:15:37Z`, **seventeen minutes and twenty-eight seconds
after the run had finished**. `full.rc` is `143` and stays `143`. Nothing was faked; `full.rc`'s
sha256 is identical before and after the score reducer ran.

**And that single non-zero exit code turned the whole table red.** The harness computes

```python
infra_fail = bool(missing_artifact or fatal_timeout or tb_rc not in (0, None))
```

so `strict_summary` reports `infra_fail = 89` — every task — with each row's `notes` containing
nothing but `['tb_rc=143']`. `missing_artifact = 0`. `parse_error = 0`. `clean_pass = 0` is the same
artifact. **`resolved = 12` is read from `raw_status` and is untouched.**

`scores.yaml` opens with `# RED-BUT-HONEST. This run's exit code is non-zero and stays non-zero.`

> **Rule (v5): `tb_rc` must be read relative to `end_time`.** A non-zero exit produced *after* the run
> finished is a process-lifecycle artifact, not a measurement fault. v4's rule 1 does not distinguish
> them, and would have marked a complete run as infrastructure-failed on the strength of a signal the
> operator sent.

The official ledger script (`tb21_qwen_official_ledger.py:90-92,124`) reads `tb21_strict_summary.json`
directly. Using it would have copied `infra_fail=89` into the ledger as fact. The reducer here
(`reduce_scores.py`) reads the 89 per-trial `results.json` and nothing else.

## Against canonical: no difference, and no borrowed σ

canonical `9/89 = 10.11%`. This run `12/89 = 13.48%`. McNemar, computed from the resolved-id sets:

```
                    today ✓   today ✗
canonical ✓            8         1      openssl-selfsigned-cert
canonical ✗            4        76      cobol-modernization · fix-code-vulnerability
                                         nginx-request-logging · qemu-startup

discordant = 5      exact two-sided binomial   p = 0.375
```

An earlier version of this note compared `+3 tasks` against a `σ_diff ≈ 3.32` measured on a
*different harness*. Transferring a variance estimate across harnesses is exactly the error that
estimate's own author had forbidden. McNemar needs no borrowed σ.

`Jaccard(canonical, today) = 0.615` — markedly higher than the `0.389` measured between two
identically-configured runs of the host-bridge harness. Wall clock `2h06m02s` vs `2h04m54s`;
`31.75M / 0.62M` tokens vs `32.47M / 0.59M`.

## Serving identity, fingerprinted

`serving_run/get_server_info_{before,after}.json` both report `random_seed = 598954308`. The seed is
assigned when sglang starts. Identical before and after means the server process was never restarted
mid-run — a stronger statement than `model_path` alone, which would survive a restart with the same
weights. `api_key` is `null`: this endpoint does not authenticate, and no key was ever in the
environment.

There is no relay in this run. `--relay-url` is a misnomer; the traffic goes straight to sglang.

## `llm_health`, and a string that means two opposite things

```
infra_class    1     terminal_bench.log:6745
                     Unknown Error in LLM interaction: RetryError[... raised Timeout]
content_class  7     HTTP 400, one each across seven tasks (16_llm_health.txt)
                     5713 × "Extra text detected after JSON object"
                      598 × "No valid JSON object found"    (canonical: 4468 and 0)
```

The `infra_class` count was first reported as `0`. It is `1`. The failure does not appear in any
`debug.json` because a retry succeeded within the same episode and overwrote it; it survives only in
the harness log. One in 8559 is not material and does not make this run `forbidden`, but it is not
zero, and reporting it as zero would have been false.

**Canonical's six `Unknown Error in LLM interaction` lines all wrap `BadRequestError` — `content_class`.
This run's one wraps `Timeout` — `infra_class`. The same log string, carrying opposite meanings.**
Classify by the wrapped exception, never by the message.

The 598 `No valid JSON object found` warnings are `content_class`: across 8551 responses,
`finish_reason` is `stop` every time, `tool_calls` never appears, no content is null or empty, and
every response body begins with `{`. sglang's `qwen3_coder` tool-call parser did not truncate
anything — a hypothesis this project carried for hours, refuted by the evidence gathered to test it.

## What is here

| Path | |
|---|---|
| `run_metadata.json`, `results.json` | the score, and its `sha256` verified against `completion_evidence/01_artifact_sha256.txt` |
| `full_run.sh` | the driver that ran |
| `reduce_scores.py` | reads the 89 per-trial results, not `strict_summary` |
| `identity_capture.py`, `leakscan.py` | how serving identity and secrets were checked |
| `serving_run/get_{model,server}_info_{before,after}.json` | four captures, `api_key: null` |
| `gate/` | preflight matrix, vendor pins |
| `completion_evidence/00..20` | 21 numbered forensics: thread table, main-thread kernel stack, `wchan` histogram, sockets, SIGTERM timestamp, `llm_health`, parser warnings, trace merkle |
| `full.rc` | `143` |
| `SHA256SUMS` | every file above |

## What is not here, and why

The 12 GB run root — 8559 `debug.json` (one directory per episode, all rounds retained, not
last-only) and the asciinema `.cast` recordings — stays on shared storage.
`completion_evidence/20_trace_merkle.txt` pins the 89 per-trial `results.json` under a single merkle
root, `c640203b5df32df9…`, which is what a reader needs to prove the score was not edited.

Hashing 12 GB was deliberately **not** done while it would have competed for I/O with a different
89-task benchmark running on the same pod. Evidence collection that perturbs the thing being measured
is not evidence collection.
