param(
  [ValidateSet("paper","live")] [string]$Mode="paper",
  [int]$Retries = 20
)
$ErrorActionPreference='Stop'

# PS5-safe mapping
$port = 4002
if ($Mode -eq 'live') { $port = 4001 }
$addr = '127.0.0.1'

# fast TCP probe
function Test-TcpPort([string]$h,[int]$p,[int]$timeoutMs=2000){
  $c=New-Object Net.Sockets.TcpClient
  try {
    $iar=$c.BeginConnect($h,$p,$null,$null)
    if(-not $iar.AsyncWaitHandle.WaitOne($timeoutMs)){$c.Close();return $false}
    $c.EndConnect($iar); $c.Close(); return $true
  } catch { try{$c.Close()}catch{}; return $false }
}

$ok = $false
for($i=0; $i -lt $Retries; $i++){
  if (Test-TcpPort -h $addr -p $port -timeoutMs 2000) { $ok = $true; break }
  Start-Sleep -Seconds 3
}

# fallback to Test-NetConnection for human-readability (once)
if (-not $ok) {
  try { $tnc = Test-NetConnection -ComputerName $addr -Port $port -WarningAction SilentlyContinue; $ok = [bool]$tnc.TcpTestSucceeded } catch {}
}

# persist a tiny line + echo to console
$logDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$line = ('{0} {1} tcp://{2}:{3} -> {4}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'), $Mode, $addr, $port, $ok)
$line | Tee-Object -FilePath (Join-Path $logDir 'probe_last.txt')

if (-not $ok) { exit 2 }
