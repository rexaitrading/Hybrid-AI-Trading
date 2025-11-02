param(
  [Parameter(Mandatory=$true)][string]$RowUrl
)
$ErrorActionPreference = 'Stop'

if (-not $env:NOTION_TOKEN) { throw "Set `$env:NOTION_TOKEN first" }

# Extract 32-hex page id and dash it
if ($RowUrl -match '([0-9a-f]{32})(?=$|[?#/])') {
  $pageRaw = $Matches[1]
} elseif ($RowUrl -match '([0-9a-f]{8})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{12})') {
  $pageRaw = ($Matches[1..5] -join '')
} else {
  throw "Not a ROW (page) link"
}
$pageId = "{0}-{1}-{2}-{3}-{4}" -f $pageRaw.Substring(0,8),$pageRaw.Substring(8,4),$pageRaw.Substring(12,4),$pageRaw.Substring(16,4),$pageRaw.Substring(20)

# Use newer API to expose multi-source parent fields
$hdr = @{
  'Authorization'  = "Bearer $env:NOTION_TOKEN"
  'Notion-Version' = '2025-09-03'
  'Content-Type'   = 'application/json'
}

$page = Invoke-RestMethod -Uri "https://api.notion.com/v1/pages/$pageId" -Headers $hdr -Method GET
$parentType = $page.parent.type

$dsDashed = $null
if ($page.parent.PSObject.Properties['data_source_id']) { $dsDashed = $page.parent.data_source_id }

$dbDashed = $null
if ($page.parent.PSObject.Properties['database_id'])    { $dbDashed = $page.parent.database_id }

if ($parentType -eq 'data_source_id' -and -not $dbDashed) {
  $ds = Invoke-RestMethod -Uri "https://api.notion.com/v1/data_sources/$dsDashed" -Headers $hdr -Method GET
  $dbDashed = $ds.parent.database_id
}

# Read DB title (sanity)
$db = Invoke-RestMethod -Uri "https://api.notion.com/v1/databases/$dbDashed" -Headers $hdr -Method GET

# Persist -> config/notion_ids.json AND export to session
$ids = [pscustomobject]@{
  page_id         = $pageId
  data_source_id  = $dsDashed
  database_id     = $dbDashed
  db_title        = $db.title[0].plain_text
  resolved_at     = (Get-Date).ToString('s')
}

$idsPath = Join-Path (Resolve-Path 'config').Path 'notion_ids.json'
$ids | ConvertTo-Json -Depth 5 | Out-File -FilePath $idsPath -Encoding utf8

if ($dbDashed) { $env:NOTION_DB_TRADES = ($dbDashed -replace '-','') }
if ($dsDashed) { $env:NOTION_DS_TRADES = ($dsDashed -replace '-','') }

"Resolved:"
"  Parent type : $parentType"
"  Data source : $dsDashed"
"  Database    : $dbDashed | Title: $($db.title[0].plain_text)"
"Saved -> $idsPath"
