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
if (-not $st) { Fail "Missing/invalid Block-G status JSON at: $statusPath" }

# --- CONTRACT-ONLY READINESS (institutional, single semantic owner) ---
$sym = $Symbol
if (-not $sym) { $sym = "NVDA" }
if ($sym.ToUpperInvariant() -eq "ALL") {
  foreach($s in @("NVDA","SPY","QQQ")){
    $k = ($s.ToLower() + "_blockg_ready")
    if (-not ($st.PSObject.Properties.Name -contains $k)) { Fail "Contract missing field: $k" }
    if (-not [bool]$st.$k) { Fail "$s not ready ($k=false)" }
  }
  Write-Host "[BLOCKG] READY: Symbol=ALL Path=$statusPath" -ForegroundColor Green
  exit 0
