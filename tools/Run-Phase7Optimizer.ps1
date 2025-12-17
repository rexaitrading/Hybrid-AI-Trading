param(
  [string]$Phase6SummaryCsv = "logs\phase6_daily_summary.csv",
  [string]$OutJson = "logs\phase7_allocation.json",
  [string]$OutCsv  = "logs\phase7_allocation.csv"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if(-not (Test-Path $Phase6SummaryCsv)){
  Write-Host "[PHASE7] FAIL-CLOSED: missing Phase-6 summary: $Phase6SummaryCsv" -ForegroundColor Red
  exit 2
}

$rows = Import-Csv -Path $Phase6SummaryCsv
if(-not $rows -or $rows.Count -eq 0){
  Write-Host "[PHASE7] FAIL-CLOSED: empty Phase-6 summary" -ForegroundColor Red
  exit 3
}

$strats = $rows | ForEach-Object { $_.strategy_id } | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique
if(-not $strats -or $strats.Count -eq 0){
  Write-Host "[PHASE7] FAIL-CLOSED: no strategy_id in Phase-6 summary" -ForegroundColor Red
  exit 4
}

$w = 1.0 / [double]$strats.Count
$alloc = foreach($s in $strats){
  [pscustomobject]@{ strategy_id = $s; weight = $w }
}

$alloc | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $OutCsv

$map = @{}
foreach($a in ($alloc | Sort-Object strategy_id)){
  $map[$a.strategy_id] = [double]$a.weight
}

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  source = "Run-Phase7Optimizer.ps1"
  phase6_summary = $Phase6SummaryCsv
  weights = $map
}

$payload | ConvertTo-Json -Depth 10 | Set-Content -Path $OutJson -Encoding UTF8

Write-Host "[PHASE7] OK: wrote $OutJson and $OutCsv" -ForegroundColor Green
exit 0