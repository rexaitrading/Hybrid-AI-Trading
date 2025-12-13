[CmdletBinding()]
param(
  [int]$Count = 60,
  [double]$EdgeRatio = 0.03,
  [double]$MicroScore = 0.0,
  [string]$StartTime = "09:30:00-08:00"
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = (Get-Date).ToString('yyyy-MM-dd')
$out = Join-Path $repoRoot 'logs\paper_trades.jsonl'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null

$rows = New-Object System.Collections.Generic.List[string]

# parse StartTime like 09:30:00-08:00
$base = "$today" + "T" + $StartTime

for ($i=0; $i -lt $Count; $i++) {
  # spread timestamps by 1 second each (stable deterministic)
  $ts = (Get-Date $base).AddSeconds($i).ToString("yyyy-MM-ddTHH:mm:sszzz")

  $signal = if (($i % 2) -eq 0) { "LONG" } else { "SHORT" }
  $price = 480.00 + ($i * 0.10)
  $qty = 1.0

  $obj = [ordered]@{
    ts = $ts
    symbol = "NVDA"
    price = [double]("{0:0.00}" -f $price)
    signal = $signal
    qty = $qty
    edge_ratio = $EdgeRatio
    micro_score = $MicroScore
  }

  $rows.Add(($obj | ConvertTo-Json -Compress))
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, (($rows -join "`n") + "`n"), $utf8NoBom)

Write-Host "[NVDA-PAPER-TRADES] Wrote $Count rows -> $out (edge=$EdgeRatio micro=$MicroScore)" -ForegroundColor Green
exit 0