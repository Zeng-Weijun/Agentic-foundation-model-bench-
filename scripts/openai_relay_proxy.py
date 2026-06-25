#!/usr/bin/env python3
"""Tiny OpenAI-compatible HTTP relay proxy for offline workers.

This proxy is intentionally dependency-free. Run it on `dev`, bind it to an
internal interface/port, and point offline workers at `http://<dev-ip>:<port>/v1`.
It forwards request headers and bodies to the upstream OpenAI-compatible relay.
Secrets remain in request headers or environment variables; the proxy does not
write request bodies to disk.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class ProxyHandler(BaseHTTPRequestHandler):
    upstream = urlsplit("http://8.130.49.170")
    timeout_s = 600

    def log_message(self, fmt: str, *args: object) -> None:
        path = self.path.split("?", 1)[0]
        self.server.logger.write(f"{self.log_date_time_string()} {self.command} {path} " + fmt % args + "\n")
        self.server.logger.flush()

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def do_DELETE(self) -> None:
        self._proxy()

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        target_path = self.path
        if not target_path.startswith("/"):
            target_path = "/" + target_path

        headers = {}
        for key, value in self.headers.items():
            if key.lower() in HOP_BY_HOP or key.lower() == "host":
                continue
            headers[key] = value
        headers["Host"] = self.upstream.netloc
        target_url = urlunsplit(
            (
                self.upstream.scheme,
                self.upstream.netloc,
                target_path,
                "",
                "",
            )
        )
        request = Request(target_url, data=body, headers=headers, method=self.command)
        try:
            with urlopen(request, timeout=self.timeout_s) as resp:
                status = resp.status
                reason = resp.reason
                response_headers = resp.headers.items()
                data = resp.read()
        except HTTPError as exc:
            status = exc.code
            reason = exc.reason
            response_headers = exc.headers.items()
            data = exc.read()
        except Exception as exc:  # pragma: no cover - exercised in deployment
            payload = f"upstream error: {type(exc).__name__}: {exc}\n".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(status, reason)
        for key, value in response_headers:
            if key.lower() in HOP_BY_HOP:
                continue
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default=os.environ.get("BENCH_PROXY_BIND", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BENCH_PROXY_PORT", "18540")))
    parser.add_argument("--upstream", default=os.environ.get("BENCH_PROXY_UPSTREAM", "http://8.130.49.170"))
    parser.add_argument("--timeout-s", type=int, default=int(os.environ.get("BENCH_PROXY_TIMEOUT_S", "600")))
    args = parser.parse_args()

    ProxyHandler.upstream = urlsplit(args.upstream.rstrip("/"))
    ProxyHandler.timeout_s = args.timeout_s
    server = ThreadingHTTPServer((args.bind, args.port), ProxyHandler)
    server.logger = open(os.environ.get("BENCH_PROXY_LOG", "/dev/stdout"), "a", buffering=1)
    print(f"proxy listening on {args.bind}:{args.port}, upstream={args.upstream}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
