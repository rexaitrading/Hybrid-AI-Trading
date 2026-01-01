[CmdletBinding()]
param(
  [int]$Port = 4002,
  [string]$StatusPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve default status path from env if not provided
if([string]::IsNullOrWhiteSpace($StatusPath)){
  $StatusPath = [string]$env:HAT_IBG_STATUS_PATH
}
if([string]::IsNullOrWhiteSpace($StatusPath)){
  $StatusPath = [System.Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")
}
if([string]::IsNullOrWhiteSpace($StatusPath)){
  $StatusPath = "C:\IBC\status\ibg_status.json"
}

$tnc = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
$now = (Get-Date).ToString("o")

$payload = [ordered]@{
  timestamp = $now
  port = $Port
  portUp = [bool]$tnc.TcpTestSucceeded
  pid = 0
  uptimeSec = $null
  cpuSec = $null
  rssMB = 0
  path = ""
  gw = $null
  lastPing = [ordered]@{
    epoch = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
    ok = [bool]$tnc.TcpTestSucceeded
  }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StatusPath) | Out-Null
[System.IO.File]::WriteAllText($StatusPath, ($payload | ConvertTo-Json -Depth 6), $utf8NoBom)

Write-Host ("[IBG] wrote {0} portUp={1} port={2} ts={3}" -f $StatusPath,$payload.portUp,$Port,$now) -ForegroundColor Green
exit 0