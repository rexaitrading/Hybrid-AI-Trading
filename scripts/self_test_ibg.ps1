param(
  [ValidateSet('paper','live')] [string]$Mode = 'paper',
  [int]$TcpTimeoutMs = 2000,
  [int]$Retries = 10,
  [int]$IntervalSec = 3
)
$ErrorActionPreference='Stop'

# PS5-safe port mapping
$port = 4002
if ($Mode -eq 'live') { $port = 4001 }
$addr = '127.0.0.1'   # DO NOT use $host (reserved automatic variable)

# Windows Time service
$timeOk = $false
try {
  $w32 = Get-Service w32time -ErrorAction Stop
  $timeOk = $w32.Status -eq 'Running'
} catch { $timeOk = $false }

function Test-TcpPort([string]$h,[int]$p,[int]$ms){
  $c=New-Object Net.Sockets.TcpClient
  try {
    $iar=$c.BeginConnect($h,$p,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($ms)){$c.Close();return $false}
    $c.EndConnect($iar); $c.Close(); return $true
  } catch { try{$c.Close()}catch{}; return $false }
}

$ok = $false
for($i=1;$i -le $Retries;$i++){
  if(Test-TcpPort $addr $port $TcpTimeoutMs){ $ok = $true; break }
  Start-Sleep -Seconds $IntervalSec
}

$status = [ordered]@{
  ts = (Get-Date).ToString('s')
  mode = $Mode
  port = $port
  tcp_address = $addr
  time_service = $timeOk
  tcp_listening = $ok
  attempts = $Retries
  interval_sec = $IntervalSec
  timeout_ms = $TcpTimeoutMs
}
$status | ConvertTo-Json -Depth 4 | Out-Host
if(-not $timeOk -or -not $ok){ exit 2 }
