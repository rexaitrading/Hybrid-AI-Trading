[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# --- Normalize symbol early (defensive, deterministic) ---
$s = ($Symbol + "").ToUpperInvariant()
if($s -notin @("NVDA","SPY","QQQ","ALL")){ Fail-Script ("Invalid -Symbol=" + $Symbol) }
# --- END normalize ---


function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n", "`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  [System.IO.File]::WriteAllText((Resolve-Path $Path).Path, $Text, $utf8NoBom)
}

function Read-Json {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $raw = Get-Content -LiteralPath $Path -Encoding utf8 -Raw
  if (-not $raw) { return $null }
  return ($raw | ConvertFrom-Json -ErrorAction Stop)
}

function Fail-Contract([string]$Msg) {
  Write-Host "[BLOCKG] NOT READY: $Msg" -ForegroundColor Red
  exit 2
}


function Fail([string]$Msg) {
  # Backward-compatible shim: treat any Fail() usage as contract failure (exit 2)
  Fail-Contract $Msg
}
function Fail-Script([string]$Msg) {
  Write-Host "[BLOCKG] ERROR: $Msg" -ForegroundColor Yellow
  exit 1
}
# 1) Optional build step (single semantic owner)
if ($Build) {
  $builder = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
  if (-not (Test-Path -LiteralPath $builder)) { Fail "Missing builder: $builder" }

  Write-Host "[BLOCKG] Build requested: running Build-BlockGStatusStub.ps1" -ForegroundColor Cyan
  powershell -NoProfile -ExecutionPolicy Bypass -File $builder | Out-Host
  if ($LASTEXITCODE -ne 0) { Fail "Build-BlockGStatusStub.ps1 failed exit=$LASTEXITCODE" }
}

# 2) Load contract JSON (contract-only validation)
$defaultPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
$statusPath = $env:HAT_BLOCKG_STATUS_PATH
if (-not $statusPath) { $statusPath = $defaultPath }

$st = Read-Json $statusPath
# MARKET_CLOSED_FAILCLOSED_CHECK_BEGIN
# Institutional clarity: when market is closed we fail-closed with an explicit operator message.
try {
  if ($st -and ($st.PSObject.Properties.Name -contains "market_closed_today") -and [bool]$st.market_closed_today) {
    Fail "market_closed_today=true (fail-closed; readiness not evaluated on closed days)"
  }
} catch { }
# MARKET_CLOSED_FAILCLOSED_CHECK_END
if (-not $st) { Fail "Missing/invalid Block-G status JSON at: $statusPath" }

# --- GateScore session-age policy (contract-only; do not recompute) ---
$MAX_GS_AGE_DAYS = 3
# 3A) Per-symbol GateScore validation (contract-only)
function Get-GS([string]$sym){
  if(-not ($st.PSObject.Properties.Name -contains "gatescore_by_symbol")){ return $null }
  $gsb = $st.gatescore_by_symbol
  if($null -eq $gsb){ return $null }
  $k = $sym.ToUpperInvariant()
  if(-not ($gsb.PSObject.Properties.Name -contains $k)){ return $null }
  return $gsb.$k
}

# 3) Validate required daily quality fields (fail-closed)
# NOTE: contract defines these booleans (default false if absent)
$reqFields = @(
  "phase4_ok_today",
  "ev_hard_daily_ok_today",
  "gatescore_fresh_today"
)

foreach ($k in $reqFields) {
  if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail "Missing field: $k" }
  if (-not [bool]$st.$k) { Fail "$k=false" }
}

# GateScore age policy (fail-closed)
if (-not [bool]$st.gatescore_recent_enough) { Fail "gatescore_recent_enough=false" }
try { $age = [int]$st.gatescore_age_days } catch { Fail "gatescore_age_days invalid" }
if ($age -gt $MAX_GS_AGE_DAYS) { Fail ("gatescore_age_days=" + $age + " max=" + $MAX_GS_AGE_DAYS) }
# Per-symbol GateScore checks (contract-only)
if ($s -ne "ALL") {
  $gs = Get-GS $s
  if (-not $gs) { Fail ("Missing gatescore_by_symbol." + $s) }
  if (-not [bool]$gs.samples_ok) { Fail ($s + " gatescore samples_ok=false") }
  if (-not [bool]$gs.threshold_ok) { Fail ($s + " gatescore threshold_ok=false") }
} else {
  foreach($sym in @("NVDA","SPY","QQQ")) {
    $gs = Get-GS $sym
    if (-not $gs) { Fail ("Missing gatescore_by_symbol." + $sym) }
    if (-not [bool]$gs.samples_ok) { Fail ($sym + " gatescore samples_ok=false") }
    if (-not [bool]$gs.threshold_ok) { Fail ($sym + " gatescore threshold_ok=false") }
  }
}


# 4) Per-symbol readiness (fail-closed)
function SymReady([string]$sym) {
  $key = ($sym.ToLower() + "_blockg_ready")
  if (-not ($st.PSObject.Properties.Name -contains $key)) { return $false }
  return [bool]$st.$key
}
# $s normalized earlier
if ($s -eq "ALL") {
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    if (-not (SymReady $sym)) { Fail "$sym not ready ($($sym.ToLower())_blockg_ready=false)" }
  }
} else {
  if (-not (SymReady $s)) { Fail "$s not ready ($($s.ToLower())_blockg_ready=false)" }
}

Write-Host "[BLOCKG] READY: Symbol=$Symbol Path=$statusPath" -ForegroundColor Green
exit 0

