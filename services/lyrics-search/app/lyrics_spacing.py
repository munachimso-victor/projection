from __future__ import annotations

import re

LINES_PER_SLIDE_BLOCK = 4

# Section labels (Verse, Chorus, …) split stanzas when blank lines are missing, then
# are removed from output. EasyWorship uses the first line of each slide as the
# label (tools/ew_song_writer/songimport.py); emit label slides once that workflow
# is defined. Keep split_stanzas in sync with lyrics-translate/app/slides.py.

_SECTION_HEADER_RE = re.compile(
    r"^(?:"
    r"verse|chorus|bridge|pre-?chorus|tag|intro|outro|instrumental|ending|refrain|hook|interlude"
    r")(?:\s+\d+)?\s*$",
    re.IGNORECASE,
)


def _is_section_header(line: str) -> bool:
    return bool(_SECTION_HEADER_RE.match(line.strip()))


def split_stanzas(text: str) -> list[list[str]]:
    """
    Split into lyric stanzas. Boundaries: blank lines or section labels.
    Labels are not included in the returned lines.
    """
    stanzas: list[list[str]] = []
    current: list[str] = []

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


def normalize_slide_spacing(lyrics: str, lines_per_block: int = LINES_PER_SLIDE_BLOCK) -> str:
    """Pack each stanza into slides of up to N lines; blank line between slides."""
    slides: list[str] = []
    for stanza in split_stanzas(lyrics):
        for start in range(0, len(stanza), lines_per_block):
            slides.append("\n".join(stanza[start : start + lines_per_block]))
    return "\n\n".join(slides)
