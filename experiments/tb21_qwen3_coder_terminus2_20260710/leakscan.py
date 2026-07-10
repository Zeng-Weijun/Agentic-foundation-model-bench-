import json, re, sys, os
# TRUE value-level scan: walk JSON, inspect string VALUES only (never keys).
CRED = re.compile(r"^(sk-[A-Za-z0-9_\-]{8,}|[A-Fa-f0-9]{32,}|[A-Za-z0-9+/]{40,}={0,2})$")
def values(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from values(v, "%s.%s" % (path, k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from values(v, "%s[%d]" % (path, i))
    elif isinstance(o, str):
        yield path, o
bad = 0
for fn in sys.argv[1:]:
    j = json.load(open(fn))
    hits = [(p, v) for p, v in values(j) if CRED.match(v)]
    keyfields = [(p, v) for p, v in values(j) if re.search(r"api_key|token|secret|password", p, re.I)]
    print("--- %s" % os.path.basename(fn))
    print("    string values scanned: %d" % sum(1 for _ in values(j)))
    print("    credential-shaped VALUES: %d %s" % (len(hits), [(p, v[:6]+"...") for p, v in hits]))
    print("    values under key-name matching api_key/token/secret: %s" % [(p, v) for p, v in keyfields])
    bad += len(hits)
print("LEAK_SCAN_%s" % ("FAIL" if bad else "CLEAN"))
sys.exit(1 if bad else 0)
