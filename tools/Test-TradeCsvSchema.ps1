# === Validate header order against Canonical Trade CSV Schema ===
param(
  [string]$Dir = (Join-Path (Split-Path $PSScriptRoot -Parent) "out\trades")
)

$ErrorActionPreference='Stop'

$Canonical = @(
  'trade_id','run_id','account','timestamp_open','timestamp_close','symbol','asset_class','side','qty',
  'entry_px','exit_px','avg_add_px','avg_reduce_px','fees_commissions','slippage_cost',
  'pnl_gross','pnl_net','pnl_r','risk_usd','kelly_f','max_adverse_excursion','max_favorable_excursion',
  'holding_sec','strategy','setup_tag','regime','market_state','order_ids','notes','screenshot_path'
)

if (-not (Test-Path $Dir)) { Write-Host "No trades dir: $Dir"; exit 0 }

Get-ChildItem $Dir -File -Filter '*_trades.csv' | ForEach-Object {
  $first = Get-Content -TotalCount 1 -Path $_.FullName
  $hdr = $first -split ','
  $hdr = $hdr | ForEach-Object { $_.Trim('"') }   # strip quotes if any
  $ok = ($hdr.Count -eq $Canonical.Count) -and (@(0..($hdr.Count-1) | ? { $hdr[$_] -eq $Canonical[$_] }).Count -eq $hdr.Count)
  if ($ok) { Write-Host "OK schema: $($_.Name)" -ForegroundColor Green }
  else {
    Write-Host "BAD schema: $($_.Name)" -ForegroundColor Red
    Write-Host "  Expected: $($Canonical -join ',')"
    Write-Host "  Actual  : $($hdr -join ',')"
  }
}
