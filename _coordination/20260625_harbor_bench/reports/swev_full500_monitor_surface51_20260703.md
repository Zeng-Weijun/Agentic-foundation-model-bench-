# SWE-V full500 monitor - surface51 - 2026-07-03

Rolling monitor for `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702`.

Rules: shared disk on swe_dev2 is authoritative; keys are never printed; TB2.1 stack is out of scope. Relay recovery requires 3 consecutive real `/v1/chat/completions` HTTP 200 with `choices`. Docker instability (`eval rc=1`, Docker Unix socket ReadTimeout) triggers shard rollback and cleanup of only `minisweagent-*` containers.

## Events

- 2026-07-03T09:26:09Z monitor initialized / corrected report file after shell quoting issue.
- 2026-07-03T09:26:09Z observed orchestrator advanced bad shards: done_chunks=20 rows=84 resolved=20; run.log had s002/s003/s004 eval rc=1 with shard_resolved=0.
- 2026-07-03T09:26:09Z wrote STOP, killed only minisweagent processes/containers on jvm9z (before=18 after=0), left TB2.1 containers untouched.
- 2026-07-03T09:26:09Z reverted ledger to known-good s000+s001: done_chunks=8 result_rows=32 pred_rows=32 resolved=20; moved s002-s004 to dockerinstability suffix and s005 to stopped suffix.
- 2026-07-03T09:30:05Z rl-ov2 stability gate passed: docker ps 3/3 rc=0, seconds=0, total_containers=20, minisweagent=0.
- 2026-07-03T09:30:05Z prepared safe resume script `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_resume_safe_20260703T093005Z.sh`; next poll will verify shared-disk effects only.
- 2026-07-03T09:58:50Z 30m checkpoint: STOP=False, ledger=done_chunks 8/86, result_rows=32, resolved=20. Active shard full500_s002 is still rollout-only, preds=14/14 nonempty, BadGateway/502=0, eval not started. Previous bad s002-s004 were rolled back and quarantined as dockerinstability; active s005 was stopped.
- 2026-07-03T10:27:06Z repeated Docker instability: current s002 had rollout rc=-100 nonempty=16/17 apierr=0, then eval rc=1 Docker Unix socket ReadTimeout; orchestrator advanced to done_chunks=12 rows=49.
- 2026-07-03T10:27:06Z wrote STOP, killed only minisweagent containers (before=1 after=0), reverted ledger again to done_chunks=8 result_rows=32 pred_rows=32 resolved=20, moved active s002/s003 to dockerinstability suffix. Holding; resume at CONCURRENCY=50 is not safe until rl-ov2 eval path stabilizes.
- 2026-07-03T10:27:40Z hold reason: rl-ov2 still has 20 non-SWE/TB2.1 containers Up 4-10h; minisweagent=0. Per redline I did not touch TB2.1 containers. Repeated s002 eval Docker ReadTimeout makes CONCURRENCY=50 resume unsafe until eval Docker path is actually stable/cleared.
- 2026-07-03T10:46:14Z Pod B cutover prep artifacts written: P0 map `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json`, canary script `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_canary_cutover_20260703.sh`, full resume script `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_full_resume_20260703.sh`. Canary uses independent canary dir and does not mutate original ledger; full script resumes original ledger only after canary PASS.
- 2026-07-03T10:46:14Z P0 coverage for remaining work: 78 run chunks remaining, 414 unique remaining instances, 414/414 have P0 digest refs in `manifests/images/swebench_verified_full500_p0_batch_next_20260629_171323.yaml`; first canary chunk `django-1776-django_02.tar` has 5/5 P0 instance digests.
- 2026-07-03T10:46:14Z Bootstrap gate still pending: `_coordination/20260625_harbor_bench/POD_B_BOOTSTRAP_20260703.md` not present at prep time. Do not execute cutover until that file says PASS.

## Pod B cutover plan - prepared by surface51

Gate file: `_coordination/20260625_harbor_bench/POD_B_BOOTSTRAP_20260703.md` must exist and state PASS before any Pod B run.

Current authoritative ledger remains untouched while waiting:

- original run dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702`
- ledger: `done_chunks=8/86`, `result_rows=32`, `resolved=20`, `STOP=True`
- do not resume on jvm9z.

Prepared artifacts:

- P0 digest map: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_p0_map_20260703.json`
- canary script: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_canary_cutover_20260703.sh`
- full resume script: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_full_resume_20260703.sh`

Inventory:

- run chunks total after matplotlib/xarray disk-host skip: 86
- done chunks: 8
- remaining run chunks: 78
- remaining unique instances: 414
- remaining unique instances with P0 digest: 414/414
- first canary chunk: `django-1776-django_02.tar`, 5 unique instances, all 5 have P0 digest refs
- P0 source manifest: `manifests/images/swebench_verified_full500_p0_batch_next_20260629_171323.yaml`

Transport strategy:

- Use `DOCKER_HOST=unix:///var/run/docker.sock` on Pod B privileged dockerd.
- Use P0 by immutable digest. The patched orchestrator generated by the scripts replaces shard `docker load` with `docker pull <p0_digest_ref>` and `docker tag <digest> <local_ref>`.
- First-pull concurrency is <=4 by construction: the canary/full patched orchestrator pulls serially inside each shard. If we later add a preheater, cap it at `xargs -P4`.
- Retag target remains `swebench/sweb.eval.x86_64.<instance>:latest`, matching mini-swe-agent and official eval expectations.
- Canary uses a separate copy directory `${SRC}_podb_canary_<UTC>` and does not mutate the original full500 ledger.
- Full resume script only runs after canary PASS and resumes the original shared ledger from `done_chunks=8`.

Exact gate/canary launch command from local Mac after PASS:

```bash
tmux new-session -d -s swev_podb_canary_$(date -u +%Y%m%dT%H%M%SZ) \
  "ssh -CAXY env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'bash /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_canary_cutover_20260703.sh'"
```

Canary success criteria:

- canary directory exists and has `full500_run.log`
- canary ledger advances by exactly 1 chunk from copied baseline: `done_chunks=9`
- canary results rows advance from 32 to 37 for the first chunk's 5 instances
- `eval rc=0` in canary run log
- report JSON exists for the canary shard
- `Instances with errors: 0`
- no `BadGateway`, no `Upstream request failed`, no `502`

Exact full resume command after canary PASS:

```bash
tmux new-session -d -s swev_podb_full_$(date -u +%Y%m%dT%H%M%SZ) \
  "ssh -CAXY env-kvm-57740737-bzw56.zengweijun+root.ailab-sciversealign.pod@h.pjlab.org.cn 'cd /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702 && CONCURRENCY=50 SHARD_CHUNKS=4 ROLL_TIMEOUT=3000 bash ./surface51_podb_full_resume_20260703.sh'"
```

Full resume reporting gate:

- if shard eval `rc=0`, report `resolved/n_inst`, `error_instances`, running total, and `done_chunks/86`
- if eval `rc=1` or Docker ReadTimeout, STOP and roll back that shard; this would mean Pod B did not cure the eval-path issue
- if `0-nonempty` or high 502, STOP, roll back, and hold for relay recovery

- 2026-07-03T10:48:18Z POD_B_BOOTSTRAP PASS detected; launched canary via local tmux `swev_podb_canary_20260703T104750Z` against `env-kvm-57740737-bzw56`, original full500 ledger remains STOP=True at 8/32/20.


## Pod B canary env fix progress (2026-07-03T11:05:48Z)

- Gate source: `_coordination/20260625_harbor_bench/POD_B_BOOTSTRAP_20260703.md` had `VERDICT: PASS`; cutover allowed only as canary first.
- Original jvm9z ledger remains stopped and untouched: `STOP=T`, `done_chunks=8`, `full500_results.jsonl=32`.
- Fixed lane-generated scripts only:
  - `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_canary_cutover_20260703.sh`
  - `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_full_resume_20260703.sh`
- Fix: Pod B has no `/data`, so scripts now use shared conda python `/mnt/shared-storage-user/mineru2-shared/zengweijun/conda_envs/swebench/bin/python`, offline mini-swe-agent `PYTHONPATH`, and offline config under `harness/offline_pydeps/.../minisweagent/config/benchmarks/swebench.yaml`.
- Added `LITELLM_LOCAL_MODEL_COST_MAP=True` for future runs to avoid per-shard public cost-map timeout.
- `bash -n` passed for both scripts after patch.
- Current canary tmux: `swev_podb_canary_20260703T105645Z`.
- Current canary dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702_podb_canary_20260703T105645Z`.
- Canary status at this tick: entered `full500_s008`, P0 pull/tag succeeded for 5 Django images, 5 containers launched with `--network=none`, 2/5 trajectories saved so far, no STOP.


## Pod B canary status tick (2026-07-03T11:27:49Z)

- Canary dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702_podb_canary_20260703T105645Z`.
- Status: still in rollout for `full500_s008`; no STOP; original ledger still `STOP=T done=8 results=32`.
- Progress: `traj_files=4/5`; remaining active container observed as `minisweagent-c6520f12` for `django-11138`, up about 29 minutes at last probe.
- Gate decision: do not start full-resume until this canary either completes rollout+official eval rc0 or records a fail-closed timeout/error.


## Pod B canary gate result (2026-07-03T12:04:10Z)

Verdict: **BLOCKED; do not start full-resume.**

Artifacts:
- Canary tmux launched from local control plane: `swev_podb_canary_20260703T105645Z`.
- Canary dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702_podb_canary_20260703T105645Z`.
- Original run dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702`.

What passed:
- Pod B bootstrap PASS gate was present before canary.
- Pod B uses `DOCKER_HOST=unix:///var/run/docker.sock`.
- P0 pull/tag for canary Django chunk worked; five target images were present and mini-swe-agent containers started with `--network=none`.
- Shared conda/offline_pydeps path issue fixed in lane-generated scripts; `/data/conda_envs/swebench` is no longer required.
- LiteLLM local model-cost-map env added for future attempts: `LITELLM_LOCAL_MODEL_COST_MAP=True`.

What failed:
- `full500_s008` rollout hit `ROLLOUT_TIMEOUT after 3000s`, with `nonempty=4/5`; one straggler did not produce a trajectory.
- The current orchestrator then proceeded with partial predictions, which is unsafe for canary/full gate.
- Official eval returned `eval rc=1` and showed an external worker-network dependency:
  `requests.exceptions.ConnectTimeout` against `raw.githubusercontent.com/django/django/.../tests/requirements/py3.txt` from `swebench/harness/test_spec/python.py:get_requirements_by_commit`.
- The canary wrapper also advanced to `full500_s009` after the failed one-chunk canary. I stopped only the canary process and its `minisweagent-*` containers after detecting this.

Ledger status:
- Original full500 ledger remains protected and unchanged: `STOP=T`, `done_chunks=8`, `full500_predictions.jsonl=32`, `full500_results.jsonl=32`.
- Failed canary copy ended with local-only counts: `done_chunks=9`, `predictions=37`, `results=37`; do not use it as canonical score evidence.

Fail-closed fixes applied to lane artifacts after failure:
- Patched `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/full500_model_orchestrator.py`:
  - `FAIL_ON_ROLLOUT_TIMEOUT=1` writes STOP and exits before partial preds proceed.
  - `FAIL_ON_EVAL_RC=1` writes STOP and exits before appending eval-failed shard results.
  - `MAX_SHARDS` support added.
- Patched canary launcher `surface51_podb_canary_cutover_20260703.sh`:
  - runs with `MAX_SHARDS=1 FAIL_ON_ROLLOUT_TIMEOUT=1 FAIL_ON_EVAL_RC=1`.
- Patched full launcher `surface51_podb_full_resume_20260703.sh`:
  - runs with `FAIL_ON_ROLLOUT_TIMEOUT=1 FAIL_ON_EVAL_RC=1`.
- Verification passed: `py_compile full500_model_orchestrator.py`, `bash -n surface51_podb_canary_cutover_20260703.sh`, `bash -n surface51_podb_full_resume_20260703.sh`.

Required next fix before any full resume:
1. Build or point the SWE-bench eval harness at an offline requirements/environment cache for every full500 instance. The failing path is `swebench/harness/test_spec/python.py` lines calling `requests.get()` for `MAP_REPO_TO_REQS_PATHS` / `MAP_REPO_TO_ENV_YML_PATHS`; worker must not hit GitHub raw.
2. Re-run only the one-chunk Pod B canary after that cache/patch, using the now fail-closed canary launcher.
3. Promote to full resume only if canary has clean rollout `5/5`, official eval rc0, no STOP, and no external-network stack trace.


## Offline req/env cache and second Pod B canary (2026-07-03T14:47:23Z)

Verdict: **still BLOCKED; full-resume was not started.**

Cache built on internet-enabled `dev`:
- Builder: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/build_eval_req_env_cache_20260703.py`.
- Cache dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/bench/swe-bench-verified/offline_eval_req_env_cache_20260703`.
- Log: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/eval_req_env_cache_20260703T130658Z.log`.
- RC: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/eval_req_env_cache_20260703T130658Z.rc` = `0`.
- Summary: `requirements_entries=18`, `environment_yml_entries=7`, `http_requests=44`, `errors=0`, `target_instances=500`.

Harness patch approach:
- Additive module only, no in-place edit of the shared conda/offline_pydeps package:
  `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/swev_offline_eval_cache_patch.py`.
- The generated `eval_wrap.py` now imports this module and overrides `swebench.harness.test_spec.python.get_requirements_by_commit()` and `get_environment_yml_by_commit()` to read cache files.
- Probe passed for the exact prior failing case: `django__django-11138`, repo `django/django`, commit `419a78300f7cd27611196e1e464d50fd0385ff27`, returned cached requirements text of 246 bytes.

Fail-closed launcher/orchestrator state:
- `MAX_SHARDS=1` in canary.
- `FAIL_ON_ROLLOUT_TIMEOUT=1` and `FAIL_ON_EVAL_RC=1` enabled.
- Verification passed after changes:
  - `python -m py_compile full500_model_orchestrator.py swev_offline_eval_cache_patch.py` rc 0.
  - `bash -n surface51_podb_canary_cutover_20260703.sh` rc 0.
  - `bash -n surface51_podb_full_resume_20260703.sh` rc 0.

Second canary:
- Tmux: `swev_podb_canary_reqenv_20260703T131030Z`.
- Dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702_podb_canary_20260703T131031Z`.
- Command shape: `CONCURRENCY=5 SHARD_CHUNKS=1 ROLL_TIMEOUT=5400 bash surface51_podb_canary_cutover_20260703.sh`.
- It reached the same canary chunk: `full500_s008`, `django-1776-django_02.tar`, 5 instances.
- Rollout result: `4/5` trajectories. `django-11138` remained a straggler and hit `ROLLOUT_TIMEOUT after 5400s`.
- Because fail-closed is now active, canary wrote STOP and exited before partial predictions/eval:
  `STOP=rollout timeout at full500_s008: non-clean shard; no partial proceed`.
- Counts stayed protected inside the canary copy: `done=8`, `pred=32`, `res=32`.
- Original canonical full500 ledger remains unchanged and stopped: `STOP=T`, `done=8`, `full500_results.jsonl=32`.
- No canary `minisweagent-*` containers remained after timeout; only an unrelated gold revalidation process from another lane was observed and not touched.

Why jvm9z did not expose this earlier:
- The canonical completed shards visible in the old ledger/log are `s000/s001` with eval rc0 and no `raw.githubusercontent.com` stack trace.
- The first repeated failure on jvm9z was Docker API instability (`UnixHTTPConnectionPool(... read timeout=60)`) in `s002`, so it masked the next layer of failure.
- Pod B removed the Docker API/rootless overlay failure, which exposed the SWE-bench harness raw-GitHub requirements/env dependency during Django eval.
- The raw-GitHub issue is therefore a latent full-offline correctness bug, not a Pod B-specific Docker problem.

Gate decision:
- Do **not** start full resume.
- The req/env cache blocker is fixed in the lane artifact, but the selected next canary chunk is still not clean because `django-11138` does not finish rollout even with `ROLL_TIMEOUT=5400`.
- Next safe options for lead decision:
  1. Retry with a single-instance diagnostic canary for `django__django-11138` to classify model/agent hang without risking the full run.
  2. Move `django__django-11138` to a deferred/timeout bucket and require an explicit policy before allowing full resume past `full500_s008`.
  3. Lower per-shard concurrency and/or split canary chunk into per-instance gates, but do not claim full500 clean until all five instances in this chunk have nonempty trajectories and eval rc0.


## Single-instance diagnostic: django__django-11138 (2026-07-03T15:49Z)

Verdict: **classified as (b) model/tool-loop timeout, not relay outage and not harness/eval infra.** Do not full-resume yet; this requires lead approval of the defer/accounting strategy below.

Run command and scope:
- Local tmux session: `swev_diag_django11138_20260703T150401Z`.
- Remote command shape: `TIMEOUT_SECONDS=2700 bash /mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702/surface51_podb_single_django11138_diag_20260703.sh` on Pod B `env-kvm-57740737-bzw56`.
- Instance: `django__django-11138` only.
- Image transport: P0 digest `100.97.118.137:8555/swe-data-harness/swebench-verified-django-django-11138@sha256:04f22446fa47ab60934ba38b9921373b434b956fdd253f6b3fb45b93fe8c8ccb`, local tag `swebench/sweb.eval.x86_64.django_1776_django-11138:latest`.
- Diagnostic dir: `/mnt/shared-storage-user/mineru2-shared/zengweijun/swe/rootless/reports/swev_full500_model_20260702_podb_diag_django__django-11138_20260703T150402Z`.

Observed result:
- `rollout.rc=124`; the 45 minute hard timeout fired.
- `trajectory_count=0`; no patch/trajectory was produced.
- LiteLLM instrumentation loaded successfully via diagnostic-only `sitecustomize.py`.
- LiteLLM calls: `completion_start=36`, `completion_end=35`, `completion_error=0`.
- Request latencies included long but successful round trips: max completed call `500.690s`; later completed calls `318.639s`, `247.094s`, `184.667s`; the final call started at `2026-07-03T15:48:21Z` and was killed by the global timeout before an end/error event could be written.
- The target testbed container was started with `--network=none`; no official eval phase was launched in this diagnostic, and no SWE-bench harness raw-GitHub stack trace was involved.

Classification rationale:
- Not (a) relay/proxy stop: there was no 5xx, no LiteLLM completion error, and the trace shows repeated successful request/response cycles through the full 45 minute window.
- Not (c) harness/eval/task container infra: no eval ran; the only observed container was the normal sleeping mini-swe-agent testbed container, and there was no Docker API or harness stack trace.
- Manual classification is therefore (b): model/tool-loop or timeout/no-patch on this instance. The generated `diagnosis_summary.json` labeled `infra_or_relay_hung_request` only because the final request was active when the outer timeout killed the process; that is too conservative given 35 successful completions and zero errors before timeout.

Ledger and cleanup:
- Canonical full500 ledger remains unchanged and stopped: `STOP=surface51 hold: repeated s002 eval rc=1 Docker ReadTimeout at 20260703T102706Z; ledger reverted to 8 chunks; do not resume until rl-ov2 eval path is stable`.
- Canonical progress remains `done_chunks=8`, `full500_predictions.jsonl=32`, `full500_results.jsonl=32`.
- The diagnostic script had a cleanup bug: `container_cleanup.log` contains `xargs: DOCKER_HOST=unix:///var/run/docker.sock: No such file or directory`, and `containers_after.txt` still listed `minisweagent-8dfe8586`.
- I manually removed only that diagnostic container with `DOCKER_HOST=unix:///var/run/docker.sock docker rm -f minisweagent-8dfe8586`; cleanup rc was `0`. No unrelated gold revalidation or full500 process was touched.

Draft defer/accounting strategy for lead approval:
1. Mark `django__django-11138` as `unresolved_timeout_no_patch` / model failure for this run, with artifact pointer to the diagnostic dir above.
2. Do not keep blocking Pod B full resume on repeated attempts for this same instance unless a new infra symptom appears.
3. Before resuming full500, modify the full runner accounting policy so a classified timeout/no-patch case produces an explicit unresolved record rather than holding the entire shard forever. The preferred record shape is: instance id, shard id, rc `124`, empty/no-op patch or no-patch marker, `classification=model_timeout_no_patch`, diagnostic artifact path, and official eval result counted as unresolved once an eval-safe placeholder is supported.
4. Resume is still gated on lead approval. Without that approval, `full500_s008` remains blocked because the current fail-closed canary requires `5/5` nonempty trajectories before eval.
5. If approved, the next operational step should be a policy canary on `full500_s008` that carries the four completed predictions plus the explicit `django__django-11138` unresolved/no-patch record through official eval, requiring eval rc `0`, no external-network trace, and no STOP before full resume.

Current gate decision:
- **No full resume started.**
- **No clean canary chunk started**, because this branch is classification (b) and needs policy approval rather than an infra fix/retry.

---

## by-85 顶班: s008 policy-canary official eval (2026-07-04 ~00:25)
51 hit Codex quota (recovers 00:54); 85 ran the s008 policy-canary eval per handoff. **NOT a full resume** — full500 resume is left for 51.
- **Predictions:** 51's 4 s008 rollout preds (django-11095/11099/11119/11133, real model patches) + `django__django-11138` explicit no-patch record (the straggler dropped by the 5400s ROLLOUT_TIMEOUT).
- **Eval:** official `swebench.harness.run_evaluation` via 51's `eval_wrap.py` (inherits the offline requirements-cache patch `swev_offline_eval_cache_patch` + docker API 1.44 pin), Pod B `unix:///var/run/docker.sock`, `--cache_level env`, c=4, **isolated** report dir `swev_s008_eval_by85_20260704/`. **0 rollout token** (eval = docker only).
- **RESULT (green):** submitted 5, completed 4, **resolved 4/4** (django-11095/11099/11119/11133), empty_patch 1 (django-11138, expected), unresolved 0, **errors 0**.
- **Acceptance:** eval rc 0 (errors 0, report written) ✓ | external-net stack trace (raw.githubusercontent / github / pypi / ConnectionError) = **0 hits** ✓ | STOP generated in eval dir = **none** ✓.
- **Evidence:** `swev_s008_eval_by85_20260704/eval.log` + `gpt-5.4-mini.s008eval_by85.json`.
- **RESUME-CLEARED**: the offline eval pipeline (eval_wrap + offline requirements cache) is verified clean on Pod B for s008 (offline-clean, no STOP, 4/4 resolve). **51 may take over the full500 resume at 00:54** — 85 did NOT resume. 51's STOP / ledger / run dirs left untouched (read-only throughout).
