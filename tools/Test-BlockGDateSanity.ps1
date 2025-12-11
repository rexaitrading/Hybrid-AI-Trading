[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ")]
    [string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$statusPath = Join-Path $repoRoot "logs\\blockg_status_stub.json"
$checker    = Join-Path $repoRoot "tools\\Check-BlockGReady.ps1"

if (-not (Test-Path $statusPath)) {
    Write-Host "[BLOCKG-DATE] ERROR: Status JSON not found at $statusPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $checker)) {
    Write-Host "[BLOCKG-DATE] ERROR: Checker not found at $checker" -ForegroundColor Red
    exit 1
}

Write-Host "[BLOCKG-DATE] Reading original status from $statusPath" -ForegroundColor Cyan
$origText = Get-Content $statusPath -Raw -Encoding UTF8
$origJson = $origText | ConvertFrom-Json

# Backup original file
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupPath = "$statusPath.bak_datesanity_$ts"
Copy-Item $statusPath $backupPath -Force
Write-Host "[BLOCKG-DATE] Backup saved at $backupPath" -ForegroundColor Yellow

# Build a stale status object: copy most fields, but mark today flags as FALSE and ts_utc as yesterday
$yesterday = (Get-Date).AddDays(-1).ToString("o")

$stale = $origJson | Select-Object *
$stale.ts_utc                    = $yesterday
$stale.phase23_health_ok_today   = $false
$stale.ev_hard_daily_ok_today    = $false
$stale.gatescore_fresh_today     = $false

$staleText = $stale | ConvertTo-Json -Depth 5
$staleText | Set-Content -Path $statusPath -Encoding UTF8

Write-Host "[BLOCKG-DATE] Wrote STALE status to $statusPath (today flags = FALSE, ts_utc=$yesterday)" -ForegroundColor Yellow

# Run the checker inside try/finally to ALWAYS restore original status
$exitCode = 0
try {
    Write-Host "[BLOCKG-DATE] Running Check-BlockGReady.ps1 -Symbol $Symbol with stale status..." -ForegroundColor Cyan
    & $checker -Symbol $Symbol
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "[BLOCKG-DATE] WARNING: Checker EXIT=0 even though today flags are FALSE." -ForegroundColor Yellow
    } else {
        Write-Host "[BLOCKG-DATE] OK: Checker EXIT=$exitCode (non-zero) when today flags are FALSE." -ForegroundColor Green
    }
}
finally {
    # Restore original status
    $origText | Set-Content -Path $statusPath -Encoding UTF8
    Write-Host "[BLOCKG-DATE] Restored original status from backup." -ForegroundColor Cyan
}

exit $exitCode