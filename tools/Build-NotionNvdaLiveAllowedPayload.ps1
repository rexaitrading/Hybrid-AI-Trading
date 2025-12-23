[CmdletBinding()]
param(
  [string]$BlockGPath = ".\logs\blockg_status_stub.json",
  [string]$StampPath  = ".\logs\nvda_live_ready_stamp.json",
  [string]$OutPath    = ".\logs\notion\nvda_live_allowed_payload.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
  param([string]$Path,[string]$Text)
  $enc = New-Object System.Text.UTF8Encoding($false)

  $repoRoot = Split-Path -Parent $PSScriptRoot
  $full = $Path
  if(-not [System.IO.Path]::IsPathRooted($full)){
    $full = Join-Path $repoRoot $Path
  }

  $t = ($Text -replace "`r`n","`n")
  if(-not $t.EndsWith("`n")){ $t += "`n" }

  $dir = Split-Path -Parent $full
  if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }

  [System.IO.File]::WriteAllText($full, $t, $enc)
}

function Read-Json {
  param([string]$Path)
  $repoRoot = Split-Path -Parent $PSScriptRoot
  $full = $Path
  if(-not [System.IO.Path]::IsPathRooted($full)){
    $full = Join-Path $repoRoot $Path
  }
  if(-not (Test-Path $full)){ throw "Missing file: $Path (resolved: $full)" }
  return (Get-Content -LiteralPath $full -Raw -Encoding utf8 | ConvertFrom-Json)
}

$bg = Read-Json -Path $BlockGPath
$st = Read-Json -Path $StampPath

$today = (Get-Date).ToString("yyyy-MM-dd")

# Fail-closed sanity: contract + stamp must be for "today" (daily semantics)
if(($bg.as_of_date + "") -ne $today){ throw "BlockG stale: bg.as_of_date=$($bg.as_of_date) today=$today" }
if(($st.as_of_date + "") -ne $today){ throw "Stamp stale: st.as_of_date=$($st.as_of_date) today=$today" }

# Contract-only payload (no recompute)
$out = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= $today

  # Primary boolean displayed in Notion
  nvda_live_allowed = [bool]$st.nvda_live_ready

  # Per-symbol contract flags
  nvda_blockg_ready = [bool]$bg.nvda_blockg_ready
  spy_blockg_ready  = [bool]$bg.spy_blockg_ready
  qqq_blockg_ready  = [bool]$bg.qqq_blockg_ready

  # Required daily gates (contract-only)
  phase4_ok_today          = [bool]$bg.phase4_ok_today
  ev_hard_daily_ok_today   = [bool]$bg.ev_hard_daily_ok_today
  phase23_health_ok_today  = [bool]$bg.phase23_health_ok_today
  gatescore_fresh_today    = [bool]$bg.gatescore_fresh_today
  gatescore_samples_ok     = [bool]$bg.gatescore_samples_ok
  gatescore_threshold_ok_today = [bool]$bg.gatescore_threshold_ok_today
  gatescore_ok_today       = [bool]$bg.gatescore_ok_today

  reasons_not_ready = @($bg.reasons_not_ready)

  # Evidence pointers (for debugging / audit trail)
  paths = @{
    blockg_status = $BlockGPath
    nvda_stamp    = $StampPath
  }
} | ConvertTo-Json -Depth 10

Write-Utf8NoBom -Path $OutPath -Text $out
Write-Host "[NOTION] wrote payload -> $OutPath" -ForegroundColor Green
