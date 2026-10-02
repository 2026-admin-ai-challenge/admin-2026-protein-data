param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot '.mpl-cache'
$env:PYTHONUTF8 = '1'
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install requirements.txt first.' }
if (-not $VerifyOnly) {
    & $pythonPath -u scripts/prepare_dataset.py
    if ($LASTEXITCODE -ne 0) { throw 'Preprocessing failed; inspect existing outputs before retrying.' }
}
& $pythonPath -u scripts/verify_dataset.py
if ($LASTEXITCODE -ne 0) { throw 'Dataset verification failed.' }
& $pythonPath -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
