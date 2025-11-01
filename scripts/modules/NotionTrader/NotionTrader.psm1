function New-NotionPageMultiSource {

  param(
    [Parameter(Mandatory=$true)][string]$DbId,
    [Parameter(Mandatory=$true)][string]$DataSourceName, # e.g. 'Trading Journal' / 'Edge Feed'
    [Parameter(Mandatory=$true)][string]$Title,
    [hashtable]$ExtraProperties = @{}  # any additional Notion props (match schema)
  )
  $hdr = @{
    Authorization    = "Bearer $env:NOTION_TOKEN"
    'Notion-Version' = '2025-09-03'
    'Content-Type'   = 'application/json'
  }

  $db = Invoke-RestMethod -Uri "https://api.notion.com/v1/databases/$DbId" -Headers $hdr -Method GET

  $ds = $db.data_sources | Where-Object { $_.name -eq $DataSourceName } | Select-Object -First 1
  if (-not $ds) { throw "Data source '$DataSourceName' not found. Available: $($db.data_sources.name -join ', ')" }
  $ds_id = $ds.id

  # get title key from the data source (not from $db)
  $dsObj = Invoke-RestMethod -Uri "https://api.notion.com/v1/data_sources/$ds_id" -Headers $hdr -Method GET
  $titleKey = $dsObj.properties.PSObject.Properties |
              Where-Object { $_.Value.type -eq 'title' } |
              Select-Object -ExpandProperty Name -First 1
  if (-not $titleKey) { throw "No title property found on data source '$DataSourceName'." }

  # build properties
  $props = @{
    $titleKey = @{ title = @(@{ text = @{ content = $Title }}) }
  }
  foreach ($k in $ExtraProperties.Keys) { $props[$k] = $ExtraProperties[$k] }

  $body = @{
    parent = @{
      type           = 'data_source_id'
      data_source_id = $ds_id
    }
    properties = $props
  } | ConvertTo-Json -Depth 20

  try {
    $res = Invoke-RestMethod -Uri 'https://api.notion.com/v1/pages' -Headers $hdr -Method POST -Body $body
    return $res
  } catch {
    if ($_.Exception.Response) {
      $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
      $msg = $reader.ReadToEnd()
      throw "POST failed: $msg"
    } else { throw }
  }

}

function Write-TradeJournalEntry {

  [CmdletBinding()]
  param(
    # Defaults so no prompts:
    [string]$DbId = '2970bf31ef1580a6983ecf2c836cf97c',
    [ValidateSet('Trading Journal','Edge Feed','New data source')]
    [string]$DataSourceName = 'Trading Journal',

    # Required trade fields
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][string]$Symbol,
    [Parameter(Mandatory)][ValidateSet('LONG','SHORT','BUY','SELL')][string]$Side,
    [Parameter(Mandatory)][double]$Qty,

    # Optional details
    [double]$EntryPx,
    [double]$ExitPx,
    [double]$Price,
    [double]$RiskUsd,
    [double]$Fees,
    [double]$Slippage,
    [double]$KellyF,
    [ValidateSet('Bull','Bear','Neutral','Volatile','Calm','RiskOff','RiskOn')][string]$Regime,
    [ValidateSet('Bullish','Bearish','Neutral')][string]$Sentiment,
    [ValidateSet('Open','Closed','Planned','Cancelled')][string]$Status,
    [string]$Reason,
    [string]$Notes,
    [datetime]$Ts = (Get-Date)
  )

  # tiny helper for selects
  function Add-NotionSelect([hashtable]$Props,[string]$Key,[string]$Name){
    if ($Name) { $Props[$Key] = @{ select = @{ name = $Name } } }
  }

  # Build properties (match your schema)
  $props = @{
    ts     = @{ date = @{ start = $Ts.ToString('s') } }
    symbol = @{ rich_text = @(@{ text = @{ content = $Symbol }}) }
    qty    = @{ number   = [double]$Qty }
  }
  Add-NotionSelect -Props $props -Key 'side'      -Name $Side
  Add-NotionSelect -Props $props -Key 'regime'    -Name $Regime
  Add-NotionSelect -Props $props -Key 'sentiment' -Name $Sentiment
  Add-NotionSelect -Props $props -Key 'status'    -Name $Status

  if ($EntryPx)  { $props.entry_px = @{ number = [double]$EntryPx } }
  if ($ExitPx)   { $props.exit_px  = @{ number = [double]$ExitPx } }
  if ($Price)    { $props.price    = @{ number = [double]$Price } }
  if ($RiskUsd)  { $props.risk_usd = @{ number = [double]$RiskUsd } }
  if ($Fees)     { $props.fees     = @{ number = [double]$Fees } }
  if ($Slippage) { $props.slippage = @{ number = [double]$Slippage } }
  if ($KellyF)   { $props.kelly_f  = @{ number = [double]$KellyF } }
  if ($Reason)   { $props.reason   = @{ rich_text = @(@{ text = @{ content = $Reason }}) } }
  if ($Notes)    { $props.notes    = @{ rich_text = @(@{ text = @{ content = $Notes }}) } }

  $r = New-NotionPageMultiSource -DbId $DbId -DataSourceName $DataSourceName -Title $Title -ExtraProperties $props
  return $r

}

Export-ModuleMember -Function New-NotionPageMultiSource, Write-TradeJournalEntry
