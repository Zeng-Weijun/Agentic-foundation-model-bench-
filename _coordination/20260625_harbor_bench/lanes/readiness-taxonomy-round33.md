# Readiness taxonomy round33

Date: 2026-06-26
Lane: readiness-taxonomy-round33
Worktree: `/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/agentic-foundation-model-bench/repo/.worktrees/image-warmup-policy`
Head verified: `bd66566 Promote TB2 qemu-startup transport`
Scope: static/readiness only. No Docker, no model calls, no benchmark execution, no production edits.

## Verdict

Overall: FAIL for docs freshness, PASS for machine-readable readiness state.

Machine-readable checks pass the requested claims after current head `bd66566`:

- PASS: default readiness target set is the tracked 9-bench set and contains no tau2 target.
- PASS: checked-in readiness JSON and live static readiness generator agree after ignoring timestamp.
- PASS: TB2 full image manifest state is 84/89 offline transports and 5 remaining gaps.
- PASS: tau3 full target is not image-transport-blocked; its image manifest is ready with 2/2 required transports. The full target is blocked by suite/adapter state, with rootless caveats documented in the manifest evidence.
- PASS: no active tau2 suite/readiness entry. `tau2` appears only inside tau3 smoke import commands, not as a suite target or active bench entry.

Docs checks fail because two stale/ambiguous README statements can mislead a user running the one-click suite.

## Machine-readable evidence

### Default readiness targets

`READINESS_TARGETS` defines exactly these default target IDs:

- `swebench_verified_multi`
- `terminal_bench_2_1`
- `mcp_atlas`
- `tool_decathlon`
- `tau3_bench`
- `programbench`
- `repozero`
- `nl2repo`
- `deepswe`

Evidence:

- `scripts/agentic_bench_suite.py:30-50` lists those 9 targets and no tau2 target.
- `scripts/agentic_bench_suite.py:747-756` returns `READINESS_TARGETS` when `--target-benches` is not supplied.
- `README.md:401-415` now documents the same 9 default readiness targets.
- `scripts/README.md:167-173` documents the same default readiness set in prose.

Static command evidence:

```text
contains_tau2_in_readiness_targets False
manifests/suite.example.yaml tau2_hits 0
_coordination/20260625_harbor_bench/readiness_20260626.json tau2_hits 0
```

Note: a broader grep found `tau2` only in tau3 image smoke commands:

- `manifests/images/tau3_bench.yaml:48`
- `manifests/images/tau3_bench.yaml:63`
- `manifests/images/tau3_oracle_direct_smoke.yaml:28`

Those are import checks inside tau3 runtime images, not suite/readiness entries.

### Readiness JSON agreement

Live static readiness generation was re-run and compared against `_coordination/20260625_harbor_bench/readiness_20260626.json` after dropping only `created_at`.

Command result:

```text
generator_rc 1
stable_json_equal True
checked_counts {'blocked': 8, 'missing': 0, 'ready': 1, 'total': 9}
generated_counts {'blocked': 8, 'missing': 0, 'ready': 1, 'total': 9}
swebench_verified_multi blocked blocked True 4 4 0 0
terminal_bench_2_1 blocked blocked True 2 2 0 0
mcp_atlas blocked blocked True 1 1 0 0
tool_decathlon blocked blocked True 1 1 0 0
tau3_bench blocked blocked True 2 2 1 1
programbench blocked blocked True 1 1 0 0
repozero ready ready True 1 1 1 1
nl2repo blocked blocked True 1 1 0 0
deepswe blocked blocked True 1 1 0 0
```

`generator_rc=1` is expected because the static readiness gate exits nonzero while selected targets are blocked or missing; here 8 targets are blocked and 1 is ready.

Checked-in readiness line evidence:

- `_coordination/20260625_harbor_bench/readiness_20260626.json:1-7` records counts `blocked=8`, `missing=0`, `ready=1`, `total=9`.
- `_coordination/20260625_harbor_bench/readiness_20260626.json:488-516` records RepoZero as the sole ready target.

### Terminal-Bench 2.1 state

PASS: current TB2 full manifest and readiness JSON both show 84/89 ready and 5 missing transports.

Manifest evidence:

- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:4` has status `materialized_from_swe_dev_cache_84_of_89_offline_transport_ready`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:11-14` records `cache_image_count: 89`, `shared_tar_count: 84`, `offline_transport_ready_count: 84`, and `remaining_transport_gap_count: 5`.
- `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml:15-19` records the remaining blockers, including `missing_transport_for_5_cache_tasks`.

Readiness evidence:

- `_coordination/20260625_harbor_bench/readiness_20260626.json:157-165` records the full TB2 target as blocked by `no_enabled_suite_entry`, `suite_entry_disabled`, `adapter_not_wired`, and `required_image_transport_missing`.
- `_coordination/20260625_harbor_bench/readiness_20260626.json:186-195` records image counts `images=89`, `required_images=89`, `required_with_offline_transport=84`, `required_without_offline_transport=5`, and manifest status `materialized_from_swe_dev_cache_84_of_89_offline_transport_ready`.
- `_coordination/20260625_harbor_bench/readiness_20260626.json:202-230` records the enabled one-task TB2 image-smoke row as image-ready but adapter-blocked.

Suite evidence:

- `manifests/suite.example.yaml:272-280` defines the full `terminal_bench_2_1` entry, marks `adapter_status: pending_adapter`, points at `manifests/images/terminal_bench_2_1_swe_dev_cache.yaml`, and sets `enabled: false`.
- `manifests/suite.example.yaml:282-297` defines the enabled `terminal_bench_2_1_image_smoke` row for `gcode-to-text`, still with `adapter_status: pending_adapter`.

### tau3 state

PASS: tau3 full target is not blocked by image transport. It is blocked at the full-target aggregation level by disabled suite entry and pending adapter. Rootless remains an operational caveat, not a missing image transport blocker.

Readiness evidence:

- `_coordination/20260625_harbor_bench/readiness_20260626.json:348-353` records tau3 target blockers as `no_enabled_suite_entry`, `suite_entry_disabled`, and `adapter_not_wired` only.
- `_coordination/20260625_harbor_bench/readiness_20260626.json:369-381` records `manifests/images/tau3_bench.yaml` as image-manifest `ready`, with `required_images=2`, `required_with_offline_transport=2`, and `required_without_offline_transport=0`.
- `_coordination/20260625_harbor_bench/readiness_20260626.json:388-413` records `tau3_bench_oracle_direct_smoke` as enabled, wired, image-ready, and ready as an image-smoke entry.

Manifest evidence:

- `manifests/images/tau3_bench.yaml:4` has status `smoke_images_ready_worker_rootless`.
- `manifests/images/tau3_bench.yaml:24` documents the rootless Docker API caveat: `DOCKER_API_VERSION=1.45` is required for CLI operations.
- `manifests/images/tau3_bench.yaml:32` says the remaining blocker is that the suite adapter is not wired yet and that the manifest only proves smoke image transport/import readiness.
- `manifests/images/tau3_bench.yaml:34-60` records both required tau3 images with P0 digest refs and fallback tar sha256s.

Suite evidence:

- `manifests/suite.example.yaml:319-333` defines the full `tau3_bench` entry as `adapter_status: pending_adapter` and `enabled: false`.
- `manifests/suite.example.yaml:335-353` defines `tau3_bench_oracle_direct_smoke` as `adapter_status: wired_legacy`, `readiness_role: image_smoke`, and `enabled: true`.

### Dry-run one-click plan

The one-click dry-run command is static and does not run adapters, models, Docker, or benchmarks.

Command result:

```text
dry_run_plan_rc 0
run_count 11
vitabench_full vitabench wired_legacy ... planned
vitabench_delivery_one_task_smoke vitabench wired_legacy ... planned
swebench_verified_qwen_code_smoke swe-bench-verified wired_legacy optional planned
repozero_py2js_smoke repozero_py2js wired_legacy required planned
cocoabench cocoabench wired_legacy ... planned
swebench_verified_mini_swe_agent swe-bench-verified wired_legacy optional planned
swebench_verified_swe_agent swe-bench-verified wired_legacy optional planned
swebench_verified_openhands swe-bench-verified wired_legacy optional planned
deepswe deepswe wired_legacy optional planned
terminal_bench_2_1_image_smoke terminal_bench_2_1 pending_adapter required planned
tau3_bench_oracle_direct_smoke tau3-bench wired_legacy required planned
```

This confirms that the default dry-run plan and the default readiness target set are different concepts: the dry-run plan includes enabled suite rows; the readiness gate aggregates the 9 tracked readiness targets.

## Stale docs

### ISSUE-READY: tau3 README still says runtime image/shared tar is missing

File:line:

- `README.md:373`

Repro:

1. Read `README.md:373`, which says tau3-bench worker offline execution still needs a prebuilt runtime image/shared tar.
2. Run the static image readiness probe:

```bash
python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('suite', 'scripts/agentic_bench_suite.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod._static_image_manifest_readiness('manifests/images/tau3_bench.yaml', project_root='.'))
PY
```

Observed static result:

```text
status: ready
blockers: []
counts: {'images': 2, 'required_images': 2, 'required_with_offline_transport': 2, 'required_without_offline_transport': 0, 'optional_placeholders': 0}
manifest_status: smoke_images_ready_worker_rootless
```

Impact:

A user following the README may spend time staging tau3 runtime images that are already represented as P0 digest refs plus fallback tars. The current blocker is suite/adapter/rootless operation, not image transport.

Fix:

Update `README.md:373` to say tau3 smoke image transport is ready for the current worker-rootless contract; the full tau3 readiness target remains blocked by the disabled full suite entry, pending full adapter, and rootless CLI/API caveats.

Dedup note:

This is a docs-freshness issue for the current README. It is distinct from earlier tau3 image-staging gaps because `manifests/images/tau3_bench.yaml` now has the transport rows.

### ISSUE-READY: scripts README says Terminal-Bench 2.1 and tau3-bench are simply disabled

File:line:

- `scripts/README.md:235-240`

Repro:

1. Read `scripts/README.md:235-240`, which lists `Terminal-Bench 2.1` and `tau3-bench` under pending adapters present but disabled in `manifests/suite.example.yaml`.
2. Cross-check the suite:
   - `manifests/suite.example.yaml:282-297` has enabled `terminal_bench_2_1_image_smoke`.
   - `manifests/suite.example.yaml:335-353` has enabled and wired `tau3_bench_oracle_direct_smoke`.
3. Cross-check readiness:
   - `_coordination/20260625_harbor_bench/readiness_20260626.json:202-230` has the TB2 image-smoke row enabled but adapter-blocked.
   - `_coordination/20260625_harbor_bench/readiness_20260626.json:388-413` has the tau3 image-smoke row enabled, wired, and ready.

Impact:

A one-click-suite user may conclude that no TB2 or tau3 suite row is active. The accurate taxonomy is: full TB2 and full tau3 are disabled/pending, but narrower image-smoke rows are present; tau3 oracle-direct smoke is already ready, while TB2 image smoke is still adapter-blocked.

Fix:

Replace the blanket disabled list with two subsections:

- Full entries disabled/pending: `terminal_bench_2_1`, `tau3_bench`, MCP-Atlas, Tool-Decathlon, programbench, NL2Repo.
- Narrow image/smoke rows enabled: `terminal_bench_2_1_image_smoke` and `tau3_bench_oracle_direct_smoke`, with their current readiness statuses.

Dedup note:

This is a README taxonomy issue, not a runner bug. It overlaps with the same suite/readiness distinction as the tau3 doc issue above but affects `scripts/README.md` and TB2 as well.

### Stale but already caveated: old local launcher examples

File:line:

- `README.md:308-343`

These lines document old local launchers such as `./run_all_smoke.sh`, `./run_gpt54mini_smoke_suite.sh`, and `./run_qwen_smoke_suite.sh`, and say the old default suite runs `vitabench terminal_bench cocoabench repozero_py2js swebench_verified tau3_bench`.

This is potentially misleading if copied out of context, but `README.md:182-186` explicitly frames the following section as historical local benchmark launcher documentation, and `README.md:401-421` explicitly says the active one-command suite is `manifests/suite.example.yaml` with the 9 readiness targets. I would not file this as a separate confirmed blocker unless users are known to land directly in the historical section.

## Command log

| Command | RC | Notes |
| --- | ---: | --- |
| `sed -n '1,760p' /Users/Zhuanz1/Desktop/ssh_work/WORKFLOW.md` | 0 | Mandatory preflight. |
| `ssh dev 'cd .../.worktrees/image-warmup-policy && hostname && pwd && git branch --show-current && git rev-parse --short HEAD && git log -1 --oneline && git status --short'` | 0 | Verified host `zwj2`, branch `feat/image-warmup-policy`, head `bd66566`. Existing unrelated dirty files were observed and not touched. |
| `nl -ba scripts/agentic_bench_suite.py | sed -n '30,60p;743,1008p;1680,1722p'` | 0 | Captured target list and readiness aggregation logic. |
| `nl -ba manifests/suite.example.yaml | sed -n '1,520p'` | 0 | Captured active suite rows and enabled/disabled state. |
| `nl -ba _coordination/20260625_harbor_bench/readiness_20260626.json | sed -n ...` | 0 | Captured checked-in readiness line evidence. |
| `nl -ba manifests/images/terminal_bench_2_1_swe_dev_cache.yaml | sed -n '1,80p'` | 0 | Captured TB2 84/89 and 5-gap manifest evidence. |
| `find manifests/images -maxdepth 1 -type f -iname '*tau*' -print -exec nl -ba {} \;` | 0 | Captured tau3 image manifest evidence. |
| `python3 scripts/agentic_bench_suite.py manifests/suite.example.yaml --readiness --json` | 1 | Expected static gate failure: readiness counts are blocked=8, ready=1, missing=0. No Docker/model/adapter execution. |
| Python stable comparison of generated readiness JSON vs `_coordination/.../readiness_20260626.json` | 0 | `stable_json_equal True`; generator itself returned 1 as expected. |
| Structured tau2 scan over `READINESS_TARGETS`, `manifests/suite.example.yaml`, and readiness JSON | 0 | No tau2 target/suite/readiness entry. |
| Broad tau2 grep over suite/readiness/image manifests | 0 | Hits only tau3 image smoke import commands, not active suite entries. |
| `scripts/run_suite_from_yaml.sh manifests/suite.example.yaml --dry-run --json` summarized by Python | 0 | Static dry-run plan only; 11 planned rows; no execution. |
| README stale-doc scans with line numbers | 0 | Found the two ISSUE-READY docs freshness items above. |

## Files changed

- `_coordination/20260625_harbor_bench/lanes/readiness-taxonomy-round33.md`

No production code, manifests, tests, commits, or pushes were changed.
