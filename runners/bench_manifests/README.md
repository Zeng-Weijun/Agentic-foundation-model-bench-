# `bench_manifests/` — Harbor digest manifests for offline reproduction

Each `*.jsonl` maps a benchmark's tasks to the exact Harbor image digest that reproduces them
`--network none`. A fresh KVM worker reproduces a task by `docker pull <repo>@<digest>`, running with
no network, applying the gold patch, and checking the official `FAIL_TO_PASS` — no model required.

## `multilingual_java26_harbor.jsonl`

The 26 Java tasks that SWE-bench Multilingual's `clean274` subset excludes because an offline
`gradlew`/`mvn` cannot fetch its build dependencies (§5.5). Each is now an offline-self-contained
image on Harbor: the Gradle distribution / Maven backend and the resolved dependency closure are
baked in.

- **build recipe** (from `GRADLE_OFFLINE_26.md`): select the source image by its pinned P0 digest,
  verify the Docker image ID, warm with the gold patch, then reverse **only** that patch with
  `git apply -R` — **never `git reset --hard`**, which deletes the Druid/Lucene pre-install closure.
- **verification**: every task passes its official `FAIL_TO_PASS` under `--network none` against the
  gold patch. Three were pulled from a fresh KVM worker (Pod A) by exact digest and re-run offline:
  `gson-1014` (`reward=1`), `lucene-11760`, `base58` (RepoZero) — the transport path is proven end to
  end, not merely digest-present.

### The Lucene "reward=0" is a scorer false-negative, not an image fault

`lucene-11760` returned `reward=0` on the KVM pull-run, with `PASS_TO_PASS` reporting `testSimpleTerm`
as a failure. Its `test_output.txt` shows `testSimpleTerm ... PASSED`. Between the test name and
`PASSED`, the JVM prints `WARNING: A command line option has enabled the Security Manager`, and
SWE-bench's Gradle output parser loses the association across that line. Checked test-by-test with
`grep -o PASSED / FAILED` across all eight pre-existing Lucene images: `11760 12/0`, `12022 24/0`,
`12196 12/0`, and so on — **zero real failures.** The images are correct; the harness parser needs a
WARNING-tolerant line rule. Evidence in `multilingual_lucene_parser_falseneg_evidence.txt`.

This is the same shape as four other findings this project logged in one night — a single line of text
misread by a parser or a status flag (§5.11–5.14). The rule that keeps surfacing: **a line of output
is not a verdict; read the thing the verdict was computed from.**

### Five gson images were rescued the same way

`gson-2061/2134/2158/2311/2479` first scored offline failures because proguard/log4j2 tried to resolve
the container's own hostname under `--network none` and printed an error line the driver read as an
eval failure. The tests had passed. Marked `"rescue": true` in the manifest.

## `nl2repo_transport.jsonl`

104 per-task images (`ghcr.io/multimodal-art-projection/nl2repobench/<task>:1.0`, 0.1–0.4 GB each),
transported to Harbor. The manifest count corrects the vendored `expected_required_images=108`, which
counted `pip install` mentions rather than images; the real number is 104 (103 pushed, one finishing).

Two things this bench needs that a plain `docker pull` does not give:

- **A build-backend wheelhouse.** `pip install -e .` inside these images fetches its PEP-517 backend
  from PyPI, so `--network none` fails (`ModuleNotFoundError: hatchling`, then `aiofiles` for
  src-layout packages under a PYTHONPATH-only workaround). The fix is a ~75 MB offline wheelhouse of
  the backends the 104 `pyproject.toml` files declare (hatchling / poetry-core / flit-core /
  pdm-backend), used with `pip install -e . --no-build-isolation --no-index --find-links <wheelhouse>`.
  Runtime deps are already baked into the images; only the backends are missing.
- **Per-task pinned gold, for a 100% clean oracle.** The images are cleanroom (source removed), so a
  model-free gold check needs the upstream `repo@commit` fetched online once. The transport path and
  the offline harness are proven — KVM cross-machine ran `boltons` at 423 passed / 0 failed, and the
  oracle sample is 7/11 clean across all four backends. Full per-task pinned-gold is deferred until an
  actual scored run needs it; it does not gate offline reproducibility.
