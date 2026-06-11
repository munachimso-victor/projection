from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    target_lang: str
    translated_max_lines: int
    allowed_origins: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip(),
            target_lang=os.environ.get("TRANSLATE_TARGET_LANG", "en").strip() or "en",
            translated_max_lines=int(os.environ.get("TRANSLATED_MAX_LINES", "6")),
            allowed_origins=_csv_env(
                "ALLOWED_ORIGINS",
                [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:3001",
                    "http://127.0.0.1:3001",
                ],
            ),
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings.from_env()
