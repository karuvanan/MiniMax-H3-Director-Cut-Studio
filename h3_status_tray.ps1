param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "tray-settings.json")
)

$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$createdNew = $false
$mutex = New-Object System.Threading.Mutex(
    $true,
    "Local\MiniMaxH3DirectorServerStatusTray",
    [ref]$createdNew
)
if (-not $createdNew) {
    exit 0
}

function Read-TrayConfig {
    $defaults = [pscustomobject]@{
        api_url = "http://127.0.0.1:8189"
        cache_path = ""
        resource_refresh_seconds = 5
        cache_refresh_seconds = 120
        server_settings_path = ""
        lm_studio_url = ""
        qwen_model = "qwen3.8-uncensored-mtp"
        qwen_key_filter = "qwen3"
    }
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        return $defaults
    }
    try {
        $saved = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if ($saved.api_url) { $defaults.api_url = [string]$saved.api_url }
        if ($saved.cache_path) { $defaults.cache_path = [string]$saved.cache_path }
        if ($saved.resource_refresh_seconds) {
            $defaults.resource_refresh_seconds = [Math]::Max(
                2, [Math]::Min(300, [int]$saved.resource_refresh_seconds)
            )
        } elseif ($saved.refresh_seconds) {
            # Backward compatibility with v0.3.7-alpha.11 and earlier.
            $defaults.resource_refresh_seconds = [Math]::Max(
                2, [Math]::Min(300, [int]$saved.refresh_seconds)
            )
        }
        if ($saved.cache_refresh_seconds) {
            $defaults.cache_refresh_seconds = [Math]::Max(
                5, [Math]::Min(3600, [int]$saved.cache_refresh_seconds)
            )
        }
        if ($saved.server_settings_path) {
            $defaults.server_settings_path = [string]$saved.server_settings_path
        }
        if ($saved.lm_studio_url) { $defaults.lm_studio_url = [string]$saved.lm_studio_url }
        if ($saved.qwen_model) { $defaults.qwen_model = [string]$saved.qwen_model }
        if ($saved.qwen_key_filter) { $defaults.qwen_key_filter = [string]$saved.qwen_key_filter }
    } catch {}
    return $defaults
}

function Write-TrayConfig {
    try {
        $configParent = Split-Path -Parent $ConfigPath
        if ($configParent) {
            New-Item -ItemType Directory -Path $configParent -Force | Out-Null
        }
        $script:config | ConvertTo-Json | Set-Content -LiteralPath $ConfigPath -Encoding UTF8 -ErrorAction Stop

        $serverSettingsPath = [string]$script:config.server_settings_path
        if ($serverSettingsPath) {
            $serverSettingsParent = Split-Path -Parent $serverSettingsPath
            if ($serverSettingsParent) {
                New-Item -ItemType Directory -Path $serverSettingsParent -Force | Out-Null
            }
            [ordered]@{
                cache_path = [string]$script:config.cache_path
                cache_refresh_seconds = [int]$script:config.cache_refresh_seconds
                resource_refresh_seconds = [int]$script:config.resource_refresh_seconds
            } | ConvertTo-Json | Set-Content -LiteralPath $serverSettingsPath -Encoding UTF8 -ErrorAction Stop
        }
        return $true
    } catch {
        [System.Windows.Forms.MessageBox]::Show(
            "Settings could not be saved.`r`n`r`n$($_.Exception.Message)",
            "H3 Server Status Settings",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
        return $false
    }
}

function Format-Percent($value) {
    if ($null -eq $value) { return "N/A" }
    try { return ("{0:0.#}%" -f [double]$value) } catch { return "N/A" }
}

function Format-Gigabytes($bytes) {
    if ($null -eq $bytes) { return "N/A" }
    try { return ("{0:0.0}GB" -f ([double]$bytes / 1GB)) } catch { return "N/A" }
}

function Get-QwenLoadedInstances {
    if (-not $script:lmEndpointBase) { return @() }
    try {
        $catalog = Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/v1/models") -Method Get -TimeoutSec 4
        $needle = [string]$config.qwen_key_filter
        if (-not $needle) { return @() }
        $out = @()
        foreach ($model in $catalog.models) {
            # -match is case-insensitive, mirroring the staged driver's key filter.
            if ([string]$model.key -match [regex]::Escape($needle)) {
                foreach ($inst in $model.loaded_instances) {
                    if ($null -eq $inst) { continue }
                    if ($inst -is [System.Management.Automation.PSCustomObject]) { $out += [string]$inst.id }
                    else { $out += [string]$inst }
                }
            }
        }
        return $out
    } catch {}
    return @()
}

function Invoke-TrayAction([string]$Title, [scriptblock]$Body) {
    try {
        & $Body | Out-Null
        Update-H3TrayStatus
        $notify.BalloonTipTitle = "H3 Status Tray"
        $notify.BalloonTipText = "$Title : done"
        $notify.ShowBalloonTip(2500)
    } catch {
        Update-H3TrayStatus
        [System.Windows.Forms.MessageBox]::Show(
            "$Title failed:`r`n$($_.Exception.Message)",
            "H3 Status Tray",
            [System.Windows.Forms.MessageBoxButtons].OK,
            [System.Windows.Forms.MessageBoxIcon].Warning
        ) | Out-Null
    }
}

$config = Read-TrayConfig
$endpoint = $config.api_url.TrimEnd("/") + "/director_studio/h3-relay-cache-status"
$lmEndpointBase = [string]$config.lm_studio_url
if (-not $lmEndpointBase) {
    try {
        $parsedApiUrl = [Uri]$config.api_url
        $lmEndpointBase = "http://$($parsedApiUrl.Host):1234"
    } catch { $lmEndpointBase = "" }
}
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.Text = "H3 Server Status"

$menu = New-Object System.Windows.Forms.ContextMenuStrip
$statusItem = New-Object System.Windows.Forms.ToolStripMenuItem
$statusItem.Text = "Connecting to ComfyUI..."
$statusItem.Enabled = $false
$menu.Items.Add($statusItem) | Out-Null
$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator)) | Out-Null
$settingsItem = New-Object System.Windows.Forms.ToolStripMenuItem
$settingsItem.Text = "Settings..."
$menu.Items.Add($settingsItem) | Out-Null
$refreshItem = New-Object System.Windows.Forms.ToolStripMenuItem
$refreshItem.Text = "Refresh now"
$menu.Items.Add($refreshItem) | Out-Null
$openComfyItem = New-Object System.Windows.Forms.ToolStripMenuItem
$openComfyItem.Text = "Open ComfyUI"
$menu.Items.Add($openComfyItem) | Out-Null
$openCacheItem = New-Object System.Windows.Forms.ToolStripMenuItem
$openCacheItem.Text = "Open H3 cache folder"
$menu.Items.Add($openCacheItem) | Out-Null
$unloadQwenItem = New-Object System.Windows.Forms.ToolStripMenuItem
$unloadQwenItem.Text = "Unload Qwen (free GPU for H3)"
$menu.Items.Add($unloadQwenItem) | Out-Null
$loadQwenItem = New-Object System.Windows.Forms.ToolStripMenuItem
$loadQwenItem.Text = "Load Qwen (for Design / agent)"
$menu.Items.Add($loadQwenItem) | Out-Null
$freeComfyItem = New-Object System.Windows.Forms.ToolStripMenuItem
$freeComfyItem.Text = "Free ComfyUI (/free)"
$menu.Items.Add($freeComfyItem) | Out-Null
$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator)) | Out-Null
$exitItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exitItem.Text = "Exit H3 Status Tray"
$menu.Items.Add($exitItem) | Out-Null
$notify.ContextMenuStrip = $menu

function Update-H3TrayStatus {
    try {
        $payload = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 4
        if (-not $payload.ok) { throw "Invalid status response" }
        $resources = $payload.resources
        $cache = Format-Gigabytes $payload.used_bytes
        $vram = Format-Percent $resources.vram_percent
        $dram = Format-Percent $resources.dram_percent
        $gpu = Format-Percent $resources.gpu_percent
        $cpu = Format-Percent $resources.cpu_percent
        $qwenInstances = Get-QwenLoadedInstances
        $ownerState = if ($qwenInstances.Count -gt 0) { "QWEN loaded (agent owns GPU)" } else { "GPU free for H3" }
        $summary = "$ownerState | Cache $cache/100GB | VRAM $vram | DRAM $dram | GPU $gpu | CPU $cpu"
        $statusItem.Text = $summary
        $notify.Text = if ($summary.Length -gt 63) {
            $summary.Substring(0, 63)
        } else { $summary }
        $high = @(
            $resources.vram_percent, $resources.dram_percent,
            $resources.gpu_percent, $resources.cpu_percent
        ) | Where-Object { $null -ne $_ } | Measure-Object -Maximum
        if ($qwenInstances.Count -gt 0 -and $null -ne $resources.vram_percent -and [double]$resources.vram_percent -ge 80) {
            # Agent side owns the GPU: Qwen resident, H3 would OOM without unload-qwen.
            $notify.Icon = [System.Drawing.SystemIcons]::Warning
        } elseif ([double]$high.Maximum -ge 95 -or [double]$payload.used_bytes -ge 90GB) {
            $notify.Icon = [System.Drawing.SystemIcons]::Error
        } elseif ([double]$high.Maximum -ge 80 -or [double]$payload.used_bytes -ge 70GB) {
            $notify.Icon = [System.Drawing.SystemIcons]::Warning
        } else {
            $notify.Icon = [System.Drawing.SystemIcons]::Information
        }
    } catch {
        $qwenState = if ((Get-QwenLoadedInstances).Count -gt 0) { "QWEN loaded" } else { "GPU free for H3" }
        $statusItem.Text = "ComfyUI unavailable | $qwenState | Cache/VRAM/DRAM/GPU/CPU N/A"
        $notify.Text = "H3 Server Status - ComfyUI unavailable"
        $notify.Icon = [System.Drawing.SystemIcons]::Warning
    }
}

function Show-TraySettings {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "H3 Server Status Settings"
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.ClientSize = New-Object System.Drawing.Size(640, 418)
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

    $resourceRefreshLabel = New-Object System.Windows.Forms.Label
    $resourceRefreshLabel.Text = "VRAM / DRAM / GPU / CPU refresh"
    $resourceRefreshLabel.Location = New-Object System.Drawing.Point(18, 22)
    $resourceRefreshLabel.Size = New-Object System.Drawing.Size(220, 24)
    $form.Controls.Add($resourceRefreshLabel)

    $resourceRefreshInput = New-Object System.Windows.Forms.NumericUpDown
    $resourceRefreshInput.Minimum = 2
    $resourceRefreshInput.Maximum = 300
    $resourceRefreshInput.Value = [decimal][Math]::Max(2, [Math]::Min(300, [int]$script:config.resource_refresh_seconds))
    $resourceRefreshInput.Location = New-Object System.Drawing.Point(250, 19)
    $resourceRefreshInput.Size = New-Object System.Drawing.Size(85, 26)
    $form.Controls.Add($resourceRefreshInput)

    $resourceSecondsLabel = New-Object System.Windows.Forms.Label
    $resourceSecondsLabel.Text = "seconds"
    $resourceSecondsLabel.Location = New-Object System.Drawing.Point(343, 22)
    $resourceSecondsLabel.Size = New-Object System.Drawing.Size(70, 24)
    $form.Controls.Add($resourceSecondsLabel)

    $cacheRefreshLabel = New-Object System.Windows.Forms.Label
    $cacheRefreshLabel.Text = "Cache Folder refresh"
    $cacheRefreshLabel.Location = New-Object System.Drawing.Point(18, 64)
    $cacheRefreshLabel.Size = New-Object System.Drawing.Size(220, 24)
    $form.Controls.Add($cacheRefreshLabel)

    $cacheRefreshInput = New-Object System.Windows.Forms.NumericUpDown
    $cacheRefreshInput.Minimum = 5
    $cacheRefreshInput.Maximum = 3600
    $cacheRefreshInput.Value = [decimal][Math]::Max(5, [Math]::Min(3600, [int]$script:config.cache_refresh_seconds))
    $cacheRefreshInput.Location = New-Object System.Drawing.Point(250, 61)
    $cacheRefreshInput.Size = New-Object System.Drawing.Size(85, 26)
    $form.Controls.Add($cacheRefreshInput)

    $cacheSecondsLabel = New-Object System.Windows.Forms.Label
    $cacheSecondsLabel.Text = "seconds"
    $cacheSecondsLabel.Location = New-Object System.Drawing.Point(343, 64)
    $cacheSecondsLabel.Size = New-Object System.Drawing.Size(70, 24)
    $form.Controls.Add($cacheSecondsLabel)

    $apiLabel = New-Object System.Windows.Forms.Label
    $apiLabel.Text = "Monitored ComfyUI URL / IP"
    $apiLabel.Location = New-Object System.Drawing.Point(18, 110)
    $apiLabel.Size = New-Object System.Drawing.Size(190, 24)
    $form.Controls.Add($apiLabel)

    $apiInput = New-Object System.Windows.Forms.TextBox
    $apiInput.Text = [string]$script:config.api_url
    $apiInput.Location = New-Object System.Drawing.Point(202, 107)
    $apiInput.Size = New-Object System.Drawing.Size(418, 26)
    $form.Controls.Add($apiInput)

    $cacheLabel = New-Object System.Windows.Forms.Label
    $cacheLabel.Text = "Monitored cache folder"
    $cacheLabel.Location = New-Object System.Drawing.Point(18, 156)
    $cacheLabel.Size = New-Object System.Drawing.Size(175, 24)
    $form.Controls.Add($cacheLabel)

    $cacheInput = New-Object System.Windows.Forms.TextBox
    $cacheInput.Text = [string]$script:config.cache_path
    $cacheInput.Location = New-Object System.Drawing.Point(202, 153)
    $cacheInput.Size = New-Object System.Drawing.Size(350, 26)
    $form.Controls.Add($cacheInput)

    $browseButton = New-Object System.Windows.Forms.Button
    $browseButton.Text = "Browse..."
    $browseButton.Location = New-Object System.Drawing.Point(560, 151)
    $browseButton.Size = New-Object System.Drawing.Size(60, 29)
    $browseButton.Add_Click({
        $picker = New-Object System.Windows.Forms.FolderBrowserDialog
        $picker.Description = "Select the H3 Relay cache folder to monitor"
        if (Test-Path -LiteralPath $cacheInput.Text -PathType Container) {
            $picker.SelectedPath = $cacheInput.Text
        }
        if ($picker.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
            $cacheInput.Text = $picker.SelectedPath
        }
        $picker.Dispose()
    })
    $form.Controls.Add($browseButton)

    $lmLabel = New-Object System.Windows.Forms.Label
    $lmLabel.Text = "LM Studio URL (empty = ComfyUI host:1234)"
    $lmLabel.Location = New-Object System.Drawing.Point(18, 196)
    $lmLabel.Size = New-Object System.Drawing.Size(175, 24)
    $form.Controls.Add($lmLabel)

    $lmInput = New-Object System.Windows.Forms.TextBox
    $lmInput.Text = [string]$config.lm_studio_url
    $lmInput.Location = New-Object System.Drawing.Point(202, 193)
    $lmInput.Size = New-Object System.Drawing.Size(418, 26)
    $form.Controls.Add($lmInput)

    $modelLabel = New-Object System.Windows.Forms.Label
    $modelLabel.Text = "Qwen model for Load Qwen"
    $modelLabel.Location = New-Object System.Drawing.Point(18, 238)
    $modelLabel.Size = New-Object System.Drawing.Size(175, 24)
    $form.Controls.Add($modelLabel)

    $modelInput = New-Object System.Windows.Forms.TextBox
    $modelInput.Text = [string]$config.qwen_model
    $modelInput.Location = New-Object System.Drawing.Point(202, 235)
    $modelInput.Size = New-Object System.Drawing.Size(418, 26)
    $form.Controls.Add($modelInput)

    $hint = New-Object System.Windows.Forms.Label
    $hint.Text = "Defaults: resources 5s, Cache Folder 120s. Changes apply immediately."
    $hint.ForeColor = [System.Drawing.Color]::FromArgb(70, 120, 145)
    $hint.Location = New-Object System.Drawing.Point(202, 278)
    $hint.Size = New-Object System.Drawing.Size(418, 36)
    $form.Controls.Add($hint)

    $saveButton = New-Object System.Windows.Forms.Button
    $saveButton.Text = "Save"
    $saveButton.Location = New-Object System.Drawing.Point(446, 320)
    $saveButton.Size = New-Object System.Drawing.Size(82, 32)
    $saveButton.Add_Click({
        $url = $apiInput.Text.Trim().TrimEnd("/")
        if ($url -and $url -notmatch "^https?://") {
            $url = "http://" + $url
        }
        try { $uri = [Uri]$url } catch { $uri = $null }
        if ($null -eq $uri -or $uri.Scheme -notin @("http", "https") -or -not $uri.Host) {
            [System.Windows.Forms.MessageBox]::Show(
                "Enter a valid HTTP or HTTPS ComfyUI address, for example:`r`nhttp://192.168.0.185:8189",
                "Invalid ComfyUI address",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            ) | Out-Null
            return
        }
        $cachePath = [Environment]::ExpandEnvironmentVariables($cacheInput.Text.Trim())
        if (-not $cachePath) {
            [System.Windows.Forms.MessageBox]::Show(
                "Select or enter the H3 Relay cache folder.",
                "Cache folder required",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            ) | Out-Null
            return
        }
        try { $cachePath = [IO.Path]::GetFullPath($cachePath) } catch {
            [System.Windows.Forms.MessageBox]::Show(
                "The cache folder path is invalid.",
                "Invalid cache folder",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            ) | Out-Null
            return
        }

        $lmUrlText = [string]$lmInput.Text.Trim().TrimEnd("/")
        if ($lmUrlText -and $lmUrlText -notmatch "^https?://") { $lmUrlText = "http://" + $lmUrlText }
        $script:config.api_url = $url
        $script:config.cache_path = $cachePath
        $script:config.lm_studio_url = $lmUrlText
        if ([string]$modelInput.Text.Trim()) { $script:config.qwen_model = [string]$modelInput.Text.Trim() }
        $script:config.resource_refresh_seconds = [int]$resourceRefreshInput.Value
        $script:config.cache_refresh_seconds = [int]$cacheRefreshInput.Value
        if (-not (Write-TrayConfig)) { return }
        $script:endpoint = $script:config.api_url.TrimEnd("/") + "/director_studio/h3-relay-cache-status"
        if ($script:config.lm_studio_url) {
            $script:lmEndpointBase = [string]$script:config.lm_studio_url
        } else {
            try {
                $reparsedApiUrl = [Uri]$script:config.api_url
                $script:lmEndpointBase = "http://$($reparsedApiUrl.Host):1234"
            } catch { $script:lmEndpointBase = "" }
        }
        $script:timer.Interval = [int]$script:config.resource_refresh_seconds * 1000
        Update-H3TrayStatus
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    })
    $form.Controls.Add($saveButton)

    $cancelButton = New-Object System.Windows.Forms.Button
    $cancelButton.Text = "Cancel"
    $cancelButton.Location = New-Object System.Drawing.Point(538, 320)
    $cancelButton.Size = New-Object System.Drawing.Size(82, 32)
    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Controls.Add($cancelButton)
    $form.AcceptButton = $saveButton
    $form.CancelButton = $cancelButton
    $form.ShowDialog() | Out-Null
    $form.Dispose()
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [int]$config.resource_refresh_seconds * 1000
$timer.Add_Tick({ Update-H3TrayStatus })
$settingsItem.Add_Click({ Show-TraySettings })
$refreshItem.Add_Click({ Update-H3TrayStatus })
$openComfyItem.Add_Click({ Start-Process $config.api_url })
$openCacheItem.Add_Click({
    $target = [string]$config.cache_path
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        $target = Split-Path -Parent $target
    }
    if (Test-Path -LiteralPath $target -PathType Container) {
        Start-Process explorer.exe -ArgumentList ('"' + $target + '"')
    }
})
$unloadQwenItem.Add_Click({
    Invoke-TrayAction "Unload Qwen" {
        if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
        $instances = Get-QwenLoadedInstances
        if ($instances.Count -eq 0) { throw "no loaded Qwen instance found" }
        foreach ($iid in $instances) {
            Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/v1/models/unload") -Method Post -ContentType "application/json" -Body (@{instance_id = $iid} | ConvertTo-Json) -TimeoutSec 30
        }
    }
})
$loadQwenItem.Add_Click({
    Invoke-TrayAction "Load Qwen" {
        if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
        $body = @{ model = [string]$config.qwen_model; messages = @(@{role = "user"; content = "reply with the single word ok"}); max_tokens = 6 } | ConvertTo-Json -Depth 4
        Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/v1/chat/completions") -Method Post -ContentType "application/json" -Body $body -TimeoutSec 90
    }
})
$freeComfyItem.Add_Click({
    Invoke-TrayAction "Free ComfyUI" {
        Invoke-RestMethod -Uri ($config.api_url.TrimEnd("/") + "/free") -Method Post -ContentType "application/json" -Body (@{unload_models = $true; free_memory = $true} | ConvertTo-Json) -TimeoutSec 30
    }
})
$notify.Add_DoubleClick({ Start-Process $config.api_url })
$context = New-Object System.Windows.Forms.ApplicationContext
$exitItem.Add_Click({
    $timer.Stop()
    $notify.Visible = $false
    $notify.Dispose()
    $context.ExitThread()
})

try {
    Update-H3TrayStatus
    $timer.Start()
    $notify.BalloonTipTitle = "H3 Server Status"
    $notify.BalloonTipText = "Tray monitors Qwen (LM Studio) + ComfyUI; menu can load/unload either side. Double-click opens ComfyUI."
    $notify.ShowBalloonTip(2500)
    [System.Windows.Forms.Application]::Run($context)
} finally {
    $timer.Stop()
    $timer.Dispose()
    $notify.Visible = $false
    $notify.Dispose()
    if ($createdNew) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
