"""Resolve UI and songimport paths for dev vs PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def static_root() -> Path:
    """HTML/JS/CSS directory (../ui in dev; bundle root when frozen)."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent / "ui"


def deploy_root() -> Path:
    """Folder containing LyricsOperator.exe (onedir) or the exe itself (onefile)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def songimport_script() -> Path:
    """First existing songimport.py (bundled, next to exe, or dev tree)."""
    # desktop/ -> lyrics_operator/ -> tools/ ; songimport lives in tools/ew_song_writer/
    tools_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        deploy_root() / "ew_song_writer" / "songimport.py",
        tools_dir / "ew_song_writer" / "songimport.py",
    ]
    if is_frozen():
        bundled = Path(sys._MEIPASS) / "ew_song_writer" / "songimport.py"
        candidates.insert(0, bundled)

    for path in candidates:
        if path.is_file():
            return path

    return candidates[0]
