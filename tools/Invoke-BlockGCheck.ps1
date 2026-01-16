[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("ALL_STRICT","SYMBOL_ONLY","BUILD_ONLY")]
  [string]$Mode = "BUILD_ONLY"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$psExe    = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

$logsRoot = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logsRoot)){
  New-Item -ItemType Directory -Force -Path $logsRoot | Out-Null
}
$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")

function Run-Tool([string]$label,[string[]]$argList,[int]$timeoutSec=120){
  $out = Join-Path $logsRoot ("invoke_blockg_" + $label + "_" + $ts + ".out.txt")
  $err = Join-Path $logsRoot ("invoke_blockg_" + $label + "_" + $ts + ".err.txt")

  if(-not (Test-Path -LiteralPath $psExe)){
    throw ("[A4] psExe missing: " + $psExe)
  }

  # Sanitize argList to avoid Start-Process ArgumentList validation errors
  $args2 = @()
  foreach($a in @($argList)){
    if($null -eq $a){ continue }
    $s = ([string]$a)
    if([string]::IsNullOrWhiteSpace($s)){ continue }
    $args2 += $s
  }
  if($args2.Count -eq 0){
    throw ("[A4] ArgumentList empty after sanitize (label=" + $label + ")")
  }

  Write-Host ("[A4] RUN label=" + $label + " timeoutSec=" + $timeoutSec + " out=" + $out + " err=" + $err) -ForegroundColor Cyan
  $p = Start-Process -FilePath $psExe -ArgumentList $args2 -PassThru -NoNewWindow `
      -RedirectStandardOutput $out -RedirectStandardError $err

  if(-not $p.WaitForExit($timeoutSec * 1000)){
    try { $p.Kill() } catch {}
    throw ("[A4] TIMEOUT label=" + $label + " timeoutSec=" + $timeoutSec + " out=" + $out + " err=" + $err)
  }

  $code = [int]$p.ExitCode
  if($code -ne 0){
    Write-Host ("[A4] FAIL label=" + $label + " exit=" + $code) -ForegroundColor Yellow
    Write-Host ("[A4] out=" + $out) -ForegroundColor DarkYellow
    Write-Host ("[A4] err=" + $err) -ForegroundColor DarkYellow
    if(Test-Path -LiteralPath $out){ Get-Content -LiteralPath $out -Tail 120 -Encoding UTF8 | Out-Host }
    if(Test-Path -LiteralPath $err){ Get-Content -LiteralPath $err -Tail 120 -Encoding UTF8 | Out-Host }
  }
  return [pscustomobject]@{ ExitCode=$code; Out=$out; Err=$err }
}

# 0) Rebuild GlobalReadyV0 contract pack (unless explicitly skipped)
try{
  if((($env:HAT_SKIP_GLOBALREADY + "")).Trim() -ne "1"){
    $gr = Join-Path $repoRoot "tools\Build-GlobalReadyV0-AllMarkets.ps1"
    if(-not (Test-Path -LiteralPath $gr)){ throw "Missing: $gr" }
    $r = Run-Tool "globalready" @("-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$gr) 180
    if($r.ExitCode -ne 0){ $global:LASTEXITCODE = $r.ExitCode; exit $r.ExitCode }
  } else {
    Write-Host "[A4] HAT_SKIP_GLOBALREADY=1 -> skip GlobalReadyV0 rebuild" -ForegroundColor DarkYellow
  }
}catch{
  Write-Host ("[A4] FAIL-CLOSED: GlobalReadyV0 rebuild failed: " + $_.Exception.Message) -ForegroundColor Red; $global:LASTEXITCODE = 2; exit 2
}

# 1) Build Block-G status stub (unless skip flag)
$skipBuild = (([string]$env:HAT_BLOCKG_SKIP_BUILD) + "").Trim()
if($skipBuild -eq "1"){
  Write-Host "[BLOCKG] Invoke-BlockGCheck: SKIP build (env:HAT_BLOCKG_SKIP_BUILD=1)" -ForegroundColor Yellow
} else {
  $builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
  if(-not (Test-Path -LiteralPath $builder)){ throw "Missing builder: $builder" }
  $r = Run-Tool "build" @("-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$builder,"-Symbol",$Symbol,"-Market",$Market) 180
  if($r.ExitCode -ne 0){ $global:LASTEXITCODE = $r.ExitCode; exit $r.ExitCode }
}

# 2) Contract-only checker
$checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $checker)){ throw "Missing checker: $checker" }

if($Symbol -eq "ALL"){
  $codes = @{}
  foreach($sym in @("NVDA","SPY","QQQ")){
    $r = Run-Tool ("check_" + $sym.ToLowerInvariant()) @("-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$checker,"-Symbol",$sym,"-Mode",$Mode,"-Market",$Market) 120
    $codes[$sym] = [int]$r.ExitCode
  }
  if(@($codes.Values | Where-Object { $_ -ne 0 }).Count -gt 0){
    Write-Host ("[BLOCKG] NOT READY some symbols => " + ($codes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } -join ", ")) -ForegroundColor Yellow
    $global:LASTEXITCODE = 2
    exit 2
  }
  Write-Host "[BLOCKG] READY for ALL symbols (NVDA, SPY, QQQ)." -ForegroundColor Green
  $global:LASTEXITCODE = 0
  exit 0
}

$r = Run-Tool "check" @("-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File",$checker,"-Symbol",$Symbol,"-Mode",$Mode,"-Market",$Market) 120
$global:LASTEXITCODE = [int]$r.ExitCode
exit $global:LASTEXITCODE
