[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [string[]]$Paths = @(),

  # Allows: powershell -File Test-PSParse.ps1 -Paths a b c
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$Rest = @()
)Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$Paths = @($Paths) + @($Rest)
$Paths = @($Paths) + @($Rest)
function Test-One([string]$p){
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing: $p" }
  $null = [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$null)
}

foreach($p in $Paths){
  Test-One $p
  Write-Host ("[PSPARSE] OK  " + $p) -ForegroundColor Green
}
exit 0
