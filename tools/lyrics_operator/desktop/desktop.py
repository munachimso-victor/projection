#!/usr/bin/env python3
"""Lyrics Operator desktop: UI from URL (cloud or local) + local import only.

  set LYRICS_OPERATOR_UI_URL=https://your-cdn.example.org/lyrics-operator/index.html
  python desktop.py

Local dev default UI: http://127.0.0.1:3001/ (run serve_ui.py in another terminal).
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from import_server import LOCAL_IMPORT_BASE, run_import_server
from serve_ui import UI_BASE

if sys.platform != "win32":
    print("desktop.py is for Windows only (EasyWorship + native window).")
    print()
    print("You are on:", sys.platform)
    print("For dev in a browser: python serve_ui.py and python import_server.py")
    sys.exit(1)

try:
    import webview
except ImportError:
    print("Desktop mode requires pywebview. Install with:")
    print("  pip install -r requirements-desktop.txt")
    sys.exit(1)

DEFAULT_UI_URL = os.environ.get("LYRICS_OPERATOR_UI_URL", f"{UI_BASE}/").strip() or f"{UI_BASE}/"


def ui_url_with_local_import(ui_url: str, local_import: str) -> str:
    """Append ?localImport= and ?desktop=1 so the UI uses the native bridge."""
    parsed = urlparse(ui_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return ui_url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["localImport"] = local_import.rstrip("/")
    query["desktop"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _save_dialog_type():
    """pywebview >= 5.4 uses FileDialog.SAVE; older uses webview.SAVE_DIALOG."""
    file_dialog = getattr(webview, "FileDialog", None)
    if file_dialog is not None and hasattr(file_dialog, "SAVE"):
        return file_dialog.SAVE
    return webview.SAVE_DIALOG


class DesktopApi:
    """Native bridge exposed to the page as window.pywebview.api.* (desktop only)."""

    def save_text(self, filename: str, text: str) -> dict:
        windows = webview.windows
        if not windows:
            return {"ok": False, "message": "No window available."}
        result = windows[0].create_file_dialog(
            _save_dialog_type(),
            save_filename=filename or "song.txt",
        )
        if not result:
            return {"ok": False, "cancelled": True}
        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            Path(path).write_text(text or "", encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "message": str(exc)}
        return {"ok": True, "path": str(path)}

    def open_external(self, url: str) -> dict:
        if url:
            webbrowser.open(url)
        return {"ok": True}


def main() -> None:
    ui_url = ui_url_with_local_import(DEFAULT_UI_URL, LOCAL_IMPORT_BASE)

    threading.Thread(target=run_import_server, kwargs={"quiet": True}, daemon=True).start()

    print("Lyrics Operator desktop")
    print(f"  UI:            {ui_url}")
    print(f"  Local import:  {LOCAL_IMPORT_BASE}")
    print("  Lyrics API:    set in the UI (default http://localhost:8000)")

    webview.create_window(
        "Lyrics Operator",
        ui_url,
        js_api=DesktopApi(),
        width=1100,
        height=780,
        min_size=(800, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
