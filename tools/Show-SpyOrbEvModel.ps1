[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$modelPath  = Join-Path $repoRoot "config\phase5\spy_orb_ev_model.json"
$configPath = Join-Path $repoRoot "config\phase5\spy_orb_phase5.json"

if (Test-Path $modelPath) {
    $json = Get-Content $modelPath -Raw | ConvertFrom-Json
    $symbol   = $json.symbol
    $regime   = $json.regime
    $ev       = [double]$json.ev_orb_model
    $ev_pct_x = [double]$json.ev_orb_model_pct
    $notes    = [string]$json.notes
    $source   = $json.source_stats_csv
} elseif (Test-Path $configPath) {
    $json = Get-Content $configPath -Raw | ConvertFrom-Json
    $symbol   = $json.symbol
    $regime   = $json.regime
    $ev       = [double]$json.ev_avg_gross_pnl_pct
    $ev_pct_x = $ev * 100.0
    $notes    = [string]$json.notes
    $source   = "config\phase5\spy_orb_phase5.json"
} else {
    Write-Host "[SPY EV] No config/model found under config\phase5" -ForegroundColor Red
    exit 1
}

Write-Host ("[SPY EV] ev_orb_model = {0:F6}  (~{1:F4}% per trade)" -f $ev, $ev_pct_x)
Write-Host ("[SPY EV] regime = {0}, source = {1}" -f $regime, $source)
Write-Host ("[SPY EV] notes  = {0}" -f $notes)