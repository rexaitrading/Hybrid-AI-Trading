[CmdletBinding()]
param(
    [int[]]$Ports = @(4001,4002,7496,7497)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "===== Diag-IBG-Network (HybridAITrading) =====" -ForegroundColor Cyan
Write-Host ("Now: {0}" -f (Get-Date)) -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# 1) Processes: ibgateway*, tws, java with user + path
# ------------------------------------------------------------
Write-Host "---- 1) IBG/TWS processes (Id, Name, Path, User) ----" -ForegroundColor Yellow

try {
    $procs = Get-Process -Name ibgateway*,tws,java -ErrorAction SilentlyContinue
} catch {
    $procs = @()
}

if (-not $procs) {
    Write-Host "No ibgateway/tws/java processes found." -ForegroundColor DarkYellow
} else {
    foreach ($p in $procs) {
        $user = $null
        $exe  = $null
        $cmd  = $null

        # Use WMI/Win32_Process for owner + executable path + command line
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
            } catch {
                $user = $null
            }

            if ($wmi.ExecutablePath) {
                $exe = $wmi.ExecutablePath
            }

            if ($wmi.CommandLine) {
                $cmd = $wmi.CommandLine
            }
        }

        if (-not $exe) {
            try {
                $exe = $p.MainModule.FileName
            } catch {
                $exe = $null
            }
        }

        if ($user) { $userText = $user } else { $userText = '<unknown>' }
        if ($exe)  { $pathText = $exe }  else { $pathText = '<unknown>' }
        if ($cmd)  { $cmdText  = $cmd }  else { $cmdText  = '<unknown>' }

        Write-Host ("PID={0} Name={1} User={2}" -f $p.Id, $p.ProcessName, $userText) -ForegroundColor Cyan
        Write-Host ("   Path       : {0}" -f $pathText) -ForegroundColor Green
        Write-Host ("   CmdLine    : {0}" -f $cmdText) -ForegroundColor DarkGray
        Write-Host ""
    }
}

# ------------------------------------------------------------
# 2) Listening ports for IBG/TWS API ports
# ------------------------------------------------------------
Write-Host "---- 2) Listening status for ports 4001/4002/7496/7497 ----" -ForegroundColor Yellow

foreach ($port in $Ports) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
                Select-Object -First 1

    if (-not $listener) {
        Write-Host ("Port {0}: NOT LISTENING" -f $port) -ForegroundColor DarkYellow
        continue
    }

    $ownerPid = [int]$listener.OwningProcess
    $proc = $null
    try {
        $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
    } catch {
        $proc = $null
    }

    $nameText = '<unknown>'
    $pathText = '<unknown>'

    if ($proc) {
        $nameText = $proc.ProcessName

        $exe = $null
        try {
            $wmi2 = Get-WmiObject Win32_Process -Filter ("ProcessId = {0}" -f $ownerPid) -ErrorAction SilentlyContinue
        } catch {
            $wmi2 = $null
        }

        if ($wmi2 -and $wmi2.ExecutablePath) {
            $exe = $wmi2.ExecutablePath
        }

        if (-not $exe) {
            try {
                $exe = $proc.MainModule.FileName
            } catch {
                $exe = $null
            }
        }

        if ($exe) { $pathText = $exe }
    }

    Write-Host ("Port {0}: LISTENING (PID={1}, Name={2})" -f $port, $ownerPid, $nameText) -ForegroundColor Green
    Write-Host ("   Exec Path  : {0}" -f $pathText) -ForegroundColor Green
}

Write-Host ""

# ------------------------------------------------------------
# 3) Internet connectivity to Interactive Brokers
# ------------------------------------------------------------
Write-Host "---- 3) Internet connectivity tests (Interactive Brokers) ----" -ForegroundColor Yellow

# 3a) DNS resolution
$hosts = @(
    'interactivebrokers.com',
    'www.interactivebrokers.com'
)

foreach ($h in $hosts) {
    try {
        $ips = [System.Net.Dns]::GetHostAddresses($h) | ForEach-Object { $_.IPAddressToString }
        if ($ips) {
            Write-Host ("DNS {0} -> {1}" -f $h, ($ips -join ', ')) -ForegroundColor Green
        } else {
            Write-Host ("DNS {0} -> <no addresses>" -f $h) -ForegroundColor DarkYellow
        }
    } catch {
        Write-Host ("DNS {0} failed: {1}" -f $h, $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host ""

# 3b) HTTPS connectivity to IB
foreach ($h in $hosts) {
    Write-Host ("Testing HTTPS to {0}:443 ..." -f $h) -ForegroundColor Cyan
    try {
        $tnc = Test-NetConnection -ComputerName $h -Port 443 -WarningAction SilentlyContinue
        Write-Host ("  TcpTestSucceeded: {0}" -f $tnc.TcpTestSucceeded) -ForegroundColor Green
    } catch {
        Write-Host ("  Test-NetConnection failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "===== End Diag-IBG-Network =====" -ForegroundColor Cyan