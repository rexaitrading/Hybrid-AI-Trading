[CmdletBinding()]
param(
  [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

. (Join-Path (Split-Path -Parent $PSCommandPath) "RepoRoot.ps1")
if(-not (Get-Command Get-RepoRoot -ErrorAction SilentlyContinue)){
  throw "RepoRoot.ps1 did not load Get-RepoRoot (fail-closed)"
}
$repoRoot = Get-RepoRoot

$stamp  = Join-Path $repoRoot "logs\daily_ops_onetap_last_ok.json"
$rcFile = Join-Path $repoRoot "logs\daily_ops_onetap_rc.txt"

function Write-Step([string]$msg){
  if(-not $Quiet){ Write-Host $msg }
}

function Set-RC([int]$code){
  $global:LASTEXITCODE = $code
  try {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($rcFile, ("{0}`n" -f $code), $enc)
  } catch { }
}

function Invoke-PSFile {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string[]]$Args = @(),
    [string]$StepName = "step"
  )
  if(-not (Test-Path -LiteralPath $Path)){ throw "Missing file: $Path" }

  Write-Step ("[DAILY-OPS] -> {0}" -f $StepName)

  if($Quiet){
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Path @Args 1>$null
  } else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Path @Args
  }

  $rc = $LASTEXITCODE
  if($rc -ne 0){
    throw ("DAILY_OPS_FAIL: {0} rc={1} file={2}" -f $StepName, $rc, $Path)
  }
}

# Default rc is fail unless we complete everything
Set-RC 2

# Run-once-per-day skip (only if last status=ok AND same as_of_date)
$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
try{
  if(Test-Path -LiteralPath $stamp){
    $j = Get-Content -LiteralPath $stamp -Raw -Encoding utf8 | ConvertFrom-Json
    $last = ([string]$j.as_of_date).Trim()
    $status = ""
    if($j.PSObject.Properties.Name -contains "status"){ $status = ([string]$j.status).Trim() }
    if(($status -eq "ok") -and ($last -eq $today)){
      Write-Step ("[DAILY-OPS] already ran today (as_of_date={0}). Skipping." -f $today)
      Set-RC 0
      return
    }
  }
}catch{ }

# HARD SAFETY: paper-only lock
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"
Remove-Item Env:HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

if([string]::IsNullOrWhiteSpace($env:HAT_IBG_STATUS_PATH)){
  $u = [Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")
  if(-not [string]::IsNullOrWhiteSpace($u)){ $env:HAT_IBG_STATUS_PATH = $u }
}

$steps = [ordered]@{
  blockg_nvda = $false
  intel       = $false
  phase6      = $false
}

try{
  Invoke-PSFile -Path (Join-Path $repoRoot "tools\Check-BlockGReady.ps1") -Args @("-Symbol","NVDA") -StepName "BlockGReady(NVDA)"
  $steps.blockg_nvda = $true

  Invoke-PSFile -Path (Join-Path $repoRoot "tools\Run-IntelPipeline.ps1") -StepName "IntelPipeline"
  $steps.intel = $true

  Invoke-PSFile -Path (Join-Path $repoRoot "tools\Run-Phase6OneTap-Notion.ps1") -StepName "Phase6OneTap+Notion"
  $steps.phase6 = $true

  # Derive as_of_date from Phase6 output
  try{
    $p6 = Get-Content -LiteralPath (Join-Path $repoRoot "logs\phase6_portfolio_state.json") -Raw -Encoding utf8 | ConvertFrom-Json
    if($p6 -and ($p6.PSObject.Properties.Name -contains "as_of_date")){
      $t = ([string]$p6.as_of_date).Trim()
      if(-not [string]::IsNullOrWhiteSpace($t)){ $today = $t }
    }
  }catch{ }

  # Success stamp
  $obj = [ordered]@{
    status     = "ok"
    as_of_date = $today
    ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
    symbol     = "NVDA"
    mode       = "paper_locked"
    steps      = $steps
  } | ConvertTo-Json -Depth 6

  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($stamp, (($obj -replace "`r`n","`n") + "`n"), $enc)

  if(-not $Quiet){
    Write-Host ("[DAILY-OPS] OK as_of={0} mode=paper_locked" -f $today) -ForegroundColor Green
  }
  Set-RC 0
  return
}
catch{
  $msg = ([string]$_.Exception.Message).Trim()

  # Failure stamp
  try{
    $obj = [ordered]@{
      status     = "fail"
      as_of_date = $today
      ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
      symbol     = "NVDA"
      mode       = "paper_locked"
      error      = $msg
      steps      = $steps
    } | ConvertTo-Json -Depth 6
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($stamp, (($obj -replace "`r`n","`n") + "`n"), $enc)
  }catch{ }

  if(-not $Quiet){
    Write-Host ("[DAILY-OPS] FAIL as_of={0} err={1}" -f $today, $msg) -ForegroundColor Red
  }

  Set-RC 2
  return
}
