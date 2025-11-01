param(
  [Parameter(Mandatory=$true)][string]$ApiKey,
  [string[]]$Channels,
  [int]$MaxPerChannel = 5,
  [string]$OutNdjson = ".\data\feeds\youtube_latest.ndjson",
  [string]$Query = "order flow scalping OR orderflow OR tape reading OR futures scalping"
)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$true

New-Item -ItemType Directory -Force (Split-Path $OutNdjson) | Out-Null
Remove-Item -Path $OutNdjson -ErrorAction SilentlyContinue

function Write-Item([hashtable]$h){
  ($h | ConvertTo-Json -Compress) + "`n" | Add-Content -Encoding UTF8 -Path $OutNdjson
}

# Channel pulls
foreach($cid in $Channels){
  $u = "https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=$cid&order=date&maxResults=$MaxPerChannel&key=$ApiKey"
  try { $r = Invoke-RestMethod -Uri $u -Method Get } catch { Write-Warning $_; continue }
  foreach($it in $r.items){
    if($it.id.kind -ne 'youtube#video'){ continue }
    Write-Item @{
      source='channel'
      channelId = $cid
      videoId = $it.id.videoId
      title = $it.snippet.title
      publishedAt = $it.snippet.publishedAt
      url = "https://www.youtube.com/watch?v=$($it.id.videoId)"
      channelTitle = $it.snippet.channelTitle
    }
  }
}

# Keyword search
$u2 = "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=10&q=$([uri]::EscapeDataString($Query))&order=date&key=$ApiKey"
try { $r2 = Invoke-RestMethod -Uri $u2 -Method Get } catch { Write-Warning $_; $r2=$null }
if($r2){
  foreach($it in $r2.items){
    Write-Item @{
      source='search'
      videoId = $it.id.videoId
      title = $it.snippet.title
      publishedAt = $it.snippet.publishedAt
      url = "https://www.youtube.com/watch?v=$($it.id.videoId)"
      channelTitle = $it.snippet.channelTitle
    }
  }
}

" Wrote $OutNdjson"
