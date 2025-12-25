[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$src = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$out = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  [System.IO.File]::WriteAllText((Resolve-Path $Path).Path, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $src)) {
  Write-Utf8NoBomLf -Path $out -Text "symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date"
  Write-Host "[GS-DAILY] FAIL-CLOSED: missing $src (wrote header only)" -ForegroundColor Yellow
  exit 2
}

$rows = @(Import-Csv -LiteralPath $src)
if (-not $rows -or $rows.Count -eq 0) {
  Write-Utf8NoBomLf -Path $out -Text "symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date"
  Write-Host "[GS-DAILY] FAIL-CLOSED: zero rows in $src (wrote header only)" -ForegroundColor Yellow
  exit 2
}

# Latest available session date (YYYY-MM-DD string sort is OK)
$latestDate = ($rows | Sort-Object as_of_date -Descending | Select-Object -First 1).as_of_date
$use = @($rows | Where-Object { ($_.as_of_date + "") -eq ($latestDate + "") })

if (-not $use -or $use.Count -eq 0) {
  Write-Utf8NoBomLf -Path $out -Text "symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date"
  Write-Host "[GS-DAILY] FAIL-CLOSED: no rows for latestDate=$latestDate (wrote header only)" -ForegroundColor Yellow
  exit 2
}

# Convert quoted CSV -> plain schema expected by other tools
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date") | Out-Null

foreach ($r in ($use | Sort-Object symbol)) {
  $lines.Add(("{0},{1},{2},{3},{4},{5},{6}" -f
    $r.symbol,$r.count_signals,$r.mean_edge_ratio,$r.mean_micro_score,$r.pnl_samples,$r.mean_pnl,$r.as_of_date
  )) | Out-Null
}

Write-Utf8NoBomLf -Path $out -Text ($lines -join "`n")
Write-Host "[GS-DAILY] OK wrote $out rows=$($use.Count) latestDate=$latestDate" -ForegroundColor Green
exit 0
