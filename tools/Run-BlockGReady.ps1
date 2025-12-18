[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",

  [Parameter(Mandatory=$false)]
  [switch]$Build
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

# Repo-root resolution safe in file execution
$scriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
  throw "[Run-BlockGReady] Cannot resolve script path. Run as a file."
}
$toolsDir = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Invoke-Child([string]$file, [string[]]$args) {
  $ps = (Get-Command powershell).Source
  & $ps -NoProfile -ExecutionPolicy Bypass -File $file @args
  return $LASTEXITCODE
}

function One([string]$sym) {
  if ($Build) {
    & (Join-Path $toolsDir "Build-BlockGStatusStub.ps1") -Symbol $sym | Out-Host
  }
  $code = Invoke-Child (Join-Path $toolsDir "Check-BlockGReady-Wrapper.ps1") @("-Symbol", $sym)
  return $code
}

$syms = @()
switch ($Symbol) {
  "ALL" { $syms = @("NVDA","SPY","QQQ") }
  default { $syms = @($Symbol) }
}

$results = @{}
foreach ($s in $syms) {
  $rc = One $s
  $results[$s] = $rc
}

# Print a stable one-liner matrix
$line = ($results.Keys | Sort-Object | ForEach-Object { "$_=$($results[$_])" }) -join "  "
Write-Host "[BLOCKG_MATRIX] $line" -ForegroundColor Cyan

# If ALL, return 0 only if all are 0; else return max exit code for visibility.
if ($Symbol -eq "ALL") {
  if (($results.Values | Where-Object { $_ -ne 0 }).Count -eq 0) { return 0 }
  return (($results.Values | Measure-Object -Maximum).Maximum)
}

return $results[$Symbol]