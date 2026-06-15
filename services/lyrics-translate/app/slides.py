from __future__ import annotations

import re
from typing import List

DEFAULT_TRANSLATED_MAX_LINES = 6

# Section labels (Verse, Chorus, …) split stanzas when blank lines are missing, then
# are removed from output. EasyWorship uses the first line of each slide as the
# label (tools/ew_song_writer/songimport.py); emit label slides once that workflow
# is defined. Keep split_stanzas in sync with lyrics-search/app/lyrics_spacing.py.

_SECTION_HEADER_RE = re.compile(
    r"^(?:"
    r"verse|chorus|bridge|pre-?chorus|tag|intro|outro|instrumental|ending|refrain|hook|interlude"
    r")(?:\s+\d+)?\s*$",
    re.IGNORECASE,
)


def _is_section_header(line: str) -> bool:
    return bool(_SECTION_HEADER_RE.match(line.strip()))


def split_stanzas(text: str) -> List[List[str]]:
    """
    Split into lyric stanzas. Boundaries: blank lines or section labels.
    Labels are not included in the returned lines.
    """
    stanzas: List[List[str]] = []
    current: List[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            stanzas.append(current)
            current = []

    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if _is_section_header(stripped):
            flush()
            continue
        current.append(line.rstrip())

    flush()
    return stanzas


def pack_units(units: List[List[str]], max_lines: int) -> List[str]:
    """Pack units (1-2 lines each) into slides of <= max_lines, never splitting a unit."""
    slides: List[str] = []
    current: List[str] = []
    count = 0
    for unit in units:
        size = len(unit)
        if count > 0 and count + size > max_lines:
            slides.append("\n".join(current))
            current = []
            count = 0
        current.extend(unit)
        count += size
    if current:
        slides.append("\n".join(current))
    return slides
