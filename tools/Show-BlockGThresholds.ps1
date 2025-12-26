[CmdletBinding()]
param([string]$Symbol="ALL")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
$thr1 = Join-Path $root "configs\blockg_thresholds.json"
$thr2 = Join-Path $root "docs\thresholds\blockg_thresholds.json"
$thr = if(Test-Path $thr1){$thr1}else{$thr2}

if(-not (Test-Path $thr)){ throw "Missing thresholds: $thr1 (or $thr2)" }
$j = Get-Content $thr -Raw -Encoding utf8 | ConvertFrom-Json

$syms = @("NVDA","SPY","QQQ")
if($Symbol -ne "ALL"){ $syms = @($Symbol.ToUpperInvariant()) }

foreach($s in $syms){
  $obj = $null
  if($j.PSObject.Properties.Name -contains $s){ $obj = $j.$s }
  elseif($j.PSObject.Properties.Name -contains "DEFAULT"){ $obj = $j.DEFAULT }
  if($null -eq $obj){ Write-Host "$s -> (no entry)" ; continue }
  [pscustomobject]@{
    symbol=$s
    min_signals=$obj.min_signals
    min_pnl_samples=$obj.min_pnl_samples
    min_edge_ratio=$obj.min_edge_ratio
    min_micro_score=$obj.min_micro_score
  } | Format-Table -AutoSize
}
