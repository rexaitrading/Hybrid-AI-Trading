$me = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
  exit
}

$ibgExe = (Get-ChildItem "C:\Jts\ibgateway\*\ibgateway.exe" | Sort-Object LastWriteTime -desc | Select-Object -First 1).FullName

# Program rule (idempotent)
if (-not (Get-NetFirewallRule -DisplayName "IB Gateway API (Program)" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "IB Gateway API (Program)" `
    -Program $ibgExe -Direction Inbound -Action Allow -Profile Private,Domain | Out-Null
} else {
  Set-NetFirewallRule -DisplayName "IB Gateway API (Program)" -Enabled True -Action Allow -Profile Private,Domain | Out-Null
}

# Port rule (idempotent)
if (-not (Get-NetFirewallRule -DisplayName "IB Gateway API Port 4003" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "IB Gateway API Port 4003" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 4003 -Profile Private,Domain | Out-Null
} else {
  Set-NetFirewallRule -DisplayName "IB Gateway API Port 4003" -Enabled True -Action Allow -Profile Private,Domain | Out-Null
}

Write-Host "Firewall rules ensured for ibgateway.exe and TCP/4003." -ForegroundColor Green