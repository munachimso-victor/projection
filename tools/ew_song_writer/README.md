# EasyWorship song writer

Python tool to import **one** lyrics `.txt` file into EasyWorship `Songs.db` and `SongWords.db`.

Based on [ew-song-importer `songimport.py`](https://github.com/Jacqueb-1337/ew-song-importer/blob/main/songimport.py). Run on **Windows**.

## Requirements

- Python 3.8+
- No third-party packages (stdlib only)

## Database location

Hardcoded in `songimport.py` as `EW_DATA_DIR`:

```text
C:\Users\Public\Documents\Softouch\Easyworship\Default\profile_12-18-2023\v6.1\Databases\Data
```

Every run prints this path and checks both `Songs.db` and `SongWords.db` exist. If your profile moves, edit `EW_DATA_DIR` at the top of `songimport.py` (the script prints a reminder).

## Lyrics file format

Use UTF-8 `.txt` files:

- **Blank line** = new slide
- **First line** of each slide = slide label (e.g. `Verse 1`, `Chorus`)
- Filename (without `.txt`) is the **song title** unless you use `--title`
- If that title **already exists** in the library, a timestamp is appended: `Base Title 2026-05-25 14:30` (local date and hour:minute)

Example `Amazing Grace.txt`:

```text
Verse 1
Amazing grace how sweet the sound
That saved a wretch like me

Verse 2
'Twas grace that taught my heart to fear
```

## Title and author

| Field | Default | Override |
|-------|---------|----------|
| **Title** | `.txt` filename or `--title` | If duplicate exists → `{title} YYYY-MM-DD HH:MM` |
| **Author** | `Unknown` | `--author "Chris Tomlin"` |
| **Copyright** | `Public Domain` | (not exposed in CLI yet) |

## CLI usage

After import, use **Refresh** in EasyWorship to load new songs. For **search by lyrics** (not just title), run **Profiles > Utilities > Rebuild Search Keys** once, then Refresh again.

**Import** (full path to one `.txt` file):

```powershell
python songimport.py "C:\Users\mvn27adm\Desktop\ew_song_writer\test_lyrics\EW-Import-Test-Song.txt" -v
```

With title and author:

```powershell
python songimport.py ".\test_lyrics\My Song.txt" --title "How Great Is Our God" --author "Chris Tomlin" -v
```

**Row counts only** (no lyric file):

```powershell
python songimport.py --status
```

## Import safety

Each import:

1. Prints and verifies `EW_DATA_DIR`
2. Verifies the `.txt` file exists
3. Backs up both databases
4. Inserts one new song (+1 row in `song` and `word`)
5. Deletes backup on success, or restores DBs and keeps backup on failure

## Programmatic API

```python
from songimport import (
    SongMetadata,
    create_backup,
    get_db_paths,
    write_song_from_text,
)

songs_db, songwords_db = get_db_paths()  # uses EW_DATA_DIR in songimport.py
create_backup(songs_db, songwords_db)

write_song_from_text(
    SongMetadata(title="How Great Is Our God", author="Chris Tomlin"),
    "Verse 1\nLine one\n\nChorus\nLine one",
    songs_db,
    songwords_db,
)
```

## WSL note

Edit in WSL; run on Windows against the live `EW_DATA_DIR`. Recopy to Desktop or use `\\wsl$\...` for the script.

## Schema (from ew-song-importer)

| Database     | Table  | Key columns                                      |
|-------------|--------|--------------------------------------------------|
| Songs.db    | `song` | `song_item_uid`, `title`, `author`, `copyright` |
| SongWords.db| `word` | `song_id`, `words` (RTF text)                   |

## Safety

Not an official EasyWorship tool — test on a copied DB first if unsure.
