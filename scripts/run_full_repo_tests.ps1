param(
  [ValidateSet("Isolated","RespectIni")] [string]$Mode = "RespectIni",
  [switch]$Install,
  [switch]$WithCoverage,
  [int]$FailUnder = 0,
  [switch]$JUnit
)
$ErrorActionPreference="Stop"
chcp 65001 > $null; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)

function Run-Pytest([string[]]$Args) {
  $pyArgs = @("-m","pytest") + $Args
  Write-Host ("pytest cmd: python {0}" -f ($pyArgs -join ' ')) -ForegroundColor Cyan
  & python @pyArgs
  $code = $LASTEXITCODE
  if ($code -ne 0) { Write-Host ("pytest exit: {0}" -f $code) -ForegroundColor Yellow }
  exit $code
}

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check
  python -m pip install -U pytest pytest-cov coverage --disable-pip-version-check
}

$repoRoot = (Resolve-Path ".").Path
$testsDir = Join-Path $repoRoot "tests"
if (-not (Test-Path $testsDir)) { throw "tests/ not found under $repoRoot" }

$baseArgs = @($testsDir)
$junitArgs = @(); if ($JUnit) { $junitArgs = @("--junit-xml=junit.xml") }

$covArgs = @()
if ($WithCoverage) {
  $covArgs = @("--cov=src","--cov-branch","--cov-config=.coveragerc",
               "--cov-report=term-missing","--cov-report=html","--cov-report=xml")
  if ($FailUnder -gt 0) { $covArgs += @("--cov-fail-under=$FailUnder") }
}

if ($Mode -eq "Isolated") {
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  Write-Host "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 (isolated)" -ForegroundColor Yellow

  $tmpDir = Join-Path $env:TEMP ("pytest_full_{0}" -f ([Guid]::NewGuid()))
  New-Item -ItemType Directory -Path $tmpDir | Out-Null
  $tmpIni = Join-Path $tmpDir "pytest.ini"
  [IO.File]::WriteAllText($tmpIni, "[pytest]`naddopts = -q --maxfail=1`n", [Text.UTF8Encoding]::new($false))

  $args = @()
  $args += $junitArgs
  if ($WithCoverage) { $args += @("-p","pytest_cov") }     # add once
  $args += $covArgs
  $args += @("-c",$tmpIni,"--rootdir",$repoRoot,"--confcutdir",$repoRoot,"-o","addopts=")
  $args += $baseArgs

  try { Run-Pytest $args } finally { try { Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue } catch {} }
}
else {
  Remove-Item Env:PYTEST_DISABLE_PLUGIN_AUTOLOAD -ErrorAction SilentlyContinue
  $iniPath  = Join-Path $repoRoot "pytest.ini"
  $needsCov = $WithCoverage
  if (Test-Path $iniPath) {
    $iniText = Get-Content -Raw $iniPath
    if ($iniText -match '--cov') { $needsCov = $true }
  }
  $args = @()
  $args += $junitArgs
  if ($needsCov) { $args += @("-p","pytest_cov") + $covArgs }
  $args += @("--rootdir",$repoRoot,"--confcutdir",$repoRoot)
  $args += $baseArgs
  Run-Pytest $args
}
