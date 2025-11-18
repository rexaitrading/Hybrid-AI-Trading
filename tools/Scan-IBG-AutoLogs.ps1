[CmdletBinding()]
param(
    [int]$TailLinesPerFile = 120
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "===== Scan-IBG-AutoLogs (HybridAITrading) =====" -ForegroundColor Cyan
Write-Host ("Now: {0}" -f (Get-Date)) -ForegroundColor Cyan
Write-Host ""

$logRoot = 'C:\Jts\logs'
if (-not (Test-Path $logRoot)) {
    Write-Host "No C:\Jts\logs directory found." -ForegroundColor DarkYellow
    Write-Host "===== End Scan-IBG-AutoLogs =====" -ForegroundColor Cyan
    return
}

$files = Get-ChildItem $logRoot -Filter 'ibg_auto_*.log' -File -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending

if (-not $files) {
    Write-Host "No ibg_auto_*.log files found in C:\Jts\logs." -ForegroundColor DarkYellow
    Write-Host "===== End Scan-IBG-AutoLogs =====" -ForegroundColor Cyan
    return
}

foreach ($f in $files) {
    Write-Host ("--- File: {0}" -f $f.FullName) -ForegroundColor Yellow
    Write-Host ("    LastWrite: {0}" -f $f.LastWriteTime) -ForegroundColor DarkYellow

    $tail = @()
    try {
        $tail = Get-Content -Path $f.FullName -Tail $TailLinesPerFile -ErrorAction Stop
    } catch {
        Write-Host ("    Failed to read: {0}" -f $_.Exception.Message) -ForegroundColor Red
        Write-Host ""
        continue
    }

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
        Write-Host "    (No obvious error/login/disconnect lines in last chunk.)" -ForegroundColor DarkYellow
        Write-Host ""
        continue
    }

    Write-Host "    Candidate reason lines:" -ForegroundColor Magenta
    foreach ($ln in $candidates) {
        Write-Host ("      {0}" -f $ln) -ForegroundColor Magenta
    }
    Write-Host ""
}

Write-Host "===== End Scan-IBG-AutoLogs =====" -ForegroundColor Cyan