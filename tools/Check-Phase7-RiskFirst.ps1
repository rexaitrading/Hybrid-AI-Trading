param(
  [switch]$PostSlack,
  [string]$SlackChannel = "C09J0KVQLJY",
  [switch]$VerboseLog
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)  # repo root

# 0) Resolve venv python / pytest
$py = Join-Path $PWD '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Write-Warning "Venv python not found at $py; falling back to PATH."; $py='python' }

try {
  & $py -c "import importlib,sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)" 2>$null
  if ($LASTEXITCODE -ne 0) { Write-Warning 'pytest not importable. Activate venv and/or: python -m pip install -U pytest' }
} catch {
  Write-Warning 'pytest check failed'
}

# 1) Discover RISK tests
$patterns = @(
  'tests\risk\*.py',
  'tests\**\test_*risk*.py',
  'tests\**\test_risk_*.py'
)
$riskFiles = New-Object System.Collections.Generic.List[string]
foreach($p in $patterns){
  $hits = Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue
  foreach($h in $hits){ [void]$riskFiles.Add($h.FullName) }
}
$riskFiles = $riskFiles | Select-Object -Unique

# 2) Run risk tests (files or fallback -k)
$riskExit = 0
if ($riskFiles.Count -gt 0) {
  if ($VerboseLog) { Write-Host ("Running risk files ({0}):" -f $riskFiles.Count) -ForegroundColor DarkGray; $riskFiles | ForEach-Object {Write-Host "  $_" -ForegroundColor DarkGray} }
  & $py -m pytest -q @riskFiles --maxfail=1
  $riskExit = $LASTEXITCODE
} else {
  Write-Warning "No risk test files matched known patterns; falling back to marker/keyword '-k risk'"
  & $py -m pytest -q tests -k 'risk and not slow' --maxfail=1
  $riskExit = $LASTEXITCODE
}

# 3) Non-IB strategies if risk passed
$stratExit = 99
if ($riskExit -eq 0) {
  # Always run the folder to avoid Windows arg parsing issues on full paths
  if (Test-Path 'tests\strategies') {
    if ($VerboseLog) { Write-Host "Running strategies folder tests\strategies (filter: not ib and not slow)" -ForegroundColor DarkGray }
    & $py -m pytest -q tests\strategies -k 'not ib and not slow' --maxfail=1
  } else {
    Write-Warning "tests\strategies folder not found; skipping strategies."
    $LASTEXITCODE = 0
  }
  $stratExit = $LASTEXITCODE
}

# 4) Summary
$status = if ($riskExit -eq 0 -and $stratExit -eq 0) { 'GREEN' } elseif ($riskExit -ne 0) { 'RISK-RED' } else { 'STRATS-RED' }
$result = [pscustomobject]@{
  phase='Phase7-RiskFirst'; when=(Get-Date).ToString('s');
  riskExit=$riskExit; stratExit=$stratExit; status=$status
}
$result

# 5) Optional Slack
if ($PostSlack) {
  try {
    Import-Module (Join-Path $PSScriptRoot 'Slack-Alerts.psm1') -Force
    $msg = switch ($status) {
      'GREEN'      { " Phase7 GREEN | risk=$riskExit strats=$stratExit | $(Get-Date -Format s)" }
      'RISK-RED'   { " Phase7 RISK FAIL | exit=$riskExit | $(Get-Date -Format s)" }
      'STRATS-RED' { " Phase7 STRATS FAIL | exit=$stratExit | $(Get-Date -Format s)" }
    }
    Send-SlackAlert -Channel $SlackChannel -Text $msg | Out-Null
  } catch { Write-Warning "Slack post skipped: $($_.Exception.Message)" }
}

# No exit; just set code for CI
$global:LASTEXITCODE = if ($status -eq 'GREEN') { 0 } else { 1 }
