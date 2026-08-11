$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Runtime = Join-Path $Root 'runtime'
$Checks = @(
    @{ Name='Embedded Python'; Path=(Join-Path $Runtime 'python/python.exe') },
    @{ Name='WanGP backend'; Path=(Join-Path $Runtime 'WanGP/studio_backend.py') },
    @{ Name='FFmpeg'; Path=(Join-Path $Runtime 'ffmpeg/bin/ffmpeg.exe') },
    @{ Name='FFprobe'; Path=(Join-Path $Runtime 'ffmpeg/bin/ffprobe.exe') }
)

$failed = $false
Write-Host 'AI Creator Studio runtime check' -ForegroundColor Cyan
foreach ($check in $Checks) {
    if (Test-Path $check.Path) {
        Write-Host "[OK]   $($check.Name): $($check.Path)" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $($check.Name): $($check.Path)" -ForegroundColor Red
        $failed = $true
    }
}

if ($failed) {
    Write-Host ''
    Write-Host 'Runtime is incomplete. This is expected until the Windows runtime packaging stage is finished.' -ForegroundColor Yellow
    exit 1
}

& (Join-Path $Runtime 'python/python.exe') --version
& (Join-Path $Runtime 'ffmpeg/bin/ffmpeg.exe') -version | Select-Object -First 1
Write-Host 'Runtime structure looks complete.' -ForegroundColor Green
