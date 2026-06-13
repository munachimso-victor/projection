from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

from app.config import Settings

_EXTRACT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["title", "artist", "lyrics_plain"],
    properties={
        "title": types.Schema(type=types.Type.STRING),
        "artist": types.Schema(type=types.Type.STRING),
        "lyrics_plain": types.Schema(type=types.Type.STRING),
    },
)

_SYSTEM = """You extract worship song lyrics from webpage text for a church projection tool.

Rules:
- Return only the song lyrics as plain text in lyrics_plain.
- Infer title and artist from the page when possible; use "Unknown Title" or "Unknown Artist" only if missing.
- Ignore navigation, ads, comments, chord charts, and unrelated page text.
- If you cannot find lyrics on the page, return empty lyrics_plain.

Formatting (important for projection slides):
- Put each sung line on its own line (do not run many lines together as one paragraph).
- After every 4 lines of lyrics, insert one blank line (an empty line between blocks).
- blocks of lines can be less than 4 lines, but not more than 4 lines.
- Use \\n for line breaks and \\n\\n for blank lines between blocks.
- Do not invent section labels like "Section 1", "Section 2", etc. unless that exact label already appears in the page text.
- Do not renumber or duplicate section headers. If the page has "Chorus" or "Bridge", keep it once as written.
"""

_MAX_PAGE_CHARS = 40_000


@dataclass(frozen=True)
class UrlExtractResult:
    title: str
    artist: str
    lyrics_plain: str


@dataclass(frozen=True)
class UrlExtractFailure:
    error: str

def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# Free reader proxy that fetches the page from its own IPs and returns clean text.
# Used as a fallback when a direct fetch is blocked (e.g. Cloudflare 403 on
# datacenter/cloud IP ranges, which affects Genius, Musixmatch, etc.).
_READER_PROXY = "https://r.jina.ai/"


def _fetch_direct(url: str) -> str:
    with httpx.Client(
        follow_redirects=True,
        timeout=20.0,
        headers=_BROWSER_HEADERS,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
    return _html_to_text(response.text)


def _fetch_via_reader(url: str) -> str:
    # r.jina.ai returns ready-to-use markdown/plain text, so no HTML parsing needed.
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(
            _READER_PROXY + url,
            headers={"User-Agent": _BROWSER_HEADERS["User-Agent"]},
        )
        response.raise_for_status()
    return (response.text or "").strip()


def _fetch_page_text(url: str) -> str:
    try:
        return _fetch_direct(url)
    except Exception as direct_exc:
        try:
            text = _fetch_via_reader(url)
        except Exception as reader_exc:
            raise RuntimeError(
                f"direct_failed: {direct_exc}; reader_failed: {reader_exc}"
            ) from reader_exc
        if not text:
            raise RuntimeError(f"direct_failed: {direct_exc}; reader_empty") from direct_exc
        return text


def fetch_lyrics_from_url(url: str, settings: Settings) -> UrlExtractResult | UrlExtractFailure:
    if not settings.gemini_configured:
        return UrlExtractFailure(error="GEMINI_API_KEY is not set")

    try:
        page_text = _fetch_page_text(url.strip())
    except Exception as exc:
        return UrlExtractFailure(error=f"page_fetch_failed: {exc}")

    if not page_text:
        return UrlExtractFailure(error="empty_page_text")

    if len(page_text) > _MAX_PAGE_CHARS:
        page_text = page_text[:_MAX_PAGE_CHARS] + "\n...[truncated]"

    prompt = f"URL: {url.strip()}\n\nPage text:\n{page_text}"

    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_EXTRACT_SCHEMA,
            ),
        )
    except Exception as exc:
        return UrlExtractFailure(error=f"gemini_extract_failed: {exc}")

    text = (response.text or "").strip()
    if not text:
        return UrlExtractFailure(error="empty_gemini_response")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return UrlExtractFailure(error="invalid_gemini_json")

    lyrics = str(data.get("lyrics_plain", "")).strip()
    if len(lyrics) < settings.min_lyrics_chars:
        return UrlExtractFailure(error="lyrics_too_short")

    return UrlExtractResult(
        title=str(data.get("title", "Unknown Title")).strip(),
        artist=str(data.get("artist", "Unknown Artist")).strip(),
        lyrics_plain=lyrics,
    )
