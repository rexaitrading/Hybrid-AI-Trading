[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [switch]$Build,

  [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# If -Quiet is used, propagate to any child scripts via env var
if($Quiet){ $env:HAT_BLOCKG_QUIET = "1" }
# HAT_IBG_HEALTH_GATE_MIN (exit 3; observe-only; no kills)
$ibgTool = Join-Path $toolsDir "Get-IBGHealth.ps1"
if(Test-Path -LiteralPath $ibgTool){
  $p = [string]$env:HAT_IBG_STATUS_PATH
  if([string]::IsNullOrWhiteSpace($p)){
    $p = [System.Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")
  }
  $ibg = & $ibgTool -StatusPath $p
  if(-not $ibg.ok){ if(-not $Quiet){ Write-Host "[BLOCKG] IBG NOT HEALTHY" -ForegroundColor Red; Write-Host ($ibg.reasons -join "; ") -ForegroundColor Red }; exit 3 }
}



# --- Quiet-aware info output (failures remain noisy) ---
function Write-BlockGInfo {
  param([Parameter(ValueFromRemainingArguments=$true)][object[]]$Args)
  if($Quiet -or ($env:HAT_BLOCKG_QUIET -eq "1")){ return }
  Write-Host @Args
}


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
  try {
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path).Path)
    $text  = [System.Text.Encoding]::UTF8.GetString($bytes)
    if($text.Length -gt 0 -and [int]$text[0] -eq 0xFEFF){ $text = $text.Substring(1) } # BOM
    if (-not $text) { return $null }
    return ($text | ConvertFrom-Json -ErrorAction Stop)
  } catch {
    return $null
  }
}

function Fail-Contract([string]$Msg) {
  Write-BlockGInfo "[BLOCKG] NOT READY: $Msg" -ForegroundColor Red
  exit 2
}


function Fail([string]$Msg) {
  # Backward-compatible shim: treat any Fail() usage as contract failure (exit 2)
  Fail-Contract $Msg
}
function Fail-Script([string]$Msg) {
  Write-BlockGInfo "[BLOCKG] ERROR: $Msg" -ForegroundColor Yellow
  exit 1
}
# 1) Optional build step (single semantic owner)
if ($Build) {
  $builder = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
  if (-not (Test-Path -LiteralPath $builder)) { Fail "Missing builder: $builder" }

if ($env:HAT_BLOCKG_BUILT_ONCE -ne "1" -and $env:HAT_BLOCKG_QUIET -ne "1") {
if((-not $Quiet) -and ($env:HAT_BLOCKG_QUIET -ne "1")){
  Write-BlockGInfo "[BLOCKG] Build requested: running Build-BlockGStatusStub.ps1"
}
}
  powershell -NoProfile -ExecutionPolicy Bypass -File $builder | Out-Host
  if ($LASTEXITCODE -ne 0) { Fail "Build-BlockGStatusStub.ps1 failed exit=$LASTEXITCODE" }
}

# 2) Load contract JSON (contract-only validation)
$defaultPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
$statusPath = $env:HAT_BLOCKG_STATUS_PATH
if (-not $statusPath) { $statusPath = $defaultPath }

$st = Read-Json $statusPath
if (-not $st) { Fail "Missing/invalid Block-G status JSON at: $statusPath" }


# ---- Contract semantics owner (single source of truth) ----
# NOTE: Do NOT recompute. Do NOT duplicate checks elsewhere in this script.
# All go/no-go semantics happen in the read-only contract decision block below.

# ---- Contract read-only decision (institutional, deterministic) ----
try {
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $statusPath = $env:HAT_BLOCKG_STATUS_PATH
  if(-not $statusPath){ $statusPath = Join-Path $repoRoot "logs\blockg_status_stub.json" }
  if(-not (Test-Path $statusPath)){ Fail "Missing contract: $statusPath" }

  $j = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json

  # 1) Today-ness (fail-closed)
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $asOf = (($j.as_of_date + "")).Trim()
  if($asOf -ne $today){ Fail ("stale as_of_date=" + $asOf + " today=" + $today) }

  # 2) Required quality fields (contract-only)
  $reqFields = @(
    "phase23_health_ok_today",
    "ev_hard_daily_ok_today",
    "phase4_ok_today",
    "gatescore_ok_today",
    "gatescore_fresh_today",
    "gatescore_recent_enough",
    "gatescore_samples_ok",
    "gatescore_threshold_ok_today"
  )
  foreach($k in $reqFields){
    if(-not ($j.PSObject.Properties.Name -contains $k)){ Fail ("Missing field: " + $k) }
    if(-not [bool]$j.$k){ Fail ($k + "=false") }
  }

  # 3) GateScore age policy (contract-only)
  $MAX_GS_AGE_DAYS = 3
  if(-not ($j.PSObject.Properties.Name -contains "gatescore_age_days")){ Fail "Missing field: gatescore_age_days" }
  try { $age = [int]$j.gatescore_age_days } catch { Fail "gatescore_age_days invalid" }
  if($age -gt $MAX_GS_AGE_DAYS){ Fail ("gatescore_age_days=" + $age + " max=" + $MAX_GS_AGE_DAYS) }

  # 4) Per-symbol readiness
  $sym = ($Symbol + "").Trim().ToUpper()
  if($sym -eq "ALL"){
    foreach($s0 in @("NVDA","SPY","QQQ")){
      $k0 = @{"NVDA"="nvda_blockg_ready";"SPY"="spy_blockg_ready";"QQQ"="qqq_blockg_ready"}[$s0]
      if(-not $k0){ Fail ("Unknown symbol: " + $s0) }
      $ok0 = $false
      try { $ok0 = [bool]$j.$k0 } catch { $ok0 = $false }
      if(-not $ok0){ Fail ("contract " + $k0 + "=false reasons=" + (($j.reasons_not_ready + "") -join ",")) }
    }
  } else {
    $k = @{"NVDA"="nvda_blockg_ready";"SPY"="spy_blockg_ready";"QQQ"="qqq_blockg_ready"}[$sym]
    if(-not $k){ Fail ("Unknown symbol: " + $sym) }
    $ok = $false
    try { $ok = [bool]$j.$k } catch { $ok = $false }
    if(-not $ok){ Fail ("contract " + $k + "=false reasons=" + (($j.reasons_not_ready + "") -join ",")) }
  }

  if($env:HAT_BLOCKG_QUIET -ne "1"){
    if((-not $Quiet) -and ($env:HAT_BLOCKG_QUIET -ne "1")){
      Write-BlockGInfo "[BLOCKG] READY: Symbol=$Symbol Path=$statusPath"
    }
  }
} catch {
  Fail ("Contract read-only decision error: " + $_.Exception.Message)
}
# ---- end contract read-only decision ----

exit 0
