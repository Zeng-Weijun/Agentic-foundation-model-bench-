import json, time, urllib.request, urllib.error, concurrent.futures as cf, os, sys
BASE = "http://100.100.104.140:30001/v1/chat/completions"
KEY = os.environ.get("OPENAI_API_KEY", "tb-terminus2-placeholder")
MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
# terminus-2 real operating condition: ~5k-token prompt, temperature 0.0, no tool schema.
FILLER = ("You are a terminal agent. Below is a directory listing and prior command output.\n"
          + "\n".join("file_%04d.py  %d bytes  modified 2026-07-%02d" % (i, 1000 + i * 7, (i % 28) + 1)
                      for i in range(700)))
def one(i):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are terminus-2 running a Terminal-Bench 2.1 task."},
            {"role": "user", "content": FILLER + "\n\nWorker %d: reply with exactly one shell command to list /app." % i},
        ],
        "temperature": 0.0,
        "max_tokens": 64,
    }
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + KEY})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            payload = json.loads(r.read().decode())
        dt = time.time() - t0
        ch = payload["choices"][0]
        return ("200", dt, payload.get("usage", {}).get("prompt_tokens"), ch.get("finish_reason"), payload.get("model"))
    except urllib.error.HTTPError as e:
        return ("http_%d" % e.code, time.time() - t0, None, None, None)
    except Exception as e:
        return ("exc_%s" % type(e).__name__, time.time() - t0, None, None, None)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 32
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
from collections import Counter
codes = Counter(); lats = []; ptoks = []; fins = Counter(); models = Counter()
t0 = time.time()
for r in range(ROUNDS):
    with cf.ThreadPoolExecutor(max_workers=N) as ex:
        for code, dt, pt, fin, mdl in ex.map(one, range(N)):
            codes[code] += 1; lats.append(dt)
            if pt: ptoks.append(pt)
            if fin: fins[fin] += 1
            if mdl: models[mdl] += 1
wall = time.time() - t0
lats.sort()
n = len(lats)
h5 = sum(v for k, v in codes.items() if k.startswith("http_5"))
h429 = codes.get("http_429", 0)
h4 = sum(v for k, v in codes.items() if k.startswith("http_4") and k != "http_429")
exc = sum(v for k, v in codes.items() if k.startswith("exc_"))
print("calls=%d wall=%.1fs c=%d rounds=%d" % (n, wall, N, ROUNDS))
print("HTTP200=%d 5xx=%d 429=%d other4xx=%d exceptions=%d" % (codes.get("200", 0), h5, h429, h4, exc))
print("raw_codes=%s" % dict(codes))
print("prompt_tokens median=%s min=%s max=%s" % (sorted(ptoks)[len(ptoks)//2] if ptoks else None,
                                                 min(ptoks) if ptoks else None, max(ptoks) if ptoks else None))
print("lat p50=%.2fs p95=%.2fs max=%.2fs  throughput=%.1f calls/s" % (lats[n//2], lats[int(n*0.95)-1], lats[-1], n/wall))
print("finish_reasons=%s" % dict(fins))
print("served_model=%s" % dict(models))
ok = codes.get("200", 0) == n and h5 == 0 and h429 == 0 and exc == 0
print("STRESS_%s" % ("OK" if ok else "FAIL"))
sys.exit(0 if ok else 4)
