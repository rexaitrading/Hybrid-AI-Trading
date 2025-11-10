$ErrorActionPreference='Stop'
function Fail($m){ Write-Host $m -ForegroundColor Red; exit 1 }

$token = $env:NOTION_TOKEN
if (-not $token -or $token -notmatch '^(ntn_|secret_)'){ Fail "NOTION_TOKEN missing/invalid in env." }

$dbId = $env:NOTION_DB_ID
if (-not $dbId -or $dbId -notmatch '^[0-9a-f-]{36}$'){
  $cache = 'C:\Dev\HybridAITrading\secrets\trading_journal_dbid.txt'
  if (Test-Path $cache){ $dbId = (Get-Content $cache -Raw).Trim() }
}
if (-not $dbId -or $dbId -notmatch '^[0-9a-f-]{36}$'){ Fail "NOTION_DB_ID missing in env and cache." }

$H = @{
  'Authorization'  = "Bearer $token"
  'Notion-Version' = '2025-09-03'
  'Content-Type'   = 'application/json'
}

$meta = Invoke-RestMethod -Method Get -Uri ("https://api.notion.com/v1/databases/{0}" -f $dbId) -Headers $H
$title = ($meta.title | Select -First 1).plain_text

$dsId = $null
if ($meta.data_sources -and $meta.data_sources.Count -gt 0) { $dsId = $meta.data_sources[0].id }
elseif ($meta.additional_data -and $meta.additional_data.child_data_source_ids) { $dsId = $meta.additional_data.child_data_source_ids[0] }

$body = @{ page_size = 1 } | ConvertTo-Json
if ($dsId) { $qr = Invoke-RestMethod -Method Post -Uri ("https://api.notion.com/v1/data_sources/{0}/query" -f $dsId) -Headers $H -Body $body }
else       { $qr = Invoke-RestMethod -Method Post -Uri ("https://api.notion.com/v1/databases/{0}/query"   -f $dbId) -Headers $H -Body $body }

$ds = if ($dsId) { $dsId } else { '' }
Write-Host ("Notion OK: {0}  ds={1} rows={2}" -f $title, $ds, $qr.results.Count) -ForegroundColor Green
