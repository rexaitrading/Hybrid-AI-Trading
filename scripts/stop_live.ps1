$ErrorActionPreference = "Stop"
Get-CimInstance Win32_Process |
  ? { $_.Name -eq "python.exe" -and $_.CommandLine -match "hybrid_ai_trading\.pipelines\.live_loop" } |
  % { try { Stop-Process -Id $_.ProcessId -Force } catch {} }
Get-CimInstance Win32_Process |
  ? { $_.Name -like "powershell*" -and $_.CommandLine -match "scripts\\run_live_min\.ps1" } |
  % { try { Stop-Process -Id $_.ProcessId -Force } catch {} }
Write-Host " live loop processes stopped" -ForegroundColor Green
