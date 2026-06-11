# Lyrics Search — local test instructions

Step-by-step commands to run and test the v1 API (`identify` + `lyrics/fetch`) on WSL or Linux.

**Prerequisites:** Python 3.10+, internet access. Optional: [Gemini API key](https://aistudio.google.com/apikey) for lyrics fetch fallback only.

---

## Terminal 1 — start the service

First-time setup (venv + dependencies):

```bash
cd /home/mvn27adm/projection/services/lyrics-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your API key (optional — only needed for `/v1/lyrics/fetch` fallback) and start Uvicorn:

```bash
cd /home/mvn27adm/projection/services/lyrics-search
source .venv/bin/activate
export GEMINI_API_KEY="paste_your_key_here"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Leave this terminal open. You should see:

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Stop the server with **Ctrl+C**.

---

## Optional — use a `.env` file instead of `export`

```bash
cd /home/mvn27adm/projection/services/lyrics-search
cp .env.example .env
```

Edit `.env` and set:

```text
GEMINI_API_KEY=your_key_here
```

Then:

```bash
cd /home/mvn27adm/projection/services/lyrics-search
source .venv/bin/activate
set -a && source .env && set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Terminal 2 — test endpoints

Open a **second** terminal while Terminal 1 is still running.

### Health check

```bash
curl -s http://localhost:8000/healthz | python3 -m json.tool
```

Expected:

```json
{
    "ok": true,
    "gemini_configured": true
}
```

If `gemini_configured` is `false`, set `GEMINI_API_KEY` in Terminal 1 and restart Uvicorn.

Returns lyric-site links only. Open a `link`, then fetch with that URL.

```bash
curl -s -X POST http://localhost:8000/v1/identify \
  -H "Content-Type: application/json" \
  -d '{"lyrics_snippet": "no throne without the cross no me without you", "max_results": 10}' \
  | python3 -m json.tool
```

Each item: `id`, `rank`, `link`, `title`, `snippet` (snippet is the full search excerpt, not trimmed).

### Fetch full lyrics (after you pick a link)

Pass the `link` from identify as `url` (only field required).

**AZLyrics link:**

```bash
curl -s -X POST http://localhost:8000/v1/lyrics/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.azlyrics.com/lyrics/josiahqueen/iambarabbas.html"}' \
  | python3 -m json.tool
```

**Genius link** (requires `GENIUS_ACCESS_TOKEN` in `.env`):

```bash
curl -s -X POST http://localhost:8000/v1/lyrics/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://genius.com/Josiah-queen-i-am-barabbas-oasis-coffee-sessions-lyrics"}' \
  | python3 -m json.tool
```

**Other lyric site** (requires `GEMINI_API_KEY` — fetches page HTML, Gemini extracts lyrics):

```bash
curl -s -X POST http://localhost:8000/v1/lyrics/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://zionlyrics.com/song/josiah-queen-i-am-barabbas-lyrics"}' \
  | python3 -m json.tool
```

Check `provenance.source`:

- `azlyrics` — AZLyrics URL
- `genius_lyricsgenius` — Genius URL
- `gemini_url_extract` — other lyric sites (Gemini extracts from page HTML)

On failure you get **502** with `source` and `error`. AZ and Genius links may fall back to `gemini_url_extract` on the same URL (`fallback_used: true`, `primary_error` set); if both fail, the response includes `primary_source`, `primary_error`, and the extract error.

---

## Browser — interactive docs

With Uvicorn running, open:

http://localhost:8000/docs

Use **POST /v1/identify** and **POST /v1/lyrics/fetch** with **Try it out**.

---

## Full v1 pipeline (manual, includes EasyWorship)

After fetch returns `lyrics_plain`:

1. Save text to a `.txt` file (EW format: blank line between slides).
2. Copy to Windows if you edited in WSL.
3. Run `songimport.py` — see `tools/ew_song_writer/README.md`.
4. Refresh EasyWorship.

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Empty identify results | Check internet; try a longer snippet |
| `502` on identify | Transient search/azapi failure — retry |
| `502` on fetch | AZ failed; set `GEMINI_API_KEY` for lyrics fallback |
| Connection refused | Uvicorn not running on port 8000 |
| azapi slow / fails | Normal occasionally; lyrics fallback uses Gemini if key is set |

---

## Related paths

| Path | Purpose |
|------|---------|
| `services/lyrics-search/app/main.py` | FastAPI routes |
| `services/lyrics-search/README.md` | Service overview |
| `tools/ew_song_writer/songimport.py` | Import into EasyWorship (Windows) |
