# Run Lyrics Operator desktop from a WSL repo path.
# Windows python/pip fail when cwd is a UNC path (\\wsl$\...). cmd "pushd" maps a real drive letter.

$ErrorActionPreference = "Stop"

$OperatorDir = $PSScriptRoot
if (-not (Test-Path (Join-Path $OperatorDir "desktop.py"))) {
    Write-Error "desktop.py not found next to this script."
}

if (-not $env:LYRICS_OPERATOR_UI_URL) {
    Write-Host "UI: cloud default (http://159.65.231.252/). For local dev: `$env:LYRICS_OPERATOR_UI_URL = 'http://127.0.0.1:3001/'"
}

if ($OperatorDir -match '^\\\\') {
    Write-Host "UNC path detected; using cmd pushd for python/pip ..."
    $ui = $env:LYRICS_OPERATOR_UI_URL
    cmd /c "pushd `"$OperatorDir`" && set LYRICS_OPERATOR_UI_URL=$ui && python -m pip install -r requirements-desktop.txt && python desktop.py && popd"
    exit $LASTEXITCODE
}

Set-Location $OperatorDir
Write-Host "Working directory: $(Get-Location)"
python -m pip install -r requirements-desktop.txt
python desktop.py
