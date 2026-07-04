import sys, re, hashlib, glob, os
DS, OUT, MAIN, RT = sys.argv[1:5]
MOUNT = "./runtime-server/task_config.json:/app/task_config.json:ro"
srcs = sorted(glob.glob(os.path.join(DS, "*/environment/docker-compose.yaml")))
hs = set(); n_mount = n_img = 0; sample = None; missing = []
for c in srcs:
    s = open(c).read()
    s2 = re.sub(r'(- \$\{HOST_AGENT_LOGS_PATH\}:\$\{ENV_AGENT_LOGS_PATH\})', r'\1\n      - ' + MOUNT, s, count=1)
    s2 = re.sub(r'build:\s*\n\s*context:\s*\./runtime-server', 'image: ' + RT, s2, count=1)
    ok = (MOUNT in s2) and (RT in s2)
    if MOUNT in s2: n_mount += 1
    if RT in s2: n_img += 1
    if not ok: missing.append(os.path.basename(os.path.dirname(os.path.dirname(c))))
    hs.add(hashlib.sha256(s2.encode()).hexdigest())
    if sample is None: sample = s2
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "tau3_effective_compose.sample.yaml"), "w").write(sample)
print("tasks=%d mount_present=%d/%d runtime_image=%d/%d unique_effective_hash=%d missing=%s" %
      (len(srcs), n_mount, len(srcs), n_img, len(srcs), len(hs), missing[:3]))
print("effective_compose_full_sha256=" + (next(iter(hs)) if len(hs) == 1 else "NONUNIFORM_" + str(len(hs))))
