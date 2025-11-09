param(
  [string]$OutFile = 'C:\ProgramData\ibg_status.json',
  [int]$Port = 4002  # PAPER=4002, LIVE=4001
)

$ErrorActionPreference='Stop'

# Prefer real process; fall back to ports; else write a stub with gwPid 0
$gwPid = 0
try {
  $proc = Get-Process -Name 'ibgateway' -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($proc) { $gwPid = $proc.Id }
} catch {}

if ($gwPid -eq 0) {
  try {
    $net = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
           Where-Object { $_.LocalPort -in 4001,4002 } | Select-Object -First 1
    if ($net) {
      $gwPid = $net.OwningProcess
      if ($Port -notin 4001,4002) { $Port = $net.LocalPort }
    }
  } catch {}
}

$obj = [pscustomobject]@{
  pid = $gwPid
  port = $Port
  ts = (Get-Date).ToString('s')
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
($obj | ConvertTo-Json -Depth 5) | Set-Content -Encoding utf8 -Path $OutFile
Write-Host " Heartbeat -> $OutFile (pid=$gwPid port=$Port ts=$($obj.ts))" -ForegroundColor Green
