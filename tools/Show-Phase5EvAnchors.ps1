[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "`n[PHASE5 EV] === Phase-5 ORB/EV Anchor Summary ===" -ForegroundColor Cyan

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# --- NVDA / SPY / QQQ EV model inspectors ---
$nvdaShow = Join-Path $toolsDir "Show-NvdaOrbEvModel.ps1"
$spyShow  = Join-Path $toolsDir "Show-SpyOrbEvModel.ps1"
$qqqShow  = Join-Path $toolsDir "Show-QqqOrbEvModel.ps1"

if (Test-Path $nvdaShow) {
    Write-Host "`n[NVDA EV] ------------------------" -ForegroundColor Yellow
    & $nvdaShow
} else {
    Write-Host "[NVDA EV] Show-NvdaOrbEvModel.ps1 not found at $nvdaShow" -ForegroundColor Red
}

if (Test-Path $spyShow) {
    Write-Host "`n[SPY EV] ------------------------" -ForegroundColor Yellow
    & $spyShow
} else {
    Write-Host "[SPY EV] Show-SpyOrbEvModel.ps1 not found at $spyShow" -ForegroundColor Red
}

if (Test-Path $qqqShow) {
    Write-Host "`n[QQQ EV] ------------------------" -ForegroundColor Yellow
    & $qqqShow
} else {
    Write-Host "[QQQ EV] Show-QqqOrbEvModel.ps1 not found at $qqqShow" -ForegroundColor Red
}

# --- EV-bands snapshot ---
Write-Host "`n[EV-BANDS] ------------------------" -ForegroundColor Yellow

$evBandsPath = Join-Path $repoRoot "config\phase5_ev_bands.yml"
if (-not (Test-Path $evBandsPath)) {
    Write-Host "[EV-BANDS] Config not found at $evBandsPath" -ForegroundColor Red
    return
}

# Show only the key live entries and regimes block
$lines = Get-Content $evBandsPath

Write-Host "[EV-BANDS] Raw nvda_bplus_live / spy_orb_live / qqq_orb_live:" -ForegroundColor Green
$lines | Where-Object { $_ -match 'nvda_bplus_live' -or $_ -match 'spy_orb_live' -or $_ -match 'qqq_orb_live' -or $_ -match 'ev_band_abs:' } |
    ForEach-Object { Write-Host "  $_" }

Write-Host "`n[EV-BANDS] Regime EV-per-trade snapshot:" -ForegroundColor Green
$inRegimes = $false
foreach ($line in $lines) {
    if ($line -match '^regimes:') {
        $inRegimes = $true
        Write-Host "  $line"
        continue
    }
    if ($inRegimes) {
        if ($line -match '^\S' -and -not ($line -match '^regimes:')) {
            # top-level key; still part of regimes block until a blank or comment-only section?
            Write-Host "  $line"
        } elseif ($line -match '^\s+ev_per_trade:' -or $line -match '^\s+band_min_ev:') {
            Write-Host "  $line"
        }
    }
}

Write-Host "`n[PHASE5 EV] === End Phase-5 ORB/EV Anchor Summary ===`n" -ForegroundColor Cyan