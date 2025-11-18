[CmdletBinding()]
param(
    # Root of IB Gateway install you expect IBC/scripts to use
    [string]$GatewayRoot = 'C:\Jts\ibgateway\1039',

    # Ports we care about (Gateway + TWS API ports)
    [int[]]$Ports = @(4001,4002,7496,7497),

    # How many recent log lines to show from each log file
    [int]$LogTail = 25
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "===== Diag-IBGatewayLoop (HybridAITrading) =====" -ForegroundColor Cyan
Write-Host ("Now: {0}" -f (Get-Date)) -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# 1) Processes: java / ibgateway / tws / IBC wrappers
# ------------------------------------------------------------
Write-Host "---- 1) Relevant processes (java / ibgateway / tws / IBC*) ----" -ForegroundColor Yellow

$procs = Get-Process -Name java,ibgateway*,tws,IBC* -ErrorAction SilentlyContinue |
         Select-Object Id, ProcessName, CPU, StartTime -ErrorAction SilentlyContinue

if (-not $procs) {
    Write-Host "No java/ibgateway/tws/IBC processes found." -ForegroundColor DarkYellow
} else {
    $procs | Format-Table -AutoSize
}
Write-Host ""

# ------------------------------------------------------------
# 2) Ports: who is listening on 4001/4002/7496/7497
# ------------------------------------------------------------
Write-Host "---- 2) Listening ports (4001/4002/7496/7497) and owning exe ----" -ForegroundColor Yellow

foreach ($port in $Ports) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
                Select-Object -First 1

    if (-not $listener) {
        Write-Host ("Port {0}: NOT LISTENING" -f $port) -ForegroundColor DarkYellow
        continue
    }

    $pid = [int]$listener.OwningProcess
    $proc = Get-CimInstance -ClassName Win32_Process -Filter ("ProcessId = {0}" -f $pid) -ErrorAction SilentlyContinue

    $exe = $null
    $cmd = $null
    if ($proc) {
        $exe = $proc.ExecutablePath
        $cmd = $proc.CommandLine
    }

    Write-Host ("Port {0}: PID={1}  Exe={2}" -f $port, $pid, ($exe -or '<unknown>')) -ForegroundColor Green
    if ($cmd) {
        Write-Host ("         CmdLine: {0}" -f $cmd) -ForegroundColor DarkGray
    }
}
Write-Host ""

# ------------------------------------------------------------
# 3) Gateway logs (latest 3 log files)
# ------------------------------------------------------------
Write-Host "---- 3) Gateway logs under $GatewayRoot ----" -ForegroundColor Yellow

if (-not (Test-Path $GatewayRoot)) {
    Write-Host "GatewayRoot not found: $GatewayRoot" -ForegroundColor Red
} else {
    $logDir = Join-Path $GatewayRoot 'logs'
    if (-not (Test-Path $logDir)) {
        Write-Host "No logs directory found at $logDir" -ForegroundColor DarkYellow
    } else {
        $latest = Get-ChildItem $logDir -File -ErrorAction SilentlyContinue |
                  Sort-Object LastWriteTime -Descending |
                  Select-Object -First 3

        if (-not $latest) {
            Write-Host "No log files in $logDir" -ForegroundColor DarkYellow
        } else {
            foreach ($f in $latest) {
                Write-Host ""
                Write-Host ("--- Log: {0} (LastWrite={1}) ---" -f $f.Name, $f.LastWriteTime) -ForegroundColor Cyan
                try {
                    Get-Content -Path $f.FullName -Tail $LogTail -ErrorAction Stop
                } catch {
                    Write-Host ("[Error reading log] {0}" -f $_.Exception.Message) -ForegroundColor Red
                }
            }
        }
    }
}
Write-Host ""

# ------------------------------------------------------------
# 4) Recent Application Error events for java/ibgateway
# ------------------------------------------------------------
Write-Host "---- 4) Recent Application Error events (java/ibgateway) ----" -ForegroundColor Yellow

try {
    $startTime = (Get-Date).AddHours(-8)  # last 8 hours
    $events = Get-WinEvent -FilterHashtable @{
        LogName      = 'Application'
        ProviderName = 'Application Error'
        StartTime    = $startTime
    } -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Message -match 'java.exe' -or
        $_.Message -match 'ibgateway' -or
        $_.Message -match 'tws.exe'
    } |
    Select-Object TimeCreated, Id, LevelDisplayName, Message -First 5

    if (-not $events) {
        Write-Host "No recent Application Error events for java/ibgateway/tws in last 8h." -ForegroundColor DarkYellow
    } else {
        $events | ForEach-Object {
            Write-Host ""
            Write-Host ("[{0}] EventId={1} Level={2}" -f $_.TimeCreated, $_.Id, $_.LevelDisplayName) -ForegroundColor Cyan
            Write-Host ($_.Message) -ForegroundColor DarkGray
        }
    }
} catch {
    Write-Host ("Get-WinEvent failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
}

Write-Host ""
Write-Host "===== End Diag-IBGatewayLoop =====" -ForegroundColor Cyan