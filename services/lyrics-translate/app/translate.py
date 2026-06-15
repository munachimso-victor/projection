from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.config import Settings
from app.providers.gemini_translate import (
    LineTranslation,
    TranslateFailure,
    translate_lines,
)
from app.slides import pack_units, split_stanzas

# Stanzas come from split_stanzas (blank lines or section labels; labels stripped).
# See slides.py for the planned EasyWorship label-slide workflow.


@dataclass(frozen=True)
class TranslateResult:
    lyrics_translated: str
    lines_translated: int


def _unit_for(line: str, lt: LineTranslation) -> List[str]:
    """A foreign line + its (translation) is one inseparable 2-line unit."""
    if lt.needs_translation and lt.translation:
        return [line, f"({lt.translation})"]
    return [line]


def translate_lyrics(
    lyrics_plain: str,
    settings: Settings,
    target_lang: str,
) -> TranslateResult | TranslateFailure:
    stanzas = split_stanzas(lyrics_plain)
    content_lines = [line for stanza in stanzas for line in stanza]
    if not content_lines:
        return TranslateResult(lyrics_translated="", lines_translated=0)

    translations = translate_lines(content_lines, settings, target_lang)
    if isinstance(translations, TranslateFailure):
        return translations

    max_lines = max(2, settings.translated_max_lines)
    slides: List[str] = []
    translated_count = 0
    idx = 0

    for stanza in stanzas:
        units: List[List[str]] = []
        for line in stanza:
            lt = translations[idx]
            idx += 1
            unit = _unit_for(line, lt)
            if len(unit) == 2:
                translated_count += 1
            units.append(unit)

        slides.extend(pack_units(units, max_lines))

    return TranslateResult(
        lyrics_translated="\n\n".join(slides),
        lines_translated=translated_count,
    )
