from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class IdentifyRequest(BaseModel):
    lyrics_snippet: str = Field(..., min_length=2, max_length=4000)
    max_results: int = Field(default=10, ge=1, le=25)


class SearchLink(BaseModel):
    id: str
    rank: int = Field(ge=0)
    link: str
    title: str = Field(description="Page title from the search result.")
    snippet: str = Field(
        default="",
        description="Search-result excerpt (DuckDuckGo body); not truncated.",
    )


class IdentifyResponse(BaseModel):
    session_id: str
    links: List[SearchLink]


class FetchLyricsRequest(BaseModel):
    url: str = Field(..., min_length=8, description="Lyric page URL from identify.")


class NormalizeLyricsRequest(BaseModel):
    lyrics_plain: str = Field(..., min_length=1, max_length=20000)


class NormalizeLyricsResponse(BaseModel):
    lyrics_plain: str


class Provenance(BaseModel):
    source: str
    fallback_used: bool = False
    primary_error: Optional[str] = Field(
        default=None,
        description="Error from genius when fallback_used is true.",
    )


class FetchLyricsResponse(BaseModel):
    title: str
    author: str
    lyrics_plain: str
    provenance: Provenance


class HealthResponse(BaseModel):
    ok: bool
    gemini_configured: bool
    genius_configured: bool
