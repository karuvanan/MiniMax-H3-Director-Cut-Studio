param(
    [string]$ComfyUIRoot = "C:\ai program\Data\Packages\ComfyUI-GPU-1",
    [string]$ComfyUIUrl = "http://127.0.0.1:8189"
)

$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "comfyui_director_h3_cache_status"
$customNodes = Join-Path $ComfyUIRoot "custom_nodes"
$destination = Join-Path $customNodes "comfyui_director_h3_cache_status"
$trayDestination = Join-Path $ComfyUIRoot "director_studio_h3_status_tray"

if (-not (Test-Path -LiteralPath (Join-Path $ComfyUIRoot "main.py") -PathType Leaf)) {
    throw "ComfyUI main.py was not found under: $ComfyUIRoot"
}
if (-not (Test-Path -LiteralPath $customNodes -PathType Container)) {
    throw "ComfyUI custom_nodes folder was not found: $customNodes"
}
if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Bundled cache-status companion was not found: $source"
}

New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source "__init__.py") -Destination $destination -Force
Copy-Item -LiteralPath (Join-Path $source "cache_status.py") -Destination $destination -Force
Copy-Item -LiteralPath (Join-Path $source "system_status.py") -Destination $destination -Force
Copy-Item -LiteralPath (Join-Path $source "README.md") -Destination $destination -Force

$configPath = Join-Path $trayDestination "tray-settings.json"
$cachePath = Join-Path $ComfyUIRoot "output\__h3_removal_cache"
$trayApiUrl = $ComfyUIUrl.TrimEnd("/")
$resourceRefreshSeconds = 5
$cacheRefreshSeconds = 120
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    try {
        $existing = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if (-not $PSBoundParameters.ContainsKey("ComfyUIUrl") -and $existing.api_url) {
            $trayApiUrl = [string]$existing.api_url
        }
        if ($existing.cache_path) {
            $cachePath = [string]$existing.cache_path
        }
        if ($existing.resource_refresh_seconds) {
            $resourceRefreshSeconds = [Math]::Max(
                2, [Math]::Min(300, [int]$existing.resource_refresh_seconds)
            )
        } elseif ($existing.refresh_seconds) {
            $resourceRefreshSeconds = [Math]::Max(
                2, [Math]::Min(300, [int]$existing.refresh_seconds)
            )
        }
        if ($existing.cache_refresh_seconds) {
            $cacheRefreshSeconds = [Math]::Max(
                5, [Math]::Min(3600, [int]$existing.cache_refresh_seconds)
            )
        }
    } catch {}
}
$serverSettingsPath = Join-Path $destination "status-settings.json"
[ordered]@{
    cache_path = $cachePath
    cache_refresh_seconds = $cacheRefreshSeconds
    resource_refresh_seconds = $resourceRefreshSeconds
} | ConvertTo-Json | Set-Content -LiteralPath $serverSettingsPath -Encoding UTF8

New-Item -ItemType Directory -Path $trayDestination -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "h3_status_tray.ps1") -Destination $trayDestination -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "start_h3_status_tray.bat") -Destination $trayDestination -Force
$trayScript = Join-Path $trayDestination "h3_status_tray.ps1"
$trayConfig = [ordered]@{
    api_url = $trayApiUrl
    cache_path = $cachePath
    resource_refresh_seconds = $resourceRefreshSeconds
    cache_refresh_seconds = $cacheRefreshSeconds
    server_settings_path = $serverSettingsPath
}
$trayConfig | ConvertTo-Json | Set-Content -LiteralPath (
    Join-Path $trayDestination "tray-settings.json"
) -Encoding UTF8

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Director Studio H3 Status Tray.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$trayScript`" -ConfigPath `"$configPath`""
$shortcut.WorkingDirectory = $trayDestination
$shortcut.Description = "MiniMax H3 Director Server Status Tray"
$shortcut.Save()

# Restart the exact installed Tray instance so an upgrade exposes the new
# Settings menu immediately. A failed process query is non-fatal; the mutex
# still prevents duplicate instances.
try {
    $trayPattern = [Regex]::Escape($trayScript)
    Get-CimInstance Win32_Process -ErrorAction Stop |
        Where-Object {
            $_.ProcessId -ne $PID -and
            [string]$_.CommandLine -match $trayPattern
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Milliseconds 300
} catch {}

Start-Process -FilePath $shortcut.TargetPath -ArgumentList $shortcut.Arguments -WorkingDirectory $trayDestination -WindowStyle Hidden

Write-Host "[H3 Cache Status] Installed to: $destination"
Write-Host "[H3 Server Status] Tray installed to: $trayDestination"
Write-Host "[H3 Server Status] Login startup shortcut: $shortcutPath"
Write-Host "[H3 Server Status] API: $trayApiUrl"
Write-Host "[H3 Server Status] Settings: right-click Tray icon, then Settings..."
Write-Host "[H3 Server Status] Defaults: resources 5 seconds; Cache Folder 120 seconds."
Write-Host "[H3 Cache Status] Restart ComfyUI, then Studio and Tray will show Cache, VRAM, DRAM, GPU and CPU."

