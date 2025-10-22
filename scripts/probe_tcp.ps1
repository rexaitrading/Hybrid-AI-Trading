param(
  [string]$Addr = '127.0.0.1',
  [int]$Port = 4002,      # 4002=Paper, 4001=Live
  [int]$Retries = 999,
  [int]$IntervalSec = 30,
  [int]$TimeoutMs = 2000
)

function Test-TcpPort {
  param([string]$addr,[int]$port,[int]$timeoutMs=2000)
  $c = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $c.BeginConnect($addr,$port,$null,$null)
    if (-not $iar.AsyncWaitHandle.WaitOne($timeoutMs)) { $c.Close(); return $false }
    $c.EndConnect($iar); $c.Close(); return $true
  } catch { try{$c.Close()}catch{}; return $false }
}

for ($i=1; $i -le $Retries; $i++) {
  $ok = Test-TcpPort -addr $Addr -port $Port -timeoutMs $TimeoutMs
  Write-Host ("{0} tcp://{1}:{2} -> {3}" -f (Get-Date -Format 'HH:mm:ss'), $Addr, $Port, $ok)
  if ($ok) { [console]::Beep(880,200); break }
  Start-Sleep -Seconds $IntervalSec
}
