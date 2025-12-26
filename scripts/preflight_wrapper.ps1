[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$logDir = Join-Path $repoRoot "logs"
if(-not (Test-Path $logDir)){ New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$log = Join-Path $logDir "preflight.log"

$stamp = (Get-Date).ToString("s")

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = "powershell.exe"
$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$repoRoot\scripts\preflight.ps1`""
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false

$p = [System.Diagnostics.Process]::Start($psi)
$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()
$p.WaitForExit()
$code = $p.ExitCode

Add-Content -Path $log -Value "[$stamp] exit=$code"
if ($out) { Add-Content -Path $log -Value $out.Trim() }
if ($err) { Add-Content -Path $log -Value ("ERR: " + $err.Trim()) }

exit $code