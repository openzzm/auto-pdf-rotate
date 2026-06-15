param(
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $PythonExecutable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Pass a Python 3.12 path with -PythonExecutable."
    }
    $PythonExecutable = $pythonCommand.Source
}

$env:PYTHONPATH = "$Root\.build-tools;$Root\vendor"

& $PythonExecutable -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath "$Root\release" `
    --workpath "$Root\build\portable" `
    "$Root\portable.spec"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$exe = Join-Path $Root "release\AutoPDFRotate-Portable\AutoPDFRotate.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build completed but executable was not found: $exe"
}

Write-Host "Build completed: $exe"
