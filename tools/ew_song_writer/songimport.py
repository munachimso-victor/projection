#!/usr/bin/env python3
"""
EasyWorship Songs.db / SongWords.db writer.

Modeled after ew-song-importer (https://github.com/Jacqueb-1337/ew-song-importer)
with a programmatic API for future use by the Windows client.

Run on Windows. After import, use Refresh in EasyWorship to load new songs.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Church EasyWorship profile — update EW_DATA_DIR if Profiles Manager / instance path changes
EW_DATA_DIR = Path(
    r"C:\Users\Public\Documents\Softouch\Easyworship\Default\profile_12-18-2023\v6.1\Databases\Data"
)

EW_DATA_DIR_CONFIG_NOTE = (
    "If EasyWorship uses a different profile or folder, edit EW_DATA_DIR at the top of songimport.py."
)

DEFAULT_BACKUP_DIR = Path(
    r"C:\Users\Public\Documents\Softouch\Easyworship\backups"
)


@dataclass(frozen=True)
class SongMetadata:
    title: str
    author: str = "Unknown"
    copyright: str = "Public Domain"
    ccli: Optional[str] = None


@dataclass(frozen=True)
class WriteResult:
    song_id: int
    title: str
    created: bool
    lyrics_written: bool
    backups: Dict[str, str]


@dataclass(frozen=True)
class BackupSet:
    songs_path: Path
    songwords_path: Path
    songs_name: str
    songwords_name: str


def log(message: str, *, verbose: bool = False) -> None:
    if verbose:
        print(message)


def register_utf8_ci_collation(connection: sqlite3.Connection) -> None:
    """Register EW's custom UTF-8 case-insensitive collation (required for some queries)."""

    def utf8_ci(x: str, y: str) -> int:
        xl, yl = x.lower(), y.lower()
        return (xl > yl) - (xl < yl)

    connection.create_collation("UTF8_U_CI", utf8_ci)


def get_db_paths(
    data_dir: Path = EW_DATA_DIR, *, verbose: bool = False
) -> Tuple[Path, Path]:
    songs_db = data_dir / "Songs.db"
    songwords_db = data_dir / "SongWords.db"
    log(f"Songs.db: {songs_db}", verbose=verbose)
    log(f"SongWords.db: {songwords_db}", verbose=verbose)
    return songs_db, songwords_db


def verify_databases_or_exit() -> Tuple[Path, Path]:
    """
    Print configured DB paths on every run; exit with error if missing.
    """
    songs_db, songwords_db = get_db_paths()

    print(f"EasyWorship data directory (EW_DATA_DIR):\n  {EW_DATA_DIR}")
    print(f"  Songs.db:     {songs_db}")
    print(f"  SongWords.db: {songwords_db}")
    print(f"Note: {EW_DATA_DIR_CONFIG_NOTE}")

    missing: List[Path] = []
    if not EW_DATA_DIR.is_dir():
        print(f"\nError: data directory not found:\n  {EW_DATA_DIR}")
        raise SystemExit(1)
    if not songs_db.is_file():
        missing.append(songs_db)
    if not songwords_db.is_file():
        missing.append(songwords_db)

    if missing:
        print("\nError: required database file(s) missing:")
        for path in missing:
            print(f"  {path}")
        print(f"\n{EW_DATA_DIR_CONFIG_NOTE}")
        raise SystemExit(1)

    return songs_db, songwords_db


def is_db_locked(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA quick_check;")
        conn.close()
        return False
    except sqlite3.OperationalError:
        return True


def create_backup(
    songs_db_path: Path,
    songwords_db_path: Path,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    *,
    verbose: bool = False,
) -> BackupSet:
    backup_dir.mkdir(parents=True, exist_ok=True)
    log("Creating backups.", verbose=verbose)

    timestamp = int(time.time())
    songs_backup_name = f"{timestamp}Songs.db.bak"
    songwords_backup_name = f"{timestamp}SongWords.db.bak"
    songs_backup_path = backup_dir / songs_backup_name
    songwords_backup_path = backup_dir / songwords_backup_name

    try:
        shutil.copy2(songs_db_path, songs_backup_path)
        print(f"Songs.db backup created: {songs_backup_name}")
        log(f"Backed up to {songs_backup_path}", verbose=verbose)

        shutil.copy2(songwords_db_path, songwords_backup_path)
        print(f"SongWords.db backup created: {songwords_backup_name}")
        log(f"Backed up to {songwords_backup_path}", verbose=verbose)
    except FileNotFoundError as exc:
        print(f"Error: Could not create backup. {exc}")
        raise SystemExit(1) from exc
    except PermissionError as exc:
        print("Error: Unable to create backups — database files may be in use.")
        print("Close EasyWorship and try again.")
        log(str(exc), verbose=verbose)
        raise SystemExit(1) from exc

    return BackupSet(
        songs_path=songs_backup_path,
        songwords_path=songwords_backup_path,
        songs_name=songs_backup_name,
        songwords_name=songwords_backup_name,
    )


def remove_backup_set(backup: BackupSet, *, verbose: bool = False) -> None:
    for path in (backup.songs_path, backup.songwords_path):
        if path.is_file():
            path.unlink()
            log(f"Removed backup {path.name}", verbose=verbose)


def restore_databases_from_backup(
    songs_db_path: Path,
    songwords_db_path: Path,
    backup: BackupSet,
    *,
    verbose: bool = False,
) -> None:
    shutil.copy2(backup.songs_path, songs_db_path)
    shutil.copy2(backup.songwords_path, songwords_db_path)
    log("Restored Songs.db and SongWords.db from backup.", verbose=verbose)
    print("Databases restored from backup.")


def count_table_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


def get_database_counts(
    songs_db_path: Path, songwords_db_path: Path
) -> Tuple[int, int]:
    return (
        count_table_rows(songs_db_path, "song"),
        count_table_rows(songwords_db_path, "word"),
    )


def validate_lyrics_txt_file(path: Path) -> Path:
    """Require an existing .txt file; return resolved path."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        print(f"Error: lyric file not found:\n  {path}")
        raise SystemExit(1)
    if resolved.suffix.lower() != ".txt":
        print(f"Error: lyric file must have a .txt extension:\n  {path}")
        raise SystemExit(1)
    return resolved


def read_lyrics_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def plain_text_to_rtf(plain: str) -> str:
    """
    Convert plain lyrics to minimal RTF for SongWords.db.

    EasyWorship import convention: blank line = new slide; first line = slide label.
    Newlines become \\par (paragraph breaks) in RTF.
    """
    escaped = (
        plain.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    body = escaped.replace("\n", "\\par ")
    return f"{{\\rtf1\\ansi\\deff0 {body}}}"


def connect_songs_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    register_utf8_ci_collation(conn)
    return conn


def connect_songwords_db(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path)


def find_song_id(cursor: sqlite3.Cursor, title: str) -> Optional[int]:
    cursor.execute("SELECT rowid FROM song WHERE title = ?", (title,))
    row = cursor.fetchone()
    return int(row[0]) if row else None


def insert_song(
    cursor: sqlite3.Cursor,
    meta: SongMetadata,
    *,
    verbose: bool = False,
) -> tuple[int, bool]:
    """Insert or return existing song. Returns (song_id, created)."""
    existing = find_song_id(cursor, meta.title)
    if existing is not None:
        log(f"Song '{meta.title}' already exists (id={existing}).", verbose=verbose)
        return existing, False

    uid = f"UID-{time.time_ns()}"
    cursor.execute(
        """
        INSERT INTO song (song_item_uid, title, author, copyright)
        VALUES (?, ?, ?, ?)
        """,
        (uid, meta.title, meta.author, meta.copyright),
    )
    song_id = int(cursor.lastrowid)
    log(f"Inserted song '{meta.title}' (id={song_id}).", verbose=verbose)
    return song_id, True


def lyrics_exist(cursor: sqlite3.Cursor, song_id: int) -> bool:
    cursor.execute("SELECT 1 FROM word WHERE song_id = ? LIMIT 1", (song_id,))
    return cursor.fetchone() is not None


def insert_lyrics(
    cursor: sqlite3.Cursor,
    song_id: int,
    plain_lyrics: str,
    *,
    overwrite: bool = False,
    verbose: bool = False,
) -> bool:
    """Insert lyrics RTF for song_id. Returns True if written."""
    if lyrics_exist(cursor, song_id):
        if not overwrite:
            log(f"Lyrics already exist for song_id={song_id}; skipping.", verbose=verbose)
            return False
        cursor.execute("DELETE FROM word WHERE song_id = ?", (song_id,))
        log(f"Removed existing lyrics for song_id={song_id}.", verbose=verbose)

    rtf = plain_text_to_rtf(plain_lyrics)
    cursor.execute(
        "INSERT INTO word (song_id, words) VALUES (?, ?)",
        (song_id, rtf),
    )
    log(f"Inserted lyrics for song_id={song_id}.", verbose=verbose)
    return True


def write_song_from_text(
    meta: SongMetadata,
    plain_lyrics: str,
    songs_db_path: Path,
    songwords_db_path: Path,
    *,
    overwrite_lyrics: bool = False,
    verbose: bool = False,
) -> WriteResult:
    """
    Write one song + lyrics into live EasyWorship databases.

    Caller is responsible for backups and ensuring EW is not locking the files.
    """
    conn_songs = connect_songs_db(songs_db_path)
    conn_words = connect_songwords_db(songwords_db_path)
    try:
        cur_songs = conn_songs.cursor()
        cur_words = conn_words.cursor()

        song_id, created = insert_song(cur_songs, meta, verbose=verbose)
        lyrics_written = insert_lyrics(
            cur_words,
            song_id,
            plain_lyrics,
            overwrite=overwrite_lyrics,
            verbose=verbose,
        )

        conn_songs.commit()
        conn_words.commit()
    finally:
        conn_songs.close()
        conn_words.close()

    return WriteResult(
        song_id=song_id,
        title=meta.title,
        created=created,
        lyrics_written=lyrics_written,
        backups={},
    )


def title_with_timestamp(base_title: str) -> str:
    """Append local date and time when base title is already in the library."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{base_title.strip()} {stamp}"


def resolve_song_title(
    base_title: str, songs_db_path: Path, *, verbose: bool = False
) -> Tuple[str, bool]:
    """
    Use base_title if unused; otherwise append YYYY-MM-DD HH:MM.
    Returns (final_title, used_timestamp_suffix).
    """
    base = base_title.strip()
    conn = connect_songs_db(songs_db_path)
    try:
        existing = find_song_id(conn.cursor(), base)
    finally:
        conn.close()

    if existing is None:
        log(f"Title {base!r} is available.", verbose=verbose)
        return base, False

    stamped = title_with_timestamp(base)
    log(
        f"Title {base!r} already exists (id={existing}); using {stamped!r}.",
        verbose=verbose,
    )
    return stamped, True


def build_song_metadata(
    file_path: Path,
    songs_db_path: Path,
    *,
    title: Optional[str] = None,
    author: Optional[str] = None,
    verbose: bool = False,
) -> SongMetadata:
    """Base title from --title or filename; timestamp suffix only if that title exists."""
    base = (title or file_path.stem).strip()
    resolved, _ = resolve_song_title(base, songs_db_path, verbose=verbose)
    return SongMetadata(
        title=resolved,
        author=(author or "Unknown").strip(),
    )


def process_txt_file(
    file_path: Path,
    songs_db_path: Path,
    songwords_db_path: Path,
    *,
    title: Optional[str] = None,
    author: Optional[str] = None,
    overwrite_lyrics: bool = False,
    verbose: bool = False,
) -> Optional[WriteResult]:
    """Import one .txt file."""
    try:
        plain = read_lyrics_file(file_path)
        meta = build_song_metadata(
            file_path,
            songs_db_path,
            title=title,
            author=author,
            verbose=verbose,
        )
        log(f"Processing {file_path} as {meta.title!r}", verbose=verbose)
        return write_song_from_text(
            meta,
            plain,
            songs_db_path,
            songwords_db_path,
            overwrite_lyrics=overwrite_lyrics,
            verbose=verbose,
        )
    except OSError as exc:
        print(f"Error reading {file_path}: {exc}")
        return None


def import_lyrics_file(
    file_path: Path,
    songs_db_path: Path,
    songwords_db_path: Path,
    *,
    title: Optional[str] = None,
    author: Optional[str] = None,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    verbose: bool = False,
) -> int:
    """
    Import one .txt into EasyWorship: backup, write, verify +1/+1 rows, rollback on failure.
    Deletes backup files when validation succeeds.
    """
    songs_before, words_before = get_database_counts(songs_db_path, songwords_db_path)
    log(f"Before: song={songs_before}, word={words_before}", verbose=verbose)

    backup = create_backup(songs_db_path, songwords_db_path, backup_dir, verbose=verbose)

    result = process_txt_file(
        file_path,
        songs_db_path,
        songwords_db_path,
        title=title,
        author=author,
        verbose=verbose,
    )
    if result is None:
        restore_databases_from_backup(songs_db_path, songwords_db_path, backup, verbose=verbose)
        print("Import failed while reading lyrics; databases restored.")
        return 1

    songs_after, words_after = get_database_counts(songs_db_path, songwords_db_path)
    log(f"After: song={songs_after}, word={words_after}", verbose=verbose)

    ok = (
        result.created
        and result.lyrics_written
        and songs_after == songs_before + 1
        and words_after == words_before + 1
    )

    if ok:
        remove_backup_set(backup, verbose=verbose)
        print(
            f"Import OK: {result.title!r} (id={result.song_id}). "
            "Row counts increased by 1. Backup removed."
        )
        log_database_state(songs_db_path, songwords_db_path)
        return 0

    print(
        "Import validation failed "
        f"(song {songs_before}->{songs_after}, word {words_before}->{words_after}, "
        f"created={result.created}, lyrics_written={result.lyrics_written})."
    )
    restore_databases_from_backup(songs_db_path, songwords_db_path, backup, verbose=verbose)
    restored_songs, restored_words = get_database_counts(songs_db_path, songwords_db_path)
    if restored_songs == songs_before and restored_words == words_before:
        print("Rollback OK: database counts match pre-import state.")
        print(f"Backup kept for inspection: {backup.songs_name}, {backup.songwords_name}")
        return 1

    print(
        "CRITICAL: Rollback may be incomplete. "
        f"Expected song={songs_before}, word={words_before}; "
        f"got song={restored_songs}, word={restored_words}. "
        f"Restore manually: {backup.songs_name}, {backup.songwords_name}"
    )
    return 2


def validate_database(db_path: Path, *, verbose: bool = False) -> bool:
    log(f"Validating {db_path}", verbose=verbose)
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("PRAGMA integrity_check;").fetchone()
        conn.close()
        ok = row is not None and row[0] == "ok"
        log(f"integrity_check: {row[0] if row else 'unknown'}", verbose=verbose)
        return ok
    except sqlite3.Error as exc:
        log(f"Validation error: {exc}", verbose=verbose)
        return False


def log_database_state(songs_db_path: Path, songwords_db_path: Path) -> None:
    for label, path, table in (
        ("Songs", songs_db_path, "song"),
        ("SongWords", songwords_db_path, "word"),
    ):
        try:
            conn = sqlite3.connect(path)
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.close()
            print(f"{label} ({path.name}): {count} rows in '{table}'")
        except sqlite3.Error as exc:
            print(f"Error reading {path}: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import lyrics into EasyWorship Songs.db and SongWords.db.",
        epilog=(
            "Lyrics .txt format: blank line separates slides; "
            "first line of each slide is the label (e.g. 'Verse 1'). "
            "If the title already exists in the library, YYYY-MM-DD HH:MM is appended."
        ),
    )
    parser.add_argument(
        "txt_file",
        metavar="TXT_FILE",
        nargs="?",
        type=Path,
        help="Full path to UTF-8 .txt lyric file to import.",
    )
    parser.add_argument(
        "--title",
        metavar="TEXT",
        help="Song title (default: .txt filename without extension).",
    )
    parser.add_argument(
        "--author",
        metavar="TEXT",
        help="Song author (default: Unknown).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print row counts and exit (no import).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    verbose = args.verbose

    songs_db, songwords_db = verify_databases_or_exit()

    if args.status:
        log_database_state(songs_db, songwords_db)
        return 0

    if args.txt_file is None:
        parser.error("TXT_FILE is required (full path to a .txt lyric file), or use --status.")

    lyrics_file = validate_lyrics_txt_file(args.txt_file)
    print(f"Lyric file:\n  {lyrics_file}")

    for db in (songs_db, songwords_db):
        if is_db_locked(db):
            print(
                f"Warning: {db} may be locked. "
                "Import may still work; use Refresh in EasyWorship after import."
            )

    base_title = (args.title or lyrics_file.stem).strip()
    final_title, stamped = resolve_song_title(base_title, songs_db, verbose=verbose)
    print(f"Importing: {lyrics_file}")
    if stamped:
        print(
            f"Duplicate title {base_title!r}; song will be added as {final_title!r}"
        )
    else:
        print(f"Song title in EasyWorship: {final_title!r}")
    return import_lyrics_file(
        lyrics_file,
        songs_db,
        songwords_db,
        title=args.title,
        author=args.author,
        verbose=verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
