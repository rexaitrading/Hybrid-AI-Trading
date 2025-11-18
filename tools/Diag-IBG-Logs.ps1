[CmdletBinding()]
param(
    [string[]]$Roots = @(
        'C:\Jts\ibgateway\1039',
        'C:\Jts\ibgateway\1040'
    ),
    [int]$TailLines = 80
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "===== Diag-IBG-Logs (HybridAITrading) =====" -ForegroundColor Cyan
Write-Host ("Now: {0}" -f (Get-Date)) -ForegroundColor Cyan
Write-Host ""

foreach ($root in $Roots) {
    $logsDir = Join-Path $root 'logs'

    Write-Host ("--- Root: {0}" -f $root) -ForegroundColor Yellow
    Write-Host ("Logs dir: {0}" -f $logsDir) -ForegroundColor DarkYellow

    if (-not (Test-Path $logsDir)) {
        Write-Host "  (No logs directory found here.)" -ForegroundColor DarkYellow
        Write-Host ""
        continue
    }

    $files = Get-ChildItem $logsDir -File -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Descending

    if (-not $files) {
        Write-Host "  (No log files found.)" -ForegroundColor DarkYellow
        Write-Host ""
        continue
    }

    $latest = $files[0]
    Write-Host ("  Latest log: {0} (LastWrite={1})" -f $latest.FullName, $latest.LastWriteTime) -ForegroundColor Green

    Write-Host ""
    Write-Host ("  --- Tail {0} lines ---" -f $TailLines) -ForegroundColor Cyan

    try {
        Get-Content -Path $latest.FullName -Tail $TailLines -ErrorAction Stop |
            ForEach-Object { Write-Host "    $_" }
    } catch {
        Write-Host ("  Failed to read log: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }

    Write-Host ""
}
Write-Host "===== End Diag-IBG-Logs =====" -ForegroundColor Cyan