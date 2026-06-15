#!/usr/bin/env python3
"""Lyrics Operator desktop: UI from URL (cloud or local) + local import only.

  python desktop.py

Default UI: PRODUCTION_UI_URL in desktop.py (cloud). Local dev:
  set LYRICS_OPERATOR_LOCAL=1
  set LYRICS_OPERATOR_UI_URL=http://127.0.0.1:3001/
  python desktop.py
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from import_server import LOCAL_IMPORT_BASE, run_import_server

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

# Cloud UI (Caddy on the droplet). Change this when the host/IP changes.
PRODUCTION_UI_URL = "http://159.65.231.252/"

# Printed at startup so you can confirm the exe was rebuilt (bump when desktop logic changes).
DESKTOP_BUILD = "ew-data-dir-2026-06-13"

# Local UI only when explicitly requested (serve_ui.py on :3001):
#   set LYRICS_OPERATOR_LOCAL=1
#   set LYRICS_OPERATOR_UI_URL=http://127.0.0.1:3001/
_LOCAL_UI_URL = "http://127.0.0.1:3001/"


def default_ui_url() -> str:
    use_local = os.environ.get("LYRICS_OPERATOR_LOCAL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if use_local:
        return os.environ.get("LYRICS_OPERATOR_UI_URL", _LOCAL_UI_URL).strip() or _LOCAL_UI_URL
    return PRODUCTION_UI_URL


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


def _folder_dialog_type():
    """pywebview >= 5.4 uses FileDialog.FOLDER; older uses webview.FOLDER_DIALOG."""
    file_dialog = getattr(webview, "FileDialog", None)
    if file_dialog is not None and hasattr(file_dialog, "FOLDER"):
        return file_dialog.FOLDER
    return webview.FOLDER_DIALOG


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

    def pick_folder(self) -> dict:
        windows = webview.windows
        if not windows:
            return {"ok": False, "message": "No window available."}
        result = windows[0].create_file_dialog(_folder_dialog_type())
        if not result:
            return {"ok": False, "cancelled": True}
        path = result[0] if isinstance(result, (list, tuple)) else result
        return {"ok": True, "path": str(path)}


def main() -> None:
    use_local = os.environ.get("LYRICS_OPERATOR_LOCAL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    ui_url = ui_url_with_local_import(default_ui_url(), LOCAL_IMPORT_BASE)

    threading.Thread(target=run_import_server, kwargs={"quiet": True}, daemon=True).start()

    print("Lyrics Operator desktop")
    print(f"  Build:         {DESKTOP_BUILD}")
    print(f"  UI mode:       {'local' if use_local else 'cloud'}")
    print(f"  UI:            {ui_url}")
    print(f"  Local import:  {LOCAL_IMPORT_BASE}")
    print("  Lyrics API:    set in the UI (auto /api on cloud; localhost:8000 for local dev)")
    if use_local:
        print("  (LYRICS_OPERATOR_LOCAL is set - unset it for cloud default)")

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
