from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from google import genai
from google.genai import types

from app.config import Settings

_SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        required=["index", "needs_translation", "translation"],
        properties={
            "index": types.Schema(type=types.Type.INTEGER),
            "needs_translation": types.Schema(type=types.Type.BOOLEAN),
            "translation": types.Schema(type=types.Type.STRING),
        },
    ),
)

_SYSTEM = """You translate worship song lyrics for a church projection tool.

You receive a JSON array of lines, each with an "index" and "text".
For every line, return an object with the same "index" and:
- needs_translation: true only if the line contains words that are NOT in {target} .
- translation: a natural {target}-language translation of the whole line (concise, one line).

Rules:
- If the line is already entirely in {target}, set needs_translation=false and translation="".
- Section labels (Chorus, Verse, Bridge, Intro, Outro, Pre-Chorus, Tag, Refrain, with or without numbers) are NOT translated: needs_translation=false, translation="".
- If a line mixes {target} and another language, translate the WHOLE line into {target}.
- Preserve worship/biblical meaning; favor natural phrasing over word-for-word.
- Do not add quotes, parentheses, or labels around the translation; return plain text only.
- Return exactly one object per input line, with matching index. Do not add or drop lines.
"""


@dataclass(frozen=True)
class LineTranslation:
    needs_translation: bool
    translation: str


@dataclass(frozen=True)
class TranslateFailure:
    error: str


def translate_lines(
    lines: List[str],
    settings: Settings,
    target_lang: str,
) -> List[LineTranslation] | TranslateFailure:
    """Per-line detect + translate. Returns one LineTranslation per input line."""
    if not settings.gemini_configured:
        return TranslateFailure(error="GEMINI_API_KEY is not set")
    if not lines:
        return []

    payload = [{"index": i, "text": text} for i, text in enumerate(lines)]
    prompt = json.dumps(payload, ensure_ascii=False)
    system = _SYSTEM.replace("{target}", target_lang)

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_SCHEMA,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return TranslateFailure(error=f"gemini_translate_failed: {exc}")

    text = (response.text or "").strip()
    if not text:
        return TranslateFailure(error="empty_gemini_response")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return TranslateFailure(error="invalid_gemini_json")

    if not isinstance(data, list):
        return TranslateFailure(error="gemini_response_not_a_list")

    # Map by index defensively; default to no-translation for any missing line.
    by_index: dict[int, LineTranslation] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        needs = bool(item.get("needs_translation", False))
        translation = str(item.get("translation", "") or "").strip()
        if not translation:
            needs = False
        by_index[idx] = LineTranslation(needs_translation=needs, translation=translation)

    return [by_index.get(i, LineTranslation(False, "")) for i in range(len(lines))]
