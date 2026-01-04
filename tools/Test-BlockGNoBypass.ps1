[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

# Institutional: Only these scripts may EXECUTE Check-BlockGReady.ps1:
# - Arm-NVDA-Live.ps1 (live arming must stay fail-closed)
# - Check-BlockGDiagnosticOk.ps1 (ops wrapper; converts exit=10 -> 0)
# - Test-BlockGWeekendSemantics.ps1 (regression test; proves ready=10 diag=0)
$allow = @(
  (Resolve-Path ".\tools\Arm-NVDA-Live.ps1" -ErrorAction SilentlyContinue).Path,
  (Resolve-Path ".\tools\Check-BlockGDiagnosticOk.ps1" -ErrorAction SilentlyContinue).Path,
  (Resolve-Path ".\tools\Test-BlockGWeekendSemantics.ps1" -ErrorAction SilentlyContinue).Path
) | Where-Object { $_ }

# Execution patterns ONLY (not mentions/docs):
$execHits = @(
  Select-String -Path .\tools\*.ps1 -ErrorAction SilentlyContinue -Pattern `
    'powershell\s+-NoProfile.*-File\s+.*Check-BlockGReady\.ps1|powershell\s+-NoProfile.*Check-BlockGReady\.ps1|&\s*"\.\\tools\\Check-BlockGReady\.ps1"|&\s*\.\\tools\\Check-BlockGReady\.ps1'
)

$bad = New-Object System.Collections.Generic.List[string]
foreach($h in $execHits){
  $p = [string]$h.Path
  if($allow -contains $p){ continue }
  $bad.Add(("{0}:{1}:{2}" -f $p, $h.LineNumber, ($h.Line.Trim()))) | Out-Null
}

if($bad.Count -gt 0){
  throw ("[TEST] Unauthorized EXECUTION of Check-BlockGReady.ps1 detected:`n" + (($bad | Sort-Object -Unique) -join "`n"))
}

Write-Host "[TEST] BlockG no-bypass OK (READY execution limited to allowlist)" -ForegroundColor Green
exit 0
