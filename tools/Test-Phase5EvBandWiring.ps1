param()

$ErrorActionPreference = "Stop"

Write-Host "`n[EV-BAND-TEST] Phase-5 EV / EV-band wiring check (NVDA / SPY / QQQ)" -ForegroundColor Cyan

# 1) Load ev_simple.json
$evJsonPath = "config\phase5\ev_simple.json"
if (-not (Test-Path $evJsonPath)) {
    Write-Host "[WARN] ev_simple.json not found at $evJsonPath" -ForegroundColor Yellow
} else {
    $evConfig = Get-Content $evJsonPath -Raw | ConvertFrom-Json

    $evNvda = $evConfig.NVDA_BPLUS_LIVE
    $evSpy  = $evConfig.SPY_ORB_LIVE
    $evQqq  = $evConfig.QQQ_ORB_LIVE

    Write-Host "`n[EV-CONFIG] Raw EV entries from ev_simple.json:" -ForegroundColor Cyan
    Write-Host ("  NVDA_BPLUS_LIVE : {0}" -f (($evNvda  | Out-String).Trim()))
    Write-Host ("  SPY_ORB_LIVE    : {0}" -f (($evSpy   | Out-String).Trim()))
    Write-Host ("  QQQ_ORB_LIVE    : {0}" -f (($evQqq   | Out-String).Trim()))
}

# 2) Load EV bands from phase5_ev_bands.yml (text scan)
$evBandsPath = "config\phase5_ev_bands.yml"
if (-not (Test-Path $evBandsPath)) {
    Write-Host "`n[EV-BAND] phase5_ev_bands.yml not found at $evBandsPath" -ForegroundColor Yellow
} else {
    Write-Host "`n[EV-BAND] SPY_ORB_LIVE block (approx):" -ForegroundColor Yellow
    Select-String -Path $evBandsPath -Pattern "spy_orb_live" -Context 0,5

    Write-Host "`n[EV-BAND] QQQ_ORB_LIVE block (approx):" -ForegroundColor Yellow
    Select-String -Path $evBandsPath -Pattern "qqq_orb_live" -Context 0,5
}

function Show-CsvEvSummary {
    param(
        [string]$Label,
        [string]$CsvPath,
        [string]$Regime
    )

    if (-not (Test-Path $CsvPath)) {
        Write-Host ("`n[EV-CSV] {0}: CSV not found at {1}" -f $Label, $CsvPath) -ForegroundColor Yellow
        return
    }

    $rows = Import-Csv $CsvPath
    if (-not $rows) {
        Write-Host ("`n[EV-CSV] {0}: no rows in CSV" -f $Label) -ForegroundColor Yellow
        return
    }
    $rows = @($rows)

    $liveRows = $rows | Where-Object {
        $_.PSObject.Properties["regime"] -ne $null -and
        $_.regime -eq $Regime
    }

    if (-not $liveRows) {
        Write-Host ("`n[EV-CSV] {0}: no rows for regime {1}" -f $Label, $Regime) -ForegroundColor Yellow
        return
    }

    Write-Host ("`n[EV-CSV] {0}: unique EV / EV band for {1} rows:" -f $Label, $Regime) -ForegroundColor Green
    $liveRows |
        Select-Object ev, ev_band_abs, side, ts |
        Sort-Object ev, ev_band_abs -Unique |
        Format-Table -Auto
}

# 3) Check CSV wiring for each symbol
Show-CsvEvSummary -Label "NVDA LIVE CSV" -CsvPath "logs\nvda_phase5_paper_for_notion.csv" -Regime "NVDA_BPLUS_LIVE"
Show-CsvEvSummary -Label "SPY LIVE CSV"  -CsvPath "logs\spy_phase5_paper_for_notion.csv"  -Regime "SPY_ORB_LIVE"
Show-CsvEvSummary -Label "QQQ LIVE CSV"  -CsvPath "logs\qqq_phase5_paper_for_notion.csv"  -Regime "QQQ_ORB_LIVE"

Write-Host "`n[EV-BAND-TEST] Completed Phase-5 EV / EV-band wiring check." -ForegroundColor Cyan