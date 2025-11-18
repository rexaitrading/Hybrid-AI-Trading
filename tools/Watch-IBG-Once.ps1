[CmdletBinding()]
param(
    [ValidateSet('Paper','Live')]
    [string]$Mode = 'Paper',

    [int]$TailLines = 80
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "===== Watch-IBG-Once (HybridAITrading) =====" -ForegroundColor Cyan
Write-Host ("Now: {0}" -f (Get-Date)) -ForegroundColor Cyan
Write-Host ("Mode: {0}" -f $Mode) -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# Helper: show last ibg_auto_*.log
# -----------------------------
function Show-LastIbgAutoLog {
    param(
        [int]$Lines = 80
    )

    $logRoot = 'C:\Jts\logs'
    Write-Host ("[LOG] Searching {0} for ibg_auto_*.log ..." -f $logRoot) -ForegroundColor Yellow

    if (-not (Test-Path $logRoot)) {
        Write-Host "  No C:\Jts\logs directory found." -ForegroundColor DarkYellow
        return
    }

    $latest = Get-ChildItem $logRoot -Filter 'ibg_auto_*.log' -File -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending |
              Select-Object -First 1

    if (-not $latest) {
        Write-Host "  No ibg_auto_*.log files found." -ForegroundColor DarkYellow
        return
    }

    Write-Host ("  Latest IBC auto log: {0} (LastWrite={1})" -f $latest.FullName, $latest.LastWriteTime) -ForegroundColor Green
    Write-Host ""
    Write-Host ("  --- Tail {0} lines (raw) ---" -f $Lines) -ForegroundColor Cyan

    $tail = @()
    try {
        $tail = Get-Content -Path $latest.FullName -Tail $Lines -ErrorAction Stop
        foreach ($ln in $tail) {
            Write-Host ("    {0}" -f $ln)
        }
    } catch {
        Write-Host ("  Failed to read log: {0}" -f $_.Exception.Message) -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "  --- Candidate reason lines (Error/login/disconnect/existing session) ---" -ForegroundColor Magenta

    $candidates = $tail | Where-Object {
        $_ -match 'Error' -or
        $_ -match 'ERROR' -or
        $_ -match 'disconnect' -or
        $_ -match 'Disconnected' -or
        $_ -match 'existing session' -or
        $_ -match 'login' -or
        $_ -match 'Login'
    }

    if (-not $candidates) {
        Write-Host "  (No obvious reason lines; inspect raw tail above.)" -ForegroundColor DarkYellow
    } else {
        foreach ($ln in $candidates) {
            Write-Host ("    {0}" -f $ln) -ForegroundColor Magenta
        }
    }

    Write-Host ""
}

# -----------------------------
# 1) Determine expected port
# -----------------------------
$expectedPort = 4002
if ($Mode -eq 'Live') {
    $expectedPort = 4001
}

Write-Host ("Expected API port: {0}" -f $expectedPort) -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# 2) Check processes
# -----------------------------
Write-Host "---- Process check (ibgateway*/tws/java) ----" -ForegroundColor Yellow

try {
    $procs = Get-Process -Name ibgateway*,tws,java -ErrorAction SilentlyContinue
} catch {
    $procs = @()
}

if (-not $procs) {
    Write-Host "No ibgateway/tws/java processes found." -ForegroundColor DarkYellow
} else {
    foreach ($p in $procs) {
        $user = '<unknown>'
        $exe  = $null

        try {
            $wmi = Get-WmiObject Win32_Process -Filter ("ProcessId = {0}" -f $p.Id) -ErrorAction SilentlyContinue
        } catch {
            $wmi = $null
        }

        if ($wmi) {
            try {
                $owner = $wmi.GetOwner()
                if ($owner) {
                    $user = "{0}\{1}" -f $owner.Domain, $owner.User
                }
            } catch { }

            if ($wmi.ExecutablePath) {
                $exe = $wmi.ExecutablePath
            }
        }

        if (-not $exe) {
            try {
                $exe = $p.MainModule.FileName
            } catch {
                $exe = '<unknown>'
            }
        }

        Write-Host ("PID={0} Name={1} User={2}" -f $p.Id, $p.ProcessName, $user) -ForegroundColor Cyan
        Write-Host ("   Path    : {0}" -f $exe) -ForegroundColor Green
        Write-Host ""
    }
}

# -----------------------------
# 3) Check expected API port
# -----------------------------
Write-Host "---- API port check ----" -ForegroundColor Yellow

$listener = Get-NetTCPConnection -State Listen -LocalPort $expectedPort -ErrorAction SilentlyContinue |
            Select-Object -First 1

if (-not $listener) {
    Write-Host ("Port {0}: NOT LISTENING" -f $expectedPort) -ForegroundColor Red
    Write-Host ""
    Write-Host ("*** STATUS: IBG API port is DOWN for mode {0}. ***" -f $Mode) -ForegroundColor Red
    Write-Host ""
    Write-Host "*** Inspecting last IBC auto log for reason why IBG might have closed or failed to auto-login... ***" -ForegroundColor Yellow
    Write-Host ""
    Show-LastIbgAutoLog -Lines $TailLines
    Write-Host "===== End Watch-IBG-Once =====" -ForegroundColor Cyan
    return
}

$ownerPid = [int]$listener.OwningProcess
Write-Host ("Port {0}: LISTENING (PID={1})" -f $expectedPort, $ownerPid) -ForegroundColor Green

$ownerProc = $null
try {
    $ownerProc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
} catch {
    $ownerProc = $null
}

if ($ownerProc) {
    $exePath = '<unknown>'
    try {
        $wmi2 = Get-WmiObject Win32_Process -Filter ("ProcessId = {0}" -f $ownerPid) -ErrorAction SilentlyContinue
    } catch {
        $wmi2 = $null
    }

    if ($wmi2 -and $wmi2.ExecutablePath) {
        $exePath = $wmi2.ExecutablePath
    } else {
        try {
            $exePath = $ownerProc.MainModule.FileName
        } catch {
            $exePath = '<unknown>'
        }
    }

    Write-Host ("API owner Name : {0}" -f $ownerProc.ProcessName) -ForegroundColor Green
    Write-Host ("API owner Path : {0}" -f $exePath) -ForegroundColor Green
} else {
    Write-Host "Warning: Could not resolve owner process for listening port." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host ("*** STATUS: IBG API port is UP and listening for mode {0}. ***" -f $Mode) -ForegroundColor Green
Write-Host ""
Write-Host "If IBG closed previously and auto-login did not trigger, run this script again AFTER it closes to inspect the newest ibg_auto_*.log for the reason (login failure, existing session, unsubscribed provider, etc.)." -ForegroundColor Cyan
Write-Host ""
Write-Host "===== End Watch-IBG-Once =====" -ForegroundColor Cyan