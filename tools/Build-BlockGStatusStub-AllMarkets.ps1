[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("US","HK","HK_SH","HK_SZ","JP","SG","IN","KR","TW")]
  [string[]]$Markets = @("US","HK","JP","SG","IN","KR","TW")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Fail([string]$m){
  Write-Host ("[BLOCKG-ALL] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

$builder = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
if(-not (Test-Path -LiteralPath $builder)){ Fail "Missing builder: $builder" }

$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

Write-Host ("[BLOCKG-ALL] RepoRoot=" + $repoRoot) -ForegroundColor DarkGray
Write-Host ("[BLOCKG-ALL] Symbol=" + $Symbol + " Markets=" + ($Markets -join ",")) -ForegroundColor Cyan

foreach($m in $Markets){
  $m2 = ($m + "").Trim().ToUpperInvariant()
  Write-Host ("[BLOCKG-ALL] Build start Market=" + $m2) -ForegroundColor Cyan

  & $psExe -NoProfile -ExecutionPolicy Bypass -File $builder -Symbol $Symbol -Market $m2 *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail ("Build-BlockGStatusStub failed Market=" + $m2 + " exit=" + $LASTEXITCODE) }

  $logRoot = & $psExe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Get-MarketLogRoot.ps1") -Market $m2
  if(-not $logRoot){ Fail ("Get-MarketLogRoot returned empty for Market=" + $m2) }

  $stub = Join-Path $logRoot "blockg_status_stub.json"
  if(-not (Test-Path -LiteralPath $stub)){ Fail ("Missing stub after build Market=" + $m2 + " path=" + $stub) }

  $fi = Get-Item -LiteralPath $stub
  Write-Host ("[BLOCKG-ALL] OK Market=" + $m2 + " stub=" + $stub + " bytes=" + $fi.Length) -ForegroundColor Green
}

Write-Host "[BLOCKG-ALL] DONE" -ForegroundColor Green
exit 0

