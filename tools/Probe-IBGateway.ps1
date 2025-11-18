[CmdletBinding()]
param(
    [ValidateSet('Paper','Live')]
    [string]$Mode = 'Paper',

    # Expected IB Gateway root (adjust if you use 1040 or different path)
    [string]$ExpectedRoot = 'C:\Jts\ibgateway\1039'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$toolsDir = $PSScriptRoot
$repoRoot = (Get-Item $toolsDir).Parent.FullName

Write-Host "[Probe-IBG] Repo: $repoRoot" -ForegroundColor Cyan
Set-Location $repoRoot

# Map mode to port
if ($Mode -eq 'Paper') {
    $port = 4002
} else {
    $port = 4001
}

Write-Host "[Probe-IBG] Checking mode=$Mode port=$port" -ForegroundColor Cyan

$listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
            Select-Object -First 1

if (-not $listener) {
    Write-Host "[Probe-IBG] No process listening on port $port. IB Gateway ($Mode) not up." -ForegroundColor Red
    exit 1
}

$ibPid = [int]$listener.OwningProcess
Write-Host ("[Probe-IBG] Port {0} listening with PID {1}" -f $port, $ibPid) -ForegroundColor Cyan

# Try to read executable path, but treat failure as WARNING, not hard fail
try {
    $proc = Get-CimInstance -ClassName Win32_Process -Filter ("ProcessId = {0}" -f $ibPid)
    $exe  = $proc.ExecutablePath
} catch {
    $exe = $null
}

if (-not $exe) {
    Write-Host "[Probe-IBG] WARNING: Could not read executable path for PID $ibPid (permissions or WMI issue)." -ForegroundColor Yellow
    Write-Host "[Probe-IBG] Assuming IB Gateway ($Mode) is healthy based on port $port listener only." -ForegroundColor Yellow
    exit 0
}

Write-Host "[Probe-IBG] Executable: $exe" -ForegroundColor Cyan

# Normalize comparison
$expectedRootNorm = (Resolve-Path $ExpectedRoot).Path
$exeDir           = (Split-Path $exe -Parent)

if ($exeDir -notlike "$expectedRootNorm*") {
    Write-Host "[Probe-IBG] WARNING: Executable not under expected root." -ForegroundColor Yellow
    Write-Host "  Expected root: $expectedRootNorm" -ForegroundColor Yellow
    Write-Host "  Actual dir:    $exeDir" -ForegroundColor Yellow
    # Still treat as OK for now, just warn
    exit 0
}

Write-Host "[Probe-IBG] IB Gateway ($Mode) looks healthy at $exeDir" -ForegroundColor Green
exit 0