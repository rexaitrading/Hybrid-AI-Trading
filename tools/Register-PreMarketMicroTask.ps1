param(
    [string]$TaskName = "HybridAITrading PreMarket Micro",
    [string]$StartTime = "06:35",   # HH:mm local time
    [switch]$UseLogWrapper           # if set, use Run-PremarketMicroAndLog.ps1 instead of run_premarket_micro.ps1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

$scriptsDir = Join-Path $root "scripts"
$toolsDir   = Join-Path $root "tools"

if ($UseLogWrapper) {
    $targetScript = Join-Path $toolsDir "Run-PremarketMicroAndLog.ps1"
} else {
    $targetScript = Join-Path $scriptsDir "run_premarket_micro.ps1"
}

if (-not (Test-Path $targetScript)) {
    throw "Target script not found at $targetScript"
}

$psExe = (Get-Command powershell.exe -ErrorAction Stop).Source

$actionArgs = @(
    '-NoLogo',
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', '"' + $targetScript + '"'
) -join ' '

Write-Host "[HybridAITrading] Registering Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host "  PowerShell: $psExe" -ForegroundColor DarkGray
Write-Host "  Script:     $targetScript" -ForegroundColor DarkGray
Write-Host "  StartTime:  $StartTime (local)" -ForegroundColor DarkGray

$action  = New-ScheduledTaskAction -Execute $psExe -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date $StartTime)

# Optional: run only on weekdays; uncomment if desired
# $trigger.DaysOfWeek = 'Monday','Tuesday','Wednesday','Thursday','Friday'

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Host "[HybridAITrading] Scheduled Task registered: $TaskName" -ForegroundColor Green
