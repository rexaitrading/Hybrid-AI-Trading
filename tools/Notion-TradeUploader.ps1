param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [string]$Token      = $env:NOTION_TOKEN,
  [string]$DatabaseId = $env:NOTION_TRADE_DB_ID,
  [switch]$DryRun
)

$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest

function New-NotionHeader([string]$Token){
  return @{
    'Authorization'  = "Bearer $Token"
    'Notion-Version' = '2022-06-28'
    'Content-Type'   = 'application/json'
  }
}

function Map-TradeToNotion([pscustomobject]$row,[string]$DbId){
  # Pre-compute Closed date string (PS5.1: if is a statement; do not inline inside a hashtable)
  $closedStart = if ([string]::IsNullOrWhiteSpace($row.timestamp_close)) { $null } else { "$($row.timestamp_close)" }

  return @{
    parent     = @{ database_id = $DbId }
    properties = @{
      Name           = @{ title     = @(@{ text = @{ content = $row.trade_id }}) }
      Symbol         = @{ rich_text = @(@{ text = @{ content = $row.symbol }}) }
      Side           = @{ select    = @{ name = $row.side } }
      Qty            = @{ number    = [double]$row.qty }
      Entry          = @{ number    = [double]$row.entry_px }
      Exit           = @{ number    = [double]$row.exit_px }
      Fees           = @{ number    = [double]$row.fees_commissions }
      Slippage       = @{ number    = [double]$row.slippage_cost }
      PnL_Net        = @{ number    = [double]$row.pnl_net }
      PnL_R          = @{ number    = [double]$row.pnl_r }
      RiskUSD        = @{ number    = [double]$row.risk_usd }
      KellyF         = @{ number    = [double]$row.kelly_f }
      Strategy       = @{ select    = @{ name = $row.strategy } }
      Setup          = @{ rich_text = @(@{ text = @{ content = $row.setup_tag }}) }
      Regime         = @{ rich_text = @(@{ text = @{ content = $row.regime }}) }
      MarketState    = @{ select    = @{ name = $row.market_state } }
      Opened         = @{ date      = @{ start = "$($row.timestamp_open)" } }
      Closed         = @{ date      = @{ start = $closedStart } }
      Account        = @{ rich_text = @(@{ text = @{ content = $row.account }}) }
      Notes          = @{ rich_text = @(@{ text = @{ content = $row.notes }}) }
    }
  }
}

# Guards (friendly messages)
if (-not (Test-Path $CsvPath))                 { throw "CSV not found: $CsvPath" }
if ([string]::IsNullOrWhiteSpace($Token))      { throw "NOTION_TOKEN missing (set env:NOTION_TOKEN or pass -Token)" }
if ([string]::IsNullOrWhiteSpace($DatabaseId)) { throw "NOTION_TRADE_DB_ID missing (set env:NOTION_TRADE_DB_ID or pass -DatabaseId)" }

$rows = Import-Csv -Path $CsvPath
$hdr  = New-NotionHeader -Token $Token
$uri  = 'https://api.notion.com/v1/pages'

$ok = 0; $fail = 0
foreach($r in $rows){
  $payload = Map-TradeToNotion -row $r -DbId $DatabaseId | ConvertTo-Json -Depth 10 -Compress
  if ($DryRun) {
    Write-Host "DRYRUN: $($r.trade_id) -> Notion" -ForegroundColor Yellow
  } else {
    try {
      $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers $hdr -Body $payload
      if ($resp.id) { $ok++ } else { $fail++ }
    } catch {
      $fail++
      Write-Host "Notion post failed: trade_id=$($r.trade_id)  $_" -ForegroundColor Red
    }
  }
}
Write-Host "Notion upload complete. ok=$ok fail=$fail" -ForegroundColor Green
