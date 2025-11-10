$ErrorActionPreference='Stop'

param(
  [string]$OutDir = "C:\Dev\HybridAITrading\out",
  [string]$Channel = $env:SLACK_CHANNEL_ID,
  [string]$Token   = $env:SLACK_BOT_TOKEN
)

function Fail($m){ Write-Host $m -ForegroundColor Red; exit 1 }
if (-not (Test-Path $OutDir)) { Fail "OutDir not found: $OutDir" }
$latest = Get-ChildItem -Path $OutDir -Filter 'trading_journal_last90d.*.csv' | Sort-Object LastWriteTime -Desc | Select-Object -First 1
$prev   = Get-ChildItem -Path $OutDir -Filter 'trading_journal_last90d.*.csv' | Sort-Object LastWriteTime -Desc | Select-Object -Skip 1 -First 1
if (-not $latest) { Fail "No trading_journal_last90d.*.csv found in $OutDir" }

# Helpers
function To-Double($x){ try { [double]$x } catch { 0.0 } }
function Pnl-Row($r){
  $qty   = To-Double $r.Qty
  $entry = To-Double $r.Entry
  $exit  = To-Double $r.Exit
  $fees  = To-Double $r.Fees
  $side  = ("" + $r.Side).ToLower()
  $gross = if ($side -eq 'buy') { ($exit - $entry) * $qty }
           elseif ($side -eq 'sell'){ ($entry - $exit) * $qty }
           else { 0.0 }
  @{ Gross = $gross; Fees = $fees; Net = ($gross - $fees) }
}
function Summarize($csvPath){
  $rows = Import-Csv -Path $csvPath
  $acc = [ordered]@{ Trades=0; Gross=0.0; Fees=0.0; Net=0.0; BySym=@{} }
  foreach($r in $rows){
    $p = Pnl-Row $r
    $acc.Trades++
    $acc.Gross += $p.Gross
    $acc.Fees  += $p.Fees
    $acc.Net   += $p.Net
    $sym = if ($r.Symbol) { (""+$r.Symbol).ToUpper() } else { '' }
    if (-not $acc.BySym.ContainsKey($sym)) { $acc.BySym[$sym] = [ordered]@{ Trades=0; Net=0.0; Gross=0.0 } }
    $acc.BySym[$sym].Trades += 1
    $acc.BySym[$sym].Net    += $p.Net
    $acc.BySym[$sym].Gross  += $p.Gross
  }
  $top = $acc.BySym.GetEnumerator() | Where-Object { $_.Key -ne '' } |
         Sort-Object { $_.Value.Net } -Descending | Select-Object -First 5 |
         ForEach-Object { "{0}:{1:N2} ({2})" -f $_.Key,$_.Value.Net,$_.Value.Trades }
  [pscustomobject]@{
    Path   = $csvPath
    Trades = $acc.Trades
    Gross  = [math]::Round($acc.Gross,2)
    Fees   = [math]::Round($acc.Fees,2)
    Net    = [math]::Round($acc.Net,2)
    Top    = if ($top) { ($top -join ", ") } else { "(no symbols)" }
  }
}

$now = Get-Date
$sumNew = Summarize $latest.FullName
$sumOld = if ($prev) { Summarize $prev.FullName } else { $null }

$deltaTrades = if ($sumOld){ $sumNew.Trades - $sumOld.Trades } else { $sumNew.Trades }
$deltaNet    = if ($sumOld){ $sumNew.Net    - $sumOld.Net }    else { $sumNew.Net    }
$deltaGross  = if ($sumOld){ $sumNew.Gross  - $sumOld.Gross }  else { $sumNew.Gross  }
$deltaFees   = if ($sumOld){ $sumNew.Fees   - $sumOld.Fees }   else { $sumNew.Fees   }

function FmtDelta($v){ if ($v -ge 0){ "+{0:N2}" -f $v } else { "{0:N2}" -f $v } }

# --- Post to Slack ---
function Post-SlackText([string]$channel,[string]$text){
  if (Get-Command Invoke-Slack -ErrorAction SilentlyContinue){
    Invoke-Slack -Method 'chat.postMessage' -Body @{ channel=$channel; text=$text }
  } else {
    if (-not $Token){ Fail "SLACK_BOT_TOKEN missing in env and Invoke-Slack not available." }
    $uri = "https://slack.com/api/chat.postMessage"
    $body = @{ channel = $channel; text = $text } | ConvertTo-Json -Depth 4
    Invoke-RestMethod -Method Post -Uri $uri -Headers @{Authorization="Bearer $Token"; 'Content-Type'='application/json'} -Body $body | Out-Null
  }
}

function Upload-SlackFile([string]$channel,[string]$filePath,[string]$title){
  if (-not $Token){ return }  # skip if no token
  $client = New-Object System.Net.Http.HttpClient
  $client.DefaultRequestHeaders.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer",$Token)
  $mp = New-Object System.Net.Http.MultipartFormDataContent
  $mp.Add((New-Object System.Net.Http.StringContent($channel)),'channels')
  $mp.Add((New-Object System.Net.Http.StringContent($title)),'title')
  $mp.Add((New-Object System.Net.Http.StringContent([IO.Path]::GetFileName($filePath))),'filename')
  $bytes = [IO.File]::ReadAllBytes($filePath)
  $ba    = New-Object System.Net.Http.ByteArrayContent($bytes)
  $ba.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue('text/csv')
  $mp.Add($ba,'file',[IO.Path]::GetFileName($filePath))
  $resp = $client.PostAsync('https://slack.com/api/files.upload',$mp).Result
  if (-not $resp.IsSuccessStatusCode){
    $t = $resp.Content.ReadAsStringAsync().Result
    Write-Host "files.upload failed: $($resp.StatusCode) $t" -ForegroundColor Yellow
  }
  $client.Dispose()
}

if (-not $Channel){ Fail "SLACK_CHANNEL_ID missing (set env var or pass -Channel)." }

$header = ":bar_chart: *Notion Audit  last 90d*  (`$($now.ToString('yyyy-MM-dd HH:mm'))`)"
$line1  = "*Trades:* $($sumNew.Trades)  (Δ $(FmtDelta $deltaTrades))"
$line2  = "*Net:* $($sumNew.Net.ToString('N2'))  (Δ $(FmtDelta $deltaNet))    *Gross:* $($sumNew.Gross.ToString('N2')) (Δ $(FmtDelta $deltaGross))    *Fees:* $($sumNew.Fees.ToString('N2')) (Δ $(FmtDelta $deltaFees))"
$line3  = "*Top5 (net):* $($sumNew.Top)"
$line4  = "_File:_ `$($latest.Name)`"
$text = "$header`n$line1`n$line2`n$line3`n$line4"

Post-SlackText -channel $Channel -text $text
Upload-SlackFile -channel $Channel -filePath $latest.FullName -title "Trading Journal last90d"

Write-Host "Slack notify sent for $($latest.Name)" -ForegroundColor Green
