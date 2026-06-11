# Lyrics Translate

Standalone microservice that adds an English translation line under each non-English lyric line, then re-blocks into projection-safe slides.

- **Engine:** Gemini (reuses the same `GEMINI_API_KEY` as `lyrics-search`; free tier is fine).
- **Port:** 8100 (separate from lyrics-search on 8000).
- **Contextual:** the whole song is sent for context; only lines with non-English words get a translation.

## How it works

1. Split lyrics into stanza segments (blank-line separated).
2. Ask Gemini, per line: is it non-English? if so, give a natural translation.
3. Rebuild on our side — each original line is kept exactly; a foreign line + its `(translation)` is one inseparable 2-line unit.
4. Pack units into slides of at most `TRANSLATED_MAX_LINES` (default 6), never splitting a unit, so a translation is never orphaned onto the next slide.

English lines and section labels (Chorus, Verse, ...) are left unchanged.

## Run

```bash
cd services/lyrics-translate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GEMINI_API_KEY
set -a && source .env && set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

## API

`POST /v1/translate`

```json
{ "lyrics_plain": "Olúwa mi\nYou are holy", "target_lang": "en" }
```

Response:

```json
{ "lyrics_translated": "Olúwa mi\n(My Lord)\nYou are holy", "lines_translated": 1, "target_lang": "en" }
```

`GET /healthz` → `{ "ok": true, "gemini_configured": true, "model": "gemini-2.0-flash" }`

## Config (env)

| Var | Default | Notes |
|-----|---------|-------|
| `GEMINI_API_KEY` | — | required |
| `GEMINI_MODEL` | `gemini-2.0-flash` | |
| `TRANSLATE_TARGET_LANG` | `en` | |
| `TRANSLATED_MAX_LINES` | `6` | max lines per bilingual slide |
| `ALLOWED_ORIGINS` | localhost:3001 / 127.0.0.1:3001 | CORS; add your production UI origin |
