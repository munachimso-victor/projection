from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException

from app.config import Settings
from app.lyrics_spacing import normalize_slide_spacing
from app.models import FetchLyricsRequest, FetchLyricsResponse, Provenance
from app.providers import gemini_url_extract, genius_lyrics


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _is_genius(url: str) -> bool:
    return _host(url) == "genius.com"


def _fetch_response(
    title: str,
    author: str,
    lyrics_plain: str,
    provenance: Provenance,
) -> FetchLyricsResponse:
    return FetchLyricsResponse(
        title=title,
        author=author,
        lyrics_plain=normalize_slide_spacing(lyrics_plain),
        provenance=provenance,
    )


def _fetch_failed(
    url: str,
    source: str,
    error: str,
    *,
    primary_source: str | None = None,
    primary_error: str | None = None,
) -> None:
    detail: dict[str, str] = {
        "message": f"{source} fetch failed",
        "url": url,
        "source": source,
        "error": error,
    }
    if primary_source and primary_error:
        detail["primary_source"] = primary_source
        detail["primary_error"] = primary_error
    raise HTTPException(status_code=502, detail=detail)


def _try_gemini_url_extract(
    url: str,
    settings: Settings,
    *,
    primary_source: str,
    primary_error: str,
) -> FetchLyricsResponse:
    if not settings.gemini_configured:
        raise HTTPException(
            status_code=502,
            detail={
                "message": f"{primary_source} failed and GEMINI_API_KEY is not configured for fallback",
                "url": url,
                "primary_source": primary_source,
                "primary_error": primary_error,
            },
        )

    result = gemini_url_extract.fetch_lyrics_from_url(url, settings)
    if isinstance(result, gemini_url_extract.UrlExtractResult):
        return _fetch_response(
            result.title,
            result.artist,
            result.lyrics_plain,
            Provenance(
                source="gemini_url_extract",
                fallback_used=True,
                primary_error=primary_error,
            ),
        )

    _fetch_failed(
        url,
        "gemini_url_extract",
        result.error,
        primary_source=primary_source,
        primary_error=primary_error,
    )


def fetch_lyrics(body: FetchLyricsRequest, settings: Settings) -> FetchLyricsResponse:
    return _fetch_by_url(body.url.strip(), settings)


def _fetch_by_url(url: str, settings: Settings) -> FetchLyricsResponse:
    if _is_genius(url):
        result = genius_lyrics.fetch_lyrics_by_url(url, settings)
        if isinstance(result, genius_lyrics.GeniusLyricsResult):
            return _fetch_response(
                result.title,
                result.artist,
                result.lyrics_plain,
                Provenance(source="genius_lyricsgenius", fallback_used=False),
            )
        return _try_gemini_url_extract(
            url,
            settings,
            primary_source="genius_lyricsgenius",
            primary_error=result.error,
        )

    result = gemini_url_extract.fetch_lyrics_from_url(url, settings)
    if isinstance(result, gemini_url_extract.UrlExtractResult):
        return _fetch_response(
            result.title,
            result.artist,
            result.lyrics_plain,
            Provenance(source="gemini_url_extract", fallback_used=False),
        )

    _fetch_failed(url, "gemini_url_extract", result.error)
