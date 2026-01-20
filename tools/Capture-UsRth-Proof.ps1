[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")][string]$Symbol = "NVDA",
  [ValidateSet("PAPERLIVE","LIVE")][string]$Mode = "PAPERLIVE"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$root=(Resolve-Path -LiteralPath ".").Path
if($root -ne "C:\HATJ\HybridAITrading"){ throw ("[FAIL-CLOSED] RepoRoot not canonical: " + $root) }

$ts=(Get-Date).ToString("yyyyMMdd_HHmmss")
$transcript = Join-Path $root ("logs\US\rth_proof_capture_{0}.txt" -f $ts)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $transcript) | Out-Null
Start-Transcript -LiteralPath $transcript | Out-Null

try {
  $env:HAT_MARKET="US"
  $env:HAT_TRADE_MODE=$Mode
  $env:HAT_MODE=$Mode
  $env:HAT_SYMBOL=$Symbol

  "=== (1) Intel minimal pulse (per-market mirror) ===" | Out-Host
  .\tools\Run-IntelPipeline-Minimal.ps1 | Out-Host

  "=== (2) ProducersOnly OneTap (US) ===" | Out-Host
  .\tools\PreMarket-OneTap.ps1 -ProducersOnly -Symbol $Symbol | Out-Host

  "=== (3) BlockG build (US) ===" | Out-Host
  .\tools\Build-BlockGStatusStub.ps1 -Market "US" -Symbol $Symbol | Out-Host

  $bgp = Join-Path $root "logs\US\blockg_status_stub.json"
  if(-not (Test-Path -LiteralPath $bgp)){ throw "[FAIL-CLOSED] missing blockg_status_stub.json after build" }
  $bg = Get-Content -LiteralPath $bgp -Raw -Encoding UTF8 | ConvertFrom-Json

  "=== US RTH PROOF FIELDS ===" | Out-Host
  $bg | Select-Object `
    as_of_date,session_name,market_is_open_now,market_closed_today,is_trading_day,`
    contract_semantics_level,contract_semantics_reason,full_live_eligible,`
    intel_ok_today,nvda_intel_ok_today,intel_age_minutes,intel_kind,intel_source_path,`
    nvda_blockg_ready,global_ready_ok_today,regime_ok_today,crisis_ok_today,crashmode_flatten_ok |
    Format-List | Out-Host

} finally {
  Stop-Transcript | Out-Null
  ("[DONE] Transcript=" + $transcript) | Out-Host
}
