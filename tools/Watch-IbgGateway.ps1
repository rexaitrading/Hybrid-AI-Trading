param(
    [string] $LogPath = "logs\\ibg_watchdog.log",
    [int]    $IntervalSeconds = 60,
    [switch] $RunOnce
)

$ErrorActionPreference = "Stop"

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path (Split-Path $LogPath -Parent))) {
    New-Item -ItemType Directory -Path (Split-Path $LogPath -Parent) -Force | Out-Null
}

Write-Host "IBG-WATCH: starting watchdog, logging to $LogPath" -ForegroundColor Cyan

while ($true) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $proc = Get-Process -Name "ibgateway1" -ErrorAction SilentlyContinue

    $line = if ($proc) {
        "$ts | ibgateway1: RUNNING (PID(s): $($proc.Id -join ', '))"
    } else {
        "$ts | ibgateway1: MISSING"
    }

    Add-Content -Path $LogPath -Value $line

    if ($RunOnce) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}