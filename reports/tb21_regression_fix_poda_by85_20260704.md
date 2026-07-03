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
