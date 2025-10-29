# tools/stream.ps1 â€” clean helpers

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir ".logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}

function start-stream {
  param(
    [string]$ClientId = '3021',
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  if (-not (Test-Path $Script:VenvPy)) {
    Write-Host "Missing Python: $Script:VenvPy" -ForegroundColor Red
    return
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = '7497'
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Set-Content $out; '' | Set-Content $err

  # Launch
  Start-Process $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `

          # If an -ArgumentList contains gw + paper, strip paper
          $prefix = $matches[1]; $args = $matches[2]
          if ($args -match 'gw[^)]*paper'){
            $args -replace '\s*["'']paper["'']\s*,?', '' | ForEach-Object { $prefix + # tools/stream.ps1 â€” clean helpers

# Resolve project paths relative to this file, not caller state
$Script:ToolsDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$Script:ProjDir  = Split-Path -Path $Script:ToolsDir -Parent
$Script:LogsDir  = Join-Path $Script:ProjDir ".logs"
$Script:VenvPy   = Join-Path $Script:ProjDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $Script:LogsDir | Out-Null

function stop-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}

function start-stream {
  param(
    [string]$ClientId = '3021',
    [int]   $MdType   = 3     # 1=REALTIME, 3=DELAYED
  )

  if (-not (Test-Path $Script:VenvPy)) {
    Write-Host "Missing Python: $Script:VenvPy" -ForegroundColor Red
    return
  }

  # Env for runner
  $env:PYTHONPATH       = (Join-Path $Script:ProjDir 'src')
  $env:PYTHONUNBUFFERED = '1'
  $env:IB_HOST          = '127.0.0.1'
  $env:IB_PORT          = '7497'
  $env:IB_CLIENT_ID     = $ClientId
  $env:IB_MDT           = "$MdType"

  # Log files
  $ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
  $out = Join-Path $Script:LogsDir "stream_run.$ts.out.log"
  $err = Join-Path $Script:LogsDir "stream_run.$ts.err.log"
  '' | Set-Content $out; '' | Set-Content $err

  # Launch
  Start-Process $Script:VenvPy `
    -WorkingDirectory $Script:ProjDir `
    -ArgumentList @('-u','-X','dev','src\hybrid_ai_trading\runners\runner_stream.py','--client-id',$ClientId) `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
}

function tail-stream {
  $o = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.out.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if ($o) {
    Get-Content $o.FullName -Wait -Tail 60
  } else {
    Write-Host 'No OUT log yet.'
  }
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' } |
    Select-Object ProcessId,
      @{n='Python';e={($_.CommandLine -split '"')[1]}},
      @{n='Args';e={ $_.CommandLine -replace '.*runner_stream\.py','runner_stream.py' }}

  Write-Host "`n== Last OUT/ERR logs ==" -ForegroundColor Cyan
  $o = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.out.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  $e = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.err.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1

  if ($o) { "OUT: $($o.FullName)"; Get-Content $o.FullName -Tail 20 } else { 'No OUT yet.' }
  if ($e) { "`nERR: $($e.FullName)"; Get-Content $e.FullName -Tail 20 } else { 'No ERR yet.' }
}
function tail-stream-err {
  $e = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.err.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if ($e) {
    "ERR: $($e.FullName)"
    Get-Content $e.FullName -Wait -Tail 120
  } else {
    Write-Host 'No ERR log yet.'
  }
}

function ps-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' -or $_.CommandLine -like '*runner_paper.py*' } |
    Select-Object ProcessId,
      @{n='Runner';e={($_.CommandLine -split 'runner_')[1] -split '\.py' | Select-Object -First 1 | ForEach-Object {"runner_$_.py"}}},
      @{n='ClientId';e={ if ($_.CommandLine -match '--client-id\s+(\d+)'){ $matches[1] } }},
      @{n='Python';e={($_.CommandLine -split '"')[1]}},
      @{n='Cmd';e={$_.CommandLine}}
}
 }
          } else { $matches[0] }
         `
    -RedirectStandardOutput $out `
    -RedirectStandardError  $err `
    -WindowStyle Minimized | Out-Null

  Write-Host "Stream booted. OUT: $out"
  Write-Host "Stream booted. ERR: $err"
}

function tail-stream {
  $o = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.out.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if ($o) {
    Get-Content $o.FullName -Wait -Tail 60
  } else {
    Write-Host 'No OUT log yet.'
  }
}

function status-stream {
  Write-Host '== Runner process ==' -ForegroundColor Cyan
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' } |
    Select-Object ProcessId,
      @{n='Python';e={($_.CommandLine -split '"')[1]}},
      @{n='Args';e={ $_.CommandLine -replace '.*runner_stream\.py','runner_stream.py' }}

  Write-Host "`n== Last OUT/ERR logs ==" -ForegroundColor Cyan
  $o = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.out.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  $e = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.err.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1

  if ($o) { "OUT: $($o.FullName)"; Get-Content $o.FullName -Tail 20 } else { 'No OUT yet.' }
  if ($e) { "`nERR: $($e.FullName)"; Get-Content $e.FullName -Tail 20 } else { 'No ERR yet.' }
}
function tail-stream-err {
  $e = Get-ChildItem (Join-Path $Script:LogsDir 'stream_run.*.err.log') -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Desc | Select-Object -First 1
  if ($e) {
    "ERR: $($e.FullName)"
    Get-Content $e.FullName -Wait -Tail 120
  } else {
    Write-Host 'No ERR log yet.'
  }
}

function ps-stream {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*runner_stream.py*' -or $_.CommandLine -like '*runner_paper.py*' } |
    Select-Object ProcessId,
      @{n='Runner';e={($_.CommandLine -split 'runner_')[1] -split '\.py' | Select-Object -First 1 | ForEach-Object {"runner_$_.py"}}},
      @{n='ClientId';e={ if ($_.CommandLine -match '--client-id\s+(\d+)'){ $matches[1] } }},
      @{n='Python';e={($_.CommandLine -split '"')[1]}},
      @{n='Cmd';e={$_.CommandLine}}
}
