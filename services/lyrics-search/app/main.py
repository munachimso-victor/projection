from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    FetchLyricsRequest,
    FetchLyricsResponse,
    HealthResponse,
    IdentifyRequest,
    IdentifyResponse,
)
from app.providers import identify_pipeline
from app.providers.fetch_pipeline import fetch_lyrics as fetch_lyrics_pipeline

app = FastAPI(
    title="Lyrics Search",
    description="v1: identify links, fetch by URL (Gemini page extract; Genius optional)",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(
        ok=True,
        gemini_configured=settings.gemini_configured,
        genius_configured=settings.genius_configured,
    )


@app.post("/v1/identify", response_model=IdentifyResponse)
def identify(body: IdentifyRequest) -> IdentifyResponse:
    try:
        links = identify_pipeline.identify_from_snippet(
            body.lyrics_snippet,
            body.max_results,
            settings,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"identify failed: {exc}") from exc

    return IdentifyResponse(
        session_id=str(uuid.uuid4()),
        links=links,
    )


@app.post("/v1/lyrics/fetch", response_model=FetchLyricsResponse)
def fetch_lyrics(body: FetchLyricsRequest) -> FetchLyricsResponse:
    try:
        return fetch_lyrics_pipeline(body, settings)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"fetch failed: {exc}") from exc
