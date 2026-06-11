from __future__ import annotations

import re

LINES_PER_SLIDE_BLOCK = 4


def normalize_slide_spacing(lyrics: str, lines_per_block: int = LINES_PER_SLIDE_BLOCK) -> str:
    """Ensure at least one blank line after every N non-empty lyric lines."""
    paragraphs = re.split(r"\n\s*\n", lyrics.replace("\r\n", "\n").strip())
    normalized: list[str] = []

    for paragraph in paragraphs:
        lines = [line.rstrip() for line in paragraph.split("\n") if line.strip()]
        if not lines:
            continue
        blocks: list[str] = []
        for start in range(0, len(lines), lines_per_block):
            blocks.append("\n".join(lines[start : start + lines_per_block]))
        normalized.append("\n\n".join(blocks))

    return "\n\n".join(normalized)
