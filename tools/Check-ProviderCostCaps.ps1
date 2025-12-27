[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$capsPath = Join-Path $repoRoot "configs\provider_cost_caps.json"
$actualsPath = Join-Path $repoRoot "logs\provider_cost_actuals.json"

function Info([string]$m){ if(-not $Quiet){ Write-Host $m } }
function Fail([string]$m){ Write-Host $m -ForegroundColor Red; exit 2 }

if(-not (Test-Path -LiteralPath $capsPath)){ Fail "COST_CAPS_MISSING: $capsPath" }
if(-not (Test-Path -LiteralPath $actualsPath)){
  Fail "COST_ACTUALS_MISSING: $actualsPath (create this JSON with your current monthly actuals)"
}

$caps = Get-Content -LiteralPath $capsPath -Raw -Encoding utf8 | ConvertFrom-Json
$act  = Get-Content -LiteralPath $actualsPath -Raw -Encoding utf8 | ConvertFrom-Json

$bad = @()
foreach($k in $caps.caps_monthly.PSObject.Properties.Name){
  $cap = [double]($caps.caps_monthly.$k)
  $val = 0.0
  if($act.actuals_monthly.PSObject.Properties.Name -contains $k){ $val = [double]($act.actuals_monthly.$k) }
  if($val -gt $cap){
    $bad += "$k actual=$val cap=$cap"
  }
}

if($bad.Count -gt 0){
  Fail ("COST_CAP_EXCEEDED: " + ($bad -join "; "))
}

Info "COST_CAPS_OK=1"
exit 0