"""Vercel Python serverless function: POST /api/migrate

Body = raw .twb/.twbx bytes; query ?name=<filename>. Returns the migration
payload (summary, conversion log, consolidation, integrity) plus the generated
artifacts inline, as JSON. Same-origin with the static frontend, so no CORS.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# make the repo-root `biforge` package importable from inside /api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biforge.service import migrate_bytes  # noqa: E402
from biforge.webui_page import build_upload_page  # noqa: E402

# the deployed single-entrypoint function serves the frontend on GET and runs
# the migration on POST (all routes reach this handler on Vercel's Python runtime)
_PAGE = build_upload_page("/api/migrate")


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", ["workbook.twb"])[0]
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return self._json(400, {"error": "empty upload"})
            data = self.rfile.read(length)
            self._json(200, migrate_bytes(data, name))
        except Exception as exc:  # surface a clean message to the UI
            self._json(400, {"error": str(exc)})

    def do_GET(self) -> None:
        body = _PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
