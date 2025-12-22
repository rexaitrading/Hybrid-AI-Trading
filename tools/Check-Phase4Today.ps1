[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail-Contract([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 2
}
function Fail-Script([string]$Msg){
  [Console]::Error.WriteLine($Msg)
  exit 1
}
function To-StrictBool {
  param([Parameter(Mandatory=$true)]$Value)
  if($null -eq $Value){ return $false }
  if($Value -is [bool]){ return [bool]$Value }
  if($Value -is [string]){
    $v = $Value.Trim().ToLowerInvariant()
    if($v -in @("1","true","yes","y")){ return $true }
    if($v -in @("0","false","no","n")){ return $false }
  }
  return [bool]$Value
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$path = Join-Path $repoRoot "logs\phase4_validation_passed.json"
if(-not (Test-Path $path)){
  Fail-Contract "PHASE4: missing logs/phase4_validation_passed.json"
}

try{
  $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
  $obj = $raw | ConvertFrom-Json
}catch{
  Fail-Script "PHASE4: failed to parse phase4_validation_passed.json"
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf = [string]$obj.as_of_date
if(-not $asOf){ Fail-Script "PHASE4: missing as_of_date in stamp JSON" }
if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }

if($asOf -ne $today){
  Fail-Contract "PHASE4: stale stamp as_of_date=$asOf today=$today"
}

if(-not (To-StrictBool $obj.phase4_ok_today)){
  Fail-Contract "PHASE4: phase4_ok_today is FALSE"
}

Write-Host "PHASE4: OK (as_of_date=$asOf)" -ForegroundColor Green
exit 0
