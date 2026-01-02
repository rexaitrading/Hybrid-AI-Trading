[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# HARD paper-only safety (institutional fail-closed)
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"

# Build Phase-6 state (includes User->Process env fallback for IBG status path)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-Phase6PortfolioState.ps1")

# Export daily summary CSV (Notion-friendly)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Export-Phase6DailySummary.ps1")

# Print single-line summary
$p = Get-Content -LiteralPath (Join-Path $repoRoot "logs\phase6_portfolio_state.json") -Raw -Encoding utf8 | ConvertFrom-Json
$ready = ""
if($null -ne $p.ready_symbols){ $ready = [string]::Join(",", @($p.ready_symbols)) }
Write-Host ("[PHASE6-ONETAP] ok={0} reason={1} ready={2} as_of={3}" -f $p.ok, $p.reason, $ready, $p.as_of_date) -ForegroundColor Cyan

# FAIL-FAST OPS: exit nonzero when phase6 state is not ok
try {
  if($null -ne $p -and ($p.PSObject.Properties.Name -contains "ok") -and (-not [bool]$p.ok)){
    exit 2
  }
} catch {
  exit 2
}
exit 0
