[CmdletBinding()]
param(
  [int]$TimeoutSec = 60,
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$root = Split-Path -Parent $toolsDir
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[GS-BUILD] python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH = (Join-Path $root "src")

$logDir = Join-Path $root "logs\gatescore"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outLog = Join-Path $logDir ("daily_build_" + $ts + ".out.txt")
$errLog = Join-Path $logDir ("daily_build_" + $ts + ".err.txt")

$csv = Join-Path $root "logs\gatescore_daily_summary.csv"
if (-not (Test-Path $csv)) { throw "[GS-BUILD] missing input csv: $csv" }


$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
function Has-TodayRow([string]$sym){
  $sd = Get-SessionDate -sym $sym
  if (-not $sd) { return $false }
  $pat = ("^" + [regex]::Escape($sym) + ",.*," + [regex]::Escape($sd) + "$")
  return (Select-String -Path $csv -Pattern $pat -Quiet)
}

# Fail-closed: if no today row, do not spawn python (prevents freeze + false data).
if($Symbol -ne "ALL"){
  if(-not (Has-TodayRow -sym $Symbol)){
    Write-Host ("[GS-BUILD] FAIL-CLOSED: no today row for {0} in {1} today={2}" -f $Symbol,$csv,$today) -ForegroundColor Yellow
    exit 2
  }
}
$startUtc = (Get-Date).ToUniversalTime()

function Kill-LeftoverVenvPython([datetime]$sinceUtc){
  $sinceWmi = $sinceUtc.ToString("yyyyMMddHHmmss.ffffff") + "+000"
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -match 'C:\\HAT\\\.venv\\Scripts\\python\.exe' -and
      $_.CreationDate -ge $sinceWmi
    } |
    ForEach-Object {
      try { Stop-Process -Id $_.ProcessId -Force } catch { }
    }
}

function RunPyTimeout([string[]]$args,[int]$timeoutSec){
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $py
  $psi.Arguments = ($args -join " ")
  $psi.WorkingDirectory = $root
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError  = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  [void]$proc.Start()
  $childPid = $proc.Id

  if (-not $proc.WaitForExit($timeoutSec * 1000)) {
    try { Stop-Process -Id $childPid -Force } catch { }
    "[TIMEOUT] killed pid=$childPid after ${timeoutSec}s args=$($args -join ' ')" | Out-File -FilePath $errLog -Encoding utf8
    Kill-LeftoverVenvPython -sinceUtc $startUtc
    exit 124
  }

  $out = $proc.StandardOutput.ReadToEnd()
  $err = $proc.StandardError.ReadToEnd()
  if ($out) { $out | Out-File -FilePath $outLog -Encoding utf8 }
  if ($err) { $err | Out-File -FilePath $errLog -Encoding utf8 }

  Kill-LeftoverVenvPython -sinceUtc $startUtc
  exit $proc.ExitCode
}

$syms = @("NVDA","SPY","QQQ")
if ($Symbol -ne "ALL") { $syms = @($Symbol) }

foreach($s in $syms){
  if(-not (Has-TodayRow -sym $s)){
    Write-Host ("[GS-BUILD] FAIL-CLOSED: no today row for {0} in {1} today={2}" -f $s,$csv,$today) -ForegroundColor Yellow
    exit 2
  }  $rc = $code = "import sys,runpy; sys.path.insert(0,r'$env:PYTHONPATH'); runpy.run_module('hybrid_ai_trading.gatescore.daily_build', run_name='__main__')"
$rc = RunPyTimeout @("-I","-X","faulthandler","-c",$code,"--csv",$csv,"--symbol",$s) $TimeoutSec
  if ($rc -ne 0) {
    Write-Host "[GS-BUILD] FAIL symbol=$s rc=$rc logs=$logDir" -ForegroundColor Yellow
    exit $rc
  }
}

Write-Host "[GS-BUILD] OK symbols=$($syms -join ',') logs=$logDir" -ForegroundColor Green
exit 0

