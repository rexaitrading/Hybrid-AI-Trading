param(
  [int]$BufferMinutes = 5,
  [string]$Entry      = "hybrid_ai_trading.runners.paper_trader",
  [string]$ScriptPath = "",
  [string]$Config     = "config\paper_runner.yaml",
  [string]$UseLivePriceRM = "1",
  [string]$Log = ".\.logs\launch_trader.log"
)
$ErrorActionPreference = "Stop"
$stamp = (Get-Date).ToString("s")

# Ensure logs dir
$dir = Split-Path -Parent $Log
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

# 1) Preflight (spawned process so we capture stdout/err + exit)
$pf = (Resolve-Path .\scripts\preflight.ps1).Path
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = "powershell.exe"
$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$pf`""
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()
$p.WaitForExit()
$code = $p.ExitCode

Add-Content -Path $Log -Value "[$stamp] preflight exit=$code"
if ($out) { Add-Content -Path $Log -Value $out.Trim() }
if ($err) { Add-Content -Path $Log -Value ("ERR: " + $err.Trim()) }

if ($code -ne 0) {
  Add-Content -Path $Log -Value "[$stamp] NO-GO: skipping trader launch"
  exit 1
}

# 2) Buffer before market open (if requested)
if ($BufferMinutes -gt 0) {
  Add-Content -Path $Log -Value "[$stamp] GO: waiting $BufferMinutes minute(s) before launch..."
  Start-Sleep -Seconds (60 * $BufferMinutes)
}

# 3) Launch trader (uses your smart run_trader.ps1)
$runner = (Resolve-Path .\scripts\run_trader.ps1).Path
$env:HAT_USE_LIVE_PRICE_RM = $UseLivePriceRM
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"

# Prefer module mode unless ScriptPath provided
if ($Entry -and -not $ScriptPath) {
  $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,
            "-Entry",$Entry,"-Config",$Config,"-UseLivePriceRM",$UseLivePriceRM) -join ' '
} else {
  if (-not $ScriptPath) { $ScriptPath = ".\src\hybrid_ai_trading\runners\paper_trader.py" }
  $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,
            "-ScriptPath",$ScriptPath,"-Config",$Config,"-UseLivePriceRM",$UseLivePriceRM) -join ' '
}

$psi2 = New-Object System.Diagnostics.ProcessStartInfo
$psi2.FileName  = "powershell.exe"
$psi2.Arguments = $args
$psi2.UseShellExecute = $false
$psi2.RedirectStandardOutput = $true
$psi2.RedirectStandardError  = $true
$p2 = [System.Diagnostics.Process]::Start($psi2)
$out2 = $p2.StandardOutput.ReadToEnd()
$err2 = $p2.StandardError.ReadToEnd()
$p2.WaitForExit()
$code2 = $p2.ExitCode

$stamp2 = (Get-Date).ToString("s")
Add-Content -Path $Log -Value "[$stamp2] trader exit=$code2"
if ($out2) { Add-Content -Path $Log -Value $out2.Trim() }
if ($err2) { Add-Content -Path $Log -Value ("ERR: " + $err2.Trim()) }

exit $code2
