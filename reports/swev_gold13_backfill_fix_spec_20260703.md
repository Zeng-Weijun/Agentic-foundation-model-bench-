# SWE-V gold-13 backfill fix spec (2026-07-03)

**Scope:** the **13 remaining** offline-induced gold instances (original 16 − psf-2931/5414 Pod-B-revalidated − pylint-4661 backfill-fixed). Per-case: cause / fix plan / effort / vendor-class. Companion to `swev_gold16_podb_revalidate_20260703.md`; format mirrors `tb21_vendor_bake_spec_pending2_20260703.md`.

**Decision (user, 2026-07-03 00:20):** the **network-8** re-investment is **HELD** — it is rstan-style vendor engineering, queued *behind* TB2.1 收榜 and full500 recovery. The env-5 are tractable and can proceed when resumed.

## Proven mechanism (reference — already flipped pylint-4661)
**pip-mirror bake:** `docker build FROM <eval-image>` + bake `/etc/pip.conf` (internal pypi mirror `mirrors.i.h.pjlab.org.cn/repository/pypi-{tsinghua,proxy}`) → re-run `run_evaluation --cache_level instance`. Fixes any case whose failure is the eval pip-step hitting Pod B's offline wall. **Confirmed:** pylint-4661 (`appdirs` installs → `test_pylint_home` passes). Low effort/case. **Caveat:** it lets pip *upgrade* deps — can introduce version skew (see astropy-8707/8872), so pair with version pins where the era needs old deps.

## Env-5 (tractable; mostly NON-vendor)
| instance | cause (evidence) | fix plan | effort | vendor-class |
|---|---|---|---|---|
| **astropy-8707** | pytest≥8 rejects nose-style tests: `test_rename_keyword using nose-specific method` → whole suite ERRORs at collection (`EEEE…[100%]`) | **pin pytest<8** (e.g. 7.4.x) into the image via internal mirror (bake, or add to eval install); do NOT let pip upgrade pytest | **Low** (bake + rerun) | No (dep pin) |
| **astropy-8872** | eval rebuilds C-ext `astropy.compiler_version` + pytest collection error (`_pytest/assertion/rewrite.py: exec_module`) | investigate collection error (likely same pytest≥8 skew and/or C-ext ABI); pin pytest<8 + ensure numpy/build-tools match the era | **Medium** (investigate) | No (dep/version) |
| **astropy-7606** | flaky: on retry FAIL_TO_PASS passed (success=1) but a PASS_TO_PASS test flaked → still red; a bare retry did NOT flip | root-cause the non-deterministic P2P test (unit parametrization/ordering); flaky-retry with N attempts or fix seed/ordering | **Medium** | No |
| **django-10097** | 3 auth-template tests fail: `test_PasswordChangeDoneView`, `test_PasswordResetChangeView`, `test_PasswordResetCompleteView` (431 P2P pass) | diagnose the template rendering diff (template-loader/env asset that offline eval lacks); apply template/env fix | **Medium** (investigate) | No |
| **sphinx-10435** | `test_latex_code_role` (test_build_latex) needs a **LaTeX toolchain** (texlive/latexmk) absent from the image | **apt-bake texlive** (minimal: `texlive-latex-extra latexmk` or `texlive-full`) into a derived image via the internal apt mirror; retag | **Medium** (texlive ~0.5–1 GB apt; must wire the image's apt to the internal mirror first) | **YES (image bake)** |

## Network-8 (VENDOR-class — **HELD**, deferred behind TB2.1 收榜 + full500)
All need an **on-pod local network service/mock** because Pod B is offline with no reachable proxy and these tests hit **live external endpoints**. This is the rstan-style vendor tier.
| instances | cause | fix plan | effort | vendor-class |
|---|---|---|---|---|
| **psf-1724 / 1766 / 1921 / 2317** | tests hit live **httpbin.org** (`test_HTTP_302_ALLOW_REDIRECT_GET`, `test_POSTBIN_GET_POST_FILES`, HTTP/DIGEST/BASICAUTH) | stand up a **local httpbin container** on-pod; repoint tests (`HTTPBIN_URL` env and/or `/etc/hosts httpbin.org→127.0.0.1`) | **High** (service + per-test URL repoint) | YES |
| **sphinx-7985 / 8269 / 8475** | `test_build_linkcheck` hits **live external URLs** (200/redirect/TooManyRedirects) | **local URL mock** serving the exact linkcheck fixtures + point sphinx test conf | **High** | YES |
| **matplotlib-20488** | `test_https_imread_smoketest` fetches an image over **HTTPS** (also a proxy `no host given` quirk) | **local HTTPS mirror** of the fetched asset + repoint the test URL | **Medium-High** | YES |

## Effort summary + recommended order (when resumed)
1. **astropy-8707** — pytest<8 pin (Low, quick flip).
2. **astropy-8872 / astropy-7606 / django-10097** — investigate (Medium, non-vendor).
3. **sphinx-10435** — texlive image bake (Medium, vendor).
4. **network-8** — local-mock vendor infra (High, **HELD** behind TB2.1/full500).

**Realistic gold ceiling:** 487 now → up to **492/500** with the env-5 flipped (no network work); **500/500** only after the network-8 local-mock vendor tier. **0 upstream-archived throughout** — all 13 are offline-induced (patches apply cleanly; failures are offline env/network provisioning, not upstream bugs).

## Red lines (execution)
Pod B only; c≤4; 51's canary/dirs/ledger untouched; 0 model tokens; only-add (image bakes = new layers, no deletes); all ledger/report commits via clean throwaway worktree (shared checkout M-files never touched).
