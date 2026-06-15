# Run Lyrics Operator desktop from a WSL repo path.
# Windows python/pip fail when cwd is a UNC path (\\wsl$\...). cmd "pushd" maps a real drive letter.

$ErrorActionPreference = "Stop"

$OperatorDir = $PSScriptRoot
if (-not (Test-Path (Join-Path $OperatorDir "desktop.py"))) {
    Write-Error "desktop.py not found next to this script."
}

if (-not $env:LYRICS_OPERATOR_LOCAL) {
    Write-Host "UI: cloud (http://159.65.231.252/ - edit PRODUCTION_UI_URL in desktop.py to change)"
    Write-Host "For local dev: `$env:LYRICS_OPERATOR_LOCAL = '1'; `$env:LYRICS_OPERATOR_UI_URL = 'http://127.0.0.1:3001/'"
}

if ($OperatorDir -match '^\\\\') {
    Write-Host "UNC path detected; using cmd pushd for python/pip ..."
    if ($env:LYRICS_OPERATOR_LOCAL) {
        $ui = $env:LYRICS_OPERATOR_UI_URL
        if (-not $ui) { $ui = "http://127.0.0.1:3001/" }
        cmd /c "pushd `"$OperatorDir`" && set LYRICS_OPERATOR_LOCAL=1 && set LYRICS_OPERATOR_UI_URL=$ui && python -m pip install -r requirements-desktop.txt && python desktop.py && popd"
    } else {
        cmd /c "pushd `"$OperatorDir`" && python -m pip install -r requirements-desktop.txt && python desktop.py && popd"
    }
    exit $LASTEXITCODE
}

Set-Location $OperatorDir
Write-Host "Working directory: $(Get-Location)"
python -m pip install -r requirements-desktop.txt
python desktop.py
