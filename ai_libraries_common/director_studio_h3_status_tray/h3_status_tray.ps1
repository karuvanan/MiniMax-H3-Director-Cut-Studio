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
        auto_load_qwen_when_free = $true
        # Optional absolute path to codex.exe (auto-resume). Empty = auto-detect.
        codex_exe = ""
        # Leaked-tool-call watchdog: local Qwen/MTP builds sometimes print their tool call as answer
        # text instead of emitting a real tool call, so Codex closes the turn and the chat looks frozen.
        # Watch the Codex rollout logs and queue "continue" by itself. false = disabled.
        watch_leaked_tool_call = $true
        # Empty = %USERPROFILE%\.codex\sessions
        codex_sessions_path = ""
        # A leaked turn must stay silent this long before the tray wakes it (seconds).
        leaked_toolcall_grace_seconds = 45
        # Never wake a thread whose leaked turn is older than this (minutes).
        leaked_toolcall_max_age_minutes = 180
        # Dead-turn watchdog: when the provider refuses a turn ("No models loaded", 503, "This model is
        # not ready", "high demand") Codex closes the turn with error.message set and NO answer, so the
        # chat just sits there until someone types. Once Qwen is back the tray queues 'continue' itself.
        watch_dead_turns = $true
        # A dead turn must stay silent this long before the tray wakes it (seconds).
        dead_turn_grace_seconds = 20
        # Per-thread wake budget. Each attempt doubles the wait (20s, 40s, 80s ... capped at 640s), so
        # 8 attempts still cover ~40 minutes of provider trouble without hammering it in between.
        dead_turn_max_wakes_per_thread = 8
        # Reverse arbiter will hold off unloading Qwen up to this long while another chat's request is
        # still in the air, so the unload cannot kill it mid-flight (seconds; 0 = never defer).
        defer_unload_for_active_turn_seconds = 150
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
        if ($saved.codex_exe) { $defaults.codex_exe = [string]$saved.codex_exe }
        if ($null -ne $saved.auto_load_qwen_when_free) {
            $defaults.auto_load_qwen_when_free = [bool]$saved.auto_load_qwen_when_free
        }
        if ($null -ne $saved.watch_leaked_tool_call) {
            $defaults.watch_leaked_tool_call = [bool]$saved.watch_leaked_tool_call
        }
        if ($saved.codex_sessions_path) { $defaults.codex_sessions_path = [string]$saved.codex_sessions_path }
        if ($saved.leaked_toolcall_grace_seconds) {
            $defaults.leaked_toolcall_grace_seconds = [Math]::Max(
                15, [Math]::Min(600, [int]$saved.leaked_toolcall_grace_seconds)
            )
        }
        if ($saved.leaked_toolcall_max_age_minutes) {
            $defaults.leaked_toolcall_max_age_minutes = [Math]::Max(
                5, [Math]::Min(1440, [int]$saved.leaked_toolcall_max_age_minutes)
            )
        }
        if ($null -ne $saved.watch_dead_turns) {
            $defaults.watch_dead_turns = [bool]$saved.watch_dead_turns
        }
        if ($saved.dead_turn_grace_seconds) {
            $defaults.dead_turn_grace_seconds = [Math]::Max(
                10, [Math]::Min(600, [int]$saved.dead_turn_grace_seconds)
            )
        }
        if ($saved.dead_turn_max_wakes_per_thread) {
            $defaults.dead_turn_max_wakes_per_thread = [Math]::Max(
                1, [Math]::Min(50, [int]$saved.dead_turn_max_wakes_per_thread)
            )
        }
        if ($null -ne $saved.defer_unload_for_active_turn_seconds) {
            $defaults.defer_unload_for_active_turn_seconds = [Math]::Max(
                0, [Math]::Min(900, [int]$saved.defer_unload_for_active_turn_seconds)
            )
        }
    } catch {}
    return $defaults
}

function Show-H3MessageBox([string]$Text, [string]$Caption, [string]$Icon = "Warning") {
    try {
        $iconEnum = if ($Icon -eq "Error") { [System.Windows.Forms.MessageBoxIcon]::Error } else { [System.Windows.Forms.MessageBoxIcon]::Warning }
        [void][System.Windows.Forms.MessageBox]::Show($Text, $Caption, [System.Windows.Forms.MessageBoxButtons]::OK, $iconEnum)
    } catch {}
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
        Show-H3MessageBox "Settings could not be saved.`r`n`r`n$($_.Exception.Message)" "H3 Server Status Settings" Error
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

function Get-LmOriginBase([string]$Url) {
    # Settings keep "/v1" for compatibility; LM/Strata management routes live at the origin, so strip it.
    $text = [string]$Url
    if (-not $text) { return "" }
    $text = $text.TrimEnd("/")
    while ($text -match '(?i)/v1$') { $text = $text.Substring(0, $text.Length - 3).TrimEnd("/") }
    return $text
}

function Write-TrayActionLog([string]$Message) {
    # Audit trail: without it nobody can tell what the tray actually did, or when.
    try {
        $line = "{0} [TRAY] {1}" -f ([DateTime]::Now.ToString("yyyy-MM-dd HH:mm:ss")), $Message
        Add-Content -LiteralPath (Join-Path $PSScriptRoot "h3_tray_actions.log") -Value $line -Encoding UTF8
    } catch {}
}

$script:lmHostKind = $null
# Round 113: the last dialect this tray actually proved.  Measured on 2026-11-10 against
# http://127.0.0.1:47831: /api/v1/models -> 404, /api/models -> 200, /v1/models -> 200, so this host is
# Strata and the LM Studio route is a *guaranteed* 404 for it.  The old code answered "unknown" by
# returning $false, which sent Get-QwenLoadedInstances down that guaranteed-404 route and reported
# "Qwen unloaded" - every owner flip at 21:32/21:37/21:39/22:09 on 2026-11-10 was that, a probe hiccup
# under render load, with no unload and no load in the log.
$script:lmHostKindLast = $null
$script:lmHostKindProbedAt = [DateTime]::MinValue
$script:lmHostProbeWarnedAt = [DateTime]::MinValue

function Test-StrataHost {
    # Cached host fingerprint: LM Studio answers /api/v1/models, Strata answers /api/models and 404s on /api/v1/models.
    # A dialect that was once proved is kept for the life of the tray (Settings... and a restart clear it on
    # purpose, lines that already reset $script:lmHostKind); while undecided, the last proved dialect is
    # served and re-probing is throttled so a 5-second enforcer tick cannot thrash the answer.
    if ($script:lmHostKind) { return ($script:lmHostKind -eq "strata") }
    if (-not $script:lmEndpointBase) { return $false }
    if (([DateTime]::Now - $script:lmHostKindProbedAt).TotalSeconds -lt 30) {
        return ($script:lmHostKindLast -eq "strata")
    }
    $script:lmHostKindProbedAt = [DateTime]::Now
    # 8 seconds, not 4: the management routes answer slowly while an H3 take is saturating the box, and
    # that is exactly when the tray must not change its mind about who owns the GPU.
    try {
        Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/v1/models") -Method Get -TimeoutSec 8 | Out-Null
        $script:lmHostKind = "lmstudio"
        $script:lmHostKindLast = "lmstudio"
        return $false
    } catch {}
    try {
        Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/models") -Method Get -TimeoutSec 8 | Out-Null
        $script:lmHostKind = "strata"
        $script:lmHostKindLast = "strata"
        return $true
    } catch {}
    # Both dialect probes failed this tick: keep serving the last dialect proved, so the catalogue query
    # still goes to a route that exists. Callers treat a failed catalogue read as unknown, not as unloaded.
    if (([DateTime]::Now - $script:lmHostProbeWarnedAt).TotalSeconds -ge 120) {
        $script:lmHostProbeWarnedAt = [DateTime]::Now
        Write-TrayActionLog ("host dialect undecided: holding {0} (both probe routes failed)" -f `
            $(if ($script:lmHostKindLast) { $script:lmHostKindLast } else { "nothing proved yet" }))
    }
    return ($script:lmHostKindLast -eq "strata")
}

function Get-QwenLoadedInstances {
    if (-not $script:lmEndpointBase) { return @() }
    try {
        if (Test-StrataHost) {
            # Strata: GET /v1/models lists *loaded* instances; the unload handle is meta.instanceId.
            $needleStrata = [string]$config.qwen_key_filter
            if (-not $needleStrata) { return @() }
            $cat = Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/v1/models") -Method Get -TimeoutSec 10
            $found = @()
            foreach ($model in @($cat.data)) {
                if ($null -eq $model) { continue }
                $hay = @([string]$model.id)
                foreach ($alias in @($model.meta.aliases)) { $hay += [string]$alias }
                $hay += [string]$model.meta.label
                $matched = $false
                foreach ($h in $hay) { if ($h -match [regex]::Escape($needleStrata)) { $matched = $true; break } }
                if (-not $matched) { continue }
                if ($null -ne $model.meta -and $model.meta.instanceId) { $found += [string]$model.meta.instanceId }
            }
            return $found
        }
        $catalog = Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/v1/models") -Method Get -TimeoutSec 10
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
    } catch {
        # Catalog query failure (LM down / transient): $null keeps FREE distinguishable from a confirmed empty list.
        return $null
    }
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
        Show-H3MessageBox "$Title failed:`r`n$($_.Exception.Message)" "H3 Status Tray"
    }
}

$config = Read-TrayConfig
$endpoint = $config.api_url.TrimEnd("/") + "/director_studio/h3-relay-cache-status"
$lmEndpointBase = Get-LmOriginBase ([string]$config.lm_studio_url)
if (-not $lmEndpointBase) {
    try {
        $parsedApiUrl = [Uri]$config.api_url
        $lmEndpointBase = "http://$($parsedApiUrl.Host):1234"
    } catch { $lmEndpointBase = "" }
}
$script:lmHostKind = $null
Write-TrayActionLog ("startup: origin={0} model={1} filter={2} autoload={3}" -f $lmEndpointBase, $config.qwen_model, $config.qwen_key_filter, $config.auto_load_qwen_when_free)
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
$autoLoadItem = New-Object System.Windows.Forms.ToolStripMenuItem
$autoLoadItem.Text = "Auto-arbitrate Qwen vs ComfyUI (load ~20s after free, unload when H3 busy ~15s)"
$autoLoadItem.Checked = [bool]$config.auto_load_qwen_when_free
$menu.Items.Add($autoLoadItem) | Out-Null
$watchdogItem = New-Object System.Windows.Forms.ToolStripMenuItem
# Local Qwen/MTP builds sometimes print the tool call as answer text; the watchdog queues "continue" for
# those turns. Some users want the chat to stop on purpose, so make it switchable and show its state here.
$watchdogItem.Text = "Tool-call watchdog (auto-continue chats frozen on a printed tool call)"
$watchdogItem.Checked = [bool]$config.watch_leaked_tool_call
$menu.Items.Add($watchdogItem) | Out-Null
$deadTurnItem = New-Object System.Windows.Forms.ToolStripMenuItem
$deadTurnItem.Text = "Dead-turn watchdog (auto-continue chats killed by model unload / provider error)"
$deadTurnItem.Checked = [bool]$config.watch_dead_turns
$menu.Items.Add($deadTurnItem) | Out-Null
$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator)) | Out-Null
$restartItem = New-Object System.Windows.Forms.ToolStripMenuItem
$restartItem.Text = "Restart Tray (apply script edits)"
$menu.Items.Add($restartItem) | Out-Null
$exitItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exitItem.Text = "Exit H3 Status Tray"
$menu.Items.Add($exitItem) | Out-Null
$notify.ContextMenuStrip = $menu

$script:lastOwnerKey = $null
$script:freeSince = $null
$script:autoLoadInFlight = $false
$script:suppressAutoLoadUntil = [DateTime]::MinValue
$script:busySince = $null
$script:autoUnloadInFlight = $false
# codex.exe discovery cache + rate limit for the "not found" warning (the enforcer ticks every 5s).
$script:codexCliPath = $null
$script:codexCliMissingWarnedAt = [DateTime]::MinValue
# Stale-script watch: PowerShell keeps the script text it read at launch, so editing this .ps1 never
# reaches a running tray. Remember path + mtime at start and flag the mismatch in the menu.
$script:trayScriptPath = if ($PSCommandPath) { $PSCommandPath } elseif ($MyInvocation.MyCommand.Path) { [string]$MyInvocation.MyCommand.Path } else { "" }
$script:trayScriptMtimeAtStart = if ($script:trayScriptPath -and (Test-Path -LiteralPath $script:trayScriptPath -PathType Leaf)) { (Get-Item -LiteralPath $script:trayScriptPath).LastWriteTime } else { $null }
$script:trayStaleMarkerShown = $false
$script:trayStaleWarnedAt = [DateTime]::MinValue
# Leaked-tool-call watchdog: dedupe table ("threadId|turnId" -> unix ts) + one-wake-per-tick throttle.
$script:leakedWakeState = @{}
$script:leakedWatchInFlight = $false
$script:leakedStateLoaded = $false
$script:autoResumeQueuedAt = [DateTime]::MinValue
# Per-thread "wake budget already spent" warning throttle + unload-defer log throttle.
$script:deadTurnBudgetWarnedAt = @{}
$script:deferUnloadLoggedAt = [DateTime]::MinValue
# Throttle for "stale comfy claim released" so a crashed driver cannot flood the log.
$script:staleClaimReleasedAt = [DateTime]::MinValue

function Notify-OwnerChange([string]$ownerKey) {
    # "UNKNOWN" means the catalogue could not be read this tick.  It is not an owner: reporting it would
    # both spam the audit log and invite the auto-loader, which treats FREE as a GPU up for grabs.
    if ($ownerKey -eq "UNKNOWN") { return }
    if ($script:lastOwnerKey -ne $null -and $script:lastOwnerKey -ne $ownerKey) {
        Write-TrayActionLog "owner change: $script:lastOwnerKey -> $ownerKey"
        $msg = if ($ownerKey -eq "QWEN") { "Qwen loaded - agent owns GPU (H3 needs unload-qwen first)" } else { "Qwen unloaded - GPU free for H3" }
        try {
            $notify.BalloonTipTitle = "H3 Tray: owner changed"
            $notify.BalloonTipText = $msg
            $notify.ShowBalloonTip(4000)
        } catch {}
    }
    $script:lastOwnerKey = $ownerKey
}

function Test-ComfyQueueIdle {
    try {
        $q = Invoke-RestMethod -Uri ($config.api_url.TrimEnd("/") + "/api/queue") -Method Get -TimeoutSec 4
        return (@($q.queue_running).Count + @($q.queue_pending).Count) -eq 0
    } catch {}
    return $null
}

function Invoke-QwenAutoLoad {
    if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
    $model = [string]$config.qwen_model
    if (Test-StrataHost) {
        # Strata load is an async job (HTTP 202). Blocking here is deliberate: it stops the next tick from firing a second load mid warm-up.
        $started = [DateTime]::Now
        $loadBody = @{ kind = "load"; args = @{ model = $model } } | ConvertTo-Json -Depth 4
        Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/native/operations") -Method Post -ContentType "application/json" -Body $loadBody -TimeoutSec 30 | Out-Null
        Write-TrayActionLog "load requested: $model (Strata /api/native/operations)"
        $deadline = $started.AddSeconds(180)
        while ([DateTime]::Now -lt $deadline) {
            Start-Sleep -Seconds 3
            $loaded = Get-QwenLoadedInstances
            if ($null -ne $loaded -and $loaded.Count -gt 0) {
                Write-TrayActionLog ("load confirmed: {0} -> {1} after {2:0}s" -f $model, ($loaded -join ","), ([DateTime]::Now - $started).TotalSeconds)
                return
            }
        }
        Write-TrayActionLog "load TIMED OUT after 180s: $model"
        throw "timed out 180s waiting for $model to load (Strata)"
    }
    $body = @{ model = $model; messages = @(@{role = "user"; content = "reply with the single word ok"}); max_tokens = 6 } | ConvertTo-Json -Depth 4
    Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/v1/chat/completions") -Method Post -ContentType "application/json" -Body $body -TimeoutSec 90 | Out-Null
    Write-TrayActionLog "load requested: $model (LM Studio chat ping)"
}
function Get-ComfyClaim {
    # Driver-written phase claim (comfy_claim.json): {"ts": <unix s>, "note": "phase"|"keep-qwen"}.
    $claimPath = Join-Path $PSScriptRoot "comfy_claim.json"
    try {
        if (-not (Test-Path -LiteralPath $claimPath)) { return $null }
        $rawText = Get-Content -LiteralPath $claimPath -Raw
        if (-not $rawText) { return $null }
        $claim = $rawText | ConvertFrom-Json
        if ($null -eq $claim.ts) { return $null }
        return $claim
    } catch {}
    return $null
}

function Test-ActiveRunRunning([int]$MaxAgeSeconds = 900) {
    # active_run.json is rewritten by the driver; "running" older than the TTL means the
    # process died without writing its terminal status, so it must not hold the GPU forever.
    $run = Get-ActiveRun
    if ($null -eq $run) { return $false }
    if ([string]$run.status -ne "running") { return $false }
    try {
        $startedAt = [DateTimeOffset]::FromUnixTimeSeconds([double]$run.ts).UtcDateTime
        return (([DateTime]::UtcNow - $startedAt).TotalSeconds -lt $MaxAgeSeconds)
    } catch {}
    return $false
}

function Release-StaleComfyClaim([string]$why) {
    if (([DateTime]::Now - $script:staleClaimReleasedAt).TotalSeconds -lt 60) { return }
    $script:staleClaimReleasedAt = [DateTime]::Now
    try {
        Remove-Item -LiteralPath (Join-Path $PSScriptRoot "comfy_claim.json") -Force -ErrorAction SilentlyContinue
        Write-TrayActionLog ("stale comfy claim released: $why")
    } catch {
        Write-TrayActionLog ("stale comfy claim NOT released: $($_.Exception.Message)")
    }
}

function Test-ComfyClaimActive([int]$GraceSeconds = 120, $QueueIdle = $null) {
    # Liveness, not age. The driver clears comfy_claim.json when a run ends, so a leftover
    # claim means the run died mid-phase. The old rule trusted the file for 5400s, which
    # parked Qwen for 90 minutes (measured 2026-11-10: unload 12:42:47 -> reload 14:13:03,
    # exactly 12:42:47 + 5400s + the ~15s free window). A claim now holds the GPU only while
    # the render it guards is plausibly still running: it is inside the inter-phase grace,
    # ComfyUI really has queue work, or a fresh active_run says a job is live.
    $claim = Get-ComfyClaim
    if ($null -eq $claim) { return $false }
    if ([string]$claim.note -like "keep*") {
        # --keep-qwen means coexistence is intentional: it must never stop Qwen from loading.
        return $false
    }
    $claimAge = -1.0
    try {
        $claimedAt = [DateTimeOffset]::FromUnixTimeSeconds([double]$claim.ts).UtcDateTime
        $claimAge = ([DateTime]::UtcNow - $claimedAt).TotalSeconds
    } catch {}
    if ($claimAge -ge 0 -and $claimAge -lt $GraceSeconds) { return $true }
    if ($QueueIdle -eq $false) { return $true }
    if (Test-ActiveRunRunning) { return $true }
    Release-StaleComfyClaim ("note=$([string]$claim.note) age=$($claimAge.ToString('0'))s, ComfyUI queue idle, no live job")
    return $false
}

function Get-ActiveRun {
    # Driver-written run registry (active_run.json): {"ts","status":"running|crashed|completed|resumed","thread_id","job"}.
    $runPath = Join-Path $PSScriptRoot "active_run.json"
    try {
        if (-not (Test-Path -LiteralPath $runPath)) { return $null }
        $rawText = Get-Content -LiteralPath $runPath -Raw
        if (-not $rawText) { return $null }
        $run = $rawText | ConvertFrom-Json
        if ($null -eq $run.ts) { return $null }
        return $run
    } catch {}
    return $null
}

function Resolve-CodexCli {
    # Find codex.exe. Order: explicit override (settings/env) -> PATH -> on-disk scan.
    # PATH only works when the tray is a child of the Codex app: the app injects its bin folder into
    # its own child processes, but it is NOT in the persisted user/system PATH. A tray started from
    # Explorer or start_h3_status_tray.bat therefore must be able to find codex.exe on disk.
    if ($script:codexCliPath -and (Test-Path -LiteralPath $script:codexCliPath -PathType Leaf)) {
        return $script:codexCliPath
    }
    $script:codexCliPath = $null
    foreach ($override in @([string]$config.codex_exe, [string]$env:H3_CODEX_EXE)) {
        if ($override -and (Test-Path -LiteralPath $override -PathType Leaf)) {
            $script:codexCliPath = $override
            Write-CodexCliResolved
            return $script:codexCliPath
        }
    }
    try {
        $cmd = Get-Command codex -ErrorAction SilentlyContinue
        if ($cmd -and (Test-Path -LiteralPath ([string]$cmd.Source) -PathType Leaf)) {
            $script:codexCliPath = [string]$cmd.Source
            Write-CodexCliResolved
            return $script:codexCliPath
        }
    } catch {}
    $script:codexCliPath = Find-CodexCliOnDisk
    if ($script:codexCliPath) { Write-CodexCliResolved }
    return $script:codexCliPath
}

function Write-CodexCliResolved {
    # One line per tray process: makes "why did auto-resume never fire" answerable from the log alone.
    if ($script:codexCliResolvedLogged) { return }
    $script:codexCliResolvedLogged = $true
    Write-TrayActionLog ("codex CLI resolved: {0}" -f $script:codexCliPath)
}

function Find-CodexCliOnDisk {
    # The desktop install lives in %LOCALAPPDATA%\OpenAI\Codex\bin\<install-id>\codex.exe and the
    # folder name is a hash, not a version - so sort candidate executables by file time instead.
    $roots = @()
    if ($env:LOCALAPPDATA) {
        $roots += (Join-Path $env:LOCALAPPDATA "OpenAI\Codex\bin")
        $roots += (Join-Path $env:LOCALAPPDATA "Programs\Codex")
    }
    if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles "Codex") }
    $candidates = @()
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        foreach ($exe in (Get-ChildItem -LiteralPath $root -Filter "codex.exe" -File -Recurse -Depth 3 -ErrorAction SilentlyContinue)) {
            $candidates += $exe
        }
    }
    if ($candidates.Count -eq 0) { return $null }
    return [string](($candidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName)
}

function Invoke-CodexKeepAlive {
    # Best-effort daemon ping so the Codex app-server keeps this thread's context loaded (user plan #2).
    # This build (codex-cli 0.163.x) has no 'status' subcommand, so the call is a plain no-op that still
    # spawns a process every 60s - opt in with H3_CODEX_KEEPALIVE=1 once a build actually supports it.
    if ($env:H3_CODEX_KEEPALIVE -ne "1") { return }
    try {
        $codexCli = Resolve-CodexCli
        if ($codexCli) {
            $proc = Start-Process -FilePath $codexCli -ArgumentList @("status", "--ping") -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue
            if ($proc) { [void]$proc.WaitForExit(5000) }
        }
    } catch {}
}

function Invoke-AutoResume {
    # Dead-thread auto-wake: the driver crashed mid-run after unloading Qwen (status=crashed), or it
    # finished successfully while our turn was already dead (status=completed, 90s grace period). Once
    # the tray's forward-enforcer has reloaded Qwen, queue a resume message into that same Codex
    # thread (codex.exe queue) - no human typing needed.
    if (-not $config.auto_load_qwen_when_free) { return }
    $run = Get-ActiveRun
    if ($null -eq $run) { return }
    $status = [string]$run.status
    if ($status -eq "running") {
        # Stale 'running' (driver hard-killed / power loss without reporting): treat as crashed after 2h.
        try {
            $ageSeconds = ([DateTime]::UtcNow - [DateTimeOffset]::FromUnixTimeSeconds([double]$run.ts).UtcDateTime).TotalSeconds
            if ($ageSeconds -lt 7200) { return }
            $status = "crashed"
        } catch { return }
    }
    if ($status -eq "completed") {
        # Success handoff: a live agent turn keeps going on its own within seconds, so only wake the
        # thread after a 90s grace period (a dead turn never resumes and gets woken by this message).
        try {
            $ageSeconds = ([DateTime]::UtcNow - [DateTimeOffset]::FromUnixTimeSeconds([double]$run.ts).UtcDateTime).TotalSeconds
            if ($ageSeconds -lt 90) { return }
        } catch { return }
    }
    if (($status -ne "crashed") -and ($status -ne "completed")) { return }
    $threadId = [string]$run.thread_id
    if (-not $threadId) { return }   # run not started from a Codex thread; nothing to wake
    $instances = Get-QwenLoadedInstances
    if ($null -eq $instances -or $instances.Count -eq 0) { return }   # Qwen must be loaded first
    $codexCli = Resolve-CodexCli
    if (-not $codexCli) {
        # Rate limited: without this the log got one identical line per 5s tick forever.
        if (([DateTime]::Now - $script:codexCliMissingWarnedAt).TotalSeconds -ge 300) {
            $script:codexCliMissingWarnedAt = [DateTime]::Now
            Write-TrayActionLog "auto-resume skipped: codex.exe not found (status=$status thread=$threadId) - set codex_exe in tray-settings.json or H3_CODEX_EXE"
            try {
                $notify.BalloonTipTitle = "H3 Tray: auto-resume"
                $notify.BalloonTipText = "driver finished but codex.exe not found; send 'continue' manually"
                $notify.ShowBalloonTip(6000)
            } catch {}
        }
        return
    }
    try {
        if ($status -eq "completed") {
            $resumeText = "Tray auto-resume: staged driver completed job " + [string]$run.job + " successfully (see manifest). Qwen was reloaded by the tray. Continue from where you stopped; only report again if the result was not already delivered."
        } else {
            $resumeText = "Tray auto-resume: staged driver crashed on job " + [string]$run.job + ". Qwen was reloaded by the tray. Continue from where you stopped."
        }
        $queueOutput = (& $codexCli queue --thread $threadId --message $resumeText 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw "codex queue exit $LASTEXITCODE : $queueOutput" }
        Write-TrayActionLog "auto-resume queued into thread $threadId (status was $status)"
        # Remembered so the leaked-tool-call watchdog does not stack a second message onto the same turn.
        $script:autoResumeQueuedAt = [DateTime]::Now
        $run.status = "resumed"
        $run.ts = [DateTimeOffset]::Now.ToUnixTimeSeconds()
        ($run | ConvertTo-Json) | Set-Content -LiteralPath (Join-Path $PSScriptRoot "active_run.json") -Encoding UTF8
        try {
            $notify.BalloonTipTitle = "H3 Tray: auto-resume"
            $notify.BalloonTipText = ("driver {0} -> queued continue into thread " -f $status) + $threadId.Substring(0, [Math]::Min(8, $threadId.Length))
            $notify.ShowBalloonTip(6000)
        } catch {}
    } catch {
        # Leave the current status (crashed/completed) so the next tick retries (the app-server daemon may be busy).
        Write-TrayActionLog "auto-resume FAILED: $($_.Exception.Message) - retrying next tick"
        try {
            $notify.BalloonTipTitle = "H3 Tray: auto-resume failed"
            $notify.BalloonTipText = "$($_.Exception.Message) - retrying next tick"
            $notify.ShowBalloonTip(6000)
        } catch {}
    }
}

function Get-LeakedToolCallSessionsDir {
    # Where Codex writes its rollout logs. Settings override -> %USERPROFILE%\.codex\sessions.
    $configured = [string]$config.codex_sessions_path
    if ($configured -and (Test-Path -LiteralPath $configured -PathType Container)) { return $configured }
    $fallback = Join-Path $env:USERPROFILE ".codex\sessions"
    if (Test-Path -LiteralPath $fallback -PathType Container) { return $fallback }
    return ""
}

function Get-LeakedToolCallState {
    # "threadId|turnId" -> unix ts, so one leaked turn is only ever woken once (the enforcer ticks every 5s).
    if ($script:leakedStateLoaded) { return }
    $script:leakedStateLoaded = $true
    try {
        $statePath = Join-Path $PSScriptRoot "leaked_toolcall_state.json"
        if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { return }
        $raw = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8
        if (-not $raw) { return }
        foreach ($prop in ($raw | ConvertFrom-Json).PSObject.Properties) {
            $script:leakedWakeState[[string]$prop.Name] = [double]$prop.Value
        }
    } catch {}
}

function Save-LeakedToolCallState {
    # Rate limited: the enforcer would otherwise rewrite this file every 5s. Also drops keys after 24h.
    if ($null -eq $script:leakedStateSavedAt) { $script:leakedStateSavedAt = [DateTime]::MinValue }
    if (([DateTime]::Now - $script:leakedStateSavedAt).TotalSeconds -lt 30) { return }
    try {
        $cutoff = [DateTimeOffset]::Now.AddHours(-24).ToUnixTimeSeconds()
        $kept = [ordered]@{}
        foreach ($key in @($script:leakedWakeState.Keys)) {
            if ([double]$script:leakedWakeState[$key] -ge $cutoff) { $kept[[string]$key] = $script:leakedWakeState[$key] }
        }
        $kept | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot "leaked_toolcall_state.json") -Encoding UTF8
        $script:leakedStateSavedAt = [DateTime]::Now
    } catch {}
}

function Test-LeakedToolCallText([string]$Text) {
    # The leak is the model's raw tool-call markup sitting in the ANSWER channel. An answer that merely
    # quotes that markup keeps it inside a code fence, and real prose never looks like this, so both are excluded.
    if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
    $trimmed = $Text.Trim()
    # The real gate is the 24-char prefix below, so the length ceiling only has to keep runaway dumps out.
    # 4000 was too tight: a leaked read_code/apply_patch call whose JSON arguments are long is still a leak.
    if ($trimmed.Length -gt 20000) { return $false }
    if ($trimmed.IndexOf('```') -ge 0) { return $false }
    $head = $trimmed.Substring(0, [Math]::Min(24, $trimmed.Length)).ToLowerInvariant()
    foreach ($prefix in @('<tool_call', '<tool_use', '<toolcall', '<function', '<antml', '<|')) {
        if ($head.StartsWith($prefix)) { return $true }
    }
    # Sometimes the model writes a sentence first and only then dumps the call.
    if ($trimmed.ToLowerInvariant().Contains('<tool_call') -and $trimmed.TrimEnd().EndsWith('</function>')) { return $true }
    return $false
}

function Test-DeadProviderTurn([string]$ErrorText, [string]$AnswerText) {
    # A turn that FAILED at the provider is recorded as task_complete with error.message set and
    # last_agent_message null. That pair is deterministic - the turn died rather than finished, and the
    # chat is waiting for someone to press continue. The tray used to guess this from idle GPU usage.
    if ([string]::IsNullOrWhiteSpace($ErrorText)) { return $false }
    if (-not [string]::IsNullOrWhiteSpace($AnswerText)) { return $false }
    $lower = $ErrorText.ToLowerInvariant()
    foreach ($skip in @('interrupt', 'cancel', 'abort')) {
        if ($lower.Contains($skip)) { return $false }   # the user stopped it on purpose
    }
    return $true
}

function Read-JsonlTail([string]$Path, [int]$MaxBytes) {
    # Codex keeps the rollout open for writing, so it must be opened with FileShare ReadWrite -
    # a plain Get-Content throws "The process cannot access the file because it is being used by another process".
    $collected = New-Object System.Collections.Generic.List[string]
    $fs = $null
    try {
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $start = [Math]::Max(0, $fs.Length - $MaxBytes)
        [void]$fs.Seek($start, [System.IO.SeekOrigin]::Begin)
        $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true)
        $fs = $null   # the reader owns the stream from here (its Close() disposes it)
        if ($start -gt 0) { [void]$reader.ReadLine() }   # drop the half-line the seek landed on
        while ($null -ne ($line = $reader.ReadLine())) {
            if ($line.Trim().Length -gt 0) { $collected.Add($line) }
            if ($collected.Count -gt 40) { $collected.RemoveAt(0) }
        }
        $reader.Close()
    } catch {} finally {
        if ($null -ne $fs) { try { $fs.Dispose() } catch {} }
    }
    return , @($collected)
}

function Get-LeakedCodexThreads {
    # One record per Codex log whose LAST finished turn (task_complete) is the agent message.
    # Returns ThreadId / TurnId / Ts (UTC, when the turn ended) / Written (UTC, log activity) / Text.
    $found = @()
    $dir = Get-LeakedToolCallSessionsDir
    if (-not $dir) { return $found }
    $cutoffUtc = ([DateTime]::UtcNow - [TimeSpan]::FromMinutes([double]$config.leaked_toolcall_max_age_minutes))
    $files = @()
    try {
        $files = @(Get-ChildItem -LiteralPath $dir -Recurse -Filter "rollout-*.jsonl" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -ge $cutoffUtc } |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 6)
    } catch { return $found }
    foreach ($file in $files) {
        # rollout-2026-10-26T23-09-57-<threadId>[_<sessionTurnId>].jsonl
        if ($file.Name -notmatch '^rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-(?<t>[0-9a-fA-F\-]{36})') { continue }
        $threadId = [string]$matches['t']
        $lines = Read-JsonlTail $file.FullName 196608
        for ($i = $lines.Count - 1; $i -ge 0; $i--) {
            $obj = $null
            try { $obj = $lines[$i] | ConvertFrom-Json } catch { continue }
            if ($null -eq $obj -or $null -eq $obj.payload) { continue }
            if ([string]$obj.payload.type -ne "task_complete") { continue }
            $turnId = [string]$obj.payload.root_turn_id
            if (-not $turnId) { $turnId = [string]$obj.payload.turn_id }
            # error is an object ({"message": "..."}) on provider failures, a bare string on others.
            $errText = ""
            try {
                if ($null -ne $obj.payload.error) {
                    if ($obj.payload.error.message) { $errText = [string]$obj.payload.error.message }
                    else { $errText = [string]$obj.payload.error }
                }
            } catch {}
            $endedAt = $file.LastWriteTimeUtc
            try {
                $endedAt = ([DateTime]::Parse([string]$obj.timestamp, [System.Globalization.CultureInfo]::InvariantCulture)).ToUniversalTime()
            } catch {}
            $found += [pscustomobject]@{
                ThreadId = $threadId
                TurnId = $turnId
                Ts = $endedAt
                Written = $file.LastWriteTimeUtc
                Text = [string]$obj.payload.last_agent_message
                Error = $errText
            }
            break   # only the newest completed turn of that thread matters
        }
    }
    return $found
}

function Get-CodexTurnsInFlight {
    # How many Codex chats have a turn that STARTED and has not COMPLETED yet. The reverse arbiter asks
    # this before unloading Qwen: cutting a chat whose request is still travelling is exactly what made
    # it die with "No models loaded" / 503 / "high demand" dozens of times.
    # The thread running the H3 job is skipped - its agent is parked inside the driver, not mid-request.
    $activeThread = ""
    $activeRun = Get-ActiveRun
    if ($null -ne $activeRun) { $activeThread = [string]$activeRun.thread_id }
    $dir = Get-LeakedToolCallSessionsDir
    if (-not $dir) { return 0 }
    $cutoffUtc = ([DateTime]::UtcNow - [TimeSpan]::FromMinutes(30))
    $files = @()
    try {
        $files = @(Get-ChildItem -LiteralPath $dir -Recurse -Filter "rollout-*.jsonl" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -ge $cutoffUtc } |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 8)
    } catch { return 0 }
    $found = 0
    foreach ($file in $files) {
        if ($file.Name -notmatch '^rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-(?<t>[0-9a-fA-F\-]{36})') { continue }
        if ($activeThread -and ([string]$matches['t'] -eq $activeThread)) { continue }
        $lines = Read-JsonlTail $file.FullName 49152
        $startedAt = $null
        $endedAt = $null
        foreach ($line in $lines) {
            # Cheap pre-filter: these three event types are the only ones that matter, and the files are huge.
            if ($line.IndexOf('"task_started"') -lt 0 -and $line.IndexOf('"task_complete"') -lt 0 -and $line.IndexOf('"turn_aborted"') -lt 0) { continue }
            $obj = $null
            try { $obj = $line | ConvertFrom-Json } catch { continue }
            if ($null -eq $obj -or $null -eq $obj.payload) { continue }
            $type = [string]$obj.payload.type
            if ($type -ne "task_started" -and $type -ne "task_complete" -and $type -ne "turn_aborted") { continue }
            $stamp = $null
            try { $stamp = ([DateTime]::Parse([string]$obj.timestamp, [System.Globalization.CultureInfo]::InvariantCulture)).ToUniversalTime() } catch {}
            if ($null -eq $stamp) { continue }
            if ($type -eq "task_started") {
                if ($null -eq $startedAt -or $stamp -gt $startedAt) { $startedAt = $stamp }
            } else {
                if ($null -eq $endedAt -or $stamp -gt $endedAt) { $endedAt = $stamp }
            }
        }
        if ($null -ne $startedAt -and ($null -eq $endedAt -or $startedAt -gt $endedAt)) { $found++ }
    }
    return $found
}

function Invoke-LeakedToolCallWatch {
    # A local Qwen/MTP build sometimes prints its tool call as answer text instead of issuing it, so
    # Codex has nothing to execute and closes the turn: the chat looks frozen, but it really did finish.
    # Nothing is lost - one queued message restarts it, which is what the user used to type by hand.
    # Dead turns (provider errors) ride the same scanner, because they show up in the same records.
    if (-not $config.watch_leaked_tool_call -and -not $config.watch_dead_turns) { return }
    if ($script:leakedWatchInFlight) { return }
    if ($config.auto_load_qwen_when_free) {
        $instances = Get-QwenLoadedInstances
        if ($null -eq $instances -or $instances.Count -eq 0) { return }   # wake it only once its model is back
    }
    if (([DateTime]::Now - $script:autoResumeQueuedAt).TotalSeconds -lt 120) { return }   # auto-resume owns that turn
    $codexCli = Resolve-CodexCli
    if (-not $codexCli) { return }
    Get-LeakedToolCallState
    $script:leakedWatchInFlight = $true
    try {
        $leakGrace = [TimeSpan]::FromSeconds([double]$config.leaked_toolcall_grace_seconds)
        $maxAge = [TimeSpan]::FromMinutes([double]$config.leaked_toolcall_max_age_minutes)
        $woke = 0
        foreach ($hit in @(Get-LeakedCodexThreads)) {
            if ($woke -ge 2) { break }   # never flood the daemon inside one tick
            if (([DateTime]::UtcNow - $hit.Ts) -gt $maxAge) { continue }
            $isLeak = ($config.watch_leaked_tool_call -and (Test-LeakedToolCallText $hit.Text))
            $isDead = ($config.watch_dead_turns -and (Test-DeadProviderTurn $hit.Error $hit.Text))
            if (-not ($isLeak -or $isDead)) { continue }
            $kind = if ($isDead) { "dead-turn" } else { "leaked-tool-call" }
            # Earlier wakes for this thread come first: a dead turn backs off exponentially, so a
            # provider that is sick for 40 minutes is probed ~8 times instead of 120.
            $wakes = 0
            foreach ($seen in @($script:leakedWakeState.Keys)) {
                if (([string]$seen).StartsWith($hit.ThreadId + "|")) { $wakes++ }
            }
            $graceSeconds = [double]$config.leaked_toolcall_grace_seconds
            if ($isDead) { $graceSeconds = [double]$config.dead_turn_grace_seconds * [Math]::Pow(2, [Math]::Min(6, $wakes)) }
            $grace = [TimeSpan]::FromSeconds($graceSeconds)
            if (([DateTime]::UtcNow - $hit.Ts) -lt $grace) { continue }
            # Log written recently => the thread is alive again (the user, or a queued message, resumed it).
            if (([DateTime]::UtcNow - $hit.Written) -lt $grace) { continue }
            $key = $hit.ThreadId + "|" + $hit.TurnId
            if ($script:leakedWakeState.ContainsKey($key)) { continue }
            if ($isDead) {
                # A thread that keeps dying must not be woken forever.
                $budget = [int]$config.dead_turn_max_wakes_per_thread
                if ($wakes -ge $budget) {
                    $lastWarn = [DateTime]::MinValue
                    if ($script:deadTurnBudgetWarnedAt.ContainsKey($hit.ThreadId)) {
                        $lastWarn = $script:deadTurnBudgetWarnedAt[$hit.ThreadId]
                    }
                    if (([DateTime]::Now - $lastWarn).TotalSeconds -ge 600) {
                        $script:deadTurnBudgetWarnedAt[$hit.ThreadId] = [DateTime]::Now
                        Write-TrayActionLog ("dead-turn wake SKIPPED: thread {0} already woke {1} time(s), budget {2} - needs a human (or raise dead_turn_max_wakes_per_thread)" -f $hit.ThreadId, $wakes, $budget)
                    }
                    continue
                }
            }
            if ($isDead) {
                $errOneLine = ($hit.Error -replace '\s+', ' ').Trim()
                if ($errOneLine.Length -gt 160) { $errOneLine = $errOneLine.Substring(0, 160) }
                                $wakeText = "Tray dead-turn watchdog (attempt " + ($wakes + 1) + "): your previous turn was killed by the provider (" + $errOneLine + ") and never produced an answer, so the chat froze. The model is loaded now - repeat that step and continue where you stopped."
            } else {
                $wakeText = "Tray tool-call watchdog: your previous turn ended with the tool call printed as answer text instead of being executed, so nothing ran. Re-issue that tool call now and continue where you stopped."
            }
            try {
                $queueOutput = (& $codexCli queue --thread $hit.ThreadId --message $wakeText 2>&1 | Out-String).Trim()
                if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE : $queueOutput" }
            } catch {
                # One unreachable thread must not stop the other candidates in this tick.
                Write-TrayActionLog ("{0} wake FAILED: thread {1} {2}" -f $kind, $hit.ThreadId, $_.Exception.Message)
                continue
            }
            $script:leakedWakeState[$key] = [DateTimeOffset]::Now.ToUnixTimeSeconds()
            $woke++
            Write-TrayActionLog ("{0} wake: queued continue into thread {1} (turn idle {2:N0}s, turn {3})" -f $kind, $hit.ThreadId, ([Math]::Round(([DateTime]::UtcNow - $hit.Ts).TotalSeconds)), $hit.TurnId)
        }
        Save-LeakedToolCallState
        if ($woke -gt 0) {
            try {
                $notify.BalloonTipTitle = "H3 Tray: watchdog"
                $notify.BalloonTipText = "a chat froze at the end of a turn (printed tool call, or killed by model unload / provider error) - the tray queued 'continue' by itself"
                $notify.ShowBalloonTip(6000)
            } catch {}
        }
    } catch {
        Write-TrayActionLog "leaked-tool-call watch error: $($_.Exception.Message)"
    } finally {
        $script:leakedWatchInFlight = $false
    }
}

function Invoke-QwenUnloadInstances($Instances) {
    # Shared by the enforcer and both menu handlers: LM Studio uses /api/v1/models/unload, Strata uses /api/native/instances/{id}/unload.
    if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
    $ids = @($Instances | Where-Object { $_ })
    if ($ids.Count -eq 0) { return 0 }
    $isStrata = Test-StrataHost
    foreach ($iid in $ids) {
        if ($isStrata) {
            Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/native/instances/$iid/unload") -Method Post -ContentType "application/json" -Body '{}' -TimeoutSec 30 | Out-Null
        } else {
            Invoke-RestMethod -Uri ($script:lmEndpointBase.TrimEnd("/") + "/api/v1/models/unload") -Method Post -ContentType "application/json" -Body (@{instance_id = $iid} | ConvertTo-Json) -TimeoutSec 30 | Out-Null
        }
        Write-TrayActionLog "unload sent: instance $iid"
    }
    return $ids.Count
}

function Invoke-QwenAutoUnload {
    if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
    $instances = Get-QwenLoadedInstances
    if ($null -eq $instances -or $instances.Count -eq 0) { return $false }
    Invoke-QwenUnloadInstances $instances | Out-Null
    return $true
}

function Test-TrayScriptStale {
    # True when the .ps1 on disk is newer than the copy this process compiled at launch.
    try {
        if (-not $script:trayScriptPath -or $null -eq $script:trayScriptMtimeAtStart) { return $false }
        if (-not (Test-Path -LiteralPath $script:trayScriptPath -PathType Leaf)) { return $false }
        return (Get-Item -LiteralPath $script:trayScriptPath).LastWriteTime -gt $script:trayScriptMtimeAtStart
    } catch { return $false }
}

function Invoke-TrayScriptStalenessWatch {
    # Runs at the end of every status tick (so it also fires while ComfyUI is offline). When the script
    # has been edited, the menu shows it and the user can pick "Restart Tray" instead of hunting a PID.
    try {
        if (-not (Test-TrayScriptStale)) { return }
        if (-not $script:trayStaleMarkerShown) {
            $script:trayStaleMarkerShown = $true
            try { $statusItem.Text = "$($statusItem.Text)  [script edited - use Restart Tray]" } catch {}
        }
        if (([DateTime]::Now - $script:trayStaleWarnedAt).TotalSeconds -ge 900) {
            $script:trayStaleWarnedAt = [DateTime]::Now
            $edited = (Get-Item -LiteralPath $script:trayScriptPath).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            Write-TrayActionLog ("stale tray script: edited {0} but this pid {1} still runs the {2} copy - menu 'Restart Tray' to apply" -f `
                $edited, $PID, $script:trayScriptMtimeAtStart.ToString("yyyy-MM-dd HH:mm:ss"))
            try {
                $notify.BalloonTipTitle = "H3 Tray: script edited"
                $notify.BalloonTipText = "h3_status_tray.ps1 changed after this tray started. Use the tray menu -> Restart Tray to apply."
                $notify.ShowBalloonTip(6000)
            } catch {}
        }
    } catch {}
}

function Update-H3TrayStatus {
    try {
        $payload = $null
        try {
            $rawPayload = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 4
            if ($rawPayload.ok) { $payload = $rawPayload }
        } catch {
            # ComfyUI (or its status companion) is offline - and that is exactly the moment the GPU is free for Qwen.
            # Never let this error skip the enforcer below, or the tray goes "无动于衷" and Qwen stays unloaded.
        }
        $resources = $payload.resources
        $cache = Format-Gigabytes $payload.used_bytes
        $vram = Format-Percent $resources.vram_percent
        $dram = Format-Percent $resources.dram_percent
        $gpu = Format-Percent $resources.gpu_percent
        $cpu = Format-Percent $resources.cpu_percent
        $qwenInstances = Get-QwenLoadedInstances
        # $null = the catalogue could not be read this tick, which is unknown, not "unloaded".  The line below
        # used to fold unknown into FREE, which logged a bogus owner change and - once the ComfyUI queue
        # looked idle for 20 s - auto-loaded Qwen into a ComfyUI phase that still needed that VRAM.
        if ($null -eq $qwenInstances) {
            $ownerKey = if ($script:lastOwnerKey) { [string]$script:lastOwnerKey } else { "UNKNOWN" }
        } elseif (@($qwenInstances).Count -gt 0) {
            $ownerKey = "QWEN"
        } else {
            $ownerKey = "FREE"
        }
        $ownerState = if ($ownerKey -eq "QWEN") {
            "QWEN loaded (agent owns GPU)"
        } elseif ($ownerKey -eq "FREE") {
            "GPU free for H3"
        } else {
            "Qwen state unknown (host not answering)"
        }
        if ($null -eq $payload) { $ownerState = "$ownerState [ComfyUI status offline]" }
        $summary = "$ownerState | Cache $cache/100GB | VRAM $vram | DRAM $dram | GPU $gpu | CPU $cpu"
        $statusItem.Text = $summary
        Notify-OwnerChange $ownerKey
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
        # Enforcer: GPU free + ComfyUI queue idle for ~20s -> auto-load Qwen so the agent is not stuck on "model unloaded".
        try {
            $queueIdle = Test-ComfyQueueIdle
            if (-not $config.auto_load_qwen_when_free) {
                $script:freeSince = $null
                $script:busySince = $null
            } elseif ($ownerKey -ne "FREE" -or ($queueIdle -eq $false) -or ([DateTime]::Now -lt $script:suppressAutoLoadUntil) -or (Test-ComfyClaimActive -QueueIdle $queueIdle)) {
                # Qwen confirmed loaded, the Qwen state unknown, or H3 queue confirmed busy, or manual-unload grace period, or a live
                # driver claim: restart the window. An unreachable ComfyUI ($queueIdle = $null) is NOT busy -
                # same rule as the reverse arbiter below, otherwise a stopped ComfyUI meant "never auto-load".
                # "unknown" belongs in this branch on purpose: 2026-11-10 measured a catalogue hiccup during a
                # live take answering FREE, and 20 s later the tray was loading a ~20 GB Qwen mid-render.
                $script:freeSince = $null
            } else {
                # GPU free (confirmed) or unknown (catalog query failed this tick) + ComfyUI idle: accumulate ~20s then start Qwen.
                if ($script:freeSince -eq $null) {
                    $script:freeSince = [DateTime]::Now
                } elseif (([DateTime]::Now - $script:freeSince).TotalSeconds -ge 20 -and -not $script:autoLoadInFlight) {
                    $script:autoLoadInFlight = $true
                    try {
                        Invoke-QwenAutoLoad
                        $notify.BalloonTipTitle = "H3 Tray: auto-load"
                        $notify.BalloonTipText = "GPU free ~20s + queue empty -> tray auto-loaded Qwen ($($config.qwen_model))"
                        $notify.ShowBalloonTip(5000)
                    } catch {
                        $script:freeSince = $null
                        try {
                            $notify.BalloonTipTitle = "H3 Tray: auto-load failed"
                            $notify.BalloonTipText = "$($_.Exception.Message)"
                            $notify.ShowBalloonTip(6000)
                        } catch {}
                    } finally {
                        $script:autoLoadInFlight = $false
                    }
                }
            }
            # Reverse arbiter: ComfyUI queue busy for ~15s while Qwen is still loaded -> auto-unload Qwen so H3 gets the GPU.
            # $queueIdle is $null when ComfyUI cannot be reached: unknown must NOT be read as "busy", or the tray
            # force-unloads Qwen while ComfyUI is not even running (this was the spurious "又强制被unload了").
            if ($config.auto_load_qwen_when_free -and $ownerKey -eq "QWEN" -and ($queueIdle -eq $false)) {
                # A fresh keep-qwen claim means coexistence is intentional (driver --keep-qwen): do not unload under it.
                $claimBlocksReverse = $false
                $keepClaim = Get-ComfyClaim
                if ($null -ne $keepClaim) {
                    try {
                        $claimedAt = [DateTimeOffset]::FromUnixTimeSeconds([double]$keepClaim.ts).UtcDateTime
                        $claimBlocksReverse = (([DateTime]::UtcNow - $claimedAt).TotalSeconds -lt 5400) -and ([string]$keepClaim.note -like "keep*")
                    } catch {}
                }
                if ($claimBlocksReverse) {
                    $script:busySince = $null
                } elseif ($null -eq $script:busySince) {
                    $script:busySince = [DateTime]::Now
                } elseif (([DateTime]::Now - $script:busySince).TotalSeconds -ge 15 -and -not $script:autoUnloadInFlight) {
                    # Unloading Qwen while another chat's request is still travelling kills that turn with
                    # "No models loaded" / 503 / "high demand". Hold the unload while a turn is mid-flight,
                    # but never longer than defer_unload_for_active_turn_seconds: H3 still wins after that.
                    $deferUnload = $false
                    $deferCap = [int]$config.defer_unload_for_active_turn_seconds
                    $busyAge = ([DateTime]::Now - $script:busySince).TotalSeconds
                    if ($deferCap -gt 0 -and $busyAge -lt $deferCap) {
                        $inFlight = 0
                        try {
                            $inFlight = Get-CodexTurnsInFlight
                        } catch {
                            Write-TrayActionLog ("in-flight scan failed: $($_.Exception.Message)")
                        }
                        if ($inFlight -gt 0) {
                            $deferUnload = $true
                            if (([DateTime]::Now - $script:deferUnloadLoggedAt).TotalSeconds -ge 30) {
                                $script:deferUnloadLoggedAt = [DateTime]::Now
                                Write-TrayActionLog ("unload deferred: {0} Codex turn(s) mid-flight (busy {1:N0}s of {2}s cap)" -f $inFlight, $busyAge, $deferCap)
                            }
                        }
                    }
                    if (-not $deferUnload) {
                        $script:autoUnloadInFlight = $true
                        try {
                            if (Invoke-QwenAutoUnload) {
                                $notify.BalloonTipTitle = "H3 Tray: auto-unload"
                                $notify.BalloonTipText = "ComfyUI queue busy ~15s -> tray auto-unloaded Qwen ($($config.qwen_model)) for H3"
                                $notify.ShowBalloonTip(6000)
                            }
                        } catch {
                            try {
                                $notify.BalloonTipTitle = "H3 Tray: auto-unload failed"
                                $notify.BalloonTipText = "$($_.Exception.Message)"
                                $notify.ShowBalloonTip(6000)
                            } catch {}
                        } finally {
                            $script:autoUnloadInFlight = $false
                        }
                    }
                }
            } else {
                $script:busySince = $null
            }
            # Dead-thread auto-wake: driver crashed mid-run -> queue 'continue' into its Codex thread once Qwen is back.
            Invoke-AutoResume
            # Keep-alive: ping the Codex daemon every ~60s so it keeps this thread's context loaded (no-op on builds without status --ping).
            if (($null -eq $script:lastKeepAlive) -or (([DateTime]::Now - $script:lastKeepAlive).TotalSeconds -ge 60)) {
                $script:lastKeepAlive = [DateTime]::Now
                Invoke-CodexKeepAlive
            }
        } catch {
            # Enforcer is best-effort: a tick-level error must not break the status update itself.
        }
    } catch {
        $catchKey = if ((Get-QwenLoadedInstances).Count -gt 0) { "QWEN" } else { "FREE" }
        $qwenState = if ($catchKey -eq "QWEN") { "QWEN loaded" } else { "GPU free for H3" }
        $statusItem.Text = "ComfyUI unavailable | $qwenState | Cache/VRAM/DRAM/GPU/CPU N/A"
        Notify-OwnerChange $catchKey
        $notify.Text = "H3 Server Status - ComfyUI unavailable"
        $notify.Icon = [System.Drawing.SystemIcons]::Warning
    }
    # Tool-call watchdog runs on both branches too: a chat that closed its turn on a leaked tool call is
    # waiting for a message, whether or not ComfyUI answered this tick.
    try { Invoke-LeakedToolCallWatch } catch { Write-TrayActionLog "leaked-tool-call watch crashed: $($_.Exception.Message)" }
    # Last thing every tick: the staleness flag must survive both branches (and ComfyUI being offline),
    # because $statusItem.Text / $notify.Text are re-assigned above on each path.
    Invoke-TrayScriptStalenessWatch
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
            Show-H3MessageBox "Enter a valid HTTP or HTTPS ComfyUI address, for example:`r`nhttp://192.168.0.185:8189" "Invalid ComfyUI address"
            return
        }
        $cachePath = [Environment]::ExpandEnvironmentVariables($cacheInput.Text.Trim())
        if (-not $cachePath) {
            Show-H3MessageBox "Select or enter the H3 Relay cache folder." "Cache folder required"
            return
        }
        try { $cachePath = [IO.Path]::GetFullPath($cachePath) } catch {
            Show-H3MessageBox "The cache folder path is invalid." "Invalid cache folder"
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
            $script:lmEndpointBase = Get-LmOriginBase ([string]$script:config.lm_studio_url)
        } else {
            try {
                $reparsedApiUrl = [Uri]$script:config.api_url
                $script:lmEndpointBase = "http://$($reparsedApiUrl.Host):1234"
            } catch { $script:lmEndpointBase = "" }
        }
        $script:lmHostKind = $null
        Write-TrayActionLog ("settings saved: origin=$($script:lmEndpointBase) model=$($script:config.qwen_model)")
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
        # Manual unload: pause auto-load for 120s so the user can queue H3 work without Qwen coming back.
        $script:suppressAutoLoadUntil = [DateTime]::Now.AddSeconds(120)
        if (-not $script:lmEndpointBase) { throw "LM Studio URL not configured (Settings...)" }
        $instances = Get-QwenLoadedInstances
        if ($null -eq $instances -or @($instances).Count -eq 0) { throw "no loaded Qwen instance found" }
        Invoke-QwenUnloadInstances $instances | Out-Null
    }
})
$loadQwenItem.Add_Click({
    Invoke-TrayAction "Load Qwen" {
        Invoke-QwenAutoLoad
    }
})
$freeComfyItem.Add_Click({
    Invoke-TrayAction "Free ComfyUI" {
        Invoke-RestMethod -Uri ($config.api_url.TrimEnd("/") + "/free") -Method Post -ContentType "application/json" -Body (@{unload_models = $true; free_memory = $true} | ConvertTo-Json) -TimeoutSec 30
    }
})
$autoLoadItem.Add_Click({
    $script:config.auto_load_qwen_when_free = -not [bool]$autoLoadItem.Checked
    $autoLoadItem.Checked = [bool]$script:config.auto_load_qwen_when_free
    if ($script:config.auto_load_qwen_when_free) { $script:suppressAutoLoadUntil = [DateTime]::MinValue }
    Write-TrayConfig | Out-Null
})
$watchdogItem.Add_Click({
    $script:config.watch_leaked_tool_call = -not [bool]$script:config.watch_leaked_tool_call
    $watchdogItem.Checked = [bool]$script:config.watch_leaked_tool_call
    Write-TrayConfig | Out-Null
    Write-TrayActionLog ("tool-call watchdog " + $(if ($script:config.watch_leaked_tool_call) { "enabled" } else { "disabled" }) + " (saved)")
})
$deadTurnItem.Add_Click({
    $script:config.watch_dead_turns = -not [bool]$script:config.watch_dead_turns
    $deadTurnItem.Checked = [bool]$script:config.watch_dead_turns
    Write-TrayConfig | Out-Null
    Write-TrayActionLog ("dead-turn watchdog " + $(if ($script:config.watch_dead_turns) { "enabled" } else { "disabled" }) + " (saved)")
})
$notify.Add_DoubleClick({ Start-Process $config.api_url })
$context = New-Object System.Windows.Forms.ApplicationContext
$restartItem.Add_Click({
    # Same shutdown sequence as "Exit", but restart_h3_status_tray.bat waits ~2s for this process to
    # release Local\MiniMaxH3DirectorServerStatusTray before relaunching, so the mutex guard cannot swallow it.
    $restartBat = Join-Path $PSScriptRoot "restart_h3_status_tray.bat"
    if (-not (Test-Path -LiteralPath $restartBat -PathType Leaf)) {
        Write-TrayActionLog "restart aborted: restart_h3_status_tray.bat not found next to the script"
        return
    }
    Write-TrayActionLog ("restart tray requested (pid={0}) -> {1}" -f $PID, $restartBat)
    Start-Process -FilePath $restartBat -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    $timer.Stop()
    $notify.Visible = $false
    $notify.Dispose()
    $context.ExitThread()
})
$exitItem.Add_Click({
    $timer.Stop()
    $notify.Visible = $false
    $notify.Dispose()
    $context.ExitThread()
})

try {
    # Startup fingerprint: the tray keeps the script text it loaded at launch, so a later edit to this
    # file never reaches a running tray. Logging pid + script mtime makes "why is the old behaviour
    # still running" answerable from h3_tray_actions.log alone (if mtime is newer than the log's first
    # line for that pid, the tray needs a restart).
    try {
        $scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }
        $scriptMtime = if ($scriptPath -and (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
            (Get-Item -LiteralPath $scriptPath).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        } else { "unknown" }
        Write-TrayActionLog ("tray started: pid={0} script_mtime={1} codex={2}" -f $PID, $scriptMtime, (Resolve-CodexCli))
        # The watchdog is silent when nothing leaks, so "is it even armed?" has to be answerable from the log.
        $watchState = if ([bool]$config.watch_leaked_tool_call) { "armed" } else { "off" }
        $watchCli = if (Resolve-CodexCli) { "found" } else { "MISSING" }
        Write-TrayActionLog ("tool-call watchdog: {0} (grace={1}s, max_age={2}min, codex_cli={3})" -f `
            $watchState, [int]$config.leaked_toolcall_grace_seconds, [int]$config.leaked_toolcall_max_age_minutes, $watchCli)
        $deadWatchState = if ([bool]$config.watch_dead_turns) { "armed" } else { "off" }
        Write-TrayActionLog ("dead-turn watchdog: {0} (grace={1}s, budget={2}/thread, defer_unload={3}s)" -f `
            $deadWatchState, [int]$config.dead_turn_grace_seconds, [int]$config.dead_turn_max_wakes_per_thread, [int]$config.defer_unload_for_active_turn_seconds)
    } catch {}
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
