param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

$logDir = Join-Path $root ".logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir ("premarket_micro_{0}.log" -f $ts)

$runner = Join-Path $root "scripts\run_premarket_micro.ps1"
if (-not (Test-Path $runner)) {
    throw "run_premarket_micro.ps1 not found at $runner"
}

Write-Host "[HybridAITrading] PreMarket MICRO+LOG starting..." -ForegroundColor Cyan
Write-Host "[HybridAITrading] Log file: $logPath" -ForegroundColor DarkCyan

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$args = @(
    "-NoLogo",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $runner
)
if ($Verbose) {
    $args += "-Verbose"
}
$psi.Arguments = ($args -join " ")
$psi.UseShellExecute        = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

$stdout = $proc.StandardOutput.ReadToEnd()
$stderr = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()

# Write to log file
$logContent = $stdout + [Environment]::NewLine + $stderr
[System.IO.File]::WriteAllText($logPath, $logContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Host $stdout
if ($stderr) {
    Write-Host $stderr -ForegroundColor Red
}

Write-Host "[HybridAITrading] PreMarket MICRO+LOG finished. Log: $logPath" -ForegroundColor Green

if ($proc.ExitCode -ne 0) {
    throw "PreMarket MICRO failed with exit code $($proc.ExitCode). See log: $logPath"
}
