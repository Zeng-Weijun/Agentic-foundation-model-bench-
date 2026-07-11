# DeepSWE full-113 FINAL RESULTS (finalizer, 2026-07-11T00:58:56Z UTC)

## Transport summary
- manifest rows: 113  (ok=109, fail=4)

- SUMMARY ok=109 fail=4 dedup=11 unique_tars=98 total=113 2026-07-11T00:58:18Z

## Retry pass over fail_* tasks

- arcane-drift-detection-baselines -> ok dig=sha256:7b97280ca5d8
- arktype-json-schema-refs-dependencies -> ok dig=sha256:7361d6b0ff68
- goreleaser-retry-publish-auditing -> ok dig=sha256:e59820a49ca8
- ts-pattern-match-each -> ok dig=sha256:70f7b265222e

retry recovered: 4/4

## Oracle sampling (>=5 cross-language, Harbor-by-digest, --network none, gold-patch)

| task | lang | harbor_digest | oracle_reward |
|---|---|---|---|
| abs-module-cache-flags | go | sha256:2a22b71ccd37 | 1 |
| boa-hierarchical-evaluation-cancellation | rust | sha256:d6c5987ef5f4 | 1 |
| awilix-async-container-initialization | typescript | sha256:c574abfc7049 | 1 |
| adaptix-name-mapping-aliases | python | sha256:3abb7745c799 | 1 |
| csstree-shorthand-expansion-compression | javascript | sha256:dd2d9ac50687 | 1 |
| abs-stepped-slices | go | sha256:2a22b71ccd37 | 1 |

## FINAL
- transported OK (post-retry): 113/113
- unique images (by harbor_digest): 102
- oracle sample passed: 6/6
- KVM cross-machine verify: PENDING_KVM_ACCESS (see report top banner)

FINALIZER DONE 2026-07-11T01:25:24Z UTC
