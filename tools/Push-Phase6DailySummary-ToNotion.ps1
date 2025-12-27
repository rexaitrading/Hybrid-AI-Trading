[CmdletBinding()]
param(
  [string]$CsvPath = ".\logs\phase6_daily_summary.csv"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path, [string]$Text){
  $enc = New-Object System.Text.UTF8Encoding($false)
  $t = $Text -replace "`r`n","`n"
  [System.IO.File]::WriteAllText((Resolve-Path $Path), $t + "`n", $enc)
}

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
$db  = $env:HAT_NOTION_PHASE6_DB_ID
if([string]::IsNullOrWhiteSpace($tok)){ throw "Missing env NOTION_TOKEN" }
if([string]::IsNullOrWhiteSpace($db)){ throw "Missing env HAT_NOTION_PHASE6_DB_ID" }

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

# Create-only mode (Phase6 summary data source currently has only Title property "Name")
$titleText = ("Phase6 {0} ok={1} ready={2}" -f $asof, $ok, $ready)

# Parent: for multi-source DBs, we are using data_source_id here
$cUrl = "https://api.notion.com/v1/pages"
$cBody = @{
  "parent" = @{ "data_source_id" = $db }
  "properties" = @{
    "Name" = @{ "title" = @(@{ "type"="text"; "text"=@{ "content" = $titleText } }) }
  }
} | ConvertTo-Json -Depth 12

$resp = Invoke-Notion -Method Post -Url $cUrl -Headers $headers -Body $cBody
$newId = [string]$resp.id
Write-Host "[NOTION] Created Phase6 row page=$newId" -ForegroundColor Green
Write-Host ("[NOTION] phase6_daily_summary: as_of={0} ok={1} ready={2} reason={3}" -f $asof,$ok,$ready,$reason) -ForegroundColor Cyan
exit 0
