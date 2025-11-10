# === Trade Journal Writer (PS 5.1-safe, UTF-8 no-BOM + LF) ===

$ErrorActionPreference = 'Stop'

# Fixed CSV header (canonical order)
$script:TradeCsvHeader = @(
  'trade_id','run_id','account','timestamp_open','timestamp_close','symbol','asset_class','side','qty',
  'entry_px','exit_px','avg_add_px','avg_reduce_px','fees_commissions','slippage_cost',
  'pnl_gross','pnl_net','pnl_r','risk_usd','kelly_f','max_adverse_excursion','max_favorable_excursion',
  'holding_sec','strategy','setup_tag','regime','market_state','order_ids','notes','screenshot_path'
)

function New-TradeRecord {
  param(
    [Parameter(Mandatory=$true)][string]$trade_id,
    [Parameter(Mandatory=$true)][string]$symbol,
    [Parameter(Mandatory=$true)][ValidateSet('equity','futures','forex','crypto')][string]$asset_class,
    [Parameter(Mandatory=$true)][ValidateSet('LONG','SHORT')][string]$side,
    [Parameter(Mandatory=$true)][double]$qty,
    [Parameter(Mandatory=$true)][double]$entry_px,
    [Parameter(Mandatory=$true)][double]$risk_usd,
    [Parameter(Mandatory=$true)][string]$strategy,
    [string]$timestamp_open = (Get-Date).ToString('s'),
    [string]$run_id = '',
    [string]$account = 'PAPER-IBG-4002',
    [string]$timestamp_close = '',
    [double]$exit_px = 0,
    [double]$avg_add_px = 0,
    [double]$avg_reduce_px = 0,
    [double]$fees_commissions = 0,
    [double]$slippage_cost = 0,
    [double]$pnl_gross = 0,
    [double]$pnl_net = 0,
    [double]$pnl_r = 0,
    [double]$kelly_f = 0,
    [double]$max_adverse_excursion = 0,
    [double]$max_favorable_excursion = 0,
    [int]$holding_sec = 0,
    [string]$setup_tag = '',
    [string]$regime = '',
    [string]$market_state = 'REG',
    [string]$order_ids = '',
    [string]$notes = '',
    [string]$screenshot_path = ''
  )
  $row = [ordered]@{
    trade_id=$trade_id; run_id=$run_id; account=$account
    timestamp_open=$timestamp_open; timestamp_close=$timestamp_close
    symbol=$symbol; asset_class=$asset_class; side=$side; qty=$qty
    entry_px=$entry_px; exit_px=$exit_px; avg_add_px=$avg_add_px; avg_reduce_px=$avg_reduce_px
    fees_commissions=$fees_commissions; slippage_cost=$slippage_cost
    pnl_gross=$pnl_gross; pnl_net=$pnl_net; pnl_r=$pnl_r
    risk_usd=$risk_usd; kelly_f=$kelly_f
    max_adverse_excursion=$max_adverse_excursion; max_favorable_excursion=$max_favorable_excursion
    holding_sec=$holding_sec; strategy=$strategy; setup_tag=$setup_tag
    regime=$regime; market_state=$market_state; order_ids=$order_ids; notes=$notes; screenshot_path=$screenshot_path
  }
  return New-Object PSObject -Property $row
}

function Close-Trade {
  param(
    [Parameter(Mandatory=$true)][pscustomobject]$Record,
    [Parameter(Mandatory=$true)][double]$ExitPx,
    [int]$HoldingSec = 0,
    [double]$Fees = 0,
    [double]$Slippage = 0
  )
  $Record.timestamp_close = (Get-Date).ToString('s')
  $Record.exit_px = $ExitPx
  $Record.holding_sec = $HoldingSec
  $Record.fees_commissions = $Fees
  $Record.slippage_cost = $Slippage

  $signedQty = if ($Record.side -eq 'LONG') { $Record.qty } else { -$Record.qty }
  $Record.pnl_gross = [Math]::Round(($ExitPx - $Record.entry_px) * $signedQty, 2)
  $Record.pnl_net   = [Math]::Round($Record.pnl_gross - $Fees - $Slippage, 2)
  if ([double]$Record.risk_usd -ne 0) {
    $Record.pnl_r = [Math]::Round($Record.pnl_net / [double]$Record.risk_usd, 4)
  }
  return $Record
}

function Write-TradeCsv {
  param(
    [Parameter(Mandatory=$true)][object[]]$Records,
    [string]$OutDir = (Join-Path $PSScriptRoot '..\out\trades'),
    [string]$TradingDate = (Get-Date).ToString('yyyy-MM-dd')
  )
  New-Item -ItemType Directory -Force $OutDir | Out-Null
  $csvPath = Join-Path $OutDir ("{0}_trades.csv" -f $TradingDate)

  if (-not (Test-Path $csvPath)) {
    $header = ($script:TradeCsvHeader -join ',') + "`n"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($csvPath, $header, $utf8)
  }

  $sb = New-Object System.Text.StringBuilder
  foreach($rec in $Records){
    $vals = foreach($col in $script:TradeCsvHeader){
      $v = [string]$rec.$col
      if ($v -match '[,"\r\n]') { '"' + ($v -replace '"','""') + '"' } else { $v }
    }
    [void]$sb.AppendLine(($vals -join ','))
  }
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::AppendAllText($csvPath, $sb.ToString().Replace("`r`n","`n"), $utf8)
  return $csvPath
}
