[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string] $Csv,
  [string] $Symbol       = "AAPL",
  [string] $NotionDb     = $env:NOTION_DB_TRADES,
  [double] $FeesPerShare = 0.003,
  [double] $SlippagePs   = 0.002,
  [int]    $OrbMinutes   = 5,
  [double] $RiskCents    = 20.0,
  [int]    $MaxQty       = 200,
  [ValidateSet("fast","step","auto")] [string] $Mode = "fast",
  [switch] $ForceExit,
  [string] $Notes        = "Phase3 replayjournal pipeline",
  [double] $KellyF       = 0.02,
  [switch] $RunPaper
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Convert-ToDashedGuid([string]$raw) {
  if (-not $raw) { return "" }
  $r = $raw -replace "-", ""
  if ($r.Length -eq 32) { return ('{0}-{1}-{2}-{3}-{4}' -f $r.Substring(0,8),$r.Substring(8,4),$r.Substring(12,4),$r.Substring(16,4),$r.Substring(20,12)) }
  return $raw
}

function Get-NotionHeaders {
  param([string]$Token)
  if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Environment variable NOTION_TOKEN is not set. Example:  `\$env:NOTION_TOKEN = 'secret_xxx...'"
  }
  return @{
    "Authorization" = "Bearer $Token"
    "Content-Type"  = "application/json"
    "Notion-Version"= "2022-06-28"
  }
}

function Ensure-NotionJournalSchema {
  param([Parameter(Mandatory=$true)][string]$DatabaseId, [Parameter(Mandatory=$true)][hashtable]$Headers)
  $body = @{
    properties = @{
      "Name"          = @{ title = @{} }
      "symbol"        = @{ rich_text = @{} }
      "ts"            = @{ date = @{} }
      "mode"          = @{ select = @{ options = @(@{name="fast"},@{name="step"},@{name="auto"}) } }
      "setup"         = @{ select = @{ options = @(@{name="ORB"}) } }
      "entry"         = @{ number = @{} }
      "exit"          = @{ number = @{} }
      "qty"           = @{ number = @{} }
      "gross_pnl"     = @{ number = @{} }
      "net_pnl"       = @{ number = @{} }
      "fees"          = @{ number = @{} }
      "slippage"      = @{ number = @{} }
      "risk_usd"      = @{ number = @{} }
      "r_multiple"    = @{ number = @{} }
      "notes"         = @{ rich_text = @{} }
      "context_notes" = @{ rich_text = @{} }
      "context_tags"  = @{ multi_select = @{} }
      "replay_id"     = @{ rich_text = @{} }
    }
  } | ConvertTo-Json -Depth 6
  Invoke-RestMethod -Uri ("https://api.notion.com/v1/databases/{0}" -f $DatabaseId) -Method Patch -Headers $Headers -Body $body | Out-Null
}

function Get-OrbFeatures {
  param([Parameter(Mandatory=$true)] [System.Object[]] $Rows, [int]$OrbBars)
  $head    = $Rows | Select-Object -First $OrbBars
  $orbHigh = ($head | Measure-Object -Property high -Maximum).Maximum
  $orbLow  = ($head | Measure-Object -Property low  -Minimum).Minimum
  $tail    = @($Rows | Select-Object -Skip $OrbBars)
  $n       = [math]::Min(6, $tail.Count)
  $slope   = 0.0
  if ($n -gt 1) {
    $xs = 0..($n-1)
    $ys = for($i=0;$i -lt $n;$i++){ [double]$tail[$i].close }
    $xbar = ($xs | Measure-Object -Average).Average
    $ybar = ($ys | Measure-Object -Average).Average
    $num=0.0; $den=0.0
    for($i=0;$i -lt $n;$i++){ $num += ($xs[$i]-$xbar)*($ys[$i]-$ybar); $den += ($xs[$i]-$xbar)*($xs[$i]-$xbar) }
    if ($den -ne 0) { $slope = [math]::Round($num/$den,6) }
  }
  $breakIdx = $null
  for($i=$OrbBars; $i -lt $Rows.Count; $i++){
    if ([double]$Rows[$i].close -gt $orbHigh * 1.0001) { $breakIdx = $i; break }
  }
  $tags = New-Object System.Collections.Generic.List[string]
  if($breakIdx -ne $null){ $null = $tags.Add("ORB_BREAKOUT") } else { $null = $tags.Add("NO_BREAK") }
  if ($breakIdx -ne $null) {
    $ret = $false
    for($k=$breakIdx+1; $k -lt [Math]::Min($breakIdx+4, $Rows.Count); $k++){
      if ([double]$Rows[$k].low -le $orbHigh * 1.0005) { $ret = $true; break }
    }
    if ($ret) { $null = $tags.Add("RETEST") }
  }
  if ($slope -gt 0) { $null = $tags.Add("TREND_UP") } else { $null = $tags.Add("RANGE/MEAN-REVERT") }
  [pscustomobject]@{ orb_high=[double]$orbHigh; orb_low=[double]$orbLow; slope=$slope; break_index=$breakIdx; tags=$tags }
}

function Get-TopFeedBullets {
  param(
    [string]$Ndjson = '.\data\feeds\youtube_latest.ndjson',
    [int]$TopN = 5
  )
  try {
    if (-not (Test-Path -LiteralPath $Ndjson)) { return '' }
    $raw = Get-Content -LiteralPath $Ndjson -ErrorAction SilentlyContinue | Where-Object { $_ -and $_.Trim() -ne '' }
    if (-not $raw) { return '' }
    $items = @()
    foreach($line in $raw){
      try { $o = $line | ConvertFrom-Json } catch { continue }
      if (-not $o) { continue }
      $dt = $null
      if ($o.publishedAt) { try { $dt = [datetime]$o.publishedAt } catch {} }
      $title = [string]$o.title
      $url   = [string]$o.url
      if (-not $url) { continue }
      $items += [pscustomobject]@{ dt=$dt; title=$title; url=$url }
    }
    if (-not $items) { return '' }
    $sel = $items | Sort-Object dt -Descending | Select-Object -First $TopN
    $lines = @()
    foreach($it in $sel){
      $d = if($it.dt){ $it.dt.ToString('yyyy-MM-dd') } else { 'n/a' }
      $t = $it.title
      if ($t -and $t.Length -gt 140) { $t = $t.Substring(0,137) + '...' }
      $lines += (" {0} ({1})`r`n  {2}" -f $t, $d, $it.url)
    }
    return ($lines -join "`r`n")
  } catch { return '' }
}

# --- Main flow ---
if (-not (Test-Path -LiteralPath $Csv)) { throw "CSV not found: $Csv" }

$notionDbId = if ($PSBoundParameters.ContainsKey("NotionDb") -and $NotionDb) {
  Convert-ToDashedGuid $NotionDb
} elseif ($env:NOTION_DB_TRADES) {
  Convert-ToDashedGuid $env:NOTION_DB_TRADES
} else {
  throw "No Notion DB id. Pass -NotionDb <db-id> or set `$env:NOTION_DB_TRADES."
}

$headers = Get-NotionHeaders -Token $env:NOTION_TOKEN
Ensure-NotionJournalSchema -DatabaseId $notionDbId -Headers $headers

# Replay  JSON
$replayArgs = @(
  "scripts/replay_cli.py",
  "--csv", $Csv,
  "--symbol", $Symbol,
  "--mode", $Mode, "--speed", "10",
  "--fees-per-share", ("{0}" -f $FeesPerShare),
  "--slippage-ps",    ("{0}" -f $SlippagePs),
  "--orb-minutes",    ("{0}" -f $OrbMinutes),
  "--risk-cents",     ("{0}" -f $RiskCents),
  "--max-qty",        ("{0}" -f $MaxQty),
  "--summary","json"
)
if ($ForceExit.IsPresent) { $replayArgs += "--force-exit" }

$line = & python @replayArgs
if ([string]::IsNullOrWhiteSpace($line)) { throw "scripts\replay_cli.py produced no output" }
$r = $line | ConvertFrom-Json

# Build features
$rows = Import-Csv -LiteralPath $Csv | ForEach-Object {
  [pscustomobject]@{ time=$_.time; open=[double]$_."open"; high=[double]$_."high"; low=[double]$_."low"; close=[double]$_."close"; volume=[int]$_."volume" }
}
$f = Get-OrbFeatures -Rows $rows -OrbBars $OrbMinutes

$entryPx = if ($r.entry_px) { [double]$r.entry_px } else { $null }
$exitPx  = if ($r.exit_px)  { [double]$r.exit_px  } else { [double]$rows[-1].close }
$qty     = if ($r.trades -gt 0 -and $entryPx) {
             $riskUsd = [double]$RiskCents/100.0
             $stopDist = [math]::Max(1e-6, $entryPx - $f.orb_low)
             [int][math]::Max(1, [math]::Floor($riskUsd / $stopDist))
           } else { 0 }
$gross   = if($r.trades -gt 0 -and $entryPx){ [math]::Round(($exitPx - $entryPx) * $qty, 2) } else { 0.0 }
$feesTot = [math]::Round($FeesPerShare * 2 * $qty, 5)
$slipTot = [math]::Round($SlippagePs * 2 * $qty, 5)
$net     = [double]$r.pnl
$riskUSD = [math]::Round(($RiskCents/100.0) * $qty, 2)
$rMult   = if($riskUSD -gt 0){ [math]::Round($gross / $riskUSD, 3) } else { 0.0 }
$nowIso  = (Get-Date).ToString("s")

# Build merged context notes with Top-5 feed
$feedBullets = Get-TopFeedBullets -Ndjson '.\data\feeds\youtube_latest.ndjson' -TopN 5
$tagText = ''
if ($f -and $f.PSObject.Properties['tags'] -and $f.tags) { $tagText = ($f.tags -join ', ') }
$mergedNotes = $Notes
if ($tagText) { $mergedNotes = ($mergedNotes + "`r`rTags: " + $tagText) }
if ($feedBullets -and $feedBullets.Trim()) { $mergedNotes = ($mergedNotes + "`r`rYouTube Top 5:`r`n" + $feedBullets) }
if ($mergedNotes.Length -gt 1800) { $mergedNotes = $mergedNotes.Substring(0,1797) + '...' }

# Notion payload
$props = @{
  "Name"          = @{ "title"     = @(@{ "text"  = @{ "content" = "$($r.symbol) ORB $($r.bars) bars  $nowIso" }}) }
  "symbol"        = @{ "rich_text" = @(@{ "text"  = @{ "content" = "$($r.symbol)" }}) }
  "ts"            = @{ "date"      = @{ "start"  = $nowIso } }
  "mode"          = @{ "select"    = @{ "name"   = $Mode } }
  "setup"         = @{ "select"    = @{ "name"   = "ORB" } }
  "entry"         = @{ "number"    = $entryPx }
  "exit"          = @{ "number"    = $exitPx }
  "qty"           = @{ "number"    = $qty }
  "gross_pnl"     = @{ "number"    = $gross }
  "net_pnl"       = @{ "number"    = $net }
  "fees"          = @{ "number"    = $feesTot }
  "slippage"      = @{ "number"    = $slipTot }
  "risk_usd"      = @{ "number"    = $riskUSD }
  "r_multiple"    = @{ "number"    = $rMult }
  "notes"         = @{ "rich_text" = @(@{ "text"  = @{ "content" = $Notes }}) }
  "context_notes" = @{ "rich_text" = @(@{ "text"  = @{ "content" = $mergedNotes }}) }
  "context_tags"  = @{ "multi_select" = @($f.tags | ForEach-Object { @{ name = $_ } }) }
  "replay_id"     = @{ "rich_text" = @(@{ "text"  = @{ "content" = "$($r.symbol)-$($nowIso)" }}) }
}
$payload = @{
  "parent"     = @{ "database_id" = $notionDbId }
  "properties" = $props
} | ConvertTo-Json -Depth 12

$resp = Invoke-RestMethod -Uri "https://api.notion.com/v1/pages" -Method Post -Headers $headers -Body $payload
" Notion journal page: $($resp.url)"

# (Optional) start paper trading after journaling
if ($RunPaper.IsPresent) {
  Write-Host "Starting IBKR paper run via scripts\paper_once.ps1 (if present)"
  if (Test-Path '.\scripts\paper_once.py') {
    try { & python '.\scripts\paper_once.py' } catch { Write-Warning "paper_once.py returned: $($_.Exception.Message)" }
  } else {
    Write-Warning "scripts\paper_once.py not found; skipping paper run."
  }
}

# Append NDJSON for ML loop
New-Item -ItemType Directory -Force -Path ".\data" | Out-Null
$nd = @{
  timestamp     = $nowIso
  symbol        = $r.symbol
  mode          = $Mode
  bars          = $r.bars
  trades        = $r.trades
  entry_px      = $entryPx
  exit_px       = $exitPx
  qty           = $qty
  gross_pnl     = $gross
  net_pnl       = $net
  fees_total    = $feesTot
  slippage_ps   = $SlippagePs
  risk_cents    = $RiskCents
  risk_usd      = $riskUSD
  r_multiple    = $rMult
  orb_high      = $f.orb_high
  orb_low       = $f.orb_low
  trend_slope   = $f.slope
  tags          = $f.tags
  csv_path      = (Resolve-Path $Csv).Path
} | ConvertTo-Json -Compress
$nd | Out-File -FilePath ".\data\replay_log.ndjson" -Append -Encoding utf8
" Appended to data\replay_log.ndjson"
