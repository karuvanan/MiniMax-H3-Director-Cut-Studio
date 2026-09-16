$ErrorActionPreference = "Stop"

$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$launcher = Join-Path $projectRoot "start_audio_separator_server.bat"
$stopper = Join-Path $projectRoot "stop_audio_separator_server.ps1"
$logDirectory = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDirectory "audio_separator_api.stdout.log"
$stderrLog = Join-Path $logDirectory "audio_separator_api.stderr.log"

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "Audio Separator launcher was not found: $launcher"
}
if (-not (Test-Path -LiteralPath $stopper -PathType Leaf)) {
    throw "Audio Separator process controller was not found: $stopper"
}

$apiReady = $false
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:7862/health" -TimeoutSec 2
    $apiReady = [bool]$health.ready -and [bool]$health.cuda_provider -and
        ([string]$health.provider -eq "CUDAExecutionProvider")
} catch {
    # The API is offline or still starting.
}
if ($apiReady) {
    exit 0
}

$existingServer = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine.IndexOf($projectRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        ($_.CommandLine -like "*audio_separator_server.py*" -or
         $_.CommandLine -like "*vocal_separator_service.py*")
    } |
    Select-Object -First 1
if ($existingServer) {
    Start-Sleep -Milliseconds 600
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:7862/health" -TimeoutSec 2
        if ([bool]$health.ready -and [bool]$health.cuda_provider) {
            exit 0
        }
    } catch {
        # Replace an incomplete or stale project-owned process below.
    }
}

& $stopper -ProjectRoot $projectRoot -Port 7862 -WaitSeconds 20
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$env:AUDIO_SEPARATOR_NO_PAUSE = "1"
Start-Process `
    -FilePath $env:ComSpec `
    -ArgumentList @("/d", "/c", "`"$launcher`"") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog
