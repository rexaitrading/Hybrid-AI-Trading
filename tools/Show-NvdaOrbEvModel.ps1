[CmdletBinding()]
param(
    [string]$Path = "config\phase5\nvda_orb_ev_model.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $Path)) {
    Write-Host "[Show-NvdaOrbEvModel] Config not found at $Path" -ForegroundColor Red
    exit 1
}

$cfg   = Get-Content $Path -Raw | ConvertFrom-Json
$ev    = [double]$cfg.ev_orb_vwap_model
$evPct = [double]$cfg.ev_orb_vwap_model_pct

Write-Host ("[NVDA EV] ev_orb_vwap_model = {0:N6}  (~{1:N3}% per trade)" -f $ev, $evPct) -ForegroundColor Cyan
Write-Host ("[NVDA EV] regime = {0}, source = {1}" -f $cfg.regime, $cfg.source_stats_csv) -ForegroundColor DarkGray
