"""Tiny local server: serves the page and POST /api/explain. Binds to 127.0.0.1 only.
Run: python3 app/server.py   (EXPLAIN_MODE=mock|anthropic|mock:fail|mock:timeout|mock:bad ...)"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import explain as ex

HERE = Path(__file__).resolve().parent
STATIC = {"/": "index.html", "/index.html": "index.html", "/explain-client.js": "explain-client.js"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8"}


def make_handler(adapter, timeout, prompt_id):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, payload, ctype="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            name = STATIC.get(self.path.split("?")[0])
            if not name:
                return self._send(404, {"error": {"code": "not_found", "message": "Not found"}})
            self._send(200, (HERE / name).read_bytes(), TYPES[Path(name).suffix])

        def do_POST(self):
            if self.path != "/api/explain":
                return self._send(404, {"error": {"code": "not_found", "message": "Not found"}})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0:
                return self._send(400, {"error": {"code": "malformed", "message": "Bad Content-Length"}})
            if length > ex.MAX_BODY:
                return self._send(413, {"error": {"code": "too_long", "message": "Request is too long"}})
            body = self.rfile.read(length)
            try:
                self._send(200, ex.explain(body, adapter, timeout, prompt_id))
            except ex.ValidationError as exc:
                self._send(exc.status, {"error": {"code": exc.code, "message": exc.message}})
    return Handler


def make_server(mode="mock", timeout=ex.DEFAULT_TIMEOUT, port=0, prompt_id=ex.DEFAULT_PROMPT):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(ex.make_adapter(mode, timeout), timeout, prompt_id))


if __name__ == "__main__":
    mode = os.environ.get("EXPLAIN_MODE", "mock")
    srv = make_server(mode, float(os.environ.get("EXPLAIN_TIMEOUT", ex.DEFAULT_TIMEOUT)),
                      int(os.environ.get("PORT", "8000")), os.environ.get("EXPLAIN_PROMPT", ex.DEFAULT_PROMPT))
    print(f"Smart Campus on http://127.0.0.1:{srv.server_address[1]}/  (explain mode: {mode})")
    srv.serve_forever()
