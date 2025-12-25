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

$today = (Get-Date).ToString("yyyy-MM-dd")

$bg = Read-Json -Path $BlockGPath
# Stamp is optional: fail-closed if missing (keeps Notion pipeline alive)
$st = $null
try {
  $st = Read-Json -Path $StampPath
} catch {
  Write-Host ("[NOTION] WARN: missing stamp -> fail-closed nvda_live_allowed=false :: " + $_.Exception.Message) -ForegroundColor Yellow
  $st = [pscustomobject]@{
    as_of_date = $today
    nvda_live_ready = $false
    reasons_not_ready = @("missing_nvda_live_ready_stamp")
  }
}


# Fail-closed sanity: contract + stamp must be for "today" (daily semantics)
if(($bg.as_of_date + "") -ne $today){ throw "BlockG stale: bg.as_of_date=$($bg.as_of_date) today=$today" }
# Fail-closed sanity: stamp must be for today IF it exists
if(($st.as_of_date + "") -ne $today){
  Write-Host ("[NOTION] WARN: stamp stale -> fail-closed nvda_live_allowed=false :: st.as_of_date=" + ($st.as_of_date + "") + " today=" + $today) -ForegroundColor Yellow
  $st = [pscustomobject]@{
    as_of_date = $today
    nvda_live_ready = $false
    reasons_not_ready = @("stamp_stale")
  }
}

# Contract-only payload (no recompute)
$out = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= $today

  # Primary boolean displayed in Notion
  nvda_live_allowed = ([bool]$st.nvda_live_ready -and [bool]$bg.nvda_blockg_ready)

  # Per-symbol contract flags
  nvda_blockg_ready = [bool]$bg.nvda_blockg_ready
  spy_blockg_ready  = [bool]$bg.spy_blockg_ready
  qqq_blockg_ready  = [bool]$bg.qqq_blockg_ready

  # Required daily gates (contract-only)
  phase4_ok_today          = [bool]$bg.phase4_ok_today
  ev_hard_daily_ok_today   = [bool]$bg.ev_hard_daily_ok_today
  phase23_health_ok_today  = [bool]$bg.phase23_health_ok_today
  gatescore_fresh_today    = [bool]$bg.gatescore_fresh_today
  gatescore_fresh_for_session = [bool]$bg.gatescore_fresh_for_session
  gatescore_recent_enough     = [bool]$bg.gatescore_recent_enough
  gatescore_age_days          = [int]($bg.gatescore_age_days + 0)

  # Notion-friendly: session-age policy OK even if fresh_today is false (holiday/weekend-safe)
  gatescore_session_policy_ok = (
    [bool]$bg.gatescore_fresh_for_session -and
    [bool]$bg.gatescore_recent_enough -and
    ([int]($bg.gatescore_age_days + 0) -le 3)
  )
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
