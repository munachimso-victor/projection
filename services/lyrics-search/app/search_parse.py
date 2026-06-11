from __future__ import annotations

from urllib.parse import urlparse

LYRIC_HOSTS = frozenset(
    {
        "azlyrics.com",
        "genius.com",
        "songfacts.com",
        "letras.com",
        "hymnal.net",
        "learnreligions.com",
        "naijagospel.org",
        "zionlyrics.com",
        "notjustok.com",
        "gospelrella.com",
        "musixmatch.com",
        "lyrics.com",
        "lyricsify.com",
        "tooxclusive.com",
        "gospellyricsng.com",
        "celebnob.com",
        "christsquare.com",
        "gospelloop.com",
        "sifalyrics.com",
        "ceenaija.com",
    }
)

_SKIP_HOSTS = frozenset(
    {
        "wikipedia.org",
        "medium.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "pinterest.com",
        "tiktok.com",
        "gsong.ai",
        "oldielyrics.com",
        "instagram.com",
    }
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def is_lyric_host(url: str) -> bool:
    host = _host(url)
    if "azlyrics.com" in host or host == "genius.com":
        return True
    return host in LYRIC_HOSTS


def should_skip_url(url: str) -> bool:
    host = _host(url)
    if not host:
        return True
    if host in _SKIP_HOSTS:
        return True
    if "facebook.com" in host or "tiktok.com" in host:
        return True
    if "/tag/" in urlparse(url).path.lower():
        return True
    return False


def host_sort_key(url: str, search_rank: int) -> tuple[int, int]:
    """
    Lower sort key = earlier in results. AZLyrics and Genius first, then other
    lyric hosts, preserving DuckDuckGo order within each tier.
    """
    host = _host(url)
    if "azlyrics.com" in host:
        tier = 0
    elif host == "genius.com":
        tier = 1
    elif host in LYRIC_HOSTS:
        tier = 2
    else:
        tier = 3
    return tier, search_rank
