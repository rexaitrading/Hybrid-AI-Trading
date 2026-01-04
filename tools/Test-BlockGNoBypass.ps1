[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

# Only Arm-NVDA-Live.ps1 may directly call Check-BlockGReady.ps1 (READY semantics owner).
$hits = @(Select-String -Path .\tools\*.ps1 -Pattern 'Check-BlockGReady\.ps1' -ErrorAction SilentlyContinue)

$bad = New-Object System.Collections.Generic.List[string]
foreach($h in $hits){
  $p = [string]$h.Path
  if($p -match '\\tools\\Check-BlockGReady\.ps1$'){ continue }          # self
  if($p -match '\\tools\\Check-BlockGDiagnosticOk\.ps1$'){ continue }   # wrapper allowed
  if($p -match '\\tools\\Arm-NVDA-Live\.ps1$'){ continue }              # only allowed direct READY caller
  $bad.Add($p) | Out-Null
}

$uniq = @($bad | Sort-Object -Unique)
if($uniq.Count -gt 0){
  throw ("[TEST] Unauthorized direct callers of Check-BlockGReady.ps1:`n" + ($uniq -join "`n"))
}

Write-Host "[TEST] BlockG no-bypass OK (only Arm-NVDA-Live calls READY directly)" -ForegroundColor Green
exit 0
