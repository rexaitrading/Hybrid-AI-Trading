# === Patch CSVs to Canonical Trade Schema (order & header) ===
param(
  [string]$Dir = (Join-Path (Split-Path $PSScriptRoot -Parent) "out\trades"),
  [switch]$WhatIf
)

$ErrorActionPreference='Stop'

$Canonical = @(
  'trade_id','run_id','account','timestamp_open','timestamp_close','symbol','asset_class','side','qty',
  'entry_px','exit_px','avg_add_px','avg_reduce_px','fees_commissions','slippage_cost',
  'pnl_gross','pnl_net','pnl_r','risk_usd','kelly_f','max_adverse_excursion','max_favorable_excursion',
  'holding_sec','strategy','setup_tag','regime','market_state','order_ids','notes','screenshot_path'
)

if (-not (Test-Path $Dir)) { Write-Host "No trades dir: $Dir"; exit 0 }
$Utf8 = New-Object System.Text.UTF8Encoding($false)

Get-ChildItem $Dir -File -Filter '*_trades.csv' | ForEach-Object {
  $p = $_.FullName
  $lines = Get-Content -Raw -Encoding UTF8 $p -ErrorAction Stop
  $lines = $lines -replace "`r`n","`n" -replace "`r","`n"
  $split = $lines -split "`n"
  if ($split.Count -lt 1) { return }
  $hdr = $split[0] -split ',' | ForEach-Object { $_.Trim('"') }

  $needPatch = $false
  if ($hdr.Count -ne $Canonical.Count) { $needPatch = $true }
  else {
    for($i=0;$i -lt $hdr.Count;$i++){ if($hdr[$i] -ne $Canonical[$i]){ $needPatch = $true; break } }
  }

  if (-not $needPatch) { Write-Host "OK: $($_.Name)"; return }

  Write-Host "PATCH: $($_.Name)" -ForegroundColor Yellow

  # Re-import properly and reorder columns
  $rows = Import-Csv -Path $p
  $out = New-Object System.Text.StringBuilder
  [void]$out.AppendLine(($Canonical -join ','))

  foreach($r in $rows){
    $vals = foreach($c in $Canonical){
      $v = ''
      if ($r.PSObject.Properties.Name -contains $c) { $v = [string]$r.$c }
      if ($v -match '[,"\r\n]') { '"' + ($v -replace '"','""') + '"' } else { $v }
    }
    [void]$out.AppendLine(($vals -join ','))
  }

  if ($WhatIf) {
    Write-Host "  (whatif) would rewrite $($_.Name)"
  } else {
    [IO.File]::WriteAllText($p, $out.ToString().Replace("`r`n","`n"), $Utf8)
    Write-Host "  rewritten"
  }
}
