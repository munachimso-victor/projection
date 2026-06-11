"""Local EasyWorship import bridge (Windows + songimport.py). Stdlib only."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from paths import songimport_script

SONGIMPORT_SCRIPT = songimport_script()

# songimport.main() mutates process-global stdout/stderr during capture; serialize imports.
_IMPORT_LOCK = threading.Lock()
_songimport_module = None


def _load_songimport():
    """Load songimport.py as a module so we can call it in-process.

    Calling in-process (instead of subprocess + sys.executable) is required for the
    frozen exe, where sys.executable is LyricsOperator.exe and would relaunch the app.
    """
    global _songimport_module
    if _songimport_module is not None:
        return _songimport_module
    spec = importlib.util.spec_from_file_location("songimport", str(SONGIMPORT_SCRIPT))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load songimport from {SONGIMPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["songimport"] = module
    spec.loader.exec_module(module)
    _songimport_module = module
    return module


def capabilities() -> dict[str, Any]:
    platform = sys.platform
    if platform != "win32":
        return {
            "easyworship_import": False,
            "platform": platform,
            "reason": "EasyWorship import requires Windows.",
        }
    if not SONGIMPORT_SCRIPT.is_file():
        return {
            "easyworship_import": False,
            "platform": platform,
            "reason": f"songimport.py not found at {SONGIMPORT_SCRIPT}",
        }
    return {
        "easyworship_import": True,
        "platform": platform,
    }


def import_lyrics(
    lyrics_plain: str,
    *,
    title: str | None = None,
    author: str | None = None,
) -> dict[str, Any]:
    caps = capabilities()
    if not caps.get("easyworship_import"):
        return {
            "ok": False,
            "message": caps.get("reason", "Import not available."),
            "output": "",
        }

    text = (lyrics_plain or "").strip()
    if len(text) < 10:
        return {
            "ok": False,
            "message": "Lyrics text is too short to import.",
            "output": "",
        }

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(text)
            tmp_path = Path(handle.name)

        argv: list[str] = [str(tmp_path)]
        if title and title.strip():
            argv.extend(["--title", title.strip()])
        if author and author.strip():
            argv.extend(["--author", author.strip()])

        with _IMPORT_LOCK:
            module = _load_songimport()
            buffer = io.StringIO()
            code = 0
            try:
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    result = module.main(argv)
                code = int(result or 0)
            except SystemExit as exc:  # argparse / verify_databases_or_exit
                code = int(exc.code or 0) if isinstance(exc.code, int) else 1
            except Exception as exc:  # noqa: BLE001 - report any importer error to UI
                output = buffer.getvalue().strip()
                return {
                    "ok": False,
                    "message": f"Import error: {exc}",
                    "output": output,
                }

        output = buffer.getvalue().strip()
        if code == 0:
            last_line = output.splitlines()[-1] if output else "Import completed."
            return {"ok": True, "message": last_line, "output": output}

        return {
            "ok": False,
            "message": f"Import failed (exit code {code}).",
            "output": output,
            "exit_code": code,
        }
    except OSError as exc:
        return {
            "ok": False,
            "message": f"Failed to import: {exc}",
            "output": "",
        }
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def parse_import_body(raw: bytes) -> dict[str, Any] | tuple[int, str]:
    try:
        data = json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError:
        return 400, "Invalid JSON body."

    if not isinstance(data, dict):
        return 400, "JSON body must be an object."

    lyrics_plain = data.get("lyrics_plain")
    if not isinstance(lyrics_plain, str):
        return 400, "lyrics_plain is required and must be a string."

    title = data.get("title")
    author = data.get("author")
    if title is not None and not isinstance(title, str):
        return 400, "title must be a string."
    if author is not None and not isinstance(author, str):
        return 400, "author must be a string."

    return {
        "lyrics_plain": lyrics_plain,
        "title": title,
        "author": author,
    }
