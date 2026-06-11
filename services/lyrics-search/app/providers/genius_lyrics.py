from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import lyricsgenius
from bs4 import BeautifulSoup

from app.config import Settings


@dataclass(frozen=True)
class GeniusLyricsResult:
    title: str
    artist: str
    lyrics_plain: str


@dataclass(frozen=True)
class GeniusLyricsFailure:
    error: str


_OG_TITLE_LEGACY_RE = re.compile(
    r"^(.+?)\s+Lyrics\s+by\s+(.+?)\s*\|\s*Genius\s*$",
    re.IGNORECASE,
)


def _client(settings: Settings) -> lyricsgenius.Genius:
    return lyricsgenius.Genius(
        settings.genius_access_token,
        remove_section_headers=True,
        timeout=15,
    )


def _genius_path(url: str) -> str:
    return url.strip().replace("https://genius.com/", "").replace("http://genius.com/", "")


def _normalize_meta_text(text: str) -> str:
    return text.replace("\xa0", " ").strip()


def _split_artist_title(raw: str) -> tuple[str, str]:
    text = _normalize_meta_text(raw)
    for sep in (" – ", " - ", " — "):
        if sep in text:
            artist, title = text.split(sep, 1)
            return artist.strip(), title.strip()
    legacy = _OG_TITLE_LEGACY_RE.match(text)
    if legacy:
        return legacy.group(2).strip(), legacy.group(1).strip()
    return "", text


def _metadata_from_page(genius: lyricsgenius.Genius, url: str) -> tuple[str, str]:
    try:
        html = genius._make_request(_genius_path(url), web=True)["html"]
    except Exception:
        return "", ""

    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return _split_artist_title(meta["content"])

    h1 = soup.find("h1")
    if h1:
        return "", _normalize_meta_text(h1.get_text())

    return "", ""


def fetch_lyrics_by_url(url: str, settings: Settings) -> GeniusLyricsResult | GeniusLyricsFailure:
    if not settings.genius_configured:
        return GeniusLyricsFailure(error="GENIUS_ACCESS_TOKEN is not set")

    parsed = urlparse(url.strip())
    if "genius.com" not in (parsed.netloc or "").lower():
        return GeniusLyricsFailure(error="not_a_genius_url")

    genius = _client(settings)

    try:
        lyrics = genius.lyrics(song_url=url.strip())
    except Exception as exc:
        return GeniusLyricsFailure(error=str(exc))

    if not lyrics or len(lyrics.strip()) < settings.min_lyrics_chars:
        return GeniusLyricsFailure(error="lyrics_too_short_or_missing")

    artist, title = _metadata_from_page(genius, url)

    return GeniusLyricsResult(
        title=title or "Unknown Title",
        artist=artist or "Unknown Artist",
        lyrics_plain=lyrics.strip(),
    )
