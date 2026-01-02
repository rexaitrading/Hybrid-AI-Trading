[CmdletBinding()]
param(
  [string]$CsvPath = ".\logs\phase6_daily_summary.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Invoke-Notion([string]$Method, [string]$Url, [hashtable]$Headers, [string]$Body){
  try{
    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -Body $Body
  } catch {
    Write-Host "[NOTION] HTTP FAILED: $Method $Url" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if($_.ErrorDetails -and $_.ErrorDetails.Message){
      Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
    }
    throw
  }
}

$tok = $env:NOTION_TOKEN
$ds  = $env:HAT_NOTION_PHASE6_DB_ID
if([string]::IsNullOrWhiteSpace($tok)){ throw "Missing env NOTION_TOKEN" }
if([string]::IsNullOrWhiteSpace($ds)){ throw "Missing env HAT_NOTION_PHASE6_DB_ID" }

if(-not (Test-Path -LiteralPath $CsvPath)){ throw "Missing CSV: $CsvPath" }
$rows = Import-Csv -LiteralPath $CsvPath
if(-not $rows){ throw "CSV has no rows: $CsvPath" }

$r = $rows[-1]
$asof    = [string]$r.as_of_date
$okStr   = [string]$r.ok
$reason  = [string]$r.reason
$ready   = [string]$r.ready_symbols
$tsUtc   = [string]$r.ts_utc
$version = [string]$r.version

if([string]::IsNullOrWhiteSpace($asof)){ throw "Missing as_of_date in CSV row" }

$ok = $false
if($okStr.Trim().ToLowerInvariant() -in @("true","1","yes","y")){ $ok = $true }

$headers = @{
  "Authorization"  = "Bearer $tok"
  "Notion-Version" = "2025-09-03"
  "Content-Type"   = "application/json"
}

# Title
$titleText = ("Phase6 {0} ok={1} ready={2}" -f $asof, $ok, $ready)

# Properties must exist in the data source
$props = @{
  "Name" = @{ "title" = @(@{ "type"="text"; "text"=@{ "content" = $titleText } }) }
  "as_of_date"    = @{ "date" = @{ "start" = $asof } }
  "ok"            = @{ "checkbox" = $ok }
  "reason"        = @{ "rich_text" = @(@{ "type"="text"; "text"=@{ "content" = $reason } }) }
  "ready_symbols" = @{ "rich_text" = @(@{ "type"="text"; "text"=@{ "content" = $ready } }) }
  "ts_utc"        = @{ "date" = @{ "start" = $tsUtc } }
  "version"       = @{ "rich_text" = @(@{ "type"="text"; "text"=@{ "content" = $version } }) }
}

# Query existing by as_of_date on the DATA SOURCE endpoint
$qBody = @{
  "filter" = @{
    "property" = "as_of_date"
    "date" = @{ "equals" = $asof }
  }
} | ConvertTo-Json -Depth 10

$qUrl = "https://api.notion.com/v1/data_sources/$ds/query"
$q = Invoke-Notion -Method Post -Url $qUrl -Headers $headers -Body $qBody

$pageId = $null
if($q -and ($q.PSObject.Properties.Name -contains "results")){
  $res = $q.results
  if($res -is [System.Array] -and $res.Length -gt 0){
    $pageId = [string]$res[0].id
  }
}

if(-not [string]::IsNullOrWhiteSpace($pageId)){
  $uUrl = "https://api.notion.com/v1/pages/$pageId"
  $uBody = @{ "properties" = $props } | ConvertTo-Json -Depth 12
  Invoke-Notion -Method Patch -Url $uUrl -Headers $headers -Body $uBody | Out-Null
  Write-Host "[NOTION] Updated Phase6 row for as_of_date=$asof page=$pageId" -ForegroundColor Green
} else {
  $cUrl = "https://api.notion.com/v1/pages"
  $cBody = @{
    "parent" = @{ "data_source_id" = $ds }
    "properties" = $props
  } | ConvertTo-Json -Depth 12

  $resp = Invoke-Notion -Method Post -Url $cUrl -Headers $headers -Body $cBody
  $newId = [string]$resp.id
  Write-Host "[NOTION] Created Phase6 row for as_of_date=$asof page=$newId" -ForegroundColor Green
}

Write-Host ("[NOTION] phase6_daily_summary: as_of={0} ok={1} ready={2} reason={3}" -f $asof,$ok,$ready,$reason) -ForegroundColor Cyan
exit 0

