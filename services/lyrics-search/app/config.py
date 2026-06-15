from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    genius_access_token: str
    min_lyrics_chars: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            genius_access_token=os.environ.get("GENIUS_ACCESS_TOKEN", "").strip(),
            min_lyrics_chars=int(os.environ.get("MIN_LYRICS_CHARS", "50")),
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def genius_configured(self) -> bool:
        return bool(self.genius_access_token)


settings = Settings.from_env()
