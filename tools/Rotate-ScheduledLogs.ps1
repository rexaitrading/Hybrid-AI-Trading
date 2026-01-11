[CmdletBinding()]
param(
  [string]$Dir = "C:\HATJ\HybridAITrading\logs\scheduled",
  [int]$KeepDays = 14,
  [int]$KeepMaxFiles = 400,
  [string]$Prefix = "crypto24x7_"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

if(-not (Test-Path -LiteralPath $Dir)){ exit 0 }

$cut = (Get-Date).AddDays(-1 * [Math]::Abs($KeepDays))

# 1) delete old by age
Get-ChildItem -LiteralPath $Dir -File -Filter ($Prefix + "*") -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -lt $cut } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }

# 2) cap by count (newest kept)
$all = Get-ChildItem -LiteralPath $Dir -File -Filter ($Prefix + "*") -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending

if($all.Count -gt $KeepMaxFiles){
  $toDel = $all | Select-Object -Skip $KeepMaxFiles
  foreach($x in $toDel){
    Remove-Item -LiteralPath $x.FullName -Force -ErrorAction SilentlyContinue
  }
}

exit 0
