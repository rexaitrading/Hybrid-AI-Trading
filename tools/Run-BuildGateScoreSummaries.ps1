[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [switch]$StrictToday
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path

Write-Host "[GS] Build-GateScorePnlSummary" -ForegroundColor Cyan
$pnArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $repoRoot "tools\Build-GateScorePnlSummary.ps1"),"-Symbol",$Symbol)
if($StrictToday){ $pnArgs += "-StrictToday" }
& powershell @pnArgs

Write-Host "[GS] Build-GateScoreDailySummary" -ForegroundColor Cyan
# GS_DAILYSUMMARY_INVOKE_BLOCK_BEGIN (do not edit)
$dsPath = (Join-Path $repoRoot "tools\Build-GateScoreDailySummary.ps1")
if(-not (Test-Path -LiteralPath $dsPath)){ throw "Missing: $dsPath" }

# Only pass -Symbol if the script actually defines it
$dsArgs = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$dsPath)
try {
  $cmd = Get-Command $dsPath -ErrorAction Stop
  if($cmd.Parameters -and $cmd.Parameters.ContainsKey("Symbol")){
    $dsArgs += @("-Symbol",$Symbol)
  }
} catch { }

& powershell @dsArgs
# GS_DAILYSUMMARY_INVOKE_BLOCK_END (do not edit)

Write-Host "[GS] DONE" -ForegroundColor Green
