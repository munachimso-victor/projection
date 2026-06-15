# Build LyricsOperator.exe on Windows.
# Syncs from \\wsl$\ to %USERPROFILE%\projection, then builds there.
# Run:  & "\\wsl$\Ubuntu\home\mvn27adm\projection\tools\lyrics_operator\desktop\build-desktop.ps1"

$ErrorActionPreference = "Stop"

$LocalRoot = Join-Path $env:USERPROFILE "projection"
$LocalOp = Join-Path $LocalRoot "tools\lyrics_operator"
$LocalDesktop = Join-Path $LocalOp "desktop"
$LocalEw = Join-Path $LocalRoot "tools\ew_song_writer"
function Get-WslProjectionRoot {
    foreach ($distro in @("Ubuntu", "Ubuntu-24.04", "Ubuntu-22.04")) {
        $root = "\\wsl$\$distro\home\mvn27adm\projection"
        if (Test-Path -LiteralPath $root) { return $root }
    }
    throw "WSL repo not found. Tried: \\wsl$\Ubuntu\..., Ubuntu-24.04, Ubuntu-22.04"
}

$WslRoot = Get-WslProjectionRoot
$WslOp = Join-Path $WslRoot "tools\lyrics_operator"
$WslEw = Join-Path $WslRoot "tools\ew_song_writer"

function Get-PythonExe {
    $pyCmd = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    $py = if ($pyCmd) { $pyCmd.Source } else { $null }
    if ($py -like "*\pyenv-win\shims\*" -or $py -like "*.bat") { $py = $null }
    if (-not $py -and (Test-Path "$env:USERPROFILE\.pyenv\pyenv-win\versions")) {
        $ver = if (Get-Command pyenv -EA SilentlyContinue) { (& pyenv version-name).Trim() } else { $null }
        if ($ver) { $py = "$env:USERPROFILE\.pyenv\pyenv-win\versions\$ver\python.exe" }
    }
    if (-not $py -or -not (Test-Path -LiteralPath $py)) {
        throw "Need Python 3.10+ (python.exe). Example: pyenv install 3.12.0 ; pyenv global 3.12.0"
    }
    return $py
}

# --- sync only the two folders the build needs (fast over \\wsl$\) ---
if (-not (Test-Path -LiteralPath $WslOp)) {
    throw "WSL repo not found at $WslOp"
}
Write-Host "Syncing build sources -> $LocalRoot ..."
New-Item -ItemType Directory -Force -Path $LocalOp | Out-Null
New-Item -ItemType Directory -Force -Path $LocalEw | Out-Null
robocopy $WslOp $LocalOp /E /XD dist build __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed for lyrics_operator (exit $LASTEXITCODE)" }
robocopy $WslEw $LocalEw /E /XD dist build __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed for ew_song_writer (exit $LASTEXITCODE)" }

$desktopPy = Join-Path $LocalDesktop "desktop.py"
$desktopSrc = Get-Content -LiteralPath $desktopPy -Raw
if ($desktopSrc -notmatch "def default_ui_url") {
    throw "Synced desktop.py is outdated (missing default_ui_url). Check WSL repo at $WslRoot"
}
$prodMatch = [regex]::Match($desktopSrc, 'PRODUCTION_UI_URL\s*=\s*"([^"]+)"')
if (-not $prodMatch.Success) { throw "PRODUCTION_UI_URL not found in synced desktop.py" }
$productionUrl = $prodMatch.Groups[1].Value
Write-Host "Synced desktop.py -> PRODUCTION_UI_URL = $productionUrl"

$buildMatch = [regex]::Match($desktopSrc, 'DESKTOP_BUILD\s*=\s*"([^"]+)"')
if ($buildMatch.Success) {
    Write-Host "Synced desktop.py -> DESKTOP_BUILD = $($buildMatch.Groups[1].Value)"
}

# --- build in %USERPROFILE%\projection\tools\lyrics_operator\desktop ---
$Py = Get-PythonExe
Set-Location $LocalDesktop
Write-Host "Building in $LocalDesktop"
Write-Host "Python:  $Py"
Write-Host ""

Get-Process -Name LyricsOperator -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping running LyricsOperator (PID $($_.Id)) ..."
    Stop-Process -Id $_.Id -Force
}

& $Py -m pip install -r requirements-build.txt
if (Test-Path build) { Remove-Item -Recurse -Force build }
$distDir = Join-Path $LocalDesktop "dist\LyricsOperator"
if (Test-Path $distDir) {
    Write-Host "Removing old dist: $distDir"
    Remove-Item -Recurse -Force $distDir
}
& $Py -m PyInstaller --clean --noconfirm lyrics_operator.spec

$ew = Join-Path $LocalDesktop "dist\LyricsOperator\ew_song_writer"
New-Item -ItemType Directory -Force -Path $ew | Out-Null
Copy-Item (Join-Path $LocalEw "songimport.py") $ew -Force

$Exe = Join-Path $LocalDesktop "dist\LyricsOperator\LyricsOperator.exe"
if (-not (Test-Path -LiteralPath $Exe)) { throw "Build failed - missing $Exe" }

$exeItem = Get-Item -LiteralPath $Exe
$exeAge = (Get-Date) - $exeItem.LastWriteTime
if ($exeAge.TotalMinutes -gt 15) {
    throw "Exe timestamp is stale ($($exeItem.LastWriteTime)) - PyInstaller did not produce a fresh binary. Close LyricsOperator and rebuild."
}

Write-Host ""
Write-Host "OK: $Exe"
Write-Host "    Modified: $($exeItem.LastWriteTime)"
Write-Host ""
Write-Host "Run (cloud UI baked in - no env vars needed):"
Write-Host ('  & "' + $Exe + '"')
Write-Host ""
Write-Host "Startup should show:"
Write-Host "  Build:         ew-data-dir-2026-06-13"
Write-Host "  UI mode:       cloud"
Write-Host "  UI:            ${productionUrl}?localImport=..."
Write-Host ""
Write-Host "If you see UI mode: local or 127.0.0.1:3001, clear stale env vars:"
Write-Host '  Remove-Item Env:LYRICS_OPERATOR_LOCAL -ErrorAction SilentlyContinue'
Write-Host '  Remove-Item Env:LYRICS_OPERATOR_UI_URL -ErrorAction SilentlyContinue'
Write-Host ""
Write-Host "Local dev only (serve_ui.py on :3001):"
Write-Host '  $env:LYRICS_OPERATOR_LOCAL = "1"'
Write-Host '  $env:LYRICS_OPERATOR_UI_URL = "http://127.0.0.1:3001/"'
Write-Host ('  & "' + $Exe + '"')
