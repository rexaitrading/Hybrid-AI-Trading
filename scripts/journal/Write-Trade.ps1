$ErrorActionPreference = 'Stop'
param(
  [string]$DbId,
  [string]$DataSourceName,
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$true)][string]$Symbol,
  [Parameter(Mandatory=$true)][string]$Side,      # validate in body
  [Parameter(Mandatory=$true)][double]$Qty,
  [double]$EntryPx,
  [double]$ExitPx,
  [double]$Price,
  [double]$RiskUsd,
  [double]$Fees,
  [double]$Slippage,
  [double]$KellyF,
  [double]$RMultiple,
  [double]$GrossPnl,
  [string]$Regime,
  [string]$Sentiment,
  [string]$Status,                                # validate in body
  [string]$SessionId,
  [string]$Reason,
  [string]$Notes,
  [datetime]$Ts = (Get-Date)
)

Set-Location C:\Dev\HybridAITrading

# Defaults (PS5-safe)
if (-not $DbId)           { $DbId = '2970bf31ef1580a6983ecf2c836cf97c' }
if (-not $DataSourceName) { $DataSourceName = 'Trading Journal' }

# Validate Side/Status values in body (avoid ValidateSet parser quirks)
$validSides  = @('LONG','SHORT','BUY','SELL')
$validStatus = @('Open','Closed','Planned','Cancelled')
if (-not $validSides.Contains($Side))  { throw "Parameter -Side must be one of: $($validSides -join ', ')" }
if (-not $validStatus.Contains($Status)) { throw "Parameter -Status must be one of: $($validStatus -join ', ')" }

$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { throw 'NOTION_TOKEN (Machine) not set.' }

Import-Module NotionTrader -Force
$env:NOTION_TOKEN = $tok

$res = Write-TradeJournalEntry `
  -DbId $DbId -DataSourceName $DataSourceName -Title $Title -Symbol $Symbol -Side $Side -Qty $Qty `
  -EntryPx $EntryPx -ExitPx $ExitPx -Price $Price -RiskUsd $RiskUsd -Fees $Fees -Slippage $Slippage `
  -KellyF $KellyF -RMultiple $RMultiple -GrossPnl $GrossPnl -Regime $Regime -Sentiment $Sentiment `
  -Status $Status -SessionId $SessionId -Reason $Reason -Notes $Notes -Ts $Ts

"WROTE -> {0}" -f $res.url
