[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$srcDir = Join-Path $repoRoot "src\.intel"
$logsDir = Join-Path $repoRoot "logs"
$logsIntel = Join-Path $logsDir ".intel"
New-Item -ItemType Directory -Force -Path $srcDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsIntel | Out-Null

$src = Join-Path $srcDir "youtube_feed.jsonl"
if(-not (Test-Path $src)){
  [System.IO.File]::WriteAllText($src, "", (New-Object System.Text.UTF8Encoding($false)))
}

Copy-Item -LiteralPath $src -Destination (Join-Path $logsIntel "youtube_feed.jsonl") -Force
Copy-Item -LiteralPath $src -Destination (Join-Path $logsDir "youtube_feed.jsonl") -Force

$line = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = (Get-Date).ToString("yyyy-MM-dd")
  kind = "intel_youtube_stub"
  path = $src
  note = "YouTube collector stub; implement channel ingestion later."
} | ConvertTo-Json -Compress

$line | Add-Content -LiteralPath (Join-Path $logsDir "intel_feed.jsonl") -Encoding utf8
Write-Host "[INTEL-YT] OK (stub) mirrored feeds + appended intel_feed.jsonl" -ForegroundColor Green
exit 0