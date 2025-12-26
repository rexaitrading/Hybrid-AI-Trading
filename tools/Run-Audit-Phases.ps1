[CmdletBinding()]
param(
  [int]$TimeoutSec = 240
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$script = Join-Path $root "tools\Audit-Phases.ps1"
if (-not (Test-Path $script)) { throw "Missing: $script" }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$psi.WorkingDirectory = $root
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()

if (-not $p.WaitForExit($TimeoutSec * 1000)) {
  try { $p.Kill($true) } catch { }
  Write-Host "[RUN-AUDIT] TIMEOUT after $TimeoutSec sec" -ForegroundColor Yellow
  exit 124
}

$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()
if ($out) { $out | Out-Host }
if ($err) { $err | Out-Host }

exit $p.ExitCode
