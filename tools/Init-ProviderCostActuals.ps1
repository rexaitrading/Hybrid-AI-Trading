[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOfYm = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$actualsPath = Join-Path $repoRoot "logs\provider_cost_actuals.json"
if($AsOfYm -eq ""){
  $AsOfYm = (Get-Date).ToString("yyyy-MM")
}

$tmpl = [ordered]@{
  currency = "CAD"
  as_of_ym = $AsOfYm
  actuals_monthly = [ordered]@{
    IBKR_market_data = 0
    TMX_datalinx = 0
    QuoteMedia = 0
    Barchart = 0
    Notion = 0
    Benzinga = 0
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$json = ($tmpl | ConvertTo-Json -Depth 4)
[System.IO.File]::WriteAllText($actualsPath, ($json -replace "`r`n","`n"), $utf8NoBom)

"ACTUALS_INIT_OK=1 PATH=$actualsPath" | Out-Host