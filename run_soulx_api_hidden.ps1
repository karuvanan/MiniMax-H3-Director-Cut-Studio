$ErrorActionPreference = "Stop"

$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$launcher = Join-Path $projectRoot "start_soulx_server.bat"
$stopper = Join-Path $projectRoot "stop_soulx_server.ps1"
$logDirectory = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDirectory "soulx_api.stdout.log"
$stderrLog = Join-Path $logDirectory "soulx_api.stderr.log"

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw "SoulX launcher was not found: $launcher"
}
if (-not (Test-Path -LiteralPath $stopper -PathType Leaf)) {
    throw "SoulX process controller was not found: $stopper"
}

$apiResponding = $false
$stableApiReady = $false
try {
    $apiInfo = Invoke-RestMethod -Uri "http://127.0.0.1:7861/gradio_api/info" -TimeoutSec 2
    $apiResponding = $true
    $endpointNames = @($apiInfo.named_endpoints.PSObject.Properties.Name)
    $stableApiReady = $endpointNames -contains "/_studio_start_svc"
} catch {
    # The API is not ready. Process inspection below prevents duplicate loading.
}

if ($stableApiReady) {
    exit 0
}

$existingServer = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine.IndexOf($projectRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
        ($_.CommandLine -like "*soulx_server.py*" -or $_.CommandLine -like "*webui_svc.py*") -and
        $_.CommandLine -like "*7861*"
    } |
    Select-Object -First 1
if ($existingServer -and -not $apiResponding) {
    # A matching process is still starting and has not published its API yet.
    exit 0
}

# Remove a responsive stale API, or prove that an otherwise silent port is
# genuinely bindable. The controller refuses to stop an unrelated listener.
& $stopper -ProjectRoot $projectRoot -Port 7861 -WaitSeconds 20

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$env:SOULX_NO_PAUSE = "1"
Start-Process `
    -FilePath $env:ComSpec `
    -ArgumentList @("/d", "/c", "`"$launcher`"") `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog
