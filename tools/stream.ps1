# tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  # Purge: kill any NON-venv runner_stream (only allow venv python)
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'runner_stream\.py' -and
      $_.CommandLine -notmatch [regex]::Escape($Script:VenvPy)
    }
  if ($bad) {
    foreach($b in $bad){
      try {
        Write-Host ("[STREAM] Killing non-venv runner_stream pid={0}" -f $b.ProcessId) -ForegroundColor Yellow
        Stop-Process -Id $b.ProcessId -Force -ErrorAction Stop
      } catch {}
    }
  }

  # Guard: do not spawn duplicates (after purge)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing Python venv executable: $Script:VenvPy"
  }

  # Prefer env IB_PORT else default 4002 (PS5.1-safe)
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on 127.0.0.1:$port (your IBG is listening on 4002 per netstat)"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"

# Containment: kill any runner_stream that is NOT venv python
try {
  $venv = (Resolve-Path $Script:VenvPy).Path
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { (# tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  # Purge: kill any NON-venv runner_stream (only allow venv python)
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'runner_stream\.py' -and
      $_.CommandLine -notmatch [regex]::Escape($Script:VenvPy)
    }
  if ($bad) {
    foreach($b in $bad){
      try {
        Write-Host ("[STREAM] Killing non-venv runner_stream pid={0}" -f $b.ProcessId) -ForegroundColor Yellow
        Stop-Process -Id $b.ProcessId -Force -ErrorAction Stop
      } catch {}
    }
  }

  # Guard: do not spawn duplicates (after purge)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing Python venv executable: $Script:VenvPy"
  }

  # Prefer env IB_PORT else default 4002 (PS5.1-safe)
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on 127.0.0.1:$port (your IBG is listening on 4002 per netstat)"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
  return
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}.CommandLine + "") -match 'runner_stream\.py' -and (# tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  # Purge: kill any NON-venv runner_stream (only allow venv python)
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'runner_stream\.py' -and
      $_.CommandLine -notmatch [regex]::Escape($Script:VenvPy)
    }
  if ($bad) {
    foreach($b in $bad){
      try {
        Write-Host ("[STREAM] Killing non-venv runner_stream pid={0}" -f $b.ProcessId) -ForegroundColor Yellow
        Stop-Process -Id $b.ProcessId -Force -ErrorAction Stop
      } catch {}
    }
  }

  # Guard: do not spawn duplicates (after purge)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing Python venv executable: $Script:VenvPy"
  }

  # Prefer env IB_PORT else default 4002 (PS5.1-safe)
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on 127.0.0.1:$port (your IBG is listening on 4002 per netstat)"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
  return
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}.CommandLine + "") -notmatch [regex]::Escape($venv) } |
    ForEach-Object {
      Write-Host ("[STREAM] KILL_NON_VENV pid={0}" -f # tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  # Purge: kill any NON-venv runner_stream (only allow venv python)
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'runner_stream\.py' -and
      $_.CommandLine -notmatch [regex]::Escape($Script:VenvPy)
    }
  if ($bad) {
    foreach($b in $bad){
      try {
        Write-Host ("[STREAM] Killing non-venv runner_stream pid={0}" -f $b.ProcessId) -ForegroundColor Yellow
        Stop-Process -Id $b.ProcessId -Force -ErrorAction Stop
      } catch {}
    }
  }

  # Guard: do not spawn duplicates (after purge)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing Python venv executable: $Script:VenvPy"
  }

  # Prefer env IB_PORT else default 4002 (PS5.1-safe)
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on 127.0.0.1:$port (your IBG is listening on 4002 per netstat)"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
  return
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}.ProcessId) -ForegroundColor Yellow
      Stop-Process -Id # tools/stream.ps1  clean helpers (PS5.1-safe, SINGLE definition)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir "logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
}

function start-stream {
  [CmdletBinding()]
  param(
    [string]$ClientId = '3021',
    [ValidateSet(1,3)]
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  # Purge: kill any NON-venv runner_stream (only allow venv python)
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'runner_stream\.py' -and
      $_.CommandLine -notmatch [regex]::Escape($Script:VenvPy)
    }
  if ($bad) {
    foreach($b in $bad){
      try {
        Write-Host ("[STREAM] Killing non-venv runner_stream pid={0}" -f $b.ProcessId) -ForegroundColor Yellow
        Stop-Process -Id $b.ProcessId -Force -ErrorAction Stop
      } catch {}
    }
  }

  # Guard: do not spawn duplicates (after purge)
  $existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' }
  if ($existing) {
    Write-Host "[STREAM] Already running. Skipping new launch." -ForegroundColor Yellow
    return
  }

  if (-not (Test-Path -LiteralPath $Script:VenvPy)) {
    throw "Missing Python venv executable: $Script:VenvPy"
  }

  # Prefer env IB_PORT else default 4002 (PS5.1-safe)
  $portStr = $env:IB_PORT
  if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "4002" }
  $port = [int]$portStr

  # Fail-closed if IB API port not listening
  $tnc = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
  if (-not $tnc.TcpTestSucceeded) {
    throw "IB API port not listening on 127.0.0.1:$port (your IBG is listening on 4002 per netstat)"
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = "$port"
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Out-File -LiteralPath $out -Encoding utf8
  '' | Out-File -LiteralPath $err -Encoding utf8

  Start-Process -FilePath $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
  return
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}.ProcessId -Force -ErrorAction SilentlyContinue
    }
} catch {}
return
  return
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'runner_stream\.py' } |
    Select-Object ProcessId, CommandLine | Format-Table -AutoSize
}