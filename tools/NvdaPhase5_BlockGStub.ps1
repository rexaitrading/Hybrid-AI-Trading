# BLOCK-G STATUS: STUB ONLY - NO LIVE TRADING

[CmdletBinding()]
param(
    [switch] $VerboseChecklist  # if set, print extra detail
)

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[BLOCK-G] === NVDA Phase-5 Block-G Live Playbook STUB ===" -ForegroundColor Cyan
Write-Host "[BLOCK-G] This script does NOT launch any live trading yet." -ForegroundColor Yellow
Write-Host "[BLOCK-G] It is a checklist + planning stub only." -ForegroundColor Yellow

# Basic context
$nowLocal = Get-Date
Write-Host ("[BLOCK-G] Now (local): {0}" -f $nowLocal.ToString("yyyy-MM-dd HH:mm:ss")) -ForegroundColor Gray

Write-Host "`n[BLOCK-G] Preconditions (high-level):" -ForegroundColor Cyan
Write-Host "  1) Phase-5 microsuite green           -> tools\Run-Phase5MicroSuite.ps1" -ForegroundColor Gray
Write-Host "  2) Phase-5 EV preflight green         -> tools\Run-Phase5EvPreflight.ps1" -ForegroundColor Gray
Write-Host "  3) Full CI green                      -> tools\Run-Phase5FullCI.ps1" -ForegroundColor Gray
Write-Host "  4) PreMarket-Check OK_TO_TRADE        -> tools\PreMarket-Check.ps1" -ForegroundColor Gray
Write-Host "  5) EV hard veto daily snapshot ready  -> tools\Invoke-Phase5EvHardVetoDaily.ps1" -ForegroundColor Gray
Write-Host "  6) IB API smoke OK                    -> tools\Test-IBAPI.ps1" -ForegroundColor Gray
Write-Host "  7) Notion NVDA Live journal prepared." -ForegroundColor Gray

if ($VerboseChecklist) {
    Write-Host "`n[BLOCK-G] For detailed Block-G rules, see:" -ForegroundColor Cyan
    Write-Host "  docs\Phase5_BlockG_LivePlaybook.md" -ForegroundColor Gray
}

Write-Host "`n[BLOCK-G] Stub status: OK (no trades executed)." -ForegroundColor Green
Write-Host "[BLOCK-G] When Block-G is armed in the future, this stub will be replaced by a live-aware runner." -ForegroundColor Green