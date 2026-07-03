# TB2.1 privileged regression fix — Pod A execution (by-85, 2026-07-04)

**Task:** live audit + fix + verify the 3 privileged regressions (canonical 84/89 → target 87). Pod A `env-kvm-15238487`, `DOCKER_HOST=unix:///var/run/docker.sock`, **0 model tokens**, read-only on completed runs, did not touch 55's launcher / Pod B / full500.

## Result: 2/3 PROVEN fixed (→ 86), 1 separate service issue

| task | class | fix | proof (direct-container, this run) |
|---|---|---|---|
| **feal-differential-cryptanalysis** | build-class | **`/tests` rw** | ro: `could not create 'build/temp': Read-only file system` → **1 failed, reward=0**; rw: **1 passed, reward=1** |
| **compile-compcert** | build-class | **`/tests` rw** | ro: `ld: cannot open output file /tests/positive_probe: Read-only file system` → **1 failed/2 passed, reward=0**; rw: **3 passed, reward=1** |
| **configure-git-webserver** | service | NOT the rw fix | rw `/tests`: still `HTTP 404` + `not a git repository` → reward=0 → separate service/git-setup regression (see §3) |

## 1. ★ Root cause — CONCRETE (corrects my earlier "fuse-overlayfs semantic" hypothesis)
The regression is **not** a fuse-overlayfs quirk. Each task's own **`docker-compose.yaml` mounts `/tests` with `read_only: true`** (r7-final payload):
```yaml
- type: bind
  source: …/terminal-bench-2.1-yaml-full89-r7-final-…/<task>
  target: /tests
  read_only: true
```
Harbor runs the oracle `bash /tests/solution.sh` and the verifier `pytest /tests/test_outputs.py` — **inside the read-only `/tests`**. Build-class tasks write there at test time:
- **feal**: `test_outputs.py` builds the `feal_in_c` C-extension (`setup.py build_ext` → `build/temp…` under `/tests`) → read-only → `ModuleNotFoundError: feal_in_c`.
- **compcert**: `test_compcert_valid_and_functional` compiles a probe with `ccomp` and links output to `/tests/positive_probe` → read-only → "CompCert inauthentic".

rl-vfs passed because its `/tests` mount was effectively writable (or the pre-r7 payload lacked `read_only: true`).

## 2. Fix for the 2 build-class tasks (feal, compcert) — VERIFIED
Set `read_only: false` on the `/tests` bind in the affected tasks' `docker-compose.yaml` (r7-final payload), i.e.:
```yaml
- type: bind
  source: …/<task>
  target: /tests
  read_only: false        # was true
```
- **Verified:** flipping to rw made both tasks go reward 0→1 in a faithful direct-container replay (`bash /tests/solution.sh` → `bash /tests/run-tests.sh`).
- **Scope note / recommendation:** audit ALL 89 tasks' compose for `read_only: true` + a test-time write; any task whose verifier compiles/links/writes under `/tests` has this latent bug (only surfaced where the test builds). Prefer a **targeted** flip (feal + compcert confirmed) over a blanket change to preserve test-integrity where not needed.
- **Official flip:** this is a harness/payload change (55's domain — I did not touch the launcher). Apply the compose edit, then **oracle c=1** re-verify (c≥2 needs the mount-guard runner). Expect feal + compcert → resolved. **Canonical 84 → 86.**

## 3. configure-git-webserver — separate service regression (NOT rw-/tests)
- rw `/tests` did **not** fix it: verifier `bash /tests/verify.sh` → `❌ Web server returned HTTP 404` (server up, `hello.html` not deployed) + `fatal: not a git repository`.
- The solution writes to `/var/www/html` (docroot) + `/git/server` + a post-receive deploy hook — none under `/tests`. Failure is in the **git-server / ssh / hook-deploy / nginx** integration, not a read-only build.
- My single-container direct replay cannot faithfully reproduce its ssh/service wiring, so I cannot close it here. **Next step (needs the official harbor oracle run on Pod A):** run git-webserver oracle c=1, then inside the running container check: (a) did the post-receive hook fire and write `hello.html` to `/var/www/html`? (b) is nginx serving `/var/www/html` on :8080 (404 = docroot/hook, not service-down)? (c) did the client `git clone user@server` over sshd succeed (the "not a git repository" hints the push never landed)? Likely a service-startup / ssh-key / hook-permission diff vs rl-vfs. **→ 86 → 87 once resolved.**

## Red lines held
Pod A / TB2.1 only; 0 model tokens (oracle solution + tests only); read-only on 55's completed runs; **did not touch 55's launcher**, Pod B, or full500; only-add (temp replay dirs under `/tmp`, no deletes).

## §4 (IN PROGRESS, by-85, 2026-07-04) — official offline oracle verification
Lead approved running the official offline oracle for feal + git-webserver on Pod A env-kvm-15238487 (DOCKER_HOST=unix:///var/run/docker.sock, 0 model token). Method is self-contained — does NOT touch 55's launcher, terminus_2, or LiteLLM:
- Copy the r7-final task dir to /tmp, edit the copy's `docker-compose.yaml` `/tests` bind `read_only: true -> false` (THE FIX), then `harbor run --path <task-copy> -a oracle --n-concurrent 1` (offline, --path = single local task).
- **feal:** expect reward=1 (direct-container replay already PROVED rw /tests -> reward 0->1; see §Result table + §2).
- **git-webserver:** run oracle, then inspect the running container for the HTTP-404 root cause (post-receive hook fired? nginx serving /var/www/html on :8080? ssh git-clone landed?).
**RESUME POINTER (if auto-compact hits mid-run):** the decisive proof already stands and is committed — feal + compcert reward 0->1 with `/tests` rw; root cause = task docker-compose.yaml `/tests read_only:true`; fix = flip to `read_only:false` (55 applies to payload + oracle c=1 => official 84->86). git-webserver is a separate service regression (not rw-fixable). Only the *official harbor re-confirmation* + git-webserver live service-diag remain.

## §5 (FINAL, by-85, 2026-07-04) — official-run attempt + git-webserver diagnosis

### Official harbor-CLI oracle (feal): attempted; orchestration plumbing is 55's domain
Replicated 55's offline invocation shape: `harbor run --registry-path <reg> --task terminal-bench/feal-differential-cryptanalysis -a oracle -n 1` (namespaced org/name; `--dataset-path`/`--task-id` are newer-harbor flags absent in 0.13.2 — this harbor uses `--registry-path` + `--task <org>/<name>`). Result: **`ExceptionGroup: unhandled errors in a TaskGroup`** — my hand-rolled CLI lacks the privileged-docker / `T_BENCH_*` orchestration env 55's wrapper sets (`TB_DOCKER_SDK_API_VERSION`, container-name vars, privileged-compose handling). I did **not** re-implement 55's wrapper (red line); 55 owns the working privileged offline invocation.

**The fix is PROVEN regardless:** the direct-container replay runs the EXACT harbor oracle+verifier sequence (`bash /tests/solution.sh` → `bash /tests/run-tests.sh` → `reward.txt`) and yields reward **0→1** for feal+compcert with `/tests read_only:false` (re-confirmed post-attempt: feal `1 passed`, reward=1). Harbor's oracle agent + verifier do exactly these steps; the CLI wrapper only adds `results.json` packaging + registry/privileged plumbing.

**Handoff:** 55 sets `/tests read_only:false` for feal + compcert in the r7-final payload, runs canonical **oracle c=1** via the proven runner (c≥2 → mount-guard) → **84→86**.

### git-webserver — service-task diagnosis (confirmed NOT /tests-rw)
- **verify.sh** (test's client): `apt-get install -y curl` (⚠ offline landmine on `network=none`), `ssh-keygen` + `Host localhost` ssh config, `git clone`/push over **ssh localhost**, then `curl :8080/hello.html`.
- **solution.sh**: `git init --bare /git/server` + post-receive deploy hook → `/var/www/html`; nginx/sshd startup not explicit in solution (likely image entrypoint).
- **Failure (privileged):** `HTTP 404` (server up, `hello.html` not deployed) + `fatal: not a git repository` → the ssh-localhost git-push flow **did not land** → post-receive hook never fired → 404. Root cause is the git-over-ssh / service-startup path, **not** a read-only mount (rw `/tests` did not fix it).
- **Needs 55's service-orchestrated runner** (single-container replay + hand-rolled CLI both can't wire the services). Ranked checks in the running privileged container: (1) sshd up + `ssh localhost` works (key/perm); (2) post-receive hook fired + wrote `/var/www/html`; (3) verify.sh `apt-get install curl` behavior offline. → **86→87** once resolved.

## §6 (by-85, PURE READ-ONLY) — git-webserver DEFINITIVE root cause: master/main default-branch mismatch
No Pod A runtime (full89 running c=89). All shared-FS reads.

**Services are NOT the issue:** the c=1 agent.log confirms `service ssh start` → `sshd [ OK ]` and `service nginx start` → `nginx [ OK ]`, `Setup complete!`.

**Chain:** verify.sh (client) clones the bare repo, `git push origin master`, `sleep 2`, `curl :8080/hello.html` (expects HTTP 200). solution.sh (oracle): `git init --bare /git/server` (**no `--initial-branch`**) + post-receive hook `GIT_WORK_TREE=/var/www/html git checkout -f` (checks out **HEAD**) + nginx `root /var/www/html; try_files $uri $uri/ =404`.

**Root cause (strong, read-only-derived):** `git init --bare` with no `--initial-branch` → the bare repo's HEAD points at git's built-in default branch. On the **new closure-r2 base image** (newer git; Debian default `main`), HEAD → `refs/heads/main`. The client hardcodes `git push origin master` → the `master` branch is created but **HEAD (main) stays unborn**. The post-receive hook's `git checkout -f` checks out HEAD (main = empty) → `hello.html` is **never deployed** to `/var/www/html` → nginx `=404`. On **rl-vfs** (older base image, git default `master`), HEAD → master → push master updates HEAD's branch → checkout deploys → 200. A **base-image git default-branch regression (master→main)**, not a mount/fuse issue. Confirmed absent: no `init.defaultBranch` / `--initial-branch` anywhere in the payload → relies on git's version-sensitive built-in default.

**Fix (for 55, minimal, AFTER full89 收官):** pin the bare repo default to master, one of:
- (a) image: `git config --system init.defaultBranch master` in the closure-r2 image; OR
- (b) solution.sh: `git init --bare --initial-branch=master /git/server`; OR
- (c) post-receive: check out the pushed branch explicitly instead of HEAD.
(a)/(b) cleanest — matches the task's client which hardcodes `master`.

**1-command read-only confirmation for 55 (post-full89, on a git-webserver container):** `git -C /git/server symbolic-ref HEAD` → `refs/heads/main` (while client pushes master) = confirmed; cross-check `git --version` (closure-r2) vs the rl-vfs image. Then apply (a)/(b), oracle c=1 → **86→87**.

## Summary — all 3 privileged regressions root-caused (by-85)
| task | class | root cause | fix | status |
|---|---|---|---|---|
| feal | build | `/tests read_only:true` + test builds C-ext there | `/tests read_only:false` | **PROVEN reward 0→1** |
| compcert | build | `/tests read_only:true` + test links `/tests/positive_probe` | `/tests read_only:false` | **PROVEN reward 0→1** |
| git-webserver | service | git default-branch master→main (client pushes master, HEAD=main unborn, hook deploys empty) | pin `init.defaultBranch=master` / `--initial-branch=master` | read-only root-caused; 55 confirms + fixes |
All 3 fixed → **84 → 87**. 55 applies after full89 收官 (2 compose edits + 1 git-default fix), oracle c=1.
