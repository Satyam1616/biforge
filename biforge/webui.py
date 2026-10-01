"""Local web UI for BIForge.

Zero-dependency HTTP server (Python stdlib only). Serves a single-page UI,
accepts a .twb/.twbx upload as the raw POST body, runs the migration pipeline,
and returns a JSON summary plus downloadable artifacts. Everything stays on the
local machine.

Run:  python -m biforge.webui [--port 8765] [--no-browser]
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import cli
from .payload import build_payload
from .webui_page import PAGE

_ROOT = tempfile.mkdtemp(prefix="biforge_web_")
_RUNS: dict[str, str] = {}          # run_id -> output directory


def _payload(run_id: str, res: dict) -> dict:
    p = build_payload(res)
    p["run_id"] = run_id
    p["file_base"] = f"/download/{run_id}/"
    return p


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):            # keep the console quiet
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = urlparse(self.path)
        if parts.path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if parts.path.startswith("/download/"):
            return self._download(parts.path)
        self._send(404, "not found", "text/plain")

    def _download(self, path):
        segs = path.split("/", 3)          # ['', 'download', run_id, filename]
        if len(segs) != 4:
            return self._send(404, "not found", "text/plain")
        run_id, fname = segs[2], unquote(segs[3])
        out_dir = _RUNS.get(run_id)
        safe = os.path.basename(fname)
        if not out_dir or safe != fname:
            return self._send(404, "not found", "text/plain")
        full = os.path.join(out_dir, safe)
        if not os.path.isfile(full):
            return self._send(404, "not found", "text/plain")
        ctype = ("text/html; charset=utf-8" if safe.endswith(".html")
                 else "application/json" if safe.endswith(".json")
                 else "text/plain; charset=utf-8")
        with open(full, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def do_POST(self):
        parts = urlparse(self.path)
        if parts.path != "/migrate":
            return self._send(404, "not found", "text/plain")
        try:
            qs = parse_qs(parts.query)
            name = qs.get("name", ["workbook.twb"])[0]
            ext = os.path.splitext(name)[1].lower() or ".twb"
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            run_id = secrets.token_hex(6)
            out_dir = os.path.join(_ROOT, run_id)
            os.makedirs(out_dir, exist_ok=True)
            in_path = os.path.join(out_dir, "input" + ext)
            with open(in_path, "wb") as fh:
                fh.write(data)
            res = cli.run(in_path, out_dir, want_json=True)
            _RUNS[run_id] = out_dir
            self._send(200, json.dumps(_payload(run_id, res)),
                       "application/json")
        except Exception as exc:
            self._send(400, json.dumps({"error": str(exc)}), "application/json")


def serve(port: int = 8765, open_browser: bool = True) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"BIForge web UI running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        srv.shutdown()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="biforge.webui",
                                 description="BIForge local web UI")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    serve(args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
