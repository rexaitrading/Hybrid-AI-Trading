[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}
function Slice-Date([string]$s){
  $s = ($s + "").Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol NVDA | ConvertFrom-Json
$todayLocal = Slice-Date ([string]$rc.as_of_date)

$logsDir = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null;
$outPath = Join-Path $logsDir "edge_validity.json"
$obj = [ordered]@{
  ts_utc   = (Get-Date).ToUniversalTime().ToString("o")
  market   = $Market
  as_of_date = $todayLocal
  ok_today = $false
  edge_score = 0.0
  reasons  = @("stub_not_implemented")
}
Write-Utf8NoBomLf $outPath ($obj | ConvertTo-Json -Depth 8)
Write-Host ("[EDGE] wrote " + $outPath + " ok_today=false reason=stub_not_implemented") -ForegroundColor Yellow
