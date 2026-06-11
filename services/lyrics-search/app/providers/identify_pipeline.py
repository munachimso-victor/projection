from __future__ import annotations

from app.config import Settings
from app.models import SearchLink
from app.providers import duckduckgo_identify


def identify_from_snippet(
    snippet: str,
    max_results: int,
    settings: Settings,
) -> list[SearchLink]:
    return duckduckgo_identify.search_links_from_snippet(
        snippet,
        max_results,
        settings,
    )
