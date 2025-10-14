param(
  [string]$Cfg     = "hybrid_ai_trading\cfg\paper.yaml",
  [string]$ApiHost = "localhost",
  [int]   $Port    = 7497,
  [string]$VenvPy  = ".\.venv\Scripts\python.exe"
)


# Normalize localhost to IPv4 (avoids IPv6/::1 handshake issues on IBG)
if (\ -eq 'localhost') { \ = '127.0.0.1' }  # Normalize localhost to 127.0.0.1
# Resolve Python
if (Test-Path $VenvPy) {
  $VenvPy = (Resolve-Path $VenvPy).Path
} else {
  $defaultPy = (Resolve-Path (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe") -ErrorAction SilentlyContinue)
  if ($defaultPy) { $VenvPy = $defaultPy.Path }
}

if (-not (Test-Path $VenvPy)) {
  Write-Error "Python not found. Pass -VenvPy (e.g. .\.venv\Scripts\python.exe)"
  exit 1
}

# Export env for downstream processes
$env:IB_HOST = $ApiHost
$env:IB_PORT = "$Port"
if (-not $env:IB_CLIENT_ID) { $env:IB_CLIENT_ID = "3001" }

# Quick PS-native port probe (renamed params to avoid $Host collision)
function Test-TcpOpen {
  param(
    [string]$HostName,
    [int]$TcpPort,
    [int]$TimeoutMs = 4000
  )
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($HostName, $TcpPort, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs)) {
      $client.Close(); return $false
    }
    $client.EndConnect($iar); $client.Close(); return $true
  } catch { return $false }
}

$open = Test-TcpOpen -HostName $ApiHost -TcpPort $Port -TimeoutMs 4000
if ($open) {
  Write-Host ("[run] IB API listening at {0}:{1} (clientId={2})" -f $ApiHost,$Port,$env:IB_CLIENT_ID) -ForegroundColor Green
} else {
  Write-Warning ("[run] {0}:{1} not open. Launching anyway (the pipeline may wait for IB)." -f $ApiHost,$Port)
}

# Launch live loop (no retry loop)
Write-Host ("[run] launching live_loop (host={0}, port={1}, cid={2}, cfg={3})" -f $ApiHost,$Port,$env:IB_CLIENT_ID,$Cfg)
& $VenvPy -u -m hybrid_ai_trading.pipelines.live_loop --cfg "$Cfg"
$code = $LASTEXITCODE

# Map Ctrl+C (0xC000013A) to a friendly exit code 130
if ($code -eq 3221225786) {
  Write-Host "[run] live_loop stopped by user (Ctrl+C)" -ForegroundColor Yellow
  $code = 130
} else {
  Write-Host "[run] live_loop exited with code $code"
}
exit $code