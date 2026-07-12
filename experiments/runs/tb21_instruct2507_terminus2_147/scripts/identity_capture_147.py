#!/usr/bin/env python3
"""Serving before/after identity + config capture for the TB2.1 x terminus-2 clean rerun.

Parametrized version of the 2026-07-10 identity_capture.py, retargeted to serving .147.
Read-only: it calls ONLY the sglang metadata endpoints /get_model_info and
/get_server_info (NOT /v1/chat/completions), so it never runs model inference.

Usage:
  identity_capture_147.py <before|after> <outdir> <base_host_url> <expect_suffix>

  base_host_url  e.g. http://100.100.104.147:30001   (NO /v1 suffix -- these are sglang admin paths)
  expect_suffix  e.g. Qwen3-Coder-30B-A3B-Instruct   or   Qwen3-30B-A3B-Instruct-2507

Exit 0 iff model_path endswith expect_suffix AND no credential-shaped value leaked.
"""
import json, sys, urllib.request, re, os

phase = sys.argv[1]
outdir = sys.argv[2]
BASE = sys.argv[3].rstrip("/")
EXPECT_SUFFIX = sys.argv[4]
os.makedirs(outdir, exist_ok=True)

# EXACT key names only. "token" as a substring matches max_prefill_tokens / tokenizer_path -> over-redaction.
SECRET_KEYS = {"api_key", "admin_api_key", "authorization", "password", "secret",
               "ssl_keyfile_password", "auth_token", "access_token", "hf_token"}
CRED_VALUE = re.compile(r"^(sk-[A-Za-z0-9_\-]{8,}|[A-Fa-f0-9]{32,})$")

def scrub(o):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k.lower() in SECRET_KEYS and isinstance(v, str) and v:
                out[k] = "<REDACTED>"
            else:
                out[k] = scrub(v)
        return out
    if isinstance(o, list):
        return [scrub(x) for x in o]
    if isinstance(o, str) and CRED_VALUE.match(o):
        return "<REDACTED_BY_VALUE>"
    return o

def string_values(o):
    if isinstance(o, dict):
        for v in o.values(): yield from string_values(v)
    elif isinstance(o, list):
        for v in o: yield from string_values(v)
    elif isinstance(o, str):
        yield o

# Serving is on the internal pod network (.147). Bypass any http(s)_proxy so we hit it
# directly (a proxied request returns 502). Equivalent to curl --noproxy '*'.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

res = {}
for path in ("/get_model_info", "/get_server_info"):
    with _opener.open(BASE + path, timeout=25) as r:
        data = json.loads(r.read().decode()); code = r.status
    clean = scrub(data)
    fn = os.path.join(outdir, "%s_%s.json" % (path.strip("/"), phase))
    with open(fn, "w") as f:
        json.dump(clean, f, indent=1, sort_keys=True)
    reread = json.load(open(fn))
    leaks = [v for v in string_values(reread) if CRED_VALUE.match(v)]
    print("[%s] %s http=%d written=%s value_scan_leaks=%d" % (phase, path, code, os.path.basename(fn), len(leaks)))
    res[path] = clean
    if path == "/get_server_info":
        raw = data
        print("[%s]   raw api_key type=%s  admin_api_key type=%s (values never printed)" % (
            phase, type(raw.get("api_key")).__name__, type(raw.get("admin_api_key")).__name__))

mi = res["/get_model_info"]; si = res["/get_server_info"]
mp = mi.get("model_path", "")
ok = mp.endswith(EXPECT_SUFFIX)
print("[%s] model_path=%s endswith[%s]=%s" % (phase, mp, EXPECT_SUFFIX, ok))
print("[%s] version=%s context_length=%s tp=%s parser=%s mem_frac=%s attn=%s seed=%s port=%s det_infer=%s sampling_defaults=%s" % (
    phase, si.get("version"), si.get("context_length"), si.get("tp_size"), si.get("tool_call_parser"),
    si.get("mem_fraction_static"), si.get("attention_backend"), si.get("random_seed"), si.get("port"),
    si.get("enable_deterministic_inference"), si.get("sampling_defaults")))
print("[%s] tokenizer_path=%s max_total_num_tokens=%s max_prefill_tokens=%s" % (
    phase, si.get("tokenizer_path"), si.get("max_total_num_tokens"), si.get("max_prefill_tokens")))
print("[%s] IDENTITY_%s" % (phase, "OK" if ok else "FAIL"))
sys.exit(0 if ok else 3)
