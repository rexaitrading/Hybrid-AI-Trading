param(
  [Parameter(Mandatory=$true)][string]$Ndjson = ".\data\feeds\youtube_latest.ndjson",
  [Parameter(Mandatory=$true)][string]$NotionDb = $env:NOTION_DB_NEWS
)
$ErrorActionPreference='Stop'
$headers = @{
  'Authorization' = "Bearer $env:NOTION_TOKEN"
  'Notion-Version' = '2022-06-28'
  'Content-Type'   = 'application/json'
}
if(-not $NotionDb){ throw "Set -NotionDb <db-id> or `$env:NOTION_DB_NEWS" }

# Ensure feed DB has schema
$body = @{
  properties = @{
    "Title"        = @{ title = @{} }
    "Channel"      = @{ rich_text = @{} }
    "PublishedAt"  = @{ date = @{} }
    "URL"          = @{ url = @{} }
    "Source"       = @{ select = @{ options = @(@{name="channel"},@{name="search"}) } }
  }
} | ConvertTo-Json -Depth 6
try { Invoke-RestMethod -Uri ("https://api.notion.com/v1/databases/{0}" -f $NotionDb) -Method Patch -Headers $headers -Body $body | Out-Null } catch {}

# Upsert by URL
Get-Content $Ndjson | ForEach-Object {
  if(-not $_){ return }
  $o = $_ | ConvertFrom-Json
  $payload = @{
    parent = @{ database_id = $NotionDb }
    properties = @{
      "Title"       = @{ title = @(@{ text = @{ content = $o.title }}) }
      "Channel"     = @{ rich_text = @(@{ text = @{ content = $o.channelTitle }}) }
      "PublishedAt" = @{ date = @{ start = $o.publishedAt } }
      "URL"         = @{ url  = $o.url }
      "Source"      = @{ select = @{ name = $o.source } }
    }
  } | ConvertTo-Json -Depth 6
  try {
    Invoke-RestMethod -Uri 'https://api.notion.com/v1/pages' -Method Post -Headers $headers -Body $payload | Out-Null
    " Posted: $($o.title)"
  } catch {
    Write-Warning $_
  }
}
" Feed upsert complete."
