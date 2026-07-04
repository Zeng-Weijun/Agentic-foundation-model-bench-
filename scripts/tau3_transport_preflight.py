import sys, os, glob, hashlib, re
DS = sys.argv[1]
MOUNT = "./runtime-server/task_config.json:/app/task_config.json:ro"
# 55-hardening: fail-closed against the FROZEN taskid_list (375). Catches spurious/extra dirs (e.g. the
# quarantined tau3-telecom-0 / tau3-banking_knowledge-0 malformed WIP) AND missing tasks — a glob-count
# alone would silently accept spurious dirs. taskid_sha = sha256 of sorted "tau3-*" basenames + trailing \n
# (same recipe as `ls -d tau3-* | xargs -n1 basename | sort | sha256sum`).
EXPECTED_TASKID_SHA = "ef22ab2741b57b0fd84ed452366d63a132de58ab19b12c36376cf7eb584c9dc0"
EXPECTED_COUNT = 375
alldirs = sorted(d for d in glob.glob(os.path.join(DS, "*")) if os.path.isdir(d))
tasks = [d for d in alldirs if os.path.basename(d).startswith("tau3-")]
extra_nontau3 = [os.path.basename(d) for d in alldirs if not os.path.basename(d).startswith("tau3-")]
taskids = sorted(os.path.basename(d) for d in tasks)
taskid_sha = hashlib.sha256(("\n".join(taskids) + "\n").encode()).hexdigest()
frozen_match = (taskid_sha == EXPECTED_TASKID_SHA)
count_ok = (len(tasks) == EXPECTED_COUNT)
missing_cfg, missing_mount, eff_hashes = [], [], set()
for t in tasks:
    b = os.path.basename(t)
    cfg = os.path.join(t, "environment/runtime-server/task_config.json")
    if not os.path.isfile(cfg) or os.path.getsize(cfg) == 0:
        missing_cfg.append(b); continue
    comp = os.path.join(t, "environment/docker-compose.yaml")
    if not os.path.isfile(comp):
        missing_mount.append(b); continue
    s = open(comp).read()
    if MOUNT in s:
        eff = s
    else:
        # insert the task_config mount right after the tau3-runtime agent-logs volume entry
        eff, n = re.subn(r'(- \$\{HOST_AGENT_LOGS_PATH\}:\$\{ENV_AGENT_LOGS_PATH\})',
                         r'\1\n      - ' + MOUNT, s, count=1)
        if n == 0:  # anchor not found -> cannot produce mount = fail-closed
            missing_mount.append(b); continue
    if MOUNT not in eff:
        missing_mount.append(b); continue
    eff_hashes.add(hashlib.sha256(eff.encode()).hexdigest())
print(f"tasks={len(tasks)} (non-tau3 dirs ignored: {extra_nontau3[:3]} n={len(extra_nontau3)})")
print(f"frozen_taskid_list: count={len(tasks)}/{EXPECTED_COUNT} count_ok={count_ok} "
      f"sha_match={frozen_match} (cur={taskid_sha[:16]} vs frozen={EXPECTED_TASKID_SHA[:16]})")
print(f"task_config_present={len(tasks)-len(missing_cfg)}/{len(tasks)}  missing={missing_cfg[:5]}(n={len(missing_cfg)})")
print(f"effective_compose_mount_present={len(tasks)-len(missing_mount)}/{len(tasks)}  missing={missing_mount[:5]}(n={len(missing_mount)})")
print(f"unique_effective_compose_hashes={len(eff_hashes)}")
if len(eff_hashes) == 1:
    print(f"effective_compose_sha256={next(iter(eff_hashes))}")
FAIL = (not frozen_match) or (not count_ok) or bool(missing_cfg) or bool(missing_mount) or len(eff_hashes) != 1
print("PREFLIGHT:", "FAIL" if FAIL else "PASS (375/375 frozen-taskid + task_config + uniform effective compose w/ mount)")
sys.exit(1 if FAIL else 0)
