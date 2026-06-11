# PyInstaller spec — build on Windows: pyinstaller lyrics_operator.spec
# Output: dist/LyricsOperator/LyricsOperator.exe

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# SPECPATH is the folder containing this spec: tools/lyrics_operator/desktop
_spec = Path(SPECPATH).resolve()
if (_spec / "desktop.py").is_file():
    root = _spec
elif (_spec.parent / "desktop.py").is_file():
    root = _spec.parent
else:
    raise SystemExit(f"desktop.py not found near SPECPATH={SPECPATH!r} (_spec={_spec})")

# UI lives in ../ui
_ui = root.parent / "ui"

# songimport lives in tools/ew_song_writer (desktop -> lyrics_operator -> tools)
_songimport = root.parent.parent / "ew_song_writer" / "songimport.py"

datas = [
    (str(_ui / "index.html"), "."),
    (str(_ui / "app.js"), "."),
    (str(_ui / "app.css"), "."),
    (str(_songimport), "ew_song_writer"),
]

binaries = []
# songimport.py is loaded dynamically at runtime, so its imports must be forced in.
hiddenimports = ["sqlite3", "_sqlite3"]
for pkg in ("webview",):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    [str(root / "desktop.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LyricsOperator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LyricsOperator",
)
