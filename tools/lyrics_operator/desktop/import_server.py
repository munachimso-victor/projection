#!/usr/bin/env python3
"""Local EasyWorship import API only (stdlib). Used by desktop.py and cloud-hosted UI."""

from __future__ import annotations

import http.server
import json
import socketserver
from urllib.parse import urlparse

from local_ew import capabilities, import_lyrics, parse_import_body

IMPORT_HOST = "127.0.0.1"
IMPORT_PORT = 3000
LOCAL_IMPORT_BASE = f"http://{IMPORT_HOST}:{IMPORT_PORT}"


class LocalImportMixin:
    """EW import routes; CORS for UI served from another origin (cloud or serve_ui)."""

    def _path(self) -> str:
        return urlparse(self.path).path

    def _add_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_OPTIONS(self) -> None:
        if self._path().startswith("/local/"):
            self.send_response(204)
            self._add_cors_headers()
            self.end_headers()
            return
        self.send_error(404)

    def _handle_local_get(self) -> bool:
        if self._path() == "/local/capabilities":
            self._send_json(200, capabilities())
            return True
        return False

    def _handle_local_post(self) -> bool:
        if self._path() != "/local/import":
            return False
        parsed = parse_import_body(self._read_body())
        if isinstance(parsed, tuple):
            code, message = parsed
            self._send_json(code, {"ok": False, "message": message, "output": ""})
            return True
        result = import_lyrics(
            parsed["lyrics_plain"],
            title=parsed.get("title"),
            author=parsed.get("author"),
        )
        status = 200 if result.get("ok") else 502
        self._send_json(status, result)
        return True


class ImportHandler(LocalImportMixin, http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def do_GET(self) -> None:
        if not self._handle_local_get():
            self.send_error(404)

    def do_POST(self) -> None:
        if not self._handle_local_post():
            self.send_error(405, "Method Not Allowed")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _bind_server() -> ThreadedTCPServer:
    try:
        return ThreadedTCPServer((IMPORT_HOST, IMPORT_PORT), ImportHandler)
    except OSError as exc:
        if exc.errno == 98:  # EADDRINUSE
            print(f"Port {IMPORT_PORT} is already in use.")
            print("Stop the other import server (Ctrl+C), or:")
            print(f"  fuser -k {IMPORT_PORT}/tcp")
            raise SystemExit(1) from exc
        raise


def run_import_server(*, quiet: bool = False) -> None:
    with _bind_server() as httpd:
        httpd.quiet = quiet
        if not quiet:
            print(f"Import API: {LOCAL_IMPORT_BASE}")
            caps = capabilities()
            if caps.get("easyworship_import"):
                print("EasyWorship import: available")
            else:
                print(f"EasyWorship import: unavailable ({caps.get('reason', 'unknown')})")
        httpd.serve_forever()


def main() -> None:
    run_import_server()


if __name__ == "__main__":
    main()
