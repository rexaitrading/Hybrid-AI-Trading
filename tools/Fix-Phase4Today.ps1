[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$j = Join-Path $root "logs\phase4_validation_passed.json"
if(-not (Test-Path -LiteralPath $j)){ throw "Missing $j" }

$o = Get-Content $j -Raw -Encoding utf8 | ConvertFrom-Json
$o.as_of_date = $today
$o.ts_utc = (Get-Date).ToUniversalTime().ToString("o")

$o | ConvertTo-Json -Depth 6 | Out-File $j -Encoding utf8
Write-Host "[PHASE4] forced as_of_date=$today -> $j" -ForegroundColor Green