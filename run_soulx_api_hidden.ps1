$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $projectRoot "start_soulx_server.bat"
$logDirectory = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDirectory "soulx_api.stdout.log"
$stderrLog = Join-Path $logDirectory "soulx_api.stderr.log"

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "SoulX launcher was not found: $launcher"
}

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:7861/gradio_api/info" -TimeoutSec 2 | Out-Null
    exit 0
} catch {
    # The API is not ready. Avoid launching a duplicate while another process loads models.
}

$existingServer = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        ($_.CommandLine -like "*soulx_server.py*" -or $_.CommandLine -like "*webui_svc.py*") -and
        $_.CommandLine -like "*7861*"
    } |
    Select-Object -First 1
if ($existingServer) {
    exit 0
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$env:SOULX_NO_PAUSE = "1"
Start-Process `
    -FilePath $env:ComSpec `
    -ArgumentList @("/d", "/c", "`"$launcher`"") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

