if(-not $Force){
  Write-Host "Refusing to kill IBG/TWS without -Force" -ForegroundColor Yellow
  exit 2
}
param([switch]$Force)

$ErrorActionPreference='Stop'
Get-Process ibgateway,javaw -ErrorAction SilentlyContinue | ForEach-Object {
  try { $_.CloseMainWindow() | Out-Null; Start-Sleep -Seconds 5 } catch {}
}
$alive = Get-Process ibgateway,javaw -ErrorAction SilentlyContinue
if ($alive) {
  Write-Host "Force killing leftover ibgateway/javaw..." -ForegroundColor Yellow
  $alive | ForEach-Object { taskkill /PID $_.Id /F | Out-Null }
}
Write-Host "IBG stopped."