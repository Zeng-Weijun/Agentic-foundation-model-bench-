# TB2.1 vendor-bake spec — pending-2 (2026-07-03)

**Purpose:** convert the 2 pending-2 tasks (verdict = **offline-induced**, `tb21_pending2_baseline_verdict_20260703.md`) from offline-**unresolved** → offline-**PASSED**, by vendoring their solve/verify-time dependencies so they run under `--network none` on the offline lane. **Design only — bake EXECUTION deferred until agent-55's full89 run completes.**

## TL;DR
| task | needs vendor-bake? | why |
|---|---|---|
| `rstan-to-pystan` | **YES** | solve pulls **deadsnakes launchpad PPA** (python3.10) + **github** (httpstan source) — neither is on the internal mirror |
| `query-optimize` | **NO** | solution = pure SQL (0.32 s, no network); its verifier deps are already vendored. Offline "timeout" = verifier-heaviness × rl-ov2 docker.sock instability → **lane/timeout fix, not a bake** |

Evidence: official-online oracle both reward=1.0 (rstan 6/6 tests). rstan solution log = `/data/tmp/tb21_pending2_verdict_85/rerun_rstan_sudoproxy/2026-07-03__19-44-05/…/agent/oracle.txt`; query-optimize = `…/2026-07-03__19-11-27/query-optimize__z8NYbPa/` (agent_exec 0.32 s, verifier 353 s).

---

## rstan-to-pystan — solve-time dependency list (from official solve.sh)
Base image `alexgshaw/rstan-to-pystan:20251031` (Ubuntu noble/24.04, amd64). Solution comment: *"pystan3 install is tricky … build httpstan from source, then install pystan3."*

| # | dep | source | on internal mirror? |
|---|---|---|---|
| 1 | apt build-tools: `build-essential gfortran libatlas-base-dev liblapack-dev libblas-dev curl ca-certificates gnupg software-properties-common git make cmake pkg-config` | ubuntu noble | ✅ via `apt-noble-proxy` (if container sources point there) |
| 2 | **python3.10 (+`-venv -dev -distutils`)** via `add-apt-repository ppa:deadsnakes/ppa` | **`ppa.launchpadcontent.net`** | ❌ **NOT mirrored** — needs egress or vendored .debs |
| 3 | **httpstan source** `git clone --branch ${HTTPSTAN_VERSION} github.com/stan-dev/httpstan` → `make` → `poetry build` → `pip install dist/*.whl` | **github.com** | ❌ **NOT mirrored** — needs egress or vendored source/wheel |
| 4 | `pip: pip setuptools wheel poetry~=1.8 pystan3` | pypi | ✅ via `pypi-proxy`/`pypi-tsinghua` mirror + wheelhouse |

**The two un-mirrored egress deps = launchpad (deadsnakes) + github (httpstan).** These are exactly what killed the 3 offline attempts (and the earlier jvm9z "launchpad-shim" that only half-fixed it).

### rstan bake plan — **into image** (recommended; matches the 79 offline-passing tasks' image-baked pattern → one immutable digest)
Build `100.97.118.137:8555/swe-data-harness/terminal-bench-2-1-rstan-to-pystan:<closure-wave-tag>` FROM `alexgshaw/rstan-to-pystan:20251031`, on a host WITH egress (swe_dev2), baking:
1. apt build-tools (from noble internal mirror).
2. **python3.10** (+venv/dev/distutils) — fetch the deadsnakes .debs for noble/amd64 once (egress), install into the image (removes the runtime launchpad dependency).
3. **Pre-built httpstan wheel** — `git clone stan-dev/httpstan @ ${HTTPSTAN_VERSION}` → `make` → `poetry build`; bake the resulting `httpstan-*.whl` into the image at `/opt/vendor/httpstan/` and `pip install` it (removes the runtime github+compile dependency).
4. pystan3 + poetry from internal pypi mirror.
5. A tiny **solve-shim** OR rely on solve.sh's idempotency: with python3.10 + httpstan wheel + pystan already present, the solve's `add-apt-repository`/`git clone`/`make` steps become no-ops or short-circuit. (If solve.sh unconditionally re-clones, add a shim that intercepts `git clone …/httpstan` → copy `/opt/vendor/httpstan` and `add-apt-repository` → no-op.)

- **Size estimate:** base 141 MB + python3.10 (~40 MB) + pystan/httpstan+deps (~150 MB) + build-tools (~400 MB). → **~700 MB** single-stage, or **~330 MB** if build-tools are stripped in a multi-stage (build httpstan in a builder stage, copy only the wheel + runtime libs). Recommend multi-stage → ~330 MB.
- **Alternative (dataset payload):** mount `python3.10 debs + httpstan wheel + launchpad-shim` as an `/offline-cache` payload (like the existing pip wheelhouse). Lighter image, but more moving parts + a mandatory shim; use only if image-bake per-task is undesirable.

### rstan verification (offline, `--network none`)
```
docker run --rm --network none <vendored-digest> bash -lc '<official solve.sh>'   # must complete, write /app/{alpha,sigma,rho,beta}_est.csv
harbor run -d terminal-bench/terminal-bench-2-1 -t terminal-bench/rstan-to-pystan -a oracle   # on the OFFLINE stable lane
# expect: reward=1.0, 6/6 tests (test_output_files_exist + {alpha,sigma,rho,beta}_estimation_accuracy + test_r_rstan_not_installed)
```

---

## query-optimize — NO bake; lane + timeout fix
- **Solution:** pure SQL CTE (`WITH word_stats AS … SELECT …`), 0.32 s, **empty stdout, no apt/pip/network**.
- **Verifier** (SHARED TB2.1 harness, ~6 min): `apt-get install curl` → `curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh` → `uvx -p 3.13 -w pytest==8.4.1 -w pytest-json-ctrf==0.3.5 pytest`. These are **already vendored** by `docker-proxy.rjob.override.yml` (curl-wrapper→local `uv`, `UV_PYTHON_INSTALL_DIR` python cache, `pypi-proxy` + wheelhouse).
- **Offline timeout root cause:** the verifier is heavy (uvx Python-3.13 bootstrap + SQL benchmark ≈ 6 min) and the **rl-ov2 lane's docker.sock instability (`docker_api_eof_before_injection`)** stalled/killed it → timeout. **Not** a missing fetch.
- **Fix (no bake):** run query-optimize on the **stable KVM/fuse-overlayfs lane** (Pod A/B — no rl-ov2 shim), ensure the shared verifier's vendored deps are present (Python 3.13 in `UV_PYTHON_INSTALL_DIR`, pytest wheels in wheelhouse), with nominal ×1.0 timeout sized for the ~6-min verifier. Expect reward=1.0 (as the online reference confirmed).
- **Shared-verifier note (repo-wide, not query-optimize-specific):** guarantee **Python 3.13** is pre-cached in `UV_PYTHON_INSTALL_DIR` for ALL TB2.1 tasks so `uvx -p 3.13` never needs astral.sh egress — this de-risks every task's verifier offline, not just this one.

---

## Execution order (deferred until 55's full89 completes)
1. On swe_dev2 (egress): build rstan multi-stage vendored image → push to P0 by digest → add to TB2.1 image manifest (`manifests/images/terminal_bench_2_1_*`).
2. Re-run rstan **offline, `--network none`, stable lane** → confirm reward=1.0, 6/6.
3. Move query-optimize to the stable lane (no image change) → confirm reward=1.0.
4. Only then flip r5_final `base_status` `unresolved → resolved` for both (offline-PASSED) → 79/89 → 81/89. **Until offline-confirmed, they stay unresolved (current annotated state).**

**Result at closure:** TB2.1 oracle ceiling **89/89, zero upstream-archived** (both pending-2 are offline-induced, fixable, not upstream bugs).
