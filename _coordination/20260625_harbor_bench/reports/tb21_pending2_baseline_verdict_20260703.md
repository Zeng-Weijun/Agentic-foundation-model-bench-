# TB2.1 pending-2 — official-baseline verdict (2026-07-03)

**Scope:** final verdict for the 2 TB2.1 tasks stuck at `pending_baseline_online_oracle_comparison` in the r5_final infra map (2 of the 10 unresolved). Method = **official original image + official solution + oracle agent, online** (network via kubebrain proxy), **timeout ×1.0**, on swe_dev2. **0 model tokens** (oracle agent applies the reference solution; no LLM).

## VERDICTS — both **offline-induced**; neither upstream-native

| task | official-online oracle | v5 verdict | archive? |
|---|---|---|---|
| `query-optimize` | **reward=1.0 (PASS)**, exit=0, no exception | **offline-induced** | **NO** |
| `rstan-to-pystan` | **reward=1.0 (PASS), 6/6 tests** | **offline-induced** | **NO** |

**Bottom line:** in a properly network-provisioned official environment, both official solutions run and pass all tests. The earlier offline `pending_baseline` state was **our-env-induced** (network/provisioning), **not** a task defect. **Zero upstream-native; do not archive either.**

## Red-line compliance
- Ran ONLY these 2 references on swe_dev2. Agent-55's flat 现场 (repo2env: P0 registry `swe-dh-shared-registry` + 9 buildkit builders) left running, untouched.
- Isolated jobs-dir `/data/tmp/tb21_pending2_verdict_85`; **no deletions**.
- 55/repo2env's `docker` wrapper (`/usr/local/bin/docker`) + compose-shim + `/root/.docker` config were **NOT modified** — bypassed only for my own harbor process, env-scoped: `PATH`→`/usr/bin/docker` (real) + `DOCKER_CONFIG`→ real compose v2.29.7. 55's global docker behaviour unchanged.
- 0 model tokens.

## Provenance
- Official images (upstream author, 8-month-old): `alexgshaw/query-optimize:20251031` (248 MB), `alexgshaw/rstan-to-pystan:20251031` (141 MB). (`tb2-offline/*` and P0 `terminal-bench-2-1-*` tags are OUR staged/closure images — deliberately NOT used for the official baseline.)
- Harbor 0.13.2, dataset resolved online (89 tasks, hub=200 via proxy), `-a oracle`, timeout ×1.0.
- query-optimize result: `/data/tmp/tb21_pending2_verdict_85/2026-07-03__19-11-27/query-optimize__z8NYbPa/`.
- rstan result (final, provisioned): `/data/tmp/tb21_pending2_verdict_85/rerun_rstan_sudoproxy/2026-07-03__19-44-05/rstan-to-pystan__mht4d4n/`.

## query-optimize → offline-induced (CONFIRMED)
```
verifier reward = 1.0   exit-code = 0   exception = none
```
Official oracle passes online, first try, within ×1.0 timeout. Task is officially resolvable → our earlier offline timeout was our-env-induced. **What our offline env lost / fix:** offline run couldn't complete within ×1.0 (timed out) while online finishes fast → solve needs the network/resources the offline lane withheld. Fix = run on a network-provisioned lane (proxy/internal-mirror for solve-time fetch) or the privileged KVM/fuse-overlayfs lane (no rl-ov2 docker.sock instability).

## rstan-to-pystan → offline-induced (CONFIRMED) — after fixing a 3-link env-provisioning chain
The official solution is a heavy multi-network-source build (apt build-tools → deadsnakes launchpad PPA → httpstan/pystan compile → Stan MCMC estimation). It failed at successive **env-provisioning** boundaries — **never at the task's actual logic** — until each was fixed:

| attempt | fix added | result | boundary hit |
|---|---|---|---|
| 1 | proxy env only | reward 0, exit 1 | container apt = direct → `Could not connect to archive.ubuntu.com` → build-tools missing |
| 2 | `apt-proxy.conf`→`/etc/apt/apt.conf.d/99forceproxy` (survives sudo) | reward 0, exit 1 | apt **fixed**; `sudo add-apt-repository ppa:deadsnakes` → `launchpadlib TimeoutError` (sudo strips proxy from launchpadlib) |
| **3** | **sudoers `env_keep` proxy** (`/etc/sudoers.d/99keepproxy`) | **reward 1.0, 6/6 PASS** | none — launchpad reached, pystan built, **Stan sampled 8000 iters, produced posterior estimates**, `=== Solution complete ===` (30m 3s) |

Final verifier (attempt 3):
```
test_outputs.py ......  [100%]
PASSED test_r_rstan_not_installed / test_output_files_exist /
       test_alpha_estimation_accuracy / test_sigma_estimation_accuracy /
       test_rho_estimation_accuracy / test_beta_estimation_accuracy
6 passed in 0.12s     ctrf: {tests:6, passed:6, failed:0}
solve produced: alpha=1.0858 sigma=0.1341 rho=[...] beta=[...]
```

**What our offline env lost / fix (the "launchpad-shim" class):**
1. Container apt must use the internal mirror **or** the proxy — not `direct` (image default `archive.ubuntu.com` is unreachable offline).
2. apt proxy via **`apt.conf`** (a file), not env — the solution runs `sudo apt-get`, and sudo strips env proxy.
3. **`sudo env_keep`** the proxy so `add-apt-repository`/launchpadlib can reach the **deadsnakes launchpad PPA** (PPAs aren't on the internal mirror; require proxy egress).
Provide these three in the offline TB2.1 runner (bake into the task-container compose override) and rstan resolves offline. (Note: the earlier jvm9z "official-image+launchpad-shim" attempt that got reward 0 only fixed link 3 partially, not links 1–2 — hence it still failed; the full chain is required.)

## r5_final map — status-update notes (NOT modifying the map; awaiting approval)
Both rows move from `pending_baseline_online_oracle_comparison` → **`resolved`** (offline-induced):
- `query-optimize`: `resolved` — category `offline_induced_official_online_pass` — evidence `.../2026-07-03__19-11-27/query-optimize__z8NYbPa/result.json` (reward 1.0).
- `rstan-to-pystan`: `resolved` — category `offline_induced_official_online_pass` — evidence `.../rerun_rstan_sudoproxy/2026-07-03__19-44-05/rstan-to-pystan__mht4d4n/` (reward 1.0, 6/6).

**Effect once approved:** r5_final oracle map **79/89 → 81/89** (both pending_baseline resolved). Remaining unresolved = 8× `docker_api_eof_before_injection` (rl-ov2 upstream docker.sock instability class). **0 upstream-archived** among the pending-2.
