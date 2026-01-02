[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string[]]$Paths = @(),

  # Allows: powershell -File Test-PSParse.ps1 -Paths a b c
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Rest = @()
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"


# Normalize argv-splitting into one canonical list (dedupe, preserve order)
$all = @()
foreach($x in @($Paths) + @($Rest)){
  if(-not $x){ continue }
  $s = ("" + $x).Trim()
  if(-not $s){ continue }
  if(-not ($all -contains $s)){ $all += $s }
}
$Paths = @($all)

function Test-One([string]$p){
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing: $p" }
  $null = [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$null)
}

foreach($p in $Paths){
  Test-One $p
  Write-Host ("[PSPARSE] OK  " + $p) -ForegroundColor Green
}
exit 0
