[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBom {
  param([string]$Path,[string]$Text)
  $enc = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$enc)
}

$repoRoot = (Resolve-Path ".").Path
$logsDir  = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$rcPath   = Join-Path $logsDir "daily_ops_onetap_rc.txt"
$errPath  = Join-Path $logsDir "daily_ops_onetap_err.txt"
$okJson   = Join-Path $logsDir "daily_ops_onetap_last_ok.json"

# ---- HARD SAFETY: paper only ----
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"
Remove-Item Env:HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# ---- ENV CLEAN (must never inherit old experiments) ----
Remove-Item Env:HAT_LOGS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue

# Repo-local pytest basetemp to avoid pytest-of-* lock spam
$pytestTmp = Join-Path $logsDir "_pytest_tmp"
New-Item -ItemType Directory -Force -Path $pytestTmp | Out-Null

function Invoke-PSFile {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string[]]$Args = @(),
    [Parameter(Mandatory=$true)][string]$StepName
  )
  Write-Host ("[DAILY-OPS] -> {0}" -f $StepName)
  $p = $Path
  if(-not [System.IO.Path]::IsPathRooted($p)){ $p = Join-Path $repoRoot $p }
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing script: $p" }

  & powershell -NoProfile -ExecutionPolicy Bypass -File $p @Args
  if($LASTEXITCODE -ne 0){ throw ("DAILY_OPS_FAIL: {0} rc={1} file={2}" -f $StepName,$LASTEXITCODE,$p) }
}

# ---- MAIN ----
$asOf = (Get-Date).ToString("yyyy-MM-dd")
try {
  # 0) Pytest first (can clobber logs; must run before evidence build)
  try{
    $env:PYTEST_ADDOPTS = "--basetemp `"$pytestTmp`""
    Invoke-PSFile -Path ".\tools\pytest.ps1" -Args @("-q") -StepName "Pytest(anti-hijack)"
  } finally {
    Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
  }

  # 1) Evidence rebuild
  Invoke-PSFile -Path ".\tools\Run-Phase23HealthDaily.ps1" -StepName "Phase23HealthDaily"
  Invoke-PSFile -Path ".\tools\Build-EvHardEvidenceRaw.ps1" -StepName "EvHardEvidenceRaw"
  Invoke-PSFile -Path ".\tools\Export-Phase5EvHardVetoDailySnapshot.ps1" -StepName "EvHardDailySnapshot"
  Invoke-PSFile -Path ".\tools\Run-EvHardVetoDaily.ps1" -StepName "EvHardVetoDaily"

  # Phase4 + stamp (force basetemp again to avoid temp lock spam)
  try{
    $env:PYTEST_ADDOPTS = "--basetemp `"$pytestTmp`""
    Invoke-PSFile -Path ".\tools\Run-Phase4Validation.ps1" -StepName "Phase4Validation"
    Invoke-PSFile -Path ".\tools\Run-Phase4Stamp.ps1" -StepName "Phase4Stamp"
  } finally {
    Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
  }

  Invoke-PSFile -Path ".\tools\Run-GateScoreDailySummary.ps1" -Args @("-Quiet") -StepName "GateScoreDailySummary"
  Invoke-PSFile -Path ".\tools\Run-GateScoreDailyBuild.ps1" -StepName "GateScoreDailyBuild"

  # 2) Build BlockG stub to canonical logs/ no matter what the builder does internally
  $env:HAT_BLOCKG_STATUS_PATH = (Join-Path $logsDir "blockg_status_stub.json")
  Invoke-PSFile -Path ".\tools\Build-BlockGStatusStub.ps1" -StepName "BuildBlockGStatusStub"

  # 3) Final contract check (must be after evidence build)
  Invoke-PSFile -Path ".\tools\Check-BlockGReady.ps1" -Args @("-Symbol","NVDA") -StepName "BlockGReady(NVDA)"

  # 4) Intel + Phase6
  Invoke-PSFile -Path ".\tools\Run-IntelPipeline.ps1" -StepName "IntelPipeline"
  Invoke-PSFile -Path ".\tools\Run-Phase6OneTap-Notion.ps1" -StepName "Phase6OneTap+Notion"

  # Success
  $ok = [ordered]@{ as_of_date=$asOf; ok=$true; mode="paper_locked"; ts_utc=(Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json -Depth 5
  Write-Utf8NoBom -Path $okJson -Text $ok
  Write-Utf8NoBom -Path $rcPath -Text "0"
  if(Test-Path $errPath){ Remove-Item -LiteralPath $errPath -Force -ErrorAction SilentlyContinue }
  exit 0
}
catch {
  $msg = ($_ | Out-String).Trim()
  Write-Utf8NoBom -Path $errPath -Text $msg
  Write-Utf8NoBom -Path $rcPath -Text "2"
  Write-Host ("[DAILY-OPS] FAIL as_of={0} err={1}" -f $asOf,$msg) -ForegroundColor Red
  exit 2
}
finally {
  Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
}
