[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$root = (Resolve-Path ".").Path
Set-Location $root
if(-not (Test-Path ".\.git")){ throw "NOT IN REPO ROOT" }

function Run-Step([string]$name, [scriptblock]$sb){
  Write-Host "`n==================== $name ====================" -ForegroundColor Cyan
  & $sb
  Write-Host "[OK] $name" -ForegroundColor Green
}

function Run-PS([string]$path, [string[]]$args=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }
  $a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$path) + $args
  & powershell @a
  $code = [int]$LASTEXITCODE
  if($code -ne 0){ throw "Tool failed: $path exit=$code" }
  return $code
}

function Run-PSAllowExit([string]$path, [int[]]$okExits, [string[]]$args=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }
  $a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$path) + $args
  & powershell @a
  $code = [int]$LASTEXITCODE
  if(-not ($okExits -contains $code)){ throw "Tool failed: $path exit=$code" }
  return $code
}

Run-Step "Phase4: Stamp (todayness)" { Run-PS ".\tools\Run-Phase4Stamp.ps1" }

Run-Step "Phase23: Health daily" { Run-PS ".\tools\Run-Phase23HealthDaily.ps1" }

Run-Step "Phase5: EV-hard snapshot" { Run-PS ".\tools\Build-EvHardSnapshot.ps1" }

Run-Step "Phase5: EV-hard daily veto row" { Run-PS ".\tools\Run-EvHardVetoDaily.ps1" }

Run-Step "Phase3: GateScore PnL summary" { Run-PS ".\tools\Build-GateScorePnlSummary.ps1" }

Run-Step "BlockG: Build contract" { Run-PS ".\tools\Build-BlockGStatusStub.ps1" @("-Symbol",$Symbol) }

Run-Step "BlockG: Contract-only checker (deterministic)" {
  $code = Run-PSAllowExit ".\tools\Check-BlockGReady.ps1" @(0,2) @("-Symbol",$Symbol)
  if($code -eq 0){
    Write-Host "[BLOCKG] READY (exit=0)" -ForegroundColor Green
  } else {
    Write-Host "[BLOCKG] NOT READY (exit=2) - expected fail-closed state" -ForegroundColor Yellow
  }
}

Run-Step "Test slice: BlockG + execution guards" {
  & pytest -q `
    tests/test_blockg_enforce.py `
    tests/execution/test_blockg_order_manager_guard.py
  if($LASTEXITCODE -ne 0){ throw "pytest slice failed exit=$LASTEXITCODE" }
}

Write-Host "`nDONE: Run-Phase1ToPhase7Daily completed successfully." -ForegroundColor Yellow
exit 0
