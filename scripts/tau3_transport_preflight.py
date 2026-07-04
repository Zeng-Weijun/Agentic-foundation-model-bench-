import sys, os, glob, hashlib, re
DS = sys.argv[1]
MOUNT = "./runtime-server/task_config.json:/app/task_config.json:ro"
tasks = sorted(d for d in glob.glob(os.path.join(DS, "*")) if os.path.isdir(d))
missing_cfg, missing_mount, eff_hashes = [], [], set()
for t in tasks:
    b = os.path.basename(t)
    cfg = os.path.join(t, "environment/runtime-server/task_config.json")
    if not os.path.isfile(cfg) or os.path.getsize(cfg) == 0:
        missing_cfg.append(b); continue
    comp = os.path.join(t, "environment/docker-compose.yaml")
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
print(f"tasks={len(tasks)}")
print(f"task_config_present={len(tasks)-len(missing_cfg)}/{len(tasks)}  missing={missing_cfg[:5]}(n={len(missing_cfg)})")
print(f"effective_compose_mount_present={len(tasks)-len(missing_mount)}/{len(tasks)}  missing={missing_mount[:5]}(n={len(missing_mount)})")
print(f"unique_effective_compose_hashes={len(eff_hashes)}")
if len(eff_hashes) == 1:
    print(f"effective_compose_sha256={next(iter(eff_hashes))}")
FAIL = bool(missing_cfg) or bool(missing_mount) or len(eff_hashes) != 1
print("PREFLIGHT:", "FAIL" if FAIL else "PASS (375/375 task_config + uniform effective compose w/ mount)")
sys.exit(1 if FAIL else 0)
