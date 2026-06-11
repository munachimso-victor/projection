# Build LyricsOperator.exe on Windows.
# Syncs from \\wsl$\ to %USERPROFILE%\projection, then builds there.
# Run:  & "\\wsl$\Ubuntu\home\mvn27adm\projection\tools\lyrics_operator\desktop\build-desktop.ps1"

$ErrorActionPreference = "Stop"

$LocalRoot = Join-Path $env:USERPROFILE "projection"
$LocalOp = Join-Path $LocalRoot "tools\lyrics_operator"
$LocalDesktop = Join-Path $LocalOp "desktop"
$LocalEw = Join-Path $LocalRoot "tools\ew_song_writer"
$WslRoot = "\\wsl$\Ubuntu\home\mvn27adm\projection"
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

# --- build in %USERPROFILE%\projection\tools\lyrics_operator\desktop ---
$Py = Get-PythonExe
Set-Location $LocalDesktop
Write-Host "Building in $LocalDesktop"
Write-Host "Python:  $Py"
Write-Host ""

& $Py -m pip install -r requirements-build.txt
& $Py -m PyInstaller --noconfirm lyrics_operator.spec

$ew = Join-Path $LocalDesktop "dist\LyricsOperator\ew_song_writer"
New-Item -ItemType Directory -Force -Path $ew | Out-Null
Copy-Item (Join-Path $LocalEw "songimport.py") $ew -Force

$Exe = Join-Path $LocalDesktop "dist\LyricsOperator\LyricsOperator.exe"
if (-not (Test-Path -LiteralPath $Exe)) { throw "Build failed - missing $Exe" }

Write-Host ""
Write-Host "OK: $Exe"
Write-Host ""
Write-Host "Run (with UI on :3001 and API on :8000):"
Write-Host '  $env:LYRICS_OPERATOR_UI_URL = "http://127.0.0.1:3001/"'
Write-Host ('  & "' + $Exe + '"')
