# Lyrics Search Service (v1)

HTTP API for the projection tool:

1. **Identify** — lyric snippet → links from lyric websites (AZLyrics/Genius first)
2. **Fetch lyrics** — URL from identify → azapi (AZ), lyricsgenius (Genius), or Gemini page extract (other lyric sites)

EasyWorship import stays in `tools/ew_song_writer/songimport.py` on Windows.

**Operator UI:** `tools/lyrics_operator/` — browser or Windows desktop app for identify + fetch + local EW import (see its README).

**Local testing:** see [INSTRUCTIONS.md](INSTRUCTIONS.md) for full copy-paste commands.

## Setup

```bash
cd services/lyrics-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
export $(grep -v '^#' .env | xargs)
```

## Run

```bash
cd services/lyrics-search
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Service up; shows if Gemini key is set |
| `POST` | `/v1/identify` | Snippet → search links |
| `POST` | `/v1/lyrics/fetch` | Lyric page URL → full lyrics |

### Identify

Returns links from lyric websites only (`search_parse.LYRIC_HOSTS`). Sorted with AZLyrics and Genius first. Each item: `id`, `rank`, `link`, `title`, `snippet` (full DDG excerpt, not cut).

```bash
curl -s -X POST http://localhost:8000/v1/identify \
  -H "Content-Type: application/json" \
  -d '{"lyrics_snippet": "amazing grace how sweet the sound that saved a wretch like me"}' | jq
```

### Fetch lyrics

```bash
curl -s -X POST http://localhost:8000/v1/lyrics/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.azlyrics.com/lyrics/josiahqueen/iambarabbas.html"}' | jq
```

On failure, the API returns **502** with `source` and `error`. AZ and Genius may fall back to `gemini_url_extract` on the same URL.

## Project layout

```text
services/lyrics-search/
  app/
    main.py              # FastAPI routes
    config.py            # env settings
    models.py            # request/response schemas
    search_parse.py        # lyric host allowlist + sort order
    providers/
      identify_pipeline.py
      duckduckgo_identify.py
      fetch_pipeline.py
      azlyrics.py
      genius_lyrics.py
      gemini_url_extract.py
  requirements.txt
  .env.example
```

## Notes

- `GENIUS_ACCESS_TOKEN` — [Genius API client](https://genius.com/api-clients) for Genius links on fetch.
- `GEMINI_API_KEY` — other lyric-site fetch (URL extract) and fallback when AZ/Genius fail.
- azapi scrapes AZLyrics; use delays and expect occasional failures.
- Always preview lyrics in the client before calling `songimport.py`.
