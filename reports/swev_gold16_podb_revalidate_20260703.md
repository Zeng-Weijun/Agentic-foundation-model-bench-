# SWE-V gold-16 offline-induced — Pod B privileged-stack re-validation (2026-07-03)

**Question:** do any of the 16 offline-induced gold failures (`V5_GOLD_LEDGER.md`) turn green just by moving from the old rootless-vfs-tmpfs stack to the **privileged fuse-overlayfs** stack (Pod B)?

**Answer: 2/16 turn green directly; 14/16 still need their targeted fixes (8 network-provisioning + 6 env).** 0 model tokens (gold-patch oracle).

## Method
- Host: **Pod B** `env-kvm-57740737-bzw56`, `DOCKER_HOST=unix:///var/run/docker.sock`, driver `fuse-overlayfs`, data-root `/docker-data-57740737` (bootstrap holds).
- Images: **P0 by-digest pull + retag** per `surface51_podb_p0_map_20260703.json` (`p0_digest_ref` → `expected_base_ref`); all 16 `PULL_OK present=True` (0 fallback-tar needed).
- Eval: `swebench.harness.run_evaluation -d SWE-bench_Verified -p gold_preds.json -i <16> --max_workers 4 -n swebench --cache_level env -t 1800` (same invocation as `diskval_orchestrator.py`), HF offline. rc=0, 3962 s (66 min — network cases hang to timeout offline).
- Isolated: own dir `swev_gold16_podb_revalidate_85_20260703/`; **51's canary + run dirs + main ledger untouched**; only-add (no `rmi` of 51's images, no deletes).

## Results — per instance (resolved bool + evidence)
Evidence: per-instance `…/eval/logs/run_evaluation/gold16_podb_85/gold/<iid>/report.json`; combined `…/eval/gold.gold16_podb_85.json`; `…/results.jsonl`. **All 16 gold patches applied cleanly (`patch_successfully_applied=True`)** — failures are test-level, not patch-level.

| instance | resolved | category | failing evidence |
|---|---|---|---|
| **psf__requests-2931** | ✅ **RESOLVED** | network→offline-safe (connect-timeout test) | passes offline on privileged stack |
| **psf__requests-5414** | ✅ **RESOLVED** | network→offline-safe | passes offline on privileged stack |
| psf__requests-1724 | ❌ | network (httpbin live) | httpbin HTTP/redirect tests |
| psf__requests-1766 | ❌ | network (httpbin live) | httpbin |
| psf__requests-1921 | ❌ | network (httpbin live) | httpbin |
| psf__requests-2317 | ❌ | network (httpbin live) | `test_HTTP_302_ALLOW_REDIRECT_GET`, `test_POSTBIN_GET_POST_FILES` |
| sphinx-doc__sphinx-7985 | ❌ | network (linkcheck live URL) | test_build_linkcheck |
| sphinx-doc__sphinx-8269 | ❌ | network (linkcheck live URL) | test_build_linkcheck |
| sphinx-doc__sphinx-8475 | ❌ | network (linkcheck live URL) | `test_TooManyRedirects_on_HEAD` |
| matplotlib__matplotlib-20488 | ❌ | network (HTTPS image fetch) | test_https_imread_smoketest (proxy `no host given`) |
| astropy__astropy-7606 | ❌ | env (flaky empty parametrization) | test_compose_roundtrip |
| astropy__astropy-8707 | ❌ | env (fits-header dep/env) | `test_card_from_bytes` +P2P |
| astropy__astropy-8872 | ❌ | env (units/quantity dep/version) | test_preserve_dtype +80 P2P |
| django__django-10097 | ❌ | env (auth template) | PasswordChange/Reset view tests |
| pylint-dev__pylint-4661 | ❌ | env (PYLINTHOME) | `test_pylint_home` |
| sphinx-doc__sphinx-10435 | ❌ | env (latex/tex) | test_latex_images |

**Tally: resolved 2 / 16.** Network-still-red 8, env-still-red 6.

## Interpretation
- The **privileged stack alone fixes only the 2 psf cases whose tests are offline-safe** (they assert timeout/error behaviour, not live-httpbin). So the "old-rootless-stack-sickness" hypothesis holds for a small slice (2), **not** the bulk.
- The other 14 fail for **task-intrinsic offline reasons unchanged by the stack**: 8 need a **live/mocked network** (httpbin, linkcheck URLs, HTTPS image fetch), 6 need **env fixes** (dep pins, PYLINTHOME, latex deps, django template, flaky-retry). These are the same offline-induced classifications as the ledger — confirmed still offline-induced (patches apply; not upstream bugs), just not stack-fixable.

## Ledger-flip suggestion (SEPARATE — canonical `V5_GOLD_LEDGER.md` NOT modified; awaiting approval)
- **Flip 2 → offline-PASSED**: `psf__requests-2931`, `psf__requests-5414` (now pass gold-eval offline on the privileged stack; old rootless stack was losing them). Evidence: this run's report.json (resolved=true).
- **Keep 14 as offline-induced (fix-pending)**, with concrete fix per sub-bucket:
  - **8 network** → offline local network services / mocks: `httpbin`-equivalent (4 psf), linkcheck URL mock (3 sphinx), HTTPS image-fetch/proxy fix (matplotlib-20488). (Same class as the TB2.1 rstan launchpad case.)
  - **6 env** → per-case: astropy-8707/8872 dep/version pin, django-10097 template env, pylint-4661 `PYLINTHOME`, sphinx-10435 latex/tex deps, astropy-7606 flaky-retry.
- **If flipped**, V5 3-part ledger would read **offline-PASSED 484→486 + offline-induced 16→14 + upstream 0 = 500** (all still offline-unresolved for the 14 until their fixes land). **0 upstream-archived preserved.**

## Red-line compliance
- Pod B only; `c=4`; 51's full500 model canary (`swev_full500_model_20260702_podb_canary_*`) + its procs/dirs/ledger **untouched**; own isolated BASE; only-add (no deletions, no `rmi` of shared/51 images); **0 model tokens**; runner nohup-detached (survived the SSH-flaky maintenance window).
