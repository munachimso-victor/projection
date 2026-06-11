from __future__ import annotations

import re
from typing import List

DEFAULT_TRANSLATED_MAX_LINES = 6


def split_segments(text: str) -> List[List[str]]:
    """Split into stanza segments (separated by blank lines); drop blank lines."""
    parts = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    segments: List[List[str]] = []
    for part in parts:
        lines = [line.rstrip() for line in part.split("\n") if line.strip()]
        if lines:
            segments.append(lines)
    return segments


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
