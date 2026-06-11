from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    lyrics_plain: str = Field(..., min_length=1, max_length=20000)
    target_lang: str = Field(default="en", min_length=2, max_length=5)


class TranslateResponse(BaseModel):
    lyrics_translated: str
    lines_translated: int = Field(
        description="Number of source lines that received a translation line."
    )
    target_lang: str


class HealthResponse(BaseModel):
    ok: bool
    gemini_configured: bool
    model: str
