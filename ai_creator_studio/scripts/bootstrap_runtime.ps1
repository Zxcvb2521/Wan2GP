$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root 'runtime'
$PythonDir = Join-Path $Runtime 'python'
$WanDir = Join-Path $Runtime 'WanGP'
$FfmpegDir = Join-Path $Runtime 'ffmpeg'

Write-Host 'AI Creator Studio - Windows runtime bootstrap' -ForegroundColor Cyan
Write-Host "Runtime: $Runtime"

New-Item -ItemType Directory -Force -Path $PythonDir,$WanDir,$FfmpegDir | Out-Null

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) is required only for BUILDING the runtime. The final application does not require system Python.'
}

Write-Host 'Installing an isolated embedded Python runtime...' -ForegroundColor Yellow
py install 3.11-embed --target=$PythonDir

$Python = Join-Path $PythonDir 'python.exe'
if (-not (Test-Path $Python)) { throw "Embedded Python was not created: $Python" }

Write-Host ''
Write-Host 'Embedded Python created successfully.' -ForegroundColor Green
Write-Host 'Next: populate runtime/WanGP with the selected WanGP runtime and install its vendored dependencies.'
Write-Host 'Do NOT run pip against the end-user installation. Dependencies must be vendored into runtime.'
Write-Host ''
Write-Host 'FFmpeg is intentionally not downloaded by this script yet; the final package must pin and verify its Windows build.'
