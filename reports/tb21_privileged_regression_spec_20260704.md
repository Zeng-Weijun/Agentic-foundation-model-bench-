# TB2.1 privileged-stack regression fix spec — 3 tasks (2026-07-04)

**Scope:** the 3 tasks that are **green under rl-vfs but red under the privileged (fuse-overlayfs) stack** — the residual regressions after the 84/89 canonical (`tb21_canonical_final_verdict_84of89_20260704.md`). Fixing all 3 → **TB2.1 oracle 87/89**. Per case: rl-vfs(pass) vs privileged(fail) first-evidence → env-diff root-cause hypothesis → validation experiment → fix. **0 model tokens** (oracle first-evidence only).

**Evidence base:** privileged c=1 run `shared_bench/terminal-bench/runs/tb21_full89_batched_batch_0N_of_06_oracle_c1_targeted6_final_oracle_c1_r7_20260703t183257z/<task>/…1-of-1…/` (`sessions/tests.log`, `panes/post-test.txt`, `results.json`). rl-vfs pass = composite map **B (79/89)**, per the canonical verdict §B (all 3 oracle-solvable under rl-vfs).

## ★ Unifying root-cause hypothesis (the headline)
Across all 3, the privileged fuse-overlayfs compose exposes a **read-only-vs-writable mount semantic** that rl-vfs did not: the test phase needs to **write** (compile a C extension, run a build, or have a service write to a docroot) into a location that is **read-only** on the privileged stack. Confirmed marker in **all 3**: `PytestCacheWarning: could not create cache path /tests/.pytest_cache` → `/tests/` is a **read-only** bind mount. The oracle *solution* ran fine (agent phase); the **verifier/test phase** is what hits read-only writes. rl-vfs mounted these rw (or the old stack ran build/service earlier in a writable layer).

---

## 1. feal-differential-cryptanalysis — **CONFIRMED read-only-fs (smoking gun)**
- **Privileged fail:** `creating build/temp.linux-x86_64-cpython-313` → `error: could not create 'build/temp.linux-x86_64-cpython-313': **Read-only file system**` → `ModuleNotFoundError: No module named 'feal_in_c'` → `test_feal_differential_cryptanalysis_attack` FAILED. CWD `/app`. (evidence: `…/feal-differential-cryptanalysis/…/sessions/tests.log`)
- **rl-vfs pass:** oracle-solvable (verdict §B); the C-ext built successfully at test time.
- **Root cause:** the verifier builds a C extension (`feal_in_c`, `setup.py build_ext`) at test time; the build-temp dir (relative to CWD, i.e. under `/app` or the `/tests`-sourced build) is on a **read-only** filesystem under the privileged compose. rl-vfs had it writable.
- **Validation experiment:**
  1. `docker run --rm <feal image> bash -lc 'cd /app && touch build_probe && echo WRITABLE || echo RO; mount | grep -E " /app | /tests "'` — confirm which path is ro.
  2. Re-run the verifier with the build redirected to a writable dir: `python setup.py build_ext --build-temp=/tmp/bt --build-lib=/tmp/bl` (if the test/setup allows) → expect `feal_in_c` imports → attack test passes.
- **Fix (pick one, least-invasive first):**
  - (a) **compose mount fix:** in the privileged r7 compose override, mount the task workdir (`/app`) and any build source **rw** (not ro), matching rl-vfs. This is the general fix and likely resolves all 3.
  - (b) **writable build-temp:** bake a `tmpfs`/rw scratch and point Python build-temp there (env `TMPDIR`/`PYTHONPYCACHEPREFIX` + `--build-temp`) if the test invokes build via a wrapper we control.
  - (c) if `/tests` must stay ro (integrity), give the C-ext a writable build CWD (copy source to `/tmp` before build) — but (a) is cleaner.

## 2. compile-compcert — likely same class (functional test), needs assertion confirm
- **Privileged fail:** `test_compcert_exists_and_executable` PASS + `test_compcert_rejects_unsupported_feature` PASS + **`test_compcert_valid_and_functional` FAIL** — `AssertionError: CompCert inauthentic or not u[sable]`. 2/3 pass. Same `/tests/.pytest_cache` read-only warning. (evidence: `…/compile-compcert/…/sessions/tests.log`)
- **rl-vfs pass:** oracle-solvable (verdict §B); functional test passed.
- **Root cause (hypothesis, ranked):**
  1. **read-only write at functional-test time** (same class as feal): the functional test compiles a program with `ccomp` and writes the binary/intermediate to a read-only CWD → the produced artifact is missing/partial → test reads it as "inauthentic". (ccomp *builds+execs* per test-1/2, so the toolchain is fine; the *functional* test likely writes+re-reads.)
  2. genuine env-sensitive check: "inauthentic" may compare a CompCert output signature/checksum that differs under the new base image toolchain.
- **Validation experiment:**
  1. Read the full assertion: `grep -A3 -B3 inauthentic .../sessions/tests.log` + the test source `test_compcert_valid_and_functional` (what it writes/compares).
  2. `docker run` the compcert image, run the functional test steps manually with a **writable** CWD → if it passes, root cause = read-only (fix = §1a); if it still fails, root cause = env/toolchain (deeper).
- **Fix:** if read-only → compose rw mount (§1a). If env-sensitive → pin the toolchain/compare tolerance to match rl-vfs (needs the assertion detail first).

## 3. configure-git-webserver — service/write task, root cause ranked
- **Privileged fail:** `test_hello_html_exists` FAILED — `❌ TEST FAILED: Web server returned HTTP <non-200>` (curl `http://server:8080/hello.html` did not return "hello world"). Multi-service task: git server + webserver:8080 + post-receive hook (push→hook→docroot). (evidence: `…/configure-git-webserver/…/sessions/tests.log`)
- **rl-vfs pass:** oracle-solvable (verdict §B); the pushed `hello.html` was served on :8080.
- **Root cause (hypothesis, ranked):**
  1. **read-only docroot write** (same class): the post-receive hook copies `hello.html` into the webserver docroot; if the docroot is a **read-only** mount under the privileged compose, the hook write fails → 404. (fits the unifying theme.)
  2. **service startup timing:** under the privileged stack the git-daemon / webserver / hook race differs; the test curls before the hook completes → transient non-200.
  3. **cross-container shared-volume propagation:** the git-server → webserver docroot is a shared volume; fuse-overlayfs may not propagate writes across the two services as rl-vfs did.
- **Validation experiment:**
  1. Get the exact HTTP code: `grep "returned HTTP" .../sessions/tests.log` (404=docroot/hook; 000/refused=service down; 500=server error).
  2. In the running compose: check docroot writability (`touch docroot/x`), whether the hook ran (hook log / `hello.html` present in docroot), and service readiness (`curl` retry loop). `mount` inside both containers for ro/rw + shared-volume.
- **Fix:** if (1) docroot rw mount (§1a); if (2) add a readiness wait (retry curl) or start-order fix in the compose; if (3) fix the shared-volume mount propagation (bind vs named volume) under fuse-overlayfs.

---

## Recommended execution order (when resumed; Pod A privileged, c=1, 0 token)
1. **First: the compose rw-mount audit** — `mount` inside a privileged task container, diff ro/rw vs an rl-vfs container. If the task workdir/build/docroot is ro under privileged and rw under rl-vfs, **one compose-override fix (rw mounts) plausibly flips all 3** — validate feal first (cleanest signal: `feal_in_c` builds).
2. feal → confirm §1a fixes it (build succeeds, attack test passes).
3. compcert → re-run functional test with writable CWD; if still red, pull the `inauthentic` assertion + toolchain compare.
4. git-webserver → HTTP code + docroot/hook/service checks; apply the matching fix.
5. Re-run the 3 on Pod A c=1 → target **87/89**. Each flip: roll the canonical verdict + ledger (separate commit).

## Red lines (execution)
Pod A privileged only; c=1; 0 model tokens (oracle); only-add (compose overrides = new files/layers, no deletes); read-only on completed runs; all commits via clean worktree.
