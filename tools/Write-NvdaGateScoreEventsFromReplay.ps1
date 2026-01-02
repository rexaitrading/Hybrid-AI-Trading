[CmdletBinding()]
param(
  [switch]$BuildReplay = $true,
  [int]$ReplayBatch = 20,
  [string]$SessionPath = ".\logs\replay\replay_session.json",
  [string]$OutPath     = ".\logs\nvda_gatescore_events.jsonl",
  [int]$MinEvents      = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "python missing: $py" }

# Always truncate OFFICIAL first (prevents stale success)
$enc = New-Object System.Text.UTF8Encoding($false)
$outFull = if([System.IO.Path]::IsPathRooted($OutPath)){$OutPath}else{ Join-Path $repoRoot $OutPath }
[System.IO.File]::WriteAllText($outFull, "", $enc)

$env:PYTHONNOUSERSITE="1"
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path $repoRoot "src")

# --- Optional: build Phase-1 replay first (ensures enough non-degenerate rows for MinEvents) ---
if($BuildReplay){
  $sessFull = if([System.IO.Path]::IsPathRooted($SessionPath)){$SessionPath}else{ Join-Path $repoRoot $SessionPath }
  if(-not (Test-Path -LiteralPath $sessFull)){ throw "Missing replay session: $sessFull" }
  $sess = (Get-Content -LiteralPath $sessFull -Raw -Encoding utf8 | ConvertFrom-Json)
  $inCsv = ("" + $sess.bars_path).Trim()
  if([string]::IsNullOrWhiteSpace($inCsv)){ throw "replay_session.json missing bars_path" }
  $p1 = Join-Path $repoRoot "tools\Run-Phase1ReplayRealCsv.ps1"
  if(-not (Test-Path -LiteralPath $p1)){ throw "Missing Phase1 tool: $p1" }
  powershell -NoProfile -ExecutionPolicy Bypass -File $p1 -Symbol NVDA -InputCsv $inCsv -Batch $ReplayBatch | Out-Host
  if($LASTEXITCODE -notin 0,2){ throw "Phase1 replay failed (exit=$LASTEXITCODE)" }
}
# --- end optional replay build ---


& $py -m hybrid_ai_trading.gatescore.events_from_replay --session $SessionPath --logs "logs" --out $OutPath --min-events $MinEvents
$rc = $LASTEXITCODE

Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

if($rc -ne 0){
  Write-Host "[REPLAY->EVENTS] FAIL rc=$rc (official file left empty for safety)" -ForegroundColor Yellow
  exit $rc
}
Write-Host "[REPLAY->EVENTS] OK wrote official nvda_gatescore_events.jsonl" -ForegroundColor Green
exit 0
