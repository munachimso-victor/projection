#!/usr/bin/env python3
"""Serve Lyrics Operator static UI only (no import). Host on cloud in production."""

from __future__ import annotations

import http.server
import os
import socketserver

from import_server import LOCAL_IMPORT_BASE
from paths import static_root

UI_HOST = "127.0.0.1"
UI_PORT = int(os.environ.get("LYRICS_OPERATOR_UI_PORT", "3001"))
UI_BASE = f"http://{UI_HOST}:{UI_PORT}"
ROOT = static_root()


class UiHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        if self.path.endswith((".js", ".html", ".css")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def list_directory(self, path):
        # Never show a directory listing; the UI must have an index.html.
        self.send_error(404, "Not the UI root - serve the ui/ folder.")
        return None


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_ui_server(*, quiet: bool = False) -> None:
    if not (ROOT / "index.html").is_file():
        print(f"WARNING: no index.html in {ROOT}")
        print("The UI files (index.html, app.js, app.css) should be in tools/lyrics_operator/ui.")
    try:
        httpd = ThreadedTCPServer((UI_HOST, UI_PORT), UiHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(f"Port {UI_PORT} is already in use.")
            raise SystemExit(1) from exc
        raise

    httpd.quiet = quiet
    if not quiet:
        print(f"Lyrics Operator UI: {UI_BASE}/")
        print(f"Local import (separate): {LOCAL_IMPORT_BASE}")
        print("Ensure lyrics-search API is running (default http://localhost:8000)")
        print(
            f"Tip: open {UI_BASE}/?localImport={LOCAL_IMPORT_BASE} "
            "or rely on app.js defaults on localhost."
        )
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


def main() -> None:
    run_ui_server()


if __name__ == "__main__":
    main()
