# Lyrics Operator

Paste a snippet -> identify songs -> fetch lyrics -> copy / download / import to EasyWorship.

## Components

| Component | Location | Role |
|-----------|----------|------|
| **Backend lyrics fetcher** | `services/lyrics-search` | API: identify + fetch (port 8000) |
| **Backend translator** | `services/lyrics-translate` | API: translate non-English lines (port 8100) |
| **UI** | `tools/lyrics_operator/ui` | Static web app (`index.html`, `app.js`, `app.css`) |
| **Desktop app** | `tools/lyrics_operator/desktop` | Windows window + local EasyWorship import (port 3000) |

```
tools/lyrics_operator/
  ui/        index.html, app.js, app.css        # served on :3001 / hosted on CDN
  desktop/   desktop.py, import_server.py, ...   # Windows import + window + build
```

The UI talks to the **backend** (`:8000`, set in the UI's API field) and, on Windows, to the **desktop import server** (`:3000`).

---

## One-time setup

Each backend has its own venv. If `services/lyrics-translate/.venv` doesn't exist yet:

```bash
cd ~/projection/services/lyrics-translate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GEMINI_API_KEY (same key as lyrics-search is fine)
```

## Run locally (4 processes)

**Terminal 1 — Lyrics API (identify + fetch), port 8000 (WSL):**

```bash
cd ~/projection/services/lyrics-search
source .venv/bin/activate && set -a && source .env && set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Translate API, port 8100 (WSL):**

```bash
cd ~/projection/services/lyrics-translate
source .venv/bin/activate && set -a && source .env && set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

> `uvicorn` does NOT auto-load `.env`; the `set -a && source .env && set +a` step is required or Gemini calls fail with `API_KEY_INVALID`.

**Terminal 3 — UI, port 3001 (WSL):**

```bash
cd ~/projection/tools/lyrics_operator/desktop
python3 serve_ui.py
```

Open **http://127.0.0.1:3001/**. In the header, **API** = `http://localhost:8000`, **Translate** = `http://localhost:8100` (both badges should read `ok`).

> Use `python3`, not `python`: in WSL, `python` may resolve to a Windows pyenv shim and fail with "cannot execute: required file not found".

**Terminal 4 — Desktop app + import, port 3000 (Windows):** see below. Without it, copy/download/translate work but Import is hidden.

The **Translate** button inserts an English line under each non-English line and re-blocks into projection-safe slides (max 6 lines). Toggling shows original/translation; whatever is shown feeds Copy/Download/Import.

---

## Desktop app (Windows)

`desktop.py` opens the UI in a window and runs the import server on `:3000`.

It defaults to the local UI at `http://127.0.0.1:3001/`, so for local use you don't set anything. Only set `LYRICS_OPERATOR_UI_URL` to point at a different UI (e.g. your cloud URL in production).

**Run from source** (`run-desktop.ps1`, handles `\\wsl$\` paths):

PowerShell (prompt shows `PS C:\...>`):

```powershell
& "\\wsl$\Ubuntu\home\mvn27adm\projection\tools\lyrics_operator\desktop\run-desktop.ps1"
```

CMD (prompt shows `C:\...>`) — `&` is PowerShell-only, so call it via `powershell`:

```cmd
powershell -ExecutionPolicy Bypass -File "\\wsl$\Ubuntu\home\mvn27adm\projection\tools\lyrics_operator\desktop\run-desktop.ps1"
```

**Build the exe** (syncs to `%USERPROFILE%\projection`, builds there):

```powershell
& "\\wsl$\Ubuntu\home\mvn27adm\projection\tools\lyrics_operator\desktop\build-desktop.ps1"
```

Output: `%USERPROFILE%\projection\tools\lyrics_operator\desktop\dist\LyricsOperator\LyricsOperator.exe`

**Run the exe** (with UI on :3001 and API on :8000):

```powershell
& "$env:USERPROFILE\projection\tools\lyrics_operator\desktop\dist\LyricsOperator\LyricsOperator.exe"
```

Use Python **3.10+** (`pyenv install 3.12.0; pyenv global 3.12.0`).

---

## Production

- **UI** -> your CDN / static host.
- **Backend** -> cloud; add the UI origin to `allow_origins` in `services/lyrics-search/app/main.py`.
- **Desktop** -> each Windows PC, with `LYRICS_OPERATOR_UI_URL=https://your-site/.../index.html`.

---

## After import

In EasyWorship: **Refresh**, then **Profiles > Utilities > Rebuild Search Keys** for lyric search.

---

## Troubleshooting

- **`Address already in use` (port 8000/8100/3001):** an old server is still running.
  `fuser -k 8100/tcp` (swap the port), or `pkill -f "uvicorn app.main:app"`, then restart.
- **`python: cannot execute: required file not found` (WSL):** `python` resolved to a Windows pyenv shim. Use `python3`, or set a Linux pyenv (`pyenv install 3.12.0 && pyenv global 3.12.0`). Inside an activated `.venv`, plain `python` is fine.
- **`translate failed: ... API_KEY_INVALID`:** the translate terminal didn't load `.env`, or the key is wrong/quoted. Run `set -a && source .env && set +a` before `uvicorn`; key line must be `GEMINI_API_KEY=AIza...` with no quotes. The same key as lyrics-search works.
- **`& was unexpected at this time` (Windows):** you're in CMD, not PowerShell. Use the `powershell -File ...` form above, or run `powershell` first.
- **UI shows a directory listing instead of the app:** an old `serve_ui.py` is serving the wrong folder. Restart it from `tools/lyrics_operator/desktop` (serves `../ui`).
- **Import button missing:** expected unless the Windows desktop/exe is running on `:3000`.
