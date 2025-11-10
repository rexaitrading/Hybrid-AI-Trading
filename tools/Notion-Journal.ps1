# tools\Notion-Journal.ps1  (PS 5.1-safe; UTF-8 no BOM)

# --- Notion constants (do NOT put secrets here) ---
$script:Base = 'https://api.notion.com/v1'
$script:NotionVersion = '2025-09-03'
# Trading Journal CHILD data_source id (NOT the merged page)
$script:ChildId = '2970bf31-ef15-809e-802a-000b4911c1fc'

function Set-NotionToken {
  param([Parameter(Mandatory=$true)][string]$Token)
  $script:Headers = @{
    'Authorization'  = "Bearer $Token"
    'Notion-Version' = $script:NotionVersion
    'Content-Type'   = 'application/json'
  }
}

function Assert-ChildSourceId {
  param([string]$Id)
  try { Invoke-RestMethod -Method Get -Uri "$script:Base/data_sources/$Id" -Headers $script:Headers | Out-Null; return }
  catch { throw "Not a data_source id (or token lacks access). Use the CHILD source id (e.g., Trading Journal)" }
}

function Search {
  param([ValidateSet('data_source','page')][string]$Object)
  $body = @{
    query  = ""
    sort   = @{ direction="descending"; timestamp="last_edited_time" }
    filter = @{ property="object"; value=$Object }
  } | ConvertTo-Json -Depth 5
  return Invoke-RestMethod -Method Post -Uri "$script:Base/search" -Headers $script:Headers -Body $body
}

function Add-Trade {
  param(
    [datetime]$Ts,
    [string]$Symbol,
    [ValidateSet('Buy','Sell')][string]$Side='Buy',
    [double]$Qty=0,[double]$Entry=0,[double]$Exit=0,[double]$Fees=0,
    [double]$KellyF=0,[double]$Confidence=0.0,
    [string]$Regime='neutral'
  )
  if (-not $script:Headers) { throw "Call Set-NotionToken first." }

  # load schema once per session
  if (-not $script:Schema) {
    $script:Schema = Invoke-RestMethod -Method Get -Uri "$script:Base/data_sources/$script:ChildId" -Headers $script:Headers
  }
  $props = $script:Schema.properties
  $titleProp = 'Name'
  foreach($p in $props.PSObject.Properties.Name){ if($props.$p.type -eq 'title'){ $titleProp=$p; break } }

  $pnl = [math]::Round(($Exit - $Entry)*$Qty,2); if($Side -eq 'Sell'){ $pnl = [math]::Round(($Entry - $Exit)*$Qty,2) }

  $pr = @{}
  $pr[$titleProp] = @{ title=@(@{ text=@{ content=("{0} {1}" -f $Side,$Symbol) }}) }
  if($props.PSObject.Properties.Name -contains 'symbol'   -and $props.symbol.type   -eq 'rich_text'){ $pr.symbol   = @{ rich_text=@(@{ text=@{ content=$Symbol }}) } }
  if($props.PSObject.Properties.Name -contains 'side'     -and $props.side.type     -eq 'select'  ){ $pr.side     = @{ select=@{ name=$Side } } }
  if($props.PSObject.Properties.Name -contains 'regime'   -and $props.regime.type   -eq 'select'  ){ $pr.regime   = @{ select=@{ name=$Regime } } }
  if($props.PSObject.Properties.Name -contains 'ts_trade' -and $props.ts_trade.type -eq 'date'    ){ $pr.ts_trade = @{ date=@{ start=($Ts.ToUniversalTime().ToString('s') + 'Z') } } }
  foreach($t in @(
    @{n='qty';v=$Qty}, @{n='entry';v=$Entry}, @{n='exit';v=$Exit},
    @{n='gross_pnl';v=$pnl}, @{n='fees';v=$Fees}, @{n='net_pnl';v=[math]::Round($pnl-$Fees,2)},
    @{n='kelly_f';v=$KellyF}, @{n='confidence';v=$Confidence}
  )){
    if($props.PSObject.Properties.Name -contains $t.n -and $props.($t.n).type -eq 'number'){ $pr[$t.n]=@{ number=[double]$t.v } }
  }

  $body = @{ parent=@{ data_source_id=$script:ChildId }; properties=$pr } | ConvertTo-Json -Depth 12
  $r = Invoke-RestMethod -Method Post -Uri "$script:Base/pages" -Headers $script:Headers -Body $body
  "JOURNALED pageId=$($r.id) $($Ts.ToString('s')) $Side $Symbol qty=$Qty net=$([math]::Round($pnl-$Fees,2))"
}
