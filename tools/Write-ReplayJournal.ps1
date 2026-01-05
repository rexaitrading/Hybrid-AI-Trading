[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [string]$BarsPath = "",
  [string]$Source = "IBKR"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if(-not $BarsPath){ throw "BarsPath required" }
if(-not (Test-Path -LiteralPath $BarsPath)){ throw "Missing BarsPath: $BarsPath" }

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$log = Join-Path $repoRoot "logs\replay_journal.jsonl"

# Minimal metadata; TODO: compute real hash + bar_count
$entry = @{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  symbol = $Symbol
  source = $Source
  bars_path = (Resolve-Path -LiteralPath $BarsPath).Path
  replay_id = ("replay_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
  data_hash = "TODO"
  bar_count = -1
} | ConvertTo-Json -Compress

Add-Content -LiteralPath $log -Encoding utf8 $entry
"[REPLAY-JOURNAL] wrote $log" | Out-Host
exit 0
