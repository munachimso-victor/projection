from __future__ import annotations

import hashlib

from ddgs import DDGS

from app.config import Settings
from app.models import SearchLink
from app.search_parse import host_sort_key, is_lyric_host, should_skip_url


def _search_query(snippet: str) -> str:
    cleaned = " ".join(snippet.split())
    return f"{cleaned} lyrics song"


def _link_id(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    return f"lnk:{digest}"


def search_links_from_snippet(
    snippet: str,
    max_results: int,
    settings: Settings,
) -> list[SearchLink]:
    del settings
    snippet_clean = snippet.strip()
    if not snippet_clean:
        return []

    query = _search_query(snippet_clean)
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=max(max_results * 3, 20)))
    except Exception:
        return []

    collected: list[tuple[int, str, str, str]] = []
    seen_urls: set[str] = set()

    for search_rank, hit in enumerate(hits):
        url = (hit.get("href") or "").strip()
        if not url or url in seen_urls:
            continue
        if should_skip_url(url) or not is_lyric_host(url):
            continue
        seen_urls.add(url)
        page_title = (hit.get("title") or "").strip() or url
        body = (hit.get("body") or "").strip()
        collected.append((search_rank, url, page_title, body))

    collected.sort(key=lambda item: host_sort_key(item[1], item[0]))

    links: list[SearchLink] = []
    for rank, (_, url, page_title, body) in enumerate(collected[:max_results]):
        links.append(
            SearchLink(
                id=_link_id(url),
                rank=rank,
                link=url,
                title=page_title,
                snippet=body,
            )
        )

    return links
