[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$configPath = Join-Path $repoRoot "config\phase5\spy_orb_phase5.json"

if (-not (Test-Path $configPath)) {
    Write-Host "[SPY EV] Config not found at $configPath" -ForegroundColor Red
    exit 1
}

$json = Get-Content $configPath -Raw | ConvertFrom-Json

$symbol   = $json.symbol
$regime   = $json.regime
$ev_pct   = [double]$json.ev_avg_gross_pnl_pct
$ev_pct_x = $ev_pct * 100.0
$notes    = [string]$json.notes

# Try to extract a simple source filename from notes if present
$source = $null
if ($notes -match "research\\\\([^\""]+)") {
    $source = "research\$($Matches[1])"
}

Write-Host ("[SPY EV] ev_orb_model = {0:F6}  (~{1:F4}% per trade)" -f $ev_pct, $ev_pct_x)
if ($source) {
    Write-Host ("[SPY EV] regime = {0}, source = {1}" -f $regime, $source)
} else {
    Write-Host ("[SPY EV] regime = {0}" -f $regime)
    Write-Host ("[SPY EV] notes  = {0}" -f $notes)
}