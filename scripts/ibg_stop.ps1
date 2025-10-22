# scripts\ibg_stop.ps1
Get-Process ibgateway,java -ErrorAction SilentlyContinue | ForEach-Object {
  try { taskkill /PID $_.Id /F | Out-Null } catch {}
}
"Stopped IB Gateway/Java."
