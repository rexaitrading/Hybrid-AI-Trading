# Combo wrapper (ASCII-only): Binance -> Kraken
$ErrorActionPreference = 'Continue'

function Write-Log([string]$Path,[string]$Line){
  Write-Host $Line
  Add-Content -Path $Path -Value $Line -Encoding UTF8
}

# robust repo root
$self = $MyInvocation.MyCommand.Path
$dir  = if ([string]::IsNullOrEmpty($self)) { (Get-Location).Path } else { Split-Path -Parent $self }
$root = Split-Path -Parent $dir

$lgd = Join-Path $root "logs"
$log = Join-Path $lgd  "eth1h_combo.log"
$bin = Join-Path $root "scripts\run_eth1h_paper.ps1"
$krk = Join-Path $root "scripts\run_eth1h_kraken.ps1"
$env:PYTHONPATH = Join-Path $root "src"
if (-not (Test-Path $lgd)) { New-Item -ItemType Directory -Path $lgd -Force | Out-Null }

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Log $log "[$stamp] Combo start (Binance -> Kraken)..."

Push-Location $root
try{
  Write-Log $log "----- Binance start -----"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bin | Out-Null
  Write-Log $log "[Combo] Binance wrapper completed."

  Write-Log $log "----- Kraken start -----"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File $krk | Out-Null
  Write-Log $log "[Combo] Kraken wrapper completed."
}
finally { Pop-Location }

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Log $log "[$stamp] Combo finished."
