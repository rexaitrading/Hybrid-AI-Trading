[CmdletBinding()]
param(
  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPER",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW","ALL")]
  [string]$Market = "ALL",

  [string]$OutPath = ".\logs\dashboard_status.json",

  [ValidateSet("STRICT","ALLOW_CLOSED_PAPER")]
  [string]$ClosedDayPolicy = "ALLOW_CLOSED_PAPER"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Resolve-RepoRoot(){
  $rr = (($env:HAT_REPO_ROOT + "")).Trim()
  if($rr){ return [System.IO.Path]::GetFullPath($rr) }
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr2 = Split-Path -Parent $toolsDir
  return [System.IO.Path]::GetFullPath($rr2)
}

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $enc = New-Object System.Text.UTF8Encoding($false)
  $norm = ($Text -replace "`r`n","`n")
  [System.IO.File]::WriteAllText($Path,$norm,$enc)
}

function Read-JsonOrNull([string]$p){
  try{
    if(Test-Path -LiteralPath $p){
      $raw = Get-Content -LiteralPath $p -Raw -Encoding UTF8
      if($raw -and $raw.Trim().Length -gt 0){
        return ($raw | ConvertFrom-Json -ErrorAction Stop)
      }
    }
  } catch {}
  return $null
}

$repoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$logsRoot = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null

# canonical markets (your known list)
$canonical = @("US","JP","HK","SG","IN","KR","TW")
$markets = if($Market -eq "ALL"){ $canonical } else { @($Market) }

# dashboard core fields (fail-closed defaults)
$nowLocal = (Get-Date)
$nowUtc   = (Get-Date).ToUniversalTime()

$details = @()
$anyRed = $false
$anyAmber = $false

foreach($m in $markets){
  $mUpper = $m.ToUpperInvariant()
  $mDir = Join-Path $logsRoot $mUpper

  # evidence candidates (best-effort; missing evidence => RED)
  $phase23 = Read-JsonOrNull (Join-Path $mDir "phase23_status.json")
  $phase4  = Read-JsonOrNull (Join-Path $mDir "phase4_validation_passed.json")
  $evhard  = Read-JsonOrNull (Join-Path $mDir "ev_hard_status.json")

  # todayness inference (fail-closed, schema-safe)
  $today = $nowLocal.ToString("yyyy-MM-dd")
  $todayness_ok = $false
  $todayness_reason = ""
  $p23_reason = ""

  if($phase23){
    if($phase23.PSObject.Properties.Name -contains "reason"){ $p23_reason = ("" + $phase23.reason) }

    if($phase23.PSObject.Properties.Name -contains "phase23_health_ok_today"){
      $todayness_ok = [bool]$phase23.phase23_health_ok_today
      $todayness_reason = "phase23_health_ok_today"
    } elseif($phase23.PSObject.Properties.Name -contains "phase23_ok_today"){
      $todayness_ok = [bool]$phase23.phase23_ok_today
      $todayness_reason = "phase23_ok_today"
    } elseif($phase23.PSObject.Properties.Name -contains "ok_today"){
      $todayness_ok = [bool]$phase23.ok_today
      $todayness_reason = "ok_today"
    }
  }

  if(-not $todayness_ok){
    if($phase4){
      if($phase4.PSObject.Properties.Name -contains "phase4_ok_today"){
        $todayness_ok = [bool]$phase4.phase4_ok_today
        $todayness_reason = "phase4_ok_today"
      } elseif($phase4.PSObject.Properties.Name -contains "validation_passed"){
        $todayness_ok = [bool]$phase4.validation_passed
        $todayness_reason = "validation_passed"
      } elseif($phase4.PSObject.Properties.Name -contains "ok"){
        $todayness_ok = [bool]$phase4.ok
        $todayness_reason = "ok"
      }
    }
  }

  if(-not $todayness_ok){
    $todayness_reason = "missing_todayness_signals"
  }

  # Closed-day policy:
  # - LIVE: always strict (fail-closed)
  # - PAPER/PAPERLIVE: allow closed days to proceed as AMBER (not RED)
  if((-not $todayness_ok) -and ($Mode -ne "LIVE") -and ($ClosedDayPolicy -eq "ALLOW_CLOSED_PAPER")){
    if($p23_reason -eq "market_closed_today"){
      $todayness_ok = $true
      $todayness_reason = "closed_day_allowed_for_paper"
    }
  }

  # Block-G status (best-effort; missing => AMBER; LIVE requires strict)
  $blockgPath = (Join-Path $mDir "blockg_status.json")
  if(-not (Test-Path -LiteralPath $blockgPath)){
    $blockgPath = (Join-Path $mDir "blockg_status_stub.json")
  }
  $blockg = Read-JsonOrNull $blockgPath
  $blockg_ok = $false
  $blockg_reason = ""
  if($blockg){
    if($blockg.PSObject.Properties.Name -contains "blockg_ready"){
      $blockg_ok = [bool]$blockg.blockg_ready
      $blockg_reason = "blockg.blockg_ready"
    } else {
      # Stub schema: infer readiness from global_ready_ok_today + no halts/flattens
      $gr = $null
      if($blockg.PSObject.Properties.Name -contains "global_ready_ok_today"){ $gr = [bool]$blockg.global_ready_ok_today }
      $halt = $false
      if($blockg.PSObject.Properties.Name -contains "portfolio_halt"){ $halt = [bool]$blockg.portfolio_halt }
      $flat = $false
      if($blockg.PSObject.Properties.Name -contains "risk_flatten"){ $flat = [bool]$blockg.risk_flatten }

      if($gr -ne $null){
        $blockg_ok = ([bool]$gr) -and (-not $halt) -and (-not $flat)
        $blockg_reason = "stub(global_ready_ok_today & !portfolio_halt & !risk_flatten)"
      } else {
        $blockg_ok = $false
        $blockg_reason = "blockg missing blockg_ready/global_ready_ok_today"
      }
    }
  } else {
    $blockg_ok = $false
    $blockg_reason = "blockg_status.json missing"
  }

  # risk caps + exposure placeholders (wired later; missing => AMBER)
  $risk_caps_ok = $true
  $risk_caps_reason = "not-yet-wired"
  $open_exposure = 0.0

  # kill-switch state placeholder (wired in Phase1-T2; missing => AMBER)
  $kill = Read-JsonOrNull (Join-Path $logsRoot "kill_switch_status.json")
  $kill_ok = $true
  $kill_reason = "not-yet-wired"
  if($kill -and ($kill.PSObject.Properties.Name -contains "halt_trading")){
    $kill_ok = -not [bool]$kill.halt_trading
    $kill_reason = "kill_switch.halt_trading"
  } elseif(-not $kill) {
    $kill_ok = $true
    $kill_reason = "kill_switch_status.json missing (treated as OK for now)"
  }

  # fail-closed decision
  $can_trade = $true
  $reasons = @()

  if(-not $todayness_ok){
    $can_trade = $false
    $reasons += ("todayness_fail: " + $todayness_reason)
  }

  if($Mode -eq "LIVE"){
    if(-not $blockg_ok){
      $can_trade = $false
      $reasons += ("blockg_fail: " + $blockg_reason)
    }
  } else {
    # paper modes: blockg missing => AMBER (visible but not blocking)
    if(-not $blockg_ok){
      $anyAmber = $true
      $reasons += ("blockg_warn: " + $blockg_reason)
    }
  }

  if(-not $kill_ok){
    $can_trade = $false
    $reasons += ("kill_switch_halt: " + $kill_reason)
  }

  # classify
  $sev = "GREEN"
  if(-not $can_trade){
    $sev = "RED"
    $anyRed = $true
  } elseif($reasons.Count -gt 0){
    $sev = "AMBER"
    $anyAmber = $true
  }

  $details += [ordered]@{
    market = $mUpper
    mode = $Mode
    today = $today
    todayness_ok = $todayness_ok
    blockg_ok = $blockg_ok
    risk_caps_ok = $risk_caps_ok
    open_exposure = $open_exposure
    kill_switch_ok = $kill_ok
    can_trade = $can_trade
    severity = $sev
    reasons = $reasons
    sources = [ordered]@{
      phase23_status = (Join-Path $mDir "phase23_status.json")
      phase4_validation = (Join-Path $mDir "phase4_validation_passed.json")
      ev_hard_status = (Join-Path $mDir "ev_hard_status.json")
      blockg_status = (Join-Path $mDir "blockg_status.json")
      kill_switch_status = (Join-Path $logsRoot "kill_switch_status.json")
    }
  }
}

$overall = "GREEN"
$canTradeAll = $true
if($anyRed){ $overall = "RED"; $canTradeAll = $false }
elseif($anyAmber){ $overall = "AMBER"; $canTradeAll = $true }

$outObj = [ordered]@{
  schema = "dashboard_status.v1"
  generated_at_local = $nowLocal.ToString("yyyy-MM-dd HH:mm:ss")
  generated_at_utc = $nowUtc.ToString("yyyy-MM-dd HH:mm:ss")
  mode = $Mode
  market = $Market
  severity = $overall
  can_trade = $canTradeAll
  markets = $details
}

$outJson = ($outObj | ConvertTo-Json -Depth 8)
$outFull = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutPath))
$odir = Split-Path -Parent $outFull
New-Item -ItemType Directory -Force -Path $odir | Out-Null
Write-Utf8NoBomLf -Path $outFull -Text $outJson

Write-Host ("[OK] wrote " + $outFull)
Write-Host ("[DASHBOARD] severity=" + $overall + " can_trade=" + $canTradeAll)