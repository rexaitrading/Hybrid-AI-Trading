[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [Parameter(Mandatory=$true)]
  [string]$BarsPath,
  [string]$Source = "IBKR",
  [string]$SessionId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Msg){
  Write-Host ("[REPLAY-JOURNAL] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

if(-not (Test-Path -LiteralPath $BarsPath)){ Fail "Missing BarsPath: $BarsPath" }

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$log = Join-Path $repoRoot "logs\replay_journal.jsonl"

$full = (Resolve-Path -LiteralPath $BarsPath).Path

# bar_count for CSV
$barCount = -1
try {
  $barCount = (Import-Csv -LiteralPath $full | Measure-Object).Count
} catch {
  Fail ("Import-Csv failed (bar_count): " + $_.Exception.Message)
}
if($barCount -lt 1){ Fail "bar_count computed < 1" }

# SHA256 file hash
$hash = ""
try {
  $hash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
} catch {
  Fail ("Get-FileHash failed: " + $_.Exception.Message)
}

$utcNow = (Get-Date).ToUniversalTime()
$rid = ("replay_" + $Symbol + "_" + $utcNow.ToString("yyyyMMdd_HHmmss"))
if(-not $SessionId){ $SessionId = $rid }

$entryObj = [ordered]@{
  ts_utc     = $utcNow.ToString("o")
  symbol     = $Symbol
  source     = $Source
  bars_path  = $full
  replay_id  = $rid
  session_id = $SessionId
  data_hash  = $hash
  bar_count  = [int]$barCount
}

$entry = ($entryObj | ConvertTo-Json -Compress)
try {
  Add-Content -LiteralPath $log -Encoding utf8 $entry
} catch {
  Fail ("Add-Content failed: " + $_.Exception.Message)
}

Write-Host ("[REPLAY-JOURNAL] OK wrote=" + $log + " replay_id=" + $rid + " bars=" + $barCount) -ForegroundColor Green
exit 0
