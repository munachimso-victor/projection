from __future__ import annotations

from dataclasses import dataclass

import azapi

from app.config import Settings

_BOT_BLOCK_MARKERS = (
    "unusual activity",
    "not a robot",
    "Type the characters from the picture",
)


@dataclass(frozen=True)
class AzlyricsResult:
    title: str
    artist: str
    lyrics_plain: str


@dataclass(frozen=True)
class AzlyricsFailure:
    error: str


def _api(settings: Settings) -> azapi.AZlyrics:
    return azapi.AZlyrics(
        settings.azlyrics_search_engine or "",
        accuracy=settings.azlyrics_accuracy,
    )


def _is_bot_block(text: str) -> bool:
    lower = text.lower()
    return any(marker.lower() in lower for marker in _BOT_BLOCK_MARKERS)


def _parse_result(
    result: object,
    api: azapi.AZlyrics,
    title: str,
    artist: str,
    settings: Settings,
) -> AzlyricsResult | AzlyricsFailure:
    if result == 0:
        return AzlyricsFailure(error="search_engine_no_match")
    if result == 1:
        return AzlyricsFailure(error="page_fetch_or_metadata_error")
    if result == 2:
        return AzlyricsFailure(error="no_lyrics_on_page")
    if not isinstance(result, str):
        return AzlyricsFailure(error="unexpected_azapi_response")

    lyrics = result.strip()
    if _is_bot_block(lyrics):
        return AzlyricsFailure(error="azlyrics_bot_blocked")
    if len(lyrics) < settings.min_lyrics_chars:
        return AzlyricsFailure(error="lyrics_too_short")

    return AzlyricsResult(
        title=(api.title or title).strip() or "Unknown Title",
        artist=(api.artist or artist).strip() or "Unknown Artist",
        lyrics_plain=lyrics,
    )


def fetch_lyrics_by_url(url: str, settings: Settings) -> AzlyricsResult | AzlyricsFailure:
    api = _api(settings)

    try:
        result = api.getLyrics(url=url.strip(), sleep=2)
    except IndexError:
        return AzlyricsFailure(error="azlyrics_bot_blocked")
    except Exception as exc:
        if "list index out of range" in str(exc).lower():
            return AzlyricsFailure(error="azlyrics_bot_blocked")
        return AzlyricsFailure(error=str(exc))

    return _parse_result(result, api, "", "", settings)
