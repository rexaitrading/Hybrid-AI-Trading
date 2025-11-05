param(
  [string]$CsvDir = ".\data",
  [string]$Universe = "AAPL,MSFT,AMD,TSLA",
  [int]$OrbMinutes = 15,
  [int]$Qty = 100,
  [int]$FeesCents = 0,
  [switch]$NoNotion
)
$ErrorActionPreference='Stop'
$symbols = $Universe.Split(',') | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }
$stamp   = Get-Date -Format 'yyyyMMdd'
New-Item -ItemType Directory -Force .\reports | Out-Null
$outCsv  = ".\reports\replay_summary_$stamp.csv"

$rows = New-Object System.Collections.Generic.List[Object]

foreach ($sym in $symbols) {
  $file = Join-Path $CsvDir "$($sym)_1m.csv"
  if (-not (Test-Path $file)) { Write-Host "SKIP $sym (missing $file)" -ForegroundColor DarkYellow; continue }

  $args = @(
    '-m','hybrid_ai_trading.tools.bar_replay',
    '--file', $file,
    '--symbol', $sym,
    '--mode','auto',
    '--orb-minutes', $OrbMinutes,
    '--qty', $Qty,
    '--fees', $FeesCents,
    '--force-exit'
  )
  if ($NoNotion) { $args += '--no-notion' }

  Write-Host "[replay] $sym -> $file" -ForegroundColor Cyan
  $res = & "$env:VIRTUAL_ENV\Scripts\python.exe" $args 2>&1 | Tee-Object -Variable log
  # Parse last [result] line
  $last = ($log | Where-Object { $_ -match '^\[result\]' } | Select-Object -Last 1)
  if ($last) {
    # [result] bars=40 trades=1 pnl=0.48 entry=100.5 exit=100.98 pos=...
    $m = [regex]::Match($last, 'bars=(\d+)\s+trades=(\d+)\s+pnl=([-\d\.]+)\s+entry=([-\d\.Nn][\w\.]*)\s+exit=([-\d\.Nn][\w\.]*)')
    $rows.Add([pscustomobject]@{
      Date    = (Get-Date).ToString('yyyy-MM-dd')
      Symbol  = $sym
      Bars    = [int]$m.Groups[1].Value
      Trades  = [int]$m.Groups[2].Value
      PnL     = [double]$m.Groups[3].Value
      Entry   = $m.Groups[4].Value
      Exit    = $m.Groups[5].Value
      ORB     = $OrbMinutes
      Qty     = $Qty
      Fees    = $FeesCents
    })
  }
}

# write summary
if ($rows.Count -gt 0) {
  $rows | Export-Csv -NoTypeInformation -Encoding UTF8 $outCsv
  Write-Host "âœ” Summary -> $outCsv" -ForegroundColor Green
} else {
  Write-Host "No rows to summarize." -ForegroundColor Yellow
}
