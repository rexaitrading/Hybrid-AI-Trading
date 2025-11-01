$ErrorActionPreference = 'Stop'
param(
  [string]$DbId,
  [string]$DataSourceName,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$true)][string]$Symbol,
  [Parameter(Mandatory=$true)][string]$Side,
  [Parameter(Mandatory=$true)][Nullable[Double]]$Qty,
  [Nullable[Double]]$EntryPx,
  [Nullable[Double]]$ExitPx,
  [Nullable[Double]]$Price,
  [Nullable[Double]]$RiskUsd,
  [Nullable[Double]]$Fees,
  [Nullable[Double]]$Slippage,
  [Nullable[Double]]$KellyF,
  [Nullable[Double]]$RMultiple,
  [Nullable[Double]]$GrossPnl,
  [string]$Regime,
  [string]$Sentiment,
  [string]$Status,
  [string]$SessionId,
  [string]$Reason,
  [string]$Notes,
  [Nullable[datetime]]$Ts
)

Set-Location C:\Dev\HybridAITrading

# defaults (PS5-safe)
if (-not $DbId)           { $DbId = '2970bf31ef1580a6983ecf2c836cf97c' }
if (-not $DataSourceName) { $DataSourceName = 'Trading Journal' }
if (-not $Ts)             { $Ts = Get-Date }

# validate enums in body
$validSides  = @('LONG','SHORT','BUY','SELL')
$validStatus = @('Open','Closed','Planned','Cancelled')
if (-not $validSides.Contains($Side))   { throw "Parameter -Side must be one of: $($validSides -join ', ')" }
if (-not $validStatus.Contains($Status)){ throw "Parameter -Status must be one of: $($validStatus -join ', ')" }

# coerce nullables to plain numbers where present
function N([Nullable[Double]]$x){ if($null -eq $x){ $null } else { [double]$x } }

$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { throw 'NOTION_TOKEN (Machine) not set.' }
Import-Module NotionTrader -Force
$env:NOTION_TOKEN = $tok

$res = Write-TradeJournalEntry `
  -DbId $DbId -DataSourceName $DataSourceName -Title $Title -Symbol $Symbol -Side $Side -Qty (N $Qty) `
  -EntryPx (N $EntryPx) -ExitPx (N $ExitPx) -Price (N $Price) -RiskUsd (N $RiskUsd) -Fees (N $Fees) -Slippage (N $Slippage) `
  -KellyF (N $KellyF) -RMultiple (N $RMultiple) -GrossPnl (N $GrossPnl) -Regime $Regime -Sentiment $Sentiment `
  -Status $Status -SessionId $SessionId -Reason $Reason -Notes $Notes -Ts $Ts

"WROTE -> {0}" -f $res.url
