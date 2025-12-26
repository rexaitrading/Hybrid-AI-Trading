[CmdletBinding()]
param(
  [switch]$DeleteStamp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n", "`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Fail([string]$Msg) {
  Write-Host "[DISARM] FAIL-CLOSED: $Msg" -ForegroundColor Red
  exit 2
}

$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$stampPath = Join-Path $logsDir "nvda_live_ready_stamp.json"

if($DeleteStamp){
  try {
    if(Test-Path $stampPath){
      Remove-Item -LiteralPath $stampPath -Force
      Write-Host "[DISARM] Removed stamp: $stampPath" -ForegroundColor Yellow
    } else {
      Write-Host "[DISARM] No stamp to remove: $stampPath" -ForegroundColor Yellow
    }
    exit 0
  } catch {
    Fail "Could not remove stamp: $($_.Exception.Message)"
  }
}

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  nvda_live_ready = $false
  reason = "manual_disarm"
}

Write-Utf8NoBom -Path $stampPath -Text ($payload | ConvertTo-Json -Depth 6)
Write-Host "[DISARM] Wrote nvda_live_ready=false stamp: $stampPath" -ForegroundColor Green
exit 0