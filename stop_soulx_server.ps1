[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [int]$Port = 7861,
    [int]$WaitSeconds = 20
)

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\', '/')

function Test-ContainsRoot {
    param([AllowNull()][string]$Value)
    return $Value -and $Value.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Test-ProjectOwnedProcess {
    param($Process)
    return (Test-ContainsRoot ([string]$Process.CommandLine)) -or
        (Test-ContainsRoot ([string]$Process.ExecutablePath))
}

function Test-SoulXProcess {
    param($Process)
    $command = [string]$Process.CommandLine
    $executable = [string]$Process.ExecutablePath
    $soulxRuntime = Join-Path $root "models\SoulX-Singer-main"
    return (Test-ProjectOwnedProcess $Process) -and (
        $command -like "*soulx_server.py*" -or
        $command -like "*webui_svc.py*" -or
        $command -like "*SoulX-Singer-main*" -or
        ($executable -and $executable.IndexOf($soulxRuntime, [StringComparison]::OrdinalIgnoreCase) -ge 0)
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
    & "$env:SystemRoot\System32\taskkill.exe" /PID $ProcessId /T /F | Out-Host
    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    }
    Write-Host "[SoulX] Stopped project-owned process tree PID $ProcessId"
}

$initialProcesses = @(
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { Test-SoulXProcess $_ }
)
foreach ($process in $initialProcesses) {
    Stop-ProcessTreeSafe ([int]$process.ProcessId)
}

$deadline = [DateTime]::UtcNow.AddSeconds([Math]::Max(5, $WaitSeconds))
do {
    $listeners = @(Get-ListeningProcessIds)
    foreach ($listenerId in $listeners) {
        $listener = Get-ProcessByIdSafe ([int]$listenerId)
        if (-not $listener) {
            continue
        }
        if (-not (Test-ProjectOwnedProcess $listener)) {
            $name = [string]$listener.Name
            $path = [string]$listener.ExecutablePath
            throw "Port $Port is owned by unrelated process PID $listenerId ($name) $path. It was not stopped."
        }
        Stop-ProcessTreeSafe ([int]$listenerId)
    }

    if (@(Get-ListeningProcessIds).Count -eq 0) {
        $probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, $Port)
        try {
            $probe.Start()
            Write-Host "[SoulX] Port $Port is free."
            exit 0
        } catch {
            # The socket can remain unavailable briefly after its process exits.
        } finally {
            $probe.Stop()
        }
    }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)

throw "Port $Port did not become bindable within $WaitSeconds seconds."
