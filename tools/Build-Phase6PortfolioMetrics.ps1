[CmdletBinding()]
param(
  [string]$AsOf = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location -LiteralPath $repoRoot

function Write-Utf8NoBomLf([string]$Path,[object]$Text){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $t = ((@($Text) | ForEach-Object { [string]$_ }) -join "`n")
  $t = $t.TrimStart([char]0xFEFF) -replace "`r`n","`n"
  if ($t.Length -gt 0 -and $t[-1] -ne "`n") { $t += "`n" }
  [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($Path), $t, $utf8NoBom)
}

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logs)){
  New-Item -ItemType Directory -Force -Path $logs | Out-Null
}

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")
$outPath = Join-Path $logs "phase6_portfolio_metrics.json"

function Read-JsonlSafe([string]$Path){
  if(-not (Test-Path -LiteralPath $Path)){ return @() }
  $rows = @()
  foreach($ln in (Get-Content -LiteralPath $Path -Encoding utf8)){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try { $rows += ($s | ConvertFrom-Json -ErrorAction Stop) } catch { }
  }
  return $rows
}

$inputs = @(
  @{ sym="NVDA"; path=(Join-Path $logs "nvda_phase5_paperlive_results_today.jsonl") },
  @{ sym="SPY";  path=(Join-Path $logs "spy_phase5_paperlive_results_today.jsonl") },
  @{ sym="QQQ";  path=(Join-Path $logs "qqq_phase5_paperlive_results_today.jsonl") }
)

$symbolStats = @()
foreach($it in $inputs){
  $rows = Read-JsonlSafe $it.path
  $sumPnl = 0.0
  foreach($r in $rows){
  # Guard: only objects can have properties; ignore primitives/arrays/null
  if($null -eq $r){ continue }
  if(-not ($r -is [psobject])){ continue }

  try {
    if($null -ne $r.PSObject.Properties["realized_pnl"] -and $null -ne $r.realized_pnl){
      $v = $r.realized_pnl
      if($v -is [ValueType] -or ($v -is [string] -and $v.Trim() -ne "")){ $sumPnl += [double]$v }
      continue
    }
    if($null -ne $r.PSObject.Properties["pnl"] -and $null -ne $r.pnl){
      $v = $r.pnl
      if($v -is [ValueType] -or ($v -is [string] -and $v.Trim() -ne "")){ $sumPnl += [double]$v }
      continue
    }
  } catch {
    # ignore parse/convert errors; fail-soft
  }
}
  $symbolStats += [pscustomobject]@{
    symbol = $it.sym
    rows   = @($rows).Count
    realized_pnl_sum = $sumPnl
    source_exists = (Test-Path -LiteralPath $it.path)
  }
}

$obj = [pscustomobject]@{
  asof   = $today
  ts_utc = $tsUtc
  phase6 = [pscustomobject]@{
    portfolio_metrics_version = 1
    symbols = $symbolStats
  }
}

Write-Utf8NoBomLf -Path $outPath -Text ($obj | ConvertTo-Json -Depth 8)
Write-Host "[PHASE6] wrote: $outPath" -ForegroundColor Cyan
exit 0

