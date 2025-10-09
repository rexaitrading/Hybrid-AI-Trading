# Binance ETH1H wrapper (ASCII-only, scheduler-proof)
$ErrorActionPreference = 'Continue'
function Write-Log([string]$Path,[string]$Line){
  Write-Host $Line
  Add-Content -Path $Path -Value $Line -Encoding UTF8
}

# resolve repo root for console + scheduler
$self = $MyInvocation.MyCommand.Path
$dir  = if ([string]::IsNullOrEmpty($self)) { (Get-Location).Path } else { Split-Path -Parent $self }
$root = Split-Path -Parent $dir

$py  = Join-Path $root ".venv\Scripts\python.exe"
$cli = Join-Path $root "scripts\run_eth1h_paper.py"
$lgd = Join-Path $root "logs"
$log = Join-Path $lgd  "eth1h_runner_ps1.log"
$env:PYTHONPATH = Join-Path $root "src"
if (-not (Test-Path $lgd)) { New-Item -ItemType Directory -Path $lgd -Force | Out-Null }

Write-Log $log "PythonPath: $py"
Write-Log $log "ScriptPath: $cli"
Write-Log $log "LogPath:    $log"

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Log $log "[$stamp] Running ETH1H Runner..."
Push-Location $root
try{
  & $py $cli 2>&1 | ForEach-Object { Write-Log $log $_ }
  Write-Log $log "[Binance done] ExitCode=0"
} finally { Pop-Location }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Log $log "[$stamp] Finished."