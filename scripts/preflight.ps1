param(
  [string]$HealthUrl     = "http://127.0.0.1:8789/health/providers",
  [int]   $IBPortPrimary = 4002,
  [string[]]$Symbols     = @("AAPL","BTCUSD","BTC/USDT","EURUSD","USDJPY","XAUUSD","CL1!")
)
$ErrorActionPreference = "Stop"
$fail = @()

# 1) Provider health (pure .NET HttpClient)
try {
  Add-Type -AssemblyName System.Net.Http | Out-Null
  $http = [System.Net.Http.HttpClient]::new()
  $http.Timeout = [TimeSpan]::FromSeconds(8)
  $jsonText = $http.GetStringAsync($HealthUrl).GetAwaiter().GetResult()
  $json     = $jsonText | ConvertFrom-Json
  $bad      = @($json.checks | Where-Object { -not $_.ok })
  if ($bad.Count -gt 0) {
    $fail += "Health BAD: " + ($bad | ForEach-Object { "$($_.provider):$($_.symbol)" } -join ", ")
  }
} catch {
  $fail += "Health fetch failed: $($_.Exception.Message)"
}

# 2) IB API port probe (Gateway-only: 4002)
try {
  $tcp = Test-NetConnection 127.0.0.1 -Port $IBPortPrimary -WarningAction SilentlyContinue
  if (-not ($tcp -and $tcp.TcpTestSucceeded)) {
    $fail += "IB API not listening on $IBPortPrimary (Gateway Paper expected)"
  }
} catch {
  $fail += "IB probe failed: $($_.Exception.Message)"
}

# 3) Mini price snapshot (Python temp)
try {
  $env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
  $pySyms = ($Symbols | ForEach-Object { "'" + ($_ -replace "'", "''") + "'" }) -join ", "
  $py = @"
from hybrid_ai_trading.utils.providers import load_providers, get_prices
cfg = load_providers('config/providers.yaml')
syms = [$pySyms]
out  = get_prices(syms, cfg)
bad  = [o for o in out if not isinstance(o.get('price'), (int,float))]
print('__OK__' if not bad else '__BAD__:' + ';'.join(f"{b.get('symbol')}:{b.get('reason')}" for b in bad))
"@
  $tmp = Join-Path $env:TEMP ("preflight_{0}.py" -f ([guid]::NewGuid().ToString("N")))
  [IO.File]::WriteAllText($tmp, $py, (New-Object System.Text.UTF8Encoding($false)))
  $res = & .\.venv\Scripts\python.exe $tmp
  Remove-Item $tmp -ErrorAction SilentlyContinue
  if (-not $res) { $fail += "Snapshot returned no output" }
  elseif ($res -like '__BAD__*') { $fail += "Snapshot BAD: " + $res.Substring(7) }
} catch {
  $fail += "Snapshot failed: $($_.Exception.Message)"
}

if ($fail.Count -eq 0) {
  Write-Host "✅ PRE-FLIGHT: GO"
  exit 0
} else {
  Write-Host "❌ PRE-FLIGHT: NO-GO"
  $fail | ForEach-Object { Write-Host " - $_" }
  exit 1
}
