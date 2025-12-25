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
if (-not $st) { Fail "Missing/invalid Block-G status JSON at: $statusPath" }

# 3) Validate required daily quality fields (fail-closed)
# NOTE: contract defines these booleans (default false if absent)
$reqFields = @(
  "phase4_ok_today",
  "ev_hard_daily_ok_today",
  "gatescore_fresh_for_session"
)

foreach ($k in $reqFields) {
  if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail "Missing field: $k" }
  if (-not [bool]$st.$k) { Fail "$k=false" }
}

# Optional: min_samples_ok_today if present must be true
if ($st.PSObject.Properties.Name -contains "min_samples_ok_today") {
  if (-not [bool]$st.min_samples_ok_today) { Fail "min_samples_ok_today=false" }
}

# 4) Per-symbol readiness (fail-closed)
function SymReady([string]$sym) {
  $key = ($sym.ToLower() + "_blockg_ready")
  if (-not ($st.PSObject.Properties.Name -contains $key)) { return $false }
  return [bool]$st.$key
}

$s = $Symbol.ToUpper()
if ($s -eq "ALL") {
  foreach ($sym in @("NVDA","SPY","QQQ")) {
    if (-not (SymReady $sym)) { Fail "$sym not ready ($($sym.ToLower())_blockg_ready=false)" }
  }
} else {
  if (-not (SymReady $s)) { Fail "$s not ready ($($s.ToLower())_blockg_ready=false)" }
}

Write-Host "[BLOCKG] READY: Symbol=$Symbol Path=$statusPath" -ForegroundColor Green
exit 0

