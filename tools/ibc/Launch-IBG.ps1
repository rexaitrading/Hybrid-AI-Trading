param([switch]$ForceRestart)

$ErrorActionPreference = "Stop"

# simple logger
$logDir = "C:\IBC\Logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("autorun_{0}.log" -f (Get-Date -Format yyyyMMdd_HHmmss))
function Log($m){ "[$(Get-Date -Format o)] $m" | Out-File $log -Append }

Log "Launch-IBG: start"

# 0) clean slate
Log "killing old ibgateway/javaw..."
if($ForceRestart){ taskkill /F /IM ibgateway.exe 2>$null }
if($ForceRestart){ taskkill /F /IM javaw.exe     2>$null }
Start-Sleep 1

# 1) paths and preflight
$bat  = "C:\IBC\StartGateway.bat"
$cini = "C:\IBC\config_paper.ini"
if (!(Test-Path $bat))  { Log "ERROR: missing $bat";  exit 1 }
if (!(Test-Path $cini)) { Log "ERROR: missing $cini"; exit 1 }

# 2) start Gateway **detached** (no /INLINE)
try {
  $cmd = "cmd.exe"
  $arg = '/c start "" "{0}" 1040 paper "{1}"' -f $bat, $cini
  Log "spawning: cmd.exe $arg"
  Start-Process -FilePath $cmd -ArgumentList $arg -WorkingDirectory 'C:\IBC' -WindowStyle Hidden | Out-Null
} catch {
  Log ("ERROR: Start-Process failed -> {0}" -f $_.Exception.Message)
  exit 1
}

# 3) wait for Gateway process to appear (max ~90s)
$appeared = $false
for ($i=0; $i -lt 45; $i++) {
  $procs = Get-Process ibgateway,javaw -ErrorAction SilentlyContinue
  $names = ($procs | Select-Object -ExpandProperty Name) -join ', '
  Log ("proc check {0}: {1}" -f $i, $names)
  if ($procs) { $appeared = $true; break }
  Start-Sleep 2
}
if (-not $appeared) { Log "ERROR: ibgateway/javaw did not appear"; exit 1 }

# 4) choose a Python to probe API (SYSTEM-safe)
$probeCands = @(
  "C:\Users\rhcy9\OneDrive\??\HybridAITrading\.venv\Scripts\python.exe",
  "C:\Python312\python.exe",
  "C:\Program Files\Python312\python.exe",
  "C:\Program Files (x86)\Python312\python.exe",
  "$env:ProgramFiles\Python311\python.exe",
  "$env:SystemRoot\py.exe"
) | Where-Object { Test-Path $_ }
$pyExe = $probeCands | Select-Object -First 1

# 5) write probe to temp and poll up to ~2 minutes
$probePy  = Join-Path $env:TEMP ("ib_probe_{0}.py" -f ([Guid]::NewGuid().ToString('N')))
$pyScript = @"
from ib_insync import *
ib=IB()
ok = ib.connect('127.0.0.1',4002,clientId=999,timeout=8)
print('connect_ok:', bool(ok))
if ok:
    print('serverTime:', ib.serverTime())
    ib.disconnect()
"@
Set-Content -LiteralPath $probePy -Value $pyScript -Encoding ASCII

$ok = $false
for ($i=0; $i -lt 60; $i++) {
  if ($pyExe) {
    try { $out = & $pyExe $probePy 2>&1 } catch { $out = $_ | Out-String }
    Log ("probe {0} -> {1}" -f $i, ($out -replace "`r?`n",' | '))
    if ($out -match 'connect_ok:\s*True') { $ok = $true; break }
  } else {
    $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port 4002 -WarningAction SilentlyContinue
    Log ("tcp probe {0} -> TcpTestSucceeded={1}" -f $i, $tcp.TcpTestSucceeded)
    if ($tcp.TcpTestSucceeded) { $ok = $true; break }
  }
  Start-Sleep 2
}

Remove-Item -Force -ErrorAction SilentlyContinue $probePy

if ($ok) { Log "API READY"; exit 0 }
else     { Log "ERROR: API NOT READY"; exit 1 }

