[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [int]$Port = 7862,
    [int]$WaitSeconds = 20
)

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/')

function Test-ContainsRoot {
    param([AllowNull()][string]$Value)
    return $Value -and $Value.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Test-ProjectAudioSeparatorProcess {
    param($Process)
    $command = [string]$Process.CommandLine
    return (Test-ContainsRoot $command) -and (
        $command -like "*audio_separator_server.py*" -or
        $command -like "*vocal_separator_service.py*"
    )
}

function Get-ProcessByIdSafe {
    param([int]$ProcessId)
    return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
}

function Get-ListeningProcessIds {
    try {
        return @(
            Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch {
        $ids = @()
        foreach ($line in (& "$env:SystemRoot\System32\netstat.exe" -ano -p tcp)) {
            if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
                $ids += [int]$Matches[1]
            }
        }
        return @($ids | Select-Object -Unique)
    }
}

function Stop-ProcessTreeSafe {
    param([int]$ProcessId)
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        return
    }
    & "$env:SystemRoot\System32\taskkill.exe" /PID $ProcessId /T /F | Out-Null
    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        # The process may exit between the second lookup and Stop-Process.
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[Audio Separator] Stopped project-owned process tree PID $ProcessId"
}

$projectProcesses = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { Test-ProjectAudioSeparatorProcess $_ }
)
foreach ($process in $projectProcesses) {
    Stop-ProcessTreeSafe ([int]$process.ProcessId)
}

$deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(5, $WaitSeconds))
do {
    foreach ($listenerId in @(Get-ListeningProcessIds)) {
        $listener = Get-ProcessByIdSafe ([int]$listenerId)
        if (-not $listener) {
            continue
        }
        if (-not (Test-ContainsRoot ([string]$listener.CommandLine))) {
            throw "Port $Port belongs to unrelated process PID $listenerId and was not stopped."
        }
        Stop-ProcessTreeSafe ([int]$listenerId)
    }
    if (@(Get-ListeningProcessIds).Count -eq 0) {
        $probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $Port)
        try {
            $probe.Start()
            Write-Host "[Audio Separator] Port $Port is free. CUDA model memory is released."
            exit 0
        } catch {
            # Windows may retain a socket briefly after process exit.
        } finally {
            $probe.Stop()
        }
    }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)

throw "Port $Port did not become bindable within $WaitSeconds seconds."
