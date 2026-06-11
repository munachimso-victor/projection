from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import HealthResponse, TranslateRequest, TranslateResponse
from app.providers.gemini_translate import TranslateFailure
from app.translate import translate_lyrics

app = FastAPI(
    title="Lyrics Translate",
    description="v1: translate non-English lyric lines (Gemini), insert (translation) under each, projection-safe slides.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(
        ok=True,
        gemini_configured=settings.gemini_configured,
        model=settings.gemini_model,
    )


@app.post("/v1/translate", response_model=TranslateResponse)
def translate(body: TranslateRequest) -> TranslateResponse:
    target_lang = (body.target_lang or settings.target_lang).strip() or "en"
    result = translate_lyrics(body.lyrics_plain, settings, target_lang)
    if isinstance(result, TranslateFailure):
        raise HTTPException(status_code=502, detail=f"translate failed: {result.error}")
    return TranslateResponse(
        lyrics_translated=result.lyrics_translated,
        lines_translated=result.lines_translated,
        target_lang=target_lang,
    )
