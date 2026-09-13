$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $projectRoot "start_ace_step_api.bat"
$logDirectory = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDirectory "ace_step_api.stdout.log"
$stderrLog = Join-Path $logDirectory "ace_step_api.stderr.log"

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "ACE-Step launcher was not found: $launcher"
}

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -TimeoutSec 2 | Out-Null
    exit 0
} catch {
    # The API is not ready. Check for an existing process that may still be loading models.
}

$existingServer = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*acestep.api_server*" -and
        $_.CommandLine -like "*--port 8001*"
    } |
    Select-Object -First 1
if ($existingServer) {
    exit 0
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$env:ACE_STEP_NO_PAUSE = "1"
Start-Process `
    -FilePath $env:ComSpec `
    -ArgumentList @("/d", "/c", "`"$launcher`"") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

