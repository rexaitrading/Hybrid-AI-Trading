Write-Host '=== Session Preflight (IB Gateway / Paper) â€” probe only ==='

# 1) Load .env
if (Test-Path ".env") {
  Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
      $name  = $matches[1].Trim()
      $value = $matches[2].Trim()
      Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
  }
}
Write-Host 'Env:'
Write-Host ('  IB_HOST={0}'    -f $env:IB_HOST)
Write-Host ('  IB_PORT={0}'    -f $env:IB_PORT)
Write-Host ('  IB_ACCOUNT={0}' -f $env:IB_ACCOUNT)

# 2) Port check (PowerShell only)
Write-Host ''
Write-Host '-- Port check (Test-NetConnection) --'
$tnc = Test-NetConnection -ComputerName $env:IB_HOST -Port ([int]$env:IB_PORT) -WarningAction SilentlyContinue
if ($tnc.TcpTestSucceeded) { Write-Host 'âœ… Port reachable' } else { Write-Host 'âŒ Port NOT reachable' }

# 3) Socket cleanup + wait: kill FIN_WAIT_2; wait up to 45s for FIN_WAIT_2 + CLOSE_WAIT to clear
Write-Host ''
Write-Host '-- Socket cleanup --'
$port = [int]$env:IB_PORT
$lines = cmd /c ("netstat -ano | findstr :{0}" -f $port)
$finPids = $lines | Select-String 'FIN_WAIT_2' | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
if ($finPids) {
  Write-Host ('Killing FIN_WAIT_2 client PIDs: {0}' -f ($finPids -join ', '))
  Stop-Process -Id $finPids -Force -ErrorAction SilentlyContinue
} else {
  Write-Host 'No FIN_WAIT_2 clients found.'
}
$deadline = (Get-Date).AddSeconds(45); $cleared = $false
do {
  Start-Sleep -Milliseconds 500
  $lines = cmd /c ("netstat -ano | findstr :{0}" -f $port)
  $hasFin   = ($lines | Select-String 'FIN_WAIT_2')
  $hasClose = ($lines | Select-String 'CLOSE_WAIT')
  if (-not $hasFin -and -not $hasClose) { $cleared = $true; break }
} while ((Get-Date) -lt $deadline)
if ($cleared) { Write-Host 'âœ… sockets clear' } else { Write-Host 'âš ï¸ sockets not fully clear; proceeding' }

# 4) Single connection: PROBE ONLY (fresh clientId)
$env:IB_CLIENT_ID = (Get-Random -Minimum 1000 -Maximum 9999).ToString()
Write-Host ''
Write-Host ('-- Probe (clientId={0}) --' -f $env:IB_CLIENT_ID)
python scripts\probe_ib.py

Write-Host ''
Write-Host 'Preflight complete.'
