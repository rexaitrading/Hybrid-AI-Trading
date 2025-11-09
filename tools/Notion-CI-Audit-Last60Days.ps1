$ErrorActionPreference='Stop'
function Fail($m){ Write-Host $m -ForegroundColor Red; exit 1 }

$token = $env:NOTION_TOKEN
if (-not $token -or $token -notmatch '^(ntn_|secret_)'){ Fail "NOTION_TOKEN missing/invalid in env." }

$H = @{
  'Authorization'  = "Bearer $token"
  'Notion-Version' = '2025-09-03'
  'Content-Type'   = 'application/json'
}
function Req($m,$u,$b=$null){
  try{
    if($b){ return Invoke-RestMethod -Method $m -Uri $u -Headers $H -Body $b }
    else  { return Invoke-RestMethod -Method $m -Uri $u -Headers $H }
  }catch{
    $resp=$_.Exception.Response
    if($resp -and $resp.GetResponseStream()){
      $sr=New-Object IO.StreamReader($resp.GetResponseStream()); $body=$sr.ReadToEnd(); $sr.Close()
      Write-Host "HTTP $m $u`n$body" -ForegroundColor Red
    } else { Write-Host $_.Exception.Message -ForegroundColor Red }
    throw
  }
}

# Enumerate data_sources (NOT databases)
$searchBody = @{ query=""; filter=@{property="object"; value="data_source"}; sort=@{direction="descending"; timestamp="last_edited_time"} } | ConvertTo-Json -Depth 5
$ds = Req Post "https://api.notion.com/v1/search" $searchBody
if (-not $ds.results){ Fail "No data_source objects visible to this token." }

# === 3 months window (override via NOTION_AUDIT_DAYS) ===
$days  = 90
try { if ($env:NOTION_AUDIT_DAYS -as [int]) { $days = [int]$env:NOTION_AUDIT_DAYS } } catch {}
$since = (Get-Date).AddDays(-$days)
$sinceIso = $since.ToString("yyyy-MM-ddTHH:mm:ssZ")

$summary = New-Object System.Collections.ArrayList
$entries = New-Object System.Collections.ArrayList
$journal = New-Object System.Collections.ArrayList

foreach($src in $ds.results){
  $dsTitle = if ($src.title){ ($src.title | Select -First 1).plain_text } else { "" }
  $dsId    = $src.id
  if (-not $dsId){ continue }

  #  Correct multi-source filter/sort for 2025-09-03 API
  $filter = @{
    filter    = @{ timestamp = 'last_edited_time'; last_edited_time = @{ on_or_after = $sinceIso } }
    sorts     = @(@{ timestamp = 'last_edited_time'; direction = 'descending' })
    page_size = 100
  }

  $hasMore=$true; $cursor=$null; $count=0
  while($hasMore){
    if($cursor){ $filter.start_cursor=$cursor } else { $filter.Remove('start_cursor') }
    $payload = ($filter | ConvertTo-Json -Depth 7)
    $qr = Req Post ("https://api.notion.com/v1/data_sources/{0}/query" -f $dsId) $payload

    foreach($pg in $qr.results){
      $count++
      $sym=$null;$side=$null;$qty=$null;$entry=$null;$exit=$null
      if ($pg.properties.Symbol.title)         { $sym = $pg.properties.Symbol.title[0].plain_text }
      elseif ($pg.properties.Symbol.rich_text) { $sym = $pg.properties.Symbol.rich_text[0].plain_text }
      if ($pg.properties.Side.select)          { $side  = $pg.properties.Side.select.name }
      if ($pg.properties.Qty.number)           { $qty   = [double]$pg.properties.Qty.number }
      if ($pg.properties.Entry.number)         { $entry = [double]$pg.properties.Entry.number }
      if ($pg.properties.Exit.number)          { $exit  = [double]$pg.properties.Exit.number }

      $null = $entries.Add([pscustomobject]@{
        DataSourceTitle=$dsTitle; DataSourceId=$dsId; PageId=$pg.id; LastEdited=[datetime]$pg.last_edited_time; Created=[datetime]$pg.created_time; Url=$pg.url
        Symbol=$sym; Side=$side; Qty=$qty; Entry=$entry; Exit=$exit
      })

      if ($dsTitle -eq 'Trading Journal'){
        $kelly=$null;$conf=$null;$fees=$null;$reg=$null;$ts=$null
        if ($pg.properties.KellyF.number)      { $kelly=[double]$pg.properties.KellyF.number }
        if ($pg.properties.Confidence.number)  { $conf =[double]$pg.properties.Confidence.number }
        if ($pg.properties.Fees.number)        { $fees =[double]$pg.properties.Fees.number }
        if ($pg.properties.Regime.select)      { $reg  =$pg.properties.Regime.select.name }
        if ($pg.properties.Ts.date)            { $ts   =$pg.properties.Ts.date.start }
        $null = $journal.Add([pscustomobject]@{
          Ts=$ts; Symbol=$sym; Side=$side; Qty=$qty; Entry=$entry; Exit=$exit; Fees=$fees; KellyF=$kelly; Confidence=$conf; Regime=$reg
          PageId=$pg.id; LastEdited=[datetime]$pg.last_edited_time; Url=$pg.url
        })
      }
    }
    $hasMore=[bool]$qr.has_more; $cursor=$qr.next_cursor
  }

  $lastMax = ($entries | Where-Object {$_.DataSourceId -eq $dsId} | Sort-Object LastEdited -Desc | Select -First 1 -ExpandProperty LastEdited)
  $null = $summary.Add([pscustomobject]@{ DataSourceTitle=$dsTitle; DataSourceId=$dsId; EditedLast90d=$count; LastEditedMax=$lastMax })
}

$out = Join-Path (Get-Location) 'out'; New-Item -ItemType Directory -Force $out | Out-Null
$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
$sum = Join-Path $out "notion_audit_summary.$ts.csv"
$ent = Join-Path $out "notion_audit_entries.$ts.csv"
$summary | Export-Csv $sum -NoTypeInformation -Encoding UTF8
$entries | Export-Csv $ent -NoTypeInformation -Encoding UTF8
if ($journal.Count -gt 0){
  $jr = Join-Path $out "trading_journal_last90d.$ts.csv"
  $journal | Export-Csv $jr -NoTypeInformation -Encoding UTF8
  Write-Host "Trading Journal export: $jr" -ForegroundColor Green
}
Write-Host "Summary: $sum" -ForegroundColor Green
Write-Host "Entries: $ent" -ForegroundColor Green
