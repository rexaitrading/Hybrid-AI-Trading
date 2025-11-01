$ErrorActionPreference = 'Stop'
param(
  [string]$DbId = '2970bf31ef1580a6983ecf2c836cf97c',
  [string]$DataSourceName = 'Trading Journal',
  [Parameter(Mandatory)][string]$Title,
  [Parameter(Mandatory)][string]$Symbol,
  [Parameter(Mandatory)][ValidateSet('LONG','SHORT','BUY','SELL')][string]$Side,
  [Parameter(Mandatory)][double]$Qty,
  [double]$EntryPx,
  [double]$ExitPx,
  [double]$Price,
  [double]$RiskUsd,
  [double]$Fees,
  [double]$Slippage,
  [double]$KellyF,
  [double]$RMultiple,
  [double]$GrossPnl,
  [ValidateSet('Bull','Bear','Neutral','Volatile','Calm','RiskOff','RiskOn')][string]$Regime,
  [ValidateSet('Bullish','Bearish','Neutral')][string]$Sentiment,
  [ValidateSet('Open','Closed','Planned','Cancelled')][string]$Status,
  [string]$SessionId,
  [string]$Reason,
  [string]$Notes,
  [datetime]$Ts = (Get-Date)
)
Set-Location C:\Dev\HybridAITrading
$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { throw 'NOTION_TOKEN (Machine) not set.' }
Import-Module NotionTrader -Force
$env:NOTION_TOKEN = $tok
$res = Write-TradeJournalEntry -DbId $DbId -DataSourceName $DataSourceName -Title $Title -Symbol $Symbol -Side $Side -Qty $Qty -EntryPx $EntryPx -ExitPx $ExitPx -Price $Price -RiskUsd $RiskUsd -Fees $Fees -Slippage $Slippage -KellyF $KellyF -RMultiple $RMultiple -GrossPnl $GrossPnl -Regime $Regime -Sentiment $Sentiment -Status $Status -SessionId $SessionId -Reason $Reason -Notes $Notes -Ts $Ts
"WROTE -> {0}" -f $res.url
