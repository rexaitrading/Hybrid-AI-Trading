[CmdletBinding()]
param(
  [int]$Count = 25
)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = (Get-Date).ToString('yyyy-MM-dd')
$out = Join-Path $repoRoot 'logs\paper_trades.jsonl'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null

# Build deterministic NVDA rows for today
# Keys: ts,symbol,price,signal,qty,edge_ratio,micro_score
$rows = New-Object System.Collections.Generic.List[string]

for ($i=0; $i -lt $Count; $i++) {
  $sec = 30 + $i
  $ts = "{0}T09:30:{1:00}-08:00" -f $today, $sec
  $signal = if (($i % 2) -eq 0) { "LONG" } else { "SHORT" }
  $price = 480.00 + ($i * 0.10)
  $qty = 1.0

  # small, positive edge; micro near 0
  $edge = 0.02
  $micro = 0.0

  $obj = [ordered]@{
    ts = $ts
    symbol = "NVDA"
    price = [string]("{0:0.00}" -f $price)
    signal = $signal
    qty = $qty
    edge_ratio = $edge
    micro_score = $micro
  }

  $rows.Add(($obj | ConvertTo-Json -Compress))
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, (($rows -join "`n") + "`n"), $utf8NoBom)

Write-Host "[NVDA-PAPER-TRADES] Wrote $Count rows -> $out" -ForegroundColor Green
exit 0