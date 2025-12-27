[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$csv = Join-Path $root "logs\phase5_ev_hard_veto_daily.csv"
if(-not (Test-Path -LiteralPath $csv)){ throw "Missing $csv" }

$rows = @((Import-Csv $csv))
if($rows.Count -eq 0){ throw "Empty $csv" }

if(-not ($rows[0].PSObject.Properties.Name -contains "date")){
  throw ("Missing column 'date' in $csv. Columns=" + (($rows[0].PSObject.Properties.Name) -join ","))
}

$rows[-1].date = $today
$rows | Export-Csv $csv -NoTypeInformation -Encoding utf8

Write-Host "[EV-HARD] forced last-row date=$today -> $csv" -ForegroundColor Green