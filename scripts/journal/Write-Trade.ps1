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

$ErrorActionPreference = 'Stop'
Set-Location C:\Dev\HybridAITrading

# defaults
if (-not $DbId)           { $DbId = '2970bf31ef1580a6983ecf2c836cf97c' }
if (-not $DataSourceName) { $DataSourceName = 'Trading Journal' }
if (-not $Ts)             { $Ts = Get-Date }

# validate required enums (Side/Status)
$validSides  = @('LONG','SHORT','BUY','SELL')
$validStatus = @('Open','Closed','Planned','Cancelled')
if (-not $validSides.Contains($Side))    { throw "Parameter -Side must be one of: $($validSides -join ', ')" }
if (-not $validStatus.Contains($Status)) { throw "Parameter -Status must be one of: $($validStatus -join ', ')" }

# number coercion helper
function N([Nullable[Double]]$x){ if($null -eq $x){ $null } else { [double]$x } }

$tok = [Environment]::GetEnvironmentVariable('NOTION_TOKEN','Machine')
if (-not $tok) { throw 'NOTION_TOKEN (Machine) not set.' }
Import-Module NotionTrader -Force
$env:NOTION_TOKEN = $tok

# build splat hashtable (only add keys if not null)
$Splat = @{
  DbId            = $DbId
  DataSourceName  = $DataSourceName
  Title           = $Title
  Symbol          = $Symbol
  Side            = $Side
  Qty             = N $Qty
  Status          = $Status
  Ts              = $Ts
}

if ($EntryPx   -ne $null) { $Splat['EntryPx']   = N $EntryPx }
if ($ExitPx    -ne $null) { $Splat['ExitPx']    = N $ExitPx }
if ($Price     -ne $null) { $Splat['Price']     = N $Price }
if ($RiskUsd   -ne $null) { $Splat['RiskUsd']   = N $RiskUsd }
if ($Fees      -ne $null) { $Splat['Fees']      = N $Fees }
if ($Slippage  -ne $null) { $Splat['Slippage']  = N $Slippage }
if ($KellyF    -ne $null) { $Splat['KellyF']    = N $KellyF }
if ($RMultiple -ne $null) { $Splat['RMultiple'] = N $RMultiple }
if ($GrossPnl  -ne $null) { $Splat['GrossPnl']  = N $GrossPnl }
if ($SessionId)           { $Splat['SessionId'] = $SessionId }
if ($Reason)              { $Splat['Reason']    = $Reason }
if ($Notes)               { $Splat['Notes']     = $Notes }
if ($Regime)              { $Splat['Regime']    = $Regime }
if ($Sentiment)           { $Splat['Sentiment'] = $Sentiment }

$res = Write-TradeJournalEntry @Splat
"WROTE -> {0}" -f $res.url
