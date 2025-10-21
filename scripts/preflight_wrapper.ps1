$ErrorActionPreference="Stop"
$log = ".\.logs\preflight.log"
$stamp = (Get-Date).ToString("s")
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = "powershell.exe"
$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `".\scripts\preflight.ps1`""
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

