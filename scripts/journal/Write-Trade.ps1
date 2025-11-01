# scripts/journal/Write-Trade.ps1  (UTF-8 no BOM, LF)
function Write-TradeJournalEntry {
  [CmdletBinding()]
  param(
    # Mutually-exclusive selectors
    [Parameter(Mandatory=$true, ParameterSetName='ByDb')]
    [string]$DbId,

    [Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [string]$DataSourceId,

    # Common required fields
    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [string]$Title,

    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [string]$Symbol,

    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [ValidateSet('BUY','SELL')][string]$Side,

    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [ValidateSet('Open','Closed')][string]$Status,

    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [double]$EntryPx,

    [Parameter(ParameterSetName='ByDb')][Parameter(ParameterSetName='ByDataSource')]
    [double]$ExitPx,

    [Parameter(Mandatory=$true, ParameterSetName='ByDb')][Parameter(Mandatory=$true, ParameterSetName='ByDataSource')]
    [double]$Qty,

    # Optional extras
    [Parameter(ParameterSetName='ByDb')][Parameter(ParameterSetName='ByDataSource')]
    [string]$Regime,

    [Parameter(ParameterSetName='ByDb')][Parameter(ParameterSetName='ByDataSource')]
    [string]$Sentiment,

    [Parameter(ParameterSetName='ByDb')][Parameter(ParameterSetName='ByDataSource')]
    [string]$SessionId
  )

  $headers = @{
    'Authorization'  = "Bearer $env:NOTION_TOKEN"
    'Notion-Version' = '2025-09-03'
  }

  # If DataSourceId not provided, resolve from DbId
  if (-not $DataSourceId -or [string]::IsNullOrWhiteSpace($DataSourceId)) {
    if (-not $DbId) { throw "Provide -DataSourceId or -DbId." }
    $dbo = Invoke-RestMethod -Uri "https://api.notion.com/v1/databases/$DbId" -Headers $headers -Method Get
    if ($dbo -and $dbo.PSObject.Properties.Name -contains 'data_sources' -and $dbo.data_sources.Count -ge 1) {
      $pick = $dbo.data_sources | Where-Object { $_.name -eq 'Trading Journal' } | Select-Object -First 1
      if (-not $pick) { $pick = $dbo.data_sources[0] }
      $DataSourceId = $pick.id
    } else {
      throw "No data_sources found for database $DbId; provide -DataSourceId explicitly."
    }
  }

  # Build properties
  $props = @{
    Name      = @{ title     = @(@{ text = @{ content = $Title }}) }
    symbol    = @{ rich_text = @(@{ text = @{ content = $Symbol }}) }
    side      = @{ select    = @{ name = $Side } }
    status    = @{ select    = @{ name = $Status } }
  }
  if ($PSBoundParameters.ContainsKey('Regime')    -and $Regime)    { $props.regime    = @{ select = @{ name = $Regime } } }
  if ($PSBoundParameters.ContainsKey('Sentiment') -and $Sentiment) { $props.sentiment = @{ select = @{ name = $Sentiment } } }
  if ($PSBoundParameters.ContainsKey('EntryPx')) { $props.entry_px = @{ number = $EntryPx } }
  if ($PSBoundParameters.ContainsKey('ExitPx'))  { $props.exit_px  = @{ number = $ExitPx } }
  if ($PSBoundParameters.ContainsKey('Qty'))     { $props.qty      = @{ number = $Qty } }

  # Parent by active parameter set
  $parent = if ($PSCmdlet.ParameterSetName -eq 'ByDataSource') {
    @{ type = 'data_source_id'; data_source_id = $DataSourceId }
  } else {
    @{ database_id = $DbId }
  }

  $payload = @{
    parent     = $parent
    properties = $props
  }
  $json = $payload | ConvertTo-Json -Depth 100

  $resp = Invoke-RestMethod -Method Post -Uri 'https://api.notion.com/v1/pages' `
            -Headers $headers -ContentType 'application/json' -Body $json
  $result = [pscustomobject]@{ id = $resp.id; url = $resp.url }

  # Optional PATCH: session_id
  if ($PSBoundParameters.ContainsKey('SessionId') -and -not [string]::IsNullOrWhiteSpace($SessionId)) {
    $patchHeaders = $headers.Clone(); $patchHeaders['Content-Type'] = 'application/json'
    $patchBody = @{
      properties = @{
        session_id = @{ rich_text = @(@{ text = @{ content = $SessionId }}) }
      }
    } | ConvertTo-Json -Depth 10
    Invoke-RestMethod -Uri "https://api.notion.com/v1/pages/$($result.id)" -Headers $patchHeaders -Method Patch -Body $patchBody | Out-Null
  }

  return $result
}
