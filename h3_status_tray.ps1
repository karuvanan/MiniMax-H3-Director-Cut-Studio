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
        refresh_seconds = 5
        server_settings_path = ""
    }
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        return $defaults
    }
    try {
        $saved = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if ($saved.api_url) { $defaults.api_url = [string]$saved.api_url }
        if ($saved.cache_path) { $defaults.cache_path = [string]$saved.cache_path }
        if ($saved.refresh_seconds) {
            $defaults.refresh_seconds = [Math]::Max(
                2, [Math]::Min(300, [int]$saved.refresh_seconds)
            )
        }
        if ($saved.server_settings_path) {
            $defaults.server_settings_path = [string]$saved.server_settings_path
        }
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

$config = Read-TrayConfig
$endpoint = $config.api_url.TrimEnd("/") + "/director_studio/h3-relay-cache-status"
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
        $summary = "Cache $cache/100GB | VRAM $vram | DRAM $dram | GPU $gpu | CPU $cpu"
        $statusItem.Text = $summary
        $notify.Text = if ($summary.Length -gt 63) {
            $summary.Substring(0, 63)
        } else { $summary }
        $high = @(
            $resources.vram_percent, $resources.dram_percent,
            $resources.gpu_percent, $resources.cpu_percent
        ) | Where-Object { $null -ne $_ } | Measure-Object -Maximum
        if ([double]$high.Maximum -ge 95 -or [double]$payload.used_bytes -ge 90GB) {
            $notify.Icon = [System.Drawing.SystemIcons]::Error
        } elseif ([double]$high.Maximum -ge 80 -or [double]$payload.used_bytes -ge 70GB) {
            $notify.Icon = [System.Drawing.SystemIcons]::Warning
        } else {
            $notify.Icon = [System.Drawing.SystemIcons]::Information
        }
    } catch {
        $statusItem.Text = "ComfyUI unavailable | Cache/VRAM/DRAM/GPU/CPU N/A"
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
    $form.ClientSize = New-Object System.Drawing.Size(640, 252)
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

    $refreshLabel = New-Object System.Windows.Forms.Label
    $refreshLabel.Text = "Refresh every (seconds)"
    $refreshLabel.Location = New-Object System.Drawing.Point(18, 22)
    $refreshLabel.Size = New-Object System.Drawing.Size(175, 24)
    $form.Controls.Add($refreshLabel)

    $refreshInput = New-Object System.Windows.Forms.NumericUpDown
    $refreshInput.Minimum = 2
    $refreshInput.Maximum = 300
    $refreshInput.Value = [decimal][Math]::Max(2, [Math]::Min(300, [int]$script:config.refresh_seconds))
    $refreshInput.Location = New-Object System.Drawing.Point(202, 19)
    $refreshInput.Size = New-Object System.Drawing.Size(110, 26)
    $form.Controls.Add($refreshInput)

    $apiLabel = New-Object System.Windows.Forms.Label
    $apiLabel.Text = "Monitored ComfyUI URL / IP"
    $apiLabel.Location = New-Object System.Drawing.Point(18, 68)
    $apiLabel.Size = New-Object System.Drawing.Size(190, 24)
    $form.Controls.Add($apiLabel)

    $apiInput = New-Object System.Windows.Forms.TextBox
    $apiInput.Text = [string]$script:config.api_url
    $apiInput.Location = New-Object System.Drawing.Point(202, 65)
    $apiInput.Size = New-Object System.Drawing.Size(418, 26)
    $form.Controls.Add($apiInput)

    $cacheLabel = New-Object System.Windows.Forms.Label
    $cacheLabel.Text = "Monitored cache folder"
    $cacheLabel.Location = New-Object System.Drawing.Point(18, 114)
    $cacheLabel.Size = New-Object System.Drawing.Size(175, 24)
    $form.Controls.Add($cacheLabel)

    $cacheInput = New-Object System.Windows.Forms.TextBox
    $cacheInput.Text = [string]$script:config.cache_path
    $cacheInput.Location = New-Object System.Drawing.Point(202, 111)
    $cacheInput.Size = New-Object System.Drawing.Size(350, 26)
    $form.Controls.Add($cacheInput)

    $browseButton = New-Object System.Windows.Forms.Button
    $browseButton.Text = "Browse..."
    $browseButton.Location = New-Object System.Drawing.Point(560, 109)
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

    $hint = New-Object System.Windows.Forms.Label
    $hint.Text = "Changes apply immediately. Studio and Tray will read the same cache folder."
    $hint.ForeColor = [System.Drawing.Color]::FromArgb(70, 120, 145)
    $hint.Location = New-Object System.Drawing.Point(202, 146)
    $hint.Size = New-Object System.Drawing.Size(418, 36)
    $form.Controls.Add($hint)

    $saveButton = New-Object System.Windows.Forms.Button
    $saveButton.Text = "Save"
    $saveButton.Location = New-Object System.Drawing.Point(446, 199)
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

        $script:config.api_url = $url
        $script:config.cache_path = $cachePath
        $script:config.refresh_seconds = [int]$refreshInput.Value
        if (-not (Write-TrayConfig)) { return }
        $script:endpoint = $script:config.api_url.TrimEnd("/") + "/director_studio/h3-relay-cache-status"
        $script:timer.Interval = [int]$script:config.refresh_seconds * 1000
        Update-H3TrayStatus
        $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $form.Close()
    })
    $form.Controls.Add($saveButton)

    $cancelButton = New-Object System.Windows.Forms.Button
    $cancelButton.Text = "Cancel"
    $cancelButton.Location = New-Object System.Drawing.Point(538, 199)
    $cancelButton.Size = New-Object System.Drawing.Size(82, 32)
    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $form.Controls.Add($cancelButton)
    $form.AcceptButton = $saveButton
    $form.CancelButton = $cancelButton
    $form.ShowDialog() | Out-Null
    $form.Dispose()
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [int]$config.refresh_seconds * 1000
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
    $notify.BalloonTipText = "Tray monitoring is active. Double-click to open ComfyUI."
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
