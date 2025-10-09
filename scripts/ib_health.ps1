param(
  [string]$Host = $env:IB_HOST ? $env:IB_HOST : "127.0.0.1",
  [int]$Port = $env:IB_PORT ? [int]$env:IB_PORT : 4003,
  [int]$ClientId = $env:IB_CLIENT_ID ? [int]$env:IB_CLIENT_ID : 3021,
  [string]$LogFile = ".\logs\ib_health.jsonl"
)
if (-not (Test-Path ".\logs")) { New-Item -ItemType Directory -Path ".\logs" | Out-Null }
Write-Host "Hybrid AI Quant Pro — IB Health via CLI" -ForegroundColor Cyan
Write-Host "Target: $Host:$Port (clientId=$ClientId)" -ForegroundColor DarkCyan
$env:PYTHONPATH = 'src'
# Port probe
$probe = Test-NetConnection $Host -Port $Port -WarningAction SilentlyContinue
Write-Host ("TcpTestSucceeded: {0}" -f $probe.TcpTestSucceeded) -ForegroundColor Green
# CLI health (structured logs to file)
& .\.venv\Scripts\python.exe -m hybrid_ai_trading.utils ib health --host $Host --port $Port --client-id $ClientId --mdt 3 --log-file $LogFile --log-level INFO --json
